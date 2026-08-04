#!/usr/bin/env python3
"""Unattended windowed sampler over query_aggregator's providers.

Repeatedly queries both aggregators over a real time window and writes one
JSON Lines record per sample per provider, so analyze_samples.py can turn a
window of real traffic into the viability metrics the D-02 decision is made
on (see 01-CONTEXT.md D-01 through D-04).

Stdlib-only. Imports query_provider() and filter_in_geofence() from
query_aggregator.py rather than reimplementing them, so the sampled geofence
is provably the same one the single-shot tool reports against.

Usage:
    python3 sample_window.py --minutes 90 --interval 30
    python3 sample_window.py --minutes 3 --interval 30 --out /tmp/smoke   # quick smoke test
"""

import argparse
import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timezone

import query_aggregator as qa

DEFAULT_OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def reduce_aircraft(ac):
    """Trim a filter_in_geofence()-tagged aircraft record down to the fields
    a JSONL sample record needs: hex, callsign, altitude (numeric or the
    on-ground sentinel), ground speed, position, vertical rate when the
    provider reports one, and `seen_pos` - seconds since the underlying
    feed actually received a position report for this aircraft, as of this
    sample's timestamp.

    `seen_pos` is what analyze_samples.py uses to measure real position-
    update frequency (message arrival gaps), independent of how often this
    sampler itself polls - both aggregators report it directly (verified
    live against adsb.fi and airplanes.live this session), so no gap
    analysis is limited to this script's own --interval.
    """
    record = {
        "hex": ac.get("hex"),
        "callsign": (ac.get("flight") or "").strip() or None,
        "altitude": ac.get("alt_baro"),
        "gs": ac.get("gs"),
        "lat": ac.get("lat"),
        "lon": ac.get("lon"),
        "on_ground": ac.get("on_ground"),
        "below_ceiling": ac.get("below_ceiling"),
        "seen_pos": ac.get("seen_pos"),
    }
    vertical_rate = ac.get("baro_rate")
    if vertical_rate is None:
        vertical_rate = ac.get("geom_rate")
    if vertical_rate is not None:
        record["vertical_rate"] = vertical_rate
    return record


def sample_provider(name, geofence, timeout):
    """One sample of one provider. Never raises - a transient provider
    failure must not kill a 90-minute unattended run; it's recorded as an
    error record and the loop continues.
    """
    timestamp = utcnow_iso()
    center = geofence["center"]
    radius_nm = geofence["radius_nm"]
    try:
        aircraft = qa.query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return {
            "timestamp": timestamp,
            "provider": name,
            "error": "%s: %s" % (type(exc).__name__, exc),
        }
    in_bbox = qa.filter_in_geofence(aircraft, geofence)
    return {
        "timestamp": timestamp,
        "provider": name,
        "total": len(aircraft),
        "in_bbox": [reduce_aircraft(ac) for ac in in_bbox],
    }


def append_jsonl(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record))
        f.write("\n")


def run(minutes, interval, out_dir, geofence_path, timeout=15.0):
    geofence = qa.load_geofence(geofence_path)
    providers = list(qa.PROVIDERS.keys())

    os.makedirs(out_dir, exist_ok=True)
    run_start = datetime.now(timezone.utc)
    run_start_tag = run_start.strftime("%Y%m%dT%H%M%SZ")
    paths = {name: os.path.join(out_dir, "%s_%s.jsonl" % (run_start_tag, name)) for name in providers}

    print(
        "Starting %.1f-minute sample window (%ss interval) - writing JSONL to %s"
        % (minutes, interval, out_dir)
    )
    for name in providers:
        print("  %s -> %s" % (name, paths[name]))

    end_epoch = time.time() + minutes * 60
    cycle = 0
    while time.time() < end_epoch:
        cycle += 1
        cycle_start = time.time()
        for i, name in enumerate(providers):
            if i > 0:
                # Courtesy delay between two different providers' calls; each
                # provider's own 1 req/sec limit is trivially respected since
                # samples are only taken every `interval` seconds anyway.
                time.sleep(1.1)
            record = sample_provider(name, geofence, timeout)
            append_jsonl(paths[name], record)
            if "error" in record:
                progress = "ERROR: %s" % record["error"]
            else:
                progress = "total=%d in_bbox=%d" % (record["total"], len(record["in_bbox"]))
            print("[%s] cycle %d %s: %s" % (record["timestamp"], cycle, name, progress))

        elapsed = time.time() - cycle_start
        remaining = interval - elapsed
        if remaining > 0 and time.time() < end_epoch:
            time.sleep(remaining)

    print("Sample window complete: %d cycles." % cycle)
    return paths


def build_parser():
    parser = argparse.ArgumentParser(description="Unattended windowed ADS-B aggregator sampler.")
    parser.add_argument("--minutes", type=float, default=90.0, help="Window length in minutes (default: 90).")
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Seconds between samples of each provider (default: 30).",
    )
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="Output directory for JSONL files.")
    parser.add_argument("--geofence", default=qa.DEFAULT_GEOFENCE, help="Path to the geofence JSON.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    run(args.minutes, args.interval, args.out, args.geofence, args.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
