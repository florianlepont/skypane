#!/usr/bin/env python3
"""Aggregator-backed detection of the one aircraft using Orly runway 3
right now.

Ports the geofence-query discipline of adsb-test/query_aggregator.py onto
`requests`, and adds multi-aircraft selection: when more than one
in-geofence aircraft is detected, exactly one is picked by a
deterministic total order.

Being inside the geofence bbox is not the same as being on the runway:
the bbox alone contains 71.9% of runway 06/24 and 80.5% of runway 02/20's
geometry too. Selection is gated on two geometric tests derived from the
runway's own published threshold coordinates:

  * a runway-aligned CORRIDOR - perpendicular offset from the centreline
    within `corridor.half_width_m`, along-track position within
    `corridor.extension_m` of either threshold;
  * a TRACK ALIGNMENT check - the record's true track within
    `corridor.axis_tolerance_deg` of the runway's bearing.

Both are required: each geometric test is blind to traffic the other
catches (e.g. runway 06/24 is close in heading but far in position;
02/20 is close in position but far in heading).

An ON-GROUND record is additionally required to be on the runway's own
PAVEMENT (`corridor.ground_half_width_m`), not merely inside the wider
airborne corridor - the corridor above was calibrated entirely on
airborne separation, and a taxiing aircraft scores the same effective
altitude (0.0) as one genuinely on the runway, so an ungated ground
record can mask real runway traffic in the selection sort.

Usage:
    server/.venv/bin/python3 server/plane/detect.py
    server/.venv/bin/python3 server/plane/detect.py --provider adsbfi --json
    server/.venv/bin/python3 server/plane/detect.py --provider all --json
"""
import argparse
import concurrent.futures
import json
import math
import os
import re
import sys
import threading
import time

import requests

# Support both package import and direct script execution (see the module
# docstring's Usage section) - matching enrich.py's own bootstrap.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import http_fetch

# Identify this project to the rate-limited public services being queried.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 2 plane-view production server; "
    "see server/README.md for what this traffic is)"
)

# Each provider's endpoint shape and the JSON key its response array lives
# under.
#
# Free public ADS-B aggregators, not a paid schedule API or a local
# receiver (see PROJECT.md). One provider in this dict (airplaneslive) is
# gated behind a feeder/sponsor/licence requirement and is never queried
# automatically - retained only for explicit `--provider` use.
#
# adsb.lol's aircraft array arrives under the key "ac" - not "aircraft"
# like adsb.fi - the one mismatch in this file that fails silently if
# ever confused (`data.get(key) or []` just returns an empty list on a
# wrong key, no exception). Both providers' own upstream documentation
# treats free access as potentially temporary, so DEFAULT_PROVIDER_ORDER
# carries two independent sources specifically so
# `poll_current_aircraft()`'s cross-validation actually runs on every
# production poll. Ordering is load-bearing, not cosmetic:
# `poll_current_aircraft()` returns the FIRST queried provider's record
# when sources agree, so listing adsb.fi first means its
# altitude/track/position values are what reach the renderer on
# agreement.
PROVIDERS = {
    "adsbfi": {
        "url_template": "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}",
        "aircraft_key": "aircraft",
    },
    "adsblol": {
        "url_template": "https://api.adsb.lol/v2/point/{lat}/{lon}/{dist}",
        "aircraft_key": "ac",
    },
    "airplaneslive": {
        "url_template": "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}",
        "aircraft_key": "ac",
    },
}

# The provider(s) an automatic poll queries when no explicit `providers`
# argument is passed - this is what production actually uses.
DEFAULT_PROVIDER_ORDER = ("adsbfi", "adsblol")

# The minimum spacing between two calls to THE SAME provider - never
# between two different providers, which are queried in parallel (see
# poll_current_aircraft()/_spaced_query()). adsb.fi documents a 1
# request/second limit on its public endpoints and counts 4xx responses
# against it; adsb.lol documents dynamic rate limits rather than a fixed
# number. Sleeping longer than the strict minimum leaves headroom for
# either.
MIN_SECONDS_BETWEEN_CALLS = 1.1

# Real ICAO aircraft type designators are short alphanumeric codes (B738,
# A20N, AT76) - never whitespace, path separators, or other punctuation.
# The raw `t` field crosses an untrusted trust boundary from the
# aggregator; a value that doesn't match this shape is treated the same
# as a missing designator, never passed through as-is.
_VALID_AIRCRAFT_TYPE_RE = re.compile(r"^[A-Z0-9]+$")

DEFAULT_GEOFENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # server/
    "..", "adsb-test", "runway3.json",
)
DEFAULT_GEOFENCE = os.path.normpath(DEFAULT_GEOFENCE)

# Metres per degree of latitude. Longitude degrees are scaled by
# cos(latitude) at the runway's own latitude - accurate to well under a
# metre over a geofence a few km across.
_M_PER_DEG_LAT = 111320.0

# Fallbacks used only when a geofence file carries no `corridor` block, so
# an older or hand-written geofence still gets the gate rather than
# silently reverting to bbox-only behaviour.
DEFAULT_CORRIDOR_HALF_WIDTH_M = 500.0
DEFAULT_CORRIDOR_EXTENSION_M = 2500.0
DEFAULT_AXIS_TOLERANCE_DEG = 30.0
# The on-ground pavement gate's half-width. Runway 3's own published
# paved half-width is 22.6m, the one committed on-ground fixture measures
# 31.1m cross-track, and off-runway ground traffic starts around 150m -
# so 75m sits inside a measured empty band.
DEFAULT_GROUND_HALF_WIDTH_M = 75.0

# The runway id used by every generalised function's default parameter,
# so pre-multi-runway callers (poll_loop.py, the CLI, existing tests) get
# exactly the same behaviour when they pass no runway_id at all.
DEFAULT_RUNWAY_ID = "3"

# query_provider()'s default `timeout=` (bounds connect and each
# individual read, same as the old default's role); PROVIDER_DEADLINE_S
# bounds the call's TOTAL wall-clock time regardless of how many small
# reads it takes; PROVIDER_MAX_BYTES caps the response body a malformed or
# hostile aggregator can make this process buffer. Providers are queried
# in parallel (poll_current_aircraft()), so the per-cycle provider budget
# is now one deadline plus one read timeout total (13s), not two calls
# back to back - which feeds the 90s systemd unit budget (see
# deploy/skypane-poll.service).
PROVIDER_TIMEOUT_S = 5.0
PROVIDER_DEADLINE_S = 8.0
PROVIDER_MAX_BYTES = 4 * 1024 * 1024


def load_geofence(path=None):
    with open(path or DEFAULT_GEOFENCE, "r") as f:
        return json.load(f)


def runway_ids(geofence):
    """The set of runway ids selectable via `--runway` / `runway_id=...`,
    read from the geofence file's own `runways` keys. Never raises: an
    older or hand-written geofence carrying no `runways` key (or an empty
    one) degrades to the single default id, `DEFAULT_RUNWAY_ID`.
    """
    runways = geofence.get("runways")
    if isinstance(runways, dict) and len(runways) > 0:
        return tuple(runways.keys())
    return (DEFAULT_RUNWAY_ID,)


def _effective_runway_id(geofence, runway_id):
    """The runway id `runway_block()` actually resolves `runway_id` to:
    `runway_id` itself when it names a real entry in `geofence["runways"]`,
    else `DEFAULT_RUNWAY_ID`. Shared by `runway_block()` and
    `select_aircraft_for_runway()`, which needs to report which runway a
    selection was actually gated on rather than the (possibly
    unrecognised) id it was asked for.
    """
    runways = geofence.get("runways")
    if isinstance(runways, dict) and isinstance(runways.get(runway_id), dict):
        return runway_id
    return DEFAULT_RUNWAY_ID


def runway_block(geofence, runway_id=DEFAULT_RUNWAY_ID):
    """The `{"runway": ..., "corridor": ...}` block for `runway_id`.

    Returns `geofence["runways"][runway_id]` when the new-shape `runways`
    key is a dict and `runway_id` names one of its entries; otherwise
    falls back to a synthetic block built from the legacy flat
    `runway`/`corridor` keys.

    This fallback is security-relevant: an unrecognised or malformed
    `runway_id` must land on the default runway's geometry, never raise,
    and never widen a gate.
    """
    runways = geofence.get("runways")
    if isinstance(runways, dict) and isinstance(runways.get(runway_id), dict):
        return runways[runway_id]
    return {
        "runway": geofence.get("runway"),
        "corridor": geofence.get("corridor"),
    }


def runway_axis(geofence, runway_id=DEFAULT_RUNWAY_ID):
    """Derive the selected runway's centreline from its two published
    threshold coordinates.

    Returns a dict with the origin, the unit vector between thresholds in
    local metres, the centreline length, and the true bearing; or `None`
    when the resolved runway block carries no usable threshold pair, in
    which case the corridor/alignment gates are skipped and only the bbox
    applies.

    Reads the new two-element `thresholds` array first, falling back to
    the legacy `threshold_07`/`threshold_25` keys. An unrecognised
    `runway_id` resolves, via `runway_block()`, to the default runway's
    geometry rather than `None` or an exception.

    The bearing is TRUE, not magnetic: thresholds come from OurAirports'
    lat/lon columns, matching what ADS-B's own `track` field is measured
    against.
    """
    block = runway_block(geofence, runway_id=runway_id)
    runway = block.get("runway") if isinstance(block, dict) else None
    if not isinstance(runway, dict):
        return None
    thresholds = runway.get("thresholds")
    if isinstance(thresholds, list) and len(thresholds) == 2:
        start, end = thresholds[0], thresholds[1]
    else:
        start = runway.get("threshold_07")
        end = runway.get("threshold_25")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    try:
        lat0, lon0 = float(start["lat"]), float(start["lon"])
        lat1, lon1 = float(end["lat"]), float(end["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    lon_scale = _M_PER_DEG_LAT * math.cos(math.radians((lat0 + lat1) / 2.0))
    dx = (lon1 - lon0) * lon_scale
    dy = (lat1 - lat0) * _M_PER_DEG_LAT
    length_m = math.hypot(dx, dy)
    if length_m <= 0:
        return None
    return {
        "lat0": lat0,
        "lon0": lon0,
        "lon_scale": lon_scale,
        "ux": dx / length_m,
        "uy": dy / length_m,
        "length_m": length_m,
        "bearing_deg": (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0,
    }


def corridor_params(geofence, runway_id=DEFAULT_RUNWAY_ID):
    """The corridor gate's four numbers for the selected runway, from
    `runway_block(geofence, runway_id)['corridor']` when present, else the
    module defaults. Non-numeric or non-positive entries fall back rather
    than raising - a malformed config must not be able to silently widen
    the gate to infinity.

    Returns `(half_width_m, extension_m, axis_tolerance_deg,
    ground_half_width_m)`. The first three describe the AIRBORNE
    corridor; the fourth is the on-ground pavement gate, used as both the
    lateral half-width and the along-track margin beyond each threshold.

    A per-runway `runways` block that omits `ground_half_width_m` falls
    through to the same `DEFAULT_GROUND_HALF_WIDTH_M` the legacy
    top-level block carries, so the pavement gate holds for every runway
    id by default; a per-runway block may override it once that runway's
    own pavement width is measured.
    """
    resolved = runway_block(geofence, runway_id=runway_id)
    block = resolved.get("corridor") if isinstance(resolved, dict) else None
    if not isinstance(block, dict):
        block = {}

    def _positive(key, default):
        value = block.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value) if value > 0 else default

    return (
        _positive("half_width_m", DEFAULT_CORRIDOR_HALF_WIDTH_M),
        _positive("extension_m", DEFAULT_CORRIDOR_EXTENSION_M),
        _positive("axis_tolerance_deg", DEFAULT_AXIS_TOLERANCE_DEG),
        _positive("ground_half_width_m", DEFAULT_GROUND_HALF_WIDTH_M),
    )


def along_cross_track_m(lat, lon, geofence, axis=None, runway_id=DEFAULT_RUNWAY_ID):
    """Position relative to the selected runway's centreline, in metres.

    Returns (along_m, cross_m): along_m is distance from the first
    threshold measured along the first -> second threshold direction
    (negative = short of the first threshold, greater than the runway
    length = beyond the second); cross_m is the perpendicular offset,
    positive to the left of that direction. Returns (None, None) when the
    geofence has no usable runway axis for `runway_id`.
    """
    axis = axis or runway_axis(geofence, runway_id=runway_id)
    if axis is None:
        return (None, None)
    dx = (lon - axis["lon0"]) * axis["lon_scale"]
    dy = (lat - axis["lat0"]) * _M_PER_DEG_LAT
    along = dx * axis["ux"] + dy * axis["uy"]
    cross = -dx * axis["uy"] + dy * axis["ux"]
    return (along, cross)


def track_axis_deviation_deg(track, geofence, axis=None, runway_id=DEFAULT_RUNWAY_ID):
    """How far a true track over ground is from the selected runway's
    axis, in degrees, 0-90.

    Every runway is used in both directions (e.g. a landing on 25 vs. a
    departure on 07), so a track is compared against the centreline
    bearing AND its reciprocal, and the smaller deviation wins.

    Returns `None` when `track` is missing/non-numeric (`bool` rejected
    explicitly, since it is an `int` subclass) or when the geofence has
    no usable runway axis. `None` here does not mean "misaligned" - see
    `filter_in_geofence()`.
    """
    axis = axis or runway_axis(geofence, runway_id=runway_id)
    if axis is None:
        return None
    if isinstance(track, bool) or not isinstance(track, (int, float)):
        return None
    forward = abs((track - axis["bearing_deg"] + 180.0) % 360.0 - 180.0)
    reverse = abs((track - axis["bearing_deg"] - 180.0 + 180.0) % 360.0 - 180.0)
    return min(forward, reverse)


def query_provider(name, lat, lon, radius_nm, timeout=PROVIDER_TIMEOUT_S):
    """Single unauthenticated GET against one aggregator, bounded by both
    `timeout` (connect and each individual read) and `PROVIDER_DEADLINE_S`
    (the call's total wall-clock time), and capped at `PROVIDER_MAX_BYTES`
    of response body.

    Raises on any failure (bad host, timeout, deadline exceeded, oversized
    body, non-2xx, malformed JSON) - the caller is responsible for
    catching this per-provider so one aggregator being down never aborts a
    poll against the other. A non-2xx status raises `requests.HTTPError`
    naming only the provider and status, never the URL (the URL is not
    secret, but there is no reason to echo it into a log line either).

    The response body must be a JSON object, and its aircraft-array field
    (`spec["aircraft_key"]`) must be either absent/null or a list - either
    violation raises `ValueError`, since an aggregator's response shape is
    untrusted input this process must never assume. Individual aircraft
    records that are not JSON objects are dropped here, before
    `filter_in_geofence()` ever sees them.
    """
    spec = PROVIDERS[name]
    url = spec["url_template"].format(lat=lat, lon=lon, dist=radius_nm)
    result = http_fetch.bounded_get(
        url, headers={"User-Agent": USER_AGENT}, timeout=timeout,
        deadline_s=PROVIDER_DEADLINE_S, max_bytes=PROVIDER_MAX_BYTES,
    )
    if not (200 <= result.status_code < 300):
        raise requests.HTTPError("%d from %s" % (result.status_code, name))
    data = json.loads(result.content)
    if not isinstance(data, dict):
        raise ValueError("%s: response body is not a JSON object" % name)
    aircraft = data.get(spec["aircraft_key"])
    if aircraft is None:
        return []
    if not isinstance(aircraft, list):
        raise ValueError("%s: aircraft value is not a list" % name)
    return [ac for ac in aircraft if isinstance(ac, dict)]


def filter_in_geofence(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    """Return the subset of `aircraft` whose position falls inside
    geofence['bbox'], each tagged with in_bbox / on_ground / below_ceiling
    booleans plus the selected-runway geometry tags below. Malformed
    records (non-numeric lat/lon) are skipped, never raised on.

      along_track_m / cross_track_m  position relative to the selected
                                     runway's real centreline (None
                                     without a runway axis)
      track_deg / track_deviation_deg  the record's true track and how far
                                     off the selected runway's axis it
                                     points
      in_corridor                    within the runway-aligned corridor
                                     for THIS record - the wide
                                     approach/departure corridor when
                                     airborne, the tight pavement
                                     rectangle when on_ground
      track_aligned                  within the axis tolerance, OR
                                     carrying no usable track at all
      on_runway                      in_corridor AND track_aligned for
                                     the requested runway_id
      on_runway3                     deprecated alias, equal to on_runway
                                     when runway_id is DEFAULT_RUNWAY_ID,
                                     False otherwise

    The bbox alone is not a runway test - see the module docstring.

    An unknown track (missing, non-numeric, or no runway axis) sets
    track_aligned True rather than False. Deliberate asymmetry with
    below_ceiling's "unknown never claims" rule: the corridor gate is
    position-based and every candidate already has a position, so an
    unknown-track record is still fully gated by geometry, whereas
    rejecting it outright would discard genuine runway traffic whenever a
    feed omits the field.

    The gate is parameterised by `runway_id`: the same corridor +
    track-alignment discipline applies to every runway, but runway 06/24
    and 02/20's corridor thresholds are copied placeholders, not
    independently derived from real captured traffic on either runway -
    see `runway3.json`'s per-runway `threshold_status`.

    ON-GROUND RECORDS GET A TIGHTER CORRIDOR: the airborne corridor
    numbers describe where an aircraft approaching or departing the
    selected runway may legitimately be - every measurement behind them
    is an airborne track. A record already on the ground is instead
    required to be on that runway's own pavement (within
    `ground_half_width_m`, laterally and along-track): otherwise a
    taxiing or holding aircraft near the centreline scores effective
    altitude 0.0 and can outrank real airborne traffic in the selection
    sort. The gate applies per-runway: the pavement rectangle is always
    the one named by `runway_id`.
    """
    bbox = geofence["bbox"]
    ceiling_ft = geofence["alt_ceiling_ft"]
    axis = runway_axis(geofence, runway_id=runway_id)
    half_width_m, extension_m, axis_tolerance_deg, ground_half_width_m = corridor_params(
        geofence, runway_id=runway_id)
    matched = []
    for ac in aircraft:
        lat = ac.get("lat")
        lon = ac.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue  # no position report this update - can't geofence it
        if not (bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lon_min"] <= lon <= bbox["lon_max"]):
            continue

        alt_baro = ac.get("alt_baro")
        on_ground = isinstance(alt_baro, str)
        if on_ground:
            below_ceiling = True  # on the ground is trivially at/below any altitude ceiling
        elif isinstance(alt_baro, (int, float)):
            below_ceiling = alt_baro <= ceiling_ft
        else:
            below_ceiling = False  # unknown/missing altitude - don't claim it's below ceiling

        along_m, cross_m = along_cross_track_m(lat, lon, geofence, axis=axis)
        deviation_deg = track_axis_deviation_deg(ac.get("track"), geofence, axis=axis)
        if axis is None:
            # No usable runway geometry in this geofence file - fall back to
            # bbox-only behaviour rather than rejecting everything.
            in_corridor = True
            track_aligned = True
        else:
            # An on-ground record is held to the runway's PAVEMENT, not
            # the approach/departure corridor - the same figure bounds
            # both the lateral offset and the along-track margin, so the
            # test reads "within ground_half_width_m of the paved
            # rectangle". A record 500m to the side, or 2.5km past a
            # threshold, is on a taxiway or apron, not the runway.
            if on_ground:
                lateral_m, margin_m = ground_half_width_m, ground_half_width_m
            else:
                lateral_m, margin_m = half_width_m, extension_m
            in_corridor = (
                -margin_m <= along_m <= axis["length_m"] + margin_m
                and abs(cross_m) <= lateral_m
            )
            track_aligned = deviation_deg is None or deviation_deg <= axis_tolerance_deg

        tagged = dict(ac)
        tagged["in_bbox"] = True
        tagged["on_ground"] = on_ground
        tagged["below_ceiling"] = below_ceiling
        tagged["along_track_m"] = along_m
        tagged["cross_track_m"] = cross_m
        tagged["track_deg"] = ac.get("track")
        tagged["track_deviation_deg"] = deviation_deg
        tagged["in_corridor"] = in_corridor
        tagged["track_aligned"] = track_aligned
        tagged["on_runway"] = bool(in_corridor and track_aligned)
        tagged["on_runway3"] = tagged["on_runway"] if runway_id == DEFAULT_RUNWAY_ID else False
        matched.append(tagged)
    return matched


def effective_altitude_ft(ac):
    """0.0 for an on-ground record, the numeric alt_baro otherwise. Used
    only by the selection sort key - an on-ground aircraft is, by
    definition, the lowest possible "altitude" an aircraft inside the
    geofence can have.

    Safe only because `filter_in_geofence()` admits an on-ground record
    ONLY when it is on the runway's own pavement - otherwise any taxiing
    or parked aircraft near the centreline would also score 0.0 and
    outrank every real airborne movement.
    """
    if ac.get("on_ground"):
        return 0.0
    alt_baro = ac.get("alt_baro")
    if isinstance(alt_baro, (int, float)):
        return float(alt_baro)
    return 0.0


def selection_sort_key(ac):
    """The total order used to pick exactly one aircraft when several are
    on the runway:

      1. lowest effective altitude (an on-ground aircraft has effective
         altitude 0 - see effective_altitude_ft);
      2. tie-break on lexicographically smallest hex.

    `hex` (the ICAO 24-bit address), not `seen_pos`, is the tie-break:
    `hex` is a property of the aircraft, identical across every feed and
    stable between polls, so the same snapshot always yields the same
    pick. `seen_pos` ("seconds since this feeder last saw a position") is
    a property of the OBSERVER - independent feeder networks measured
    tens of seconds apart on this field - so ranking a shared reality by
    an observer-local value produced different picks from different
    feeds on the same real aircraft, which broke cross-provider
    corroboration.

    Ties are not rare: every on-ground record collapses to 0.0, and
    airborne altitude is quantised in 25ft steps. Trade-off, accepted
    knowingly: dropping `seen_pos` means a stale-but-still-reported
    record can now win a tie against a fresher one; the old behaviour was
    not reliably better, since it was unstable rather than consistently
    fresher, and a proper staleness filter needs more data than is
    currently available to size safely. `seen_pos` is still carried in
    the returned selection for diagnostics - only its role in ordering
    was removed.

    Runway-independent: ranks records already gated to one runway by
    `runway_candidates()`.
    """
    return (effective_altitude_ft(ac), ac.get("hex") or "")


def runway_candidates(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    """Every record in `aircraft` that is on the selected runway and below
    the ceiling - the candidate set `select_aircraft_for_runway()` then
    picks one from.

    Split out as its own function so `poll_current_aircraft()` can
    cross-validate the two providers' whole candidate SETS instead of
    only their final picks - comparing picks alone manufactured
    disagreements, since two independent feeder networks routinely hold
    overlapping-but-unequal sets even when they agree about the aircraft
    that is actually there.

    Gates on `on_runway`, not the deprecated `on_runway3` alias, so the
    candidate set follows the selected runway.
    """
    return [
        ac for ac in filter_in_geofence(aircraft, geofence, runway_id=runway_id)
        if ac.get("below_ceiling") and ac.get("on_runway")
    ]


def runway3_candidates(aircraft, geofence):
    """Back-compat wrapper pinned to the default runway (id "3"), for
    pre-multi-runway callers.
    """
    return runway_candidates(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID)


def _normalise_selection(winner, selected_runway=DEFAULT_RUNWAY_ID):
    """Shape one gated candidate record into the selection dict described
    by `select_aircraft_for_runway()`'s docstring. Shared with
    `poll_current_aircraft()`'s corroborated branch, so there is exactly
    one definition of what a selection looks like.

    `selected_runway` is the runway id the candidate was actually gated
    on, already resolved through `_effective_runway_id()` by the caller -
    so an unrecognised `runway_id` reports the default it really fell
    back to, not the string it was handed.
    """
    callsign = (winner.get("flight") or "").strip() or None
    raw_type = winner.get("t")
    if isinstance(raw_type, str):
        candidate_type = raw_type.strip().upper()
        aircraft_type = candidate_type if _VALID_AIRCRAFT_TYPE_RE.match(candidate_type) else None
    else:
        aircraft_type = None
    vertical_rate_fpm = winner.get("baro_rate")
    if vertical_rate_fpm is None:
        vertical_rate_fpm = winner.get("geom_rate")

    return {
        "hex": winner.get("hex"),
        "callsign": callsign,
        "aircraft_type": aircraft_type,
        "altitude_ft": effective_altitude_ft(winner),
        "on_ground": bool(winner.get("on_ground")),
        "vertical_rate_fpm": vertical_rate_fpm,
        "lat": winner.get("lat"),
        "lon": winner.get("lon"),
        "gs": winner.get("gs"),
        "seen_pos": winner.get("seen_pos"),
        "along_track_m": winner.get("along_track_m"),
        "cross_track_m": winner.get("cross_track_m"),
        "track_deg": winner.get("track_deg"),
        "track_deviation_deg": winner.get("track_deviation_deg"),
        "selected_runway": selected_runway,
    }


def select_aircraft_for_runway(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    """When more than one aircraft is inside the selected runway's
    geofence in the same poll, select exactly one by the total order in
    `selection_sort_key()` - lowest effective altitude, then
    lexicographically smallest hex.

    Rationale: lowest-and-closest-to-the-ground is the aircraft actually
    committed to the runway right now; the hex tie-break makes the pick
    independent of aggregator array ordering, of which aggregator
    answered, and of poll timing - the same snapshot always yields the
    same flight.

    Candidates are gated on `on_runway` (see `filter_in_geofence()`), not
    bbox containment - the bbox alone contains a large fraction of the
    neighbouring runways' geometry too, so bbox-only selection can pick
    an aircraft that is not on this runway at all. The corridor and
    pavement gates fix that at the gate, not in the sort: an aircraft
    physically on the runway's pavement genuinely IS the aircraft using
    it, so demoting it below an airborne one in the sort would be wrong
    - the defect that motivated the pavement gate was a ground record
    being admitted into the wrong (too-wide) corridor, not the ranking
    itself.

    Returns a normalised dict (hex, callsign, aircraft_type, altitude_ft,
    on_ground, vertical_rate_fpm, lat, lon, gs, seen_pos, plus the
    along_track_m / cross_track_m / track_deg / track_deviation_deg
    geometry the gate accepted it on, plus `selected_runway` - the
    runway id actually gated on, resolved via `runway_block()` so an
    unrecognised `runway_id` reports the default it fell back to) for
    the winner, or `None` if no candidate is on the selected runway and
    below the ceiling. `aircraft_type` is the ICAO type designator as
    reported (uppercased), or `None` for anything missing, empty, or not
    shaped like a real designator - an ordinary, expected case, not an
    error.
    """
    effective_runway_id = _effective_runway_id(geofence, runway_id)
    candidates = runway_candidates(aircraft, geofence, runway_id=runway_id)
    if not candidates:
        return None
    return _normalise_selection(
        min(candidates, key=selection_sort_key),
        selected_runway=effective_runway_id,
    )


def select_runway3_aircraft(aircraft, geofence):
    """Back-compat wrapper pinned to the default runway (id "3"), for
    pre-multi-runway callers - `poll_loop.py`, the CLI, and the existing
    checks in `server/test_plane_detection.py`.
    """
    return select_aircraft_for_runway(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID)


def _spaced_query(name, center, radius_nm, timeout, last_call_at, lock, clock, sleep):
    """Wait out `name`'s own `MIN_SECONDS_BETWEEN_CALLS` spacing - measured
    against `last_call_at[name]` alone, never against any other provider's
    entry - then call `query_provider`. Runs inside one
    `ThreadPoolExecutor` worker per provider, so waiting for one provider
    never delays another's own call.

    The read-wait-write around `last_call_at` is split so the actual
    `sleep()` never happens while `lock` is held - otherwise one
    provider's wait would block every other provider's read of its own
    entry, defeating the point of spacing them independently. `clock` and
    `sleep` are the caller's already-resolved `time.time`/`time.sleep` (or
    a test double), never looked up here.
    """
    with lock:
        previous = last_call_at.get(name)
        wait = (previous + MIN_SECONDS_BETWEEN_CALLS - clock()) if previous is not None else 0.0
    if wait > 0:
        sleep(wait)
    with lock:
        last_call_at[name] = clock()
    return query_provider(name, center["lat"], center["lon"], radius_nm, timeout)


def poll_current_aircraft(geofence, timeout=PROVIDER_TIMEOUT_S, providers=None, runway_id=DEFAULT_RUNWAY_ID,
                           diagnostics=None, last_call_at=None, clock=None, sleep=None):
    """Query provider(s) (by default `DEFAULT_PROVIDER_ORDER`) in
    parallel, one `ThreadPoolExecutor` worker per provider, each worker
    spaced against its OWN previous call via `_spaced_query` rather than
    sleeping between different providers - catching
    `(requests.RequestException, ValueError)` per provider so one
    aggregator being down never aborts the poll.

    `last_call_at` is a mutable `{provider_name: epoch_seconds}` map the
    caller may keep across polls (a timer cycle followed by a manual
    "poll now" is the hazard this guards: without it, two back-to-back
    polls could both call the same provider immediately). Passing `None`
    (the default) uses a fresh local dict, so a single poll never sleeps
    for spacing it cannot know about, and never raises. `clock`/`sleep`
    default to `time.time`/`time.sleep`, resolved here rather than as
    default parameter values, so a test (or a future caller) that patches
    `time.sleep` is honoured even though the actual wait happens inside a
    worker thread.

    Futures are submitted and collected in `provider_names` order (never
    `as_completed`), so which provider physically answers first has no
    effect on `queried`/`failed`/`polled`, or on which provider's record
    wins below - only submission order does.

    When more than one provider actually answers, their candidate SETS
    (not their final picks) are cross-validated - comparing final picks
    alone manufactures disagreements, since two independent feeder
    networks routinely hold overlapping-but-unequal sets even when they
    agree about the aircraft that is actually there:

      >=1 aircraft common to every answering source
                          -> select one from that common set, corroborated=True
      only one answered   -> return its pick, corroborated=None (no
                             corroboration was available, not the same as
                             disagreement)
      nothing in common   -> log every source's candidate set, return None

    Returning `None` on disagreement is the same outcome as "nothing
    detected": two feeds naming different aircraft means at most one is
    right, and a stale-but-real panel beats a coin-flip between them.
    The safety property is unchanged from a simpler equal-picks
    comparison - the winner is still drawn only from records every
    answering provider's own set contains - corroboration only got more
    effective (fewer false suppressions from mismatched sets), never
    weaker. What corroboration still cannot catch: both feeds carrying
    the identical bad record - cross-source agreement has never been able
    to detect two sources being wrong in the same way.

    Ordering is load-bearing: on agreement, the winner is drawn from the
    FIRST-queried provider's own records, so its altitude/track/position
    values are what reach the renderer.

    The returned dict carries `sources` (provider names whose candidate
    set contained the winner), `corroborated`, `runway_id` (echoed back),
    and (via `_normalise_selection`) `selected_runway` (what the gate
    actually resolved to).

    `diagnostics`, when a dict is passed, is populated in place with
    `queried`, `failed`, `selected` (providers that contributed a
    candidate set), `disagreement` (bool) and `runway_id` - the sole
    signal that distinguishes "every source is down" from "nothing is on
    the runway right now" (both otherwise return `None`). Passing no
    `diagnostics` argument leaves this function's return value and
    stderr output unchanged.
    """
    provider_names = providers if providers is not None else list(DEFAULT_PROVIDER_ORDER)
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]

    # Resolved here, not as default parameter values, so a caller (or
    # test) that patches time.sleep/time.time AFTER this module loads is
    # still honoured - a default argument would have captured the
    # unpatched function at import time instead.
    resolved_clock = clock or time.time
    resolved_sleep = sleep or time.sleep
    # A caller-supplied map is mutated in place (that persistence across
    # polls is the whole point); no caller means a fresh dict local to
    # this one poll, which can never carry a previous call for any
    # provider, so it never waits and never raises.
    call_times = last_call_at if last_call_at is not None else {}
    call_times_lock = threading.Lock()

    effective_runway_id = _effective_runway_id(geofence, runway_id)
    queried = []
    failed = []
    # [(provider_name, candidate_records)] in provider order, for the
    # providers that both answered AND saw at least one aircraft on the
    # selected runway. A provider that answered but saw nothing there is
    # not a dissenting vote - it simply has nothing to corroborate with.
    polled = []

    # One worker per provider so no provider's own spacing wait ever
    # blocks another provider's call - the fixed inter-provider sleep this
    # replaces used to cost ~90% of a no-network poll cycle. Futures are
    # submitted AND collected in provider_names order (never
    # as_completed()), so which provider physically answers first can
    # never change queried/failed/polled ordering or which provider's
    # record wins on agreement below.
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(provider_names))) as pool:
        futures = [
            pool.submit(
                _spaced_query, name, center, radius_nm, timeout,
                call_times, call_times_lock, resolved_clock, resolved_sleep,
            )
            for name in provider_names
        ]
        for name, future in zip(provider_names, futures):
            queried.append(name)
            try:
                aircraft = future.result()
            except (requests.RequestException, ValueError) as exc:
                print("detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
                failed.append(name)
                continue
            candidates = runway_candidates(aircraft, geofence, runway_id=runway_id)
            if candidates:
                polled.append((name, candidates))

    # Populated before every return below, so an all-providers-failed poll
    # stays distinguishable from a nothing-on-the-runway poll even though
    # both return None.
    if diagnostics is not None:
        diagnostics["queried"] = queried
        diagnostics["failed"] = failed
        diagnostics["selected"] = [name for name, _ in polled]
        diagnostics["disagreement"] = False
        diagnostics["runway_id"] = runway_id

    if not polled:
        return None

    if len(polled) == 1:
        name, candidates = polled[0]
        result = _normalise_selection(
            min(candidates, key=selection_sort_key),
            selected_runway=effective_runway_id,
        )
        result["sources"] = [name]
        result["corroborated"] = None
        result["runway_id"] = runway_id
        return result

    # Two or more sources each saw traffic on the selected runway. `hex` is
    # normalised the same way selection_sort_key() normalises it, so this
    # comparison cannot disagree with the ordering that follows.
    common = set.intersection(*[{ac.get("hex") or "" for ac in c} for _, c in polled])

    if not common:
        if diagnostics is not None:
            diagnostics["disagreement"] = True
        print(
            "detect: providers disagree on the runway-%s aircraft (%s) - no aircraft common to "
            "every source, treating as doubt, selecting nothing this poll"
            % (
                effective_runway_id,
                "; ".join(
                    "%s=[%s]" % (name, ",".join(sorted(ac.get("hex") or "?" for ac in c)))
                    for name, c in polled
                ),
            ),
            file=sys.stderr,
        )
        return None

    # Ordering is load-bearing: the winner is picked from the
    # FIRST-queried provider's own records, so its altitude/track/position
    # values are what reach the renderer.
    first_candidates = polled[0][1]
    corroborated_records = [ac for ac in first_candidates if (ac.get("hex") or "") in common]
    result = _normalise_selection(
        min(corroborated_records, key=selection_sort_key),
        selected_runway=effective_runway_id,
    )
    result["sources"] = [name for name, _ in polled]
    result["corroborated"] = True
    result["runway_id"] = runway_id
    return result


def build_parser():
    parser = argparse.ArgumentParser(
        description="Print the aircraft currently selected as \"using runway 3 right now\" (D-P2-01)."
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS) + ["default", "all"],
        default="default",
        help="Which aggregator(s) to query. Omitting this flag (the "
             "default) queries the production default order - currently "
             "adsb.fi then adsb.lol. Naming a single provider (adsbfi, "
             "adsblol, airplaneslive) restricts the poll to that one "
             "source. 'all' additionally reaches airplaneslive, the "
             "opt-in-only provider - expected to fail for anyone without "
             "feeder, sponsor, or licensee access.",
    )
    parser.add_argument(
        "--geofence",
        default=DEFAULT_GEOFENCE,
        help="Path to the geofence JSON (default: adsb-test/runway3.json).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the selection (or null) as JSON instead of a human-readable line.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=PROVIDER_TIMEOUT_S,
        help="Per-request connect/read timeout in seconds (default: %s). "
             "The total time any one call may take is separately bounded "
             "by PROVIDER_DEADLINE_S (%ss)." % (PROVIDER_TIMEOUT_S, PROVIDER_DEADLINE_S),
    )
    parser.add_argument(
        "--runway",
        default=DEFAULT_RUNWAY_ID,
        help="Which runway id to track (default: %s). `choices` can't be "
             "computed here - the geofence path is itself a flag - so this "
             "accepts a free string and main() validates it against the "
             "loaded geofence's own runway_ids() after parsing, printing "
             "every legal id and exiting non-zero on an unknown one rather "
             "than silently falling back (T-06-02-01 is the library-level "
             "fallback; this CLI-level check exists so a typo is caught "
             "immediately instead of quietly landing on the default "
             "runway)." % DEFAULT_RUNWAY_ID,
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    geofence = load_geofence(args.geofence)

    legal_runway_ids = runway_ids(geofence)
    if args.runway not in legal_runway_ids:
        print(
            "detect: unknown --runway %r - legal ids for this geofence are: %s"
            % (args.runway, ", ".join(sorted(legal_runway_ids))),
            file=sys.stderr,
        )
        return 1

    if args.provider == "default":
        # No explicit providers argument - poll_current_aircraft() reads
        # its own DEFAULT_PROVIDER_ORDER.
        providers = None
    elif args.provider == "all":
        providers = list(PROVIDERS)
    else:
        providers = [args.provider]
    selection = poll_current_aircraft(
        geofence, timeout=args.timeout, providers=providers, runway_id=args.runway)

    if args.as_json:
        print(json.dumps(selection))
    elif selection is None:
        print("no aircraft in the runway-%s geofence" % args.runway)
    else:
        print(
            "%s %s alt=%sft vrate=%s on_ground=%s cross=%sm track=%s dev=%s runway=%s sources=%s corroborated=%s"
            % (
                selection["hex"],
                selection["callsign"] or "?",
                selection["altitude_ft"],
                selection["vertical_rate_fpm"],
                selection["on_ground"],
                None if selection["cross_track_m"] is None else round(selection["cross_track_m"]),
                selection["track_deg"],
                None if selection["track_deviation_deg"] is None else round(selection["track_deviation_deg"], 1),
                selection.get("selected_runway"),
                ",".join(selection.get("sources") or []) or "?",
                selection.get("corroborated"),
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
