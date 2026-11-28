#!/usr/bin/env python3
"""One schema-migration mechanism for fleet.db and history.db.

A database is described by an ordered tuple of `Step`s and a `Policy`:

- `Policy(locking="immediate", newer="refuse")` is fleet.db. Steps are
  one-time: each runs inside `BEGIN IMMEDIATE` together with its
  `PRAGMA user_version` bump, a step another process already applied while
  this one waited for the lock is skipped, and a file stamped newer than
  the last step is refused (`policy.error`) before anything is written.
- `Policy(locking="idempotent", newer="keep")` is history.db. Several
  processes can open a fresh file at the same moment, so every step must be
  safe to repeat and to run beside another process; all steps run on every
  call, and the stamp is only ever raised to the newest step, never lowered
  and never refused.

`python3 -m server.sqlite_migrations report --state-dir DIR` is a read-only
dry run: one line per database file with its version, the target version
and the pending steps. It opens every file read-only and prints versions,
step names and counts only, never row contents.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import sqlite3
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Every connection to either database waits this long for a lock.
BUSY_TIMEOUT_MS = 5000

EXIT_CURRENT = 0
EXIT_UNREADABLE = 2
EXIT_PENDING = 3


@dataclass(frozen=True)
class Step:
    """One schema step: `apply` brings a file from `version - 1` to `version`.

    `impact` describes, for the report only, what the step would change on a
    file that has not had it yet. It reads the connection (read-only) and
    returns a short text without spaces or row data.
    """

    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]
    impact: Callable[[sqlite3.Connection], str] | None = None


@dataclass(frozen=True)
class Policy:
    """How a database's steps are applied; see the module docstring."""

    locking: Literal["immediate", "idempotent"]
    newer: Literal["refuse", "keep"]
    error: type[Exception] = RuntimeError
    label: str = "database"


def set_busy_timeout(conn: sqlite3.Connection) -> None:
    """Make every wait for a lock on `conn` last `BUSY_TIMEOUT_MS`."""
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")


def read_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def target_version(steps: Sequence[Step]) -> int:
    return max((step.version for step in steps), default=0)


def pending_steps(conn: sqlite3.Connection, steps: Sequence[Step]) -> list[Step]:
    """The steps above the file's current version. Reads only."""
    current = read_user_version(conn)
    return [step for step in steps if step.version > current]


def refuse_if_newer(
    conn: sqlite3.Connection, steps: Sequence[Step], policy: Policy
) -> None:
    """Raise `policy.error` for a file stamped above the last step, under a
    "refuse" policy. Writes nothing."""
    if policy.newer != "refuse":
        return
    current = read_user_version(conn)
    target = target_version(steps)
    if current > target:
        raise policy.error(
            f"{policy.label} schema {current} is newer than supported {target}"
        )


def add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, sql_type: str
) -> None:
    """`ALTER TABLE ... ADD COLUMN` unless the column is present.

    Two processes can reach this on the same file: "duplicate column name"
    means the other one added it between the column read and the ALTER,
    which counts as done. Any other error propagates. `table`, `column` and
    `sql_type` are identifiers that cannot be bound parameters; callers pass
    them from fixed tuples, never from input.
    """
    present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column in present:
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc):
            raise


def _apply_immediate(
    conn: sqlite3.Connection, steps: Sequence[Step], policy: Policy
) -> None:
    refuse_if_newer(conn, steps, policy)
    current = read_user_version(conn)
    for step in steps:
        if step.version <= current:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Another process may have applied this step while we waited
            # for the write lock; re-read inside the lock and skip it.
            if read_user_version(conn) >= step.version:
                conn.execute("COMMIT")
                continue
            step.apply(conn)
            # PRAGMA cannot take bound parameters; the value is an int.
            conn.execute("PRAGMA user_version = %d" % step.version)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise


def _apply_idempotent(conn: sqlite3.Connection, steps: Sequence[Step]) -> None:
    # Every step repeats safely, so all of them run each time: a file stamped
    # current but missing an object is repaired, and a newer stamp is kept.
    for step in steps:
        step.apply(conn)
    conn.commit()
    target = target_version(steps)
    if read_user_version(conn) < target:
        conn.execute("PRAGMA user_version = %d" % target)


def apply_steps(
    conn: sqlite3.Connection, steps: Sequence[Step], policy: Policy
) -> None:
    """Bring `conn`'s database up to the last of `steps` under `policy`."""
    if policy.locking == "immediate":
        _apply_immediate(conn, steps, policy)
    else:
        _apply_idempotent(conn, steps)


# --- read-only report -------------------------------------------------------


def _open_readonly(path: str) -> sqlite3.Connection:
    """Open `path` so that nothing on disk can change, side files included.

    A live WAL database (both side files present) is read with `mode=ro`,
    which sees the log. Without both side files there is no log to read, and
    a plain read-only open would create them, so the file is opened
    `immutable` (no locking, no side files).
    """
    uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
    if not (os.path.exists(path + "-wal") and os.path.exists(path + "-shm")):
        uri += "&immutable=1"
    conn = sqlite3.connect(uri, uri=True, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.execute("PRAGMA query_only=ON")
    return conn


def _step_field(conn: sqlite3.Connection, step: Step) -> str:
    impact = step.impact(conn) if step.impact is not None else "unknown"
    return f"step={step.version}:{step.name}:{impact}"


def report_line(label: str, path: str, steps: Sequence[Step], policy: Policy) -> tuple[str, int]:
    """One report line and its exit code for the database at `path`."""
    if not os.path.exists(path):
        return f"{label} absent", EXIT_CURRENT
    try:
        conn = _open_readonly(path)
    except sqlite3.Error:
        return f"{label} unreadable", EXIT_UNREADABLE
    try:
        current = read_user_version(conn)
        target = target_version(steps)
        pending = pending_steps(conn, steps)
        status = "ok"
        if current > target:
            status = "newer"
        elif pending:
            status = "pending"
        fields = [label, status, f"current={current}", f"target={target}",
                  f"pending={len(pending)}"]
        fields.extend(_step_field(conn, step) for step in pending)
        return " ".join(fields), EXIT_PENDING if pending else EXIT_CURRENT
    except sqlite3.Error:
        return f"{label} unreadable", EXIT_UNREADABLE
    finally:
        conn.close()


def _history_paths(state_dir: str) -> list[tuple[str, str]]:
    from server import device_dirs, history_db

    paths = [(history_db.HISTORY_DB_FILENAME,
              history_db.history_db_path(state_dir))]
    devices = os.path.join(state_dir, device_dirs.DEVICES_DIRNAME)
    if os.path.isdir(devices) and not os.path.islink(devices):
        for entry in sorted(os.listdir(devices)):
            folder = os.path.join(devices, entry)
            if device_dirs.is_valid_device_id(entry) and not os.path.islink(folder):
                paths.append((
                    f"{device_dirs.DEVICES_DIRNAME}/{entry}/{history_db.HISTORY_DB_FILENAME}",
                    history_db.history_db_path(folder),
                ))
    return paths


def report(state_dir: str) -> tuple[list[str], int]:
    """Report lines for fleet.db, the root history.db and every frame's
    history.db, and the worst exit code. Opens every file read-only."""
    from server import fleet_db, history_db

    jobs: list[tuple[str, str, Sequence[Step], Policy]] = [
        (fleet_db.FLEET_DB_FILENAME, fleet_db.fleet_db_path(state_dir),
         fleet_db.FLEET_STEPS, fleet_db.FLEET_POLICY),
    ]
    jobs.extend(
        (label, path, history_db.HISTORY_STEPS, history_db.HISTORY_POLICY)
        for label, path in _history_paths(state_dir)
    )
    lines: list[str] = []
    codes: list[int] = []
    for label, path, steps, policy in jobs:
        line, code = report_line(label, path, steps, policy)
        lines.append(line)
        codes.append(code)
    if EXIT_UNREADABLE in codes:
        return lines, EXIT_UNREADABLE
    return lines, max(codes, default=EXIT_CURRENT)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser(
        "report",
        help="print each database's schema version and pending steps; writes nothing",
    )
    rep.add_argument("--state-dir", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    lines, code = report(args.state_dir)
    with contextlib.suppress(BrokenPipeError):
        for line in lines:
            print(line)
    return code


if __name__ == "__main__":
    # Run as `python3 -m server.sqlite_migrations`: the repo root is on
    # sys.path then; as a plain script, add it.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    sys.exit(main())
