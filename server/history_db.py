#!/usr/bin/env python3
"""SQLite history store behind CFG-03's health trend, CFG-06's flight log,
and CFG-08's resolution statistics, plus the Caddy access-log tailer that
is the only permitted path to device battery telemetry (D-03,
06-CONTEXT.md - `stub-server/byos_server.py` is vendored and must never be
modified, even though it is the process that actually receives
`X-Battery-Mv` per request).

Stdlib-only (`sqlite3`, `json`, `os`, `datetime`). This module must not
import `device_config`, `server.plane.detect`, `server.plane.render`, or
`server.poll_loop` - it is a leaf, like `server.device_config`.

Cadence rule (Pitfall 1, 06-RESEARCH.md): `runway_events` rows are written
only on a real transition - a new `hex`, a `confirmed_state` flip, or a
`corroborated` flip - never once per 30-second poll cycle. The always-
changing "when did the pipeline last run" signal belongs in the fixed-size
`meta` table instead (see the `META_*` key constants below), so D-13's
keep-forever retention does not turn into unbounded per-cycle row growth
(T-06-01-04).

Concurrency (Pitfall 9): every connection this module opens sets
`PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`, so a concurrent
write from the 30-second poll oneshot and a read from the long-running
companion service wait briefly on a lock instead of raising
"database is locked" (T-06-01-05).
"""
import contextlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Same repo-root sys.path bootstrap as server/poll_loop.py (lines 31-38),
# so this file works both as `import server.history_db` and when executed
# directly.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

HISTORY_DB_FILENAME = "history.db"

# Fixed-size per-cycle signals (Pitfall 1) - constant storage regardless of
# how many poll cycles run, unlike a hypothetical one-row-per-cycle table.
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

# T-06-01-03: the only header names ever extracted from a Caddy access-log
# line. Extraction always indexes into this fixed allowlist, one name at a
# time - the header map is never copied wholesale - so a future Caddy
# config that stops redacting Authorization/Cookie cannot leak a
# credential into history.db.
_TELEMETRY_HEADER_ALLOWLIST = ("X-Fw-Version", "X-Boot-Reason", "X-Rssi", "X-Battery-Mv")

DEVICE_DISPLAY_URI = "/device/v1/display"


def utc_now_iso():
    """Timezone-aware UTC ISO-8601 string at seconds precision - matches
    the format server.plane.enrich.note_unresolved_prefix() already uses
    for first_seen/last_seen, so the two stores sort consistently.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def history_db_path(state_dir):
    return os.path.join(state_dir, HISTORY_DB_FILENAME)


def init_schema(conn):
    """Create all three tables (and their indexes/constraints) with
    IF NOT EXISTS, so both the poll oneshot and the companion service can
    call this safely on every connection.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runway_events ("
        "id INTEGER PRIMARY KEY, "
        "ts TEXT NOT NULL, "
        "hex TEXT, "
        "callsign TEXT, "
        "aircraft_type TEXT, "
        "confirmed_state TEXT, "
        # corroborated is stored as the TEXT of the three-state flag (the
        # string forms of true/false/none) - SQLite has no tri-state
        # boolean, and collapsing the unknown case into false would
        # destroy exactly the signal D-15 wants surfaced.
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
        # A re-tail of an overlapping log range cannot double-count -
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
    conn.commit()


def connect(state_dir, timeout=5.0):
    """Open (creating if needed) `<state_dir>/history.db`, apply the WAL +
    busy_timeout pragmas on this connection, ensure the schema exists, and
    return the connection. Callers are responsible for closing it - see
    `open_db()` below for a context-manager wrapper that does so
    automatically.
    """
    os.makedirs(state_dir, exist_ok=True)
    conn = sqlite3.connect(history_db_path(state_dir), timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    init_schema(conn)
    return conn


@contextlib.contextmanager
def open_db(state_dir, timeout=5.0):
    """`with open_db(state_dir) as conn:` - closes the connection on exit
    even if the block raises, so a request handler cannot leak a handle.
    """
    conn = connect(state_dir, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


# --- Writers -------------------------------------------------------------


def record_runway_event(conn, **fields):
    """Insert one `runway_events` row. `fields` may supply any subset of
    `_RUNWAY_EVENT_COLUMNS`; an omitted column is stored as NULL, except
    `ts` (defaults to `utc_now_iso()` when omitted) and `corroborated`
    (always stored as `str(value)` - "True"/"False"/"None" - never the raw
    Python object, so a hostile or malformed value can never reach SQL as
    anything but a parameterised text string). Every value is passed via a
    `?` placeholder (T-06-01-02, ASVS V5) - never string-formatted into the
    SQL text, so a callsign or airline name carrying HTML or a SQL quote is
    stored and returned byte-identical, never executed.
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
    conn.commit()


def record_device_health(conn, ts, battery_mv=None, fw_version=None, boot_reason=None, rssi=None):
    """Insert one `device_health` row, `INSERT OR IGNORE` against the
    `UNIQUE(ts, battery_mv)` constraint so a re-tail of an overlapping
    Caddy log range cannot double-count. Returns the number of rows
    actually inserted (0 or 1).
    """
    cur = conn.execute(_DEVICE_HEALTH_INSERT_SQL, (ts, battery_mv, fw_version, boot_reason, rssi))
    conn.commit()
    return cur.rowcount


# --- Readers ---------------------------------------------------------------


def recent_runway_events(conn, limit=50):
    """Newest first (`ts DESC, id DESC` - the tiebreak matters when two
    events share a timestamp at seconds precision).
    """
    rows = conn.execute(
        "SELECT * FROM runway_events ORDER BY ts DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def route_source_counts(conn, since=None):
    """`{route_source: count}` over `runway_events`, optionally restricted
    to `ts >= since` (an ISO-8601 string, compared with a `?` placeholder -
    never interpolated).
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
    """`{corroborated_text: count}` over `runway_events` - the three legal
    values ("True", "False", "None") are bucketed separately; the unknown
    ("None") case is never collapsed into "False".
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
    `datetime`, or `None` if it does not parse. A naive `ts` (no UTC
    offset) is taken as UTC.

    The ONE parse path in this module: `_paris_day_or_none()` below and
    `check_in_gaps()` further down both go through it, so a timestamp that
    buckets to a given Paris day can never simultaneously fail to date an
    interval on that same day. `ts` is `TEXT NOT NULL` but otherwise
    unvalidated and attacker-influenceable (see `tail_caddy_battery_log()`
    below), so every caller must handle the `None` return.
    """
    try:
        parsed = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _paris_day_or_none(ts):
    """Parse a stored `device_health.ts` string and return the `date` of its
    Europe/Paris calendar day, or `None` if `ts` does not parse. A naive
    `ts` (no UTC offset) is taken as UTC before converting - the same
    assumption SQLite's `date()` made, so a `2026-09-02T01:30:00+02:00`
    reading still buckets to `2026-09-02` in Paris, not `2026-09-01` in UTC.
    """
    parsed = _instant_or_none(ts)
    if parsed is None:
        return None
    return parsed.astimezone(ZoneInfo("Europe/Paris")).date()


def check_in_gaps(conn, since=None):
    """(24-03-PLAN.md Task 1, CFG-43) The OBSERVED intervals between
    consecutive `device_health` check-ins, oldest-first, one dict per
    interval:

        {"ts": <the later check-in's stored ts>,
         "from_ts": <the earlier check-in's stored ts>,
         "gap_s": <int seconds, or None when the span is undatable>,
         "day": <"YYYY-MM-DD" Europe/Paris day of `ts`, or None>}

    The key is deliberately named `ts`, not `to_ts` - the same
    row-shape-as-contract rule `daily_battery_averages()` states above:
    one emitter can bucket these rows by day alongside the battery rows
    with no adapter layer, and `day` comes from `_paris_day_or_none()`, the
    one Paris-day conversion in this module, so a grid drawn from these
    intervals and a chart drawn from the battery averages cannot disagree
    about which day a reading belongs to.

    `since`, when given, is an ISO-8601 string compared raw against `ts` in
    SQL through a `?` placeholder - the same `since` vocabulary and the
    same index-preserving shape `daily_battery_averages(conn, since=...)`
    uses, never a `date()` call wrapped around the left-hand side.  Like
    every other `since` in this codebase it is a DISPLAY window, never a
    retention bound: nothing is deleted (D-13).

    NO `battery_mv` FILTER, deliberately. A row whose `battery_mv` is NULL
    is a real check-in whose `X-Battery-Mv` header was absent or
    unparseable - `ingest_caddy_battery_log()` keeps one row per
    `/device/v1/display` access-log entry, not one per battery reading.
    Applying the `battery_mv IS NOT NULL` filter `daily_battery_averages()`
    legitimately uses would silently merge the intervals either side of
    such a row into one long gap, inventing a missed wake out of a missing
    HTTP header.

    ORDERED BY INGEST (`id`), not by `ts`. The SQL window predicate and
    ordering still run on `ts` so `idx_device_health_ts` is used, but the
    series is re-sorted by `id` in Python before intervals are taken,
    because `id` is assigned by `ingest_caddy_battery_log()` in the order
    Caddy appended the lines, whereas `ts` is attacker-influenceable. A
    hostile or malformed timestamp therefore cannot reorder the series
    around itself; it can only make the spans it bounds undatable.

    An interval is reported with `gap_s = None` - unknown, never a number -
    whenever either bound's `ts` does not parse, and whenever the later
    bound parses EARLIER than the earlier bound (a timestamp out of ingest
    order: its duration is not knowable). Dropping the offending row
    instead would merge two real intervals into one long false one that
    renders as a missed wake that never happened.

    Fewer than two rows in the window bounds no interval at all and returns
    `[]`. Nothing here raises.

    WHAT THIS READER CANNOT KNOW (24-RESEARCH.md Risk 1 - this travels with
    the data, not only with whatever caption is drawn from it; it is also
    why no name in this codebase calls the result an honoured-wake rate):

    - A LOG RANGE THE INGEST MISSED IS INDISTINGUISHABLE FROM A MISSED
      WAKE. `ingest_caddy_battery_log()` recovers a rotate-in-place (it
      resets its offset to 0 when the file is shorter than the stored
      offset) but cannot recover a rotation that moved the old file away
      between two ingests: that range is simply gone, and the resulting
      hole in `device_health` looks exactly like a device that did not wake
      up. No schema change recovers it. Related: `meta.caddy_log_offset` is
      the only ingest state kept, so "no rows in this window" cannot be
      distinguished from "the ingest did not run in this window" either.
    - `UNIQUE(ts, battery_mv)` CAN COLLAPSE TWO GENUINE CHECK-INS into one
      row - but only when they share a whole second AND a millivolt
      reading. `device_config.WAKE_INTERVAL_MIN_S` is 60, so two real
      consecutive wakes are at least 60 seconds apart at any configurable
      cadence and cannot land in the same second: at any cadence this
      deployment can be configured to, the collapse cannot lose a real
      wake. That is a provable bound, not a hope.

    Finally, this reader returns raw observed gaps and deliberately
    classifies nothing. `wake.device_staleness_thresholds()` is the single
    definition of "late" in this codebase and `wake.classify_check_in_gap()`
    is its one application to these intervals - kept in `wake.py` so the
    Frame tile and any grid drawn from these rows can never disagree, and
    so this module stays the leaf its own header promises (it must not
    import `device_config`, which `wake.py` does).
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
    """(22-06-PLAN.md Task 1) One row per Europe/Paris calendar day that has
    at least one numeric battery reading, newest day first: `{"ts":
    "YYYY-MM-DD", "battery_mv": <int>, "reading_count": <int>}`.

    The key is deliberately named `ts`, not `day` - it makes these rows
    structurally interchangeable with `recent_device_health()`'s rows for
    `battery_sparkline_svg()`, which reads exactly `battery_mv` and `ts`
    off whatever it is given. One plotting function, one row contract, no
    adapter layer.

    `battery_mv` is the mean of the bucket's `battery_mv` values rounded to
    the nearest integer in Python (`int(round(...))`) - `reading_count` is
    how many rows contributed to that average.

    Five facts (the first four preserved from the SQL version this
    replaced, re-verify before trusting, a stored `ts` is attacker-
    influenceable - see `tail_caddy_battery_log()` below):
    - The calendar day is now the Europe/Paris day, not the UTC day:
      bucketing happens in Python via `_paris_day_or_none()`, which
      converts through `ZoneInfo("Europe/Paris")` before taking `.date()`.
      `2026-09-02T01:30:00+02:00` -> Paris day `2026-09-02` (it was UTC day
      `2026-09-01` under the old `date(ts)` behaviour). Every other
      timestamp shape the writer produces (naive, `Z`-suffixed,
      space-separated, fractional seconds) still parses, via
      `datetime.fromisoformat()`.
    - A row whose `ts` does not parse forms no bucket at all, rather than a
      phantom NULL-keyed day - `ts` in this table is `TEXT NOT NULL` but
      not otherwise validated, and `tail_caddy_battery_log()` stores
      whatever string sits in a Caddy access-log entry's own `ts` field, so
      a hostile or malformed value can reach this column. `_paris_day_or_
      none()` catches the parse failure per row and returns `None`, which
      is filtered out before averaging - the same behaviour `date(ts) IS
      NOT NULL` provided.
    - The `battery_mv IS NOT NULL` filter stays in the SQL fetch: without
      it, a day with only NULL-battery rows would still form a bucket (an
      average of nothing would then choke the `int(round(...))` cast), and
      `reading_count` needs to mean "readings that contributed to this
      average", not "rows recorded on this day".
    - This is a read. D-13's keep-forever retention is untouched here or
      anywhere - `since`, like `BATTERY_TREND_LIMIT` elsewhere in this
      codebase, is a display window, never a retention bound. Nothing is
      deleted.
    - DST caveat, same accepted framing as `seconds_until_quiet_hours_end()`
      (`server/device_config.py`): there is no SQL fixed-offset modifier
      that is DST-correct for Europe/Paris (`date(ts, '+1 hours')` is wrong
      for half the year; `date(ts, 'localtime')` follows the server OS's
      timezone, not a fixed Europe/Paris), so the bucketing had to move to
      Python. `ZoneInfo` resolves the fold correctly across both
      transitions (the skipped March hour and the repeated October hour),
      which is the property a fixed-offset SQL modifier cannot have.

    The `since` cutoff still compares raw `ts` directly against the
    placeholder in SQL - never a `date()` call wrapped around the
    left-hand side - so `idx_device_health_ts` is still used; only the
    GROUP BY moved out of SQL.
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
    conn.commit()


# --- Caddy battery-log tailer (Pattern 6, D-03) -----------------------------
#
# Assumption A3 (06-RESEARCH.md): the exact JSON nesting of Caddy's logged
# request headers below (`request.headers.<Header-Name>` as a list of
# strings) is taken from Caddy's own documentation and has not been
# confirmed against a real captured line on the live host - plan 06-12
# confirms it there. Until then, a nesting mismatch degrades to "zero
# readings ingested" (every line's `request`/`headers` lookup comes back
# `None`/absent and is skipped), never to an exception.


def tail_caddy_battery_log(log_path, offset):
    """Read `log_path` from byte `offset` to EOF, one line at a time, and
    return `(readings, new_offset)`.

    Each line is a Caddy JSON access-log entry; a line that fails to parse
    as JSON (Caddy can leave a partial final line across a rotation) is
    skipped silently, as is any line whose request URI is not
    `DEVICE_DISPLAY_URI`. The four telemetry headers are extracted only by
    name from `_TELEMETRY_HEADER_ALLOWLIST` - the header map itself is
    never copied wholesale (T-06-01-03) - and each header value is taken
    as the first element of Caddy's list-of-strings representation. The
    battery value is coerced to `int` inside a `try`, yielding `None` on
    failure rather than raising. The entry's own `ts` field is used when it
    is a string; converted when it is a float/int epoch; and falls back to
    `utc_now_iso()` when absent.

    A missing or unreadable file returns `([], offset)` rather than
    raising.
    """
    readings = []
    try:
        with open(log_path) as fh:
            fh.seek(offset)
            for line in fh:
                line = line.strip()
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
                    ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc).isoformat(timespec="seconds")
                else:
                    ts = utc_now_iso()

                readings.append({
                    "ts": ts,
                    "battery_mv": battery_mv,
                    "fw_version": extracted.get("X-Fw-Version"),
                    "boot_reason": extracted.get("X-Boot-Reason"),
                    "rssi": extracted.get("X-Rssi"),
                })
            new_offset = fh.tell()
    except OSError:
        return [], offset
    return readings, new_offset


def ingest_caddy_battery_log(conn, log_path):
    """Read the stored `META_CADDY_LOG_OFFSET`, reset it to 0 when the file
    is now shorter than the stored offset (a rotation happened), tail the
    file, insert every reading via `record_device_health()`, store the new
    offset, and return the number of rows actually inserted (never the
    number of readings attempted - a re-tail of an already-seen range is
    silently ignored by the `UNIQUE(ts, battery_mv)` constraint). A missing
    log file returns 0 without raising.
    """
    if not os.path.exists(log_path):
        return 0

    stored_offset = get_meta(conn, META_CADDY_LOG_OFFSET)
    offset = int(stored_offset) if stored_offset else 0

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
