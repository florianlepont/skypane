---
phase: 36-state-integrity-and-device-protocol
plan: 07
subsystem: infra
tags: [flock, atomic-write, poll-loop, companion, traceback, adsbdb-cache, gallery]

# Dependency graph
requires:
  - phase: 36-01
    provides: "server/atomic_io.py: atomic_write(path, data, mode=None), exclusive_lock(lock_path, timeout_s, blocking=True), LockBusy"
  - phase: 36-05
    provides: "server/plane/calendar_rules.py, server/notify.py migrated onto atomic_io + http_fetch (no code this plan reuses directly, but confirms the atomic_io contract used here)"
  - phase: 36-06
    provides: "server/plane/enrich.py lookup_route()/resolve_route() now=None parameter (epoch seconds), TTL/LRU adsbdb cache"
provides:
  - "server/poll_loop.py: poll_cycle_lock(state_dir, timeout_s=None), PollBusy, POLL_LOCK_FILENAME, POLL_LOCK_WAIT_S; run_once(..., lock_timeout_s=None) wraps the unchanged cycle body (now _run_once_locked()) inside the lock"
  - "server/poll_loop.py: save_poll_state(), write_panel_atomic() and _save_to_gallery() all publish through atomic_io.atomic_write() - no fixed temp name left in the poll loop"
  - "server/poll_loop.py: main() catches PollBusy first (one line, no traceback) then the generic Exception (existing summary line + traceback.print_exc(file=sys.stdout))"
  - "server/poll_loop.py: _record_history(..., detected=False) - META_LAST_DETECTION advances on flight is not None or detected; the held branch passes detected=flight is not None"
  - "server/poll_loop.py: enrich.resolve_route() called with now=now_s() - the adsbdb cache's cached_at/TTL now follow the injected test clock end to end"
  - "companion/app.py: _handle_poll_now() calls run_once(lock_timeout_s=0), catching poll_loop.PollBusy before the generic except -> FLASH_KEY_POLL_ALREADY_RUNNING, never calling mark_poll_triggered"
  - "companion/app.py: the illustration upload's raw temp is a tempfile.mkstemp() name in the override dir; the encoded PNG is built in memory and published through atomic_io.atomic_write()"
affects: [37-11, 39-arc-01, 39-arc-02, 39-arc-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-process poll-cycle lock: poll_cycle_lock() wraps the whole cycle body in atomic_io.exclusive_lock(<state_dir>/poll.lock), translating LockBusy into the poll-cycle-specific PollBusy; lock_timeout_s=None (the oneshot) waits POLL_LOCK_WAIT_S=10s, lock_timeout_s=0 (the companion) raises at once, never blocking a request thread"
    - "Every poll-loop and companion state write now goes through atomic_io.atomic_write() - no writer in this codebase constructs its own fixed or pid-tagged temp name any more"
    - "detected= as an explicit keyword distinguishing 'this cycle's raw detection' from 'what reached the display', so a queued-not-shown aircraft still advances a last-detection timestamp"

key-files:
  created: [server/test_poll_lock.py, companion/test_poll_now_lock.py]
  modified: [server/poll_loop.py, server/test_poll_loop.py, companion/app.py]

key-decisions:
  - "The RED run of the two-process x 200 reproduction (server/test_poll_lock.py, before poll_cycle_lock existed) was run 5 times against the pre-change code: 4 of 5 failed with FileNotFoundError on the shared poll_state.json.tmp (a lost-update race on the fixed temp name - the FileNotFoundError comes from one process's os.replace() racing the other process's cleanup-on-exception unlink of the SAME fixed tmp path), 1 of 5 happened to pass. Full output captured below."
  - "main()'s PollBusy handling stays a single line with no traceback (an expected, bounded-wait outcome, not a bug), added in Task 1; the generic Exception branch's traceback.print_exc(file=sys.stdout) was deliberately deferred to Task 2's own commit, matching the plan's task split and this project's per-task TDD gate convention, even though both branches sit in the same main() function."
  - "poll_cycle_lock() reads POLL_LOCK_WAIT_S from the module global at call time (not as a Python default-argument value baked in at function-definition time), so a test that monkeypatches poll_loop.POLL_LOCK_WAIT_S is honoured without needing to reload the module."
  - "The comment-history guard (scripts/check_comment_history.py) flagged three early docstring/comment drafts that named INT-01/INT-07 directly ('(INT-01)' section headers, 'INT-07 deadline' prose); all three were reworded to describe the mechanism instead of the requirement ID, per this project's 'no plan/ticket/phase IDs in comments' rule - the guard now exits 0 across every file this plan touches."
  - "The illustration upload's raw temp keeps living inside override_dir (not a system tempdir) so validate_illustration_file()/Image.open() never cross a filesystem boundary reading it back; only its NAMING scheme changed (tempfile.mkstemp() instead of a key+pid string). The encoded PNG is never staged as a file at all any more - it is built into an io.BytesIO and published straight through atomic_io.atomic_write(), which owns its own unique temp name and self-cleans on failure, so the upload handler's own finally now unlinks only the one raw temp it created."

patterns-established:
  - "Pattern: a caller that needs 'serialise across processes, but never block a request thread' exposes its own Busy exception (PollBusy) over atomic_io.LockBusy, keeping atomic_io itself request-thread-agnostic - future phases (39-ARC-01/02) can reuse this shape for a state_store.py lock without importing atomic_io.LockBusy directly at call sites."
  - "Pattern: a durable-signal writer that must record 'this happened' on a strictly wider condition than one existing boolean parameter takes a new keyword (detected=) rather than overloading the existing parameter's meaning (flight=None still means 'nothing on the panel', detected=True separately means 'something was seen')."

requirements-completed: [INT-01, INT-02, INT-07, INT-08, INT-11, INT-13]

# Metrics
duration: 90min (includes one platform-side interruption between the Task 2 RED and GREEN commits)
completed: 2026-09-26
---

# Phase 36 Plan 07: Poll cycle - lock, atomic writes, traceback, clock wiring Summary

**Cross-process poll_cycle_lock() over atomic_io.exclusive_lock(<state_dir>/poll.lock) serialises run_once() across the systemd oneshot and the companion's POST /poll-now (proven by a two-process x 200 locked-increment reproduction ending at exactly 400, zero lost updates); every remaining fixed-.tmp/pid-tagged temp name in server/poll_loop.py and companion/app.py is gone, main() now prints a full traceback on a genuine cycle failure, a queued-but-undisplayed detection still advances "Last aircraft detected", and the adsbdb cache's TTL/LRU stamps now follow the injected poll clock end to end.**

## Performance

- **Duration:** ~90 min wall-clock across the session (includes one platform-side rate-limit interruption between the Task 2 test commit and its implementation commit; no work was lost - the harness resumed from the last commit exactly as instructed)
- **Started:** 2026-09-26T09:42:00Z (approx., first read of the plan, right after 36-06 completed)
- **Completed:** 2026-09-26T11:13:15Z
- **Tasks:** 2 (both TDD: test/RED then feat/GREEN)
- **Files modified:** 5 (2 created: `server/test_poll_lock.py`, `companion/test_poll_now_lock.py`; 3 modified: `server/poll_loop.py`, `server/test_poll_loop.py`, `companion/app.py`)

## Accomplishments

- **Task 1 (INT-01):** `server/poll_loop.py` gained `POLL_LOCK_FILENAME`/`POLL_LOCK_WAIT_S`, `PollBusy` and `poll_cycle_lock(state_dir, timeout_s=None)` - a context manager over `atomic_io.exclusive_lock(<state_dir>/poll.lock, ...)` that translates `LockBusy` into `PollBusy`. `run_once()`'s existing body moved unchanged into a private `_run_once_locked()`, called inside the lock; `run_once()` itself now takes `lock_timeout_s` (`None` waits `POLL_LOCK_WAIT_S=10s`, `0` raises `PollBusy` at once). `save_poll_state()` migrated onto `atomic_io.atomic_write()` in this same task (the reproduction needs a unique temp name to demonstrate zero lost updates). `main()` catches `PollBusy` first, printing the busy lock path and exiting 1 - distinct from a genuine cycle failure. `companion/app.py`'s `_handle_poll_now()` now calls `run_once(lock_timeout_s=0)` and catches `poll_loop.PollBusy` before the generic `except Exception`, answering the existing `poll_already_running` flash without ever blocking the request thread or consuming the poll-trigger cooldown.
- **Task 2 (INT-02, INT-11, INT-13, INT-08):** `write_panel_atomic()` and `_save_to_gallery()` now publish through `atomic_io.atomic_write()` - the gallery PNG is encoded into an `io.BytesIO` first, so a failed write never touches the filesystem beyond `atomic_write`'s own self-cleaning temp. `main()`'s generic exception handler now also calls `traceback.print_exc(file=sys.stdout)` after its existing one-line summary. `_record_history()` gained a `detected=False` keyword; `META_LAST_DETECTION` now advances when `flight is not None or detected`, and the held branch (a distinct aircraft detected but only queued, never displayed) passes `detected=flight is not None`. `enrich.resolve_route()` is now called with `now=now_s()`, so the adsbdb cache's `cached_at` stamp and TTL follow the same injected clock every other pacing decision in this module already used. `companion/app.py`'s illustration upload replaced its key+pid-tagged raw/encoded temp pair with a `tempfile.mkstemp()` raw temp plus an in-memory encode published through `atomic_io.atomic_write()`.
- 17 new/rewritten tests across `server/test_poll_lock.py` (the two-process x 200 reproduction), `server/test_poll_loop.py` (11 new tests: busy-lock promptness, wait-then-complete, `main()`'s busy-lock message, the panel/gallery round-trip, the gallery-failure containment, the traceback assertion, the queued-detection and held-cycle-unchanged pair, the clock-wiring stamp) and `companion/test_poll_now_lock.py` (2 tests: the busy flash without waiting, and the busy attempt not consuming the cooldown).

## Task Commits

Each task is a test (RED) then feat (GREEN) pair:

1. **Task 1: cross-process poll lock, reproduction, companion busy path (INT-01)**
   - `a9209ad` test(36-07): add the two-process x 200 poll-lock reproduction (RED)
   - `f3ee637` feat(36-07): serialise poll cycles across processes (INT-01)
2. **Task 2: remaining atomic writes, traceback, last detection, clock wiring (INT-02, INT-11, INT-13, INT-08)**
   - `4c5f9be` test(36-07): add failing coverage for remaining atomic writes, traceback, last-detection and clock wiring
   - `6d042e4` feat(36-07): finish the atomic-write migration, traceback, last-detection and clock wiring (INT-02, INT-11, INT-13, INT-08)

_No refactor commit was needed for either task._

## RED Run: the two-process x 200 reproduction against the pre-change code

Per the plan's action, `server/test_poll_lock.py` was first written with its child script falling
back to a no-op context manager (`getattr(poll_loop, "poll_cycle_lock", None) or (lambda sd:
contextlib.nullcontext())`) so it would run at all against the unmodified `9eb92a6`-descended
code, then run 5 times in a row:

| Run | Result |
|-----|--------|
| 1 | **FAILED** - one child exited 1 with `FileNotFoundError: [Errno 2] No such file or directory: '.../poll_state.json.tmp' -> '.../poll_state.json'` from `os.replace(tmp, path)` inside `save_poll_state()` |
| 2 | **FAILED** - the other child hit the identical `FileNotFoundError` on the same fixed `poll_state.json.tmp` path |
| 3 | **passed** - the race did not manifest this run (both processes happened to interleave without colliding on the shared fixed temp name) |
| 4 | **FAILED** - `FileNotFoundError` again |
| 5 | **FAILED** - `FileNotFoundError` again |

4 of 5 runs demonstrated the bug: two processes writing the shared fixed `poll_state.json.tmp`
name raced each other's `os.replace()`/cleanup-on-exception `os.remove()`, so one process's
`os.replace()` found the temp file already gone. This is exactly the lost-update/torn-file failure
mode INT-01 exists to close - not merely a missing-attribute error, since the RED test's `getattr`
shim let the reproduction run against the real (pre-lock) `save_poll_state()`. After landing
`poll_cycle_lock()` and migrating `save_poll_state()` onto `atomic_io.atomic_write()`, the same test
(with the `getattr` shim removed, calling `poll_loop.poll_cycle_lock` directly) was re-run 5 times
in a row per the plan's own acceptance criterion: all 5 passed, counter == 400 each time.

## Files Created/Modified

- `server/poll_loop.py` - `poll_cycle_lock()`/`PollBusy`/`POLL_LOCK_FILENAME`/`POLL_LOCK_WAIT_S`; `run_once()`/`_run_once_locked()` split; `save_poll_state()`, `write_panel_atomic()`, `_save_to_gallery()` on `atomic_io.atomic_write()`; `main()` catches `PollBusy` then adds `traceback.print_exc()` to the generic handler; `_record_history(..., detected=False)`; `enrich.resolve_route(..., now=now_s())`; module/function docstrings no longer cite byos's old fixed-`.tmp` scheme
- `server/test_poll_lock.py` (new) - the two-process x 200 locked-increment reproduction
- `server/test_poll_loop.py` - 11 new tests for the lock's caller-side contract, the remaining atomic writes, the traceback, the last-detection fix and the clock-wiring stamp
- `companion/app.py` - `_handle_poll_now()` calls `run_once(lock_timeout_s=0)` and catches `PollBusy`; the illustration upload's raw temp is `tempfile.mkstemp()`-named, the encoded PNG goes through `atomic_io.atomic_write()`; `_POLL_LOCK`'s comment documents it as the in-process fast path alongside `poll.lock`
- `companion/test_poll_now_lock.py` (new) - `/poll-now` answers `poll_already_running` without waiting on a lock held by another process, and the busy attempt does not consume the poll-trigger cooldown

## Decisions Made

See `key-decisions` in the frontmatter. In short: the RED run's 4-of-5 failure rate is recorded in
full above rather than summarized away; `main()`'s traceback addition was deliberately kept out of
Task 1's commit even though both exception branches sit in the same function, to keep the task
boundary (and its own RED/GREEN pair) clean; `poll_cycle_lock()` reads `POLL_LOCK_WAIT_S` from the
module global at call time so a monkeypatching test is honoured; three early comment/docstring
drafts that named requirement IDs directly were reworded once the comment-history guard flagged
them; the illustration upload's raw temp stays inside `override_dir` (only its naming changed) so
the existing decompression-bomb-guarding `validate_illustration_file()`/`Image.open()` calls never
cross a filesystem boundary.

## Deviations from Plan

None beyond what the plan itself specified as required actions (the RED-run recording, the
comment-guard rewording it implies, and the task-boundary split for `main()`'s two exception
branches) - plan executed as written.

## Issues Encountered

One platform-side rate-limit interruption occurred between Task 2's RED (test) commit and its
GREEN (feat) commit; per the orchestrator's own resume instructions, execution continued from the
last commit with no rework - Task 2's implementation, verification and commit proceeded exactly as
planned once resumed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every state write this phase's audit ledger flagged (`poll_state.json`, `panel.bin`, the gallery
  PNG, the illustration override) now goes through `atomic_io.atomic_write()`; the phase-wide
  `git grep` for a fixed or pid-tagged temp name across production Python prints nothing (the two
  documented out-of-scope exceptions - `deploy/backup/skypane_backup.py`'s per-archive
  `.partial-<name>` files and `deploy/activate.sh`'s deploy-time `.current.tmp` symlink swap - do
  not match the pattern either, consistent with CONTEXT's own scoping).
- This is the last plan of Phase 36: all 14 `INT-01`..`INT-14` requirements are now marked Complete
  in `.planning/REQUIREMENTS.md` (INT-03/04/05/06/09/10/12/14 by earlier plans in this phase;
  INT-01/02/07/08/11/13 by this plan).
- `poll_cycle_lock()`'s `PollBusy`-over-`atomic_io.LockBusy` shape and the `detected=` keyword
  pattern are both candidates for Phase 39's `state_store.py`/`ARC-01`/`ARC-02` decomposition to
  reuse, per this plan's own `patterns-established`.
- No blockers for Phase 37 (37-11, gated on this phase per `36-CONTEXT.md`, can now proceed: this
  plan left byos's server construction and outbound-connection surface untouched).

## Self-Check: PASSED

- FOUND: server/poll_loop.py
- FOUND: server/test_poll_lock.py
- FOUND: server/test_poll_loop.py
- FOUND: companion/app.py
- FOUND: companion/test_poll_now_lock.py
- FOUND commit a9209ad (test, Task 1 RED)
- FOUND commit f3ee637 (feat, Task 1 GREEN)
- FOUND commit 4c5f9be (test, Task 2 RED)
- FOUND commit 6d042e4 (feat, Task 2 GREEN)
- Full suite (`./scripts/run-all-tests.sh`): 2721 passed, 133 skipped (pre-existing
  Playwright-Chromium/root-euid skips in this sandbox), coverage 93.85% (floor 93.0%), exit 0
- `ruff check .` and `scripts/check_comment_history.py check` both exit 0

## TDD Gate Compliance

Both tasks show the required RED -> GREEN sequence in git log:
- Task 1: `a9209ad test(36-07): ...` then `f3ee637 feat(36-07): ...`
- Task 2: `4c5f9be test(36-07): ...` then `6d042e4 feat(36-07): ...`

No REFACTOR commit was needed for either task.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
