#!/usr/bin/env python3
"""Move the retired legacy files into a quarantine directory.

Run as `python3 -m server.retire_legacy_state --state-dir DIR [--apply]`
from a release directory, by the owner. The device server reads identity
from fleet.db only, so `devices.json` and `byos_state.json` are leftovers.
The airline registries and the artwork are read from the fleet root only, so
the per-frame copies `devices/<id>/manual_resolutions.json`,
`airline_name_overrides.json`, `airline_default_types.json` and
`devices/<id>/illustration_overrides/` are leftovers too.

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
- The per-frame copies move to `retired-legacy/<UTC date>/devices/<id>/`
  under the same rules (rename, no delete, no overwrite). Only valid frame
  directories are looked at; a symlinked frame directory, registry file or
  artwork directory, and a `devices/` entry that is not a frame id, are
  skipped and reported, never followed. The fleet-root registries and the
  fleet-root artwork are never touched. The move is refused until the
  merge marker of each kind of copy present exists in the state root
  (`airline_registry_migration.json` for registry files,
  `illustration_migration.json` for pictures): without it the copy may not
  have been merged into the fleet root yet. This step does not depend on
  the identity step and the identity step does not depend on it.
- Output names files, frame ids, sizes and counts only; never a MAC,
  secret hash, token or file content.

Exit codes: 0 done or nothing to do (including a dry run), 2 refused,
1 a file operation failed.
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

# Same repo-root sys.path bootstrap as server/fleet_migrate.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_dirs, fleet_migrate  # noqa: E402

LEGACY_FILES = (fleet_migrate.LEGACY_REGISTRY_FILE, fleet_migrate.LEGACY_STATE_FILE)
# Top-level directory under the state root; listed in the backup allow-list.
QUARANTINE_DIRNAME = "retired-legacy"
# Per-frame copies of what now lives at the fleet root, and the root marker
# that shows each kind was merged there.
FRAME_COPY_FILES = (
    "manual_resolutions.json",
    "airline_name_overrides.json",
    "airline_default_types.json",
)
FRAME_COPY_DIR = "illustration_overrides"
REGISTRY_MARKER = "airline_registry_migration.json"
ARTWORK_MARKER = "illustration_migration.json"
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


def _run_identity(state_dir: str, apply: bool, day: str) -> tuple[int, list[str]]:
    """The identity step: the exit code and the lines to print."""
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


@dataclass
class FrameCopies:
    """The per-frame copies found under `devices/`."""

    items: list[tuple[str, str]]  # (frame id, file or directory name)
    lines: list[str]  # one description per item
    skipped: list[str]  # reasons, no values
    registry_files: int = 0
    pictures: int = 0


def _count_files(directory: str) -> int:
    total = 0
    for _base, _dirs, files in os.walk(directory, followlinks=False):
        total += len(files)
    return total


def _scan_frame(devices: str, frame: str, found: FrameCopies) -> None:
    directory = os.path.join(devices, frame)
    try:
        if stat.S_ISLNK(os.lstat(directory).st_mode):
            found.skipped.append("devices/%s is a symlink" % frame)
            return
        if not stat.S_ISDIR(os.lstat(directory).st_mode):
            found.skipped.append("devices/%s is not a directory" % frame)
            return
    except OSError:
        return
    for name in FRAME_COPY_FILES + (FRAME_COPY_DIR,):
        path = os.path.join(directory, name)
        try:
            mode = os.lstat(path).st_mode
        except OSError:
            continue
        if stat.S_ISLNK(mode):
            found.skipped.append("devices/%s/%s is a symlink" % (frame, name))
        elif name == FRAME_COPY_DIR and stat.S_ISDIR(mode):
            count = _count_files(path)
            found.items.append((frame, name))
            found.lines.append("devices/%s/%s: %d file(s)" % (frame, name, count))
            found.pictures += count
        elif name != FRAME_COPY_DIR and stat.S_ISREG(mode):
            found.items.append((frame, name))
            found.lines.append("devices/%s/%s: %d bytes" % (frame, name, os.lstat(path).st_size))
            found.registry_files += 1
        else:
            found.skipped.append("devices/%s/%s is not a regular file or directory" % (frame, name))


def find_frame_copies(state_dir: str) -> FrameCopies:
    """Look for per-frame copies without following any link."""
    found = FrameCopies([], [], [])
    devices = os.path.join(state_dir, device_dirs.DEVICES_DIRNAME)
    try:
        if stat.S_ISLNK(os.lstat(devices).st_mode):
            found.skipped.append("devices is a symlink")
            return found
        names = sorted(os.listdir(devices))
    except OSError:
        return found
    odd = 0
    for name in names:
        if device_dirs.is_valid_device_id(name):
            _scan_frame(devices, name, found)
        else:
            odd += 1
    if odd:
        found.skipped.append("%d entr%s of devices/ not named like a frame id" % (odd, "y" if odd == 1 else "ies"))
    return found


def _missing_markers(state_dir: str, found: FrameCopies) -> list[str]:
    needed = []
    if found.registry_files:
        needed.append(REGISTRY_MARKER)
    if found.pictures:
        needed.append(ARTWORK_MARKER)
    return [m for m in needed if not os.path.isfile(os.path.join(state_dir, m))]


def move_frame_copies(state_dir: str, found: FrameCopies, today: str) -> str:
    """Rename each copy into `retired-legacy/<today>/devices/<id>/`. Every
    target is checked before the first rename; nothing is overwritten."""
    base = quarantine_path(state_dir, today)
    targets = [os.path.join(base, device_dirs.DEVICES_DIRNAME, frame, name) for frame, name in found.items]
    for target in targets:
        if os.path.lexists(target):
            raise Refused("%s already exists in the quarantine directory" % os.path.relpath(target, base))
    for (frame, name), target in zip(found.items, targets):
        os.makedirs(os.path.dirname(target), mode=0o700, exist_ok=True)
        os.rename(os.path.join(state_dir, device_dirs.DEVICES_DIRNAME, frame, name), target)
        _fsync_dir(os.path.dirname(target))
        _fsync_dir(os.path.join(state_dir, device_dirs.DEVICES_DIRNAME, frame))
    return base


def _run_frame_copies(state_dir: str, apply: bool, day: str) -> tuple[int, list[str]]:
    """The per-frame step: the exit code and the lines to print (no line
    at all when there is no copy and nothing was skipped)."""
    found = find_frame_copies(state_dir)
    lines = ["skipped: %s" % reason for reason in found.skipped]
    if not found.items:
        return EXIT_OK, lines
    lines = ["per-frame copies present: %d" % len(found.items)] + found.lines + lines
    destination = os.path.join(QUARANTINE_DIRNAME, day, device_dirs.DEVICES_DIRNAME)
    missing = _missing_markers(state_dir, found)
    if missing:
        lines.append("refused: merge marker missing in the state directory: %s" % ", ".join(missing))
        return EXIT_REFUSED, lines
    if not apply:
        lines.append("dry run: would move %d per-frame copies into %s (rerun with --apply)"
                     % (len(found.items), destination))
        return EXIT_OK, lines
    try:
        move_frame_copies(state_dir, found, day)
    except Refused as exc:
        lines.append("refused: %s" % exc)
        return EXIT_REFUSED, lines
    except OSError as exc:
        lines.append("error: %s" % type(exc).__name__)
        return EXIT_FAILED, lines
    lines.append("moved %d per-frame copies into %s" % (len(found.items), destination))
    return EXIT_OK, lines


def run(state_dir: str, apply: bool, today: str | None = None) -> tuple[int, list[str]]:
    """The exit code and the lines to print: the identity step, then the
    per-frame step. The code is the worst of the two (2 refused, 1 failed)."""
    day = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    code, lines = _run_identity(state_dir, apply, day)
    frame_code, frame_lines = _run_frame_copies(state_dir, apply, day)
    worst = EXIT_REFUSED if EXIT_REFUSED in (code, frame_code) else max(code, frame_code)
    return worst, lines + frame_lines


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Move the retired devices.json, byos_state.json and the per-frame "
                    "registry and artwork copies into a quarantine directory "
                    "(dry run unless --apply).")
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
