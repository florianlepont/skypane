# Phase 63: Fast CI - Context

**Gathered:** 2026-11-10 (analysis session with the owner; no separate discuss-phase)
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the CI check `Lint, test, coverage, attribution` finish in 10 minutes or less (median of five consecutive pull-request runs), down from about 27 minutes, without skipping, disabling, deselecting or quarantining any test. The owner's words: about 10 minutes is the goal, but test quality must not be degraded.
</domain>

<decisions>
## Implementation Decisions

### Measured baseline (do not re-derive)
- Run 42770577886: job 27.5 min; pytest step 26.5 min; setup, Playwright, ruff, mypy and guards about 1 min together. 12,821 tests. The runner uses 4 xdist workers (`created: 4/4 workers`), same as the 4-core analysis machine.
- Browser tests (`*browser*`, about 2,800 tests): 17 min 47 s alone on 4 cores, 70 min of summed test time. `companion/test_browser_overhaul_sweep.py` is 739 tests / 11.1 min summed; `companion/test_browser_components_page.py` 59 tests / 7.8 min; `test_browser_personalisation.py` 40 / 4.2; `test_browser_airline_table.py` 25 / 3.1; `test_browser_update.py` 49 / 2.0; `test_browser_airline_collection.py` 39 / 1.7.
- Non-browser tests (about 10,900): 9 min 40 s on 4 cores. By area (summed minutes): companion 17.7, server 6.6, deploy 2.0, stub-server 1.8.
- Slow non-browser tests: `server/test_firmware_registry.py::test_legacy_size_bound_is_unchanged` (51.8 s), `deploy/tests/test_release_manifest.py::test_image_at_the_bound_passes_and_one_byte_over_fails` (51.3 s), `server/test_firmware_image.py::test_size_bound_defaults_to_the_ota_slot_not_the_display_bound` (51.2 s), `server/test_golden_giant_render.py::test_every_case_is_legal_and_matches_the_manifest` (22 s).
- xdist scales almost linearly (3,757-test subset: 478 s / 244 s / 134 s / 120 s with 1 / 2 / 4 / 8 workers). Coverage overhead: about 1% on server tests, about 12% on browser tests.
- Conclusion: the lever is more machines (parallel jobs and shards) plus trimming a few heavy tests, not xdist tuning or dropping coverage.

### Chosen direction
- Split into parallel jobs: static checks; non-browser tests; browser tests in shards. One aggregate job keeps the current check name and the dependency the `deploy` job relies on, combines coverage from every job and applies the existing `fail_under` floor unchanged.
- Make the slowest tests cheaper without dropping any case (the three firmware size-bound tests, the giant render test, then the sweep and components-page browser files).

### Hard constraints (from the owner)
- No test is skipped, disabled, deselected or quarantined. Executed count stays at or above 12,821.
- A missing browser still fails CI (`SKYPANE_REQUIRE_BROWSER`). The non-loopback network guard stays on in every job. `companion/test_suite_guards.py` and the behaviour-over-source rule stay in force.
- The coverage floor never goes down without the owner's explicit agreement.
- The `deploy` job, its `production` environment approval and its dependency on the test result are not changed. CI deploys to production on every merge to `main`: never merge; every PR stays a draft until the owner says it is ready.
- Do not touch any file of Phase 47 or anything under `hardware/`.
- Phase 61 (companion UX overhaul) is running in parallel and changes companion test files: any edit to a companion test file that Phase 61 also changes needs the owner's agreement first (make it a checkpoint task, not an assumption).
- Repository documents in English; CLAUDE.md conventions (no plan, phase or ticket IDs in code comments).
- Plans change CI configuration only on a pull-request branch and are verified by real CI runs of that branch.

### Claude's Discretion
- Shard count and split method (by file or by test) for the browser tests, as long as the criteria are met and coverage merges correctly.
- How to carry coverage data between jobs (artifacts) and combine it.
</decisions>

<specifics>
## Specific Ideas

- `./scripts/run-all-tests.sh` stays the single entry point that matches CI.
- Before and after timings are recorded in the phase documentation.
</specifics>

<deferred>
## Deferred Ideas

- Running browser tests only when companion or UI files change: the owner has not accepted it (it would let some changes merge without browser tests running). Not in this phase.
</deferred>
