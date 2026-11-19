---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 02
subsystem: hardware
tags: [enclosure, blender, stl, print-order]
requires: [69-01]
provides:
  - reworked design, four STL, filled print-order tables
affects: [hardware/ENCLOSURE-PRINT-ORDER.md, hardware/ENCLOSURE-3D-DESIGN.md, hardware/ENCLOSURE-AUDIT.md, hardware/cad/]
key-files:
  modified:
    - hardware/cad/skypane_cassette.blend
    - hardware/cad/export/skypane_tray.stl
    - hardware/cad/export/skypane_lid.stl
    - hardware/cad/export/skypane_stand.stl
    - hardware/cad/export/skypane_shim.stl
    - hardware/ENCLOSURE-PRINT-ORDER.md
    - hardware/ENCLOSURE-AUDIT.md
decisions:
  - One loose stand plate (20 degree tilt, landscape and portrait) replaces the hinged stand; stored flat on the lid back with magnets
  - Plates 132.0 x 182.0 mm; shim 1.0 mm; battery pocket moved 10 mm; landscape hook with notches
requirements: [ENC-01]
completed: 2026-11-19
status: incomplete
---

# Phase 69 Plan 02: Design update, export and print-order spec Summary

Status: incomplete. The design, the export and the tables are done; the slice check by the owner is not.

## What changed
- The design was reworked with the owner, one change at a time, in `hardware/cad/skypane_cassette.blend`: new tray layout with engraved component names, four wide tab pads, optional screw lugs, antenna moved above the board, landscape hook with notches, signature and logo, board indications (RESET, ON, OFF), one loose stand plate with two stop walls and magnet storage, shim 1.0 mm, battery pocket moved 10 mm for the cable exit.
- Four STL exported to `hardware/cad/export/` in their printing pose: closed meshes, no support needed (tray, stand, shim; the lid has 13 small groups within the 4.5 mm bridge rule).
- `hardware/ENCLOSURE-PRINT-ORDER.md`: design changes, design checks redone (computed in Blender, not printed), print-order spec; `hardware/ENCLOSURE-AUDIT.md` with 16 findings.

## Not done
- No slice in Bambu Studio and no print: the slice check table is empty and must be filled from what the owner sees.
- Nothing is measured on a printed part. The IKEA wood edge (74 mm), the mass centre depth (6 mm) and the tab grip are model values.

## Deviations from Plan
The plan expected a hinged stand and a 132.6 x 182.6 mm plate; the owner chose a loose plate and a 132.0 x 182.0 mm plate after the audit.
