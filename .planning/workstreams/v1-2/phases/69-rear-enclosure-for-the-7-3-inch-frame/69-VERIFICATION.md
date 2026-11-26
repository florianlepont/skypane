---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
status: in_progress_three_items_left
updated: 2026-11-26
requirements: [ENC-01]
---

# Phase 69 verification: rear enclosure for the 7.3 inch frame

State on 2026-11-26. The phase ran as an owner-driven track: the owner printed and
assembled the parts and reported results in chat; plans 03 and 04 were done directly
on the design (no summary) and recorded in `hardware/ENCLOSURE-TEST-PRINT-LOG.md`,
`ENCLOSURE-PRINT-ORDER.md` and `ENCLOSURE-3D-DESIGN.md`. Everything below is what the
owner reported or what the assistant computed; nothing was measured by the assistant
on a printed part.

## Success criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Measurements recorded, design updated | Met | plans 01 and 02 (summaries); `ENCLOSURE-MEASUREMENTS.md` |
| 2 | Open choices decided | Met | plan 02 summary; settings in the print log |
| 3 | Parts exported, sliced, checked | Met | STL in `hardware/cad/print/`, print project `skypane_print_project.3mf`; supports enabled for the one-part tray (owner, 2026-11-26) |
| 4 | Test print, clearances adjusted | Met | rounds of 2026-11-23 and 2026-11-24; changes in `ENCLOSURE-PRINT-ORDER.md` |
| 5 | Assembled frame validated by the owner | Met except Wi-Fi and image reframing | reported by the owner on 2026-11-26: wall hanging "works perfectly"; USB-C, switch, RESET and buttons reachable ("no problem"); hinge pins snap in and hold, stop resists, leg does not close under the frame; lid holds on the frame tabs; tray, shim, board fit. The pack in the 7.3 inch frame is the 3000 mAh Kubii (owner, 2026-11-26). Not reported: screen centred behind the mat, battery not pinched |
| 6 | Files, assembly note, BOM, SEED-014 | Open | design and printable files are stored; assembly note, BOM and SEED-014 update to do now (owner, 2026-11-26) |

## Left to do before closing (owner, 2026-11-26)

1. Wi-Fi with the enclosure against the bare-frame baseline: to be discussed and decided (the protocol is in `hardware/ENCLOSURE-WIFI-TEST.md`; no reading with the enclosure exists).
2. Image reframing to the visible window of the mat (D-14): to be done now; needs its own plan before any change.
3. Assembly note, BOM update, SEED-014 update (plan 07): to be done now.

## Reported on 2026-11-26 and moved to SEED-022 (they do not block closing)

- The teeth of the horizontal hook slot are too small to be useful (wall hanging itself works perfectly).
- The foot of the leg touches the desk on part of its surface only; accepted with anti-slip pads, no model change.
