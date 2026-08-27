#!/usr/bin/env python3
"""adsbdb.com flight-route enrichment client with a persistent,
callsign-keyed hit/miss cache (D-02, D-P2-05), plus a second, independent
airline-identity source (quick task 260827-hyy, 2026-08-27).

adsbdb's callsign->route lookup is all-or-nothing: it requires airline +
origin + destination to all resolve, or the whole result is a miss. For
carriers with per-tail rotating callsigns (Transavia France measured at
2/20 = 10% - see `.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md`),
that threw away the airline identity on ~90% of detections even though it
never depended on adsbdb in the first place: it is carried directly in the
callsign's ICAO 3-letter prefix (`TVF` = Transavia France), stable
standardised reference data. `airline_from_callsign()` resolves that prefix
against a static, in-repo table (D-01); `resolve_route()` (D-05) layers it
above an adsbdb miss as a fourth outcome, `"airline_only"` - the caller
still learns the airline, even when adsbdb has nothing. This adds zero
network calls, zero new dependencies, and zero cache entries of its own -
it is a pure lookup, recomputed from the static table on every call.

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


# --- ICAO callsign-prefix -> airline-name fallback (D-01/D-02/D-05, quick
# task 260827-hyy) ------------------------------------------------------------
#
# Independent of adsbdb (D-04): the callsign's first three letters are a
# standardised ICAO airline designator - stable reference data, not a
# per-flight lookup. Every value below is copied verbatim from the resolved
# `airline_name` column of `.planning/phases/
# 03.1-procedural-per-airline-livery-rendering/03.1-LIVE-RESOLUTION.md`'s
# 24-airline live-resolution table - never retyped from a current public
# brand name, and never a guess (T-hyy-03). Three entries are the exact
# stale-brand-name traps `illustrations.py`'s own module docstring already
# documents: `FPO` resolves to `"Europe Airpost"` (not "ASL Airlines
# France"), `CRL` resolves to `"Corsairfly"` (not "Corsair International"),
# and `CCM` resolves to `"CCM Airlines"` (not "Air Corsica") - copy these
# strings, never retype them from the brand name.
#
# Amelia International and La Compagnie are deliberately absent:
# 03.1-LIVE-RESOLUTION.md marks both `[UNRESOLVED]` (a candidate ICAO code
# for each turned out to belong to a different real airline), mirroring
# `illustrations._ILLUSTRATION_TARGETS`'s own exclusion of the same two
# carriers for the same reason. `test_enrich.py`'s drift guard asserts every
# value here is a member of `illustrations.target_airline_names()` (D-07) -
# renaming or dropping an illustration target without mirroring the change
# here fails that check.
_ICAO_AIRLINE_PREFIXES = {
    "AFR": "Air France",  # callsign AFR56XX
    "CCM": "CCM Airlines",  # callsign CCM21AW
    "VLG": "Vueling Airlines",  # airline endpoint VLG
    "IBE": "Iberia Airlines",  # airline endpoint IBE
    "TAP": "TAP Portugal",  # airline endpoint TAP
    "TVF": "Transavia France",  # callsign TVF16VB
    "EZY": "easyJet",  # callsign EZY63GN (UK AOC)
    # EJU (easyJet Europe, Austrian AOC) is the one entry NOT sourced from
    # 03.1-LIVE-RESOLUTION.md - D-02's deliberate brand-level exception.
    # EJU flies the same brand/livery as EZY, this project vendors exactly
    # one asset for the brand (easyjet.png), and EJU is a confirmed
    # permanent adsbdb miss (illustrations.py's module docstring,
    # 03.1-RESEARCH.md P-03) - it can never contradict a live adsbdb hit.
    "EJU": "easyJet",
    "WZZ": "Wizz Air",  # cited callsign WZZ8025
    "VOE": "Volotea",  # cited callsign VOE8KA
    "ITY": "ITA Airways",  # cited callsign ITY1830
    "AEA": "Air Europa",  # cited callsign AEA075
    "DAH": "Air Algerie",  # airline endpoint DAH
    "FPO": "Europe Airpost",  # callsigns FPO701/FPO458 - stale-brand trap, NOT "ASL Airlines France"
    "RAM": "Royal Air Maroc",  # cited callsign RAM754
    "TAR": "Tunisair",  # airline endpoint TAR
    "PGT": "Pegasus Airlines",  # callsign PGT80PT
    "LOT": "LOT Polish Airlines",  # cited callsign LOT331
    "CLG": "Chalair Aviation",  # airline endpoint CLG
    "TJT": "Twin Jet",  # callsign TJT352A
    "FWI": "Air Caraïbes",  # cited callsign FWI701
    "CRL": "Corsairfly",  # airline endpoint CRL - stale-brand trap, NOT "Corsair International"
    "FBU": "French Bee",  # cited callsign FBU701
}

# Gate applied before any prefix lookup (mirrors classify_aircraft_type()'s
# security property exactly, T-hyy-01): the normalised callsign must be
# alphanumeric-only, at least 4 characters, with its first three characters
# in A-Z. This rejects a bare 3-letter string with no flight suffix, a
# path-separator payload, and anything shorter than a real callsign, before
# `_ICAO_AIRLINE_PREFIXES.get()` is ever called.
_AIRLINE_PREFIX_SHAPE_RE = re.compile(r"^[A-Z]{3}[A-Z0-9]+$")


def airline_from_callsign(callsign):
    """Return the airline name for `callsign`'s ICAO prefix (its first
    three letters), or `None` for anything that does not resolve - an
    unknown prefix, a non-string, an int, an empty string, a bare 3-letter
    string with no flight suffix, or a callsign containing a path separator
    or any other non-alphanumeric character. Never raises (T-hyy-02).

    Mirrors `illustrations.classify_aircraft_type()`'s security property
    exactly (T-hyy-01): the only strings this function can ever return are
    the fixed `_ICAO_AIRLINE_PREFIXES` table values, or `None` - never
    anything derived from its argument, so a hostile callsign can never
    reach `illustrations.py`'s path construction through this seam.

    Pure, no I/O, no network - a lookup against a static, in-repo table
    (D-01), entirely independent of `lookup_route()`'s adsbdb call (D-04).
    """
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    return _ICAO_AIRLINE_PREFIXES.get(normalised[:3])


def airline_only_route(airline_name):
    """Build the D-03 airline-only route dict: `airline_name` set to
    `airline_name`, and the same four `origin_iata`/`origin_city`/
    `destination_iata`/`destination_city` keys `_parse_route()` produces,
    all `None`. This is the sole construction site for that shape - every
    downstream consumer (`city_for_state()`, `render._flight_line1_text()`,
    `render._flight_line2_text()`, `illustrations.select_illustration()`)
    already works unchanged against it, because the shape is identical to a
    real resolved route's.

    Returns `None` for a falsy or non-string `airline_name`.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return None
    return {
        "airline_name": airline_name,
        "origin_iata": None,
        "origin_city": None,
        "destination_iata": None,
        "destination_city": None,
    }


def resolve_route(callsign, cache, transport=None, timeout=DEFAULT_TIMEOUT):
    """D-05's single resolution seam: classify `callsign`'s enrichment
    outcome into one of four sources and return `(route, source)`.

    `source` is one of:
      - `"fresh_hit"`: adsbdb resolved a full route this cycle (no cache
        entry existed for this callsign before the call).
      - `"cache_hit"`: the cache already held a resolved route for this
        callsign - the request was spared entirely.
      - `"airline_only"` (new): adsbdb had no route (a fresh or a cached
        miss), but the callsign's ICAO prefix identified the carrier via
        `airline_from_callsign()` - a route carrying only the airline name,
        the other four fields `None`.
      - `"miss"`: neither adsbdb nor the prefix table resolved anything.

    `was_cached` is computed from the normalised callsign before delegating
    to `lookup_route()` (D-04: unchanged, not loosened), so the fresh/cache
    distinction is exactly the one `poll_loop.py` used to compute inline -
    `"cache_hit"` still means the cache spared a request *and* returned a
    usable route; a cached miss is still not a cache hit. The prefix
    resolution itself is never cached - it is recomputed from the static
    table on every call, since it is cheaper than a dict lookup and adds no
    state of its own. Never raises (T-hyy-02).
    """
    normalised = normalise_callsign(callsign)
    was_cached = normalised is not None and normalised in cache
    route = lookup_route(callsign, cache, transport=transport, timeout=timeout)
    if route is not None:
        return route, ("cache_hit" if was_cached else "fresh_hit")
    airline_name = airline_from_callsign(callsign)
    if airline_name:
        return airline_only_route(airline_name), "airline_only"
    return None, "miss"


def trim_cache(cache, max_entries=CACHE_MAX_ENTRIES):
    """Bound `cache` to at most `max_entries` via simple insertion-order
    eviction (T-02-04-04) - a long-running server's poll_state.json cannot
    grow without limit. Plain dicts preserve insertion order (Python
    3.7+), so the oldest entry is always the current first key.
    """
    while len(cache) > max_entries:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key, None)
