---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
status: complete
updated: 2026-11-26
requirements: [ENC-01]
---

# Phase 69 verification: rear enclosure for the 7.3 inch frame

State on 2026-11-26, phase closed. The phase ran as an owner-driven track: the owner printed and
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
| 5 | Assembled frame validated by the owner | Met | reported by the owner on 2026-11-26: wall hanging "works perfectly"; USB-C, switch, RESET and buttons reachable ("no problem"); hinge pins snap in and hold, stop resists, leg does not close under the frame; lid holds on the frame tabs; tray, shim, board fit. The pack in the 7.3 inch frame is the 3000 mAh Kubii (owner, 2026-11-26). Not reported: screen centred behind the mat, battery not pinched |
| 6 | Files, assembly note, BOM, SEED-014 | Met | design and printable files stored; `hardware/ENCLOSURE-ASSEMBLY.md`, the enclosure section of `hardware/BOM.md`, SEED-014 (calibration-at-setup idea), SEED-022 |
| 7 | Image reframed to the mat window (D-14) | Met | plan 69-08; PR 614 merged (CI green on Linux, 13.3 inch images unchanged) and deployed 2026-11-26; window read from the owner's photo and confirmed by the owner; the owner tested the assembled frame after deploy and reported everything good (`hardware/ENCLOSURE-VISIBLE-WINDOW.md`) |

## The three closing items (owner, 2026-11-26), all done

1. Wi-Fi with the enclosure: concluded by the owner's decision of 2026-11-26. Bare history of 2026-11-19 to 2026-11-23 (about 1315 wakes, hourly medians around -60 dBm; A1 16 wakes, -59) against 541 wakes with the enclosure (median -59): no loss, difference 0 to +1 dB. Not the interleaved protocol (the owner declined to take the frame out again, printed PLA threads). The signal was 13 dB lower from 2026-11-23 about 20:00 to 2026-11-24 05:24 UTC because the frame was moved (reported by the owner on 2026-11-26) (`hardware/ENCLOSURE-WIFI-TEST.md`).
2. Image reframing to the visible window of the mat (D-14): done, plan 69-08, PR 614 merged and deployed on 2026-11-26; the owner tested the assembled frame afterwards and reported everything good.
3. Assembly note, BOM and SEED-014: done (`hardware/ENCLOSURE-ASSEMBLY.md`, enclosure section of `hardware/BOM.md`, SEED-014, SEED-022). Not reported by the owner: the format and price of the anti-slip pads (not used).

## Reported on 2026-11-26 and moved to SEED-022 (they do not block closing)

- The teeth of the horizontal hook slot are too small to be useful (wall hanging itself works perfectly).
- The foot of the leg touches the desk on part of its surface only; the owner decided to change nothing in the model and did not use the anti-slip pads (2026-11-26), so the effect of pads is not tested.
