#!/usr/bin/env python3
"""SQLite history store behind the health trend, the flight log, and
resolution statistics, plus the Caddy access-log tailer that is the only
permitted path to device battery telemetry.

Leaf module: stdlib only, must never import `device_config`,
`server.plane.detect`, `server.plane.render`, or `server.poll_loop`.

Cadence rule: `runway_events` rows are written only on a real transition (an
aircraft drawn, or detected and dropped before it could be), never once per
30-second cycle - the always-changing "pipeline last ran"
signal lives in the fixed-size `meta` table instead, so keep-forever
retention doesn't turn into unbounded per-cycle row growth. The one
per-cycle trace, `poll_cycles`, only records cycles that saw, queued,
dropped or drew an aircraft and is pruned to `POLL_CYCLE_RETENTION_DAYS`.

Concurrency: `connection_scope(state_dir)` gives every `open_db()` call on
the same thread inside it one lazily-opened connection, closed only once
the outermost scope exits; outside any scope `open_db()` keeps its own
open-per-call behaviour. Every connection sets `PRAGMA busy_timeout=5000`;
`PRAGMA journal_mode=WAL` and the schema run once per process for a given
database file identity, not once per connection. A concurrent
poll-oneshot write and a companion read still just wait briefly on a lock
instead of raising "database is locked".
"""
import contextlib
import json
import os
import pathlib
import re
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Same repo-root sys.path bootstrap as server/poll_loop.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import sqlite_migrations  # noqa: E402
from server.wake_stats import WAKE_COLUMNS, parse_wake_stats  # noqa: E402

HISTORY_DB_FILENAME = "history.db"

# Fixed-size per-cycle signals - constant storage regardless of cycle count.
META_LAST_PIPELINE_RUN = "last_pipeline_run"
META_LAST_DETECTION = "last_detection"
META_SOURCE_FAULT = "source_fault"
META_CADDY_LOG_OFFSET = "caddy_log_offset"
META_LAST_POLL_TRIGGER = "last_poll_trigger"

# Prefix for one meta key per ADS-B provider name (e.g.
# "provider_last_call:adsbfi"), holding that provider's own last-call
# epoch as a float string. Fixed-size regardless of cycle count: one row
# per provider, updated in place, never appended. Lives here rather than
# in poll_state.json so concurrent processes
# share the same bookkeeping across process boundaries without perturbing
# poll_state.json's own "only write when content changes" contract.
META_PROVIDER_LAST_CALL_PREFIX = "provider_last_call:"

# `poll_cycles` keeps this many days: a few hundred rows a day, enough to
# explain a missed flight after the weekend without growing without bound.
POLL_CYCLE_RETENTION_DAYS = 14

# Columns of one `poll_cycles` row, in storage order after `id` and `ts`.
POLL_CYCLE_COLUMNS = (
    "branch", "detected_hex", "detected_callsign", "detected_altitude_ft",
    "detected_rate_fpm", "detected_on_ground", "shown_hex", "shown_callsign",
    "confirmed_state", "render_state", "state_source", "pending",
    "pending_hexes", "dropped", "redraw_blocked", "panel_changed",
    "source_fault", "tracked_runway",
)

_RUNWAY_EVENT_COLUMNS = (
    "ts", "hex", "callsign", "aircraft_type", "confirmed_state",
    "corroborated", "route_source", "airline", "origin", "destination",
    "tracked_runway", "gallery_name", "route_directory",
)

_RUNWAY_EVENT_INSERT_SQL = (
    "INSERT INTO runway_events "
    "(" + ", ".join(_RUNWAY_EVENT_COLUMNS) + ") "
    "VALUES (" + ", ".join("?" * len(_RUNWAY_EVENT_COLUMNS)) + ")"
)

# `PRAGMA user_version` of history.db. 0 is a database created before the
# route-directory counters; 1 has the `route_lookups` table and the
# `runway_events.route_directory` column. `init_schema()` raises the stamp
# once the steps for it are done and never lowers it.
HISTORY_SCHEMA_VERSION = 1

# The route directories `route_lookups` counts, and what a lookup can end in.
ROUTE_DIRECTORIES = ("vrs", "adsbdb")
ROUTE_LOOKUP_OUTCOMES = ("found", "none", "failed")

# `route_lookups` keeps this many days of requests.
ROUTE_LOOKUP_RETENTION_DAYS = 14

_DEVICE_HEALTH_OLD_COLUMNS = ("ts", "battery_mv", "fw_version", "boot_reason", "rssi")

_DEVICE_HEALTH_INSERT_SQL = (
    "INSERT OR IGNORE INTO device_health ("
    + ", ".join(_DEVICE_HEALTH_OLD_COLUMNS + WAKE_COLUMNS)
    + ") VALUES ("
    + ", ".join("?" * (len(_DEVICE_HEALTH_OLD_COLUMNS) + len(WAKE_COLUMNS)))
    + ")"
)

_META_UPSERT_SQL = (
    "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)"
)

# The only header names ever extracted from a Caddy access-log line -
# indexed one at a time, the header map never copied wholesale, so a
# future Caddy config that stops redacting Authorization/Cookie can't
# leak a credential into history.db. X-Wake-Stats is stored only through
# `parse_wake_stats`, never as raw text.
_TELEMETRY_HEADER_ALLOWLIST = (
    "X-Fw-Version", "X-Boot-Reason", "X-Rssi", "X-Battery-Mv", "X-Wake-Stats",
)

# Wake columns added to `device_health` after the first release; every one
# is nullable, only `prev_outcome` is text.
_WAKE_COLUMN_TYPES = {
    column: ("TEXT" if column == "prev_outcome" else "INTEGER")
    for column in WAKE_COLUMNS
}

DEVICE_DISPLAY_URI = "/device/v1/display"


def utc_now_iso():
    """Timezone-aware UTC ISO-8601 string at seconds precision, matching
    enrich.note_unresolved_prefix()'s format so the two stores sort
    consistently.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def history_db_path(state_dir):
    return os.path.join(state_dir, HISTORY_DB_FILENAME)


def _create_initial_schema(conn):
    """Create all six tables with IF NOT EXISTS and add the additive
    nullable columns by guarded ALTER TABLE
    (`_add_missing_wake_columns`, `_add_missing_runway_event_columns`).
    Idempotent and safe while another process uses the file.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runway_events ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "hex TEXT, "
        "callsign TEXT, "
        "aircraft_type TEXT, "
        "confirmed_state TEXT, "
        # Stored as TEXT ("True"/"False"/"None"): SQLite has no tri-state
        # boolean, and collapsing "unknown" into false would lose it.
        "corroborated TEXT, "
        "route_source TEXT, "
        "airline TEXT, "
        "origin TEXT, "
        "destination TEXT, "
        "tracked_runway TEXT, "
        # The archived render the frame showed for this flight: NULL for a row
        # written before the column existed (unknown), "" when the cycle that
        # recorded the flight archived no render, else the gallery file name.
        "gallery_name TEXT, "
        # Which route directory supplied the route shown: "vrs" or "adsbdb",
        # NULL when neither did and for a row from before the column.
        "route_directory TEXT"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runway_events_ts ON runway_events(ts)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS device_health ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "battery_mv INTEGER, "
        "fw_version TEXT, "
        "boot_reason TEXT, "
        "rssi TEXT, "
        # A re-tail of an overlapping log range can't double-count:
        # inserts use INSERT OR IGNORE against this constraint.
        "UNIQUE(ts, battery_mv)"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_device_health_ts ON device_health(ts)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL, "
        "updated_at TEXT NOT NULL"
        ")"
    )
    # One row per CHANGE in the device's effective wake interval, added as
    # a table because it is a change log, not a per-wake reading, so it has
    # no `device_health` row to hang off. Nullable on
    # purpose: a NULL epoch records "cadence undetermined from here",
    # never lets a reader infer the previous interval silently continued.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wake_epochs ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "wake_interval_s INTEGER"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS poll_cycles ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "branch TEXT, "
        "detected_hex TEXT, "
        "detected_callsign TEXT, "
        "detected_altitude_ft REAL, "
        "detected_rate_fpm REAL, "
        "detected_on_ground INTEGER, "
        "shown_hex TEXT, "
        "shown_callsign TEXT, "
        "confirmed_state TEXT, "
        "render_state TEXT, "
        "state_source TEXT, "
        "pending INTEGER, "
        "pending_hexes TEXT, "
        "dropped TEXT, "
        "redraw_blocked INTEGER, "
        "panel_changed INTEGER, "
        "source_fault INTEGER, "
        "tracked_runway TEXT"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_poll_cycles_ts ON poll_cycles(ts)")
    _create_route_lookups(conn)
    _add_missing_wake_columns(conn)
    _add_missing_runway_event_columns(conn)


def _create_route_lookups(conn):
    # One row per request that really went to a route directory (a cache hit
    # makes none): when, which directory, and how it ended. Counts and times
    # only, no callsign.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS route_lookups ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "directory TEXT NOT NULL, "
        "outcome TEXT NOT NULL"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_route_lookups_ts ON route_lookups(ts)")


def _add_missing_wake_columns(conn):
    """Add each wake column `device_health` lacks. The companion and the
    poll oneshot can both reach this on the same file: a "duplicate column
    name" error means the other process added it between the column read
    and the ALTER, which counts as done. Any other error propagates.
    """
    for column, sql_type in _WAKE_COLUMN_TYPES.items():
        sqlite_migrations.add_column_if_missing(
            conn, "device_health", column, sql_type)


_RUNWAY_EVENT_ADDED_COLUMNS = ("gallery_name", "route_directory")


def _add_missing_runway_event_columns(conn):
    """Add the `runway_events` columns a database created before them lacks
    (an existing row reads NULL, "unknown"). Same race handling as
    `_add_missing_wake_columns`."""
    for column in _RUNWAY_EVENT_ADDED_COLUMNS:
        sqlite_migrations.add_column_if_missing(
            conn, "runway_events", column, "TEXT")


_HISTORY_TABLES = (
    "runway_events", "device_health", "meta", "wake_epochs", "poll_cycles",
    "route_lookups",
)


def _initial_schema_impact(conn):
    """What `_create_initial_schema` would still change in `conn`'s file, as
    counts (read-only, used by the schema report)."""
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing_tables = sum(1 for name in _HISTORY_TABLES if name not in tables)
    missing_columns = 0
    for table, wanted in (
        ("device_health", tuple(_WAKE_COLUMN_TYPES)),
        ("runway_events", _RUNWAY_EVENT_ADDED_COLUMNS),
    ):
        if table in tables:
            # `table` comes from the fixed pairs above, never from input.
            present = {row[1] for row in conn.execute(
                "PRAGMA table_info(" + table + ")")}
            missing_columns += sum(1 for name in wanted if name not in present)
    return "creates-tables:%d,adds-columns:%d" % (missing_tables, missing_columns)


HISTORY_STEPS = (
    sqlite_migrations.Step(
        HISTORY_SCHEMA_VERSION, "initial-schema", _create_initial_schema,
        _initial_schema_impact),
)

# Idempotent and race-tolerant: the companion and the poll oneshot can open
# a fresh file at the same moment, and a newer stamp is kept, never refused.
HISTORY_POLICY = sqlite_migrations.Policy(
    locking="idempotent", newer="keep", error=sqlite3.Error, label="history.db")


def init_schema(conn):
    """Create or complete the schema, safe to call on every connection.
    Every step is idempotent and safe while another process uses the file;
    the stamp `PRAGMA user_version` is raised to `HISTORY_SCHEMA_VERSION`
    after the steps and never lowered, so a run interrupted before it simply
    repeats the steps next time.
    """
    sqlite_migrations.apply_steps(conn, HISTORY_STEPS, HISTORY_POLICY)


class _HistoryConnection(sqlite3.Connection):
    """`sqlite3.Connection` subclass carrying a batch-depth counter, so
    `write_batch()` can defer a writer's commit across several calls
    without any writer's signature changing. `0` by default: a connection
    never inside a `write_batch` behaves exactly like a plain
    `sqlite3.Connection`.
    """
    _batch_depth = 0


# Database file identities (`os.path.realpath(path)`, `st_dev`, `st_ino`)
# that have already had `init_schema()` run in this process - avoids
# re-running its table- and index-creation statements on every connection,
# since they are idempotent but not free. Guarded by a lock: the
# companion's request threads and a poll-oneshot's own connect can race
# here.
_SCHEMA_READY = set()
_SCHEMA_LOCK = threading.Lock()


def connect(state_dir, timeout=5.0):
    """Open (creating if needed) `<state_dir>/history.db`, apply the
    busy_timeout pragma (every connection), and the WAL pragma + schema
    (once per process for this database file's identity - see
    `_SCHEMA_READY` below). Callers must close it - see `open_db()` for a
    wrapper that does.
    """
    os.makedirs(state_dir, exist_ok=True)
    path = history_db_path(state_dir)
    conn = sqlite3.connect(path, timeout=timeout, factory=_HistoryConnection)
    conn.row_factory = sqlite3.Row
    sqlite_migrations.set_busy_timeout(conn)

    stat_result = os.stat(path)
    key = (os.path.realpath(path), stat_result.st_dev, stat_result.st_ino)
    with _SCHEMA_LOCK:
        # A brand-new or just-recreated file is always empty at this
        # point (sqlite3.connect() creates it with size 0) - re-running
        # the schema there even if this exact (device, inode) key was
        # already marked ready covers a backup restore or a
        # deleted-and-recreated history.db coincidentally reusing a
        # retired inode number. `PRAGMA journal_mode=WAL` is persisted in
        # the file itself, so setting it once per key is enough too.
        if key not in _SCHEMA_READY or stat_result.st_size == 0:
            conn.execute("PRAGMA journal_mode=WAL")
            init_schema(conn)
            _SCHEMA_READY.add(key)
    return conn


# One re-entrant connection slot per thread: `ThreadingHTTPServer` runs one
# thread per request and sqlite3 defaults to check_same_thread=True, so a
# thread-local (rather than a ContextVar, whose inheritance across a
# ThreadPoolExecutor worker or a bare threading.Thread differs by Python
# version) is the one place that is both "shared within a scope" and
# "never visible to another thread" by construction.
_SCOPE = threading.local()


@contextlib.contextmanager
def connection_scope(state_dir):
    """`with connection_scope(state_dir):` - every `open_db(state_dir)`
    call on this thread inside the block, however deep it is nested,
    shares one connection, opened lazily on the first `open_db()` call and
    closed once this outermost scope exits (rolled back first if a write
    was left uncommitted). Re-entrant: a nested `connection_scope` for the
    same path just extends the same scope. A `connection_scope` for a
    different path started while this one is active does not take over -
    it is served as if no scope were active (see `open_db()`'s
    passthrough branch), since one thread-local slot can hold only one
    path at a time.
    """
    path = history_db_path(state_dir)
    active_path = getattr(_SCOPE, "path", None)

    if active_path == path:
        _SCOPE.depth += 1
        try:
            yield
        finally:
            _SCOPE.depth -= 1
        return

    if active_path is not None:
        yield  # a different path is already scoped on this thread
        return

    _SCOPE.path = path
    _SCOPE.depth = 1
    _SCOPE.conn = None
    _SCOPE.error = None
    try:
        yield
    finally:
        conn = _SCOPE.conn
        _SCOPE.path = None
        _SCOPE.depth = 0
        _SCOPE.conn = None
        _SCOPE.error = None
        if conn is not None:
            if conn.in_transaction:
                conn.rollback()
            conn.close()


@contextlib.contextmanager
def open_db(state_dir, timeout=5.0):
    """`with open_db(state_dir) as conn:` - closes on exit even if the
    block raises. Inside a `connection_scope(state_dir)` active on this
    thread, yields that scope's shared connection instead (opened lazily
    on first use here) and does not close it; a prior failed open in the
    same scope re-raises the same exception again without retrying.
    """
    path = history_db_path(state_dir)
    if getattr(_SCOPE, "path", None) == path:
        if _SCOPE.error is not None:
            raise _SCOPE.error
        if _SCOPE.conn is None:
            try:
                _SCOPE.conn = connect(state_dir, timeout=timeout)
            except (sqlite3.Error, OSError) as exc:
                _SCOPE.error = exc
                raise
        yield _SCOPE.conn
        return

    conn = connect(state_dir, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


@contextlib.contextmanager
def write_batch(conn):
    """`with write_batch(conn):` - every writer called on `conn` while the
    block is open defers its commit (see `_commit()`); the batch commits
    once on clean exit, or rolls back and re-raises on an exception.
    Re-entrant on the same connection: only the outermost `write_batch`
    actually commits or rolls back. Tracked on `conn._batch_depth`
    (`getattr` with a `0` default, so a plain `sqlite3.Connection` - one
    not opened through this module's `connect()` - still behaves
    correctly as a single-level batch, just without the attribute
    persisting across calls).
    """
    depth = getattr(conn, "_batch_depth", 0) + 1
    try:
        conn._batch_depth = depth
    except AttributeError:
        pass
    try:
        yield
    except BaseException:
        _exit_batch(conn, depth, commit=False)
        raise
    else:
        _exit_batch(conn, depth, commit=True)


def _exit_batch(conn, depth, commit):
    try:
        conn._batch_depth = depth - 1
    except AttributeError:
        pass
    if depth == 1:  # outermost write_batch on this connection
        if commit:
            conn.commit()
        else:
            conn.rollback()


def _commit(conn):
    """Commit `conn` unless a `write_batch` is active on it - writers call
    this instead of `conn.commit()` directly, so several writes inside a
    batch land in one COMMIT while a bare writer call outside any batch
    still commits immediately, exactly as before this module had a batch
    at all.
    """
    if getattr(conn, "_batch_depth", 0) == 0:
        conn.commit()


# --- Writers -------------------------------------------------------------


def record_runway_event(conn, **fields):
    """Insert one `runway_events` row from any subset of
    `_RUNWAY_EVENT_COLUMNS`; an omitted column is NULL except `ts`
    (defaults to `utc_now_iso()`) and `corroborated` (always `str(value)`).
    Every value goes through a `?` placeholder, never string-formatted, so
    a callsign or airline name carrying HTML or a SQL quote is stored and
    returned byte-identical, never executed.
    """
    ts = fields.get("ts") or utc_now_iso()
    values = []
    for column in _RUNWAY_EVENT_COLUMNS:
        if column == "ts":
            values.append(ts)
        elif column == "corroborated":
            values.append(str(fields.get("corroborated")))
        else:
            values.append(fields.get(column))
    conn.execute(_RUNWAY_EVENT_INSERT_SQL, values)
    _commit(conn)


# A detected aircraft that never reached the display is recorded once; a
# second record for the same hex within this window is the same pass.
UNSHOWN_DEDUPE_WINDOW_S = 1800


def record_unshown_event(conn, ts, **fields):
    """Insert a `runway_events` row for an aircraft the poll cycle detected
    but dropped from the display queue before it was drawn, stamped `ts`
    (when it was first seen). It has no archived render (`gallery_name` is
    "") and whatever the cycle knew: its route when one fits, its direction.

    Skipped, returning 0, when the same hex already has a row within
    `UNSHOWN_DEDUPE_WINDOW_S` before `ts`, so re-detection of one pass after
    it was dropped does not add a second row. Returns 1 when a row is added.
    """
    hex_code = fields.get("hex")
    if hex_code:
        try:
            earliest = (datetime.fromisoformat(ts) - timedelta(seconds=UNSHOWN_DEDUPE_WINDOW_S)).isoformat(timespec="seconds")
        except (TypeError, ValueError):
            earliest = ts
        if conn.execute(
            "SELECT 1 FROM runway_events WHERE hex = ? AND ts >= ? LIMIT 1", (hex_code, earliest),
        ).fetchone():
            return 0
    fields.pop("gallery_name", None)
    record_runway_event(conn, ts=ts, gallery_name="", **fields)
    return 1


def record_device_health(conn, ts, battery_mv=None, fw_version=None, boot_reason=None, rssi=None,
                         wake_stats=None):
    """Insert one `device_health` row, `INSERT OR IGNORE` against
    `UNIQUE(ts, battery_mv)`. Returns rows actually inserted (0 or 1).
    `wake_stats` is a dict from `parse_wake_stats`; a column it lacks (or
    `None` altogether) is stored NULL, meaning unknown.
    """
    stats = wake_stats or {}
    wake_values = tuple(stats.get(column) for column in WAKE_COLUMNS)
    cur = conn.execute(
        _DEVICE_HEALTH_INSERT_SQL,
        (ts, battery_mv, fw_version, boot_reason, rssi) + wake_values)
    _commit(conn)
    return cur.rowcount


def record_wake_epoch(conn, ts, wake_interval_s):
    """Record that the wake interval became `wake_interval_s` at `ts`,
    but only when it differs from the newest row stored - an
    unconditional insert would add ~2,880 rows/day for no new
    information. Returns rows actually inserted (0 or 1).
    `wake_interval_s=None` is a distinct value, not a continuation: it
    inserts a fresh row even following a stored NULL, since a later
    reader must not infer the old cadence continued when nothing said so.
    Compared against the newest row by `id` (insertion order), not `ts`.
    """
    newest = conn.execute(
        "SELECT wake_interval_s FROM wake_epochs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if newest is not None and newest[0] == wake_interval_s:
        return 0
    conn.execute(
        "INSERT INTO wake_epochs (ts, wake_interval_s) VALUES (?, ?)",
        (ts, wake_interval_s),
    )
    _commit(conn)
    return 1


def record_poll_cycle(conn, ts, values):
    """Insert one `poll_cycles` row from `values`, a dict keyed by
    `POLL_CYCLE_COLUMNS` (a missing key stores NULL, an unknown key is
    ignored). Booleans are stored as 0/1. Returns 1.
    """
    row = [ts]
    for column in POLL_CYCLE_COLUMNS:
        value = values.get(column)
        row.append(int(value) if isinstance(value, bool) else value)
    conn.execute(
        "INSERT INTO poll_cycles (ts, " + ", ".join(POLL_CYCLE_COLUMNS) + ") VALUES ("
        + ", ".join("?" * (len(POLL_CYCLE_COLUMNS) + 1)) + ")",
        row,
    )
    _commit(conn)
    return 1


def prune_poll_cycles(conn, now_iso):
    """Delete `poll_cycles` rows older than `POLL_CYCLE_RETENTION_DAYS`
    before `now_iso`. An unparseable `now_iso` prunes nothing. Returns the
    number of rows deleted.
    """
    try:
        now = datetime.fromisoformat(now_iso)
    except (TypeError, ValueError):
        return 0
    cutoff = (now - timedelta(days=POLL_CYCLE_RETENTION_DAYS)).isoformat(timespec="seconds")
    deleted = conn.execute("DELETE FROM poll_cycles WHERE ts < ?", (cutoff,)).rowcount
    _commit(conn)
    return deleted


def record_route_lookups(conn, ts, lookups):
    """Insert one `route_lookups` row per `(directory, outcome)` in
    `lookups`, all stamped `ts`. A pair naming a directory or outcome this
    module does not know is skipped. Returns the number of rows added."""
    rows = [
        (ts, directory, outcome) for directory, outcome in lookups
        if directory in ROUTE_DIRECTORIES and outcome in ROUTE_LOOKUP_OUTCOMES]
    if rows:
        conn.executemany(
            "INSERT INTO route_lookups (ts, directory, outcome) VALUES (?, ?, ?)", rows)
        _commit(conn)
    return len(rows)


def prune_route_lookups(conn, now_iso):
    """Delete `route_lookups` rows older than `ROUTE_LOOKUP_RETENTION_DAYS`
    before `now_iso`. An unparseable `now_iso` prunes nothing. Returns the
    number of rows deleted."""
    try:
        now = datetime.fromisoformat(now_iso)
    except (TypeError, ValueError):
        return 0
    cutoff = (now - timedelta(days=ROUTE_LOOKUP_RETENTION_DAYS)).isoformat(timespec="seconds")
    deleted = conn.execute("DELETE FROM route_lookups WHERE ts < ?", (cutoff,)).rowcount
    _commit(conn)
    return deleted


# --- Readers ---------------------------------------------------------------


_CALLSIGN_PREFIX_RE = re.compile(r"^([A-Z]{3})[A-Z0-9]+$")


def recent_runway_events(conn, limit=50, airline_names=None):
    """Newest first (`ts DESC, id DESC`; the tiebreak matters at
    seconds-precision timestamps).

    `airline_names`, a `{3-letter prefix: name}` mapping (the owner's name
    overrides), replaces each returned row's `airline` for a callsign
    under one of those prefixes. It is applied to the rows as they are
    read and never written back: the stored `airline` stays the name the
    flight was resolved with, so dropping an override restores it with no
    migration, and the poll loop's writes are untouched.
    """
    rows = conn.execute(
        "SELECT * FROM runway_events ORDER BY ts DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    events = [dict(row) for row in rows]
    if airline_names:
        for event in events:
            name = override_airline_name(event, airline_names)
            if name is not None:
                event["airline"] = name
    return events


def override_airline_name(event, airline_names):
    """The owner's name for `event`'s callsign prefix in `airline_names`
    (`{3-letter prefix: name}`), or None when the prefix has none."""
    match = _CALLSIGN_PREFIX_RE.match(str(event.get("callsign") or "").strip().upper())
    if match and match.group(1) in airline_names:
        return airline_names[match.group(1)]
    return None


def route_source_counts(conn, since=None):
    """`{route_source: count}` over `runway_events`, optionally restricted
    to `ts >= since`.
    """
    if since is not None:
        rows = conn.execute(
            "SELECT route_source, COUNT(*) AS n FROM runway_events WHERE ts >= ? GROUP BY route_source",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT route_source, COUNT(*) AS n FROM runway_events GROUP BY route_source"
        ).fetchall()
    return {row["route_source"]: row["n"] for row in rows}


def route_directory_stats(conn, since):
    """`{directory: stats}` for every directory in `ROUTE_DIRECTORIES`, from
    `route_lookups`. `stats` holds `lookups`, `found` and `failed` (requests
    with `ts >= since`), `last_answer_ts` (the newest request that was
    answered, found or none, over all retained rows, else None) and
    `reachable` (True when the newest request was answered, False when it
    failed, None when there is none)."""
    stats = {}
    for directory in ROUTE_DIRECTORIES:
        counts = {
            row["outcome"]: row["n"] for row in conn.execute(
                "SELECT outcome, COUNT(*) AS n FROM route_lookups "
                "WHERE directory = ? AND ts >= ? GROUP BY outcome", (directory, since))}
        last = conn.execute(
            "SELECT outcome FROM route_lookups WHERE directory = ? "
            "ORDER BY ts DESC, id DESC LIMIT 1", (directory,)).fetchone()
        answered = conn.execute(
            "SELECT MAX(ts) AS ts FROM route_lookups "
            "WHERE directory = ? AND outcome != 'failed'", (directory,)).fetchone()
        stats[directory] = {
            "lookups": sum(counts.values()),
            "found": counts.get("found", 0),
            "failed": counts.get("failed", 0),
            "last_answer_ts": answered["ts"],
            "reachable": None if last is None else last["outcome"] != "failed",
        }
    return stats


def route_directory_counts(conn, since):
    """`{directory: flights}` over `runway_events` with `ts >= since`, for the
    directories in `ROUTE_DIRECTORIES`: how many flights each one's route was
    shown for. Rows from before the column count for neither."""
    rows = conn.execute(
        "SELECT route_directory, COUNT(*) AS n FROM runway_events "
        "WHERE ts >= ? AND route_directory IS NOT NULL GROUP BY route_directory", (since,)).fetchall()
    by_directory = {row["route_directory"]: row["n"] for row in rows}
    return {directory: by_directory.get(directory, 0) for directory in ROUTE_DIRECTORIES}


def corroboration_counts(conn, since=None):
    """`{corroborated_text: count}` over `runway_events` - "True"/"False"/
    "None" bucketed separately, "None" never collapsed into "False".
    """
    if since is not None:
        rows = conn.execute(
            "SELECT corroborated, COUNT(*) AS n FROM runway_events WHERE ts >= ? GROUP BY corroborated",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT corroborated, COUNT(*) AS n FROM runway_events GROUP BY corroborated"
        ).fetchall()
    return {row["corroborated"]: row["n"] for row in rows}


def recent_device_health(conn, limit=200):
    rows = conn.execute(
        "SELECT * FROM device_health ORDER BY ts DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _stored_since(since):
    """`since` (`...Z`) spelled the way the battery-log tailer stores `ts`
    (`...+00:00`), so the text comparison `ts >= since` is inclusive at the
    boundary: `+` sorts before `Z`, so comparing the two spellings directly
    would drop a row stamped exactly at `since`.
    """
    return since[:-1] + "+00:00"


class TooManyRows(Exception):
    """A read-only export matched more rows than its caller allows."""


def _select_export_rows(conn, since, max_rows):
    params = (_stored_since(since), max_rows + 1)
    tail = " FROM device_health WHERE ts >= ? ORDER BY ts LIMIT ?"
    try:
        return conn.execute(
            "SELECT " + ", ".join(_DEVICE_HEALTH_OLD_COLUMNS + WAKE_COLUMNS) + tail,
            params).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such column" not in str(exc):
            raise
    padding = (None,) * len(WAKE_COLUMNS)
    old_rows = conn.execute(
        "SELECT " + ", ".join(_DEVICE_HEALTH_OLD_COLUMNS) + tail, params).fetchall()
    return [tuple(row) + padding for row in old_rows]


def export_device_health(state_dir, since, max_rows):
    """The `device_health` rows with `ts >= since`, oldest first, as
    (ts, battery_mv, fw_version, boot_reason, rssi, *WAKE_COLUMNS) tuples.
    A database not yet migrated to the wake columns yields the five old
    values followed by thirteen `None`s instead of failing.

    Opens history.db read-only (`mode=ro`): it never creates the file, runs
    no schema statement and cannot write. Raises `TooManyRows` when more
    than `max_rows` rows match, never a silent truncation, and
    `sqlite3.Error` when the database is missing or unreadable. `since` is
    bound as a parameter and compared as stored text.
    """
    path = os.path.abspath(history_db_path(state_dir))
    uri = pathlib.Path(path).as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        sqlite_migrations.set_busy_timeout(conn)
        conn.execute("PRAGMA query_only=ON")
        rows = _select_export_rows(conn, since, max_rows)
    finally:
        conn.close()
    if len(rows) > max_rows:
        raise TooManyRows()
    return rows


# Tables the read-only exports may name, with the columns each exposes, in
# output order. Fixed here so no caller-supplied text ever reaches a query.
EXPORT_TABLES = {
    "runway_events": (
        "ts", "hex", "callsign", "aircraft_type", "confirmed_state",
        "corroborated", "route_source", "airline", "origin", "destination",
        "tracked_runway", "gallery_name",
    ),
    "poll_cycles": ("ts",) + POLL_CYCLE_COLUMNS,
}

# `meta` keys the status export shows: pipeline heartbeat and provider calls,
# never an offset or anything a caller could use to read other files.
_STATUS_META_KEYS = (
    META_LAST_PIPELINE_RUN, META_LAST_DETECTION, META_SOURCE_FAULT,
    META_LAST_POLL_TRIGGER,
)


def _open_read_only(state_dir):
    path = os.path.abspath(history_db_path(state_dir))
    conn = sqlite3.connect(pathlib.Path(path).as_uri() + "?mode=ro", uri=True, timeout=5.0)
    sqlite_migrations.set_busy_timeout(conn)
    conn.execute("PRAGMA query_only=ON")
    return conn


def export_table_rows(state_dir, table, since, max_rows):
    """The rows of `table` (a key of `EXPORT_TABLES`) with `ts >= since`,
    oldest first, as tuples of that table's export columns. A table or
    column the database does not have yet (a poll oneshot has not run since
    a deploy) reads as no rows or NULL, never as an error.

    Opens history.db read-only like `export_device_health()`; raises
    `TooManyRows` rather than truncating, `sqlite3.Error` when the database
    is missing or unreadable, and `KeyError` for a table not in
    `EXPORT_TABLES`.
    """
    columns = EXPORT_TABLES[table]
    conn = _open_read_only(state_dir)
    try:
        present = {row[1] for row in conn.execute("PRAGMA table_info(" + table + ")")}
        if not present:
            return []
        select = ", ".join(c if c in present else "NULL" for c in columns)
        rows = conn.execute(
            "SELECT " + select + " FROM " + table + " WHERE ts >= ? ORDER BY ts, id LIMIT ?",
            (_stored_since(since), max_rows + 1)).fetchall()
    finally:
        conn.close()
    if len(rows) > max_rows:
        raise TooManyRows()
    return rows


def export_status_meta(state_dir):
    """`{key: {"value", "updated_at"}}` for the heartbeat keys the status
    export shows plus every per-provider last-call key. Read-only.
    """
    conn = _open_read_only(state_dir)
    try:
        try:
            rows = conn.execute("SELECT key, value, updated_at FROM meta").fetchall()
        except sqlite3.OperationalError:
            return {}
    finally:
        conn.close()
    return {
        key: {"value": value, "updated_at": updated_at}
        for key, value, updated_at in rows
        if key in _STATUS_META_KEYS or key.startswith(META_PROVIDER_LAST_CALL_PREFIX)
    }


def latest_device_health(conn):
    row = conn.execute(
        "SELECT * FROM device_health ORDER BY ts DESC, id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row is not None else None


def instant_or_none(ts):
    """Parse a stored `device_health.ts` string into a timezone-aware UTC
    `datetime`, or `None` if it doesn't parse. A naive `ts` is taken as
    UTC. The one parse path in this module - `paris_day_or_none()` and
    `check_in_gaps()` both go through it, so a day-bucketing and an
    interval-dating decision can never disagree. `ts` is attacker-
    influenceable (see `tail_caddy_battery_log()`); every caller handles
    `None`.
    """
    try:
        parsed = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def paris_day_or_none(ts):
    """A stored `device_health.ts` string's Europe/Paris calendar `date`,
    or `None` if it doesn't parse - e.g. `2026-09-02T01:30:00+02:00`
    buckets to `2026-09-02` in Paris, not `2026-09-01` in UTC.
    """
    parsed = instant_or_none(ts)
    if parsed is None:
        return None
    return parsed.astimezone(ZoneInfo("Europe/Paris")).date()


def check_in_gaps(conn, since=None):
    """The observed intervals between consecutive `device_health`
    check-ins, oldest-first: `{"ts": <later ts>, "from_ts": <earlier ts>,
    "gap_s": <int or None if undatable>, "day": <Europe/Paris "YYYY-MM-DD"
    of ts, or None>}`. `since`, when given, restricts to `ts >= since`
    (display window, never a retention bound).

    No `battery_mv` filter, deliberately: a NULL-battery row is still a
    real check-in whose `X-Battery-Mv` header was absent or unparseable,
    and filtering it out (as `daily_battery_averages()` does) would merge
    its neighbouring intervals into one long false gap.

    Ordered by ingest (`id`), not `ts`, since `ts` is attacker-
    influenceable (`tail_caddy_battery_log()`) and `id` is assigned in
    true ingest order - a hostile timestamp can only make its own span
    undatable, never reorder the series.

    `gap_s = None` whenever either bound doesn't parse, or the later
    bound parses earlier than the earlier one (out-of-order timestamp,
    duration unknowable) - dropping such a row instead would merge two
    real intervals into one false long gap.

    What this reader cannot know, and why it returns raw gaps rather than
    classifying them (that's `wake.classify_check_in_gap()`'s job): a log
    rotation the ingest missed is indistinguishable from a missed wake,
    and `UNIQUE(ts, battery_mv)` can only ever collapse two check-ins
    that land in the same second with the same reading - provably
    impossible at any configurable cadence (device_config.WAKE_INTERVAL_MIN_S
    is 60s).
    """
    if since is not None:
        rows = conn.execute(
            "SELECT id, ts FROM device_health WHERE ts >= ? ORDER BY ts ASC, id ASC",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, ts FROM device_health ORDER BY ts ASC, id ASC"
        ).fetchall()

    series = sorted(rows, key=lambda row: row["id"])

    gaps = []
    for earlier, later in zip(series, series[1:]):
        start = instant_or_none(earlier["ts"])
        end = instant_or_none(later["ts"])
        if start is None or end is None:
            gap_s = None
        else:
            delta = (end - start).total_seconds()
            gap_s = int(round(delta)) if delta >= 0 else None
        day = paris_day_or_none(later["ts"])
        gaps.append({
            "ts": later["ts"],
            "from_ts": earlier["ts"],
            "gap_s": gap_s,
            "day": day.isoformat() if day is not None else None,
        })
    return gaps


def daily_battery_averages(conn, since=None):
    """One row per Europe/Paris calendar day with at least one numeric
    battery reading, newest first: `{"ts": "YYYY-MM-DD", "battery_mv":
    <mean, int>, "reading_count": <int>}`. Keyed `ts`, not `day`, so
    these rows are structurally interchangeable with
    `recent_device_health()`'s for `battery_sparkline_svg()`.

    Bucketing happens in Python via `paris_day_or_none()`, not SQL:
    there's no SQL fixed-offset modifier that's DST-correct for
    Europe/Paris, but `ZoneInfo` resolves the fold correctly across both
    transitions. A row whose `ts` doesn't parse forms no bucket, rather
    than a phantom NULL-keyed day. The `battery_mv IS NOT NULL` filter
    stays in SQL so a day with only NULL-battery rows forms no bucket
    either. `since` is a display window, like elsewhere in this
    codebase - never a retention bound.
    """
    if since is not None:
        rows = conn.execute(
            "SELECT ts, battery_mv FROM device_health "
            "WHERE ts >= ? AND battery_mv IS NOT NULL",
            (since,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ts, battery_mv FROM device_health WHERE battery_mv IS NOT NULL"
        ).fetchall()

    buckets = {}
    for row in rows:
        day = paris_day_or_none(row["ts"])
        if day is None:
            continue
        total, count = buckets.get(day, (0, 0))
        buckets[day] = (total + row["battery_mv"], count + 1)

    return [
        {
            "ts": day.isoformat(),
            "battery_mv": int(round(buckets[day][0] / buckets[day][1])),
            "reading_count": buckets[day][1],
        }
        for day in sorted(buckets.keys(), reverse=True)
    ]


# --- Home statistics (read-only aggregates) ------------------------------
#
# Each function reads the one frame's own history database (`conn`), never
# writes, and takes the frame's IANA time zone and an explicit `now` (an
# aware datetime or an ISO string) instead of reading the clock.

# Two stored events of one pass within this many seconds count once, the same
# window the Flights and Home lists fold on (companion/flight_card.py).
PASS_DUPLICATE_WINDOW_S = 60
HOME_STATS_DIRECTIONS = ("arriving", "departing")
HOME_STATS_DAYS = 7
_FALLBACK_TIMEZONE = "Europe/Paris"


def _frame_zone(tz_name):
    try:
        return ZoneInfo(tz_name)
    except (KeyError, ValueError, TypeError, OSError):
        return ZoneInfo(_FALLBACK_TIMEZONE)


def _local_today(tz_name, now):
    """`(zone, today)`: the frame's zone and the local calendar date of `now`."""
    instant = instant_or_none(now) if isinstance(now, str) else now
    if instant is None:
        instant = datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    zone = _frame_zone(tz_name)
    return zone, instant.astimezone(zone).date()


def _day_window(zone, first_day, last_day):
    """The stored-`ts` text bounds `[start, end)` of the local days
    `first_day..last_day` inclusive, spelled as the poll loop stores them."""
    start = datetime.combine(first_day, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(last_day + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return (start.astimezone(timezone.utc).isoformat(timespec="seconds"),
            end.astimezone(timezone.utc).isoformat(timespec="seconds"))


def _direction_events(conn, zone, first_day, last_day, columns="ts, hex, callsign, origin, "
                      "destination, confirmed_state"):
    """The arrivals and departures between two local days as dicts, oldest
    first, with a pass stored twice folded to one and each row's local
    `moment` (an aware datetime). One range scan of `idx_runway_events_ts`."""
    start, end = _day_window(zone, first_day, last_day)
    rows = conn.execute(
        "SELECT %s FROM runway_events WHERE ts >= ? AND ts < ? "
        "AND confirmed_state IN (?, ?) ORDER BY ts ASC, id ASC" % columns,
        (start, end) + HOME_STATS_DIRECTIONS,
    ).fetchall()
    events = []
    last_seen = {}
    for row in rows:
        moment = instant_or_none(row["ts"])
        if moment is None:
            continue
        key = tuple(row[name] for name in (
            "hex", "callsign", "origin", "destination", "confirmed_state"))
        earlier = last_seen.get(key)
        last_seen[key] = moment
        if earlier is not None and (moment - earlier).total_seconds() < PASS_DUPLICATE_WINDOW_S:
            continue
        event = dict(row)
        event["moment"] = moment.astimezone(zone)
        events.append(event)
    return events


def home_day_timeline(conn, tz_name, now):
    """Today's arrivals and departures in the frame's local day:
    `{"day": "YYYY-MM-DD", "arriving": n, "departing": n, "hours": [24 x
    {"hour", "arriving", "departing"}], "ticks": [{"at": local hour as a
    float, "state"}]}`. Every hour of the day is present, zero when quiet."""
    zone, today = _local_today(tz_name, now)
    hours = [{"hour": hour, "arriving": 0, "departing": 0} for hour in range(24)]
    ticks = []
    for event in _direction_events(conn, zone, today, today):
        moment, state = event["moment"], event["confirmed_state"]
        hours[moment.hour][state] += 1
        ticks.append({"at": moment.hour + moment.minute / 60.0, "state": state})
    return {
        "day": today.isoformat(),
        "arriving": sum(h["arriving"] for h in hours),
        "departing": sum(h["departing"] for h in hours),
        "hours": hours,
        "ticks": ticks,
    }


def home_week_totals(conn, tz_name, now):
    """The last seven local days, oldest first and ending today, zero-filled:
    `[{"day": "YYYY-MM-DD", "arriving": n, "departing": n, "total": n}]`."""
    zone, today = _local_today(tz_name, now)
    first = today - timedelta(days=HOME_STATS_DAYS - 1)
    days = {
        (first + timedelta(days=i)): {"arriving": 0, "departing": 0}
        for i in range(HOME_STATS_DAYS)}
    for event in _direction_events(conn, zone, first, today):
        days[event["moment"].date()][event["confirmed_state"]] += 1
    return [
        {"day": day.isoformat(), "arriving": c["arriving"], "departing": c["departing"],
         "total": c["arriving"] + c["departing"]}
        for day, c in sorted(days.items())]


def _airline_of(event, airline_names):
    override = override_airline_name(event, airline_names) if airline_names else None
    return override or (event.get("airline") or "").strip()


def home_airline_highlights(conn, tz_name, now, airline_names=None):
    """Over the last seven local days: `{"most_seen": {"airline", "count"} or
    None, "new_airlines": [names]}`. The most seen airline has the highest
    count, ties broken alphabetically; a new airline is one first seen
    inside the window (no earlier row names it). A flight without an airline
    counts for none. `airline_names` is the owner's `{prefix: name}` override
    applied to what is read, never written back."""
    zone, today = _local_today(tz_name, now)
    first = today - timedelta(days=HOME_STATS_DAYS - 1)
    counts = {}
    for event in _direction_events(
            conn, zone, first, today,
            columns="ts, hex, callsign, origin, destination, confirmed_state, airline"):
        name = _airline_of(event, airline_names)
        if name:
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return {"most_seen": None, "new_airlines": []}
    best = min(counts, key=lambda name: (-counts[name], name))
    start, _ = _day_window(zone, first, today)
    earlier = {
        _airline_of(dict(row), airline_names) for row in conn.execute(
            "SELECT DISTINCT airline, callsign FROM runway_events "
            "WHERE ts < ? AND airline IS NOT NULL", (start,))}
    return {
        "most_seen": {"airline": best, "count": counts[best]},
        "new_airlines": sorted(name for name in counts if name not in earlier),
    }


def get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else None


def set_meta(conn, key, value):
    conn.execute(_META_UPSERT_SQL, (key, value, utc_now_iso()))
    _commit(conn)


# --- Caddy battery-log tailer -----------------------------------------------
#
# The JSON nesting of Caddy's logged request headers below
# (`request.headers.<Header-Name>` as a list of strings) is taken from
# Caddy's own documentation. A nesting mismatch degrades to "zero
# readings ingested", never an exception.


def tail_caddy_battery_log(log_path, offset):
    """Read `log_path` from byte `offset`, one COMPLETE Caddy JSON
    access-log line at a time (a line without a trailing `\\n` - a
    rotation can catch Caddy mid-write - is never parsed, and is not
    counted into the returned offset, so the next tail re-reads it once
    it is complete); return `(readings, new_offset)`.

    Read in binary and decoded per line with `errors="replace"`, so
    invalid-UTF-8 bytes can never raise here, and every offset - `offset`
    itself and the returned `new_offset` - is an exact BYTE count, safe
    to `seek()` back to even mid-multi-byte-character in a header value.

    A line that fails to parse as JSON, or whose URI isn't
    `DEVICE_DISPLAY_URI`, is skipped silently (but still counted into
    `new_offset` - it was a complete line, just not one this tailer
    keeps). Battery is coerced to `int`, `None` on failure. `ts` is used
    as-is if a string; if a float/int epoch, converted via
    `datetime.fromtimestamp()` - an out-of-range value (`OverflowError`,
    `OSError`, or non-finite per `ValueError`, e.g. the JSON `NaN` token)
    skips the line entirely rather than raising or storing a garbage
    timestamp; otherwise `utc_now_iso()`. A missing/unreadable file
    returns `([], offset)`.
    """
    readings = []
    consumed_through = offset
    try:
        with open(log_path, "rb") as fh:
            fh.seek(offset)
            for raw_line in fh:
                if not raw_line.endswith(b"\n"):
                    # Partial last line (Caddy still mid-write, or a
                    # rotation caught it mid-line) - leave both the
                    # reading and the offset behind for the next tail.
                    break
                consumed_through += len(raw_line)
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                request = entry.get("request")
                if not isinstance(request, dict):
                    continue
                if request.get("uri") != DEVICE_DISPLAY_URI:
                    continue
                headers = request.get("headers")
                if not isinstance(headers, dict):
                    headers = {}
                extracted = {}
                for name in _TELEMETRY_HEADER_ALLOWLIST:
                    values = headers.get(name)
                    if isinstance(values, list) and values:
                        extracted[name] = values[0]
                wake_stats = None
                if "X-Wake-Stats" in extracted:
                    wake_stats = parse_wake_stats(extracted["X-Wake-Stats"])

                battery_mv = None
                battery_raw = extracted.get("X-Battery-Mv")
                if battery_raw is not None:
                    try:
                        battery_mv = int(battery_raw)
                    except (TypeError, ValueError):
                        battery_mv = None

                ts_raw = entry.get("ts")
                if isinstance(ts_raw, str):
                    ts = ts_raw
                elif isinstance(ts_raw, (int, float)) and not isinstance(ts_raw, bool):
                    try:
                        ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc).isoformat(timespec="seconds")
                    except (OverflowError, OSError, ValueError):
                        continue  # out-of-range or non-finite epoch ts - skip this line
                else:
                    ts = utc_now_iso()

                readings.append({
                    "ts": ts,
                    "battery_mv": battery_mv,
                    "fw_version": extracted.get("X-Fw-Version"),
                    "boot_reason": extracted.get("X-Boot-Reason"),
                    "rssi": extracted.get("X-Rssi"),
                    "wake_stats": wake_stats,
                })
    except OSError:
        return [], offset
    return readings, consumed_through


def read_caddy_battery_log(conn, log_path):
    """The read-only half of the Caddy-log tailer: resolve the stored
    offset (a non-integer, negative, or empty stored value resets to 0
    rather than raising; reset to 0 if the file shrank, i.e. rotated) and
    tail the file from there. Returns `(readings, new_offset)`, or `None`
    for a missing log file.

    Deliberately reads `META_CADDY_LOG_OFFSET` via a plain `get_meta()`
    SELECT and touches no writer - a caller may run this BEFORE opening a
    `write_batch()`, so tailing up to a 10 MiB file never happens while
    the write lock is held (a companion writer would otherwise wait on
    `busy_timeout` for that whole read). `apply_caddy_battery_log()` is
    this function's write-side counterpart.
    """
    if not os.path.exists(log_path):
        return None

    stored_offset = get_meta(conn, META_CADDY_LOG_OFFSET)
    try:
        offset = int(stored_offset) if stored_offset else 0
    except (TypeError, ValueError):
        offset = 0
    if offset < 0:
        offset = 0

    try:
        file_size = os.path.getsize(log_path)
    except OSError:
        return None
    if file_size < offset:
        offset = 0  # Caddy rotated the log out from under us.

    return tail_caddy_battery_log(log_path, offset)


def apply_caddy_battery_log(conn, readings, new_offset):
    """The write half of the Caddy-log tailer: insert every reading from
    `read_caddy_battery_log()`'s result and store the new offset. Returns
    rows actually inserted (a re-tail of an already-seen range is
    silently ignored by `UNIQUE(ts, battery_mv)`).
    """
    inserted = 0
    for reading in readings:
        inserted += record_device_health(
            conn,
            reading["ts"],
            battery_mv=reading["battery_mv"],
            fw_version=reading["fw_version"],
            boot_reason=reading["boot_reason"],
            rssi=reading["rssi"],
            wake_stats=reading.get("wake_stats"),
        )
    set_meta(conn, META_CADDY_LOG_OFFSET, str(new_offset))
    return inserted
