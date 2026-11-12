"""Opt-in experiment that separates the frame's check interval from its
redraw interval.

Normally the frame wakes every `wake_interval_s` and the poll cycle may
change the panel on any of those wakes. With the experiment on, the frame
wakes every `check_interval_s` (at least 60 s) while the flight image is
replaced at most once per saved `wake_interval_s`; in between, the served
image hash is unchanged, so the firmware leaves the panel alone.

The experiment is off unless `check_interval_experiment.json` exists in the
device's state directory:

    {"check_interval_s": 60, "expires_at": <epoch seconds>}

It is inactive (every consumer behaves exactly as without the file) when:

* the file is missing, unreadable, or holds invalid values;
* `expires_at` has passed, or is more than 72 hours away;
* no valid `wake_interval_s` is saved in device_config.json (the fallback
  sleep is not a redraw period the owner chose);
* `check_interval_s` is not shorter than `wake_interval_s`;
* the last battery reading is unknown or at or below 3700 mV.

Operate it with `python3 -m server.check_interval set|status|clear`.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from collections.abc import Sequence

from server import atomic_io, device_policy, state_store

EXPERIMENT_FILENAME = "check_interval_experiment.json"
# poll_state.json key holding the epoch time of the last flight-path panel
# change; present only while the experiment is active.
LAST_FLIGHT_REDRAW_KEY = "last_flight_redraw_at"


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def experiment_path(state_dir: str) -> str:
    return os.path.join(state_dir, EXPERIMENT_FILENAME)


def read_experiment(state_dir: str, now: float) -> tuple[int, float] | None:
    """(check_interval_s, expires_at) when the file holds a valid, unexpired
    experiment whose expiry is at most 72 h away; None otherwise. Never
    raises.
    """
    try:
        with open(experiment_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    check = data.get("check_interval_s")
    expires = data.get("expires_at")
    if (not isinstance(check, int) or isinstance(check, bool)
            or check < device_policy.CHECK_INTERVAL_MIN_S):
        return None
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        return None
    if not now < expires <= now + device_policy.CHECK_INTERVAL_MAX_DURATION_S:
        return None
    return check, float(expires)


def active_check_interval_s(
    state_dir: str, wake_interval_s: object, battery_mv: object, now: float,
) -> int | None:
    """The check interval to serve as sleep_s, or None when the experiment
    is inactive for any reason listed in the module docstring.
    """
    experiment = read_experiment(state_dir, now)
    if experiment is None:
        return None
    check = experiment[0]
    if not _is_int(wake_interval_s) or not isinstance(wake_interval_s, int):
        return None
    if wake_interval_s <= check:
        return None
    if not _is_number(battery_mv) or not isinstance(battery_mv, (int, float)):
        return None
    if battery_mv <= device_policy.CHECK_INTERVAL_BATTERY_FLOOR_MV:
        return None
    return check


def redraw_due(last_redraw_at: object, now: float, wake_interval_s: float) -> bool:
    """Whether the flight image may change now: no previous redraw, a clock
    stepped backwards, or at least `wake_interval_s` since the last one.
    """
    if not _is_number(last_redraw_at) or not isinstance(last_redraw_at, (int, float)):
        return True
    if now < last_redraw_at:
        return True
    return now - last_redraw_at >= wake_interval_s


def write_experiment(
    state_dir: str, check_interval_s: int, duration_s: float, now: float,
    wake_interval_s: int | None = None,
) -> None:
    """Persist an experiment lasting `duration_s` from `now`. Raises
    ValueError for values the reader would reject.
    """
    if not _is_int(check_interval_s) or check_interval_s < device_policy.CHECK_INTERVAL_MIN_S:
        raise ValueError(
            "check_interval_s must be an integer of at least %d"
            % device_policy.CHECK_INTERVAL_MIN_S)
    if not _is_number(duration_s) or not 0 < duration_s <= device_policy.CHECK_INTERVAL_MAX_DURATION_S:
        raise ValueError(
            "duration must be positive and at most %d hours"
            % (device_policy.CHECK_INTERVAL_MAX_DURATION_S // 3600))
    if _is_int(wake_interval_s) and wake_interval_s is not None and check_interval_s >= wake_interval_s:
        raise ValueError(
            "check_interval_s must be shorter than the saved wake_interval_s (%d)"
            % wake_interval_s)
    os.makedirs(state_dir, exist_ok=True)
    payload = {"check_interval_s": check_interval_s, "expires_at": now + duration_s}
    atomic_io.atomic_write(experiment_path(state_dir), json.dumps(payload))


def clear_experiment(state_dir: str) -> bool:
    """Remove the experiment file; True when one was removed."""
    try:
        os.unlink(experiment_path(state_dir))
    except FileNotFoundError:
        return False
    return True


def _saved_wake_interval_s(state_dir: str) -> int | None:
    # Local import keeps this module light for the byos import chain.
    from server import device_config

    value = device_config.load_device_config(state_dir).get("wake_interval_s")
    return value if _is_int(value) else None


def _cmd_set(args: argparse.Namespace) -> int:
    wake = _saved_wake_interval_s(args.state_dir)
    if wake is None:
        print("error: no wake_interval_s is saved for this device; save one in "
              "the companion first", file=sys.stderr)
        return 2
    try:
        write_experiment(args.state_dir, args.check_interval_s,
                         args.hours * 3600, time.time(), wake_interval_s=wake)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print("check-interval experiment set: check every %d s, redraw every %d s, "
          "for %g h" % (args.check_interval_s, wake, args.hours))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    now = time.time()
    experiment = read_experiment(args.state_dir, now)
    if experiment is None:
        print("inactive: no valid unexpired experiment file")
        return 0
    wake = _saved_wake_interval_s(args.state_dir)
    battery = state_store.load_battery_state(args.state_dir)
    active = active_check_interval_s(args.state_dir, wake, battery, now)
    expires = datetime.datetime.fromtimestamp(experiment[1], datetime.timezone.utc)
    print("%s: check_interval_s=%d wake_interval_s=%s battery_mv=%s expires_at=%s"
          % ("active" if active is not None else "inactive", experiment[0],
             wake, battery, expires.isoformat()))
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    removed = clear_experiment(args.state_dir)
    print("check-interval experiment cleared" if removed
          else "no check-interval experiment was set")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m server.check_interval",
        description="Set, inspect or clear the check-interval experiment.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler, help_text in (
            ("set", _cmd_set, "start the experiment"),
            ("status", _cmd_status, "show the experiment"),
            ("clear", _cmd_clear, "stop the experiment")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--state-dir", default=state_store.DEFAULT_STATE_DIR)
        p.set_defaults(func=handler)
        if name == "set":
            p.add_argument("--check-interval-s", type=int,
                           default=device_policy.CHECK_INTERVAL_MIN_S)
            p.add_argument("--hours", type=float, default=24.0)
    args = parser.parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
