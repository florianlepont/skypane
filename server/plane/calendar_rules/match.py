"""Calendar-theme matching: compares a detected, enriched flight against
the loaded registry and the operator's chosen theme.

The pure function `poll_loop.py` calls at both of
`colour_rules.resolve_effective_theme_id()`'s call sites.
"""
from __future__ import annotations

from server import device_config

from .ics import _AIRLINE_IATA_RE, _AIRPORT_IATA_RE
from .registry import _normalise_calendar_entry

# Per-match tolerance in seconds around a calendar entry's DTSTART/DTEND:
# generous enough to absorb ordinary delay, tight enough that same-route
# rotations roughly eight hours apart are never ambiguously close.
CALENDAR_MATCH_TOLERANCE_S = 5400

# This module's own copies of runway_config.py's two confirmed
# render-state strings — duplicated rather than imported, to keep this
# package a leaf.
DEPARTING_STATE = "departing"
ARRIVING_STATE = "arriving"


def _airline_iata_from_route(route):
    """Derive the detected flight's 2-letter IATA airline code from
    `route["callsign_iata"]`'s leading two characters, or `None`.

    No lookup table needed: `callsign_iata`'s prefix already carries the
    IATA code alongside the 3-letter ICAO prefix `enrich.py` keys on — do
    not reintroduce a static ICAO-to-IATA mapping table here.

    Requires a string `callsign_iata`; the candidate must pass
    `_AIRLINE_IATA_RE`. Never raises.
    """
    if not isinstance(route, dict):
        return None
    callsign_iata = route.get("callsign_iata")
    if not isinstance(callsign_iata, str):
        return None
    candidate = callsign_iata.strip().upper()[:2]
    if _AIRLINE_IATA_RE.match(candidate):
        return candidate
    return None


def _far_end_iata(route, render_state):
    """The detected flight's "far end" airport for this direction: the
    destination for a departure, the origin for an arrival. `None` for a
    non-dict `route` or an unrecognised `render_state`.

    Paired with `_entry_far_end_iata()` below so the match is always
    destination-against-destination or origin-against-origin, never
    crossed.
    """
    if not isinstance(route, dict):
        return None
    if render_state == DEPARTING_STATE:
        return route.get("destination_iata")
    if render_state == ARRIVING_STATE:
        return route.get("origin_iata")
    return None


def _entry_far_end_iata(entry, render_state):
    """`_far_end_iata()`'s mirror for a registry entry: `destination_iata`
    for a departure, `origin_iata` for an arrival. `None` otherwise.
    """
    if not isinstance(entry, dict):
        return None
    if render_state == DEPARTING_STATE:
        return entry.get("destination_iata")
    if render_state == ARRIVING_STATE:
        return entry.get("origin_iata")
    return None


def _reference_time(entry, render_state):
    """The moment a calendar entry is measured against for this
    direction: `start_at` for a departure (near off-blocks), `end_at` for
    an arrival (near on-blocks). `None` otherwise.
    """
    if not isinstance(entry, dict):
        return None
    if render_state == DEPARTING_STATE:
        return entry.get("start_at")
    if render_state == ARRIVING_STATE:
        return entry.get("end_at")
    return None


def match_calendar_theme(registry, route, render_state, device_cfg, now):
    """Return the operator's configured calendar theme id when the
    detected, enriched `route` and `render_state` match at least one
    candidate entry in `registry` on airline, far-end airport and time;
    `None` otherwise. Never raises.

    Excludes the raw flight dict and the enrichment-provenance label:
    the match key never depends on the raw callsign — only 11% of Orly's
    dominant carrier's flights carry a commercial-looking IATA number,
    while `origin_iata`/`destination_iata` are populated on every
    enriched detection.

    Resolves the configured theme first (a string member of
    `device_config.THEMES`); requires a recognised `render_state`;
    requires `route` to carry non-empty origin/destination/callsign IATA
    (true only for a fresh or cached detection); derives the detected
    airline and far end; walks the registry, re-validating every entry
    from scratch (the file is operator-inspectable, so a previous
    writer's validation is never trusted); keeps entries matching on
    airline, far-end airport and a time within
    `CALENDAR_MATCH_TOLERANCE_S`; returns the theme when at least one
    candidate survives. A tie breaks deterministically so the result
    never depends on iteration order.

    The whole body is guarded: a malformed registry, route, config or
    clock returns `None` rather than raising — this runs inside the poll
    cycle and must never become a new way for a render to fail.
    """
    try:
        theme_id = device_cfg.get("calendar_theme_id") if isinstance(device_cfg, dict) else None
        if not isinstance(theme_id, str) or theme_id not in device_config.THEMES:
            return None

        if render_state not in (DEPARTING_STATE, ARRIVING_STATE):
            return None

        if not isinstance(route, dict):
            return None
        origin_iata = route.get("origin_iata")
        destination_iata = route.get("destination_iata")
        callsign_iata = route.get("callsign_iata")
        if not isinstance(origin_iata, str) or not origin_iata:
            return None
        if not isinstance(destination_iata, str) or not destination_iata:
            return None
        if not isinstance(callsign_iata, str) or not callsign_iata:
            return None
        if not _AIRPORT_IATA_RE.match(origin_iata) or not _AIRPORT_IATA_RE.match(destination_iata):
            return None

        detected_airline = _airline_iata_from_route(route)
        detected_far_end = _far_end_iata(route, render_state)
        if detected_airline is None or detected_far_end is None:
            return None

        if isinstance(now, bool) or not isinstance(now, (int, float)):
            return None

        raw_entries = registry.get("entries") if isinstance(registry, dict) else None
        if not isinstance(raw_entries, list):
            return None

        best = None  # (abs_diff, reference_time, tie_key) - smallest wins
        for raw_entry in raw_entries:
            normalised = _normalise_calendar_entry(raw_entry)
            if normalised is None:
                continue
            if normalised["airline_iata"] != detected_airline:
                continue
            if _entry_far_end_iata(normalised, render_state) != detected_far_end:
                continue
            reference_time = _reference_time(normalised, render_state)
            if reference_time is None:
                continue
            diff = abs(now - reference_time)
            if diff > CALENDAR_MATCH_TOLERANCE_S:
                continue
            tie_key = (
                normalised["airline_iata"], normalised["origin_iata"],
                normalised["destination_iata"], normalised["start_at"],
                normalised["end_at"],
            )
            candidate = (diff, reference_time, tie_key)
            if best is None or candidate < best:
                best = candidate

        if best is None:
            return None
        return theme_id
    except Exception:
        # Defence in depth - see docstring.
        return None
