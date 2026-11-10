---
phase: 63-fast-ci
plan: 01
status: executed-pending-ci
requirements: [CIS-01, CIS-04, CIS-05]
---

# Plan 63-01 Summary

Measurement harness, group/shard tooling and local entry-point knobs. No workflow file and no existing test was changed.

## Delivered

- `scripts/ci_run_timing.py`: `jobs RUN_ID...` (job and step tables, critical path) and `median RUN_ID...`; REST only through `gh api`; repository from `GITHUB_REPOSITORY`, else the origin remote, else `--repo`. Tested offline in `test-support/test_ci_run_timing.py` (5 tests).
- `scripts/ci_shards.py`: `files GROUP INDEX COUNT` and `check`. A file is in the `browser` group when its name contains "browser" or its source uses the browser marker (two files, `companion/test_freshness_token.py` and `companion/test_static_cache.py`, mix browser and plain tests without "browser" in the name); everything else is `core`. Whole-file selection, greedy packing, optional `scripts/ci_shard_weights.json`. Lists tracked files plus untracked, non-ignored ones, so a not-yet-committed test file is not silently dropped by a local partial run. Tested in `test-support/test_ci_shards.py` (21 tests).
- `scripts/run-all-tests.sh`: optional `SKYPANE_TEST_GROUP`, `SKYPANE_TEST_SHARD`, `SKYPANE_JUNIT_XML`. A partial run writes coverage data only and enforces no floor; an unknown group, a malformed shard or an empty selection exits 2.
- `63-TIMINGS.md`: baseline of run 42770577886.

## Verified locally

- Default command line unchanged: `-m pytest -n auto --cov --cov-report=term-missing:skip-covered --durations=15`.
- Collected counts: whole tree 13,602 = core 10,824 + browser 2,778 (equal; before the untracked-file fix the sum was 21 short, exactly the new shard tests).
- Real shard run (core, 1/40): 147 passed, nothing deselected, `.coverage` data written.
- `ruff`, `mypy`, comment-history guard, function-size gate, `deploy/tests/test_ci_secrets.py` and `companion/test_suite_guards.py` pass. `pyproject.toml`, `companion/`, `hardware/` and `.github/` are untouched.

## Points to note

- Baseline executed count is 12,821 passed, 0 skipped (matches the phase context). The tree now collects 13,602 tests locally; the difference from 12,821 is the Phase 61 and 62 tests merged since that CI run plus the 26 new tests here. Plan 02 must take its floor from a fresh CI run of the branch, not from 12,821.
- `shellcheck scripts/run-all-tests.sh` reports one pre-existing warning (`cd` without `|| exit`, SC2164) on a line this plan did not change. CI does not shellcheck `scripts/`.
- Not yet done: the real CI run of the unchanged workflow on the draft PR branch (plan verification step).
