---
phase: 45-controlled-second-discharge-study
plan: 04
subsystem: hardware-study
tags: [battery, run-report, results]
requires: ["45-03"]
provides:
  - "hardware/logs/battery-run2-report.json, committed verbatim from logtools.py run-report"
  - "## Run 2 Results in hardware/BATTERY-RUN.md, every figure copied from the report"
affects: [46]
key-decisions:
  - "Failed gates reported and diagnosed, never retuned (thresholds 0.95 / 3 / 100 / 3400 untouched)"
requirements-completed: [BAT-02]
completed: 2026-10-12
---

# Phase 45 Plan 04: Run 2 results Summary

`run-report` ran on the owner's export (6193 usable rows, sha256 `540d8f56aeab41b3a2de395a4f5820e069a9b4c1f470e526c0df12fc0557efdb`) and exited 1 (a verdict failed, not a refusal). Window 2026-10-05T14:08:05Z to 2026-10-12T16:22:02Z (7.093 days); normal-cadence window ends 2026-10-10T20:33:30Z.

- Continuity: FAIL. Coverage 0.946 against 0.95 (the normal-window mean gap is 5.8 % above the frozen 70 s reference, the drift case of protocol 4a) and largest gap 5.97 intervals against 3 (22 isolated gaps of 381-418 s; cause not established).
- Voltage validity: PASS (drop 593.1 mV, last reading 3296 mV).
- Baseline: PASS (fw-v1.0.2 only).
- Boot witness: not computable.

No two-run model and no interval or pack decision was written; that is Phase 46 (BAT-03).

## Deviations from Plan

None to the plan's rules. The gap listing behind the largest-gap diagnosis came from a separate pass over the export and is labelled as such in the Results section, not as report output.

## Known Stubs

None.
