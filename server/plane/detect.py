#!/usr/bin/env python3
"""Aggregator-backed detection of the one aircraft using Orly runway 3
right now (D-01, D-P2-01).

Ports adsb-test/query_aggregator.py's discipline verbatim - the same
provider table, geofence filter, and per-provider error isolation - onto
`requests` instead of stdlib urllib (this is the real server, not a
throwaway spike script; requests' timeout/retry ergonomics are worth the
one dependency, per 02-RESEARCH.md's Standard Stack decision). Adds the
D-P2-01 multi-aircraft selection rule, which adsb-test/query_aggregator.py
never needed because Phase 1 only ever reported *all* in-bbox aircraft,
never picked exactly one.

Runway-3 identification (revised 2026-08-27, debug session
.planning/debug/runway3-false-positive.md). Being inside the geofence bbox
is NOT the same as being on runway 3, and treating it as such was a real,
reproduced bug: measured against real published OurAirports LFPO geometry,
that axis-aligned 19.8 km2 bbox contains 71.9% of Orly's runway 06/24 and
80.5% of its runway 02/20, and a 22-poll live capture caught two real
aircraft on those runways being displayed as "runway 3". Selection is now
gated on two geometric tests derived from the runway's own published
threshold coordinates:

  * a runway-aligned CORRIDOR - perpendicular offset from the 07/25
    centreline within `corridor.half_width_m`, along-track position within
    `corridor.extension_m` of either threshold;
  * a TRACK ALIGNMENT check - the record's true track within
    `corridor.axis_tolerance_deg` of 074/254 TRUE.

Both are required because each is blind to the runway the other catches:
06/24 is only 12 deg off runway 3's heading but never within 887m of its
centreline, while 02/20 crosses that centreline outright but sits 56 deg
off its heading. runway3.json's `corridor` block carries the measured
derivation of every threshold.

On-ground pavement gate (added 2026-08-27, debug session
.planning/debug/missed-flights-not-displayed.md). The corridor above was
calibrated entirely on AIRBORNE separation - every measurement behind
half_width_m=500 and extension_m=2500 is an approach or departure track.
Applied to a record that is already on the ground it is physically
meaningless: a +/-500m x 8315m box around a 3315m runway also contains
taxiways, holding points and apron positions, which is the residual
runway3.json's own `corridor.known_residuals` admitted. That mattered
because effective_altitude_ft() scores EVERY on-ground record at exactly
0.0, so one taxiing aircraft inside that box outranked every real
airborne runway-3 movement in select_runway3_aircraft()'s sort - and
since its hex never changed, the rendered panel bytes stayed identical
and the display froze while real traffic passed unseen. An on-ground
record is therefore now required to be on the runway's PAVEMENT: within
`corridor.ground_half_width_m` of the paved rectangle. The sort itself is
deliberately unchanged - an aircraft genuinely on runway 3's pavement
SHOULD outrank one 900ft above it, which is exactly what D-P2-01 says.

Usage:
    server/.venv/bin/python3 server/plane/detect.py
    server/.venv/bin/python3 server/plane/detect.py --provider adsbfi --json
    server/.venv/bin/python3 server/plane/detect.py --provider all --json
"""
import argparse
import json
import math
import os
import re
import sys
import time

import requests

# Identify this project to the rate-limited public services we're calling -
# same self-identification convention adsb-test/query_aggregator.py
# established for Phase 1's spike, updated for the real Phase 2 server.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 2 plane-view production server; "
    "see server/README.md for what this traffic is)"
)

# Each provider's endpoint shape and the JSON key its response array lives
# under.
#
# The Phase 1 decision to use free public ADS-B aggregators at all - over a
# paid schedule API or a local RTL-SDR receiver - still stands (see
# .planning/PROJECT.md Key Decisions). What changed, 2026-08-27: the
# *ordering* half of that decision reversed when airplanes.live withdrew
# free API access, gating it behind running a feeder, a paid sponsorship,
# or a commercial licence. The same day, a live GET against the exact
# production endpoint template below returned HTTP 403 for airplanes.live
# and HTTP 200 for adsb.fi. adsb.fi became the first entry in
# DEFAULT_PROVIDER_ORDER as a result - for the rest of that day this
# project ran with exactly one default provider, meaning no automatic
# fallback and no second selection for the cross-validation this module
# implements (see poll_current_aircraft()) to ever actually corroborate
# against in production. The airplaneslive entry is retained here only for
# explicit `--provider` use - by a feeder operator, sponsor, or licensee -
# and is never queried automatically. See COMPLIANCE.md for the full
# record.
#
# 2026-08-27 (same day, later): adsb.lol added as the second default
# provider, live-verified, CC0-licensed, no API key required today. Its
# aircraft array arrives under the key "ac" - NOT the "aircraft" key
# adsb.fi uses - the one mismatch in this file that fails completely
# silently if ever confused (query_provider()'s `data.get(key) or []`
# just returns an empty list on a wrong key: no exception, no log line, no
# other failing test - see check 28 in server/test_plane_detection.py,
# which proves both keys are read correctly through a stubbed transport
# rather than trusting a dict literal). adsb.lol's own upstream
# documentation pre-announces a possible future feeder-contributed API key
# requirement, which places it in the same volunteer-sustainability risk
# class as the provider that withdrew above - COMPLIANCE.md records this
# as a known-temporary second source, not a permanent guarantee. The point
# of a second default entry: poll_current_aircraft()'s cross-validation -
# built by the runway3-false-positive debug session but never exercised by
# a bare production call until now - actually runs on every production
# poll instead of always taking the single-source branch. Ordering is
# load-bearing, not cosmetic: poll_current_aircraft() returns the FIRST
# queried provider's record when sources agree, so listing adsb.fi first
# means its altitude/track/position values are what reach the renderer on
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

# The only provider(s) an automatic poll queries when no explicit
# `providers` argument is passed. `server/poll_loop.py`'s production call
# to `poll_current_aircraft()` passes no providers argument, so this
# constant is what production actually uses.
DEFAULT_PROVIDER_ORDER = ("adsbfi", "adsblol")

# Both providers document a 1 request/second limit (02-RESEARCH.md Code
# Examples, inherited from 01-RESEARCH.md). Sleeping longer than the strict
# minimum leaves headroom.
MIN_SECONDS_BETWEEN_CALLS = 1.1

# Real ICAO aircraft type designators are short alphanumeric codes (B738,
# A20N, AT76, E145) - never containing whitespace, path separators, or any
# other punctuation. T-03.1-02-01 (ASVS V5): the raw `t` field crosses an
# untrusted trust boundary from the aggregator, so this is the normalization
# boundary - a value that doesn't match this shape is treated the same as a
# genuinely missing designator (None), never passed through as-is.
_VALID_AIRCRAFT_TYPE_RE = re.compile(r"^[A-Z0-9]+$")

DEFAULT_GEOFENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # server/
    "..", "adsb-test", "runway3.json",
)
DEFAULT_GEOFENCE = os.path.normpath(DEFAULT_GEOFENCE)

# Metres per degree of latitude. Longitude degrees are scaled by
# cos(latitude) at the runway's own latitude - over a geofence a few km
# across, this equirectangular approximation is accurate to well under a
# metre, which is three orders of magnitude finer than the 500m corridor
# half-width it feeds (see runway3.json's `corridor.threshold_derivation`).
_M_PER_DEG_LAT = 111320.0

# Fallbacks used only when a geofence file carries no `corridor` block, so
# an older or hand-written geofence still gets the gate rather than
# silently reverting to the bbox-only behaviour this whole module was
# fixed to stop trusting.
DEFAULT_CORRIDOR_HALF_WIDTH_M = 500.0
DEFAULT_CORRIDOR_EXTENSION_M = 2500.0
DEFAULT_AXIS_TOLERANCE_DEG = 30.0
# The on-ground pavement gate's single number. Runway 3's own published
# paved half-width is 22.6m (OurAirports width_ft=148 = 45.1m), the only
# real on-ground runway-3 record in server/fixtures measures 31.1m
# cross-track, and the off-runway ground traffic this excludes starts at
# ~150m - so 75 sits inside an empty measured band. See runway3.json's
# `corridor.ground_gate_derivation` for the full derivation.
DEFAULT_GROUND_HALF_WIDTH_M = 75.0


def load_geofence(path=None):
    with open(path or DEFAULT_GEOFENCE, "r") as f:
        return json.load(f)


def runway_axis(geofence):
    """Derive runway 3's centreline from the two published threshold
    coordinates in geofence['runway'].

    Returns a dict with the origin (threshold 07), the unit vector along
    07 -> 25 in local metres, the centreline length, and the true bearing;
    or None when the geofence carries no usable threshold pair (a custom or
    older geofence file), in which case the corridor/alignment gates are
    skipped and only the bbox applies - see filter_in_geofence().

    The bearing is TRUE, not magnetic: the thresholds come from
    OurAirports' le/he_latitude/longitude columns and the resulting bearing
    (74.41 deg) matches the `le_heading_degT` column, which is what ADS-B's
    own `track` field is measured against. runway3.json's
    `runway.correction_2026_08_27` records why that distinction matters.
    """
    runway = geofence.get("runway")
    if not isinstance(runway, dict):
        return None
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


def corridor_params(geofence):
    """The corridor gate's four numbers, from geofence['corridor'] when
    present, else the module defaults. Non-numeric or non-positive entries
    fall back rather than raising - a malformed config must not be able to
    silently widen the gate to infinity.

    Returns (half_width_m, extension_m, axis_tolerance_deg,
    ground_half_width_m). The first three describe the AIRBORNE corridor;
    the fourth is the on-ground pavement gate, used as both the lateral
    half-width and the along-track margin beyond each threshold (one
    concept - "within X of runway 3's paved rectangle" - rather than two
    tunables).
    """
    block = geofence.get("corridor")
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


def along_cross_track_m(lat, lon, geofence, axis=None):
    """Position relative to runway 3's centreline, in metres.

    Returns (along_m, cross_m): along_m is distance from threshold 07
    measured along the 07 -> 25 direction (negative = short of 07, greater
    than the runway length = beyond 25); cross_m is the perpendicular
    offset, positive to the left of the 07 -> 25 direction (i.e. north of
    the runway). Returns (None, None) when the geofence has no usable
    runway axis.
    """
    axis = axis or runway_axis(geofence)
    if axis is None:
        return (None, None)
    dx = (lon - axis["lon0"]) * axis["lon_scale"]
    dy = (lat - axis["lat0"]) * _M_PER_DEG_LAT
    along = dx * axis["ux"] + dy * axis["uy"]
    cross = -dx * axis["uy"] + dy * axis["ux"]
    return (along, cross)


def track_axis_deviation_deg(track, geofence, axis=None):
    """How far a true track over ground is from runway 3's axis, in
    degrees, 0-90.

    Runway 3 is used in both directions (landing/departing 07 or 25), so a
    track is compared against the centreline bearing AND its reciprocal and
    the smaller deviation wins - an aircraft on final to 25 (track ~254)
    and one rolling out on 07 (track ~074) are both perfectly aligned.

    Returns None when `track` is missing/non-numeric (bools are rejected
    explicitly - Python's bool is an int subclass, so an unguarded True
    would read as a track of 1 degree) or when the geofence has no usable
    runway axis. A None here does NOT mean "misaligned"; see
    filter_in_geofence() for how an unknown track is treated.
    """
    axis = axis or runway_axis(geofence)
    if axis is None:
        return None
    if isinstance(track, bool) or not isinstance(track, (int, float)):
        return None
    forward = abs((track - axis["bearing_deg"] + 180.0) % 360.0 - 180.0)
    reverse = abs((track - axis["bearing_deg"] - 180.0 + 180.0) % 360.0 - 180.0)
    return min(forward, reverse)


def query_provider(name, lat, lon, radius_nm, timeout=10.0):
    """Single unauthenticated GET against one aggregator.

    Raises on any failure (bad host, timeout, non-2xx, malformed JSON) - the
    caller is responsible for catching this per-provider so one aggregator
    being down never aborts a poll against the other (T-02-01-02).
    """
    spec = PROVIDERS[name]
    url = spec["url_template"].format(lat=lat, lon=lon, dist=radius_nm)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    aircraft = data.get(spec["aircraft_key"]) or []
    return aircraft


def filter_in_geofence(aircraft, geofence):
    """Return the subset of `aircraft` whose position falls inside
    geofence['bbox'], each tagged with in_bbox / on_ground / below_ceiling
    booleans plus the runway-3 geometry tags described below.

    Ported unchanged in behaviour from adsb-test/query_aggregator.py
    (T-02-01-01): explicit isinstance() checks on lat/lon, bbox
    containment, the alt_baro string sentinel meaning on-ground, and
    "unknown altitude never claims below ceiling" - malformed records are
    skipped, never raised on.

    Records are still returned on bbox containment alone, so "in bbox"
    counts keep the meaning adsb-test/RESULTS.md recorded for Phase 1.
    What changed (2026-08-27, runway3-false-positive) is that each record
    now also carries:

      along_track_m / cross_track_m  position relative to runway 3's real
                                     centreline (None without a runway axis)
      track_deg / track_deviation_deg  the record's true track and how far
                                     off runway 3's axis it points
      in_corridor                    within the runway-aligned corridor
                                     that applies to THIS record - the wide
                                     approach/departure corridor when
                                     airborne, the tight pavement rectangle
                                     when on_ground (see below)
      track_aligned                  within the axis tolerance, OR carrying
                                     no usable track at all (see below)
      on_runway3                     in_corridor AND track_aligned - the
                                     tag select_runway3_aircraft() filters on

    The bbox alone was never a runway-3 test: measured against real
    published OurAirports LFPO geometry it contains 71.9% of runway 06/24
    and 80.5% of runway 02/20, and a live capture on 2026-08-27 caught two
    real aircraft on those other runways being selected as "runway 3".

    An unknown track (missing, non-numeric, or no runway axis available)
    sets track_aligned True rather than False. This is a deliberate
    asymmetry with below_ceiling's "unknown never claims" rule, for a
    concrete reason: the corridor gate is position-based and every
    candidate already has a position (a record without one is dropped
    above), so an unknown-track record is still fully gated by geometry -
    whereas rejecting it outright would discard genuine runway-3 traffic
    whenever a feed omits the field. Measured 21/21 live adsb.fi records
    carried a numeric track; the pre-existing committed fixtures carry
    none. runway3.json's `corridor.known_residuals` records the exposure.

    ON-GROUND RECORDS GET A TIGHTER CORRIDOR (2026-08-27,
    missed-flights-not-displayed). `half_width_m`/`extension_m` describe
    where an aircraft IN THE AIR on approach to or departure from runway 3
    may legitimately be; every measurement they were derived from is an
    airborne track. A record already on the ground is instead required to
    be on runway 3's own pavement - within `ground_half_width_m` of the
    paved rectangle, laterally AND along-track. Without that, any taxiing
    or holding aircraft within 500m of the centreline scored effective
    altitude 0.0 and masked every real airborne runway-3 movement, freezing
    the panel on an aircraft that was not going anywhere. The pavement
    figure is calibrated against runway 3's published 45.1m width and the
    real on-ground fixture's measured 31.1m offset; see runway3.json's
    `corridor.ground_gate_derivation`.
    """
    bbox = geofence["bbox"]
    ceiling_ft = geofence["alt_ceiling_ft"]
    axis = runway_axis(geofence)
    half_width_m, extension_m, axis_tolerance_deg, ground_half_width_m = corridor_params(geofence)
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
            # An on-ground record is held to runway 3's PAVEMENT, not to
            # the approach/departure corridor: the same figure bounds the
            # lateral offset and the along-track margin beyond each
            # threshold, so the test reads "within ground_half_width_m of
            # the paved rectangle". An aircraft 500m to the side of the
            # runway, or 2.5km past a threshold, is on a taxiway or an
            # apron - not on runway 3 - and admitting it let it mask real
            # runway-3 traffic at effective altitude 0.0.
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
        tagged["on_runway3"] = bool(in_corridor and track_aligned)
        matched.append(tagged)
    return matched


def effective_altitude_ft(ac):
    """0.0 for an on-ground record, the numeric alt_baro otherwise. Used
    only by select_runway3_aircraft's D-P2-01 sort key - an on-ground
    aircraft is, by definition, the lowest possible "altitude" an aircraft
    inside the geofence can have.

    That collapse to a single value is only safe because filter_in_geofence()
    admits an on-ground record ONLY when it is on runway 3's own pavement.
    Before that gate existed, any taxiing or parked aircraft within 500m of
    the centreline also scored 0.0 here and therefore outranked every real
    airborne runway-3 movement - freezing the panel on a stationary aircraft
    while real traffic went unseen (2026-08-27,
    .planning/debug/missed-flights-not-displayed.md). If the ground gate is
    ever widened, this function stops discriminating again.
    """
    if ac.get("on_ground"):
        return 0.0
    alt_baro = ac.get("alt_baro")
    if isinstance(alt_baro, (int, float)):
        return float(alt_baro)
    return 0.0


def select_runway3_aircraft(aircraft, geofence):
    """D-P2-01 (locked, 02-01-PLAN.md): when more than one aircraft is
    inside the runway-3 geofence in the same poll, select by a total
    order:

      1. lowest effective altitude (an on-ground aircraft has effective
         altitude 0 - see effective_altitude_ft);
      2. tie-break on smallest seen_pos (freshest position report);
      3. tie-break on lexicographically smallest hex.

    Rationale: lowest-and-closest-to-the-ground is the aircraft actually
    committed to the runway right now, which is what "the plane using
    runway 3" means to a person looking at the frame; the two tie-breaks
    make the pick independent of the aggregator's own array ordering, so
    the same snapshot always yields the same flight and the display never
    flickers between two simultaneous aircraft.

    Candidates are gated on `on_runway3` (see filter_in_geofence), not on
    bbox containment. That gate replaces the "known limitation (accepted
    for v1)" this docstring used to carry, which understated the problem
    badly: measured against real published OurAirports LFPO geometry the
    bbox contains 71.9% of runway 06/24 AND 80.5% of runway 02/20
    (including runway 02's threshold), and a 22-poll live capture on
    2026-08-27 caught two real aircraft using those other runways winning
    this selection - a runway-20 departure climbing at +2304 ft/min 750m
    off runway 3's centreline (which would also have flipped the panel to
    "departing"), and a 02/20-aligned arrival 611m off it. The sort below
    was never the problem; the absence of any lateral or directional test
    was. See runway3.json's `corridor` block for the gate's thresholds and
    why both a corridor and a track check are needed.

    The same conclusion held a second time, for a different symptom
    (2026-08-27, .planning/debug/missed-flights-not-displayed.md: real
    flights passing without ever being displayed). A taxiing aircraft was
    masking real runway-3 movements because effective_altitude_ft() scores
    every on-ground record at 0.0 and the corridor was wide enough to
    contain non-runway ground traffic. The temptation is to fix that in
    the sort - it would be wrong. An aircraft physically on runway 3's
    pavement genuinely IS the aircraft using runway 3, and demoting it
    below an airborne one would break D-P2-01 for the correct case. The
    defect was again the gate, not the ranking: the corridor was
    calibrated on airborne separation and was being applied to ground
    records. filter_in_geofence() now holds on-ground records to the
    runway's pavement instead. The sort below is unchanged.

    Returns a normalised dict (hex, callsign, aircraft_type, altitude_ft,
    on_ground, vertical_rate_fpm, lat, lon, gs, seen_pos, plus the
    along_track_m / cross_track_m / track_deg / track_deviation_deg
    geometry the gate accepted it on, so a questionable pick is diagnosable
    from the logged selection alone) for the winner, or None if no
    candidate is on runway 3 and below the ceiling. aircraft_type is
    the ICAO type designator as reported by the aggregator (B738, A20N,
    AT76), uppercased, or None when the record carries none, carries an
    empty/whitespace-only value, carries a non-string value, or carries a
    string that isn't shaped like a real ICAO type designator (alphanumeric
    only - see _VALID_AIRCRAFT_TYPE_RE) - a missing designator is an
    ordinary, expected case, not an error.
    """
    candidates = [
        ac for ac in filter_in_geofence(aircraft, geofence)
        if ac.get("below_ceiling") and ac.get("on_runway3")
    ]
    if not candidates:
        return None

    def sort_key(ac):
        seen_pos = ac.get("seen_pos")
        seen_pos_key = seen_pos if isinstance(seen_pos, (int, float)) else float("inf")
        return (effective_altitude_ft(ac), seen_pos_key, ac.get("hex") or "")

    winner = min(candidates, key=sort_key)

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
    }


def poll_current_aircraft(geofence, timeout=10.0, providers=None):
    """Query provider(s) in order - by default just DEFAULT_PROVIDER_ORDER
    (adsb.fi then adsb.lol), not every registered provider - sleeping
    MIN_SECONDS_BETWEEN_CALLS between successive calls in that sequence,
    catching (requests.RequestException, ValueError) per provider so one
    aggregator being down never aborts the poll (T-02-01-02).

    When more than one provider is actually queried (an explicit multi-
    provider `providers` argument, e.g. `--provider both`, or a future
    second entry in DEFAULT_PROVIDER_ORDER), their independent selections
    are cross-validated instead of returning on the first hit - pure
    failover for source *availability* cannot catch a source being
    confidently *wrong* (see the runway3-false-positive debug session:
    the bug there was a bad selection, not a missing one):

      both agree on hex   -> return it, corroborated=True
      only one selected   -> return it, corroborated=None (single source;
                             the other errored or saw nothing on runway 3 -
                             no corroboration was available, which is NOT
                             the same as disagreement)
      they disagree       -> log both and return None

    Returning None on disagreement is deliberately the same outcome as
    "nothing detected", which D-04 already defines as "leave the panel
    alone". Two feeds naming two different aircraft as the one on runway 3
    means at most one of them is right, and a stale-but-real panel beats a
    coin-flip between them.

    Today DEFAULT_PROVIDER_ORDER has two entries - adsb.fi first, then
    adsb.lol (added 2026-08-27 as a second default source, see the
    PROVIDERS comment above and COMPLIANCE.md) - so a default production
    poll now reaches all three outcomes above on every real cycle, not
    only through an explicit `providers` argument or a test double: two
    agreeing feeds return a corroborated selection carrying adsb.fi's own
    record (ordering is load-bearing - see the return-on-agreement branch
    above); one feed unreachable - an adsb.lol outage, a block, or the
    future feeder-contributed API key requirement its own upstream
    documentation pre-announces, or an ordinary adsb.fi hiccup - degrades
    to a single-source, uncorroborated selection rather than blanking the
    display; and the two feeds naming different aircraft returns None
    entirely, a genuinely reachable branch in production for the first
    time (`server/poll_loop.py`'s log line, extended by this same change,
    is what makes that outcome observable rather than silent). The
    cross-validation path remains reachable through an explicit
    multi-provider `providers` argument too (`--provider all` reaches
    every registered provider including the opt-in one, or a test
    double).

    The returned dict carries two extra keys - `sources` (provider names
    that independently selected this aircraft) and `corroborated` - so the
    caller and the logs can tell a two-source agreement from a lone
    unverified reading.
    """
    provider_names = providers if providers is not None else list(DEFAULT_PROVIDER_ORDER)
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]

    selections = []  # [(provider_name, selection)] in provider order
    for i, name in enumerate(provider_names):
        if i > 0:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS)
        try:
            aircraft = query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
        except (requests.RequestException, ValueError) as exc:
            print("detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
            continue
        selection = select_runway3_aircraft(aircraft, geofence)
        if selection is not None:
            selections.append((name, selection))

    if not selections:
        return None

    winner = selections[0][1]
    agreeing = [name for name, sel in selections if sel.get("hex") == winner.get("hex")]

    if len(selections) == 1:
        corroborated = None
    elif len(agreeing) == len(selections):
        corroborated = True
    else:
        print(
            "detect: providers disagree on the runway-3 aircraft (%s) - "
            "treating as doubt, selecting nothing this poll"
            % ", ".join("%s=%s" % (name, sel.get("hex")) for name, sel in selections),
            file=sys.stderr,
        )
        return None

    result = dict(winner)
    result["sources"] = agreeing
    result["corroborated"] = corroborated
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
        default=10.0,
        help="Per-request timeout in seconds (default: 10).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    geofence = load_geofence(args.geofence)
    if args.provider == "default":
        # No explicit providers argument at all, so poll_current_aircraft()
        # reads its own DEFAULT_PROVIDER_ORDER - there is exactly one
        # definition of "the production default order" in this codebase.
        providers = None
    elif args.provider == "all":
        providers = list(PROVIDERS)
    else:
        providers = [args.provider]
    selection = poll_current_aircraft(geofence, timeout=args.timeout, providers=providers)

    if args.as_json:
        print(json.dumps(selection))
    elif selection is None:
        print("no aircraft in the runway-3 geofence")
    else:
        print(
            "%s %s alt=%sft vrate=%s on_ground=%s cross=%sm track=%s dev=%s sources=%s corroborated=%s"
            % (
                selection["hex"],
                selection["callsign"] or "?",
                selection["altitude_ft"],
                selection["vertical_rate_fpm"],
                selection["on_ground"],
                None if selection["cross_track_m"] is None else round(selection["cross_track_m"]),
                selection["track_deg"],
                None if selection["track_deviation_deg"] is None else round(selection["track_deviation_deg"], 1),
                ",".join(selection.get("sources") or []) or "?",
                selection.get("corroborated"),
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
