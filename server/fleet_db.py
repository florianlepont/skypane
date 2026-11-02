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
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

# Same repo-root sys.path bootstrap as server/history_db.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import atomic_io, device_dirs, hardware  # noqa: E402

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


class LastAdminError(FleetDbError):
    """The change would leave no active admin."""


class SelfActionError(FleetDbError):
    """A user may not demote or disable themselves."""


class LocationInUse(FleetDbError):
    """A device still references the location."""


class UnknownDevice(FleetDbError):
    """No frame has the given id."""


class IneligibleUser(FleetDbError):
    """The user cannot be added as a co-manager of the frame."""


class AlreadyCoManager(FleetDbError):
    """The user already co-manages the frame."""


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


def _migrate_v3(conn: sqlite3.Connection) -> None:
    # Expand-only: a new nullable column and two new tables. Existing
    # locations keep owner NULL (visible to admins only).
    conn.execute(
        "ALTER TABLE locations ADD COLUMN owner_user_id INTEGER REFERENCES users(id)"
    )
    conn.execute(
        "CREATE TABLE pending_devices ("
        " id TEXT PRIMARY KEY CHECK (id GLOB 'p_[0-9a-f][0-9a-f][0-9a-f][0-9a-f]"
        "[0-9a-f][0-9a-f][0-9a-f][0-9a-f]' AND length(id) = 10),"
        " mac TEXT NOT NULL UNIQUE,"
        " secret_sha256 TEXT NOT NULL,"
        " token TEXT,"
        " hardware_type TEXT NOT NULL,"
        " status TEXT NOT NULL DEFAULT 'pending'"
        " CHECK (status IN ('pending', 'retired')),"
        " code_salt TEXT,"
        " code_hash TEXT,"
        " code_expires_at INTEGER,"
        " last_seen_at INTEGER,"
        " battery_mv INTEGER,"
        " fw_version TEXT,"
        " created_at TEXT NOT NULL,"
        " created_by INTEGER,"
        " previous_owner_user_id INTEGER,"
        " previous_device_id TEXT,"
        " previous_state_path TEXT,"
        " previous_name TEXT,"
        " retired_at INTEGER)"
    )
    # No foreign key on the actor: the trail must outlive a user row.
    conn.execute(
        "CREATE TABLE audit_log ("
        " id INTEGER PRIMARY KEY,"
        " ts INTEGER NOT NULL,"
        " actor_user_id INTEGER,"
        " actor_label TEXT NOT NULL,"
        " action TEXT NOT NULL,"
        " target_type TEXT NOT NULL,"
        " target_id TEXT,"
        " outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'failed', 'denied')),"
        " source_ip TEXT,"
        " detail TEXT)"
    )
    conn.execute("CREATE INDEX audit_log_ts ON audit_log (ts DESC, id DESC)")
    for event in ("UPDATE", "DELETE"):
        conn.execute(
            f"CREATE TRIGGER audit_log_no_{event.lower()} BEFORE {event} ON audit_log "
            "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END"
        )


def _migrate_v4(conn: sqlite3.Connection) -> None:
    # Expand-only: one new table, one index and two triggers; no existing
    # table or row is touched. A frame owner is never also a co-manager of
    # that frame: the first trigger refuses such a membership row, the second
    # refuses handing ownership to someone who is already a co-manager. The
    # adder has no foreign key so the trail outlives a user row.
    conn.execute(
        "CREATE TABLE device_co_managers ("
        " device_id TEXT NOT NULL REFERENCES devices(id),"
        " user_id INTEGER NOT NULL REFERENCES users(id),"
        " added_by INTEGER,"
        " added_at INTEGER NOT NULL,"
        " PRIMARY KEY (device_id, user_id))"
    )
    conn.execute(
        "CREATE INDEX device_co_managers_user ON device_co_managers (user_id)"
    )
    conn.execute(
        "CREATE TRIGGER device_co_managers_not_owner "
        "BEFORE INSERT ON device_co_managers "
        "WHEN NEW.user_id = (SELECT owner_user_id FROM devices WHERE id = NEW.device_id) "
        "BEGIN SELECT RAISE(ABORT, 'a frame owner cannot be a co-manager'); END"
    )
    conn.execute(
        "CREATE TRIGGER devices_owner_not_co_manager "
        "BEFORE UPDATE OF owner_user_id ON devices "
        "WHEN EXISTS (SELECT 1 FROM device_co_managers "
        "WHERE device_id = NEW.id AND user_id = NEW.owner_user_id) "
        "BEGIN SELECT RAISE(ABORT, 'a co-manager cannot become the frame owner'); END"
    )


MIGRATIONS: tuple[Migration, ...] = (_migrate_v1, _migrate_v2, _migrate_v3, _migrate_v4)
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


def connect_readonly(state_dir: str, immutable: bool = False) -> sqlite3.Connection:
    """Read-only handle; never creates and never migrates.

    `immutable` skips locking and the WAL side files, which is the only way
    to read a database inside a directory that cannot be written. It is for
    that degraded case only: concurrent writers would go unseen.
    """
    path = fleet_db_path(state_dir)
    if not os.path.exists(path):
        raise FleetDbAbsent(path)
    uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
    if immutable:
        uri += "&immutable=1"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        _apply_pragmas(conn)
        _refuse_if_too_new(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def _state_dir_writable(state_dir: str) -> bool:
    return os.access(state_dir, os.W_OK)


def _wal_has_pending_data(state_dir: str) -> bool:
    """Whether the write-ahead log holds data not yet merged into the main
    file. A log that cannot be inspected counts as pending.
    """
    try:
        return os.path.getsize(fleet_db_path(state_dir) + "-wal") > 0
    except FileNotFoundError:
        return False
    except OSError:
        return True


def connect_readonly_fallback(state_dir: str) -> sqlite3.Connection | None:
    """The degraded read for a state directory that cannot be written, or
    None when the caller should surface the original connect error: the
    directory is writable, or a pending write-ahead log means an immutable
    read would skip revocations and demotions and serve a revoked session.
    Prints one line (no secrets) whenever it engages or refuses.
    """
    if _state_dir_writable(state_dir):
        return None
    if _wal_has_pending_data(state_dir):
        print("companion: fleet.db read-only fallback refused: "
              "write-ahead log has unmerged data", flush=True)
        return None
    print("companion: fleet.db state directory is not writable; "
          "reading sessions from the main file only", flush=True)
    return connect_readonly(state_dir, immutable=True)


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


@contextlib.contextmanager
def _atomic(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Join the caller's transaction, or open one when none is active, so a
    check-then-write helper is never run without the write lock held.
    """
    if conn.in_transaction:
        yield conn
        return
    with transaction(conn):
        yield conn


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


def count_active_admins(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT count(*) FROM users WHERE role = 'admin' AND disabled = 0"
    ).fetchone()
    return int(row[0])


def _is_active_admin(conn: sqlite3.Connection, user_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM users WHERE id = ? AND role = 'admin' AND disabled = 0",
        (user_id,),
    ).fetchone() is not None


def set_user_role_guarded(
    conn: sqlite3.Connection, actor_user_id: int | None, target_user_id: int, role: str
) -> bool:
    """Change a role; False for an unknown user.

    Raises SelfActionError when an actor demotes themselves and
    LastAdminError when the target is the only active admin. The count and
    the write share one transaction.
    """
    if role not in ROLES:
        raise ValueError(f"invalid role: {role!r}")
    with _atomic(conn):
        if role != "admin":
            if actor_user_id is not None and actor_user_id == target_user_id:
                raise SelfActionError("cannot demote yourself")
            if _is_active_admin(conn, target_user_id) and count_active_admins(conn) <= 1:
                raise LastAdminError("cannot demote the last active admin")
        cur = conn.execute(
            "UPDATE users SET role = ? WHERE id = ?", (role, target_user_id)
        )
        return cur.rowcount > 0


def set_user_disabled_guarded(
    conn: sqlite3.Connection,
    actor_user_id: int | None,
    target_user_id: int,
    disabled: bool,
) -> bool:
    """Disable or re-enable a user; False for an unknown user.

    Disabling deletes the user's sessions in the same transaction (this
    module is a leaf and cannot call the session store). The same
    self-action and last-admin refusals as `set_user_role_guarded` apply.
    """
    with _atomic(conn):
        if disabled:
            if actor_user_id is not None and actor_user_id == target_user_id:
                raise SelfActionError("cannot disable yourself")
            if _is_active_admin(conn, target_user_id) and count_active_admins(conn) <= 1:
                raise LastAdminError("cannot disable the last active admin")
        cur = conn.execute(
            "UPDATE users SET disabled = ? WHERE id = ?",
            (1 if disabled else 0, target_user_id),
        )
        if cur.rowcount > 0 and disabled:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (target_user_id,))
        return cur.rowcount > 0


def list_users_with_frame_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Users with owned-frame count, newest session activity and whether an
    identity has signed in (iss and sub set). Never the issuer or subject.
    """
    return list(conn.execute(
        "SELECT u.id, u.email, u.role, u.disabled, u.created_at, "
        "(SELECT count(*) FROM devices d WHERE d.owner_user_id = u.id) AS frame_count, "
        "(SELECT max(s.last_seen_at) FROM sessions s WHERE s.user_id = u.id) "
        "AS last_seen_at, "
        "(u.iss IS NOT NULL AND u.sub IS NOT NULL) AS has_identity "
        "FROM users u ORDER BY u.id"
    ))


# ---- locations -------------------------------------------------------


def _validate_location(name: str, latitude: float, longitude: float, tz: str) -> None:
    if not name.strip():
        raise ValueError("location name is empty")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"latitude out of range: {latitude}")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"longitude out of range: {longitude}")
    try:
        ZoneInfo(tz)
    except (KeyError, ValueError, OSError) as exc:
        raise ValueError(f"unknown timezone: {tz!r}") from exc


def add_location(
    conn: sqlite3.Connection,
    name: str,
    latitude: float,
    longitude: float,
    timezone: str,
    owner_user_id: int | None = None,
) -> int:
    """Insert a location; latitude/longitude are degrees, timezone an IANA name.

    A NULL owner (the default, and every pre-existing row) is visible to
    admins only.
    """
    _validate_location(name, latitude, longitude, timezone)
    cur = conn.execute(
        "INSERT INTO locations (name, latitude, longitude, timezone, owner_user_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, latitude, longitude, timezone, owner_user_id),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def list_locations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM locations ORDER BY id"))


def get_location(conn: sqlite3.Connection, location_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        "SELECT * FROM locations WHERE id = ?", (location_id,)
    ).fetchone()
    return row


def list_locations_for(
    conn: sqlite3.Connection, user_id: int, is_admin: bool
) -> list[sqlite3.Row]:
    """All locations for an admin; only the user's own for everyone else."""
    if is_admin:
        return list_locations(conn)
    return list(conn.execute(
        "SELECT * FROM locations WHERE owner_user_id = ? ORDER BY id", (user_id,)
    ))


def update_location(
    conn: sqlite3.Connection,
    location_id: int,
    name: str,
    latitude: float,
    longitude: float,
    timezone: str,
) -> bool:
    """Rewrite a location's name, position and timezone; False when unknown."""
    _validate_location(name, latitude, longitude, timezone)
    cur = conn.execute(
        "UPDATE locations SET name = ?, latitude = ?, longitude = ?, timezone = ? "
        "WHERE id = ?",
        (name, latitude, longitude, timezone, location_id),
    )
    return cur.rowcount > 0


def delete_location_if_unused(conn: sqlite3.Connection, location_id: int) -> bool:
    """Delete a location no device uses. Raises LocationInUse when one does;
    False for an unknown id. Run inside the caller's transaction so the
    check and the delete cannot interleave with an assignment.
    """
    with _atomic(conn):
        if conn.execute(
            "SELECT 1 FROM devices WHERE location_id = ?", (location_id,)
        ).fetchone():
            raise LocationInUse(location_id)
        return conn.execute(
            "DELETE FROM locations WHERE id = ?", (location_id,)
        ).rowcount > 0


def count_locations_owned(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT count(*) FROM locations WHERE owner_user_id = ?", (user_id,)
    ).fetchone()
    return int(row[0])


def location_usage_counts(
    conn: sqlite3.Connection, owner_user_id: int | None = None
) -> dict[int, int]:
    """Devices per location id (locations no device uses are absent).

    With `owner_user_id`, only that user's devices are counted, so a viewer
    never learns how many frames of other owners use a location.
    """
    where = "location_id IS NOT NULL"
    args: tuple[int, ...] = ()
    if owner_user_id is not None:
        where += " AND owner_user_id = ?"
        args = (owner_user_id,)
    rows = conn.execute(
        "SELECT location_id, count(*) AS n FROM devices WHERE "
        + where + " GROUP BY location_id",
        args,
    )
    return {int(r["location_id"]): int(r["n"]) for r in rows}


def set_device_location_checked(
    conn: sqlite3.Connection,
    device_id: str,
    location_id: int | None,
    actor_user_id: int | None,
    is_admin: bool,
) -> bool:
    """Assign (or clear, with None) a device's location with owner checks.

    A user who owns or co-manages the device may assign only a location owned
    by the device owner. An admin may assign any location except one owned by
    a different user than the device owner; a location or device without an
    owner links to anything. Anything else raises PermissionError; an unknown
    device returns False.
    """
    with _atomic(conn):
        device = conn.execute(
            "SELECT owner_user_id FROM devices WHERE id = ?", (device_id,)
        ).fetchone()
        if device is None:
            return False
        if not is_admin and (
            actor_user_id is None
            or (
                device["owner_user_id"] != actor_user_id
                and not is_co_manager(conn, device_id, actor_user_id)
            )
        ):
            raise PermissionError("device is not managed by the acting user")
        if location_id is not None:
            loc = get_location(conn, location_id)
            if loc is None:
                if is_admin:
                    raise ValueError(f"unknown location: {location_id}")
                raise PermissionError("location is not owned by the device owner")
            if not is_admin and loc["owner_user_id"] != device["owner_user_id"]:
                raise PermissionError("location is not owned by the device owner")
            location_owner = loc["owner_user_id"]
            if (
                location_owner is not None
                and device["owner_user_id"] is not None
                and location_owner != device["owner_user_id"]
            ):
                raise PermissionError("location belongs to another owner")
        conn.execute(
            "UPDATE devices SET location_id = ? WHERE id = ?", (location_id, device_id)
        )
        return True


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
    allow_shared_live: bool = False,
) -> str:
    """Insert a device and return its opaque id (`d_` plus 8 hex).

    The owner is mandatory: a missing or unknown owner raises
    sqlite3.IntegrityError. The hardware type must be available under the
    simulation gate in `environ`; reading existing rows never consults it.

    `state_path` is either "." (the live frame, the default) or "auto",
    which stores `devices/<the generated id>`. Any other value raises
    ValueError before the INSERT: a stored path becomes a directory the
    services read and write, and a hand-built `devices/<id>` could name
    another device's directory. Reads re-validate through
    `device_dirs.resolve_state_dir`, so an edited row cannot escape either.

    Only one device may use "." (the live frame's state is the state root,
    so a second one would share its image, history and battery): a second
    "." row raises ValueError and the caller must pass "auto". The import
    of a legacy registry sets `allow_shared_live`, because the previous
    release already served every registered MAC from the root.
    """
    _check_mac(mac)
    _check_secret(secret_sha256)
    if state_path not in (device_dirs.LIVE_STATE_PATH, "auto"):
        raise ValueError(f"state_path must be '.' or 'auto': {state_path!r}")
    hardware.get_profile(hardware_type, environ)
    if conn.execute("SELECT 1 FROM pending_devices WHERE mac = ?", (mac,)).fetchone():
        raise ValueError("MAC is already registered as a pending frame")
    if (
        state_path == device_dirs.LIVE_STATE_PATH
        and not allow_shared_live
        and conn.execute("SELECT 1 FROM devices WHERE state_path = ?", (state_path,)).fetchone()
        is not None
    ):
        raise ValueError(
            "a device already uses the live state path '.'; "
            "add further devices with state_path 'auto'"
        )
    while True:
        device_id = "d_" + secrets.token_hex(4)
        if conn.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone() is None:
            break
    if state_path == "auto":
        state_path = device_dirs.state_path_for(device_id)
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


def get_device(conn: sqlite3.Connection, device_id: str) -> sqlite3.Row | None:
    """One device by id; never a secret hash or token."""
    row: sqlite3.Row | None = conn.execute(
        "SELECT id, mac, hardware_type, name, state_path, owner_user_id, "
        "location_id, created_at FROM devices WHERE id = ?",
        (device_id,),
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
        "u.email AS owner_email, l.name AS location_name, d.owner_user_id "
        "FROM devices d JOIN users u ON u.id = d.owner_user_id "
        "LEFT JOIN locations l ON l.id = d.location_id ORDER BY d.created_at, d.id",
        (_SECRET_PREFIX_LEN,),
    ))


def device_coordinates(conn: sqlite3.Connection) -> dict[str, tuple[float, float]]:
    """Device id -> (latitude, longitude) of its own assigned location.

    Devices without a location are absent. Reads only coordinates, so the
    poll cycle never touches owner or secret columns.
    """
    rows = conn.execute(
        "SELECT d.id AS id, l.latitude AS lat, l.longitude AS lon "
        "FROM devices d JOIN locations l ON l.id = d.location_id"
    )
    return {str(r["id"]): (float(r["lat"]), float(r["lon"])) for r in rows}


def remove_device(
    conn: sqlite3.Connection, mac: str, actor: AuditActor | None = None
) -> bool:
    """Hard-delete a frame by MAC, clearing and auditing its co-managers first."""
    with _atomic(conn):
        row = conn.execute("SELECT id FROM devices WHERE mac = ?", (mac,)).fetchone()
        if row is not None:
            removed = clear_co_managers(conn, str(row["id"]))
            audit_co_manager_removals(
                conn, actor or AuditActor(None, "system", None),
                str(row["id"]), removed, "delete",
            )
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


# ---- co-managers -----------------------------------------------------

# A user can be added to a frame when invited (a users row exists), not
# disabled, and neither the frame owner nor already a co-manager. Admins and
# users who never signed in qualify.
_ELIGIBLE_SQL = (
    "FROM users u WHERE u.disabled = 0 "
    "AND u.id <> (SELECT owner_user_id FROM devices WHERE id = :device) "
    "AND NOT EXISTS (SELECT 1 FROM device_co_managers c "
    "WHERE c.device_id = :device AND c.user_id = u.id)"
)


def is_co_manager(conn: sqlite3.Connection, device_id: str, user_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM device_co_managers WHERE device_id = ? AND user_id = ?",
        (device_id, user_id),
    ).fetchone()
    return row is not None


def list_co_managers(conn: sqlite3.Connection, device_id: str) -> list[sqlite3.Row]:
    """Co-managers of a frame, disabled ones included, ordered by e-mail."""
    return list(conn.execute(
        "SELECT c.user_id, u.email, u.disabled, c.added_at "
        "FROM device_co_managers c JOIN users u ON u.id = c.user_id "
        "WHERE c.device_id = ? ORDER BY lower(u.email), c.user_id",
        (device_id,),
    ))


def co_managed_device_ids(conn: sqlite3.Connection, user_id: int) -> set[str]:
    return {
        str(r["device_id"]) for r in conn.execute(
            "SELECT device_id FROM device_co_managers WHERE user_id = ?", (user_id,)
        )
    }


def add_co_manager(
    conn: sqlite3.Connection,
    device_id: str,
    user_id: int,
    added_by: int | None,
    now: int | None = None,
) -> None:
    """Add a co-manager; eligibility is checked inside the write transaction."""
    with _atomic(conn):
        owner = conn.execute(
            "SELECT owner_user_id FROM devices WHERE id = ?", (device_id,)
        ).fetchone()
        if owner is None:
            raise UnknownDevice(device_id)
        user = conn.execute(
            "SELECT disabled FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None or user["disabled"] or user_id == owner["owner_user_id"]:
            raise IneligibleUser("user cannot co-manage this frame")
        if is_co_manager(conn, device_id, user_id):
            raise AlreadyCoManager("user already co-manages this frame")
        conn.execute(
            "INSERT INTO device_co_managers (device_id, user_id, added_by, added_at) "
            "VALUES (?, ?, ?, ?)",
            (device_id, user_id, added_by, int(time.time()) if now is None else now),
        )


def remove_co_manager(conn: sqlite3.Connection, device_id: str, user_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM device_co_managers WHERE device_id = ? AND user_id = ?",
        (device_id, user_id),
    )
    return cur.rowcount > 0


def clear_co_managers(conn: sqlite3.Connection, device_id: str) -> list[int]:
    """Remove every co-manager of a frame; returns the removed user ids."""
    with _atomic(conn):
        ids = [
            int(r["user_id"]) for r in conn.execute(
                "SELECT user_id FROM device_co_managers WHERE device_id = ? "
                "ORDER BY user_id", (device_id,)
            )
        ]
        conn.execute("DELETE FROM device_co_managers WHERE device_id = ?", (device_id,))
    return ids


def eligible_co_manager_candidates(
    conn: sqlite3.Connection, device_id: str
) -> list[sqlite3.Row]:
    """Users who could be added to the frame, ordered by e-mail."""
    return list(conn.execute(
        f"SELECT u.id, u.email {_ELIGIBLE_SQL} ORDER BY lower(u.email), u.id",
        {"device": device_id},
    ))


def find_eligible_co_manager(
    conn: sqlite3.Connection, device_id: str, email: str
) -> int | None:
    """The user id for an eligible address, or None for any other outcome."""
    try:
        normalized = normalize_email(email)
    except ValueError:
        return None
    row = conn.execute(
        f"SELECT u.id {_ELIGIBLE_SQL} AND u.email = :email",
        {"device": device_id, "email": normalized},
    ).fetchone()
    return None if row is None else int(row["id"])


def dump_logical(conn: sqlite3.Connection) -> list[str]:
    """The `iterdump()` statements, for logical-equality assertions."""
    return list(conn.iterdump())


# ---- audit log -------------------------------------------------------

_AUDIT_DETAIL_MAX = 1000

ACTION_CO_MANAGER_ADD = "device.co_manager_add"
ACTION_CO_MANAGER_REMOVE = "device.co_manager_remove"

# UI filter chips mapped to action prefixes; "failed" is by outcome instead.
AUDIT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "all": (),
    "pairing": ("pairing.",),
    "frames": ("frame.", "device."),
    "users": ("user.",),
    "locations": ("location.",),
    "releases": ("release.",),
    "failed": (),
}


class AuditActor(NamedTuple):
    """Who performed an audited action; `user_id` is None for the legacy
    admin or a system actor.
    """

    user_id: int | None
    label: str
    source_ip: str | None


def audit_append(
    conn: sqlite3.Connection,
    actor: AuditActor,
    action: str,
    target_type: str,
    target_id: str | None,
    outcome: str,
    detail: Mapping[str, object] | None = None,
    now: int | None = None,
) -> int:
    """Insert one audit row in the caller's transaction and return its id.

    `detail` is a mapping of non-secret facts, stored as JSON truncated to
    1000 characters. Codes, secrets, tokens and guesses have no parameter.
    """
    if outcome not in ("ok", "failed", "denied"):
        raise ValueError(f"invalid audit outcome: {outcome!r}")
    text: str | None = None
    if detail is not None:
        text = json.dumps(dict(detail), sort_keys=True, default=str)[:_AUDIT_DETAIL_MAX]
    ts = int(time.time()) if now is None else now
    cur = conn.execute(
        "INSERT INTO audit_log (ts, actor_user_id, actor_label, action, "
        "target_type, target_id, outcome, source_ip, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ts, actor.user_id, actor.label, action, target_type, target_id,
         outcome, actor.source_ip, text),
    )
    assert cur.lastrowid is not None
    return cur.lastrowid


def audit_co_manager_removals(
    conn: sqlite3.Connection,
    actor: AuditActor,
    device_id: str,
    user_ids: Iterable[int],
    via: str,
) -> None:
    """One audit row per co-manager removed by a wider operation."""
    for user_id in user_ids:
        audit_append(
            conn, actor, ACTION_CO_MANAGER_REMOVE, "device", device_id, "ok",
            {"co_manager_user_id": user_id, "via": via},
        )


def _audit_where(category: str) -> tuple[str, tuple[str, ...]]:
    if category not in AUDIT_CATEGORIES:
        raise ValueError(f"unknown audit category: {category!r}")
    if category == "all":
        return "", ()
    if category == "failed":
        return " WHERE outcome != 'ok'", ()
    prefixes = AUDIT_CATEGORIES[category]
    clause = " OR ".join("substr(action, 1, ?) = ?" for _ in prefixes)
    params: list[str] = []
    for prefix in prefixes:
        params.extend((str(len(prefix)), prefix))
    return f" WHERE ({clause})", tuple(params)


def list_audit(
    conn: sqlite3.Connection, category: str, limit: int, offset: int
) -> list[sqlite3.Row]:
    """Audit rows newest first for a category chip."""
    where, params = _audit_where(category)
    return list(conn.execute(
        "SELECT * FROM audit_log" + where + " ORDER BY ts DESC, id DESC LIMIT ? OFFSET ?",
        (*params, int(limit), int(offset)),
    ))


def count_audit(conn: sqlite3.Connection, category: str) -> int:
    where, params = _audit_where(category)
    row = conn.execute("SELECT count(*) FROM audit_log" + where, params).fetchone()
    return int(row[0])


# ---- pending devices -------------------------------------------------

PENDING_STATUS_PENDING = "pending"
PENDING_STATUS_RETIRED = "retired"
PENDING_ID_RE = re.compile(r"\Ap_[0-9a-f]{8}\Z")

# Listing columns: never the secret hash, token, code salt or code hash.
_PENDING_LIST_COLS = (
    "id, mac, hardware_type, status, code_expires_at, last_seen_at, battery_mv, "
    "fw_version, created_at, created_by, previous_owner_user_id, "
    "previous_device_id, previous_state_path, previous_name, retired_at, "
    "(code_hash IS NOT NULL) AS has_code"
)


def new_pending_id(conn: sqlite3.Connection | None = None) -> str:
    """A fresh `p_` plus 8 hex id; unused in `conn` when one is given."""
    while True:
        pending_id = "p_" + secrets.token_hex(4)
        if conn is None or conn.execute(
            "SELECT 1 FROM pending_devices WHERE id = ?", (pending_id,)
        ).fetchone() is None:
            return pending_id


def register_pending(
    conn: sqlite3.Connection,
    mac: str,
    secret_sha256: str,
    hardware_type: str,
    created_by: int | None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Insert a pending frame and return its id. Only the secret's sha256 is
    accepted; a MAC already in `devices` or `pending_devices` raises
    ValueError.
    """
    _check_mac(mac)
    _check_secret(secret_sha256)
    hardware.get_profile(hardware_type, environ)
    with _atomic(conn):
        if conn.execute("SELECT 1 FROM devices WHERE mac = ?", (mac,)).fetchone():
            raise ValueError("MAC is already a registered frame")
        if conn.execute("SELECT 1 FROM pending_devices WHERE mac = ?", (mac,)).fetchone():
            raise ValueError("MAC is already pending")
        pending_id = new_pending_id(conn)
        conn.execute(
            "INSERT INTO pending_devices (id, mac, secret_sha256, hardware_type, "
            "status, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pending_id, mac, secret_sha256, hardware_type,
             PENDING_STATUS_PENDING, utc_now_iso(), created_by),
        )
    return pending_id


# The code columns are included for single-row lookups (the pairing check
# needs the salt and hash); the secret hash and token never are.
_PENDING_GET_COLS = _PENDING_LIST_COLS + ", code_salt, code_hash"


def get_pending(conn: sqlite3.Connection, pending_id: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        f"SELECT {_PENDING_GET_COLS} FROM pending_devices WHERE id = ?", (pending_id,)
    ).fetchone()
    return row


def get_pending_by_mac(conn: sqlite3.Connection, mac: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        f"SELECT {_PENDING_GET_COLS} FROM pending_devices WHERE mac = ?", (mac,)
    ).fetchone()
    return row


def list_pending(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute(
        f"SELECT {_PENDING_LIST_COLS} FROM pending_devices ORDER BY created_at, id"
    ))


def set_pending_token(conn: sqlite3.Connection, mac: str, token: str | None) -> bool:
    cur = conn.execute("UPDATE pending_devices SET token = ? WHERE mac = ?", (token, mac))
    return cur.rowcount > 0


def issue_pending_code(
    conn: sqlite3.Connection,
    pending_id: str,
    code_salt: str,
    code_hash: str,
    expires_at: int,
) -> bool:
    """Store a pairing code as salt, hash and an epoch-seconds expiry."""
    cur = conn.execute(
        "UPDATE pending_devices SET code_salt = ?, code_hash = ?, code_expires_at = ? "
        "WHERE id = ?",
        (code_salt, code_hash, expires_at, pending_id),
    )
    return cur.rowcount > 0


def clear_pending_code(conn: sqlite3.Connection, pending_id: str) -> bool:
    cur = conn.execute(
        "UPDATE pending_devices SET code_salt = NULL, code_hash = NULL, "
        "code_expires_at = NULL WHERE id = ?",
        (pending_id,),
    )
    return cur.rowcount > 0


def touch_pending(
    conn: sqlite3.Connection,
    pending_id: str,
    now: int,
    battery_mv: int | None,
    fw_version: str | None,
) -> bool:
    """Record a check-in: epoch seconds, battery in millivolts, firmware."""
    cur = conn.execute(
        "UPDATE pending_devices SET last_seen_at = ?, battery_mv = ?, fw_version = ? "
        "WHERE id = ?",
        (now, battery_mv, fw_version, pending_id),
    )
    return cur.rowcount > 0


def delete_pending(conn: sqlite3.Connection, pending_id: str) -> bool:
    return conn.execute(
        "DELETE FROM pending_devices WHERE id = ?", (pending_id,)
    ).rowcount > 0


def pending_registry_view(conn: sqlite3.Connection) -> dict[str, dict[str, dict[str, str]]]:
    """Same shape as `registry_view`, over pending and retired rows."""
    rows = conn.execute("SELECT mac, secret_sha256 FROM pending_devices")
    return {
        "devices": {
            str(r["mac"]): {"secret_sha256": str(r["secret_sha256"])} for r in rows
        }
    }


def pending_tokens_by_mac(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT mac, token FROM pending_devices WHERE token IS NOT NULL")
    return {str(r["mac"]): str(r["token"]) for r in rows}


def park_retired(conn: sqlite3.Connection, device_id: str, now: int) -> str | None:
    """Move a registered frame to a retired pending row in one transaction.

    The MAC, secret hash, token and hardware type carry over, and the
    previous owner, device id, state path and name are kept for the audit
    trail. Returns the new pending id, or None for an unknown device. The
    live-frame guard belongs to the caller.
    """
    with _atomic(conn):
        dev = conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if dev is None:
            return None
        # Membership rows reference the device; clear them before the delete.
        clear_co_managers(conn, device_id)
        conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        pending_id = new_pending_id(conn)
        conn.execute(
            "INSERT INTO pending_devices (id, mac, secret_sha256, token, hardware_type, "
            "status, created_at, previous_owner_user_id, previous_device_id, "
            "previous_state_path, previous_name, retired_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pending_id, dev["mac"], dev["secret_sha256"], dev["token"],
             dev["hardware_type"], PENDING_STATUS_RETIRED, utc_now_iso(),
             dev["owner_user_id"], dev["id"], dev["state_path"], dev["name"], now),
        )
        return pending_id


def reactivate_pending(conn: sqlite3.Connection, pending_id: str) -> bool:
    """Bring a retired row back to pending with its code cleared."""
    cur = conn.execute(
        "UPDATE pending_devices SET status = ?, code_salt = NULL, code_hash = NULL, "
        "code_expires_at = NULL WHERE id = ?",
        (PENDING_STATUS_PENDING, pending_id),
    )
    return cur.rowcount > 0
