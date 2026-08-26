#!/usr/bin/env python3
"""adsbdb.com flight-route enrichment client with a persistent,
callsign-keyed hit/miss cache (D-02, D-P2-05).

Live-verified this session (02-RESEARCH.md) against all 38 distinct real
callsigns observed in Phase 1's Orly-area sample: `api.adsbdb.com/v0/
callsign/{callsign}` returned a full route (airline + origin + destination)
for only **20 of 38 (52.6%)**. Coverage is excellent for legacy/full-service
carriers (Air France, Iberia, TAP, Air Algerie, CCM Airlines, Vueling all
hit) and poor for low-cost carriers using per-tail rotating callsigns
(Transavia France `TVF*` hit only 2 of 20) - and this airport's traffic mix
is dominated by exactly the carriers adsbdb covers least well. The miss
path this module implements (returning `None`, never raising) is therefore
a **designed first-class state**, not an error path bolted on afterward -
02-UI-SPEC.md's "Route unavailable" fallback is the expected, roughly
coin-flip outcome for this project's real traffic, not a rare edge case
(N-02-04-01).

Every failure mode - a 404, a 5xx, a connection error, a non-JSON body, or
a structurally incomplete 200 - degrades to a cached miss instead of
raising (T-02-04-01/03): a lookup problem must never abort a poll cycle.
Both hits and misses are cached, and a cached callsign (hit or miss) is
never re-queried - 02-RESEARCH.md names re-querying every poll as an
explicit anti-pattern, and adsbdb's rate limit is undocumented (assumption
A2). The cache is a plain, JSON-serialisable dict so it can be persisted in
`poll_state.json` across `poll_loop.py`'s process boundary (D-P2-02 - this
script is a systemd oneshot with no in-process memory between cycles).
"""
import os
import re
import sys

import requests

# Allow both `import server.plane.enrich` (package import) and direct
# script execution, matching detect.py/render.py's sys.path bootstrap.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.plane import runway_config

ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"

# adsbdb is a free, unauthenticated, crowdsourced service - identify this
# project honestly, same self-identification convention detect.py already
# established for the aggregator calls.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 2 plane-view production server; "
    "see server/README.md for what this traffic is)"
)

DEFAULT_TIMEOUT = 10.0

# T-02-04-04: bound poll_state.json's "enrichment_cache" so a long-running
# server cannot grow the state file without limit. "a few hundred entries"
# comfortably covers this airport's realistic distinct-callsign volume
# (02-RESEARCH.md: tens to low hundreds of enrichment calls/day).
CACHE_MAX_ENTRIES = 300

# T-02-04-02: an aggregator-supplied callsign is untrusted input
# interpolated directly into the outbound adsbdb request URL - constrain it
# to alphanumeric-only before that interpolation happens, so a hostile
# callsign field can never inject a path segment or query parameter.
_CALLSIGN_SAFE_RE = re.compile(r"^[A-Z0-9]+$")

# adsbdb returns municipality names in title case (e.g. "Palma De
# Mallorca"); UI-SPEC's Body role calls for sentence case. These interior
# connective particles are lower-cased unless they are the first word.
_LOWERCASE_CITY_PARTICLES = {"de", "del", "la", "le", "van", "von", "di", "da"}


def normalise_callsign(raw):
    """Strip whitespace and upper-case `raw`; return None for anything
    empty or non-string. Every cache key and every outbound request URL
    goes through this exact function, so `"TVF16VB "` and `"tvf16vb"`
    always resolve to the same cache entry and the same request
    (02-RESEARCH.md assumption A4 - rules out a self-inflicted formatting
    bug as a cause of misses).
    """
    if not isinstance(raw, str):
        return None
    stripped = raw.strip().upper()
    return stripped or None


def _is_url_safe_callsign(normalised):
    return bool(_CALLSIGN_SAFE_RE.match(normalised))


def to_sentence_case_city(raw):
    """Turn an adsbdb-style title-case municipality name (e.g. "Palma De
    Mallorca") into UI-SPEC's sentence case ("Palma de Mallorca"):
    capitalise every word except interior connective particles, which are
    lower-cased unless they are the first word of the name.
    """
    words = raw.split(" ")
    out = []
    for i, word in enumerate(words):
        lowered = word.lower()
        if i > 0 and lowered in _LOWERCASE_CITY_PARTICLES:
            out.append(lowered)
        else:
            out.append(word.capitalize())
    return " ".join(out)


def default_transport(callsign, timeout=DEFAULT_TIMEOUT):
    """Thin `requests.get()` wrapper: GET the adsbdb endpoint for
    `callsign` (already normalised by the caller) and return
    `(status_code, parsed_json_or_None)`. A body that fails to parse as
    JSON is reported as `(status_code, None)` rather than raising -
    `lookup_route` treats a None body the same as any other structurally
    unexpected response (a miss).

    `lookup_route`'s injectable `transport` parameter exists specifically
    so tests can replace this with a hermetic fake that replays a
    committed fixture instead of making a live network call - see
    server/test_enrich.py.
    """
    url = ADSBDB_URL.format(callsign=callsign)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    try:
        body = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def _parse_route(body):
    """Defensive `isinstance()` walk of an adsbdb 200 response body
    (T-02-04-01), mirroring detect.py's own explicit-type-check discipline.
    Every one of `airline.name`, `origin.iata_code`, `origin.municipality`,
    `destination.iata_code` and `destination.municipality` must be a
    non-empty string, or the whole result is a miss - UI-SPEC has no
    partial-route state to render, so a half-resolved route must never
    reach the renderer.
    """
    if not isinstance(body, dict):
        return None
    response = body.get("response")
    if not isinstance(response, dict):
        return None
    flightroute = response.get("flightroute")
    if not isinstance(flightroute, dict):
        return None

    airline = flightroute.get("airline")
    origin = flightroute.get("origin")
    destination = flightroute.get("destination")
    if not isinstance(airline, dict) or not isinstance(origin, dict) or not isinstance(destination, dict):
        return None

    airline_name = airline.get("name")
    origin_iata = origin.get("iata_code")
    origin_city_raw = origin.get("municipality")
    destination_iata = destination.get("iata_code")
    destination_city_raw = destination.get("municipality")

    for value in (airline_name, origin_iata, origin_city_raw, destination_iata, destination_city_raw):
        if not isinstance(value, str) or not value.strip():
            return None

    return {
        "airline_name": airline_name,
        "origin_iata": origin_iata,
        "origin_city": to_sentence_case_city(origin_city_raw),
        "destination_iata": destination_iata,
        "destination_city": to_sentence_case_city(destination_city_raw),
    }


def _cache_get(cache, key):
    entry = cache.get(key)
    if not isinstance(entry, dict):
        return None, False
    return entry, True


def _route_from_entry(entry):
    return {
        "airline_name": entry.get("airline_name"),
        "origin_iata": entry.get("origin_iata"),
        "origin_city": entry.get("origin_city"),
        "destination_iata": entry.get("destination_iata"),
        "destination_city": entry.get("destination_city"),
    }


def lookup_route(callsign, cache, transport=None, timeout=DEFAULT_TIMEOUT):
    """Resolve `callsign` to a normalised route dict
    (`airline_name`/`origin_iata`/`origin_city`/`destination_iata`/
    `destination_city`), or `None` on any miss or failure. Never raises -
    every failure mode degrades to a cached miss instead of aborting the
    caller's render cycle (T-02-04-01/03).

    `cache` is a plain, JSON-serialisable dict (the caller persists it
    across process boundaries via poll_state.json's "enrichment_cache" key,
    D-P2-02) mapping the normalised callsign to either
    `{"found": True, <route fields>}` or `{"found": False}`. Both hits and
    misses are cached, and a cached callsign - hit or miss - is never
    re-queried.
    """
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _is_url_safe_callsign(normalised):
        return None

    entry, present = _cache_get(cache, normalised)
    if present:
        if entry.get("found"):
            return _route_from_entry(entry)
        return None

    fetch = transport or default_transport
    try:
        status_code, body = fetch(normalised, timeout)
    except Exception:
        cache[normalised] = {"found": False}
        return None

    if not (200 <= status_code < 300):
        # Covers the 404 "unknown callsign" definitive-miss case and every
        # other non-2xx response uniformly.
        cache[normalised] = {"found": False}
        return None

    route = _parse_route(body)
    if route is None:
        cache[normalised] = {"found": False}
        return None

    cache_entry = dict(route)
    cache_entry["found"] = True
    cache[normalised] = cache_entry
    return route


def city_for_state(route, state):
    """Return the city that matters for `state`: the destination city for
    departing, the origin city for arriving - so render.py never has to
    re-derive which end of the route to show. Returns None if `route` is
    None.
    """
    if route is None:
        return None
    if state == runway_config.STATE_DEPARTING:
        return route.get("destination_city")
    if state == runway_config.STATE_ARRIVING:
        return route.get("origin_city")
    return None


def trim_cache(cache, max_entries=CACHE_MAX_ENTRIES):
    """Bound `cache` to at most `max_entries` via simple insertion-order
    eviction (T-02-04-04) - a long-running server's poll_state.json cannot
    grow without limit. Plain dicts preserve insertion order (Python
    3.7+), so the oldest entry is always the current first key.
    """
    while len(cache) > max_entries:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key, None)
