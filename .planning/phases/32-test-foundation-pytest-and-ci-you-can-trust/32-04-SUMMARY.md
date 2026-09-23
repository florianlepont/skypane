---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 04
subsystem: testing
tags: [pytest, migration-ledger, root-safety, adsbdb, transport-injection]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py fake_providers fixture and DNS guard, test-support/skypane_test_support.py (child_env, requires_non_root)
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/*.txt transcripts, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_manual_resolutions.py, server/test_colour_rules.py, server/test_enrich.py as real pytest modules
  - 3 ledger fragments under 32-ledger/ mapping all 116 baseline checks (23+33+60) to node ids
  - the first worked example of `@requires_non_root` applied to real (not synthetic) root-sandbox FAILs recorded in 32-BASELINE/INDEX.md's "## Notes"
  - the first worked example of adsbdb enrichment tests that need zero fake_providers/network stubbing because every check injects a fake transport directly
affects: [32-05, 32-06, 32-07, 32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A baseline FAIL line caused only by euid 0 (32-BASELINE/INDEX.md's WR-11 root-sandbox note) ports as a normal test with @requires_non_root added - same assertion, same tmp_path target, no special-casing of the FAIL vs the neighbouring PASS rows; skipped under root with an explicit reason, runs and passes under a non-root euid (verified with `runuser -u nobody`)."
    - "A hand-rolled check() call whose body loops internally over several inputs and reports ONE pass/fail (not one baseline PASS/FAIL line per input) stays ONE pytest test function with an internal loop, not a @pytest.mark.parametrize split (restated from 32-03's summary, now proven against two more checks in test_enrich.py: the never-raises battery and the three stale-brand-name pairs) - parametrize would silently turn 1 baseline row into N node ids, which the 1:1 ledger-check tool would then have nothing to point the extra ids at."
    - "A module whose every test already injects the seam it would otherwise stub (enrich.lookup_route()'s `transport=` parameter) needs neither the fake_providers fixture nor any monkeypatch of requests.get - test_enrich.py's 60 tests make zero network-guard-relevant calls by construction, not because a guard was stubbed around them."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_manual_resolutions.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_colour_rules.md
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_enrich.md
  modified:
    - server/test_manual_resolutions.py
    - server/test_colour_rules.py
    - server/test_enrich.py

key-decisions:
  - "server/test_manual_resolutions.py's two WR-11 read-only-parent-directory checks (baseline rows 21/22, both FAIL under this sandbox's euid 0) ported unchanged with @requires_non_root added per MR-8 - the assertion itself is untouched (still expects ADD_FAILED/False for a chmod-0o500 target), only the skip condition and tmp_path in place of tempfile.TemporaryDirectory() are new. Confirmed passing under a non-root euid via `runuser -u nobody`."
  - "test_manual_resolutions.py's legacy __main__ bridge needed test-support/ added to its own sys.path bootstrap (same fix 32-03 made for test_pipeline_e2e.py) because it imports skypane_test_support.requires_non_root, which pyproject.toml's pythonpath config only adds for a `pytest` invocation, not a direct `python3 server/test_manual_resolutions.py` run."
  - "test_enrich.py's never-raises battery (baseline check 21) and three-stale-brand-pairs check (baseline check 36) both stayed single test functions with an internal loop rather than @pytest.mark.parametrize, since the original harness reported each as exactly ONE baseline PASS line - parametrizing either would have produced N node ids for 1 baseline row, which 32-ledger-check.py's strict 1:1 row-to-target mapping has no way to represent."
  - "test_enrich.py needed no fake_providers fixture and no requests.get monkeypatch at all: every one of its 60 checks calls enrich.lookup_route()/resolve_route() with an explicit transport= callable (make_transport()), so none of them ever reaches enrich.default_transport() (the real requests.get wrapper) - the module is hermetic by construction, not by a guard working around it."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (7 harnesses remain after this plan); TST-03 was already completed by plan 32-01 - neither is (re-)marked by this plan per the "every plan it spans" rule.

# Metrics
duration: ~40min
completed: 2026-09-23
---

# Phase 32 Plan 04: Migrate test_manual_resolutions, test_colour_rules, test_enrich to pytest Summary

**server/test_manual_resolutions.py (23 checks, the first root-safety case), server/test_colour_rules.py (33 checks), and server/test_enrich.py (60 checks, the adsbdb enrichment client) are now real pytest modules passing under `-n 4` with zero network access, zero filesystem writes outside tmp_path, and both real root-sandbox FAILs from the baseline now skipping cleanly under euid 0 and passing under a non-root euid.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files modified:** 6 (3 test modules + 3 new ledger fragments)

## Accomplishments
- `server/test_manual_resolutions.py` (23 checks) converted to plain `test_*` functions over `tmp_path`; the two WR-11 read-only-parent-directory checks (baseline rows 21/22, the project's first documented root-sandbox FAILs) gained `@requires_non_root` and were confirmed passing (0 skips) under `runuser -u nobody`.
- `server/test_colour_rules.py` (33 checks) converted to plain `test_*` functions - pure CRUD/resolver logic over `tmp_path`, no root-safety or network concerns.
- `server/test_enrich.py` (60 checks, the largest single-file migration in the phase so far) converted to plain `test_*` functions plus three pytest fixtures (`hit_body`, `miss_fixture`, `aia_hit_body`) replacing the old harness's module-level fixture loads; every check injects a fake `transport=` callable, so the module needs neither `fake_providers` nor any `requests.get` monkeypatch.
- All three ledger fragments verified against `32-ledger-check.py`: 116/116 baseline checks mapped (23+33+60), 0 pending, 0 `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` leftovers.
- All three files pass `pytest -q` and `pytest -q -n 4`, and their legacy-runner `__main__` bridges (`python3 server/test_*.py`) still exit 0 (MR-3).

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_manual_resolutions (root-safe) and test_colour_rules** - `0f9a488` (feat)
2. **Task 2: Migrate test_enrich (adsbdb seam via transport injection)** - `faef94e` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_manual_resolutions.py` - 23 `test_*` functions, `@requires_non_root` on the two WR-11 checks, `test-support/` added to the legacy-bridge sys.path bootstrap
- `server/test_colour_rules.py` - 33 `test_*` functions, a shared `_resolver_with(tmp_path_factory, ...)` helper replacing the old harness's inline resolver-priming closure
- `server/test_enrich.py` - 60 `test_*` functions, `hit_body`/`miss_fixture`/`aia_hit_body` fixtures, an autouse `_reset_manual_registry_state_dir` fixture as a belt-and-braces MR-4 guard
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_manual_resolutions.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_colour_rules.md` (new)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_enrich.md` (new)

## Decisions Made
- Ported the two WR-11 root-sandbox FAILs (32-BASELINE/INDEX.md's documented root-euid environment condition, not a regression) unchanged with `@requires_non_root` added, rather than rewriting their assertions - the check still expects the chmod-0o500 write to fail; only the skip condition changed. Confirmed running (not skipped) and passing under `runuser -u nobody`.
- Kept both of `test_enrich.py`'s internally-looping checks (the never-raises battery, the three stale-brand-name pairs) as single test functions rather than `@pytest.mark.parametrize`, per the rule 32-03 established: parametrize is reserved for checks the OLD harness itself emitted as separate PASS/FAIL lines from a loop, never for internal iteration inside one `check()` call - each of these two checks has exactly one baseline PASS line.
- Did not add a `fake_providers` fixture use anywhere in `test_enrich.py`: every one of its 60 checks already injects a `transport=` callable, so none of them exercises `enrich.default_transport()`'s real `requests.get` wrapper - there is nothing in this file for `fake_providers` to usefully stand in for.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] server/test_manual_resolutions.py: legacy-runner bridge needed test-support/ on its own sys.path**
- **Found during:** Task 1, running `server/.venv/bin/python3 server/test_manual_resolutions.py` directly (MR-3 acceptance criterion)
- **Issue:** The file imports `skypane_test_support.requires_non_root` at module scope. `pyproject.toml`'s `pythonpath` config adds `test-support/` to `sys.path` only for a `pytest`-driven run; a direct `python3 server/test_manual_resolutions.py` invocation never reads that config, so the import raised `ModuleNotFoundError` before any test could run.
- **Fix:** Added the same `_TEST_SUPPORT_DIR` bootstrap block `server/test_pipeline_e2e.py` already uses (plan 32-03) immediately after the existing `REPO_ROOT` bootstrap, so the legacy bridge finds `skypane_test_support` regardless of how the file is invoked.
- **Files modified:** `server/test_manual_resolutions.py`
- **Verification:** `server/.venv/bin/python3 server/test_manual_resolutions.py` now exits 0 (21 passed, 2 skipped under this sandbox's euid 0).
- **Committed in:** `0f9a488` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking fix, following an already-established pattern from plan 32-03)
**Impact on plan:** No scope creep - the fix only extends the same legacy-bridge sys.path bootstrap plan 32-03 already introduced for `test_pipeline_e2e.py`, applied here because this file is the first subsequent one to import `skypane_test_support` from its own `__main__` bridge.

## Issues Encountered

None beyond the sys.path deviation above. `server/test_colour_rules.py` and `server/test_enrich.py` both passed on the first full run with no fixes needed - `test_colour_rules.py` imports nothing from `test-support/`, and `test_enrich.py`'s legacy bridge needs nothing beyond the stdlib/`pytest` imports it already had.

## Next Phase Readiness
- 8 of 15 server-side harnesses now migrated (163 of 769 baseline checks: 47 from plan 32-03 + 116 from this plan); 7 remain across plans 32-05..32-10.
- The `@requires_non_root` pattern is now proven against a real (not synthetic) root-sandbox FAIL, confirmed passing under `runuser -u nobody` - directly reusable by any later plan whose harness has a permission-bit check (none of the remaining 7 harnesses are flagged as root-safety cases in 32-PATTERNS.md, but the pattern is available if one surfaces).
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (7 more harnesses to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 3 migrated test modules, 3 ledger fragments, and this summary confirmed present on disk;
task commit hashes (`0f9a488`, `faef94e`) confirmed present in `git log --oneline --all`.
