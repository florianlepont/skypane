#!/usr/bin/env python3
"""The single owner of `<state_dir>/poll_state.json` and the read-only
reader of byos's `<state_dir>/battery_state.json`.

Every writer of poll_state.json (server/poll_loop.py's `_run_once_locked`)
and every reader (server/wake.py, stub-server/byos_server.py, the
companion's health/airlines pages) goes through this module instead of
each keeping its own copy of the path, the load/save logic and the
compact-JSON encoding. Key names and the compact serialisation format are
an on-disk contract shared across three independent processes (the
systemd poll timer, the always-on byos device endpoint, and the
companion) - changing either here changes it for all of them at once.

Do not edit poll_loop.py, wake.py or byos_server.py here: this module is a
new, unwired file; later plans switch those callers over to it, one owner
at a time.
"""
from __future__ import annotations

import json
import os

from server import atomic_io, device_policy

POLL_STATE_FILENAME = "poll_state.json"
BATTERY_STATE_FILENAME = "battery_state.json"

# Allow both `import server.state_store` (package import) and direct
# script execution: sys.path[0] is server/ itself when this file is
# executed directly - mirrors poll_loop.py's own `_HERE`/DEFAULT_STATE_DIR
# bootstrap.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
DEFAULT_STATE_DIR = os.path.join(_HERE, "state")

# Tri-valued hold-state latch; `None` means not holding. A single key
# keeps "already holding?" the single test `was_hold is None` for any
# number of hold mechanisms.
HOLD_KINDS = ("quiet_hours", "display_off", "battery_empty")


def poll_state_path(state_dir: str) -> str:
    return os.path.join(state_dir, POLL_STATE_FILENAME)


def load_poll_state(state_dir: str) -> dict[str, object]:
    """Missing, unreadable, or malformed -> empty state, never a crash."""
    try:
        with open(poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def hold_state(poll_state: dict[str, object]) -> str | None:
    """The current hold kind, or `None` when not holding. Falls back to
    the legacy `quiet_hours_active` boolean when `hold_state` is absent
    (an older poll_state.json); the caller retires that key on its next
    write. Never raises.
    """
    if "hold_state" in poll_state:
        kind = poll_state.get("hold_state")
        return kind if kind in HOLD_KINDS else None
    return "quiet_hours" if poll_state.get("quiet_hours_active") is True else None


def load_battery_state(state_dir: str) -> int | None:
    """Read-only: `<state_dir>/battery_state.json` is owned and written
    exclusively by stub-server/byos_server.py's save_battery_state().
    Returns the int `battery_mv` reading, or None on any failure (missing
    file, invalid JSON, wrong type, non-positive). Never raises.
    """
    try:
        with open(os.path.join(state_dir, BATTERY_STATE_FILENAME)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    mv = data.get("battery_mv")
    if isinstance(mv, bool) or not isinstance(mv, int) or mv <= 0:
        return None
    return mv


def serialize_poll_state(state: dict[str, object]) -> str:
    """Compact JSON encoding of `state` - no indentation, no space after a
    "," or ":". Every reader uses json.load, so this is invisible to them;
    the compactness only shrinks the file on disk, and gives
    `persist_poll_state_if_changed()` a cheap string to diff against the
    snapshot taken at load time.
    """
    return json.dumps(state, separators=(",", ":"))


def save_poll_state(state_dir: str, state: dict[str, object]) -> None:
    """Atomic same-directory-mkstemp-then-os.replace() via atomic_io, so
    two processes writing this same path (the systemd oneshot and the
    companion's POST /poll-now) can never collide on one fixed temp name.
    Always writes, unconditionally - the public seam the test suite uses
    to seed a poll_state.json directly; the write-once-only-if-changed
    decision lives in `persist_poll_state_if_changed()`.
    """
    atomic_io.atomic_write(poll_state_path(state_dir), serialize_poll_state(state))


def persist_poll_state_if_changed(
    state_dir: str, poll_state: dict[str, object], baseline: str,
) -> None:
    """The cycle's single end-of-cycle save. Serialises `poll_state` once
    and writes it through the same atomic path as `save_poll_state()`, but
    only when that serialisation differs from `baseline` - the compact
    snapshot the caller took right after `load_poll_state()`, before any
    branch mutated the dict in place. An unchanged repeat cycle (a held
    hold, an unchanged empty sky) compares equal and writes nothing.
    """
    serialized = serialize_poll_state(poll_state)
    if serialized != baseline:
        atomic_io.atomic_write(poll_state_path(state_dir), serialized)


def read_battery_critical(state_dir: str) -> bool:
    """True only when poll_state.json's `device_policy.BATTERY_CRITICAL_STATE_KEY`
    is literally `True`; any failure degrades to False, never raises -
    fail-open, since a wrongly-returned False costs a few extra wakes,
    never a missed BATTERY EMPTY render. Semantically identical to
    `wake.read_battery_critical()` and byos_server.py's own copy: both
    degrade to `{}` on the same failures `load_poll_state()` does.
    """
    return load_poll_state(state_dir).get(device_policy.BATTERY_CRITICAL_STATE_KEY) is True
