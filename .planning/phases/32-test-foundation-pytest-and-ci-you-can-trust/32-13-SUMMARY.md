---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 13
subsystem: testing
tags: [pytest, pytest-cov, coverage, subprocess-coverage, migration-ledger, ci]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure and the 15 migrated server/stub-server pytest files (32-01 through 32-12)
provides:
  - Assembled and verified 32-MIGRATION-LEDGER.md (769/769 baseline checks accounted for, 0 pending)
  - scripts/run-all-tests.sh rewritten as a thin `pytest -n auto --cov` wrapper (PYTHON=/JOBS= contract kept)
  - scripts/run_all_tests.py retired (hand-rolled HARNESSES list + coverage combine/report gone)
  - pyproject.toml [tool.coverage.run] patch = ["subprocess"] (subprocess coverage measurement)
  - 15 migrated files with their legacy-runner pytest.main bridges removed
affects: [32-14-ci-workflow-rewrite, 32-15-measure-and-lower-omit-list]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "coverage.py patch=[\"subprocess\"] (coverage >= 7.10) as the sole subprocess-coverage mechanism, replacing pytest-cov's removed .pth injection"
    - "scripts/run-all-tests.sh as a pure exec wrapper: bash owns only the PYTHON=/JOBS=/COVERAGE_CORE contract, pytest owns everything else"

key-files:
  created: []
  modified:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-MIGRATION-LEDGER.md
    - scripts/run-all-tests.sh
    - pyproject.toml
    - server/test_calendar_rules.py
    - server/test_colour_rules.py
    - server/test_config_history.py
    - server/test_dither.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_manual_resolutions.py
    - server/test_notify.py
    - server/test_panel_preview.py
    - server/test_pipeline_e2e.py
    - server/test_plane_detection.py
    - server/test_poll_loop.py
    - server/test_render.py
    - server/test_runway_config.py
    - stub-server/test_poll_cycle.py
    - companion/test_browser_ux.py
    - companion/test_browser_ux_health_drawings.py
    - companion/test_browser_ux_quiet_wake.py
    - companion/test_browser_ux_helpers.py
    - companion/test_legacy_harness_shim.py
  deleted:
    - scripts/run_all_tests.py

key-decisions:
  - "Left [tool.coverage.run] source/omit/fail_under=83 unchanged per the plan; 32-15 measures and lowers them once companion/app.py, byos_server.py and make_test_panel.py leave the omit list"
  - "Fixed 5 stale scripts/run_all_tests.py comment references in companion/test_browser_ux*.py and test_legacy_harness_shim.py that the retirement left dangling (Rule 1), since the plan's own acceptance criteria require zero non-doc occurrences of the retired filename repo-wide"

requirements-completed: [TST-01, TST-09]

# Metrics
duration: ~35min
completed: 2026-09-23
---

# Phase 32 Plan 13: Retire the legacy test runner; pytest + pytest-cov become the single entry point Summary

**`scripts/run_all_tests.py`'s hand-rolled `HARNESSES` list and manual `coverage combine`/`report` retired; `scripts/run-all-tests.sh` is now a thin `pytest -n auto --cov` wrapper, subprocess coverage is measured via coverage.py's `patch = ["subprocess"]`, and the phase 32 migration ledger is assembled and verified against all 769 pre-migration baseline checks.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-23
- **Tasks:** 3/3 completed
- **Files modified:** 22 (1 deleted, 21 modified)

## Accomplishments
- `32-ledger-check.py --all` passes for all 15 server-side harnesses (769/769 baseline checks mapped, 0 pending); `--assemble` regenerated `32-MIGRATION-LEDGER.md` with grand totals (769 baseline, 769 ported, 0 deleted) matching `32-BASELINE/INDEX.md` exactly.
- `scripts/run_all_tests.py` deleted; `scripts/run-all-tests.sh` rewritten as `exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov ...`, keeping the `PYTHON=`, `JOBS=` and `COVERAGE_CORE=sysmon` (3.12+) contracts.
- `pyproject.toml`'s `[tool.coverage.run]` gained `patch = ["subprocess"]` (coverage >= 7.10; pinned coverage is 7.16.1) — proven live: `companion/pages/config_page.py` and every other `companion/pages/*.py` module now shows non-zero coverage in the combined report, confirming subprocess data files (from `byos_server.py`, `companion/app.py`, and the legacy companion harness subprocesses) are being measured and combined.
- Gate proof: `./scripts/run-all-tests.sh server/test_dither.py --cov-fail-under=100` exits non-zero with `FAIL Required test coverage of 100% not reached`.
- All 15 migrated files' `if __name__ == "__main__": raise SystemExit(pytest.main([...]))` bridges removed (dead code now that pytest is the sole entry point); the then-unused `import pytest` removed from 3 files (`test_colour_rules.py`, `test_dither.py`, `test_manual_resolutions.py`) per ruff F401.
- `pytest server/ stub-server/ -n auto -q` passes both as root (729 passed, 3 skipped — `requires_non_root`) and as `runuser -u nobody` (732 passed, 0 skips, exit 0). `--collect-only` finds 732 node ids, matching the 732 distinct `ported` node ids in the assembled ledger.

## Task Commits

Each task was committed atomically:

1. **Task 1: Assemble and verify the migration ledger** - `720d2b8` (docs)
2. **Task 2: pytest becomes the single entry point; coverage gate on pytest-cov with subprocess coverage** - `1cb80d3` (feat: `scripts/run_all_tests.py` deletion) + `f0bee52` (feat: the rest of the task — `run-all-tests.sh` rewrite, `pyproject.toml` coverage config, stale-comment fixes)
3. **Task 3: Remove legacy-runner bridges; root and non-root runs** - `c370921` (refactor)

**Plan metadata:** committed together with this SUMMARY (see below)

_Note: Task 2 landed as two commits because a stray pathspec (`scripts/run_all_tests.py`, already staged by the earlier `git rm`) in a `git add` invocation aborted that command before it staged the rest of the task's files — the first commit captured only the already-staged deletion. Both commits are within Task 2's scope; no work was lost or duplicated._

## Files Created/Modified
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-MIGRATION-LEDGER.md` - assembled from the 15 `32-ledger/*.md` fragments; one row per pre-migration baseline check
- `scripts/run-all-tests.sh` - thin `pytest -n auto --cov` wrapper replacing the bespoke orchestrator
- `scripts/run_all_tests.py` - deleted (retired hand-rolled runner)
- `pyproject.toml` - `[tool.coverage.run] patch = ["subprocess"]` added; `parallel = true` comment rewritten for pytest-xdist + subprocess measurement
- `server/test_*.py` (14 files), `stub-server/test_poll_cycle.py` - legacy-runner `pytest.main` bridge removed
- `companion/test_browser_ux.py`, `companion/test_browser_ux_health_drawings.py`, `companion/test_browser_ux_quiet_wake.py`, `companion/test_browser_ux_helpers.py`, `companion/test_legacy_harness_shim.py` - stale `scripts/run_all_tests.py` comment references updated to describe the retirement instead of naming the deleted file

## Decisions Made
- Kept `[tool.coverage.run]`'s `source`, `omit` and `[tool.coverage.report] fail_under = 83` unchanged, exactly as the plan specifies — 32-15 measures the new floor once the omit list shrinks.
- Fixed 5 stale `scripts/run_all_tests.py` comment mentions in `companion/` files outside this plan's `files_modified` list, because the plan's own acceptance criterion (`git grep -n "run_all_tests.py" -- ':!.planning' ':!*.md'` prints nothing) is a direct, mechanical consequence of Task 2's file deletion — Rule 1 (auto-fix bugs/stale references caused by this task's own change), not scope creep.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Stale reference] Fixed 5 dangling `scripts/run_all_tests.py` comment references**
- **Found during:** Task 2 (retiring `scripts/run_all_tests.py`)
- **Issue:** `companion/test_browser_ux.py`, `test_browser_ux_health_drawings.py`, `test_browser_ux_quiet_wake.py`, `test_browser_ux_helpers.py` and `test_legacy_harness_shim.py` each had a docstring/comment naming `scripts/run_all_tests.py` by path — accurate before this plan, false and misleading after the file's deletion, and directly failing the plan's own acceptance criterion for a clean repo-wide grep.
- **Fix:** Reworded each reference to describe the current mechanism (the pytest legacy-harness shim / the retired hand-rolled runner) without naming the deleted file.
- **Files modified:** the 5 files listed above.
- **Verification:** `git grep -n "run_all_tests.py" -- ':!.planning' ':!*.md'` now prints nothing.
- **Committed in:** `f0bee52` (part of Task 2's second commit)

**2. [Rule 1 - Lint] Removed 3 now-unused `import pytest` statements**
- **Found during:** Task 3 (removing the `pytest.main` bridges)
- **Issue:** `server/test_colour_rules.py`, `server/test_dither.py` and `server/test_manual_resolutions.py` imported `pytest` only for the removed bridge's `pytest.main(...)` call; ruff flagged F401 (unused import) after the bridge was deleted.
- **Fix:** `ruff check --fix` removed the import in all three files; a leftover double blank line each fix left behind was cleaned up by hand.
- **Files modified:** `server/test_colour_rules.py`, `server/test_dither.py`, `server/test_manual_resolutions.py`.
- **Verification:** `ruff check .` reports `All checks passed!`.
- **Committed in:** `c370921` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — stale/dead references directly caused by this plan's own deletions).
**Impact on plan:** Both fixes are mechanical accuracy corrections required by the plan's own acceptance criteria and lint gate. No scope creep, no behavior change.

## Issues Encountered
- A `git add` invocation in Task 2 included the already-`git rm`'d pathspec `scripts/run_all_tests.py`; git aborted the whole `add` on that unmatched pathspec, so the first Task 2 commit (`1cb80d3`) landed only the deletion. Recovered by staging and committing the remaining Task 2 files in a follow-up commit (`f0bee52`) with a note in its message; no work lost.
- The plan's `PYTHON=/nonexistent` gate-proof check behaves unexpectedly in this specific sandbox because `/nonexistent` happens to already exist here as a directory (an environment artifact unrelated to this plan — `ls -la /` shows it pre-dated any of this session's changes). A directory's executable bit makes bash's `[ ! -x "${PYTHON}" ]` check pass even though it isn't a runnable interpreter, so the script proceeds instead of erroring — this is pre-existing behavior of the check (unchanged from the original script) and not a regression. Verified the actual behavior against a genuinely nonexistent path (`/definitely/not/here/python3`): exits 1 with `ERROR: interpreter not found or not executable`, as intended. In any normal environment (CI, a real dev machine) `/nonexistent` does not exist and the literal acceptance-criterion command works as written.
- The full suite (`./scripts/run-all-tests.sh`, includes the still-unmigrated companion legacy-harness shim) exits 1 when run as root in this sandbox: 749 passed, 3 skipped, 2 failed (`test_status_pages`'s `anomaly_active()` check, `test_companion_app`'s 2 WR-11 read-only-directory checks) — these are the exact pre-existing root-sandbox failures documented before this plan started (root ignores read-only directory permission bits) and are unrelated to Task 2's runner rewrite; re-running the identical command under `runuser -u nobody` passes cleanly (754 passed, exit 0). This is the expected/known state, not a regression from this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `pytest -n auto --cov` is now the sole test entry point; `scripts/run_all_tests.py` no longer exists.
- Subprocess coverage measurement (`patch = ["subprocess"]`) is live and proven — 32-15 can now safely remove `companion/app.py`, `stub-server/byos_server.py` and `stub-server/make_test_panel.py` from the coverage `omit` list and measure the new `fail_under` floor.
- `.github/workflows/ci.yml`'s `./scripts/run-all-tests.sh` step needs no change to keep working (32-14's scope, same wave) — the wrapper's name and `PYTHON=` contract are unchanged.
- The migration ledger is complete and verifiable at any time via `32-ledger-check.py --all`; TST-02 can be marked complete now that every server-side plan in its span (32-03 through 32-12, assembled here) is done.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*
