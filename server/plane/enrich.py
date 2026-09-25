#!/usr/bin/env python3
"""adsbdb.com flight-route enrichment client with a persistent,
callsign-keyed hit/miss cache, plus an independent airline-identity
fallback sourced from the callsign's own ICAO prefix.

adsbdb's callsign->route lookup is all-or-nothing: airline + origin +
destination must all resolve, or the result is a miss. For carriers with
rotating callsigns that discards the airline identity too, even though it
never depended on adsbdb — the callsign's own ICAO 3-letter prefix (e.g.
`TVF` = Transavia France) is stable reference data.
`airline_from_callsign()` resolves that prefix against a static, in-repo
table; `resolve_route()` layers it above an adsbdb miss as the
`"airline_only"` outcome, and `airline_source_from_callsign()` extends
the same seam to a runtime, operator-writable registry
(`server.plane.manual_resolutions`) as a further `"manual"` outcome —
five sources total (`fresh_hit`/`cache_hit`/`airline_only`/`manual`/
`miss`).

adsbdb resolved roughly half of this airport's real traffic in a live
sample: well for legacy/full-service carriers, poorly for low-cost
carriers using rotating callsigns. The miss path (`None`, never raising)
is a designed first-class state, not a bolted-on error path — every
failure mode degrades to a cached miss, since a lookup problem must never
abort a poll cycle. Both hits and misses are cached and never re-queried;
the cache is a plain JSON-serialisable dict persisted in
`poll_state.json` across the poll oneshot's process boundary.
"""
import os
import re
import sys
from datetime import datetime, timezone

import requests

# Support both package import and direct script execution.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.plane import manual_resolutions, runway_config

ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"

# adsbdb is a free, unauthenticated, crowdsourced service — identify this
# project honestly, matching detect.py's self-identification convention.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 2 plane-view production server; "
    "see server/README.md for what this traffic is)"
)

DEFAULT_TIMEOUT = 10.0

# Bounds poll_state.json's enrichment_cache so a long-running server
# cannot grow the state file without limit.
CACHE_MAX_ENTRIES = 300

# An aggregator-supplied callsign is untrusted input interpolated
# directly into the outbound adsbdb request URL — constrain it to
# alphanumeric-only before that interpolation happens, so a hostile
# callsign field can never inject a path segment or query parameter.
_CALLSIGN_SAFE_RE = re.compile(r"^[A-Z0-9]+$")

# Gate applied before any prefix lookup: the normalised callsign must be
# alphanumeric-only, at least 4 characters, with its first three
# characters in A-Z. Rejects a bare 3-letter string with no flight
# suffix, a path-separator payload, and anything shorter than a real
# callsign, before `_ICAO_AIRLINE_PREFIXES.get()` or
# `_AIRLINE_NAME_CORRECTIONS.get()` is ever called.
_AIRLINE_PREFIX_SHAPE_RE = re.compile(r"^[A-Z]{3}[A-Z0-9]+$")

# adsbdb returns municipality names in title case (e.g. "Palma De
# Mallorca"); the panel's Body role calls for sentence case. These
# interior connective particles are lower-cased unless first word.
_LOWERCASE_CITY_PARTICLES = {"de", "del", "la", "le", "van", "von", "di", "da"}


def normalise_callsign(raw):
    """Strip whitespace and upper-case `raw`; `None` for anything empty
    or non-string. Every cache key and outbound request URL goes through
    this, so equivalent-but-differently-formatted callsigns always
    resolve to the same entry.
    """
    if not isinstance(raw, str):
        return None
    stripped = raw.strip().upper()
    return stripped or None


def _is_url_safe_callsign(normalised):
    return bool(_CALLSIGN_SAFE_RE.match(normalised))


def to_sentence_case_city(raw):
    """Turn an adsbdb-style title-case municipality name (e.g. "Palma De
    Mallorca") into sentence case ("Palma de Mallorca"): capitalise every
    word except interior connective particles, which are lower-cased
    unless they are the first word.
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


def _primary_city_name(raw):
    """Reduce a compound municipality name (e.g. "Toulon/Hyeres/Le
    Palyvestre") to its first, primary segment. OurAirports lists every
    served commune "/"-separated in this field, and no panel text role
    has room for all of them. Names without a "/" pass through
    unchanged.
    """
    return raw.split("/", 1)[0].strip()


def default_transport(callsign, timeout=DEFAULT_TIMEOUT):
    """Thin `requests.get()` wrapper: GET the adsbdb endpoint for
    `callsign` and return `(status_code, parsed_json_or_None)`. A body
    that fails to parse as JSON is `(status_code, None)`, not a raise —
    `lookup_route()` treats it as any other unexpected response.

    The injectable `transport` parameter on `lookup_route()` lets tests
    replace this with a hermetic fake.
    """
    url = ADSBDB_URL.format(callsign=callsign)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    try:
        body = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def _parse_route(body):
    """Defensive `isinstance()` walk of an adsbdb 200 response body.

    Five fields are required — `airline.name`, `origin.iata_code`,
    `origin.municipality`, `destination.iata_code`,
    `destination.municipality` — each a non-empty string, or the whole
    result is a miss: there is no partial-route state to render. One
    field is optional — `callsign_iata` — since a route with a real
    airline and cities but no IATA identifier is still fully displayable;
    requiring it would turn resolvable flights into misses for every
    carrier adsbdb has no IATA callsign for.
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

    callsign_iata_raw = flightroute.get("callsign_iata")
    if isinstance(callsign_iata_raw, str) and callsign_iata_raw.strip():
        callsign_iata = callsign_iata_raw.strip()
    else:
        callsign_iata = None

    return {
        "airline_name": airline_name,
        "origin_iata": origin_iata,
        "origin_city": to_sentence_case_city(_primary_city_name(origin_city_raw)),
        "destination_iata": destination_iata,
        "destination_city": to_sentence_case_city(_primary_city_name(destination_city_raw)),
        "callsign_iata": callsign_iata,
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
        "callsign_iata": entry.get("callsign_iata"),
    }


# --- adsbdb-resolved-name correction seam -----------------------------------
#
# adsbdb's crowdsourced database sometimes resolves a callsign's ICAO
# prefix to a stale name (a pre-rebrand legal name) or, worse, an
# outright wrong one (a different, defunct carrier that once held the
# same ICAO code). This table corrects that at the source, once, rather
# than leaving every caller to work around it.
#
# Keyed on the PAIR (three-letter ICAO callsign prefix, the exact
# airline_name string the upstream API returned) — never on the string
# alone, so an unrelated carrier legitimately named by a corrected-away
# string, under a different prefix, is never rewritten.
_AIRLINE_NAME_CORRECTIONS = {
    # AIA6412 (a real Amelia flight) resolves live via adsbdb to "Avies",
    # a different, defunct Estonian carrier that happened to hold the
    # same ICAO prefix before ceasing operations. Worse than a
    # stale-brand mismatch: an actively wrong carrier attribution.
    ("AIA", "Avies"): "Amelia",
    # Real carriers under their pre-rebrand legal/trading name; adsbdb
    # never updated these after the rebrand.
    ("FPO", "Europe Airpost"): "ASL Airlines France",  # rebranded 2015
    ("CRL", "Corsairfly"): "Corsair",  # reverted to "Corsair" ~2012
    ("CCM", "CCM Airlines"): "Air Corsica",  # rebranded 2013
    # DJT/"Denver Jet" -> "La Compagnie": adsbdb's DJT code attributes to
    # a different, unrelated US operator. Defensive — no confirmed live
    # DJT callsign hit has been observed with this exact string; if one
    # ever does, the correction is already in place.
    ("DJT", "Denver Jet"): "La Compagnie",
}


def correct_airline_name(callsign, airline_name):
    """Return the corrected current name for `airline_name` as resolved
    under `callsign`'s ICAO prefix, or `airline_name` unchanged when no
    correction applies. Gates `callsign` the same way
    `airline_from_callsign()` does, so the only strings this can return
    are a fixed `_AIRLINE_NAME_CORRECTIONS` value or the input
    `airline_name` — never a value derived from the callsign itself.
    Returns any non-string/falsy `airline_name` unchanged. Never raises.
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
    """Return `route` unchanged when `correct_airline_name()` finds
    nothing to correct, otherwise a shallow copy with a corrected
    `airline_name`. Returns any non-dict `route`, or a `route` whose
    `.get()` itself raises, unchanged. Never raises.
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
    """Resolve `callsign` to a normalised route dict, or `None` on any
    miss or failure. Never raises — every failure mode degrades to a
    cached miss rather than aborting the caller's render cycle.

    `cache` is a plain, JSON-serialisable dict (persisted across process
    boundaries via `poll_state.json`'s `enrichment_cache` key) mapping
    the normalised callsign to `{"found": True, <route fields>}` or
    `{"found": False}`. Both hits and misses are cached; a cached
    callsign is never re-queried.

    Both success paths (a fresh 200 and a cached hit) converge on
    `apply_airline_name_correction()` at the end — the one seam every
    adsbdb-sourced route passes through. The cache stores the raw,
    uncorrected upstream payload; correction is applied on read, never on
    write, so an older `poll_state.json` starts producing corrected names
    on its very next poll with zero cache migration.
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
            # Covers the 404 "unknown callsign" miss and every other
            # non-2xx response uniformly.
            cache[normalised] = {"found": False}
            return None

        route = _parse_route(body)
        if route is None:
            cache[normalised] = {"found": False}
            return None

        # The cache holds the raw, uncorrected payload — correction
        # happens on read, in the return statement below.
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


# --- ICAO callsign-prefix -> airline-name fallback --------------------------
#
# Independent of adsbdb: the callsign's first three letters are a
# standardised ICAO airline designator — stable reference data, not a
# per-flight lookup. Values are copied verbatim from live-resolved
# results, never retyped from a current public brand name and never
# guessed.
#
# Three entries (FPO, CRL, CCM) hold the CORRECTED current name rather
# than whatever adsbdb itself still resolves to — `test_enrich.py`
# enforces the invariant that for every `_AIRLINE_NAME_CORRECTIONS` row,
# this table's value for that prefix equals the corrected value, since
# this table is itself the illustration-selection key and cannot mirror
# a string the correction seam would immediately rewrite on the
# adsbdb-hit path.
#
# La Compagnie's real ICAO prefix was for a while absent, after an
# earlier candidate resolved to a different real airline in adsbdb; see
# the DJT row below for how it was eventually confirmed.
_ICAO_AIRLINE_PREFIXES = {
    "AFR": "Air France",
    # Corrected value: adsbdb still resolves this prefix to the
    # pre-rebrand string "CCM Airlines" (see _AIRLINE_NAME_CORRECTIONS'
    # CCM row); this table stores the corrected name directly.
    "CCM": "Air Corsica",
    "VLG": "Vueling Airlines",
    "IBE": "Iberia Airlines",
    "TAP": "TAP Portugal",
    "TVF": "Transavia France",
    "EZY": "easyJet",  # UK AOC
    # EJU (easyJet Europe, Austrian AOC) flies the same brand/livery as
    # EZY; this project vendors one asset for the brand and EJU is a
    # confirmed permanent adsbdb miss, so it can never contradict a live
    # adsbdb hit.
    "EJU": "easyJet",
    "WZZ": "Wizz Air",
    "VOE": "Volotea",
    "ITY": "ITA Airways",
    "AEA": "Air Europa",
    "DAH": "Air Algerie",
    # Corrected value: adsbdb still resolves this prefix to the
    # pre-rebrand "Europe Airpost" (see _AIRLINE_NAME_CORRECTIONS' FPO
    # row); this table stores the corrected name directly.
    "FPO": "ASL Airlines France",
    "RAM": "Royal Air Maroc",
    "TAR": "Tunisair",
    "PGT": "Pegasus Airlines",
    "LOT": "LOT Polish Airlines",
    "CLG": "Chalair Aviation",
    "TJT": "Twin Jet",
    "FWI": "Air Caraïbes",
    # Corrected value: adsbdb still resolves this prefix to the
    # pre-rebrand "Corsairfly" (see _AIRLINE_NAME_CORRECTIONS' CRL row);
    # this table stores the corrected name directly.
    "CRL": "Corsair",
    "FBU": "French Bee",
    # Confirmed permanent adsbdb miss: KM Malta Airlines replaced Air
    # Malta (ceased operations 2024) and adsbdb was never updated.
    "KMM": "KM Malta Airlines",
    # adsbdb resolves this prefix to the pre-2016 legacy brand name
    # "Jetairfly"; this table deliberately keeps the current brand name
    # instead. A flight whose callsign hits adsbdb still renders
    # "Jetairfly" and drops to a lower illustration tier — the
    # airline-only fallback path (this table) renders "TUIfly Belgium".
    "JAF": "TUIfly Belgium",
    # adsbdb's AIA callsign resolves live to "Avies", a different,
    # defunct Estonian carrier that held the same ICAO prefix before
    # ceasing operations in 2016. The real prefix is independently
    # corroborated by Flightradar24, Airhex, Wikipedia, ERAA and IATA.
    # Must equal _AIRLINE_NAME_CORRECTIONS' ("AIA", "Avies") value.
    "AIA": "Amelia",
    # adsbdb resolves this prefix correctly already — no correction row
    # exists or should be added for it.
    "HOP": "Air France Hop",
    # Wizz Air Malta: a separate legal entity/AOC from WZZ (main Wizz
    # Air), mapped to the parent brand name deliberately — same
    # brand-standard livery, visually indistinguishable at this
    # project's flat side-profile illustration fidelity. Wizz Air UK
    # (WUK/W9) is out of scope and must not be added here.
    "WMT": "Wizz Air",
    # KlasJet, confirmed via a real observed flight at Orly.
    "KLJ": "KlasJet",
    # Air Caraïbes Atlantique: the group's long-haul AOC, a separate
    # legal entity from FWI above but the same brand/livery — mapped to
    # the parent brand's existing key, zero new artwork.
    "CAJ": "Air Caraïbes",
    # La Compagnie: adsbdb's airline endpoint for this code resolves to
    # a different, unrelated US operator ("Denver Jet") — see the
    # matching _AIRLINE_NAME_CORRECTIONS row.
    "DJT": "La Compagnie",
    "QAF": "Qatar Amiri Flight",
    # South Korea Government: the ROKAF-operated presidential fleet.
    # Not Kuwait Air Force, despite the shared "KAF" reading.
    "KAF": "South Korea Government",
    "RJA": "Royal Jordanian",
    # French Air Force. The operator's real name is COTAM (Commandement
    # du Transport Aerien Militaire) — named here for greppability; the
    # illustration is filed under the broader "French Air Force" name.
    "CTM": "French Air Force",
    "SRA": "Saudi Royal Aviation",
    "SVA": "Saudia",  # current name; "Saudi Arabian Airlines" is a legacy alias, never stored
    # Defensive alias, not a second ICAO code: the observed callsign read
    # TFV60HA, but the official prefix (above) is TVF — a letter
    # transposition in the observed data is more likely than a real
    # second code. Maps to the same "Transavia France" value.
    "TFV": "Transavia France",
    # Gendarmerie Nationale: the aviation branch of the French national
    # gendarmerie, a state law-enforcement operator, not a commercial
    # airline.
    "FGN": "Gendarmerie Nationale",
    # Iraqi Government: the Iraqi Prime Minister's Office aircraft
    # (observed tail YI-ASF), a state operator, not a commercial
    # airline.
    "IPF": "Iraqi Government",
}


def static_airline_name_for_prefix(prefix):
    """Return the static-table-only airline name for a bare 3-letter ICAO
    `prefix`, or `None`. Deliberately narrower than
    `airline_from_callsign()`: never consults the manual registry, only
    `_ICAO_AIRLINE_PREFIXES`. Its one consumer is the companion's
    supersession check on the Airlines management list, which needs to
    ask "has the built-in table caught up with this prefix yet?" — a
    question `airline_from_callsign()` alone can no longer answer once
    the manual registry is in play.

    Returns `None` for anything that is not exactly three uppercase ASCII
    letters. Never raises.
    """
    if not isinstance(prefix, str) or len(prefix) != 3 or not prefix.isalpha() or prefix != prefix.upper():
        return None
    return _ICAO_AIRLINE_PREFIXES.get(prefix)


def airline_source_from_callsign(callsign):
    """Return `(airline_name, source)` for `callsign`'s ICAO prefix,
    where `source` is `"static"`, `"manual"`, or `None`.

    Gate and lookup order is security-relevant — never reorder:
      1. `normalise_callsign()`; `None` -> `(None, None)`.
      2. `_AIRLINE_PREFIX_SHAPE_RE` fails -> `(None, None)`, before any
         registry read.
      3. `_ICAO_AIRLINE_PREFIXES.get(prefix)` — a hit wins immediately
         and always (a prefix present in both tables can never report
         `"manual"`).
      4. Only on a static miss, `manual_resolutions.airline_name_for_prefix()`.
      5. Otherwise `(None, None)`.

    Never raises: every gate is a type/shape check before either table is
    consulted, and `manual_resolutions.airline_name_for_prefix()` itself
    never raises (it reads a process-scoped dict, never the disk).
    """
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None, None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None, None
    prefix = normalised[:3]
    static_name = _ICAO_AIRLINE_PREFIXES.get(prefix)
    if static_name:
        return static_name, "static"
    manual_name = manual_resolutions.airline_name_for_prefix(prefix)
    if manual_name:
        return manual_name, "manual"
    return None, None


def airline_from_callsign(callsign):
    """Return the airline name for `callsign`'s ICAO prefix, or `None`.
    A thin wrapper: `return airline_source_from_callsign(callsign)[0]`.
    Never raises.

    Returnable values now include operator-supplied names from
    `server.plane.manual_resolutions`'s runtime registry, not only fixed
    `_ICAO_AIRLINE_PREFIXES` values. This stays safe for
    `illustrations.py`'s path construction because
    `manual_resolutions.add_entry()` refuses at write time any name
    whose slug fails a positive allowlist, and
    `load_manual_resolutions()` re-applies that allowlist on every
    read — a hostile or traversal-shaped name can never be stored, let
    alone returned from here.

    Performs no network access and opens no file of its own: it reads a
    process-scoped dict that
    `manual_resolutions.set_manual_registry_state_dir()` populates once
    per poll cycle. A process that never calls that setter sees an empty
    registry here.
    """
    return airline_source_from_callsign(callsign)[0]


def airline_only_route(airline_name):
    """Build the airline-only route dict: `airline_name` as given, and
    the same five `origin_iata`/`origin_city`/`destination_iata`/
    `destination_city`/`callsign_iata` keys `_parse_route()` produces,
    all `None` — every downstream consumer already works unchanged
    against this shape, since it is identical to a real resolved
    route's. Returns `None` for a falsy or non-string `airline_name`.
    """
    if not isinstance(airline_name, str) or not airline_name:
        return None
    return {
        "airline_name": airline_name,
        "origin_iata": None,
        "origin_city": None,
        "destination_iata": None,
        "destination_city": None,
        "callsign_iata": None,
    }


def resolve_route(callsign, cache, transport=None, timeout=DEFAULT_TIMEOUT):
    """Single resolution seam: classify `callsign`'s enrichment outcome
    into one of five sources and return `(route, source)`.

    - `"fresh_hit"`: adsbdb resolved a full route this cycle.
    - `"cache_hit"`: the cache already held a resolved route.
    - `"airline_only"`: adsbdb had no route, but the ICAO prefix
      identified the carrier via the static `_ICAO_AIRLINE_PREFIXES`
      table.
    - `"manual"`: adsbdb and the static table both missed, but the
      prefix identified the carrier via
      `server.plane.manual_resolutions`'s runtime registry.
    - `"miss"`: none of the above resolved anything.

    `"airline_only"` and `"manual"` stay distinct (not folded together)
    because the companion's health page renders the `"airline_only"`
    bucket with a gloss naming the static table specifically — folding a
    manually-resolved prefix in would misrepresent what the static table
    covers. The static table always wins when a prefix is in both (see
    `airline_source_from_callsign()`), so `"manual"` is reported only on
    a genuine static miss.

    `was_cached` is computed from the normalised callsign before
    delegating to `lookup_route()`, matching the fresh/cache distinction
    `poll_loop.py` used to compute inline. The prefix resolution is never
    cached — recomputed from the static and manual tables on every call,
    cheaper than a second cache. Never raises.
    """
    normalised = normalise_callsign(callsign)
    was_cached = normalised is not None and normalised in cache
    route = lookup_route(callsign, cache, transport=transport, timeout=timeout)
    if route is not None:
        return route, ("cache_hit" if was_cached else "fresh_hit")
    airline_name, airline_source = airline_source_from_callsign(callsign)
    if airline_name:
        source = "airline_only" if airline_source == "static" else "manual"
        return airline_only_route(airline_name), source
    return None, "miss"


def trim_cache(cache, max_entries=CACHE_MAX_ENTRIES):
    """Bound `cache` to at most `max_entries` via simple insertion-order
    eviction — a long-running server's poll_state.json cannot grow
    without limit. Plain dicts preserve insertion order (Python 3.7+), so
    the oldest entry is always the current first key.
    """
    while len(cache) > max_entries:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key, None)


# --- Unrecognized-ICAO-prefix recorder --------------------------------------
#
# `resolve_route()`'s `"miss"` outcome means neither adsbdb, the static
# table, nor the manual registry resolved a shape-valid callsign's
# prefix. This section is observability only: it does not change
# `resolve_route()`'s contract or anything the renderer sees.
#
# `count` increments once per poll cycle the prefix is seen, not once
# per distinct flight — an aircraft held on the runway across ten cycles
# reads as ten. This must never be presented as a flight count.
#
# The remediation for a prefix that shows up here is to live-verify it
# against adsbdb and add a row to `_ICAO_AIRLINE_PREFIXES`. Never guess
# an airline name from the three letters alone.

# Bounds the registry's entry count so a spoofed or buggy callsign field
# cannot grow poll_state.json without limit — sized like the 300-entry
# enrichment_cache this file already tolerates.
UNRESOLVED_PREFIX_MAX_ENTRIES = 200

# Bounds the stored example callsign's length. Real ICAO callsigns are at
# most eight characters, but the shape regexes above impose no length
# limit, and ADS-B callsign fields are unauthenticated and spoofable.
UNRESOLVED_EXAMPLE_MAX_LEN = 16


def note_unresolved_prefix(callsign, registry, now=None):
    """Record `callsign`'s 3-letter ICAO prefix in `registry` as an
    unrecognized carrier, or return `None` without recording anything.

    Records only when `callsign` passes `_AIRLINE_PREFIX_SHAPE_RE` AND
    `airline_from_callsign(callsign)` returns `None` — both derived from
    that single call, so this function can never drift from
    `airline_from_callsign()`'s resolve/`None` verdict as either backing
    table grows. `clear_resolved_unresolved_prefix()` (this function's
    structural inverse) is gated on the identical call, so the two can
    never disagree.

    `registry` is a plain, JSON-serialisable dict
    (`poll_state.json`'s `unresolved_prefixes` key) mapping a prefix to
    `{"count", "first_seen", "last_seen", "example_callsign"}`. A first
    sighting sets `count=1` and both timestamps to `now`; a later
    sighting increments `count`, updates `last_seen`/`example_callsign`,
    and leaves `first_seen` untouched.

    `now` defaults to a UTC ISO-8601 string computed inside the
    function, but stays injectable. `example_callsign` is truncated to
    `UNRESOLVED_EXAMPLE_MAX_LEN`. A pre-existing entry that is not a
    well-shaped dict is rebuilt fresh rather than trusted. Never raises.
    """
    if not isinstance(registry, dict):
        return None
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    if airline_from_callsign(callsign) is not None:
        return None

    prefix = normalised[:3]
    if now is None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    example = normalised[:UNRESOLVED_EXAMPLE_MAX_LEN]

    entry = registry.get(prefix)
    if not isinstance(entry, dict) or not isinstance(entry.get("count"), int):
        registry[prefix] = {
            "count": 1,
            "first_seen": now,
            "last_seen": now,
            "example_callsign": example,
        }
    else:
        entry["count"] = entry["count"] + 1
        entry["last_seen"] = now
        entry["example_callsign"] = example

    return prefix


def clear_resolved_unresolved_prefix(callsign, registry):
    """Remove `callsign`'s 3-letter ICAO prefix from `registry` if
    present AND now resolves, returning the removed prefix; otherwise
    `None`, leaving `registry` untouched. Never raises.

    `note_unresolved_prefix()` already stops recording a prefix once it
    resolves, but nothing removed an entry that predates the resolution
    — without this function a resolved prefix would keep showing up in
    the gap report as a phantom, permanently stale entry. Written as that
    function's structural inverse, with the identical gate order, so the
    two can never drift apart.

    The resolution test is `airline_from_callsign()` — a hit in either
    table — deliberately never a `resolve_route()` source value: the
    source describes only this cycle's specific adsbdb outcome (adsbdb
    wins by construction there), not whether the prefix as a whole is now
    resolvable.

    Must run, in the caller (`server/poll_loop.py`'s `run_once()`),
    before `trim_unresolved_prefixes()` and the `unresolved_prefixes`
    write-back, so a newly-resolved prefix is removed the same cycle it
    stops mattering. Calling this twice for the same callsign is safe —
    the second call finds the prefix already absent.
    """
    if not isinstance(registry, dict):
        return None
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    prefix = normalised[:3]
    if prefix not in registry:
        return None
    if airline_from_callsign(callsign) is None:
        return None
    del registry[prefix]
    return prefix


def _unresolved_prefix_sort_key(item):
    """Sort key used by `trim_unresolved_prefixes()` to find the weakest
    (most evictable) entry: lowest `count` first, then oldest `last_seen`,
    then lexicographically smallest prefix. A malformed entry (not a dict,
    or a non-string/missing `last_seen`) sorts as the weakest possible
    candidate rather than raising.
    """
    prefix, entry = item
    if not isinstance(entry, dict):
        return (-1, "", prefix)
    count = entry.get("count")
    if not isinstance(count, int):
        count = -1
    last_seen = entry.get("last_seen")
    if not isinstance(last_seen, str):
        last_seen = ""
    return (count, last_seen, prefix)


def trim_unresolved_prefixes(registry, max_entries=UNRESOLVED_PREFIX_MAX_ENTRIES):
    """Bound `registry` to at most `max_entries` by evicting the weakest
    entry — lowest `count`, then oldest `last_seen`, then
    lexicographically smallest prefix — one at a time.

    Deliberately not insertion-order eviction: the oldest entry here is
    the longest-standing coverage gap, the most valuable row in this
    registry, and a recurring prefix must outrank one-off arrivals.
    Insertion-order eviction would let a burst of spoofed or one-off
    prefixes push out the finding this registry exists to surface.
    Tolerates malformed entries. Does nothing for a non-dict `registry`.
    """
    if not isinstance(registry, dict):
        return
    while len(registry) > max_entries:
        weakest_prefix, _weakest_entry = min(registry.items(), key=_unresolved_prefix_sort_key)
        registry.pop(weakest_prefix, None)
