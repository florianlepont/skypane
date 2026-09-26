---
phase: 38-efficiency-companion-poll-cycle-storage
plan: 07
subsystem: backend
tags: [sqlite, transactions, poll-cycle, threading-local]

# Dependency graph
requires:
  - phase: 38-03
    provides: "server/history_db.py's connection_scope(state_dir), open_db()'s scope-aware yield, and write_batch(conn) - the storage-layer machinery this plan wires into the poll cycle without changing either signature"
provides:
  - "server/poll_loop.py: run_once() nests history_db.connection_scope(state_dir) inside poll_cycle_lock() for the whole cycle body, so every open_db() call _run_once_locked() makes on this thread shares one connection"
  - "server/poll_loop.py: _record_history() groups every write (runway_events insert, the three set_meta() calls, the Caddy ingest, the wake_epochs write) in one history_db.write_batch(conn), committed once before either _notify_silence_transition() call site ever runs"
  - "server/test_poll_efficiency.py: 6 tests proving 1 connection/1 commit across the research's seven poll-cycle branches, init_schema at most once across that sequence, the injected-snapshot path, no open write transaction during the notify send, a mid-batch failure rolling back as one unit, and run_once() nested inside an already-active connection_scope() opening no additional connection"
affects: [38-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "run_once() opens its connection_scope() INSIDE poll_cycle_lock(), never the other way round - the lock still serialises the whole cycle across processes, and the scope (a thread-local slot, per 38-03) only ever needs to outlive the cycle body on this one thread, so nesting order was never really a choice - it just had to be lock-outside/scope-inside to match poll_cycle_lock()'s own existing whole-cycle span"
    - "_record_history()'s write_batch() wraps the SAME open_db() block it always used - no new with-block nesting depth was added at that call site beyond the one new write_batch() layer, since open_db() itself already yields the scope's shared connection when called inside run_once()'s new connection_scope()"

key-files:
  created:
    - server/test_poll_efficiency.py
  modified:
    - server/poll_loop.py

key-decisions:
  - "Verified the fix by literally reverting server/poll_loop.py under git stash and re-running the new test file before committing anything - 4 of 6 tests failed against the pre-fix code (3 connections/commits per cycle, or a persisted runway_events row surviving a rolled-back batch), confirming the tests actually exercise the change rather than passing by construction"
  - "The no-transaction-during-notify test captures the cycle's own connection through a monkeypatched sqlite3.connect wrapper (proving there is exactly ONE), then opens a genuinely SEPARATE second connection via history_db.connect() (bypassing the active scope on purpose) from inside the fake notify sender, to prove the batch's row is visible to an independent reader - not just that the same connection reports in_transaction=False"

requirements-completed: []

# Metrics
duration: ~35min
completed: 2026-09-26
---

# Phase 38 Plan 07: One SQLite connection and one transaction per poll cycle Summary

**`server/poll_loop.py`'s `run_once()` now opens one `history_db.connection_scope(state_dir)` for the whole cycle, and `_record_history()` commits every write in one `history_db.write_batch(conn)` before any ntfy notification ever fires.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-26T17:05Z (approx.)
- **Completed:** 2026-09-26T17:40Z (approx.)
- **Tasks:** 1 completed (TDD: RED then GREEN)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `run_once()` now nests `with history_db.connection_scope(state_dir):` inside its existing `with poll_cycle_lock(...):`, and returns `_run_once_locked(...)` from inside it. Every `history_db.open_db(state_dir)` call the cycle makes on this thread - `_last_source_fault()`'s read, `_record_history()`'s writes, and both of `_run_once_locked()`'s `_notify_silence_transition()` call sites (the hold-branch early return and the shared tail) - now shares that one connection instead of each opening and closing its own.
- `_record_history()` now wraps its entire write sequence (the conditional `runway_events` insert, the two unconditional `set_meta()` calls, the conditional third `set_meta()`, the conditional Caddy ingest, and the conditional `wake_epochs` write) in one `with history_db.write_batch(conn):` block. The batch commits once as `_record_history()` returns, which is always before either `_notify_silence_transition()` call - so a write transaction is never open while the cycle's ntfy HTTP request runs. A mid-batch exception (still caught by the function's existing `except (sqlite3.Error, OSError)`) now rolls back every write the batch made, not just the one write call that raised.
- Both docstrings were updated to describe the new shape: `_record_history()`'s from "in one connection" to "in one connection and one transaction", spelling out the rollback-as-one-unit consequence; `run_once()`'s to describe the new `connection_scope()` nesting and its interaction with a caller (e.g. a future companion request handler) already inside an active scope for the same path.
- New `server/test_poll_efficiency.py` (6 tests): the research's seven poll-cycle branches (empty sky first/repeat, flight detected, same flight again, nothing new with a flight on screen, display_off hold entry/repeat) run in sequence against one state dir via `efficiency_probe.cycle_probe()`, each asserted at exactly 1 connection and 1 commit; `init_schema` asserted at most once across that whole sequence; the injected-`snapshot=` path asserted at exactly 1 connection; a cycle whose frame-silent notification fires asserted to have no open write transaction on its own (captured) connection while the fake `notify.send_notification` runs, with the batch's own meta row already visible from a second, independently-opened connection; a `history_db.set_meta()` failure asserted to leave zero `runway_events` rows behind even on a flight-detected cycle that would otherwise have written one; and `run_once()` called from inside an already-active `connection_scope()` asserted to open no additional connection.

## Task Commits

Task 1 ran RED then GREEN, per its TDD gate:

1. **Task 1: Cycle scope in run_once and one write_batch in _record_history**
   - `9cf2b4f` (test, RED): failing `server/test_poll_efficiency.py` - 4 of 6 tests fail against the pre-fix `poll_loop.py` (verified directly via `git stash` on `server/poll_loop.py` before committing the GREEN implementation)
   - `1ff7f71` (feat, GREEN): `connection_scope()` nesting in `run_once()`, `write_batch()` wrapping in `_record_history()`
   - `7922d32` (test, fixup): reworded the test module's docstring to drop a requirement ID `scripts/check_comment_history.py check` forbids in comments

## Files Created/Modified
- `server/test_poll_efficiency.py` - 6 tests: seven-branch connection/commit counts, cross-sequence `init_schema` bound, injected-snapshot path, no-transaction-during-notify with second-connection visibility, mid-batch-failure rollback, nested-`connection_scope()` reuse
- `server/poll_loop.py` - `run_once()` nests `history_db.connection_scope(state_dir)` inside `poll_cycle_lock()`; `_record_history()` wraps its writes in `history_db.write_batch(conn)`; both functions' docstrings updated

## Decisions Made
- Confirmed the fix by reverting `server/poll_loop.py` alone (via `git stash push -- server/poll_loop.py`) and re-running the new test file before ever committing the implementation - 4 of the 6 new tests genuinely failed against the unmodified code (3 connections/3 commits per cycle for the seven-branch test; a persisted `runway_events` row surviving a `set_meta()` failure for the rollback test), so the tests are proven to exercise the change, not just pass by construction.
- The no-transaction-during-notify test distinguishes "the cycle's own connection has no pending transaction" from "the batch's data is durable and visible elsewhere" as two separate assertions: a `sqlite3.connect` wrapper captures the cycle's one connection (proving there is exactly one), and the fake `notify.send_notification` additionally opens a genuinely independent second connection via `history_db.connect()` (bypassing the active `connection_scope()` on purpose, since `open_db()` inside the same scope would just hand back the same connection) to read the freshly-committed meta row from a different file handle.

## Deviations from Plan

`_last_source_fault()` and both `_notify_silence_transition()` call sites needed no code change, as the plan's own interfaces block anticipated: inside the new scope they transparently reuse the cycle's one connection through `open_db()`'s existing scope-aware behaviour from plan 03.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test module docstring's leading requirement ID tripped the comment-history check**
- **Found during:** Task 1, after the GREEN commit, running this plan's own `<verify>` block (`scripts/check_comment_history.py check`).
- **Issue:** `server/test_poll_efficiency.py`'s module docstring opened with `"""EFF-03 contract tests: ..."` - a plan/requirement ID in a comment, which `CLAUDE.md`'s "no plan/ticket/decision/phase IDs in comments" rule (enforced by `scripts/check_comment_history.py check`) forbids.
- **Fix:** Reworded the opening sentence to `"""Contract tests for one SQLite connection and one transaction per poll cycle.` - same meaning, no requirement ID.
- **Files modified:** `server/test_poll_efficiency.py`.
- **Commit:** `7922d32`.

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** Comment-wording only; no behaviour or test coverage changed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`connection_scope()` and `write_batch()` are now proven wired all the way through the poll cycle's own entry point, and `server/test_poll_efficiency.py` establishes the counting-instrument pattern (`efficiency_probe.cycle_probe()` over the research's seven branches) a later plan re-measuring this phase's efficiency gains can reuse directly. EFF-03 stays open: `38-08` (`depends_on: ["38-03"]`, the companion side) is the remaining half - nothing in `companion/app.py` or `companion/pages/*.py` calls `connection_scope()` yet. No blockers.

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
*Completed: 2026-09-26*

## Self-Check: PASSED

All created/modified files (`server/test_poll_efficiency.py`, `server/poll_loop.py`) and both task commits (`9cf2b4f`, `1ff7f71`) verified present.
