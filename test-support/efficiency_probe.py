"""Stdlib (+ repo modules) measurement instruments for the phase's six
efficiency findings: SQLite connections/schema-runs/statements/commits,
`time.sleep` calls, `poll_state.json` writes, per-route byte weight, and a
faked poll cycle's wall time and counts.

Every helper is a context manager that patches one production attribute
and always restores it on exit (`_patched`), so this module is safe to use
both under pytest (which has its own monkeypatch teardown) and from a
plain script (`scripts/measure_efficiency.py`, which has none). No
production code path is changed by importing this module: every count is
observed by wrapping an existing seam, never by adding a new one.

No pytest import here - a plain script must be able to use this module
directly.
"""
import contextlib
import copy
import gzip
import os
import sqlite3
import threading
import time
from collections import defaultdict

import companion_markup
from companion_app_server import http_request

import server.atomic_io as atomic_io
import server.history_db as history_db
import server.plane.detect as detect
import server.plane.enrich as enrich
import server.poll_loop as poll_loop

# Captured at import time, before anything in this module could have
# patched time.sleep - every recorder below sleeps through this, never
# through the (possibly patched) module attribute, so recorders never
# recurse into their own recording.
REAL_SLEEP = time.sleep

POLL_STATE_BASENAME = "poll_state.json"


@contextlib.contextmanager
def _patched(obj, name, value):
    """Swap `obj.name` for `value`, restoring the original attribute on
    exit even if the block raises.
    """
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield original
    finally:
        setattr(obj, name, original)


# --- SQLite connections / schema runs / statements / commits ---------------

class DbCounts:
    """Mutable counters filled in by `count_db()`'s patches. `by_thread`
    maps a thread name to the number of connections opened on it, so a
    caller can tell a same-thread reuse apart from genuine cross-thread
    activity.
    """

    def __init__(self):
        self.connections = 0
        self.init_schema = 0
        self.statements = 0
        self.commits = 0
        self.by_thread = defaultdict(int)


@contextlib.contextmanager
def count_db():
    """Context manager yielding a `DbCounts`, live-updated for the
    block's duration. Wraps `sqlite3.connect` (module attribute, so every
    caller that does `sqlite3.connect(...)` or `history_db.connect()` is
    counted) and `server.history_db.init_schema`. Every `sqlite3.connect`
    call installs a `set_trace_callback` on the new connection, counting
    every statement sent to SQLite (which includes the implicit COMMIT a
    `Connection.commit()` call issues) and every statement whose stripped
    upper-case text starts with "COMMIT". Guarded by a `threading.Lock`,
    since a poll cycle's provider workers or a `ThreadingHTTPServer`
    request thread may open a connection concurrently with another.
    """
    counts = DbCounts()
    lock = threading.Lock()
    real_connect = sqlite3.connect
    real_init_schema = history_db.init_schema

    def counting_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        with lock:
            counts.connections += 1
            counts.by_thread[threading.current_thread().name] += 1

        def trace(statement):
            with lock:
                counts.statements += 1
                if statement.strip().upper().startswith("COMMIT"):
                    counts.commits += 1

        conn.set_trace_callback(trace)
        return conn

    def counting_init_schema(conn):
        with lock:
            counts.init_schema += 1
        return real_init_schema(conn)

    with _patched(sqlite3, "connect", counting_connect), \
            _patched(history_db, "init_schema", counting_init_schema):
        yield counts


# --- time.sleep --------------------------------------------------------

@contextlib.contextmanager
def count_sleeps():
    """Context manager yielding a list, appended with every `time.sleep`
    duration called while the block is open (recorded, then actually
    slept through `REAL_SLEEP`, so timing-sensitive code under
    measurement still behaves the same wall-clock way).
    """
    calls = []

    def recording_sleep(seconds):
        calls.append(seconds)
        REAL_SLEEP(seconds)

    with _patched(time, "sleep", recording_sleep):
        yield calls


# --- poll_state.json writes ---------------------------------------------

@contextlib.contextmanager
def count_poll_state_writes():
    """Context manager yielding a list, appended with the encoded byte
    length of every `server.atomic_io.atomic_write` call whose path
    basename is `poll_state.json`. A write to any other filename (a
    panel, a gallery PNG, device_config.json, ...) passes through
    untouched and is not counted.
    """
    writes = []
    real_atomic_write = atomic_io.atomic_write

    def counting_atomic_write(path, data, mode=None):
        if os.path.basename(path) == POLL_STATE_BASENAME:
            payload = data if isinstance(data, bytes) else data.encode("utf-8")
            writes.append(len(payload))
        return real_atomic_write(path, data, mode=mode)

    with _patched(atomic_io, "atomic_write", counting_atomic_write):
        yield writes


# --- Faked ADS-B provider latency ---------------------------------------

@contextlib.contextmanager
def fake_provider_latency(latency_s, records_by_provider=None):
    """Context manager yielding a call log list, patching
    `server.plane.detect.query_provider` with a fake that sleeps
    `latency_s` (through `REAL_SLEEP`, never through a possibly-patched
    `time.sleep`, so the simulated network latency is unaffected by
    `count_sleeps()` running in the same `with` chain) then returns a
    deep copy of `records_by_provider.get(name, [])`. Each call appends
    `(name, start, end, thread_name)` to the log, guarded by a
    `threading.Lock`.
    """
    records_by_provider = records_by_provider or {}
    calls = []
    lock = threading.Lock()

    def fake_query_provider(name, lat, lon, radius_nm, timeout=None):
        start = time.time()
        REAL_SLEEP(latency_s)
        end = time.time()
        with lock:
            calls.append((name, start, end, threading.current_thread().name))
        return copy.deepcopy(records_by_provider.get(name, []))

    with _patched(detect, "query_provider", fake_query_provider):
        yield calls


# --- History seed --------------------------------------------------------

def seed_history(state_dir, n=30):
    """Seed `<state_dir>/history.db` with `n` `device_health` rows, `n`
    `runway_events` rows and a `META_LAST_PIPELINE_RUN` meta row - the
    same shape the research measured baseline numbers against.
    """
    with history_db.open_db(state_dir) as conn:
        for i in range(n):
            history_db.record_device_health(
                conn, ts=history_db.utc_now_iso(), battery_mv=3700 + i,
                fw_version="1.0.0", boot_reason="timer", rssi="-60",
            )
            history_db.record_runway_event(
                conn, hex="39a1b2", callsign="AFR%03d" % i,
                aircraft_type="A320", confirmed_state="departure",
                corroborated=True, route_source="fresh_hit",
                airline="Air France", origin="ORY", destination="JFK",
                tracked_runway="3",
            )
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, history_db.utc_now_iso())


# --- Per-route byte/time weight ------------------------------------------

def route_weight(server, path, cookie=None, repeats=5, extra_headers=None):
    """One warm-up GET, then `repeats` timed GETs of `path` against
    `server` (an `InProcessAppServer`), via
    `companion_app_server.http_request`. Returns a dict: `status`,
    `headers` (of the last timed response), `identity_bytes`,
    `gzip_bytes` (gzip level 6 of the last body), `ms` (mean over the
    timed requests), `script_srcs` (ordered `src` values of every
    `script[src]` node, parsed via `companion_markup.parse_html`; empty
    for a non-HTML response), and `connections`/`init_schema`/`commits`
    (this route's `count_db()` totals, averaged per request).
    """
    url = server.url(path)
    http_request(url, cookie=cookie, extra_headers=extra_headers)  # warm-up

    total_ms = 0.0
    totals = {"connections": 0, "init_schema": 0, "commits": 0}
    status = headers = body = None
    for _ in range(repeats):
        with count_db() as counts:
            start = time.perf_counter()
            status, headers, body = http_request(url, cookie=cookie, extra_headers=extra_headers)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
        total_ms += elapsed_ms
        totals["connections"] += counts.connections
        totals["init_schema"] += counts.init_schema
        totals["commits"] += counts.commits

    content_type = (headers or {}).get("Content-Type", "")
    script_srcs = []
    if content_type.startswith("text/html"):
        root = companion_markup.parse_html(body.decode("utf-8"))
        script_srcs = [node.attrs["src"] for node in root.select("script[src]")]

    n = max(repeats, 1)
    return {
        "status": status,
        "headers": headers,
        "identity_bytes": len(body or b""),
        "gzip_bytes": len(gzip.compress(body or b"", compresslevel=6)),
        "ms": total_ms / n,
        "script_srcs": script_srcs,
        "connections": totals["connections"] / n,
        "init_schema": totals["init_schema"] / n,
        "commits": totals["commits"] / n,
    }


# --- Poll-cycle probe -----------------------------------------------------

def cycle_probe(state_dir, latency_s=0.25, records=None, **run_once_kwargs):
    """Run one `server.poll_loop.run_once(state_dir=state_dir,
    **run_once_kwargs)` under every counter above, plus a fake
    `server.plane.enrich.default_transport` that returns `(404, None)`
    (an unresolved-callsign response, so a cycle never makes a real HTTP
    call). Returns a dict: `wall_s` (measured with
    `time.perf_counter`), `sleeps` (the list `count_sleeps()` recorded),
    `connections`, `init_schema`, `commits`, `poll_state_writes` (count),
    `poll_state_bytes` (sum of the recorded byte lengths), `state` (the
    cycle's own returned `"state"` value).

    `records` is the `records_by_provider` dict `fake_provider_latency`
    serves - the aircraft each provider name answers with (default: none
    see any traffic).
    """
    def fake_default_transport(callsign, timeout=None):
        return 404, None

    with _patched(enrich, "default_transport", fake_default_transport):
        with count_db() as db_counts, count_sleeps() as sleeps, \
                count_poll_state_writes() as writes, \
                fake_provider_latency(latency_s, records):
            start = time.perf_counter()
            result = poll_loop.run_once(state_dir=state_dir, **run_once_kwargs)
            wall_s = time.perf_counter() - start

    return {
        "wall_s": wall_s,
        "sleeps": list(sleeps),
        "connections": db_counts.connections,
        "init_schema": db_counts.init_schema,
        "commits": db_counts.commits,
        "poll_state_writes": len(writes),
        "poll_state_bytes": sum(writes),
        "state": result.get("state"),
    }
