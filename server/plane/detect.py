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

Usage:
    server/.venv/bin/python3 server/plane/detect.py
    server/.venv/bin/python3 server/plane/detect.py --provider airplaneslive --json
"""
import argparse
import json
import os
import sys
import time

import requests

# Identify this project to the rate-limited public services we're calling -
# same self-identification convention adsb-test/query_aggregator.py
# established for Phase 1's spike, updated for the real Phase 2 server.
USER_AGENT = (
    "ink-frame-server/0.1 "
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

DEFAULT_GEOFENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # server/
    "..", "adsb-test", "runway3.json",
)
DEFAULT_GEOFENCE = os.path.normpath(DEFAULT_GEOFENCE)


def load_geofence(path=None):
    with open(path or DEFAULT_GEOFENCE, "r") as f:
        return json.load(f)


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
    booleans.

    Ported unchanged in behaviour from adsb-test/query_aggregator.py
    (T-02-01-01): explicit isinstance() checks on lat/lon, bbox
    containment, the alt_baro string sentinel meaning on-ground, and
    "unknown altitude never claims below ceiling" - malformed records are
    skipped, never raised on.
    """
    bbox = geofence["bbox"]
    ceiling_ft = geofence["alt_ceiling_ft"]
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

        tagged = dict(ac)
        tagged["in_bbox"] = True
        tagged["on_ground"] = on_ground
        tagged["below_ceiling"] = below_ceiling
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

    Known limitation (accepted for v1, inherited from runway3.json's own
    sourcing note): the bbox is not perfectly exclusive of the nearby 06/24
    runway, so an occasional wrong-runway aircraft can win this selection.

    Returns a normalised dict (hex, callsign, altitude_ft, on_ground,
    vertical_rate_fpm, lat, lon, gs, seen_pos) for the winner, or None if
    no candidate is both in-bbox and below-ceiling.
    """
    candidates = [
        ac for ac in filter_in_geofence(aircraft, geofence)
        if ac.get("below_ceiling")
    ]
    if not candidates:
        return None

    def sort_key(ac):
        seen_pos = ac.get("seen_pos")
        seen_pos_key = seen_pos if isinstance(seen_pos, (int, float)) else float("inf")
        return (effective_altitude_ft(ac), seen_pos_key, ac.get("hex") or "")

    winner = min(candidates, key=sort_key)

    callsign = (winner.get("flight") or "").strip() or None
    vertical_rate_fpm = winner.get("baro_rate")
    if vertical_rate_fpm is None:
        vertical_rate_fpm = winner.get("geom_rate")

    return {
        "hex": winner.get("hex"),
        "callsign": callsign,
        "altitude_ft": effective_altitude_ft(winner),
        "on_ground": bool(winner.get("on_ground")),
        "vertical_rate_fpm": vertical_rate_fpm,
        "lat": winner.get("lat"),
        "lon": winner.get("lon"),
        "gs": winner.get("gs"),
        "seen_pos": winner.get("seen_pos"),
    }


def poll_current_aircraft(geofence, timeout=10.0, providers=None):
    """Try each provider in order, sleeping MIN_SECONDS_BETWEEN_CALLS
    between calls, catching (requests.RequestException, ValueError) per
    provider so one aggregator being down never aborts the poll (T-02-01-02).
    Returns the first provider's selection that is not None, else None.
    """
    provider_names = providers if providers is not None else list(PROVIDERS.keys())
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]

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
            return selection
    return None


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
            "%s %s alt=%sft vrate=%s on_ground=%s"
            % (
                selection["hex"],
                selection["callsign"] or "?",
                selection["altitude_ft"],
                selection["vertical_rate_fpm"],
                selection["on_ground"],
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
