---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 07
subsystem: testing
tags: [pytest, migration-ledger, device-config, history-db, wake-battery-critical]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py DNS guard, test-support/skypane_test_support.py
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/server__test_config_history.txt transcript, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_config_history.py as a real pytest module (90 test functions covering all 90 baseline checks 1:1)
  - 1 ledger fragment under 32-ledger/ mapping all 90 baseline checks to node ids
  - a worked example of a large (2,633-line) pure check()->test mechanical migration with no consolidation and no parametrization, since none of this harness's checks were genuinely loop-emitted at the print level
affects: [32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A THEMES.items()-iterating check whose old harness printed exactly ONE aggregate PASS/FAIL line (the loop lives inside the check function's own body, not around repeated check() call sites) stays ONE pytest test with the loop preserved in the test body - only a check whose OLD harness printed a SEPARATE PASS/FAIL line per loop iteration becomes @pytest.mark.parametrize (per the 32-03..32-06 lesson and MR-1); server/test_config_history.py has 8 THEMES-iterating checks and none of them qualify, confirmed by baseline transcript inspection, not by source grep."
    - "tempfile.mkdtemp(prefix=...)/try:/finally: shutil.rmtree(tmpdir, ignore_errors=True) becomes a bare `tmpdir = tmp_path` assignment as the first body statement, with the try/finally wrapper removed and its body dedented one level - preserves every downstream `tmpdir`-named reference unchanged (no variable renaming needed) while satisfying MR-5 (no tempfile. call, pytest owns cleanup)."
    - "return False, \"reason\" (or a %-formatted, possibly multi-line, reason) becomes pytest.fail(\"reason\") in place; return True, \"\" is dropped entirely (falls off the end of the function) - preserves every early-exit code path and every leading/interstitial explanatory comment byte-for-byte, since the transform touches only the two return-statement shapes and leaves every other line in the function body untouched."
    - "server/history_db.py's own module docstring forbids importing device_config, which server/wake.py does - so the classify_check_in_gap()/battery-critical checks that need both device_config and history_db symbols stay in this harness (their original home) rather than moving to a hypothetical wake-specific file; device_config, panel_format, history_db, and wake are now four plain module-level imports (the old per-section try/except ImportError guards are gone - pytest's own collection-error reporting subsumes them, MR-2)."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_config_history.md
  modified:
    - server/test_config_history.py

key-decisions:
  - "All 90 old checks map 1:1 to 90 new pytest test functions - no consolidation (MR-4) and no parametrization, because inspecting the actual baseline transcript (not source grep) showed every check(), including the 8 that internally loop over device_config.THEMES.items(), prints exactly one PASS/FAIL line. Parametrizing those 8 anyway would have required inventing per-theme labels the baseline never had, breaking the ledger's strict 1:1 row-to-baseline-line mapping."
  - "Used an AST-based mechanical transform (not hand-editing 2,633 lines) to guarantee correctness at this scale: each check(label, fn) call site is matched to its helper FunctionDef, tempfile.mkdtemp()/try/finally is structurally unwrapped in favour of tmp_path, every `return False, X` Return node's exact source span is replaced with `pytest.fail(X)` using precise line/column offsets (not regex), and the trailing `return True, \"\"` is dropped - preserving all interior comments, blank lines, and nested helper functions (e.g. test_read_battery_critical_is_fail_open's two local _write_raw/_write_json closures) exactly as they were."
  - "_GAP_T0/_GAP_T1/_GAP_T2 (three shared check_in_gaps() timestamp fixtures) and the _caddy_log_line() helper moved from main()-local scope to module scope, since four/one test functions respectively now reference them directly as top-level names."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (this is 32-07 of 8; server/test_calendar_rules.py, test_render.py, test_poll_loop.py remain in 32-08..32-10) - not (re-)marked by this plan per the "every plan it spans" rule. TST-03 was already completed by plan 32-01.

# Metrics
duration: ~45min
completed: 2026-09-23
---

# Phase 32 Plan 07: Migrate test_config_history to pytest Summary

**server/test_config_history.py's 90-check device_config.py/history_db.py/wake.py contract harness is now 90 real pytest test functions, one per baseline check with zero consolidation or parametrization, passing under `-n 4` with every path under `tmp_path` and every original explanatory comment preserved.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 1
- **Files modified:** 2 (1 test module + 1 new ledger fragment)

## Accomplishments
- Converted `server/test_config_history.py` (2,633 lines, 90 `check()` calls covering `device_config.py`'s theme registry/quiet-hours/wake-interval/theme_arriving/display_enabled/calendar_theme_id/screen_id/notifications fields, `history_db.py`'s runway-event/device-health/battery-averages/check-in-gap tables, and `wake.py`'s `classify_check_in_gap()`/battery-critical mirror) into 90 standalone pytest test functions, each carrying its old check label verbatim as the docstring.
- Built and ran an AST-based transform (not manual editing) to guarantee correctness across all 90 checks at this file size: matched each `check(label, fn)` call to its helper `FunctionDef`, structurally unwrapped `tempfile.mkdtemp()`/`try`/`finally: shutil.rmtree(...)` into a bare `tmpdir = tmp_path` assignment (55 of the 90 checks used this pattern), replaced every `return False, X` with `pytest.fail(X)` using precise AST offsets (26 of these spanned multiple physical lines with `%`-formatted tuples), and dropped every trailing `return True, ""` - while leaving every interior comment, blank line, and nested helper (`_write_raw`/`_write_json` closures, local `from datetime import ...` imports) untouched.
- Determined via the baseline transcript (not source grep) that none of the 8 `THEMES.items()`-iterating checks in this file were genuinely loop-emitted (each already printed exactly one aggregate PASS/FAIL line before migration), so per the 32-03..32-06 lesson they stay one test each with the loop preserved inside the test body - no parametrization was invented that the baseline never had.
- Moved `device_config`, `panel_format`, `history_db`, and `wake` to plain module-level imports (dropping the two `try/except ImportError` collection guards - pytest's own collection-error reporting subsumes them, MR-2) and promoted `_GAP_T0`/`_GAP_T1`/`_GAP_T2` and `_caddy_log_line()` from `main()`-local to module scope.
- All 90 baseline checks verified mapped by `32-ledger-check.py`: 90/90, 90 ported, 0 deleted, 0 pending.
- Passes under both `-n 0` and `-n 4` (90 passed), `ruff check` clean, legacy-runner bridge (`server/.venv/bin/python3 server/test_config_history.py`) exits 0, zero `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` occurrences, zero new untracked files after a fresh run, zero production-code changes, zero `enable_socket` markers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_config_history** - `ecf2a93` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_config_history.py` - 90 `test_*` functions; module docstring trimmed of the ~110-line `EXPECTED_CHECK_COUNT` phase/plan/ticket changelog (MR-10); `device_config`/`panel_format`/`history_db`/`wake` now top-level imports; `_GAP_T0`/`_GAP_T1`/`_GAP_T2`/`_caddy_log_line()` promoted to module scope
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_config_history.md` (new) - 90 rows, all `ported`

## Decisions Made
- No consolidation and no parametrization anywhere in this migration (unlike 32-05's `test_illustrations.py` or 32-06's `test_poll_cycle.py`) - every one of the 90 old checks was already independent (its own `tmpdir` or no filesystem interaction at all) and printed exactly one baseline line, so a 1:1 `check()` -> `test_*` mapping was both the simplest and the most faithful translation.
- Chose an AST-driven mechanical transform over hand-editing given the file's size (2,633 lines) and check count (90): manual editing at this scale carries meaningfully higher risk of silently dropping a comment, mis-transcribing a multi-line `%`-formatted message, or breaking a nested closure than a script whose output was verified statement-by-statement against the original AST and then proven behaviourally identical by running all 90 tests to green.

## Deviations from Plan

None - plan executed exactly as written. The migration_rules (MR-1..MR-13) were applied directly with no need for a production-code fix, no DNS-stub gap (this harness never resolves an external hostname), and no root-safety skip (no `os.chmod` checks in this harness).

## Issues Encountered

None.

## Next Phase Readiness
- 7 of 15 server-side harnesses now migrated (9 harnesses through 32-06, plus `server/test_config_history.py` from this plan) - 369 of 769 baseline checks. `server/test_calendar_rules.py` (32-08), `server/test_render.py` (32-09), and `server/test_poll_loop.py` (32-10) remain.
- The AST-based mechanical-transform approach (match `check()` call to helper `FunctionDef`, unwrap `tempfile.mkdtemp()`/`try`/`finally`, offset-precise `return False` -> `pytest.fail()` substitution) is reusable by any later plan migrating a large, purely-independent-checks harness with no genuine loop-emission or shared subprocess state to worry about.
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (3 more harnesses to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

`server/test_config_history.py`, the ledger fragment, and this summary confirmed present on
disk; task commit hash (`ecf2a93`) confirmed present in `git log --oneline --all`.
