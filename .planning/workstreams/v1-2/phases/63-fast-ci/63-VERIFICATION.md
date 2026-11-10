---
phase: 63-fast-ci
status: passed
verified: 2026-11-10
---

# Phase 63 verification

Success criteria of the roadmap, checked against what is on `main`:

1. **Wall time.** Median of the five consecutive green runs of the final pipeline: 9.0 min (6.2 to 9.1), against 27.4 min before (`63-TIMINGS.md`). Met.
2. **No test lost.** 13,818 tests executed, 0 skipped, 0 failed in every one of those runs; the floor in `scripts/ci_gates.py` is 12,821. No test was skipped, deselected or quarantined, and no assertion was changed. Met.
3. **Coverage.** Combined coverage from all shards is 96.31% (96.23% before) and `fail_under = 93` is unchanged; a local run of the combined data with `--fail-under=100` fails as it should. Met.
4. **Guards.** A missing browser errors instead of skipping (49 errors, exit 1); the network guard plugin is active in every shard; `companion/test_suite_guards.py` is unchanged and passes. Met.
5. **Deploy.** The `deploy` job text on `main` is identical to the one before the phase (same checksum), `needs: test` and the `production` approval are unchanged. After the merges, the deploy job waits for the reviewer's approval as before. Met.

Proofs of the failure paths: a failing job fails the aggregate check; a matrix with one shard removed fails it with `expected 7 shards; found 6`.

## After the merges (on `main`)

- Merge of #320: tests green, critical path 12.4 min.
- Merge of #322: tests green, critical path 8.9 min.
- Across all eight runs measured (the five, the PR run of #322 at 11.3 min, and these two) the median is 9.05 min.

## Follow-up on the open item

The slow `playwright install --with-deps` step was addressed after the phase closed (PR 328): the font packages it downloads are cached and put back in apt's archive before the install (details in `63-TIMINGS.md`). Checked on `main` after the merge:

- First run on `main` (run 42826596562, cache empty): tests green; the step took 8 to 19 s on four browser shards and 226 s on the fifth, where the package mirror was slow; the cache was saved.
- Run of the branch afterwards (run 42828296713, manual dispatch, cache restored from the one saved on `main`): the step took 7 to 8 s on all five browser shards, no font package downloaded, tests green.

Only two runs have been seen since the change, so the margin below 10 minutes is expected to hold but has not been measured over many runs. A cache miss (a new Playwright version or runner image version) still pays the download once.

## Left as they were

Two other timing-sensitive tests of `companion/test_browser_place_search.py` that fail only under an extreme local load; the two large browser files (owner's decision).
