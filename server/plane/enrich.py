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

# Gate applied before any prefix lookup (mirrors classify_aircraft_type()'s
# security property exactly, T-hyy-01): the normalised callsign must be
# alphanumeric-only, at least 4 characters, with its first three characters
# in A-Z. This rejects a bare 3-letter string with no flight suffix, a
# path-separator payload, and anything shorter than a real callsign, before
# `_ICAO_AIRLINE_PREFIXES.get()` or `_AIRLINE_NAME_CORRECTIONS.get()` is ever
# called. Moved up here (quick task 260827-kih) from beside
# `_ICAO_AIRLINE_PREFIXES` so the correction seam below can be defined ahead
# of its call site (`lookup_route()`) without a forward reference - this is
# a pure move, same pattern, same comment, no behaviour change.
_AIRLINE_PREFIX_SHAPE_RE = re.compile(r"^[A-Z]{3}[A-Z0-9]+$")

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


# --- adsbdb-resolved-name correction seam (quick task 260827-kih) ------------
#
# `adsbdb`'s crowdsourced database sometimes resolves a callsign's ICAO
# prefix to a name that is stale (a real airline's pre-rebrand legal name)
# or, worse, outright wrong (a *different*, defunct carrier that once held
# the same ICAO code). Prior sessions (Phase 3.1, quick task 260827-hyy)
# worked around this by filing illustration/selection keys under whatever
# string adsbdb happened to return - correct for the machinery that existed
# then, but it meant the panel could show a real airline under another
# company's name. This seam fixes that at the source, once, instead of
# leaving every caller to work around it.
#
# QT-kih-D-01: every correction lives in this ONE table, keyed on the PAIR
# `(three-letter ICAO callsign prefix, the exact airline_name string the
# upstream API returned)` - never on the string alone. This is deliberately
# not a global string replace: a hypothetical unrelated carrier legitimately
# named by a corrected-away string, arriving under a different prefix, is
# never rewritten (T-kih-02, proven by test_enrich.py checks 29/35's
# negative case).
_AIRLINE_NAME_CORRECTIONS = {
    # AIA6412 (a real Amelia flight) resolves live via adsbdb to "Avies", a
    # *different*, defunct Estonian carrier (ceased operations 2016) that
    # happened to hold the same ICAO prefix - see the AIA row above for the
    # full live-evidence citation and server/fixtures/adsbdb_hit_AIA6412.json
    # for the recorded response. Worse than a stale-brand mismatch: an
    # actively wrong carrier attribution.
    ("AIA", "Avies"): "Amelia",
}


def correct_airline_name(callsign, airline_name):
    """Return the corrected current name for `airline_name` as resolved
    under `callsign`'s ICAO prefix, or `airline_name` unchanged when no
    correction applies. Gates `callsign` through `normalise_callsign()` and
    `_AIRLINE_PREFIX_SHAPE_RE` before deriving any prefix - exactly like
    `airline_from_callsign()` - so the only strings this function can ever
    return are a fixed `_AIRLINE_NAME_CORRECTIONS` table value or the
    `airline_name` argument it was handed, never a value derived from the
    callsign itself (T-kih-01). Returns any non-string or falsy
    `airline_name` unchanged without ever consulting the table. Never
    raises.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return airline_name
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return airline_name
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return airline_name
    prefix = normalised[:3]
    return _AIRLINE_NAME_CORRECTIONS.get((prefix, airline_name), airline_name)


def apply_airline_name_correction(callsign, route):
    """Return `route` unchanged when `correct_airline_name()` finds nothing
    to correct, otherwise a shallow copy of `route` with a corrected
    `airline_name`. Returns any non-dict `route` unchanged, and returns
    `route` unchanged (rather than raising) if `route.get()` itself raises
    - mirroring `illustrations.select_illustration()`'s same defensive
    shape. Never raises.
    """
    if not isinstance(route, dict):
        return route
    try:
        airline_name = route.get("airline_name")
    except Exception:
        return route
    corrected = correct_airline_name(callsign, airline_name)
    if corrected == airline_name:
        return route
    corrected_route = dict(route)
    corrected_route["airline_name"] = corrected
    return corrected_route


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

    QT-kih-D-01/D-02/D-03: both success paths (a fresh 200 and a cached
    hit) converge on the single `apply_airline_name_correction()` call at
    the end of this function - the one seam every adsbdb-sourced route
    leaves through, fresh or cached. The cache deliberately stores the raw,
    uncorrected upstream payload (the correction is applied on read, never
    on write): a server whose `poll_state.json` predates this correction
    seam starts producing corrected names on its very next poll, with zero
    cache migration or purge, and the cache remains a faithful record of
    what adsbdb actually returned. The prefix-only fallback path
    (`airline_from_callsign()` below) needs no call into this seam at all,
    because `_ICAO_AIRLINE_PREFIXES` already holds corrected values by
    construction - an agreement `test_enrich.py`'s check 32 asserts as a
    machine-checked invariant across both tables, rather than assumes.
    """
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _is_url_safe_callsign(normalised):
        return None

    entry, present = _cache_get(cache, normalised)
    if present:
        if not entry.get("found"):
            return None
        route = _route_from_entry(entry)
    else:
        fetch = transport or default_transport
        try:
            status_code, body = fetch(normalised, timeout)
        except Exception:
            cache[normalised] = {"found": False}
            return None

        if not (200 <= status_code < 300):
            # Covers the 404 "unknown callsign" definitive-miss case and
            # every other non-2xx response uniformly.
            cache[normalised] = {"found": False}
            return None

        route = _parse_route(body)
        if route is None:
            cache[normalised] = {"found": False}
            return None

        # The cache holds the raw, uncorrected payload (QT-kih-D-02) -
        # correction happens on read, in the return statement below.
        cache_entry = dict(route)
        cache_entry["found"] = True
        cache[normalised] = cache_entry

    return apply_airline_name_correction(normalised, route)


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
    # KMM (KM Malta Airlines) and JAF (TUIfly Belgium) added by quick task
    # 260827-jz6 (2026-08-27). Neither is sourced from
    # 03.1-LIVE-RESOLUTION.md - both are new carriers this session verified
    # live, directly against adsbdb, rather than retyped from a candidate
    # ICAO code or a training-knowledge guess.
    #
    # KMM: this session ran `curl https://api.adsbdb.com/v0/callsign/
    # KMM466` (2026-08-27) and got back "unknown callsign" - a confirmed
    # permanent miss. KM Malta Airlines replaced Air Malta (ICAO AMC, ceased
    # operations March 2024) and adsbdb was never updated for the 2023
    # rebrand. Exactly like EJU above, this value can never be contradicted
    # by a live adsbdb hit, because adsbdb has nothing to say about this
    # carrier at all.
    "KMM": "KM Malta Airlines",
    # JAF: this session ran `curl https://api.adsbdb.com/v0/callsign/
    # JAF7521` (2026-08-27) and it DOES resolve, returning the pre-2016
    # legacy brand name "Jetairfly". QT-jz6-D-02: the developer chose the
    # current brand name "TUIfly Belgium" anyway, deliberately - a named
    # exception to the FPO/CRL/CCM stale-brand-mirroring precedent directly
    # above, not an oversight. Accepted consequence: a real TUIfly Belgium
    # flight whose callsign hits adsbdb renders "Jetairfly" and drops to a
    # lower illustration tier, while the airline-only fallback path (this
    # table) renders "TUIfly Belgium" and reaches its own dedicated art.
    "JAF": "TUIfly Belgium",
    # AIA (Amelia) added by quick task 260827-kih (2026-08-27) - a worse
    # failure mode than every entry above. This is not a stale label for
    # the same real airline (like KMM/JAF); adsbdb's AIA callsign resolves
    # live to "Avies", a *different, defunct* Estonian carrier (ICAO AIA,
    # IATA U3, ceased operations 2016) that happened to hold the same ICAO
    # prefix before ceasing, and whose code was never retired upstream.
    # Live-verified this session: `curl https://api.adsbdb.com/v0/
    # callsign/AIA6412` (2026-08-27) returns a populated result -
    # airline.name "Avies", airline.country "Estonia" - recorded verbatim
    # in server/fixtures/adsbdb_hit_AIA6412.json. The real ICAO prefix
    # AIA/Amelia is independently corroborated by Flightradar24
    # (live-tracked flight 8R6412 as callsign 8R/AIA), Airhex, Wikipedia,
    # ERAA and IATA. This value is also the corrected value
    # `_AIRLINE_NAME_CORRECTIONS` maps ("AIA", "Avies") to below - the two
    # tables agree by construction, an agreement `test_enrich.py`'s check
    # 32 asserts as a machine-checked invariant rather than assumes.
    "AIA": "Amelia",
}


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
