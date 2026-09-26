#!/usr/bin/env python3
"""SQLite history store behind the health trend, the flight log, and
resolution statistics, plus the Caddy access-log tailer that is the only
permitted path to device battery telemetry.

Leaf module: stdlib only, must never import `device_config`,
`server.plane.detect`, `server.plane.render`, or `server.poll_loop`.

Cadence rule: `runway_events` rows are written only on a real transition,
never once per 30-second cycle - the always-changing "pipeline last ran"
signal lives in the fixed-size `meta` table instead, so keep-forever
retention doesn't turn into unbounded per-cycle row growth.

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
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Same repo-root sys.path bootstrap as server/poll_loop.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

HISTORY_DB_FILENAME = "history.db"

# Fixed-size per-cycle signals - constant storage regardless of cycle count.
META_LAST_PIPELINE_RUN = "last_pipeline_run"
META_LAST_DETECTION = "last_detection"
META_SOURCE_FAULT = "source_fault"
META_CADDY_LOG_OFFSET = "caddy_log_offset"
META_LAST_POLL_TRIGGER = "last_poll_trigger"

_RUNWAY_EVENT_COLUMNS = (
    "ts", "hex", "callsign", "aircraft_type", "confirmed_state",
    "corroborated", "route_source", "airline", "origin", "destination",
    "tracked_runway",
)

_RUNWAY_EVENT_INSERT_SQL = (
    "INSERT INTO runway_events "
    "(ts, hex, callsign, aircraft_type, confirmed_state, corroborated, "
    "route_source, airline, origin, destination, tracked_runway) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_DEVICE_HEALTH_INSERT_SQL = (
    "INSERT OR IGNORE INTO device_health "
    "(ts, battery_mv, fw_version, boot_reason, rssi) VALUES (?, ?, ?, ?, ?)"
)

_META_UPSERT_SQL = (
    "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)"
)

# The only header names ever extracted from a Caddy access-log line -
# indexed one at a time, the header map never copied wholesale, so a
# future Caddy config that stops redacting Authorization/Cookie can't
# leak a credential into history.db.
_TELEMETRY_HEADER_ALLOWLIST = ("X-Fw-Version", "X-Boot-Reason", "X-Rssi", "X-Battery-Mv")

DEVICE_DISPLAY_URI = "/device/v1/display"


def utc_now_iso():
    """Timezone-aware UTC ISO-8601 string at seconds precision, matching
    enrich.note_unresolved_prefix()'s format so the two stores sort
    consistently.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def history_db_path(state_dir):
    return os.path.join(state_dir, HISTORY_DB_FILENAME)


def init_schema(conn):
    """Create all four tables with IF NOT EXISTS, safe to call on every
    connection. This is the project's entire migration story: no schema
    version stamp, no in-place table alteration - a new table is free,
    a new column would have required inventing one.
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
        "tracked_runway TEXT"
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
    # a table (free, via IF NOT EXISTS) rather than a new column on
    # `device_health` (would need a migration mechanism). Nullable on
    # purpose: a NULL epoch records "cadence undetermined from here",
    # never lets a reader infer the previous interval silently continued.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wake_epochs ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "wake_interval_s INTEGER"
        ")"
    )
    conn.commit()


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
    conn.execute("PRAGMA busy_timeout=5000")

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


def record_device_health(conn, ts, battery_mv=None, fw_version=None, boot_reason=None, rssi=None):
    """Insert one `device_health` row, `INSERT OR IGNORE` against
    `UNIQUE(ts, battery_mv)`. Returns rows actually inserted (0 or 1).
    """
    cur = conn.execute(_DEVICE_HEALTH_INSERT_SQL, (ts, battery_mv, fw_version, boot_reason, rssi))
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


# --- Readers ---------------------------------------------------------------


def recent_runway_events(conn, limit=50):
    """Newest first (`ts DESC, id DESC`; the tiebreak matters at
    seconds-precision timestamps).
    """
    rows = conn.execute(
        "SELECT * FROM runway_events ORDER BY ts DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


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


def latest_device_health(conn):
    row = conn.execute(
        "SELECT * FROM device_health ORDER BY ts DESC, id DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row is not None else None


def _instant_or_none(ts):
    """Parse a stored `device_health.ts` string into a timezone-aware UTC
    `datetime`, or `None` if it doesn't parse. A naive `ts` is taken as
    UTC. The one parse path in this module - `_paris_day_or_none()` and
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


def _paris_day_or_none(ts):
    """A stored `device_health.ts` string's Europe/Paris calendar `date`,
    or `None` if it doesn't parse - e.g. `2026-09-02T01:30:00+02:00`
    buckets to `2026-09-02` in Paris, not `2026-09-01` in UTC.
    """
    parsed = _instant_or_none(ts)
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
        start = _instant_or_none(earlier["ts"])
        end = _instant_or_none(later["ts"])
        if start is None or end is None:
            gap_s = None
        else:
            delta = (end - start).total_seconds()
            gap_s = int(round(delta)) if delta >= 0 else None
        day = _paris_day_or_none(later["ts"])
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

    Bucketing happens in Python via `_paris_day_or_none()`, not SQL:
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
        day = _paris_day_or_none(row["ts"])
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
                })
    except OSError:
        return [], offset
    return readings, consumed_through


def ingest_caddy_battery_log(conn, log_path):
    """Read the stored offset (a non-integer, negative, or empty stored
    value resets to 0 rather than raising; reset to 0 if the file shrank,
    i.e. rotated), tail the file, insert every reading, store the new
    offset. Returns rows actually inserted (a re-tail of an already-seen
    range is silently ignored by `UNIQUE(ts, battery_mv)`). A missing log
    file returns 0 without raising.
    """
    if not os.path.exists(log_path):
        return 0

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
        return 0
    if file_size < offset:
        offset = 0  # Caddy rotated the log out from under us.

    readings, new_offset = tail_caddy_battery_log(log_path, offset)
    inserted = 0
    for reading in readings:
        inserted += record_device_health(
            conn,
            reading["ts"],
            battery_mv=reading["battery_mv"],
            fw_version=reading["fw_version"],
            boot_reason=reading["boot_reason"],
            rssi=reading["rssi"],
        )
    set_meta(conn, META_CADDY_LOG_OFFSET, str(new_offset))
    return inserted
