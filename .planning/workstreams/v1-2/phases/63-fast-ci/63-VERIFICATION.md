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

## Open item

Two of the later runs (11.3 and 12.4 min) were above 10 minutes. In both, the cause is the step `playwright install --with-deps` (operating-system packages through apt), which takes between 7 s and 331 s depending on the runner, while the tests themselves take 260 to 330 s per shard. The criterion (median of five runs) is met; the margin is thin until that step is dealt with. Not changed in this phase.

Also left as they were, by decision or by scope: the two large browser files (owner's decision), and two other timing-sensitive tests of `companion/test_browser_place_search.py` that fail only under an extreme local load.
