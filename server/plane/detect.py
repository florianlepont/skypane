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

Usage:
    server/.venv/bin/python3 server/plane/detect.py
    server/.venv/bin/python3 server/plane/detect.py --provider airplaneslive --json
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
# under. Provider order puts airplaneslive first per the Phase 1 decision
# recorded in STATE.md (tighter median update gap - 22.4s vs 36.2s - and
# zero sample errors vs adsbfi's one, over the ~92-minute validation
# window); adsbfi is retained second given the near-total 37/38 hex overlap
# observed in that same window.
PROVIDERS = {
    "airplaneslive": {
        "url_template": "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}",
        "aircraft_key": "ac",
    },
    "adsbfi": {
        "url_template": "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}",
        "aircraft_key": "aircraft",
    },
}

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
    """The corridor gate's three numbers, from geofence['corridor'] when
    present, else the module defaults. Non-numeric or non-positive entries
    fall back rather than raising - a malformed config must not be able to
    silently widen the gate to infinity.
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
    """
    bbox = geofence["bbox"]
    ceiling_ft = geofence["alt_ceiling_ft"]
    axis = runway_axis(geofence)
    half_width_m, extension_m, axis_tolerance_deg = corridor_params(geofence)
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
            in_corridor = (
                -extension_m <= along_m <= axis["length_m"] + extension_m
                and abs(cross_m) <= half_width_m
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
    """Query EVERY provider each poll and cross-validate their selections,
    sleeping MIN_SECONDS_BETWEEN_CALLS between calls and catching
    (requests.RequestException, ValueError) per provider so one aggregator
    being down never aborts the poll (T-02-01-02).

    This used to stop at the first provider that returned a selection -
    pure failover for source *availability*, which cannot catch a source
    being confidently *wrong*. Both aggregators are now polled every cycle
    and their independent selections compared, so a disagreement becomes an
    observable signal rather than something the early return hid:

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

    Note (2026-08-27): api.airplanes.live currently answers 403 to this
    project's User-Agent while adsb.fi answers 200, so in practice the
    single-source branch is the live one today. That is exactly why an
    unreachable provider must not be scored as disagreement.

    The returned dict carries two extra keys - `sources` (provider names
    that independently selected this aircraft) and `corroborated` - so the
    caller and the logs can tell a two-source agreement from a lone
    unverified reading.
    """
    provider_names = providers if providers is not None else list(PROVIDERS.keys())
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
        choices=sorted(PROVIDERS) + ["both"],
        default="both",
        help="Which aggregator(s) to try, in order (default: both, airplaneslive first).",
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
    providers = None if args.provider == "both" else [args.provider]
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
