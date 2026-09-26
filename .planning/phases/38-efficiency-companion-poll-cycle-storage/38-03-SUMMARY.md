---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 03
subsystem: storage
tags: [sqlite, threading-local, transactions, stdlib]

# Dependency graph
requires:
  - phase: 38-01
    provides: "test-support/efficiency_probe.py's count_db() (connections/init_schema/commits counters), reused directly by this plan's tests"
provides:
  - "server/history_db.py: connection_scope(state_dir) — a re-entrant, thread-bound context manager giving every open_db() call on the same thread inside it one lazily-opened connection, closed and rolled-back-if-pending only at the outermost exit"
  - "server/history_db.py: open_db(state_dir, timeout=5.0) — unchanged signature; scoped when a connection_scope for the same path is active on this thread, passthrough (today's connect/yield/close) otherwise; a scoped open failure is remembered and re-raised on every later call in the scope without retrying"
  - "server/history_db.py: schema and PRAGMA journal_mode=WAL now run once per process per database file identity (realpath, st_dev, st_ino), with an empty-file override so a restored or recreated history.db always gets it again"
  - "server/history_db.py: write_batch(conn) — defers every writer's commit while open, committing once on clean exit or rolling back and re-raising on an exception; a private _commit() keeps every writer's outside-a-batch behaviour identical to before this plan"
affects: [38-07, 38-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_SCOPE = threading.local() rather than contextvars.ContextVar: a scope must never be visible to a second thread even under a bare threading.Thread (whose ContextVar inheritance rules differ from a ThreadPoolExecutor's), and sqlite3's own check_same_thread=True already assumes one connection per OS thread"
    - "_HistoryConnection(sqlite3.Connection) carries the batch-depth counter as an instance attribute rather than a side dict keyed by id(conn), so the counter's lifetime is exactly the connection's own, with no separate cleanup path to forget"
    - "_commit(conn) is the one seam every writer calls instead of a bare conn.commit() — the same 'wrap an existing seam, don't add a seam per feature' shape efficiency_probe.py already established in 38-01"

key-files:
  created:
    - server/test_history_db_scope.py
  modified:
    - server/history_db.py

key-decisions:
  - "Schema-once is keyed by (os.path.realpath(path), st_dev, st_ino) from os.stat() taken after sqlite3.connect() (which creates the file if missing), with an st_size == 0 override that always reruns the schema on an empty file regardless of whether that exact key was already marked ready — covers a backup restore or a delete-and-recreate coincidentally reusing a retired inode number, without needing to force that collision in a test to prove the file-level behavior"
  - "write_batch()'s and _exit_batch()'s attribute writes are wrapped in try/except AttributeError so a bare sqlite3.Connection (never opened through this module's connect(), and therefore missing _batch_depth entirely) still behaves as a correct single-level batch instead of raising — proven directly by a test that opens a plain sqlite3.connect() and drives write_batch() through both a commit and a rollback"
  - "A connection_scope for a different path started while one is already active on the same thread is served exactly as if no scope were active at all (today's connect/yield/close on its own open_db call), rather than raising or queueing — the one thread-local slot can hold only one path, and this passthrough keeps every existing call site correct without a caller ever needing to know which scope, if any, is active"

requirements-completed: []

# Metrics
duration: 45min
completed: 2026-09-26
---

# Phase 38 Plan 03: history_db connection scope, schema-once, and write batching Summary

**Added `connection_scope`, a schema-once-per-file-identity guard, and `write_batch` to `server/history_db.py`, with all ~16 existing `open_db()` call sites and every writer left byte-for-byte unchanged outside a scope or batch.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-26T13:50Z (approx.)
- **Completed:** 2026-09-26T14:35Z (approx.)
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `connection_scope(state_dir)`: a re-entrant, thread-bound (`threading.local()`-backed) context manager. Every `open_db(state_dir)` call on the same thread inside it — however deeply nested — shares one connection, opened lazily on first use and closed (rolling back first if a write was left pending) only once the outermost scope exits. A `connection_scope` for a *different* path started while one is already active on the thread does not take over the slot; it is served exactly as if no scope were active. Another thread never sees this thread's scope, by construction.
- `open_db(state_dir, timeout=5.0)`: signature unchanged. Scoped when a `connection_scope` for the same path is active on this thread (yields the shared connection, does not close it); passthrough otherwise (today's connect/yield/close, unchanged). A scoped open failure (`sqlite3.Error`/`OSError`) is remembered for the rest of the scope and re-raised on every later call, so the ~12-connections-per-request problem in the research doesn't become 12 retried failures instead.
- Schema-once: `connect()` keys a process-wide, lock-guarded set by `(os.path.realpath(path), st_dev, st_ino)` and only runs `PRAGMA journal_mode=WAL` + `init_schema()` when that key is new *or* the file is empty (`st_size == 0`) — the latter guarantees a restored or deleted-and-recreated `history.db` always gets its schema again, even if the OS handed back a previously-seen inode number. `PRAGMA busy_timeout=5000` still runs on every connection.
- `write_batch(conn)`: connections now come from a small `sqlite3.Connection` subclass (`_HistoryConnection`) carrying a `_batch_depth` counter. `write_batch` defers commits while open and commits once on clean exit, or rolls back and re-raises on an exception. A private `_commit(conn)` — now called by `record_runway_event`, `record_device_health`, `record_wake_epoch` and `set_meta` instead of a bare `conn.commit()` — commits immediately whenever no batch is active, so every writer's behaviour outside a batch is identical to before this plan (`init_schema` keeps its own unconditional commit).
- `server/test_history_db_scope.py`: 17 tests, including two explicit branch-coverage tests (a different-path `connection_scope` nested inside an active one; `write_batch` driven against a bare `sqlite3.Connection` lacking `_batch_depth`) added after the first coverage run showed those two new branches untested.

## Task Commits

Each task was committed atomically, RED then GREEN per its TDD gate:

1. **Task 1: Thread-bound re-entrant connection_scope and scoped open_db**
   - `2a4ae7c` (test, RED): failing `server/test_history_db_scope.py` for `connection_scope`/scoped `open_db`
   - `66d7286` (feat, GREEN): `connection_scope`/`open_db` implementation
2. **Task 2: Schema once per database file identity, and write_batch with deferred writer commits**
   - `5f44c1f` (test, RED): failing schema-once/`write_batch` tests
   - `f214183` (feat, GREEN): schema-once guard, `_HistoryConnection`, `write_batch`, `_commit`, writer updates

## Files Created/Modified
- `server/test_history_db_scope.py` - 17 tests: scope sharing/nesting/passthrough/cross-thread isolation/failure-memo/pending-transaction-rollback, unscoped-open_db-unchanged, schema-once (3 connects, recreated-empty-file, two state dirs), write_batch (multi-writer single commit, exception rollback, unbatched-writer-still-commits, `ingest_caddy_battery_log` inside a batch, a plain-connection batch)
- `server/history_db.py` - `connection_scope`, scoped `open_db`, `_HistoryConnection`, `_SCHEMA_READY`/`_SCHEMA_LOCK`, `write_batch`, `_exit_batch`, `_commit`; the four writers now call `_commit(conn)`; module docstring's concurrency paragraph rewritten

## Decisions Made
- Keyed schema-once by file identity (device + inode) with an empty-file override, rather than only by path string, per the plan's T-38-11 mitigation for a restored/recreated `history.db`.
- Used `threading.local()` rather than `contextvars.ContextVar` for the scope slot, per the plan's own rationale: a `ContextVar`'s inheritance across a bare `threading.Thread` differs from a `ThreadPoolExecutor` worker across Python versions, and the scope must be strictly thread-bound to match sqlite3's `check_same_thread=True`.
- Left `write_batch`/`_exit_batch` tolerant of a plain `sqlite3.Connection` (via `try/except AttributeError` around the attribute writes) rather than requiring every caller to route through `history_db.connect()`, since the plan's action explicitly calls this out and a direct test now proves it.

## Deviations from Plan

**1. [Rule 2 - missing coverage] Added two branch-coverage tests not in the plan's behavior list**

- **Found during:** Task 2, after running coverage on `server/history_db.py` alone.
- **Issue:** The first coverage run showed two new branches from Task 1/2 uncovered: `connection_scope`'s "a different path is already scoped on this thread" passthrough (only exercised via `open_db` for a different path in the original test, never via a nested `connection_scope` itself), and `write_batch`/`_exit_batch`'s `except AttributeError` fallback for a connection without `_batch_depth` (never exercised, since every connection in the other tests comes from `history_db.connect()`, which always returns a `_HistoryConnection`).
- **Fix:** Added `test_nested_scope_for_a_different_path_is_also_served_unscoped` and `test_write_batch_on_a_plain_connection_still_commits_once`.
- **Files modified:** `server/test_history_db_scope.py`.
- **Commit:** `f214183` (included in the Task 2 GREEN commit, before it was made).

**2. [Rule 1 - bug] Reworded a comment that broke an existing regex-based test**

- **Found during:** Task 2, first full test run.
- **Issue:** `server/test_config_history.py::test_every_create_table_is_guarded_and_there_are_exactly_four` scans `history_db.py`'s raw source text for the literal substring `CREATE TABLE` and asserts every occurrence is immediately followed by `IF NOT EXISTS`. The new `_SCHEMA_READY` comment's phrase "4 CREATE TABLE + 2 CREATE INDEX statements" tripped this guard as an unguarded fifth occurrence.
- **Fix:** Reworded the comment to describe the same thing ("its table- and index-creation statements") without the literal phrase.
- **Files modified:** `server/history_db.py`.
- **Commit:** `f214183`.

## Issues Encountered

None beyond the two items above, both resolved before their task's commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`connection_scope`, `open_db`, and `write_batch` exist and are proven correct in isolation, but nothing calls `connection_scope` yet outside this plan's own tests — every one of the ~16 existing `open_db()` call sites in `companion/app.py`, `companion/pages/*.py`, and `server/poll_loop.py` still opens and closes its own connection today, exactly as before. Plans `38-07` and `38-08` (both declare `depends_on: ["38-03"]`) are the ones that wire the companion's request dispatch and the poll cycle's entry point into `connection_scope` and group their writes with `write_batch` - this plan is the storage-layer machinery those plans will consume without any caller signature change. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files and all four task commits (`2a4ae7c`, `66d7286`, `5f44c1f`, `f214183`) verified present.
