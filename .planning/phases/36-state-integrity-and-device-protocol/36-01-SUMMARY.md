---
phase: 36-state-integrity-and-device-protocol
plan: 01
subsystem: infra
tags: [atomic-write, fcntl, flock, tempfile, concurrency, stdlib]

# Dependency graph
requires: []
provides:
  - "server/atomic_io.py: atomic_write(path, data, mode=None), staged_write(path, data, mode=None), exclusive_lock(lock_path, timeout_s, blocking=True), LockBusy, DEFAULT_FILE_MODE, LOCK_POLL_S"
affects: [36-03, 36-04, 36-05, 36-06, 36-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One same-directory mkstemp + fsync + os.replace atomic write helper, replacing every fixed '.tmp' or pid-only temp name in server/, stub-server/ and companion/"
    - "One exclusive_lock(lock_path, timeout_s, blocking) over fcntl.flock, generalising calendar_rules._calendar_registry_lock for poll.lock, device_config.lock and the calendar registry lock"

key-files:
  created: [server/atomic_io.py, server/test_atomic_io.py]
  modified: []

key-decisions:
  - "G-35 gate re-verified independently before any edit: 23 35-*-SUMMARY.md on origin/main, 35-VERIFICATION.md status passed on HEAD, ROADMAP Phase 35 fully checked, origin/main is an ancestor of HEAD -- all four checks passed, no edits made by that task."
  - "Umask read via /proc/self/status's 'Umask:' line (present on this Linux runner: 0022), not the racy os.umask(0)/os.umask(old) pair; the racy pair is kept only as a fallback for a platform without /proc, and is exercised by a dedicated test that fakes /proc's absence."
  - "Task 2's GREEN commit only implements atomic_write/staged_write per the plan's task split; exclusive_lock/LockBusy/LOCK_POLL_S and the lock-order docstring paragraph are added in Task 3's own RED/GREEN pair, reading server/atomic_io.py as Task 2 left it."
  - "Added 8 extra tests beyond the plan's required behaviour list to close a coverage shortfall the new module's defensive branches (no-/proc fallback, no-fcntl fallback, write failure after temp open, already-deleted temp at cleanup, an unrelated OSError from flock) caused against the repo's 93.0% floor -- ./scripts/run-all-tests.sh went from 92.93% to 93.11% after adding them (Rule 1/2: the coverage gate is a correctness requirement, not scope creep)."

patterns-established:
  - "Pattern: atomic_write/staged_write -- validate data type before touching the filesystem, fchmod the temp fd before any byte is written, fsync the file (not the directory) before os.replace, unlink the temp on any failure path including a cleanup unlink racing a second deleter."
  - "Pattern: exclusive_lock -- os.open(O_CREAT|O_RDWR, 0o600), poll fcntl.flock(LOCK_EX|LOCK_NB) to a monotonic deadline (or fail at once with blocking=False), raise LockBusy (a TimeoutError subclass), unlock and close in finally, no-op on a platform without fcntl."

requirements-completed: [INT-01, INT-02]

# Metrics
duration: 25min
completed: 2026-09-26
---

# Phase 36 Plan 01: atomic_io primitives Summary

**One stdlib `server/atomic_io.py` module: `atomic_write`/`staged_write` (unique-name mkstemp + fsync + os.replace, mode set on the temp fd before rename) and `exclusive_lock` (a reusable `fcntl.flock` lock with a `LockBusy` timeout), proven by 19 behaviour tests including 8 threads x 50 writes, 2 OS processes x 200 writes, and cross-process/cross-thread lock exclusion.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-26T07:20:00Z (approx., first read of the plan)
- **Completed:** 2026-09-26T07:40:34Z
- **Tasks:** 3 (1 gate check, 2 TDD)
- **Files modified:** 2 (both created: `server/atomic_io.py`, `server/test_atomic_io.py`)

## Accomplishments
- Confirmed Phase 35 is complete on `main` (gate G-35) before making any edit.
- Landed `atomic_write`/`staged_write`: a same-directory `mkstemp` + `fchmod` + write + `fsync` + `os.replace`, with `DEFAULT_FILE_MODE` reproducing `open()`'s own `0o666 & ~umask` so a caller migrating from `open()` keeps its current file mode unless it asks for a different one.
- Landed `exclusive_lock`/`LockBusy`: one cross-process, cross-thread `fcntl.flock` lock generalising `calendar_rules._calendar_registry_lock`, ready for INT-01's poll lock, INT-03's `device_config.lock` and the calendar registry lock (36-05 will make `calendar_rules` delegate to it).
- 19 behaviour tests: str/bytes round trip, default and explicit mode (including "temp file mode at the moment of `os.replace`"), a failed `os.replace` and an unsupported data type both leaving no temp, 8 threads x 50 writes and 2 OS processes x 200 writes to one path each producing exactly one complete 64 KiB payload with no leftover temp, `staged_write`'s commit/rollback contract, cross-process and cross-thread lock exclusion with correctly-bounded timing, `LockBusy` as a `TimeoutError` subclass, the lock file's parent-directory creation and 0600 mode, and lock release on an exception inside the block.

## Task Commits

Each task was committed atomically (Task 1 made no changes, so it has no commit):

1. **Task 1: Gate G-35 (Phase 35 complete on main)** - no commit (read-only check; all four automated checks passed, `git status --porcelain` empty)
2. **Task 2: atomic_write and staged_write (INT-02)** - `481fbc9` (test, RED) + `08352b2` (feat, GREEN)
3. **Task 3: exclusive_lock and LockBusy** - `1151e42` (test, RED) + `1d420f3` (feat, GREEN, includes the added coverage tests)

_TDD tasks: each is a test → feat pair (RED then GREEN); no refactor commit was needed._

## Files Created/Modified
- `server/atomic_io.py` - `DEFAULT_FILE_MODE`, `staged_write`, `atomic_write`, `LockBusy`, `LOCK_POLL_S`, `exclusive_lock`; module docstring documents the write contract and the lock order (`threading.Lock` -> `poll.lock` -> `calendar_rules.lock`, `device_config.lock` never held with another file lock)
- `server/test_atomic_io.py` - 19 behaviour tests covering both the plan's required behaviour list and the module's own defensive branches

## Decisions Made
- Umask source on this runner: `/proc/self/status`'s `Umask:` line (value `0022` observed locally), not the `os.umask(0)`/`os.umask(old)` fallback pair. The fallback path is still real code, exercised by `test_read_umask_falls_back_without_proc`, which fakes `open("/proc/self/status")` raising `OSError`.
- Kept Task 2 and Task 3 strictly to their planned scope (write helpers only, then lock helpers only), per the plan's own task split and the "one writer per file per wave" convention -- `exclusive_lock` was not added early even though the interfaces section describes it as part of the same file.
- See `key-decisions` in the frontmatter for the coverage-gate fix; it is elaborated in Deviations below since it is Rule 1/2 auto-fixed work not in the plan's task list.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/2 - Coverage gate correctness] Added 8 tests for atomic_io.py's defensive branches**
- **Found during:** Task 3, after the GREEN implementation, running `./scripts/run-all-tests.sh` per the plan's own verification step
- **Issue:** The new 87-statement module landed at 77% coverage on its own defensive branches (the `/proc`-less umask fallback, the no-`fcntl` lock fallback, a write failure after the temp file is opened, an already-deleted temp file at cleanup time, and an unrelated `OSError` from `flock` that must propagate rather than becoming `LockBusy`), none of which the plan's required behaviour list exercises. This pulled the whole-repo coverage from wherever it stood before this plan down to 92.93%, below the repo's 93.0% floor (`[tool.coverage.report] fail_under` in `pyproject.toml`) -- `./scripts/run-all-tests.sh` printed `FAIL Required test coverage of 93.0% not reached. Total coverage: 92.93%` even though the pytest process itself exited 0.
- **Fix:** Added `test_read_umask_falls_back_without_proc`, `test_staged_write_failure_during_write_leaves_no_temp`, `test_staged_write_cleanup_tolerates_already_deleted_temp`, `test_exclusive_lock_without_fcntl_yields_unlocked` and `test_exclusive_lock_propagates_unrelated_oserror` to `server/test_atomic_io.py`, each targeting one previously-uncovered branch by faking the platform condition (a failing `open("/proc/self/status")`, `atomic_io.fcntl = None`, a failing `os.fsync`, a temp file deleted mid-block, a failing `fcntl.flock` with an unrelated errno) rather than reading any source text.
- **Files modified:** `server/test_atomic_io.py` (tests only; no production code change was needed -- the branches were already correct, just untested)
- **Verification:** `server/atomic_io.py` coverage went from 77% (20 lines missing) to 98% (2 lines missing, an unreachable double-failure edge in the write-failure cleanup path); `./scripts/run-all-tests.sh` now reports `Required test coverage of 93.0% reached. Total coverage: 93.11%`, exit 0, 2597 passed / 132 skipped (all Playwright-Chromium or root-euid skips, pre-existing and expected in this sandbox).
- **Committed in:** `1d420f3` (Task 3's GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 coverage-gate correctness fix, Rule 1/2)
**Impact on plan:** No scope creep on production code -- the fix is test-only, closing a gap the plan's own verification step (`./scripts/run-all-tests.sh`) is what surfaced. `server/atomic_io.py` itself is unchanged from the exact interface contract in the plan.

## Issues Encountered
None beyond the coverage-gate deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/atomic_io.py` is ready for 36-03..36-07 to migrate their fixed-`.tmp`-name and pid-only-name writers onto `atomic_write`/`staged_write`, and their ad hoc locks onto `exclusive_lock`.
- byos (`stub-server/byos_server.py`) still needs its own local `_atomic_write` copy in 36-03 (documented "never import `server.*`" vendor boundary, retired only in Phase 39's ARC-05) -- this plan does not touch `stub-server/`.
- No blockers for wave 2 (36-03..36-06).

## Self-Check: PASSED

- FOUND: server/atomic_io.py
- FOUND: server/test_atomic_io.py
- FOUND commit 481fbc9 (test RED, Task 2)
- FOUND commit 08352b2 (feat GREEN, Task 2)
- FOUND commit 1151e42 (test RED, Task 3)
- FOUND commit 1d420f3 (feat GREEN, Task 3)

## TDD Gate Compliance

Both TDD tasks show the required RED -> GREEN sequence in git log:
- Task 2: `481fbc9 test(36-01): ...` then `08352b2 feat(36-01): ...`
- Task 3: `1151e42 test(36-01): ...` then `1d420f3 feat(36-01): ...`

No REFACTOR commit was needed for either task.

---
*Phase: 36-state-integrity-and-device-protocol*
*Completed: 2026-09-26*
