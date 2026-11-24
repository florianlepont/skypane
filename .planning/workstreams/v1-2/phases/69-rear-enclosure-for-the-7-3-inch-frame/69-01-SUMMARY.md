---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 01
subsystem: hardware
tags: [enclosure, measurements, owner-driven]
requires: []
provides:
  - hardware/ENCLOSURE-MEASUREMENTS.md with the owner's readings
affects: [hardware/ENCLOSURE-3D-DESIGN.md, hardware/ENCLOSURE-PRINT-ORDER.md, hardware/cad/source/skypane_cassette.blend]
key-files:
  modified:
    - hardware/ENCLOSURE-MEASUREMENTS.md
decisions:
  - Only the owner's reports are recorded as measured; every other number stays "design value, not measured"
requirements: [ENC-01]
completed: 2026-11-18
status: complete
---

# Phase 69 Plan 01: Measurement sheet and owner readings Summary

The measurement sheet exists in the table style of the second-hardware sheet and carries the owner's readings of 2026-11-18, with the tool each time (tape measure, kitchen scale), taken screen first, then frame, ribbon, cable and masses.

## What changed
- `hardware/ENCLOSURE-MEASUREMENTS.md`: rows 1 to 13 filled from the owner's reports; rows 7b to 7d (tab height, width, positions along the sides) and 13 (Wi-Fi antenna cable) added; notes that frames vary from one to the next.
- The owner confirmed that `hardware/cad/source/skypane_cassette.blend` is the working design file and drove its rework in a local session (see plan 02).

## Limits
- No calliper was used: every reading has about 0.1 to 0.2 mm of uncertainty. The tab force and the wood profile behind the screw lugs are not measured.
- Only one frame was measured; four more frames are planned and the owner expects variation.

## Deviations from Plan
None.
