---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 06
subsystem: testing
tags: [pytest, migration-ledger, network-guard, subprocess-fixture, byos-server]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py DNS guard, test-support/skypane_test_support.py (child_env, requires_non_root)
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/stub-server__test_poll_cycle.txt transcript, 32-ledger-check.py, 32-ledger/ fragment format
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 03)
    provides: the byos_server_factory / BYOSHarness subprocess-fixture precedent (server/test_pipeline_e2e.py) this plan's Harness class follows
provides:
  - stub-server/test_poll_cycle.py as a real pytest module (19 node ids covering the 46 baseline checks)
  - 1 ledger fragment under 32-ledger/ mapping all 46 baseline checks to node ids
  - the second worked example (after server/test_pipeline_e2e.py) of a subprocess-launching Harness whose child_env() covers BOTH a one-shot subprocess.run (make_test_panel.py) and a long-lived subprocess.Popen (byos_server.py) in the same class
affects: [32-07, 32-08, 32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A hand-rolled harness whose checks split cleanly into pure-unit checks (no shared process state) and a long sequential device-protocol scenario (one subprocess, one token, one served image, cumulative state) becomes TWO kinds of pytest test: N independent test functions for the unit checks (each with their own tmp_path, sharing a read-only module-scoped fixture for an expensive immutable load like importlib.util module loading) plus ONE consolidated test function for the sequential scenario (MR-4) - splitting the sequential part further would either duplicate its setup or introduce inter-test ordering dependencies the migration forbids."
    - "Two checks that only call a pure validation function on a hand-built dict (validate_display_response() with literal sleep_s=0 / uppercase image_hash) need neither a harness nor tmp_path at all - they become trivial standalone tests, further shrinking what the consolidated integration test has to cover."
    - "A subprocess-launching Harness class that calls BOTH subprocess.run (a one-shot helper CLI, make_test_panel.py) and subprocess.Popen (a long-lived server, byos_server.py) needs child_env() passed to both call sites, not just the Popen - the guard only protects a child that actually receives the env dict."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/stub-server__test_poll_cycle.md
  modified:
    - stub-server/test_poll_cycle.py

key-decisions:
  - "stub-server/test_poll_cycle.py's 46 old checks split into 19 pytest node ids: 16 independent unit tests for the quiet-hours/wake-interval/display-off/battery-critical pure sleep_s functions (each check had its own tmpdir and touched no shared harness state in the original harness either), 2 standalone tests for the validate_display_response() negative controls (no harness needed at all), and 1 consolidated integration test for the 28 checks that share one long-lived byos_server.py subprocess's device_token, served image hash, and battery_state.json across the scenario - genuinely sequential state per MR-4, not independently reorderable."
  - "Harness.__init__ now takes a state_dir argument (always a pytest tmp_path) instead of calling tempfile.mkdtemp() itself, and no longer has a cleanup() method - tmp_path's own teardown replaces the harness's manual shutil.rmtree(), satisfying MR-5 (no tempfile. call anywhere in the migrated file)."
  - "Both of Harness's subprocess call sites (generate_panel()'s subprocess.run of make_test_panel.py, and start_server()'s subprocess.Popen of byos_server.py) now pass env=self.env, defaulting to child_env() - TST-03's guard-must-apply-to-subprocess-launched-servers requirement covers both child interpreters this harness starts, not just the long-lived one."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (this is 32-06 of 8; server/test_config_history.py, test_calendar_rules.py, test_render.py, test_poll_loop.py remain in 32-07..32-10) - not (re-)marked by this plan per the "every plan it spans" rule. TST-03 was already completed by plan 32-01.

# Metrics
duration: ~35min
completed: 2026-09-23
---

# Phase 32 Plan 06: Migrate stub-server/test_poll_cycle.py to pytest (byos fixtures, guarded children) Summary

**stub-server/test_poll_cycle.py's 46-check hand-rolled device-protocol harness is now 19 pytest node ids (16 pure-unit tests, 2 standalone validator tests, 1 consolidated 28-check integration test), passing under `-n 4` with both byos_server.py and make_test_panel.py children launched via `child_env()` and every path under tmp_path.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 1
- **Files modified:** 2 (1 test module + 1 new ledger fragment)

## Accomplishments
- Converted `stub-server/test_poll_cycle.py` (1,744 lines, 46 `check()` calls) into a real pytest module: 16 independent unit tests for the quiet-hours/wake-interval/display-off/battery-critical sleep_s pure functions (sharing a module-scoped `byos_module` fixture that loads `byos_server.py` once via `importlib.util`), 2 standalone `validate_display_response()` negative-control tests, and 1 consolidated `test_device_protocol_end_to_end_over_real_http` covering the 28 checks that share one long-lived `byos_server.py` subprocess's device_token/image-hash/battery-state sequence.
- `Harness` (the class `server/test_pipeline_e2e.py`'s own `BYOSHarness` says it structurally mirrors) now takes a `state_dir` argument instead of calling `tempfile.mkdtemp()`, has no `cleanup()` method (tmp_path owns teardown), and passes `env=self.env` (defaulting to `child_env()`) to BOTH its `subprocess.run` (make_test_panel.py) and `subprocess.Popen` (byos_server.py) call sites - TST-03's "the guard must apply to the subprocess-launched servers too" requirement covers both children this harness starts.
- All 46 baseline checks verified mapped by `32-ledger-check.py`: 46/46, 0 deleted, 0 pending.
- Passes under both `-n 0` and `-n 4` (19 passed), `ruff check` clean, legacy-runner bridge (`python3 stub-server/test_poll_cycle.py`) exits 0, zero `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` occurrences, zero new untracked files after a fresh run, zero production-code changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_poll_cycle (byos fixtures, guarded children)** - `1f39e1d` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `stub-server/test_poll_cycle.py` - 19 `test_*` functions/fixtures; `Harness` reworked to take `state_dir`/`env` and drop `tempfile.mkdtemp()`/`cleanup()`; module docstring trimmed of phase/plan/ticket changelog history (MR-10)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/stub-server__test_poll_cycle.md` (new) - 46 rows, all `ported`

## Decisions Made
- Split the 46 old checks into three groups rather than one big consolidation like `server/test_pipeline_e2e.py`'s: the 16 quiet-hours/wake-interval/display-off/battery-critical unit checks and the 2 `validate_display_response()` negative controls touched no shared harness state in the ORIGINAL harness either (each had its own `tempfile.mkdtemp()` or no filesystem/process interaction at all) - keeping them independent is the more faithful translation and gives more precise pytest failure isolation than folding 18 genuinely-independent checks into the same consolidated node id as the 28 that truly do share one subprocess's state.
- Reused `server/test_pipeline_e2e.py`'s `byos_server_factory`/`BYOSHarness` shape (32-03) but did not adopt the factory-fixture form itself, since this file needs only two `Harness` instances total (the main one and the https-scheme one), both created inline inside the one consolidated test rather than via a factory a pytest fixture would inject - a plain local variable plus `try/finally` was simpler and stayed closer to the original harness's own control flow.

## Deviations from Plan

None - plan executed exactly as written. The migration_rules (MR-1..MR-13) were applied directly with no need for a production-code fix, no DNS-stub gap (unlike plan 32-03's `server/test_notify.py`, `byos_server.py` never resolves an external hostname), and no root-safety skip (no `os.chmod` checks in this harness).

## Issues Encountered

None.

## Next Phase Readiness
- 6 of 15 server-side harnesses now migrated (server/test_dither.py, test_runway_config.py, test_notify.py, test_panel_preview.py, test_pipeline_e2e.py from 32-03; test_manual_resolutions.py, test_colour_rules.py, test_enrich.py from 32-04; test_illustrations.py, test_plane_detection.py from 32-05; stub-server/test_poll_cycle.py from this plan) - 9 harnesses, 279 of 769 baseline checks. `server/test_config_history.py` (32-07), `server/test_calendar_rules.py` (32-08), `server/test_render.py` (32-09), and `server/test_poll_loop.py` (32-10) remain.
- The "independent unit checks vs. one consolidated sequential-state test" split pattern established here is reusable by any later plan whose harness mixes pure-function checks with a stateful subprocess scenario in the same file.
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (4 more harnesses to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

`stub-server/test_poll_cycle.py`, the ledger fragment, and this summary confirmed present on
disk; task commit hash (`1f39e1d`) confirmed present in `git log --oneline --all`.
