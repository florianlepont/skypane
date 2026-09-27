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
server/poll_cycle.py, shared unchanged with the companion's POST /poll-now;
this module is only the CLI wrapper systemd invokes.

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

from server.poll_cycle import PollBusy, run_once  # noqa: E402
from server.state_store import DEFAULT_STATE_DIR  # noqa: E402

# Transitional read-only bindings for the companion's own switch (a
# separate, isolated commit): removed once companion/app.py imports
# server.poll_cycle directly instead of reaching these through here.
from server.poll_cycle import _save_to_gallery, now_s, poll_cycle_lock, write_panel_atomic  # noqa: E402,F401


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit. This script is always single-cycle "
             "(a systemd timer, added in plan 02-05, drives the 30s repeat cadence) - "
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


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        run_once(state_dir=args.state_dir, geofence=args.geofence, caddy_log=args.caddy_log)
    except PollBusy as exc:
        # Distinct from the generic failure below: another process (the
        # companion, or an overlapping timer firing) is mid-cycle, not a
        # cycle that itself failed. No traceback - this is an expected,
        # bounded wait outcome, not a bug.
        print(str(exc))
        return 1
    except Exception as exc:
        # A failed cycle must leave the previously served panel intact and
        # never crash-loop the systemd timer silently - log to stdout
        # (journald captures this) and exit non-zero.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        # journald captures stdout, not this process's own traceback
        # rendering choices - a one-line summary alone leaves no way to
        # tell which line raised without reproducing the failure locally.
        traceback.print_exc(file=sys.stdout)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
