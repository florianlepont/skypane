#!/usr/bin/env python3
"""scripts/multi_site_replay.py -- replays a recorded session through the
current code.

`multi_site_run.py` keeps the raw provider answers of every zone fetch
(`payloads/<zone>.jsonl`) and the real adsbdb answers (`adsbdb_shared_cache.json`).
This script creates a fresh scratch root with the same simulated devices and
runs the unchanged fleet cycle over those answers, in recorded order, with a
fake clock set to each recorded time. A route comes from the recorded adsbdb
cache; a callsign not in it is a miss. Nothing touches the network and the
live state is never read or written.

Use it to see what a change would have done to traffic that really happened:
export the replayed root with `multi_site_export.py` and compare it with the
export of the original root.
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import multi_site_run, multi_site_setup  # noqa: E402
from server import fleet_cycle, history_db, poll_cycle, zone_fetch  # noqa: E402
from server.plane import enrich  # noqa: E402

# Records of one fleet cycle are written within a few seconds of each other.
CYCLE_GAP_S = 10.0
ROUTE_CACHE_NAME = "adsbdb_shared_cache.json"


class ReplayError(Exception):
    """The source cannot be replayed."""


def _epoch(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def read_cycles(source):
    """The recorded cycles of `source`, oldest first: `[{"ts", "epoch",
    "zones": {zone_key: record}}]`. Records closer than CYCLE_GAP_S belong to
    one cycle."""
    records = []
    for path in sorted(glob.glob(os.path.join(source, multi_site_run.PAYLOADS_DIRNAME, "*.jsonl"))):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    if not records:
        raise ReplayError("no recorded payloads under %s" % source)
    records.sort(key=lambda r: r["ts"])
    cycles = []
    for record in records:
        epoch = _epoch(record["ts"])
        if cycles and epoch - cycles[-1]["epoch"] <= CYCLE_GAP_S:
            cycles[-1]["zones"][record["zone_key"]] = record
        else:
            cycles.append({"ts": record["ts"], "epoch": epoch, "zones": {record["zone_key"]: record}})
    return cycles


def load_routes(source):
    """The recorded adsbdb answers, `{callsign: {"status", "body"}}`; empty when absent."""
    path = os.path.join(source, ROUTE_CACHE_NAME)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def route_transport(routes):
    """An adsbdb transport answering from the recorded answers only."""
    def transport(callsign, timeout=None):
        entry = routes.get(callsign)
        if isinstance(entry, dict) and isinstance(entry.get("status"), int):
            return entry["status"], entry.get("body")
        return 404, None
    return transport


class _CycleFetcher:
    """Answers each zone fetch of one replayed cycle from its recorded record."""

    def __init__(self):
        self.cycle = None

    def __call__(self, ledger, lat, lon, radius_nm, **kwargs):
        from server import fleet_zones
        key = fleet_zones.Zone(lat, lon, radius_nm).key
        record = (self.cycle or {}).get("zones", {}).get(key)
        if record is None:
            return zone_fetch.ZoneFetch((("adsbfi", []),), ("adsbfi",), ())
        results = tuple((name, aircraft) for name, aircraft in record["results"].items())
        return zone_fetch.ZoneFetch(results, tuple(record["queried"]), tuple(record["failed"]))


def replay_session(source, out_root, specs, out=lambda line: None):
    """Replay the recorded cycles of `source` on a new scratch root `out_root`
    holding the devices `specs`; returns how many cycles ran."""
    if os.path.exists(out_root):
        raise ReplayError("%s already exists; give a new directory" % out_root)
    cycles = read_cycles(source)
    routes = route_transport(load_routes(source))
    multi_site_setup.create_scratch_fleet(out_root, specs)
    clock_now = {"t": cycles[0]["epoch"]}
    fetcher = _CycleFetcher()
    real_now, real_iso, real_vrs = poll_cycle.now_s, history_db.utc_now_iso, enrich.default_vrs_transport
    # The poll cycle times its display queue by now_s() and stamps its rows
    # with utc_now_iso(): drive both with the recorded time, or the queue
    # pacing (90 s, 150 s) is not replayed and the rows carry today's time.
    poll_cycle.now_s = lambda: clock_now["t"]
    # The recorded cache holds adsbdb answers only: the VRS standing data is
    # never asked, and every VRS lookup is a miss.
    enrich.default_vrs_transport = lambda key, timeout=None: (404, None)
    history_db.utc_now_iso = lambda: datetime.fromtimestamp(
        clock_now["t"], timezone.utc).isoformat(timespec="seconds")
    try:
        with multi_site_run.simulation_flag():
            return _run_cycles(out_root, cycles, clock_now, fetcher, routes, out)
    finally:
        poll_cycle.now_s, history_db.utc_now_iso = real_now, real_iso
        enrich.default_vrs_transport = real_vrs


def _run_cycles(out_root, cycles, clock_now, fetcher, routes, out):
    done = 0
    for cycle in cycles:
        clock_now["t"] = cycle["epoch"]
        fetcher.cycle = cycle
        result = fleet_cycle.run_fleet(
            out_root, None, None, clock=lambda: clock_now["t"], monotonic=lambda: clock_now["t"],
            sleep=lambda seconds: None, fetcher=fetcher, route_transport=routes, runner=None)
        done += 1
        out(multi_site_run._summary(done, cycle["epoch"], result))
    return done


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", required=True, help="scratch root of a recorded session")
    parser.add_argument("--out", required=True, help="new scratch root for the replay")
    parser.add_argument("--device", action="append", required=True, metavar="NAME=ICAO:DESIGNATOR")
    args = parser.parse_args(argv)
    try:
        specs = [multi_site_setup.parse_device(text) for text in args.device]
        replay_session(args.source, args.out, specs, out=print)
    except (ReplayError, multi_site_setup.ScratchRootError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
