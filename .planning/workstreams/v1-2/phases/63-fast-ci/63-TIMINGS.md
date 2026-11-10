# Phase 63: Fast CI - Timings

Measured with `scripts/ci_run_timing.py` (REST API only). All numbers are
wall-clock seconds unless stated.

## Baseline (before any change)

Run 42770577886 (pull request, 2026-11-10, unsplit workflow, one test job).
The runner uses 4 xdist workers (`created: 4/4 workers`).

| Step | Seconds |
|---|---|
| Check out repository | 4 |
| Set up Python | 4 |
| Create virtualenv and install dependencies (hash-enforced) | 9 |
| Cache Playwright browsers | 3 |
| Download the Chromium headless shell | 25 |
| Lint, comment-history guard, mypy, function-size gate, shellcheck, systemd scoring | 7 together |
| Run full test suite with coverage threshold | 1588 (26 min 28 s) |
| Check vendored-asset attribution completeness | 1 |
| **Job total** | **1647 (27.4 min)** |

Pytest summary line, verbatim:

```
12821 passed, 182 warnings in 1585.99s (0:26:25)
```

- Executed tests: 12,821 passed, 0 skipped, 0 failed, 0 deselected.
- Coverage: `TOTAL 24691 931 96%`; `Required test coverage of 93.0% reached. Total coverage: 96.23%`.

Slowest tests in that run (`--durations=15`), seconds:

| s | Test |
|---|---|
| 52.81 | deploy/tests/test_release_manifest.py::test_image_at_the_bound_passes_and_one_byte_over_fails[2424833-2] |
| 50.13 | server/test_firmware_registry.py::test_legacy_size_bound_is_unchanged |
| 47.42 | server/test_firmware_image.py::test_size_bound_defaults_to_the_ota_slot_not_the_display_bound |
| 39.02 | companion/test_browser_airline_table.py::test_the_menu_deletes_an_uploaded_artwork_and_stars_the_default_type[chromium] |
| 27.93 | companion/test_browser_airline_table.py::test_a_type_row_is_customised_then_deleted_back_to_the_default[chromium-360] |
| 27.36 | companion/test_browser_airline_table.py::test_a_type_row_is_customised_then_deleted_back_to_the_default[chromium-1280] |
| 26.33 | companion/test_browser_airline_table.py::test_renaming_saves_on_change_and_the_menu_resets_it[chromium] |
| 23.41 | companion/test_browser_ux_04.py::test_a_row_expands_to_its_types_and_each_type_has_its_own_replace[chromium] |
| 15.89 | companion/test_browser_personalisation.py::test_the_floating_save_bar_saves_the_look[chromium] |

The executed count matches the 12,821 floor in the phase context.

## Analysis-machine measurements (4 cores, same count of workers as CI)

- Whole suite on that machine: 10,855 passed, 8 skipped, 2,713 errors in 9 min 40 s;
  the errors are the browser tests, which could not launch the Chromium build
  installed there (version mismatch). The 8 skips were not investigated.
- Browser tests alone: 2,825 passed in 17 min 47 s.
- xdist scaling on a 3,757-test subset: 478 s (1 worker), 244 s (2), 134 s (4),
  120 s (8). Coverage overhead: 134 s without, 136 s with (server tests);
  63 s without, 71 s with (88 browser tests).

## Split into parallel jobs, no shards (plan 02)

Run 42797272747 (pull request, commit with the split workflow and the cheaper
firmware tests; all jobs green):

| Job | Wall s |
|---|---|
| Static checks | 34 |
| Tests (non-browser) | 575 (9 min 35 s); pytest 542 s, 11,038 passed |
| Tests (browser) | 1293 (21 min 33 s); pytest 1248 s, 2,778 passed |
| Lint, test, coverage, attribution (aggregate) | 39 |
| **Critical path** | **1349 (22.5 min)** |

- Executed: 13,816 tests, 0 skipped, 0 failed (JUnit totals gate over both reports).
- Combined coverage: `TOTAL 25771 statements, 951 missed, 96%` = 96.31%, against 96.23% for the baseline run (difference 0.08 points); the floor `fail_under = 93` is applied by `coverage report` on the combined data.
- The browser job is the critical path; sharding it is the next step.

Proofs:

- Floor: the artifacts of that run, combined locally (with a path mapping in a temporary copy of the configuration, repository untouched), pass `coverage report` with the repository floor (exit 0) and fail `coverage report --fail-under=100` (exit 2).
- Job failure: run 42800589063 (commit with a deliberate ruff violation and a deliberately failing test, since reverted): Static checks = failure, Tests (non-browser) = failure, Tests (browser) = success, `Lint, test, coverage, attribution` = failure, Deploy to production = skipped. The aggregate check is a failure, not skipped and not green.
- Missing browser: `SKYPANE_REQUIRE_BROWSER=1 PLAYWRIGHT_BROWSERS_PATH=<empty dir> ./scripts/run-all-tests.sh companion/test_browser_update.py` ends with 49 errors and exit code 1, none skipped.
- Network guard: both test jobs show `plugins: ... socket-0.8.1 ...` in the pytest header and 4/4 xdist workers; the guard tests in `test-support/test_test_support.py` pass (27).
- `deploy` job: its text is identical to `origin/main` (checked by comparing the job's lines); `deploy/tests/test_ci_secrets.py` passes.

## Matrix shards: 5 browser + 2 non-browser (plan 03)

Shard counts come from per-file test times of run 42797272747
(`scripts/ci_shard_weights.json`). Predicted time per shard (summed file
weight / 4 workers): browser 4.1 min, non-browser 4.3 min with 2 shards;
other counts evaluated: 4+2 browser 5.1 / core 4.3, 5+3 4.1 / 2.9,
6+3 3.4 / 2.9. The prediction matched reality: the unsplit runs measured
1,248 s browser against 1,224 s predicted, and 542 s non-browser against
516 s predicted. Shards come out within 1% of each other in predicted
weight.

Proof that a dropped shard is caught: run 42805370904 (second attempt),
commit with one browser shard removed from the matrix, reverted afterwards:
`Lint, test, coverage, attribution` = failure with `expected 7 shards;
found 6 coverage files and 6 JUnit files`; every other job succeeded.
(The first attempt of that run was cancelled by a concurrency race: the
group names of the test jobs had just changed, so an older run's aggregate
job, which was still going, cancelled the newer one's. It does not recur
with stable names.)

## Five consecutive green runs of the final pipeline (plan 06)

Final pipeline = split jobs, 5 + 2 shards, aggregate gate. All five are
green, with 13,818 tests executed, 0 skipped, 0 failed, and the combined
coverage `TOTAL 25771 statements, 951 missed` = 96.31% in every one (the
same figure as the unsharded run: sharding loses no coverage data).

| Run | Produced by | Commit | Critical path | Aggregate job |
|---|---|---|---|---|
| RUN_ID=42804186330 | pull request push | 56129e1 | 451 s (7.5 min) | 27 s |
| RUN_ID=42807798895 | pull request push | 9a78fae | 547 s (9.1 min) | 25 s |
| RUN_ID=42809102527 | pull request push | 27a4103 | 543 s (9.1 min) | 34 s |
| RUN_ID=42810365788 | manual dispatch of the branch | 27a4103 | 541 s (9.0 min) | 26 s |
| RUN_ID=42811616750 | manual dispatch of the branch | 27a4103 | 369 s (6.2 min) | 26 s |

`scripts/ci_run_timing.py median` over the five: **9.0 min** (minimum 6.2,
maximum 9.1). Two of the five runs are manual dispatches of the same branch
because a documentation-only push does not start the workflow; they run the
same jobs (the production deploy job is skipped outside `main`).

Where the spread comes from: the pytest step of a shard is steady (about
260-310 s in every run), but the step `playwright install --with-deps`
(operating-system packages through apt) took between 7 s and 192 s across
browser shards and runs; the run at 6.2 min is the one where it took 7-9 s
everywhere. The slow runs sit at about 9 min only because of that step.

## Before and after

| | Before (run 42770577886) | After (median of 5) | Min / max of 5 |
|---|---|---|---|
| Test check wall time | 27.4 min | 9.0 min | 6.2 / 9.1 min |
| Tests executed | 12,821 | 13,818 | 13,818 / 13,818 |
| Skipped | 0 | 0 | 0 / 0 |
| Combined coverage | 96.23% | 96.31% | 96.31% / 96.31% |
| Coverage floor | 93 | 93 (unchanged) | |

The executed count rose because the tree changed since the baseline run and this phase added tests (the builder digest matrix, the per-case golden render tests and the tooling tests); nothing was removed or skipped.
