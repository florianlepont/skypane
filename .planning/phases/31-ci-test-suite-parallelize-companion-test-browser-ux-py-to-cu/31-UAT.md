---
status: testing
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
source: [31-VERIFICATION.md]
started: 2026-09-22T19:57:42Z
updated: 2026-09-22T19:57:42Z
---

## Current Test

number: 1
name: Push this branch and read a real `gh run view` timing for the CI "test" job, comparing against D-01's ~340s baseline
expected: |
  A materially faster wall time (D-06's bar — no fixed target). 31-TIMINGS.md's own
  local-proxy estimate ranges 9.1%-29.6% job-level (mean 22.4%, median 28.7%) across
  five samples, missing D-05's 30-40% gate on every sample; the phase's own closing
  verdict explicitly asks for this to be "re-checked on the first real CI run ...
  and revised if the CI figure disagrees materially."
awaiting: user response

## Tests

### 1. Real CI wall-time confirmation
expected: A materially faster wall time (D-06's bar — no fixed target). 31-TIMINGS.md's own local-proxy estimate ranges 9.1%-29.6% job-level (mean 22.4%, median 28.7%) across five samples, missing D-05's 30-40% gate on every sample; the phase's own closing verdict explicitly asks for this to be "re-checked on the first real CI run ... and revised if the CI figure disagrees materially."
result: [pending]

### 2. Real-CI pool-contention / flakiness check
expected: 24/24 harnesses pass in CI, with no new intermittent failures beyond the three already-documented, pre-existing ARM64/macOS-only Chromium flakes (which do not reproduce on Linux amd64, i.e. real CI). Contention behavior (three simultaneous Chromium-launching harnesses sharing the 4-worker pool) is resource/scheduler-dependent and can only be confirmed by watching real CI runs.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
