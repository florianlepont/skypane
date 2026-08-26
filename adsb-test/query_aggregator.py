#!/usr/bin/env python3
"""Single-shot geofenced live query against adsb.fi and airplanes.live.

Stdlib-only (urllib.request) - both aggregators are free, unauthenticated,
public REST APIs, so no pip install is needed (see 01-RESEARCH.md's Package
Legitimacy Audit). Answers the question this whole adsb-test/ track exists
for: right now, which aircraft can a public ADS-B aggregator see inside the
Orly runway-3 geofence, and at what altitude?

Usage:
    python3 query_aggregator.py --provider both
    python3 query_aggregator.py --provider adsbfi --json
    python3 query_aggregator.py --geofence path/to/other-geofence.json

See adsb-test/README.md for interpretation guidance and the sampling/
analysis tools built on top of this script.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# Identify this project to the rate-limited public services we're calling,
# per T-01-04-02 in the 01-04-PLAN.md threat register.
USER_AGENT = (
    "skypane-adsb-validation/0.1 "
    "(hobby project, Phase 1 ADS-B-viability spike; "
    "see adsb-test/README.md for what this traffic is)"
)

# Each provider's endpoint shape and the JSON key its response array lives
# under - these two aggregators use a compatible but not identical response
# shape (verified live this session: adsb.fi nests aircraft under "aircraft",
# airplanes.live nests it under "ac").
PROVIDERS = {
    "adsbfi": {
        "url_template": "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}",
        "aircraft_key": "aircraft",
    },
    "airplaneslive": {
        "url_template": "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}",
        "aircraft_key": "ac",
    },
}

# Both providers document a 1 request/second limit (RESEARCH.md Code
# Examples). Sleeping longer than the strict minimum leaves headroom.
MIN_SECONDS_BETWEEN_CALLS = 1.1

DEFAULT_GEOFENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runway3.json")


def load_geofence(path):
    with open(path, "r") as f:
        return json.load(f)


def query_provider(name, lat, lon, radius_nm, timeout):
    """Single unauthenticated GET against one aggregator.

    Raises on any failure (bad host, timeout, non-2xx, malformed JSON) - the
    caller is responsible for catching this per-provider so one aggregator
    being down never aborts a run against the other.
    """
    spec = PROVIDERS[name]
    url = spec["url_template"].format(lat=lat, lon=lon, dist=radius_nm)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    data = json.loads(raw)
    aircraft = data.get(spec["aircraft_key"]) or []
    return aircraft


def filter_in_geofence(aircraft, geofence):
    """Return the subset of `aircraft` whose position falls inside
    geofence['bbox'], each tagged with on_ground / below_ceiling booleans.

    The aggregators report a barometric-altitude field (`alt_baro`) that is
    a number when airborne and a string on-ground sentinel (e.g. "ground")
    when the aircraft is on the ground - handled explicitly here rather than
    assumed to always be numeric, because the on-ground case is exactly what
    this plan exists to detect (Pitfall 3, 01-RESEARCH.md). A missing or
    unexpectedly-typed field is skipped/tagged conservatively rather than
    raising, per T-01-04-01 in the plan's threat register.
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


def format_altitude(ac):
    alt_baro = ac.get("alt_baro")
    if isinstance(alt_baro, str):
        return "ON GROUND (%s)" % alt_baro
    if isinstance(alt_baro, (int, float)):
        return "%sft" % alt_baro
    return "unknown"


def human_line(ac):
    return "  %-8s %-10s alt=%-18s gs=%-6s lat=%.5f lon=%.5f" % (
        ac.get("hex", "?"),
        (ac.get("flight") or "").strip() or "?",
        format_altitude(ac),
        ac.get("gs", "?"),
        ac.get("lat", 0.0),
        ac.get("lon", 0.0),
    )


def run(providers, geofence, timeout, as_json):
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]
    results = {}

    for i, name in enumerate(providers):
        if i > 0:
            # Honour the documented 1 req/sec limit before the next provider call.
            time.sleep(MIN_SECONDS_BETWEEN_CALLS)
        try:
            aircraft = query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            # A provider being unreachable or returning malformed JSON must not
            # abort the run - record it and continue to the next provider.
            results[name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
            continue
        results[name] = {
            "total": len(aircraft),
            "in_bbox": filter_in_geofence(aircraft, geofence),
        }

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for name in providers:
            r = results[name]
            print("=== %s ===" % name)
            if "error" in r:
                print("  ERROR: %s" % r["error"])
                continue
            print("  total aircraft returned: %d" % r["total"])
            print("  in runway-3 bbox: %d" % len(r["in_bbox"]))
            for ac in r["in_bbox"]:
                print(human_line(ac))

    return results


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Query adsb.fi and/or airplanes.live for aircraft inside the runway-3 "
            "geofence right now."
        )
    )
    parser.add_argument(
        "--provider",
        choices=["adsbfi", "airplaneslive", "both"],
        default="both",
        help="Which aggregator(s) to query (default: both).",
    )
    parser.add_argument(
        "--geofence",
        default=DEFAULT_GEOFENCE,
        help="Path to the geofence JSON (default: adsb-test/runway3.json next to this script).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a single JSON object instead of human-readable lines.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Per-request timeout in seconds (default: 15).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    geofence = load_geofence(args.geofence)
    providers = list(PROVIDERS.keys()) if args.provider == "both" else [args.provider]
    run(providers, geofence, args.timeout, args.as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
