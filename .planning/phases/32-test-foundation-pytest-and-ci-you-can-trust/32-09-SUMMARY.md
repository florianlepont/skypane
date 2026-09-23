---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 09
subsystem: testing
tags: [pytest, migration-ledger, render, module-scoped-fixtures, tmp_path, ast-transform]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py DNS guard, test-support/skypane_test_support.py
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/server__test_render.txt transcript, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_render.py as a real pytest module (140 test functions covering all 140 baseline checks 1:1, 0 deleted) - the largest harness in the phase by check count
  - 1 ledger fragment under 32-ledger/ mapping all 140 baseline checks to node ids
  - a worked example of converting a harness's cross-check `ctx` dict (checks that read bytes an earlier check computed) into module-scoped pytest fixtures, decoupling shared-render checks from check-call order under xdist
affects: [32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A harness's `ctx = {}` dict, written by one check() and read by several later ones (server/test_render.py's departing_bytes/arriving_bytes, computed once by checks 1-2 and read by checks 3-6/9), becomes TWO `scope=\"module\"` pytest fixtures returning the computed bytes - not a mechanical transform, since the reading checks' defensive `if buf is None: return False, ...` branches become genuinely unreachable once a fixture guarantees the value exists, and were dropped rather than converted to a no-op assert."
    - "`tempfile.NamedTemporaryFile(suffix=X, delete=False)` used only for its `.name` (never its handle) becomes `str(tmp_path / \"some-name.ext\")` - no `.close()` call needed since nothing was ever written through the handle in this harness's 9 CLI-preview checks; a loop building N such names (the four-tier CLI-callsign sweep) gets `tmp_path / (\"cli-%d.png\" % i)` for a distinct name per iteration rather than reusing one path across iterations."
    - "`tempfile.mkdtemp()`/`tempfile.TemporaryDirectory()` become `str(tmp_path)` directly (no subdirectory needed) when the check only needs A writable directory to point a CLI flag at, dropping the `with`/`try/finally` wrapper entirely since pytest owns tmp_path's lifecycle."
    - "A helper function called by multiple check bodies to build a throwaway file (`_write_garbage_png()`/`_write_oversized_png()`, previously self-contained via `tempfile.NamedTemporaryFile()` and cleaned up by each caller's own `try/finally: os.unlink(...)`) is refactored to accept `tmp_path` as a parameter instead of calling `tempfile` itself - every caller becomes a fixture-parametrized test and the `os.unlink()` calls are dropped as dead code (tmp_path's own teardown supersedes them). Grepping only for the literal substring `tempfile.` under-counts which checks need `tmp_path` when a shared helper hides the call - the check functions calling `_write_garbage_png()`/`_write_oversized_png()` had to be found separately (by tracing the helper's own call sites), not by re-running the same grep."
    - "An AST-guided mechanical transform matched all 140 `check(label, fn)` call sites to their target `FunctionDef` (140/140 with zero ambiguity: every funcdef is the statement immediately preceding its check() call, confirmed programmatically before writing any output), then rewrote 124 of them automatically: `return False, X` -> `pytest.fail(X)` (via the Return node's own source span, preserving multi-line %-formatted reasons verbatim) and `return True, \"\"` -> deleted (safe only when it is the function's last statement - see the one behavioural fix below), reassembling the file from true-source-line chunks so every leading comment (including 3-line section-divider banners) travels with the statement it precedes. The remaining 16 checks (7 ctx-sharing, 9 tempfile-using) were excluded from the mechanical pass and hand-written directly against the fixture/tmp_path shape described above."
    - "`pytestmark = pytest.mark.slow` added at module scope: a single-worker run of this harness's 140 real Pillow renders takes ~21s, over the phase's own ~10s slow-marker threshold (32-CONTEXT.md planner_notes) - the first migrated harness in the phase to actually cross it."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_render.md
  modified:
    - server/test_render.py

key-decisions:
  - "All 140 old checks map 1:1 to 140 new pytest test functions - no consolidation and no parametrization, matching the baseline transcript exactly (every check() call, including the ones inside for-loops over THEME_IDS/RUNWAY_IDS/band ids, printed exactly one aggregate PASS line in the baseline, so per the 32-05/32-07/32-08 lesson the loop stays inside the test body rather than becoming @pytest.mark.parametrize)."
  - "The mechanical AST transform's blanket rule (\"every `return True, \"\"` is deleted\") is only correct when that return is the function's LAST statement. One check (`_unknown_state_still_raises_naming_all_three_states`, baseline check 57) had a `return True, \"\"` nested inside an `except ValueError:` block, guarding against fall-through to a final `return False, \"did not raise\"` line below the try/except - deleting it silently broke the check's own \"did not raise\" detection (confirmed by running the transformed suite: this was the only one of 140 that failed). Verified programmatically that this is the ONLY such case in the file (searched for any `return True` node that is not a direct top-level statement of its enclosing check function) before hand-fixing it with a bare `return` in place of the deleted tuple-return."
  - "`_write_garbage_png()`/`_write_oversized_png()` (module-level helpers shared by 3 checks) were changed to accept `tmp_path` as a parameter rather than keeping their own internal `tempfile.NamedTemporaryFile()` calls - this is a production-adjacent signature change to test-only helper code (not production code, MR-11 unaffected), chosen because threading `tmp_path` through the helper is the only way to satisfy MR-5 (no `tempfile.` call anywhere in the migrated file) without duplicating the PNG-fixture-building logic three times."
  - "No `@requires_non_root` marker anywhere in this file: confirmed by grep that the original harness has zero `os.chmod`/permission-bit checks (unlike test_calendar_rules.py or test_manual_resolutions.py) - every check in this harness asserts on rendered pixel/byte content or CLI exit codes, none on filesystem permission enforcement, so MR-8 does not apply to this migration."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (this is 32-09 of 8; server/test_poll_loop.py remains in 32-10) - not (re-)marked by this plan per the "every plan it spans" rule. TST-03 was already completed by plan 32-01.

# Metrics
duration: ~70min
completed: 2026-09-23
---

# Phase 32 Plan 09: Migrate test_render to pytest Summary

**server/test_render.py's 140-check render_panel()/build_canvas() poster-layout contract harness - the largest and slowest of the phase's 15 harnesses - is now 140 real pytest test functions, with the two expensive shared active-state renders promoted to module-scoped fixtures and every CLI-preview/undecodable-illustration check converted from `tempfile` to `tmp_path`.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 1
- **Files modified:** 2 (1 test module + 1 new ledger fragment)

## Accomplishments
- Converted `server/test_render.py` (4,167 lines, 140 `check()` calls covering `render_panel()`/`build_canvas()`'s byte-packing, nibble/palette legality, D-24 illustration-mirroring guard, D-25 full-color compositing, D-08/D-10 content-ladder text tiers, D-12 optical-offset geometry, D-26 tracked-glyph top row, per-theme dominance, battery-low/source-fault indicators, band themes, and the quiet_hours/display_off/battery_empty dimmed-hold screens) into 140 standalone pytest test functions, each carrying its old check label verbatim as the docstring.
- Built and ran an AST-guided mechanical transform for 124 of the 140 checks: matched each `check(label, fn)` call (verified 140/140 with zero ambiguity - every check's target funcdef is the immediately preceding top-level statement in `main()`, confirmed programmatically before writing output) to its helper `FunctionDef`, replaced every `return False, X` with `pytest.fail(X)` via the Return node's own source span, dropped every trailing `return True, ""`, and reassembled the module from true-source-line chunks so leading comments (including multi-line section-divider banners) travel with the statement they precede.
- Hand-converted the remaining 16 checks: 7 that shared `main()`'s old `ctx` dict (checks 1-2 compute `departing_bytes`/`arriving_bytes`, checks 3-6/9 read them) became two `scope="module"` pytest fixtures, decoupling those checks from check-call order under `-n 4`; 9 CLI-preview checks plus 3 undecodable-illustration checks converted from `tempfile.NamedTemporaryFile()`/`mkdtemp()`/`TemporaryDirectory()` to `tmp_path`, including refactoring the shared `_write_garbage_png()`/`_write_oversized_png()` helpers to accept `tmp_path` as a parameter (a grep for the literal substring `tempfile.` alone under-counted these 3 since the temp-file creation was hidden one call behind a shared helper).
- Fixed one genuine behavioural bug the mechanical transform's blanket "delete every `return True, \"\"`" rule exposed: `_unknown_state_still_raises_naming_all_three_states` (baseline check 57) had its `return True, \"\"` nested inside an `except ValueError:` block guarding against fall-through to a final "did not raise" failure - deleting it silently broke the check. Verified this was the only such case in the file (no other `return True` is non-top-level within its enclosing check function) before hand-adding a bare `return` in its place.
- Added `pytestmark = pytest.mark.slow` - a single-worker run takes ~21s (140 real Pillow canvas renders), the first migrated harness in the phase to cross the ~10s planner-notes threshold.
- All 140 baseline checks verified mapped by `32-ledger-check.py`: 140/140, 140 ported, 0 deleted, 0 pending.
- Passes under both `-n 0` and `-n 4` (140 passed each), `ruff check` clean, legacy-runner bridge (`server/.venv/bin/python3 server/test_render.py`) exits 0, zero `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` occurrences, zero new untracked files after a fresh run, zero production-code changes, zero `enable_socket` markers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_render** - `0d7f8ff` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_render.py` - 140 `test_*` functions; module docstring trimmed of the `EXPECTED_CHECK_COUNT` changelog comments (MR-10); `render`/`panel_format`/`illustrations`/`Image` now top-level imports; `departing_bytes`/`arriving_bytes` added as `scope="module"` fixtures; `_write_garbage_png()`/`_write_oversized_png()` now take `tmp_path`; `pytestmark = pytest.mark.slow` added
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_render.md` (new) - 140 rows, all `ported`

## Decisions Made
- No consolidation and no parametrization anywhere in this migration - every one of the 140 old checks (including the several that internally loop over `THEME_IDS`/`RUNWAY_IDS`/band theme ids) printed exactly one baseline PASS line and became exactly one node id, matching the baseline transcript and the ledger's strict 1:1 row-per-baseline-line requirement.
- Used an AST-guided mechanical transform for 124/140 checks and hand-wrote the remaining 16 (the ctx-sharing and tempfile-using ones) rather than trying to generalize the mechanical transform to cover those two shapes - both involve genuine restructuring (dict-to-fixture, tempfile-to-tmp_path with signature changes to a shared helper) rather than a pure text substitution, so hand-writing 16 functions against a clear target shape was both faster and safer than extending the script's edge-case handling for a one-off harness.
- Chose to thread `tmp_path` through `_write_garbage_png()`/`_write_oversized_png()` as a new parameter (rather than duplicating the PNG-fixture-building code inline in each of the 3 calling tests) to keep the fixture-construction logic in one place, matching how the helper was already shared before migration.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mechanical transform's blanket return-True deletion broke one check's control flow**
- **Found during:** Task 1, first full test run (`pytest -n 0`) - 139/140 passed, `test_unknown_state_still_raises_naming_all_three_states` failed
- **Issue:** The AST transform's rule "every `return True, \"\"` is deleted" is only sound when that return is the function's last statement (dead code otherwise, since Python falls off the end of a function returning `None` regardless). One check's `return True, ""` sat inside an `except ValueError:` block specifically to short-circuit BEFORE a later `return False, "did not raise"` line meant only for the no-exception-at-all path. Deleting it made every well-formed-exception case fall through into the same "did not raise" failure the check exists to prevent conflating with.
- **Fix:** Verified programmatically that this was the only one of 140 checks with a non-top-level `return True` inside its function body, then replaced the deleted line with a bare `return` (correct here since the caller only inspects pytest's own pass/fail outcome, not a return value).
- **Files modified:** `server/test_render.py`
- **Verification:** `pytest server/test_render.py -q -p no:cacheprovider` and `-n 4`, both 140 passed.
- **Committed in:** `0d7f8ff` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness (a real control-flow bug the mechanical transform's simplifying assumption introduced, not present in the original hand-rolled harness). No scope creep.

## Issues Encountered

None beyond the one auto-fixed transform bug above.

## Next Phase Readiness
- 14 of 15 server-side harnesses now migrated (13 through 32-08, plus `server/test_render.py` from this plan) - 622 of 769 baseline checks. `server/test_poll_loop.py` (32-10, 110 checks) is the only harness remaining.
- The ctx-dict-to-module-scoped-fixture pattern (for checks that read a shared expensive render computed by an earlier check) and the "grep for the direct call, then also trace shared helpers that hide it" lesson for tempfile-to-tmp_path conversions are both reusable if `test_poll_loop.py` has similar shapes.
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (1 more harness to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

`server/test_render.py`, the ledger fragment, and this summary confirmed present on
disk; task commit hash (`0d7f8ff`) confirmed present in `git log --oneline --all`.
