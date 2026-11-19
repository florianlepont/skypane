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
| 1 Screen outline | 170 x 111 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 2 Screen thickness | 0.9 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 3 Active area and offsets | Active area 160 x 96 mm; offsets left 4, right 4, top 4, bottom 10 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 4 Rebate | 133 x 183 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 5 Free depth | 23 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 6 Mat thickness and opening | Thickness 1 mm; opening 140 x 99 mm (as it is today) | 2026-11-18 | Tape measure (no calliper) | measured |
| 7 Metal tabs | Depth 8 mm (corrected by the owner on 2026-11-18, first reported as 0.8 mm); thickness not measurable; 1 per side | 2026-11-18 | Tape measure (no calliper) | measured |
| 8 Ribbon length | 24 mm | 2026-11-18 | Tape measure (no calliper) | measured |
| 9 Battery cable | 95 mm; extension needed: depends on the design (owner) | 2026-11-18 | Tape measure (no calliper) | measured |
| 10 Battery dimensions and mass | Thickness 8, width 60, length 50 mm; mass 49 g; pack: Kubii 3000 mAh (confirmed by the owner, 2026-11-18) | 2026-11-18 | Tape measure (no calliper) | measured |
| 11 Masses: board, screen, antenna | Board with antenna and cable 20 g; screen 36 g | 2026-11-18 | Kitchen scale | measured |
| 12 Masses: frame | Complete frame 173 g; empty frame 149 g | 2026-11-18 | Kitchen scale | measured |
| 7b Metal tab, height behind the back of the screen, folded | 15 mm (confirmed by the owner) | 2026-11-18 | Reported in the design session; tool not stated | owner-reported |
| 7c Metal tab, width | 4 mm | 2026-11-18 | Confirmed by the owner in the design session; tool not stated | owner-reported |
| 7d Metal tabs, position along each side (seen from the back, frame in portrait) | Top tab: its right edge is 48 mm from the right corner of the rebate. Bottom tab: its right edge is 77 mm from the right corner. Left tab: its lower edge is 86 mm from the bottom edge of the rebate. Right tab: 82 mm, same method | 2026-11-18 | Reported in the design session; tool not stated | owner-reported |
| 13 Wi-Fi antenna cable | 50 mm | 2026-11-18 | Reported in the design session; tool not stated | owner-reported |

## Design checks to redo after the masses are in

The checks on the model (closed meshes, no support, no wall under 0.8 mm, no
slot under 1 mm, centre of gravity on the landscape hook axis) used estimated
masses: tray about 57 g, lid about 48 g, stand about 11 g, shim about 6 g
(design values, not measured). The owner reruns them after the measurements.

## Notes

Reported by the owner on 2026-11-18. The owner has a tape measure and no
calliper, so length readings have about 1 mm resolution; the design clearances
are 0.4 mm per side, smaller than that. Values are recorded as reported, not
rounded or corrected.

Points to settle with the owner (nothing here is concluded by the assistant):

- Row 6: the mat keeps its current opening of 140 x 99 mm (owner decision,
  2026-11-18). The displayed image is to be adapted to what shows through the
  mat, instead of recutting the mat. The active area reported in row 3 is
  160 x 96 mm, so a 140 mm wide opening hides part of its width, and 99 mm is
  taller than 96 mm. Changing the displayed image is a rendering change, outside
  this phase (no code); the enclosure is centred on the mat opening, to be
  confirmed with the owner.
- Row 7: tab depth corrected by the owner to 8 mm (design value about 12.6 mm,
  design value, not measured).
- Row 7, clarification by the owner on 2026-11-18: the 8 mm is the length of the
  tab (how far it reaches over the back), not its depth behind the screen. The
  height of the folded tab is row 7b (15 mm). Rows 7b to 7d replace the design
  value of about 12.6 mm and the "middle of each side" assumption. The owner
  adds that frames probably vary from one to another, so the lid pads are wide.
- Row 13: the vendor sheet gives 80 mm for the antenna coaxial cable; the owner's
  own reading is 50 mm, which is the one used.
- Row 10: the pack in the enclosure is the Kubii 3000 mAh (owner, 2026-11-18);
  the reported dimensions match its vendor size (8 x 50 x 60 mm). The frame in
  production uses another pack today (see `BATTERY-MODEL.md`).
- Row 11: the 20 g reading includes the antenna and its cable; the board alone
  was not weighed.
- Row 3: offsets and sizes agree with row 1 to within the tape's resolution.
- Row 9: whether a JST-PH extension is needed depends on the final design.

## CAD file state

Reported by the owner on 2026-11-18, not checked by Claude:

- `hardware/cad/skypane_cassette.blend` is saved and current; last save
  2026-11-17.
- The four parts and the script `skypane_cassette.py` are in it.
- The Father Christmas figurine and the abandoned versions are no longer in it.
- The file is not lost.
- The owner adds that this version is not final and that the design must be
  reworked together; Claude cannot open Blender from the cloud session, so that
  work needs a local session on the owner's computer.
