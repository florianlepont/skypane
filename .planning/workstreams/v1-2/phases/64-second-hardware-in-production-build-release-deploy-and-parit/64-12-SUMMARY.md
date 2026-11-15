---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 12
status: partial-awaiting-owner
requirements: [HW2-05]
key-files:
  created:
    - hardware/SECOND-HARDWARE-MEASUREMENTS.md
---

# Phase 64 Plan 12: Second panel measurements (partial) Summary

The measurement sheet exists and is empty. The plan is waiting for the owner's
measurements on the physical unit (Task 2), so Task 3 has not run.

## Done

- Task 1: `hardware/SECOND-HARDWARE-MEASUREMENTS.md` (commit 1ad36f16). It has a
  procedure per item, the repository value each item replaces, and an empty
  values table with date, unit MAC, method and status columns.

## Waiting for the owner

- Task 2 (checkpoint:human-action): the owner fills the table on the unit
  (MAC 84:c7:bb:70:b2:7c), or replies "partial" naming the items left provisional.
- Task 3 (apply measured values) is not started.

## Still provisional (nothing changed)

No firmware value, pin, wake budget, refresh spacing, busy timeout, battery
profile or host test was touched. Everything stays as it was:

- Wake budget 700 s and the 190 s blit stage: derived by formula.
- Refresh spacing: firmware default, not tuned.
- Panel pins, key, battery sense, ADC enable and LED pins: copied or paper sources.
- Battery profile in `server/hardware.py`: provisional copy. It stays provisional
  until a real battery measurement exists.

## Deviations from plan

None. One note for the owner: `firmware/main/epd7in3e.c` prints no per-stage
timing lines and the native USB console vanishes during deep sleep, so the sheet
points to the BUSY line (GPIO4) on a logic analyser, a stopwatch, or a throwaway
instrumented build kept out of the repository. No firmware change was made for this.
