---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 03
subsystem: tracking-validation
tags: [external-comparison, checkpoint]
requires: [65-01]
provides:
  - "scripts/runway_external_compare.py (seeded sampler, reference join, verdicts)"
  - "150-event stratified sample covering all 15 days"
affects: [65-04]
key-files:
  created:
    - scripts/runway_external_compare.py
    - scripts/test_runway_external_compare.py
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-TRACKING-EXTERNAL.md
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/data/external/
completed: 2026-11-15
status: PARTIAL (blocked at owner checkpoint)
---

# Phase 65 Plan 03: External comparison Summary (partial)

Task 1 done (tool and 11 tests); Task 2 reached 0 percent reference coverage, so the plan stops at the owner checkpoint with status NEEDS-OWNER-REFERENCE. Task 3 (run and verdicts) not executed.

## Results

- Tool: stdlib, reproducible sampling (seed 65), verdicts match / direction-mismatch / route-mismatch / unverifiable-no-reference plus missed-aircraft list; reads JSONL or CSV references.
- Sample: 150 of 4221 events (5031 rows collapsed), all 15 days.
- Sources: ORY timetable blocked by bot protection, Flightradar24 403, FlightAware history needs an account and disallows scraping, OpenSky history needs an account. Nothing bypassed; no reference rows invented.
- Owner request and CSV format are in 65-TRACKING-EXTERNAL.md; template `data/external/owner_reference_template.csv`.

## Deviations from Plan

None beyond: CSV input support added to the tool so the owner can supply a simple CSV (requested by the orchestrator).

## Verification

11 tests pass, ruff clean, comment-history guard clean, nothing under server/ or stub-server/ touched.

## Self-Check: PASSED
