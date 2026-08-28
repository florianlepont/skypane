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

# The runway id used by every generalised function's default parameter
# (CFG-12), so the pre-CFG-12 default behaviour - runway 3, the only
# runway this module ever tracked before this change - is exactly what a
# caller gets when it passes no runway_id at all. poll_loop.py, the CLI,
# and every pre-existing check in server/test_plane_detection.py all rely
# on this.
DEFAULT_RUNWAY_ID = "3"


def load_geofence(path=None):
    with open(path or DEFAULT_GEOFENCE, "r") as f:
        return json.load(f)


def runway_ids(geofence):
    """The set of runway ids selectable via `--runway` / `runway_id=...`,
    read from the geofence file's own `runways` keys. Never raises: an
    older or hand-written geofence carrying no `runways` key (or an empty
    one) degrades to the single default id, `DEFAULT_RUNWAY_ID` - exactly
    the one runway that geofence shape has ever supported.
    """
    runways = geofence.get("runways")
    if isinstance(runways, dict) and len(runways) > 0:
        return tuple(runways.keys())
    return (DEFAULT_RUNWAY_ID,)


def _effective_runway_id(geofence, runway_id):
    """The runway id `runway_block()` actually resolves `runway_id` to:
    `runway_id` itself when it names a real entry in `geofence["runways"]`,
    else `DEFAULT_RUNWAY_ID` (the id whose geometry the legacy-fallback
    branch serves). Shared by `runway_block()` and
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
    key is a dict and `runway_id` names one of its entries. Otherwise -
    including an unrecognised `runway_id`, a malformed `runways` value, or
    an older geofence file carrying no `runways` key at all - falls back
    to a synthetic block built from the legacy flat `runway`/`corridor`
    keys.

    This fallback is the security-relevant branch (T-06-02-01, ASVS V5):
    an unrecognised or malformed `runway_id` must land on the default
    runway's geometry, never raise, and never widen a gate - the same
    "malformed config falls back rather than raising" discipline
    `corridor_params()` already applies to a single malformed number,
    extended here to the runway selector itself.
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
    threshold coordinates (see runway_block()).

    Returns a dict with the origin (the first threshold), the unit vector
    from the first threshold to the second in local metres, the centreline
    length, and the true bearing; or None when the resolved runway block
    carries no usable threshold pair (a custom or older geofence file), in
    which case the corridor/alignment gates are skipped and only the bbox
    applies - see filter_in_geofence().

    Reads the new two-element `thresholds` array first, falling back to
    the legacy `threshold_07`/`threshold_25` keys so an old-shape geofence
    (or runway_block()'s legacy-fallback branch) still works - every
    existing guard (non-dict, missing key, non-numeric, zero-length axis
    all return None) is unchanged. An unrecognised `runway_id` resolves,
    via runway_block(), to the default runway's geometry rather than None
    or an exception (T-06-02-01).

    For runway 3 (the default), the bearing is TRUE, not magnetic: the
    thresholds come from OurAirports' le/he_latitude/longitude columns and
    the resulting bearing (74.41 deg) matches the `le_heading_degT` column,
    which is what ADS-B's own `track` field is measured against.
    runway3.json's `runway.correction_2026_08_27` records why that
    distinction matters; the same TRUE-heading convention applies to the
    other runways' `heading_deg_true` fields.
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
    the gate to infinity. An unrecognised `runway_id` resolves to the
    default runway's corridor via runway_block() rather than raising or
    widening anything (T-06-02-01).

    Returns (half_width_m, extension_m, axis_tolerance_deg,
    ground_half_width_m). The first three describe the AIRBORNE corridor;
    the fourth is the on-ground pavement gate, used as both the lateral
    half-width and the along-track margin beyond each threshold (one
    concept - "within X of the selected runway's paved rectangle" - rather
    than two tunables).

    NOTE on the ground gate and per-runway corridor blocks (merge of the
    2026-08-27 pavement fix with CFG-12's runway parameterisation): the
    measured derivation for `ground_half_width_m` lives on the legacy
    top-level `corridor` block, while the per-runway blocks under
    `runways` do not carry the key. That resolves to the SAME 75.0 either
    way - a per-runway block omitting it falls through to
    DEFAULT_GROUND_HALF_WIDTH_M, which is the identical figure - so the
    pavement gate holds for every runway id, and the fallback direction is
    the tight one. A per-runway block MAY override it once that runway's
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

    Every runway here is used in both directions (e.g. runway 3's
    landing/departing 07 or 25), so a track is compared against the
    centreline bearing AND its reciprocal and the smaller deviation wins -
    an aircraft on final to one end (track ~254 for runway 3's 25) and one
    rolling out on the other (track ~074 for runway 3's 07) are both
    perfectly aligned.

    Returns None when `track` is missing/non-numeric (bools are rejected
    explicitly - Python's bool is an int subclass, so an unguarded True
    would read as a track of 1 degree) or when the geofence has no usable
    runway axis for `runway_id`. A None here does NOT mean "misaligned";
    see filter_in_geofence() for how an unknown track is treated.
    """
    axis = axis or runway_axis(geofence, runway_id=runway_id)
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


def filter_in_geofence(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    """Return the subset of `aircraft` whose position falls inside
    geofence['bbox'], each tagged with in_bbox / on_ground / below_ceiling
    booleans plus the selected-runway geometry tags described below.

    Ported unchanged in behaviour from adsb-test/query_aggregator.py
    (T-02-01-01): explicit isinstance() checks on lat/lon, bbox
    containment, the alt_baro string sentinel meaning on-ground, and
    "unknown altitude never claims below ceiling" - malformed records are
    skipped, never raised on.

    Records are still returned on bbox containment alone, so "in bbox"
    counts keep the meaning adsb-test/RESULTS.md recorded for Phase 1.
    What changed (2026-08-27, runway3-false-positive) is that each record
    now also carries:

      along_track_m / cross_track_m  position relative to the selected
                                     runway's real centreline (None
                                     without a runway axis)
      track_deg / track_deviation_deg  the record's true track and how far
                                     off the selected runway's axis it
                                     points
      in_corridor                    within the runway-aligned corridor
                                     that applies to THIS record - the wide
                                     approach/departure corridor when
                                     airborne, the tight pavement rectangle
                                     when on_ground (see below)
      track_aligned                  within the axis tolerance, OR carrying
                                     no usable track at all (see below)
      on_runway                      in_corridor AND track_aligned for the
                                     requested runway_id - the tag
                                     select_aircraft_for_runway() filters on
      on_runway3                     DEPRECATED alias (CFG-12), preserved
                                     because several existing checks read
                                     this exact tag name: equal to
                                     on_runway when runway_id is
                                     DEFAULT_RUNWAY_ID, False otherwise.
                                     Retire once every caller has migrated
                                     to on_runway.

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

    The gate is now parameterised by `runway_id` (CFG-12): the same
    corridor + track-alignment discipline that produced the figures above
    for runway 3 is applied identically to runway 06/24 and runway 02/20,
    but those two runways' corridor thresholds are copied placeholders,
    not independently re-derived from real captured traffic on either
    runway - runway3.json's `runways["06-24"].corridor.threshold_status`
    and `runways["02-20"].corridor.threshold_status` record this
    explicitly, and plan 06-12 is the live-capture pass that confirms or
    replaces them (06-RESEARCH.md Assumption A1).

    ON-GROUND RECORDS GET A TIGHTER CORRIDOR (2026-08-27,
    missed-flights-not-displayed). `half_width_m`/`extension_m` describe
    where an aircraft IN THE AIR on approach to or departure from the
    selected runway may legitimately be; every measurement they were
    derived from is an airborne track. A record already on the ground is
    instead required to be on that runway's own pavement - within
    `ground_half_width_m` of the paved rectangle, laterally AND
    along-track. Without that, any taxiing or holding aircraft within 500m
    of the centreline scored effective altitude 0.0 and masked every real
    airborne runway-3 movement, freezing the panel on an aircraft that was
    not going anywhere. The pavement figure is calibrated against runway
    3's published 45.1m width and the real on-ground fixture's measured
    31.1m offset; see runway3.json's `corridor.ground_gate_derivation`.
    The gate applies per-runway: the pavement rectangle is always the
    rectangle of the runway named by `runway_id`, so selecting 06/24 or
    02/20 gates its ground records on ITS pavement, not runway 3's.
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
        tagged["on_runway"] = bool(in_corridor and track_aligned)
        tagged["on_runway3"] = tagged["on_runway"] if runway_id == DEFAULT_RUNWAY_ID else False
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


def selection_sort_key(ac):
    """The D-P2-01 total order, as one named thing:

      1. lowest effective altitude (an on-ground aircraft has effective
         altitude 0 - see effective_altitude_ft);
      2. tie-break on lexicographically smallest hex.

    WHY `seen_pos` IS NOT IN HERE (removed 2026-08-28, debug session
    .planning/debug/missed-flights-not-displayed.md, mechanism B). This key
    used to be `(effective_altitude_ft, seen_pos, hex)`. `seen_pos` is the
    only value ever placed in it that is a property of the OBSERVER rather
    than the observed: it means "seconds since THIS feeder network last
    received a position report". adsb.fi and adsb.lol are independent
    feeder networks, queried at least MIN_SECONDS_BETWEEN_CALLS apart, and
    adsb-test/RESULTS.md measures their spread on this very field at tens
    of seconds (36.2s median / 56.7s max reconstructed update gap for
    adsb.fi; 22.4s / 69.8s for airplanes.live). Ranking a shared reality by
    an observer-local value cannot produce a shared answer - so whenever
    two records tied on effective altitude, the two feeds ordered the same
    two real aircraft differently, poll_current_aircraft() saw two
    different hexes, and the D-04 disagreement branch threw the whole cycle
    away. The panel froze while real traffic passed, which is exactly the
    symptom that session was opened for.

    `hex` is the ICAO 24-bit address: a property of the AIRCRAFT, identical
    across every feed that sees it, and unchanged between polls. It is
    therefore the only tie-break that actually delivers what this rule's
    own rationale has always claimed - "the same snapshot always yields the
    same flight and the display never flickers between two simultaneous
    aircraft". `seen_pos` structurally could not deliver that, because it
    changes on every poll by definition; it made the pick unstable across
    consecutive polls as well as across providers.

    Ties are not rare enough to ignore. effective_altitude_ft() collapses
    every on-ground record to exactly 0.0 (see runway3.json's
    known_residuals item 3: one aircraft lining up on 07 while another
    rolls out toward 25 are both genuinely on runway 3 and both score 0.0),
    and airborne alt_baro is quantised - every altitude in every committed
    fixture is a multiple of 25ft - so two airborne aircraft sharing a
    reported altitude is ordinary too.

    TRADE-OFF, recorded honestly rather than hidden: dropping seen_pos
    means a genuinely stale record (an aircraft that has already vacated
    the runway but is still being reported) can now win a tie against a
    fresher one. The old behaviour was not reliably better - being
    unstable, it oscillated rather than consistently preferring the fresher
    aircraft - and the correct remedy is a staleness FILTER, which
    RESULTS.md's measured update gaps make unsafe to add without more data:
    any threshold tight enough to catch a vacated aircraft would also drop
    genuine traffic. Tracked as runway3.json known_residuals item (4).
    `seen_pos` is still carried in the returned selection for diagnostics;
    only its role in the ORDERING was removed.

    This key is runway-independent (CFG-12): it ranks records that have
    ALREADY been gated to one runway by runway_candidates(), so which
    runway is being tracked never enters the ordering.
    """
    return (effective_altitude_ft(ac), ac.get("hex") or "")


def runway_candidates(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID):
    """Every record in `aircraft` that is on the selected runway and below
    the ceiling - the candidate set select_aircraft_for_runway() then picks
    one from.

    Split out of select_runway3_aircraft() (2026-08-28, mechanism B of the
    missed-flights-not-displayed debug session) with no behaviour change,
    so poll_current_aircraft() can cross-validate the two providers' whole
    candidate SETS instead of only their final picks. Comparing picks alone
    manufactured disagreements: two independent feeder networks routinely
    hold overlapping-but-unequal sets, so their winners can differ even
    when both agree about the aircraft that is actually there. See
    poll_current_aircraft() for why that mattered.

    Gates on `on_runway` - the real gate result for `runway_id` - rather
    than the deprecated `on_runway3` alias, so the candidate set follows
    the selected runway (CFG-12). For `runway_id=DEFAULT_RUNWAY_ID` the two
    tags are equal by construction, so the default path is unchanged.
    """
    return [
        ac for ac in filter_in_geofence(aircraft, geofence, runway_id=runway_id)
        if ac.get("below_ceiling") and ac.get("on_runway")
    ]


def runway3_candidates(aircraft, geofence):
    """Preserved back-compat wrapper (CFG-12), pinned to the default runway
    (id "3") - the same wrapper discipline select_runway3_aircraft() uses,
    so pre-CFG-12 callers and checks keep working unchanged.
    """
    return runway_candidates(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID)


def _normalise_selection(winner, selected_runway=DEFAULT_RUNWAY_ID):
    """Shape one gated candidate record into the selection dict described
    by select_aircraft_for_runway()'s docstring. Shared by that function and
    by poll_current_aircraft()'s corroborated branch, so there is exactly
    one definition of what a selection looks like.

    `selected_runway` is the runway id the candidate was actually gated on,
    already resolved through _effective_runway_id() by the caller - so an
    unrecognised runway_id reports the default it really fell back to
    rather than the string it was handed (CFG-12).
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
    """D-P2-01 (locked, 02-01-PLAN.md): when more than one aircraft is
    inside the selected runway's geofence in the same poll, select exactly
    one by the total order in selection_sort_key() - lowest effective
    altitude, then lexicographically smallest hex.

    Rationale: lowest-and-closest-to-the-ground is the aircraft actually
    committed to the runway right now, which is what "the plane using this
    runway" means to a person looking at the frame; the hex tie-break makes
    the pick independent of the aggregator's own array ordering, of which
    aggregator is answering, and of when the poll happened - so the same
    snapshot always yields the same flight and the display never flickers
    between two simultaneous aircraft. See selection_sort_key() for why the
    former `seen_pos` tie-break was removed on 2026-08-28.

    Candidates are gated on `on_runway` (see filter_in_geofence), not on
    bbox containment. That gate replaces the "known limitation (accepted
    for v1)" this docstring used to carry, which understated the problem
    badly: measured against real published OurAirports LFPO geometry the
    bbox contains 71.9% of runway 06/24 AND 80.5% of runway 02/20
    (including runway 02's threshold), and a 22-poll live capture on
    2026-08-27 caught two real aircraft using those other runways winning
    this selection (for runway 3, the default) - a runway-20 departure
    climbing at +2304 ft/min 750m off runway 3's centreline (which would
    also have flipped the panel to "departing"), and a 02/20-aligned
    arrival 611m off it. The sort below was never the problem; the absence
    of any lateral or directional test was. See runway3.json's `corridor`
    block for each runway's gate thresholds and why both a corridor and a
    track check are needed.

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

    CFG-12 parameterised the gate by `runway_id` so the same discipline
    applies to runway 06/24 and runway 02/20 as well; see
    filter_in_geofence()'s docstring for the caveat on those two runways'
    corridor thresholds. Both properties compose: the pavement gate is
    applied to whichever runway's rectangle `runway_id` names.

    Returns a normalised dict (hex, callsign, aircraft_type, altitude_ft,
    on_ground, vertical_rate_fpm, lat, lon, gs, seen_pos, plus the
    along_track_m / cross_track_m / track_deg / track_deviation_deg
    geometry the gate accepted it on, plus `selected_runway` - the runway
    id it was actually gated on, resolved through runway_block() so an
    unrecognised `runway_id` reports the default it actually fell back to
    rather than the string it was handed - so a questionable pick is
    diagnosable from the logged selection alone) for the winner, or None
    if no candidate is on the selected runway and below the ceiling.
    aircraft_type is the ICAO type designator as reported by the
    aggregator (B738, A20N, AT76), uppercased, or None when the record
    carries none, carries an empty/whitespace-only value, carries a
    non-string value, or carries a string that isn't shaped like a real
    ICAO type designator (alphanumeric only - see _VALID_AIRCRAFT_TYPE_RE)
    - a missing designator is an ordinary, expected case, not an error.
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
    """Preserved back-compat wrapper (CFG-12): every pre-CFG-12 caller -
    `poll_loop.py`, the CLI, and the existing checks in
    `server/test_plane_detection.py` - keeps working unchanged, pinned to
    the default runway (id "3").
    """
    return select_aircraft_for_runway(aircraft, geofence, runway_id=DEFAULT_RUNWAY_ID)


def poll_current_aircraft(geofence, timeout=10.0, providers=None, runway_id=DEFAULT_RUNWAY_ID, diagnostics=None):
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

      >=1 aircraft common to every answering source
                          -> select one from that common set, corroborated=True
      only one answered   -> return its pick, corroborated=None (single
                             source; the other errored or saw nothing on
                             runway 3 - no corroboration was available,
                             which is NOT the same as disagreement)
      nothing in common   -> log every source's candidate set, return None

    Returning None on disagreement is deliberately the same outcome as
    "nothing detected", which D-04 already defines as "leave the panel
    alone". Two feeds naming two different aircraft as the one on runway 3
    means at most one of them is right, and a stale-but-real panel beats a
    coin-flip between them.

    CORROBORATION IS ON CANDIDATE SETS, NOT ON FINAL PICKS (changed
    2026-08-28, debug session
    .planning/debug/missed-flights-not-displayed.md, mechanism B). This
    function used to compare only each provider's winner. That asked the
    wrong question - "did you pick the same aircraft?" instead of "did you
    SEE the aircraft I picked?" - and it manufactured disagreements out of
    nothing in two distinct ways:

      * via an unstable ranking. The old sort key tie-broke on `seen_pos`,
        a per-provider staleness value, so two feeds ranked the same two
        real aircraft differently and the cycle was suppressed. That half
        is fixed in selection_sort_key(), which no longer reads it.
      * via unequal candidate SETS, which no amount of determinism can
        reconcile. adsb.fi and adsb.lol are independent feeder networks:
        one routinely holds a record the other has not received yet
        (adsb-test/RESULTS.md, ~92 minutes at this geofence: 37 hex seen by
        both, 1 by adsb.fi only - and instantaneously the gap is wider than
        that aggregate, because a 36.2s median position-update gap means a
        newly-appeared aircraft reaches one feed before the other by
        construction). With sets {X, Y} and {Y}, even a perfectly
        deterministic sort picks X and Y - two different hexes, suppressed
        cycle - although both feeds agree Y is real and on runway 3, and
        neither ever asserted X was absent.

    So corroboration is now the INTERSECTION of the answering providers'
    candidate hex sets, and the winner is selected once, deterministically,
    from the first provider's records restricted to that intersection.

    THIS DOES NOT WEAKEN D-04, and the distinction matters. The safety
    property on what reaches the panel is unchanged: before, a corroborated
    display required the winner to be in both providers' sets (that is what
    equal picks implies); now the winner is drawn from the intersection, so
    it is still in every answering provider's set. What narrows is only the
    SUPPRESSION TRIGGER - from "the picks differ" to "no aircraft at all is
    common to every answering source". Genuine doubt still suppresses. And
    a feed carrying a phantom or stale record the other lacks now yields
    the corroborated REAL aircraft instead of a blank panel, because the
    uncorroborated record is excluded from selection rather than merely
    losing a comparison - corroboration became more effective, not less.
    Unanimity is preserved exactly: the intersection is taken across ALL
    answering providers, so a three-source poll where two agree and one
    dissents still suppresses, as it did before.

    What corroboration still cannot catch, unchanged by this: both feeds
    carrying the SAME bad record. A shared phantom or a shared stale
    position is in the intersection and will be displayed as corroborated.
    Cross-source agreement has never been able to detect two sources being
    wrong in the same way (runway3.json known_residuals item 5).

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

    The returned dict carries two extra keys - `sources` (the provider
    names whose own candidate set for this runway contained this aircraft)
    and `corroborated` - so the caller and the logs can tell a two-source
    agreement from a lone unverified reading. It also carries `runway_id`,
    the runway this poll was asked to track, echoed back for the caller's
    own logging, and (via _normalise_selection) `selected_runway`, the
    runway the gate actually resolved to.

    Two new keyword parameters (CFG-12):

    `runway_id` (default DEFAULT_RUNWAY_ID) is threaded into the
    per-provider `select_aircraft_for_runway()` call, so the whole poll -
    query, selection, cross-validation - runs against one consistently
    selected runway.

    `diagnostics`, when a dict is passed, is populated in place with
    `queried` (the provider names actually attempted, in call order),
    `failed` (the subset that raised), `selected` (the subset that
    contributed a runway candidate set, i.e. the subset that would have
    returned a selection), `disagreement` (a bool, set True only on the
    no-common-aircraft branch below) and `runway_id`. This is the sole
    signal that tells "every ADS-B source is down" apart from "nothing is
    on the runway right now" - both return None from this function, an
    ambiguity CFG-05's fault icon needs resolved (T-06-02-03). Passing no
    `diagnostics` argument (the default, and every pre-CFG-12 caller)
    leaves this function's return value and stderr output completely
    unchanged.
    """
    provider_names = providers if providers is not None else list(DEFAULT_PROVIDER_ORDER)
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]

    effective_runway_id = _effective_runway_id(geofence, runway_id)
    queried = []
    failed = []
    # [(provider_name, candidate_records)] in provider order, for the
    # providers that both answered AND saw at least one aircraft on the
    # selected runway. A provider that answered but saw nothing there is
    # not a dissenting vote - it simply has nothing to corroborate with,
    # exactly as it was before this function compared sets rather than
    # picks.
    polled = []
    for i, name in enumerate(provider_names):
        if i > 0:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS)
        queried.append(name)
        try:
            aircraft = query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
        except (requests.RequestException, ValueError) as exc:
            print("detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
            failed.append(name)
            continue
        candidates = runway_candidates(aircraft, geofence, runway_id=runway_id)
        if candidates:
            polled.append((name, candidates))

    # Populated before every return below, so an all-providers-failed poll
    # stays distinguishable from a nothing-on-the-runway poll even though
    # both return None (T-06-02-03).
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
    # comparison cannot disagree with the ordering that follows. (A record
    # carrying no hex at all therefore still compares equal to another
    # record carrying none - pre-existing behaviour, deliberately not
    # changed here; no real aggregator record omits the field.)
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

    # Ordering is load-bearing (see the PROVIDERS comment and
    # ARCHITECTURE.md): the winner is picked from the FIRST-queried
    # provider's own records, so its altitude/track/position values are
    # what reach the renderer, exactly as when this function returned the
    # first provider's selection on agreement.
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
        default=10.0,
        help="Per-request timeout in seconds (default: 10).",
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
        # No explicit providers argument at all, so poll_current_aircraft()
        # reads its own DEFAULT_PROVIDER_ORDER - there is exactly one
        # definition of "the production default order" in this codebase.
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
