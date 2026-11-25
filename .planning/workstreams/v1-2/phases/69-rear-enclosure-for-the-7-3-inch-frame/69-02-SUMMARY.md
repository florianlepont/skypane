---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 02
subsystem: hardware
tags: [enclosure, blender, stl, print-order]
requires: [69-01]
provides:
  - reworked design, four STL, corrected and consistent hardware records, dated owner reports
affects: [hardware/ENCLOSURE-PRINT-ORDER.md, hardware/ENCLOSURE-3D-DESIGN.md, hardware/ENCLOSURE-AUDIT.md, hardware/ENCLOSURE-MEASUREMENTS.md]
key-files:
  modified:
    - hardware/ENCLOSURE-PRINT-ORDER.md
    - hardware/ENCLOSURE-3D-DESIGN.md
    - hardware/ENCLOSURE-AUDIT.md
    - hardware/ENCLOSURE-MEASUREMENTS.md
decisions:
  - One loose stand plate (20 degree tilt, landscape and portrait) replaces the hinged stand; stored flat on the lid back with magnets
  - Plates 132.0 x 182.0 mm; shim 1.0 mm; battery pocket moved 10 mm; landscape hook with notches
  - Printer purchase is not decided; the machine that prints is recorded per round
requirements: [ENC-01]
completed: 2026-11-19
status: complete
---

# Phase 69 Plan 02: Design closeout and owner questions Summary

Status: complete for the closeout work (stale-text sweep, go condition, owner questions asked and replies recorded). Several owner answers are still open and are handed to later plans (see below). Nothing is measured on a printed part and nothing has been printed.

## What is true

- The design was reworked with the owner on 2026-11-18 and 2026-11-19 in `hardware/cad/source/skypane_cassette.blend`; four STL are in `hardware/cad/print/` (exported 2026-11-18 per the previous record).
- The owner sliced all four parts on 2026-11-19 (Bambu Studio 2.9.1.70, P2S profile, PETG Basic, 0.20 mm, 3 walls, 20 % grid, textured PEI, no supports). Times and masses are in the print order: tray 1 h 32 min, 56.29 g; lid 1 h 22 min, 51.56 g; stand and shim 29 min 8 s, 11.70 g together. Nothing has been printed.
- The thinnest wall and slot are model values computed in Blender, not read from Bambu Studio. The fibreboard edge depth (74 mm, called wood in the model), the mass centre depth (6 mm) and the tab grip are model values too.

## Owner replies of 2026-11-19 (reported by the owner)

- Exported STL match the final blend: "oui". No export date and no statement on what `skypane_lid.3mf` is: both stay open.
- Slicer warnings: none ("non, pas d'avertissements"), not detailed per part, no reading of thin walls.
- Calliper: the owner did not know what it is; it was explained to him on 2026-11-19 (a pied a coulisse, about 0.02 mm reading, 10 to 20 EUR or easy to borrow). He has not said whether he has one, borrows or buys.

## What changed

- `ENCLOSURE-PRINT-ORDER.md`: two-cell rows in the print-order spec; corrected Decisions table (P2S slice, textured PEI, PETG Basic, filament, lid fixing and insert caveat) with new rows Magnets, Printer purchase (not decided), Measuring tool, Lid opening; "Superseded and out-of-scope notes" (mat opening of 158 x 94 mm, Soldered 10000 mAh pack not fitting the Kubii pocket); Files table with export and blend columns, the `.3mf` and the `.blend1` backup; slicer warnings line; "Go condition for the print rounds".
- `ENCLOSURE-3D-DESIGN.md`: status, decisions, open questions and files updated; frame material terms (fibreboard, polystyrene front sheet); article 105.488.67 versus 105.488.72 noted; arrival column in the To buy table.
- `ENCLOSURE-AUDIT.md`: hook load reconciled (3.2 to 4.0 N, 5.8 N kept as a conservative test load), material terms, screw lugs as an anti-shift aid, first-layer decision, top line on the basis of the findings.
- `ENCLOSURE-MEASUREMENTS.md`: row 6b added as open, asked on 2026-11-19, no value.

Stale items fixed: research divergence rows 1 to 3, 12, 13 and 15 to 22 as covered by the edits above, the print-order table formatting, the hook load.

## Open items handed to later plans

- Calliper: not confirmed in hand; round A is blocked until one is.
- Mat window height 90 or 99 mm: unanswered (row 6b open).
- Arrival of the magnets, M2 screws and JST extensions, and the screw head type: unanswered.
- Export date of the STL and the role of `skypane_lid.3mf`: unanswered.
- Wake cadence of the second hardware: asked in the Wi-Fi plan.
- Printer in use per round, spool, plate: recorded per round in the test-print log.

## Deviations from Plan

The checkpoint task was answered only in part by the owner; the unanswered fields stay open with the date asked. The test-print log referenced by the Decisions table is created by a later plan and does not exist yet.
