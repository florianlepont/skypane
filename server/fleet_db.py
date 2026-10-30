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
import re
import secrets
import sqlite3
import sys
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Same repo-root sys.path bootstrap as server/history_db.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import atomic_io, hardware  # noqa: E402

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

# Stored MAC form: lowercase, colon separated.
_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")
# Leading characters of a secret hash shown in listings; never the full hash.
_SECRET_PREFIX_LEN = 12


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


def _migrate_v2(conn: sqlite3.Connection) -> None:
    # Timestamps are integer epoch seconds: lifetime and idle checks are
    # arithmetic. Only the sha256 of the session token is stored.
    conn.execute(
        "CREATE TABLE sessions ("
        " id_hash TEXT PRIMARY KEY,"
        " user_id INTEGER REFERENCES users(id),"
        " principal TEXT NOT NULL CHECK (principal IN ('user', 'legacy-admin')),"
        " created_at INTEGER NOT NULL,"
        " last_seen_at INTEGER NOT NULL,"
        " expires_at INTEGER NOT NULL,"
        " CHECK ((principal = 'user') = (user_id IS NOT NULL)))"
    )
    conn.execute("CREATE INDEX sessions_user ON sessions (user_id)")
    conn.execute("CREATE INDEX sessions_expires ON sessions (expires_at)")


MIGRATIONS: tuple[Migration, ...] = (_migrate_v1, _migrate_v2)
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
            # Another process may have applied this step while we waited
            # for the write lock; re-read inside the lock and skip it.
            if schema_version(conn) > index:
                conn.execute("COMMIT")
                continue
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


# ---- users -----------------------------------------------------------


def normalize_email(value: str) -> str:
    """Lowercase and shape-check an email; raises ValueError."""
    email = value.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError(f"invalid email: {value!r}")
    return email


def add_user(
    conn: sqlite3.Connection,
    email: str,
    role: str,
    disabled: bool = False,
    iss: str | None = None,
    sub: str | None = None,
) -> int:
    """Insert a user and return its id; duplicates raise IntegrityError."""
    if role not in ROLES:
        raise ValueError(f"invalid role: {role!r}")
    cur = conn.execute(
        "INSERT INTO users (email, role, disabled, iss, sub, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (normalize_email(email), role, 1 if disabled else 0, iss, sub, utc_now_iso()),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def get_user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        "SELECT * FROM users WHERE email = ?", (normalize_email(email),)
    ).fetchone()
    return row


def list_users(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM users ORDER BY id"))


def set_user_disabled(conn: sqlite3.Connection, email: str, disabled: bool) -> bool:
    cur = conn.execute(
        "UPDATE users SET disabled = ? WHERE email = ?",
        (1 if disabled else 0, normalize_email(email)),
    )
    return cur.rowcount > 0


def get_user_role(conn: sqlite3.Connection, user_id: int) -> str | None:
    """The stored role of a user, or None for an unknown id.

    This is the only role reader. The role comes from the local row alone;
    it is never derived from an issuer claim or a request header.
    """
    row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    return None if row is None else str(row["role"])


# ---- locations -------------------------------------------------------


def add_location(
    conn: sqlite3.Connection,
    name: str,
    latitude: float,
    longitude: float,
    timezone: str,
) -> int:
    """Insert a location; latitude/longitude are degrees, timezone an IANA name."""
    if not name.strip():
        raise ValueError("location name is empty")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude out of range: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude out of range: {longitude}")
    try:
        ZoneInfo(timezone)
    except (KeyError, ValueError, OSError) as exc:
        raise ValueError(f"unknown timezone: {timezone!r}") from exc
    cur = conn.execute(
        "INSERT INTO locations (name, latitude, longitude, timezone) "
        "VALUES (?, ?, ?, ?)",
        (name, latitude, longitude, timezone),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def list_locations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM locations ORDER BY id"))


# ---- devices ---------------------------------------------------------


def _check_mac(mac: str) -> None:
    if not _MAC_RE.match(mac):
        raise ValueError(f"invalid MAC (lowercase aa:bb:cc:dd:ee:ff): {mac!r}")


def _check_secret(secret_sha256: str) -> None:
    if not _SHA256_RE.match(secret_sha256):
        raise ValueError("secret_sha256 must be 64 lowercase hex characters")


def add_device(
    conn: sqlite3.Connection,
    mac: str,
    secret_sha256: str,
    hardware_type: str,
    owner_user_id: int | None,
    location_id: int | None = None,
    name: str | None = None,
    token: str | None = None,
    state_path: str = ".",
    environ: Mapping[str, str] | None = None,
) -> str:
    """Insert a device and return its opaque id (`d_` plus 8 hex).

    The owner is mandatory: a missing or unknown owner raises
    sqlite3.IntegrityError. The hardware type must be available under the
    simulation gate in `environ`; reading existing rows never consults it.
    """
    _check_mac(mac)
    _check_secret(secret_sha256)
    hardware.get_profile(hardware_type, environ)
    while True:
        device_id = "d_" + secrets.token_hex(4)
        if conn.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone() is None:
            break
    conn.execute(
        "INSERT INTO devices (id, mac, secret_sha256, token, hardware_type, "
        "owner_user_id, location_id, name, state_path, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (device_id, mac, secret_sha256, token, hardware_type, owner_user_id,
         location_id, name, state_path, utc_now_iso()),
    )
    return device_id


def get_device_by_mac(conn: sqlite3.Connection, mac: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        "SELECT * FROM devices WHERE mac = ?", (mac,)
    ).fetchone()
    return row


def get_device_owner(conn: sqlite3.Connection, device_id: str) -> int | None:
    """The owner user id of a device, or None for an unknown id.

    Reads only `owner_user_id`; never a secret hash or token.
    """
    row = conn.execute(
        "SELECT owner_user_id FROM devices WHERE id = ?", (device_id,)
    ).fetchone()
    return None if row is None else int(row["owner_user_id"])


def list_devices(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Devices with owner email and location name; no token, no full hash."""
    return list(conn.execute(
        "SELECT d.id, d.mac, d.hardware_type, d.name, d.state_path, d.created_at, "
        "substr(d.secret_sha256, 1, ?) AS secret_prefix, "
        "u.email AS owner_email, l.name AS location_name "
        "FROM devices d JOIN users u ON u.id = d.owner_user_id "
        "LEFT JOIN locations l ON l.id = d.location_id ORDER BY d.created_at, d.id",
        (_SECRET_PREFIX_LEN,),
    ))


def remove_device(conn: sqlite3.Connection, mac: str) -> bool:
    return conn.execute("DELETE FROM devices WHERE mac = ?", (mac,)).rowcount > 0


def set_device_secret(conn: sqlite3.Connection, mac: str, secret_sha256: str) -> bool:
    _check_secret(secret_sha256)
    cur = conn.execute(
        "UPDATE devices SET secret_sha256 = ? WHERE mac = ?", (secret_sha256, mac)
    )
    return cur.rowcount > 0


def set_device_token(conn: sqlite3.Connection, mac: str, token: str | None) -> bool:
    cur = conn.execute("UPDATE devices SET token = ? WHERE mac = ?", (token, mac))
    return cur.rowcount > 0


def assign_owner(conn: sqlite3.Connection, mac: str, owner_user_id: int) -> bool:
    """Re-point the single owner; an unknown user raises IntegrityError."""
    cur = conn.execute(
        "UPDATE devices SET owner_user_id = ? WHERE mac = ?", (owner_user_id, mac)
    )
    return cur.rowcount > 0


def set_device_location(
    conn: sqlite3.Connection, mac: str, location_id: int | None
) -> bool:
    cur = conn.execute(
        "UPDATE devices SET location_id = ? WHERE mac = ?", (location_id, mac)
    )
    return cur.rowcount > 0


def tokens_by_mac(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT mac, token FROM devices WHERE token IS NOT NULL")
    return {str(r["mac"]): str(r["token"]) for r in rows}


def registry_view(conn: sqlite3.Connection) -> dict[str, dict[str, dict[str, str]]]:
    """Secret registry in the shape the byos server already consumes."""
    rows = conn.execute("SELECT mac, secret_sha256 FROM devices")
    return {
        "devices": {
            str(r["mac"]): {"secret_sha256": str(r["secret_sha256"])} for r in rows
        }
    }


def dump_logical(conn: sqlite3.Connection) -> list[str]:
    """The `iterdump()` statements, for logical-equality assertions."""
    return list(conn.iterdump())
