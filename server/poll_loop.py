#!/usr/bin/env python3
"""The systemd-timer oneshot entrypoint: detect -> render -> atomic swap.

Poll cadence: 30 seconds, inside both aggregators' 1 req/s limit. No
in-process loop - a systemd `.timer`/`.service` unit pair drives the
cadence by invoking this repeatedly.

No in-process memory between invocations: cross-cycle state lives in
`<state_dir>/poll_state.json` (written through server/atomic_io.py's
same-directory-mkstemp-then-os.replace(), so this process and a
concurrent companion/app.py trigger can never collide on one fixed temp
name); malformed state degrades to empty, never a crash.
`<state_dir>/battery_state.json` is a second, read-only input owned
exclusively by stub-server/byos_server.py.

Display pacing: the frame can't redraw as fast as this server polls, so a
distinct new detection is queued rather than shown immediately, and the
"current" slot advances no faster than the device's measured redraw floor
- a mitigation, not a cure: a severe burst can still overflow the queue
and lose flights.

The poll cycle itself (detect/infer/enrich/render/publish/record) lives in
server/poll_cycle.py, shared by every device. One run of
this module serves every device of the fleet through server/fleet_cycle.py:
devices sharing a zone cost one request set, and a failure for one device
never stops the others. Without a fleet.db it serves the live frame alone,
as a single-device cycle. The exit status reflects the live frame only.

Usage:
    server/.venv/bin/python3 server/poll_loop.py --once
    server/.venv/bin/python3 server/poll_loop.py --once --state-dir /tmp/x
"""
import argparse
import os
import sys
import traceback

# Allow both `import server.poll_loop` and direct script execution:
# sys.path[0] is server/ itself when run directly.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server.fleet_cycle import FleetResult, run_fleet  # noqa: E402
from server.poll_cycle import run_once  # noqa: E402
from server.state_store import DEFAULT_STATE_DIR  # noqa: E402


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit. This script is always single-cycle "
             "(a systemd timer drives the 30s repeat cadence) - "
             "accepted for explicitness at the CLI.",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Directory holding panel.bin / poll_state.json (default: server/state/).",
    )
    parser.add_argument(
        "--geofence",
        default=None,
        help="Path to the geofence JSON (default: adsb-test/runway3.json).",
    )
    parser.add_argument(
        "--caddy-log",
        default=None,
        help="Path to Caddy's durable device-protocol access log "
             "(SKYPANE_CADDY_ACCESS_LOG in skypane.env), tailed every cycle "
             "for CFG-03's X-Battery-Mv telemetry. Omit to skip ingestion.",
    )
    return parser


def _report(result: FleetResult) -> int:
    """Print the run summary and per-failure lines; 1 only for a live-frame failure."""
    print(
        "poll_loop: fleet ok=%d held=%d busy=%d failed=%d deferred=%d skipped=%d "
        "zones=%d requests=%d" % (
            result.count("ok"), result.count("held"), result.count("busy"),
            result.count("failed"), result.count("deferred"), result.count("skipped"),
            result.zone_fetches, result.requests))
    exit_code = 0
    for outcome in result.outcomes:
        if outcome.status not in ("busy", "failed"):
            continue
        if not outcome.is_live:
            print("poll_loop: device %s %s: %s" % (outcome.device_id, outcome.status, outcome.detail))
        elif outcome.status == "busy":
            # Another process (the companion, or an overlapping timer firing)
            # is mid-cycle: an expected, bounded wait outcome, not a bug.
            print(outcome.detail)
            exit_code = 1
        else:
            # journald captures stdout, so the traceback goes there too.
            print("poll_loop: cycle failed: %s" % outcome.detail)
            print(outcome.trace, end="")
            exit_code = 1
    return exit_code


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = run_fleet(args.state_dir, args.geofence, args.caddy_log, runner=run_once)
    except Exception as exc:
        # A failed run must leave the previously served panels intact and
        # never crash-loop the systemd timer silently.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        traceback.print_exc(file=sys.stdout)
        return 1
    return _report(result)


if __name__ == "__main__":
    sys.exit(main())
