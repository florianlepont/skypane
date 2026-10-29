#!/usr/bin/env python3
"""Fleet database: users, roles, locations and devices in one SQLite file.

Leaf module: stdlib plus `server.hardware` and `server.atomic_io`. It must
never import the companion, the poll loop, or the byos server.

Invariants:
- Every device has exactly one owner: `devices.owner_user_id` is NOT NULL
  and references `users(id)`. Foreign keys are enforced per connection
  (SQLite does not persist the setting), so every connection helper here
  turns them on. Nothing cascades and there is no user-delete API:
  disabling a user never orphans a device.
- A user's role lives only in `users.role` and is read only through
  `get_user_role`.
- The schema moves forward by `PRAGMA user_version` steps, each applied in
  one transaction together with the version bump. A database newer than
  this code is refused and never written.
- The file is created mode 0600 before SQLite touches it, so the -wal and
  -shm files derived from it are never wider than 0600 either.
"""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import sys
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

# Same repo-root sys.path bootstrap as server/history_db.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import atomic_io  # noqa: E402

FLEET_DB_FILENAME = "fleet.db"
FLEET_STATUS_FILENAME = "fleet_status.json"

META_MIGRATED = "migrated_v1"
META_BOOTSTRAP_OWNER = "bootstrap_owner_user_id"

# "absent": no fleet.db or not yet migrated (a normal pre-deploy state).
# "fault": the file exists but is unreadable, corrupt, or newer than this code.
STATUS_OK = "ok"
STATUS_ABSENT = "absent"
STATUS_FAULT = "fault"

ROLES = ("admin", "user")

_BUSY_TIMEOUT_MS = 5000


class FleetDbError(Exception):
    """Base class for fleet database failures."""


class FleetDbAbsent(FleetDbError):
    """fleet.db does not exist."""


class FleetDbTooNew(FleetDbError):
    """The database schema is newer than this code understands."""


Migration = Callable[[sqlite3.Connection], None]


def _migrate_v1(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE users ("
        " id INTEGER PRIMARY KEY,"
        " email TEXT NOT NULL UNIQUE COLLATE NOCASE,"
        " role TEXT NOT NULL CHECK (role IN ('admin', 'user')),"
        " disabled INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),"
        " iss TEXT,"
        " sub TEXT,"
        " created_at TEXT NOT NULL,"
        " UNIQUE (iss, sub))"
    )
    conn.execute(
        "CREATE TABLE locations ("
        " id INTEGER PRIMARY KEY,"
        " name TEXT NOT NULL,"
        " latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),"
        " longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),"
        " timezone TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE devices ("
        " id TEXT PRIMARY KEY,"
        " mac TEXT NOT NULL UNIQUE,"
        " secret_sha256 TEXT NOT NULL,"
        " token TEXT,"
        " hardware_type TEXT NOT NULL,"
        " owner_user_id INTEGER NOT NULL REFERENCES users(id),"
        " location_id INTEGER REFERENCES locations(id),"
        " name TEXT,"
        " state_path TEXT NOT NULL DEFAULT '.',"
        " created_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )


MIGRATIONS: tuple[Migration, ...] = (_migrate_v1,)
SCHEMA_VERSION = len(MIGRATIONS)


def utc_now_iso() -> str:
    """Timezone-aware UTC ISO-8601 string at seconds precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fleet_db_path(state_dir: str) -> str:
    return os.path.join(state_dir, FLEET_DB_FILENAME)


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    # Per connection: SQLite does not persist this setting in the file.
    conn.execute("PRAGMA foreign_keys=ON")


def _refuse_if_too_new(conn: sqlite3.Connection) -> None:
    if schema_version(conn) > SCHEMA_VERSION:
        raise FleetDbTooNew(
            f"fleet.db schema {schema_version(conn)} is newer than "
            f"supported {SCHEMA_VERSION}"
        )


def migrate_schema(
    conn: sqlite3.Connection,
    migrations: tuple[Migration, ...] = MIGRATIONS,
) -> None:
    """Apply pending steps, each atomically with its version bump."""
    current = schema_version(conn)
    if current > len(migrations):
        raise FleetDbTooNew(
            f"fleet.db schema {current} is newer than supported {len(migrations)}"
        )
    for index in range(current, len(migrations)):
        conn.execute("BEGIN IMMEDIATE")
        try:
            migrations[index](conn)
            # PRAGMA cannot take bound parameters; the value is an int.
            conn.execute("PRAGMA user_version = %d" % (index + 1))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise


def connect(
    state_dir: str, create: bool = True, timeout: float = 5.0
) -> sqlite3.Connection:
    """Open (and migrate) fleet.db, creating it mode 0600 when allowed."""
    path = fleet_db_path(state_dir)
    if not os.path.exists(path):
        if not create:
            raise FleetDbAbsent(path)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
    conn = sqlite3.connect(path, timeout=timeout, isolation_level=None)
    try:
        _apply_pragmas(conn)
        # Checked before the journal mode is touched so a too-new file is
        # never written.
        _refuse_if_too_new(conn)
        conn.execute("PRAGMA journal_mode=WAL")
        migrate_schema(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def connect_readonly(state_dir: str) -> sqlite3.Connection:
    """Read-only handle; never creates and never migrates."""
    path = fleet_db_path(state_dir)
    if not os.path.exists(path):
        raise FleetDbAbsent(path)
    uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        _apply_pragmas(conn)
        _refuse_if_too_new(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def connect_memory() -> sqlite3.Connection:
    """Fully migrated in-memory database for dry runs."""
    conn = sqlite3.connect(":memory:", isolation_level=None)
    _apply_pragmas(conn)
    migrate_schema(conn)
    return conn


@contextlib.contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE ... COMMIT, or ROLLBACK when the body raises."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def meta_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def read_status(state_dir: str) -> dict[str, str] | None:
    """The status document, or None when absent or malformed."""
    path = os.path.join(state_dir, FLEET_STATUS_FILENAME)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    out: dict[str, str] = {}
    for key in ("state", "detail", "updated_at"):
        value = doc.get(key)
        if not isinstance(value, str):
            return None
        out[key] = value
    return out


def write_status(state_dir: str, state: str, detail: str = "") -> None:
    """Record the fleet.db state; skips the write when nothing changed."""
    current = read_status(state_dir)
    if current is not None and current["state"] == state and current["detail"] == detail:
        return
    doc = {"state": state, "detail": detail, "updated_at": utc_now_iso()}
    atomic_io.atomic_write(
        os.path.join(state_dir, FLEET_STATUS_FILENAME),
        json.dumps(doc, sort_keys=True) + "\n",
    )
