---
phase: 63-fast-ci
plan: 03
status: executed
requirements: [CIS-01, CIS-02, CIS-03, CIS-04]
---

# Plan 63-03 Summary

The test jobs are matrices: 5 browser shards and 2 non-browser shards.

## Delivered

- `scripts/ci_shards.py weights JUNIT_XML...` (+ tests) and `scripts/ci_shard_weights.json`, generated from the JUnit files of run 42797272747 (393 files). Weights only balance the shards; the completeness check does not depend on them, and a weight for a deleted file is ignored.
- `ci.yml`: `strategy.matrix.shard` lists (`fail-fast: false`), `SKYPANE_TEST_SHARD: <shard>/<job-total>`, per-shard artifacts and concurrency groups; `BROWSER_SHARDS` / `CORE_SHARDS` at the top of the file feed the static completeness check and the aggregate job, which fails unless exactly that many coverage and JUnit files arrive.

## Results

First matrix run: critical path 7.5 min, 13,818 executed, 0 skipped, combined coverage identical to the unsplit run. Five consecutive green runs: median 9.0 min (6.2 to 9.1). Proof that a dropped shard fails the run: see `63-TIMINGS.md`. The shard count was chosen from predicted shard time (about 4.1 min browser, 4.3 min non-browser); predictions were within 5% of the unsplit measurements.

## Notes

- The pytest step per shard is 260-310 s in every run; the spread between runs comes from `playwright install --with-deps` (7 s to 192 s).
