---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 02
subsystem: tracking-validation
tags: [analysis, internal-consistency, runway-events]
requires: ["65-01"]
provides:
  - "scripts/runway_compare.py read-only analyser (7 classes, per-day counts, coverage)"
  - "65-TRACKING-INTERNAL.md class table with example rows and 2026-11-11 section"
affects: [65-03]
key-files:
  created:
    - scripts/runway_compare.py
    - scripts/test_runway_compare.py
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-TRACKING-INTERNAL.md
key-decisions:
  - "Added a seventh class, route-direction-mismatch, because the six planned classes cannot see stale routes inside runway_events alone"
completed: 2026-11-15
---

# Phase 65 Plan 02: Internal-consistency analysis Summary

A tested stdlib analyser plus a class table over the 2026-11-01..11-15 snapshot; thresholds come from `server.plane.runway_config`, no detection code changed.

## Class counts (5031 events)

| Class | Count |
|-------|-------|
| held-carry-over | 0 (poll_cycles covers 75 rows, 11-15 12:13-13:40Z only) |
| state-contradiction | 0 testable; 5009 events not testable |
| stateless | 1 |
| rotating-route | 0 |
| no-route | not testable (needs 30+ days; 22 callsigns at a 5-day threshold) |
| flip-flop | 39 (14 on 2026-11-11) |
| route-direction-mismatch | 447 (10.1% of rows with a route) |

The 2026-11-11 known issues cannot be located exactly because poll_cycles has no 11-11 rows; indirect evidence (14 flip-flops, 56 route mismatches) is listed with exact rows in 65-TRACKING-INTERNAL.md.

## Commits

- RED tests, analyser (GREEN), route-direction-mismatch extension, class table document (see git log on gsd/phase-65-execute, messages prefixed `test|feat|docs(65-02)`).

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Seventh class route-direction-mismatch.** The planned classes found 0 stale routes, which would have hidden 447 rows whose route contradicts the state. Added with a test. Also added a supplementary pending-rate count (3 rows). Files: scripts/runway_compare.py, scripts/test_runway_compare.py.

## Verification

11 tests pass, ruff clean, comment-history guard clean, no diff under server/ or stub-server/.

## Self-Check: PASSED
