---
phase: 67-project-and-code-optimisation
plan: 01
subsystem: ci-gates
tags: [baseline, ci, test-floor, quality]
requires: []
provides:
  - measured before record (67-BASELINE.md) with commands, collected-id count and hash
  - executed-test floor equal to the measured executed count
affects: [67-02, later 67 plans]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/67-project-and-code-optimisation/67-BASELINE.md
  modified:
    - scripts/ci_gates.py
    - test-support/test_ci_gates.py
decisions:
  - MIN_EXECUTED set to 17598 (CI run 45993237674 on main, 0 skipped); MAX_SKIPPED stays 0
metrics:
  completed: 2026-11-27
  tasks: 2
  files: 3
requirements: [QUAL-01]
---

# Phase 67 Plan 01: Baseline and test floor Summary

Recorded the reproducible before state and raised `MIN_EXECUTED` from 12,821 to 17,598, so about 4,800 tests can no longer vanish unnoticed.

## Commits

- 368f85e docs(67-01): record the measured before state of the repository
- 9b37f9d test(67-01): raise the executed-test floor to the measured 17,598

## Measured numbers

- Executed count used for the floor: 17,598 (last green main CI run 45993237674: 0 failures, 0 skipped); local collection also gives 17,598 ids.
- before.ids sha256: 96b64df5aab477e27ed49cb8862b9dbb3bfa9a640c61955a2996fbdf7122b65c, baseline commit ace564b.
- Other figures are in `67-BASELINE.md`.

## Verification

- `test-support/test_ci_gates.py`: 14 passed; ruff clean on both files; comment-history check clean.
- Freeze and golden check: 115 passed.

## Deviations from Plan

None. The one structural difference from the research table: the tree has moved since research (companion production 166 modules and 45,856 lines, 3,139 tracked files, 40 remote branches); the baseline records the re-measured values.

## Known Stubs

None.

## Self-Check: PASSED
