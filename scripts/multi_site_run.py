#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""scripts/multi_site_run.py -- runs the unchanged fleet cycle over a scratch
state root (see multi_site_setup.py) for a number of cycles or until a time,
and keeps the raw provider answers of every zone fetch for later replay.

Each cycle is one fleet_cycle.run_fleet call: the same zone grouping, the
same request ledger and spacing and the same provider list as the production
poll timer. The recording fetcher only appends what the real fetcher
returned to payloads/<zone>.jsonl under the scratch root; it never changes
the result. The simulation flag is set in this process's environment while
the session runs and restored afterwards.

A cycle starts at least --interval seconds (never under 30, the production
cadence) after the previous one. Creating the --stop-file ends the session
cleanly after the current cycle.
"""
import argparse
import contextlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import multi_site_setup  # noqa: E402
from server import fleet_cycle, fleet_zones, hardware, state_store, zone_fetch  # noqa: E402

MIN_INTERVAL_S = 30.0
PAYLOADS_DIRNAME = "payloads"
_STOP_POLL_S = 1.0
_UNSAFE_NAME_CHARS = re.compile(r"[^0-9A-Za-z.\-]")


def require_scratch_root(root):
    """Raise ScratchRootError unless `root` is an existing, marked scratch root."""
    real = os.path.realpath(root)
    if real == os.path.realpath(state_store.DEFAULT_STATE_DIR):
        raise multi_site_setup.ScratchRootError("refusing the server's default state directory")
    if not os.path.isfile(os.path.join(real, multi_site_setup.MARKER_FILENAME)):
        raise multi_site_setup.ScratchRootError(
            "%s has no scratch marker; create it with multi_site_setup.py" % root)


def zone_file_stem(zone_key):
    """A file-name-safe form of a zone key such as '48.7|2.4|10.0'."""
    return _UNSAFE_NAME_CHARS.sub("_", zone_key)


def _iso(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def recording_fetcher(root, inner, clock=None):
    """Wrap a zone fetcher so each answer is appended under `<root>/payloads/`.

    The wrapped call returns exactly what `inner` returned. A failure to
    write the record is reported on stderr and never fails the fetch.
    """
    now = clock if clock is not None else time.time

    def fetch(ledger, lat, lon, radius_nm, **kwargs):
        fetched = inner(ledger, lat, lon, radius_nm, **kwargs)
        try:
            zone = fleet_zones.Zone(lat, lon, radius_nm)
            record = {
                "ts": _iso(now()),
                "zone_key": zone.key,
                "lat": zone.lat,
                "lon": zone.lon,
                "radius_nm": zone.radius_nm,
                "results": {name: aircraft for name, aircraft in fetched.results},
                "queried": list(fetched.queried),
                "failed": list(fetched.failed),
            }
            directory = os.path.join(root, PAYLOADS_DIRNAME)
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, zone_file_stem(zone.key) + ".jsonl")
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        except (OSError, ValueError, TypeError) as exc:
            print("multi_site_run: could not record a payload: %s" % type(exc).__name__,
                  file=sys.stderr)
        return fetched

    return fetch


@contextlib.contextmanager
def simulation_flag():
    """Set the simulation flag for this process only and restore it on exit."""
    previous = os.environ.get(hardware.SIM_ENV_VAR)
    os.environ[hardware.SIM_ENV_VAR] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(hardware.SIM_ENV_VAR, None)
        else:
            os.environ[hardware.SIM_ENV_VAR] = previous


def _summary(number, when, result):
    return (
        "cycle %d %s ok=%d held=%d busy=%d failed=%d deferred=%d skipped=%d zones=%d requests=%d"
        % (number, _iso(when), result.count(fleet_cycle.STATUS_OK),
           result.count(fleet_cycle.STATUS_HELD), result.count(fleet_cycle.STATUS_BUSY),
           result.count(fleet_cycle.STATUS_FAILED), result.count(fleet_cycle.STATUS_DEFERRED),
           result.count(fleet_cycle.STATUS_SKIPPED), result.zone_fetches, result.requests))


def run_session(
    root, cycles=None, until=None, interval=MIN_INTERVAL_S, stop_file=None,
    fetcher=None, runner=None, clock=None, monotonic=None, sleep=None, out=print,
):
    """Run fleet cycles over the scratch `root`; returns how many ran.

    `cycles` and `until` (an aware datetime) each end the session; at least
    one is required. The fetcher, runner and clocks are injectable for tests.
    """
    if interval < MIN_INTERVAL_S:
        raise ValueError("interval must be at least %d seconds" % MIN_INTERVAL_S)
    if cycles is None and until is None:
        raise ValueError("give --cycles or --until")
    require_scratch_root(root)
    wall = clock if clock is not None else time.time
    mono = monotonic if monotonic is not None else time.monotonic
    nap = sleep if sleep is not None else time.sleep
    inner = fetcher if fetcher is not None else zone_fetch.fetch_zone
    recorder = recording_fetcher(root, inner, wall)
    until_epoch = None if until is None else until.timestamp()

    def stopped():
        return stop_file is not None and os.path.exists(stop_file)

    done = 0
    with simulation_flag():
        while True:
            if until_epoch is not None and wall() >= until_epoch:
                break
            started_mono, started_wall = mono(), wall()
            result = fleet_cycle.run_fleet(
                root, None, None, clock=clock, monotonic=monotonic, sleep=sleep,
                runner=runner, fetcher=recorder)
            done += 1
            out(_summary(done, started_wall, result))
            next_start = started_mono + interval
            if (cycles is not None and done >= cycles) or stopped():
                break
            if until_epoch is not None and wall() + (next_start - mono()) >= until_epoch:
                break
            while mono() < next_start and not stopped():
                nap(min(_STOP_POLL_S, next_start - mono()))
            if stopped():
                break
    return done


def _parse_until(text):
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", required=True, help="scratch state root")
    parser.add_argument("--cycles", type=int, help="number of cycles to run")
    parser.add_argument("--until", type=_parse_until, help="UTC end, e.g. 2026-11-20T09:00:00Z")
    parser.add_argument("--interval", type=float, default=MIN_INTERVAL_S,
                        help="seconds between cycle starts (not below 30)")
    parser.add_argument("--stop-file", help="end cleanly after the current cycle when this exists")
    args = parser.parse_args(argv)
    try:
        run_session(args.root, args.cycles, args.until, args.interval, args.stop_file)
    except (multi_site_setup.ScratchRootError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
