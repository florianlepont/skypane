#!/usr/bin/env python3
"""Move the retired legacy identity files into a quarantine directory.

Run as `python3 -m server.retire_legacy_state --state-dir DIR [--apply]`
from a release directory, by the owner. The device server reads identity
from fleet.db only, so `devices.json` and `byos_state.json` are leftovers.

Invariants:
- Dry run by default: without `--apply` nothing is written or moved (a
  read-only open of fleet.db may create SQLite's own -wal/-shm files).
- With `--apply` a file is only renamed (mode preserved) into
  `<state-dir>/retired-legacy/<UTC date>/`; nothing is ever deleted and an
  existing target is never overwritten. The quarantine directory is part
  of the nightly backup.
- Parity first: the move is refused unless fleet.db is migrated, readable
  and holds every device the legacy files register (checked with the same
  reader and planner the import uses). A secret or token that differs is
  not a gap: fleet.db is the only writer since the device server stopped
  mirroring, so it holds the newer value.
- Idempotent: with no legacy file left there is nothing to do.
- Output names files and counts only; never a MAC, secret hash or token.

Exit codes: 0 done or nothing to do (including a dry run), 2 refused,
1 a file operation failed.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

# Same repo-root sys.path bootstrap as server/fleet_migrate.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import fleet_migrate  # noqa: E402

LEGACY_FILES = (fleet_migrate.LEGACY_REGISTRY_FILE, fleet_migrate.LEGACY_STATE_FILE)
# Top-level directory under the state root; listed in the backup allow-list.
QUARANTINE_DIRNAME = "retired-legacy"
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2


class Refused(Exception):
    """The move cannot go ahead safely; the message names no value."""


@dataclass(frozen=True)
class Parity:
    legacy_devices: int
    legacy_tokens: int
    missing_devices: int
    differing_secrets: int
    differing_tokens: int

    @property
    def holds(self) -> bool:
        return self.missing_devices == 0


def present_legacy_files(state_dir: str) -> list[str]:
    return [name for name in LEGACY_FILES
            if os.path.lexists(os.path.join(state_dir, name))]


def check_parity(state_dir: str) -> Parity:
    """Compare the legacy files with fleet.db; raises Refused when the
    comparison cannot be made."""
    try:
        legacy = fleet_migrate.read_legacy(state_dir)
    except fleet_migrate.LegacyStateError as exc:
        raise Refused(str(exc)) from exc
    try:
        snapshot = fleet_migrate.read_snapshot(state_dir)
        if not snapshot.marker:
            raise Refused("fleet.db is absent or not migrated")
        plan = fleet_migrate.plan_migration(legacy, snapshot, None)
    except fleet_migrate.MigrationError as exc:
        raise Refused(str(exc)) from exc
    kinds = [action[0] for action in plan.actions]
    return Parity(
        legacy_devices=len(legacy.devices),
        legacy_tokens=len(legacy.tokens),
        missing_devices=kinds.count("add_device"),
        differing_secrets=kinds.count("sync_secret"),
        differing_tokens=kinds.count("sync_token"),
    )


def quarantine_path(state_dir: str, today: str) -> str:
    return os.path.join(state_dir, QUARANTINE_DIRNAME, today)


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def move_to_quarantine(state_dir: str, names: list[str], today: str) -> str:
    """Rename `names` into the dated quarantine directory and return its
    path. Every target is checked before the first rename."""
    target = quarantine_path(state_dir, today)
    for name in names:
        if os.path.lexists(os.path.join(target, name)):
            raise Refused("%s already exists in the quarantine directory" % name)
    os.makedirs(target, mode=0o700, exist_ok=True)
    for name in names:
        os.rename(os.path.join(state_dir, name), os.path.join(target, name))
    _fsync_dir(target)
    _fsync_dir(state_dir)
    return target


def _report_parity(parity: Parity) -> list[str]:
    lines = [
        "legacy devices: %d, legacy tokens: %d"
        % (parity.legacy_devices, parity.legacy_tokens),
        "devices the legacy files hold that fleet.db lacks: %d" % parity.missing_devices,
    ]
    if parity.differing_secrets or parity.differing_tokens:
        lines.append(
            "values that differ (fleet.db is newer and is kept): "
            "%d secret(s), %d token(s)"
            % (parity.differing_secrets, parity.differing_tokens))
    return lines


def run(state_dir: str, apply: bool, today: str | None = None) -> tuple[int, list[str]]:
    """The exit code and the lines to print."""
    names = present_legacy_files(state_dir)
    if not names:
        return EXIT_OK, ["nothing to do: no legacy identity file in the state directory"]
    lines = ["legacy identity files present: %s" % ", ".join(names)]
    try:
        parity = check_parity(state_dir)
    except Refused as exc:
        lines.append("refused: %s" % exc)
        return EXIT_REFUSED, lines
    lines.extend(_report_parity(parity))
    if not parity.holds:
        lines.append("refused: fleet.db does not hold every legacy device")
        return EXIT_REFUSED, lines
    day = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    destination = os.path.join(QUARANTINE_DIRNAME, day)
    if not apply:
        lines.append("dry run: would move %s into %s (rerun with --apply)"
                     % (", ".join(names), destination))
        return EXIT_OK, lines
    try:
        move_to_quarantine(state_dir, names, day)
    except Refused as exc:
        lines.append("refused: %s" % exc)
        return EXIT_REFUSED, lines
    except OSError as exc:
        lines.append("error: %s" % type(exc).__name__)
        return EXIT_FAILED, lines
    lines.append("moved %s into %s" % (", ".join(names), destination))
    return EXIT_OK, lines


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Move the retired devices.json and byos_state.json into a "
                    "quarantine directory (dry run unless --apply).")
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="move the files; without it nothing changes")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code, lines = run(args.state_dir, args.apply)
    for line in lines:
        print(line, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
