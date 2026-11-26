---
id: SEED-022
status: dormant
planted: 2026-11-24
planted_during: "v1.2, Phase 69 (rear enclosure of the 7.3 inch frame), owner's scope decision"
trigger_when: "After the 7.3 inch enclosure is validated (Phase 69) and the owner wants a rear enclosure for the 13.3 inch frame, the first device (Seeed XIAO ePaper DIY Kit EE02); also at v1.3 hardware planning"
target_milestone: v1.3
scope: large
---

# SEED-022: Hardware rework for the 13.3 inch frame (rear enclosure) and improvements of the 7.3 inch frame

## Why This Matters

Phase 69 designs and tests a printed rear enclosure for the 7.3 inch frame
(Seeed EE04) only. The 13.3 inch frame, the live first device (Seeed XIAO ePaper
DIY Kit EE02, 13.3 inch E Ink Spectra 6, 1200 x 1600 pixels), has no enclosure
yet. The owner decided on 2026-11-24 that it stays out of Phase 69 and is planned
later as its own piece of hardware work, so that this is not forgotten.

## When to Surface

**Trigger:** after the 7.3 inch enclosure has been fitted and validated, or at
the planning of the hardware milestone (v1.3, SEED-014).

## Scope Estimate

**Large.** A new design on a larger board and panel, a different battery pack, a
larger frame, a longer wall load and its own print and fit rounds. The 7.3 inch
work gives a method and a generating script to start from (`hardware/cad/`), not
a design to scale up.

## Things to settle first

- The frame for the 13.3 inch panel and its real rebate, depth and mat
  (measured, as for the RÖDALM frame in Phase 69).
- The pack: the production frame uses the 10000 mAh Soldered pack
  (11 x 60 x 100 mm per the battery records), not the 3000 mAh pack of the 7.3 inch
  enclosure; its size and its protection need their own checks.
- The board and panel outlines of the EE02 kit and where the ribbon, the
  antenna, the USB-C port, the switch and the buttons sit.
- Print method for a part that large: the build plate of the owner's printers,
  a split into several parts, or another method (SEED-015 for series).
- What the 7.3 inch rounds taught: clearances in the material used, the ribbon
  slot, the battery pocket clearance, the hook and the stand.

## 7.3 inch improvements reported by the owner (2026-11-26)

Reported after the first assembly; they do not block Phase 69. Not measured by the assistant.

- Wall hanging on the keyhole blocks works perfectly, but the teeth of the horizontal slot are too small to be of real use: make them larger or drop them.
- The foot of the leg touches the desk on part of its surface only, with and without the IKEA frame. Accepted with anti-slip pads and no model change; the assistant's model check does not explain it. Look at it again at the next design round.
- The pack in the 7.3 inch frame is the 3000 mAh Kubii; the 10000 mAh Soldered pack is the 13.3 inch frame's.

## Breadcrumbs

- `hardware/ENCLOSURE-3D-DESIGN.md`, `hardware/ENCLOSURE-PRINT-ORDER.md`,
  `hardware/ENCLOSURE-TEST-PRINT-LOG.md`, `hardware/cad/README.md`: the 7.3 inch
  method and results.
- `hardware/BOM.md`: the 13.3 inch hardware.
- SEED-014 (enclosure and administrator tool), SEED-015 (series production).

## Notes

Planted at the owner's request. Nothing about the 13.3 inch enclosure is
designed, measured or printed.
