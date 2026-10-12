---
phase: 45-controlled-second-discharge-study
plan: 03
subsystem: hardware-study
tags: [battery, discharge-study, owner-action]
requires: ["45-01", "45-02"]
provides:
  - "## Run 2 Start Record, the 48 h reference-interval freeze and ## Run 2 Run Conditions in hardware/BATTERY-RUN.md"
  - "hardware/logs/battery-run2-params.json, complete as far as the owner reported"
  - "hardware/logs/battery-run2-export.jsonl, the owner's raw read-only export (6194 rows)"
affects: [45-04]
key-decisions:
  - "The owner ended the run at the BATTERY EMPTY park (2026-10-12) rather than waiting days for 0 %; the end reason is recorded as depleted because run-report only accepts depleted or ceiling and its check is last reading at or below 3400 mV, with the nuance written out"
requirements-completed: [BAT-01]
completed: 2026-10-12
---

# Phase 45 Plan 03: Physical discharge Summary

The owner disconnected the pack at 2026-10-05T14:08:00Z (60 s cadence, quiet hours off), the 48 h reference interval was frozen at 70 s on 2026-10-08 before any continuity verdict, and the run was stopped on 2026-10-12 at the park (last reading 3296 mV). The owner restored 300 s and quiet hours 23:30-06:00, inspected the pack (normal) and exported the full history.

Every start and end value is owner-supplied or read from the owner's export. Boot counts were never captured (the frame stayed off the computer), so the boot witness is not computable. No verdict was written in this plan.

## Deviations from Plan

- The run ended at the park, not at depletion or the ceiling (owner's call, stated in `## Run 2 Run Conditions`).
- The plan's final verify forbids a `## Run 2 Results` section at this point; the results were recorded in the same session as plan 45-04, so both sections exist when this summary is written.

## Known Stubs

None.
