# Enclosure: measurement sheet

Measurements of the real parts for the rear enclosure of the 7.3 inch frame
(Seeed XIAO ePaper EE04, IKEA RÖDALM 13 x 18 cm black). The design record is
[ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md).

Rules for this sheet:

- Only a reading the owner reports goes in. An empty row stays
  "design value, not measured".
- Every filled row needs the date, the tool and the method actually used.
- Nothing is estimated, derived or rounded by the assistant.
- Tools: calliper (depth gauge if available) and a scale, 0.1 g if possible.
  No printer is needed.
- Battery safety: measure the cell with its connector unplugged from the board.
  Do not squeeze, bend or puncture it.

## Measurements and the design value each one replaces

Order: screen, then frame, then ribbon, cable and masses. Every design value
below is a design value, not measured.

| # | Item | How to take it | Design value (source) | Replaces |
|---|------|----------------|-----------------------|----------|
| 1 | Screen outline, length x width | Bare panel glass at its widest points, three readings each; record the mean and the spread | about 170.2 x 111.2 mm (vendor drawing) | Centring shim opening |
| 2 | Screen thickness | Calliper on the panel edge, away from the ribbon | about 0.91 mm (vendor drawing) | Shim thickness, stack height |
| 3 | Screen active area and its four offsets from the outline edges | Edge to edge of the coloured area; offset to each outline edge | 160 x 96 mm (vendor drawing) | Mat opening, centring |
| 4 | Frame rear rebate, length x width | Inside the rebate, both ends and the middle of each side | about 133.4 x 183.4 mm (IKEA 3D model) | Tray and lid outer size, rebate clearance |
| 5 | Frame free depth behind the screen, up to the wooden edge | Depth gauge or calliper rod, glass and mat in place, four corners | 22.7 mm (IKEA 3D model) | Tray depth, hook length |
| 6 | Mat thickness and mat opening actually cut | Calliper; record the opening size cut | 1.2 mm assumed; opening about 158 x 94 mm to cut | Shim and stack height |
| 7 | Metal tabs: depth behind the screen, thickness, number per side | Calliper | about 12.6 mm, one per side (IKEA 3D model) | Tray wall height and tab clearance |
| 8 | Screen ribbon length, panel edge to board connector, as plugged | Ruler or calliper | 24 mm assumed | Ribbon slot (4 x 28 mm) |
| 9 | Battery cable length, cell to JST-PH plug; is an extension needed | Ruler | under 105 mm per the owner, exact value unknown | Battery bay, cable routing |
| 10 | Battery outer dimensions and mass | Calliper and scale, connector unplugged | 8 x 50 x 60 mm (vendor value); mass not recorded | Battery bay, centre of gravity |
| 11 | Mass of the board, of the screen, and of the antenna with its cable | Scale | not recorded | Centre of gravity |
| 12 | Mass of the IKEA frame as it will hang (frame, glass, mat), and of the empty frame | Scale | not recorded | Hook load, centre of gravity |

## Values table

Filled from the owner's reports only.

| Item | Value | Date | Method (tool, how) | Status (measured or design value, not measured) |
|------|-------|------|--------------------|--------------------------------------------------|
| 1 Screen outline | | | | design value, not measured |
| 2 Screen thickness | | | | design value, not measured |
| 3 Active area and offsets | | | | design value, not measured |
| 4 Rebate | | | | design value, not measured |
| 5 Free depth | | | | design value, not measured |
| 6 Mat thickness and opening | | | | design value, not measured |
| 7 Metal tabs | | | | design value, not measured |
| 8 Ribbon length | | | | design value, not measured |
| 9 Battery cable | | | | design value, not measured |
| 10 Battery dimensions and mass | | | | design value, not measured |
| 11 Masses: board, screen, antenna | | | | design value, not measured |
| 12 Masses: frame | | | | design value, not measured |

## Design checks to redo after the masses are in

The checks on the model (closed meshes, no support, no wall under 0.8 mm, no
slot under 1 mm, centre of gravity on the landscape hook axis) used estimated
masses: tray about 57 g, lid about 48 g, stand about 11 g, shim about 5 g
(design values, not measured). The owner reruns them after the measurements.

## Notes

None yet.

## CAD file state

Not yet reported by the owner. Questions: is `hardware/cad/skypane_cassette.blend`
saved and current (date of last save); are the four parts and the script
`skypane_cassette.py` in it; are the Father Christmas test figurine and the
abandoned versions still in it; was the file lost.
