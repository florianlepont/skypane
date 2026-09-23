---
status: complete
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
source: [31-VERIFICATION.md]
started: 2026-09-22T19:57:42Z
updated: 2026-09-22T20:22:51Z
---

## Current Test

## Tests

### 1. Real CI wall-time confirmation
expected: A materially faster wall time (D-06's bar — no fixed target). 31-TIMINGS.md's own local-proxy estimate ranges 9.1%-29.6% job-level (mean 22.4%, median 28.7%) across five samples, missing D-05's 30-40% gate on every sample; the phase's own closing verdict explicitly asks for this to be "re-checked on the first real CI run ... and revised if the CI figure disagrees materially."
result: pass
notes: "Confirmed via PR #78, CI run 35778948703 (2026-09-22): real total job time 327s vs D-01's ~340s baseline (-3.8%); job-level estimate -8.6%. Lands at/below the worst local sample (9.1%), confirming (not contradicting) the local proxy's missed-gate finding. Developer reviewed the real number and confirmed the skip-flights/close-phase decision stands. Full arithmetic in 31-TIMINGS.md's \"Real CI confirmation\" section."

### 2. Real-CI pool-contention / flakiness check
expected: 24/24 harnesses pass in CI, with no new intermittent failures beyond the three already-documented, pre-existing ARM64/macOS-only Chromium flakes (which do not reproduce on Linux amd64, i.e. real CI). Contention behavior (three simultaneous Chromium-launching harnesses sharing the 4-worker pool) is resource/scheduler-dependent and can only be confirmed by watching real CI runs.
result: pass
notes: "PR #78's CI run: 24/24 harnesses green, including all three Chromium-launching harnesses running concurrently. None of the three ARM64/macOS-only flakes appeared (expected, since real CI is Linux amd64). Contention is visible in timing, not failures: browser-ux-quiet-wake and browser-ux-health-drawings ran slower on the CI runner's 4 vCPUs than locally, consistent with the phase's own contention hypothesis, but caused no test failures on this run."

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

none
