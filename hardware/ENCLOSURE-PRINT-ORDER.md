# Enclosure: print order

Decisions, design changes, checks and the spec sent to the print provider for
the rear enclosure of the 7.3 inch frame. The design record is
[ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md); the measurements are in
[ENCLOSURE-MEASUREMENTS.md](ENCLOSURE-MEASUREMENTS.md).

Rules: every number copied from the design record is a design value, not
measured, until the owner reports otherwise. Nothing here says a part was
exported, sliced or printed until the owner reports it.

Centring reference (owner decision, 2026-11-18): everything is centred on the
opening of the mat (140 mm wide; 90 mm high per the owner's report of 2026-11-19, first read as 99 mm, not remeasured), not on the active area of the screen.

## Decisions

| Subject | Proposed value | Status | Date |
|---|---|---|---|
| Printer or means | The parts were sliced for a Bambu Lab P2S profile (owner's slice of 2026-11-19). The first prints are planned on the Bambu Lab X1 series printers at the owner's workplace (decided by the owner on 2026-11-18). The machine that actually prints is to be recorded per round in [ENCLOSURE-TEST-PRINT-LOG.md](ENCLOSURE-TEST-PRINT-LOG.md); it is not guessed here. | decided by the owner (printer in use: open, per round) | 2026-11-18 |
| Provider | The owner's workplace (own access, no print service) | decided by the owner | 2026-11-18 |
| Material | PETG Basic (as read on the owner's slice of 2026-11-19); any colour (changed by the owner on 2026-11-18; the previous proposal was black); colour recorded per round | decided by the owner | 2026-11-18 |
| Nozzle | 0.4 mm, or another if needed | decided by the owner | 2026-11-18 |
| Filament | Bambu PETG Basic profile; colour and spool recorded per round in the test-print log; do not change brand between rounds; dry the spool if it has been open long | decided by the owner (brand); spool open | 2026-11-18 |
| Build plate | Textured PEI, as read on the owner's slice of 2026-11-19; keep the same plate every round | reported by the owner | 2026-11-19 |
| Lid fixing | M2 self-tapping screws, pilot holes 1.7 mm, through holes 2.4 mm (design values, not measured). Heat-set inserts would need a redesign of the bosses (standoffs are 4.0 mm across, lid corner wall about 3.2 mm), so they are not a drop-in swap; decided only after the screw reuse test (5 removal and insertion cycles per lid screw, a design value the owner may adjust). Lengths from the model, assuming a pan head: lid corners M2 x 6 to x 8 (pilot 7 mm deep under a 1.5 mm lid); board standoffs M2 x 4 at most (a 6 mm screw would pierce the 0.8 mm pilot floor). Screw head type: open, asked on 2026-11-19 | decided by the owner; lengths computed by the assistant | 2026-11-19 |
| Magnets | 6 x 2 mm, pocket 6.2 x 2.2 mm (design value, not measured). Arrival: not yet arrived (reported by the owner on 2026-11-19). Real size by calliper, pocket ladder and polarity marking: open, to be filled by the owner | open | 2026-11-19 |
| Printer purchase | Not decided; the owner's call. Offer noted until 2026-12-01 to recheck; the first fit result arrives after that date. The X2D Combo (749 EUR noted) is not bought | not decided | 2026-11-19 |
| Measuring tool | Calliper: none used so far (all readings so far are tape measure). The owner reported on 2026-11-19 that he did not know what a calliper is; it was explained to him on 2026-11-19 (a pied a coulisse, about 0.02 mm reading, 10 to 20 EUR or easy to borrow). On 2026-11-19 he reported that he has no calliper; whether he buys or borrows one is not decided (asked on 2026-11-19). Round A is blocked until a calliper is in hand | open: no calliper (reported by the owner on 2026-11-19); to buy or borrow, not decided | 2026-11-19 |
| Lid opening | No tool-free latch; a PH0 or PH00 screwdriver opens the lid. A recommendation the owner may overrule | proposed | 2026-11-19 |
| Slicer | Bambu Studio (2.9.1.70, used 2026-11-19) | decided by the owner | 2026-11-18 |

### Superseded and out-of-scope notes

(a) The mat opening of about 158 x 94 mm to cut, written in the first measurement plan and the first decision record, is superseded by the owner's decision to keep the mat's existing opening (140 x 99 mm as first read, tape measure). The height is 90 mm according to the owner (reported on 2026-11-19: the 99 was a typing error), not remeasured. (b) The pack enclosed in this design is the single Kubii 3000 mAh unit (8 x 50 x 60 mm). The frame in production uses the 10000 mAh Soldered pack (11 x 60 x 100 mm per the battery records), which does not fit this pocket, and a replacement of the Kubii pack may differ in size (the vendor listing showed out of stock on 2026-11-01).

## Design changes from the measurements

Origin of every row: the design session in Blender with the owner on 2026-11-18,
edited by the assistant. "Design value, not measured" applies to every new value
unless a measurement row is given. Nothing has been printed.

| Part | Dimension | Old design value (design value, not measured) | New value | Measurement row | Date |
|---|---|---|---|---|---|
| Tray, lid, shim | Plate size (audit, owner choice) | 132.6 x 182.6 mm, 0.2 mm clearance per side; the model's smallest clearance to the fibreboard frame in the model was 0.07 mm | 132.0 x 182.0 mm, 0.5 mm per side; smallest clearance in the model 0.37 mm (tray) and 0.44 mm (lid) | 4 (reading 133 x 183, about 1 mm resolution) | 2026-11-18 |
| Lid | Landscape hook slot edge (owner request) | smooth slot edge, position held by friction only | 12 V notches with a flat bottom, 2 mm pitch and 0.6 mm deep, on the edge that carries the screw shank, so the frame sits in a notch and is shifted by lifting it one notch (about 2.4 degrees of tilt per notch); graduations every 2 mm engraved on the hook block, the centre mark and the two ends open to the block edge. The 0.4 mm wide ridges between notches are functional, not free-standing walls | none | 2026-11-18 |
| Lid | Landscape hook rail centre (audit, owner choice) | y = 0 mm | y = +3 mm, adjustment still +-12 mm around it; the estimated centre of gravity is at y = +0.6 to +5.2 mm | none | 2026-11-18 |
| Lid | Support under the frame tabs | none; lid top at 12.5 mm, tabs assumed at 12.6 mm | 4 pads, top at 15.0 mm, 20 mm wide along the side and 8 mm deep (owner asked for wide pads to tolerate frame-to-frame variation) | 7b | 2026-11-18 |
| Lid | Pad positions along the sides | at the middle of each side | centres, from the rebate centre: top +16.5, bottom -12.5, left -3.5, right -7.5 mm; computed by the assistant from the owner's four readings and a 4 mm tab width | 7c, 7d | 2026-11-18 |
| Lid | Screw lugs on the edge (new, owner request) | none | 4 lugs 4 x 8 mm, z 12.5 to 22 mm, 2.2 mm horizontal hole at z 18 mm, head recess 4.2 mm; assume a vertical rebate wall between z 14 and 22 mm, not measured | none | 2026-11-18 |
| Lid | Stand stop walls (new) | hinge knuckles for a folding stand | two stop walls 2.4 mm thick and 4.5 mm high with two 2.4 mm side guides (same thickness, no step), 0.5 mm clearance to the plate: landscape at x 6.9 mm, portrait at y -32 mm | none | 2026-11-18 |
| Lid | Signature and logo (new, owner request) | none | "SKYPANE" and the SkyPane mark (the S in its tile, from `companion/static/favicon.svg`) engraved 0.4 mm deep on the wall side; the S strokes are 1.9 mm wide, the tile outline 1.0 mm | none | 2026-11-18 |
| Tray | Antenna position | top left, on a 41 x 21 mm platform with ribs and a 0.6 mm top plate | above the board: 40 x 20 mm footprint at x 12 to 52 mm and y 65 to 85 mm, on a solid block; moved instead of buying an extension | 13 | 2026-11-18 |
| Tray | Interior layout | scattered stops and ribs, L-shaped bay with filler blocks | one continuous partition, battery pocket with solid walls, service well with 1.2 mm walls and rounded corners, free area under the partition; names and outlines of the components engraved 0.4 mm | none | 2026-11-18 |
| Shim | Thickness (audit, owner choice) | 0.8 mm, 0.12 mm lower than the screen (0.92 in the model), so the mat would rest on the screen glass | 1.0 mm (5 layers of 0.2 mm), 0.08 mm higher than the screen, 0.1 mm below the mat; screen and mat thicknesses read with a tape measure, about 0.1 to 0.2 mm uncertain, so the value stays a design value; at the first fit, check with a strip of paper between mat and shim | 2, 6 (tape measure) | 2026-11-18 |
| Tray | Battery pocket position (owner request: the cable could not leave the corner) | pocket centre y = -1.65 mm; the lower wall of the service well sat 0.5 mm above the cell, 0.6 mm of room for the cable at the top-right corner | pocket centre y = -11.65 mm (10 mm lower); the service-well wall stays where it was, so the lid opening is unchanged; the short top wall stops at x = -25 mm, which leaves about 10 mm free above the corner where the wires leave; the cable then runs west of the well and along the strip above it, staying inside the box | 10 (cable on the owner's photo) | 2026-11-18 |
| Lid, stand | Stand storage (new, owner request) | none | two round bosses 10 mm diameter, 3 mm high, at x = 31 mm, y = 11 and 39 mm on the wall side, each with a 6.2 x 2.2 mm magnet pocket; two matching pockets on the small face of the stand plate, 28 mm apart; the plate is stored flat, small face down, 3.6 mm from the wall; four 6 x 2 mm magnets to buy | none | 2026-11-18 |
| Lid | Board indications (new, owner request) | none | "RESET" (in front of the fourth button, the one next to the switch, y = -4.5 mm), "OFF" and "ON" (switch travel, ON downward on the owner's reading) and a down arrow, engraved 0.4 mm deep, letters 7 mm high, on the lid back to the right of the service opening (board side), x 12 to 39 mm, y -23 to -1 mm. Engraved lines are 0.7 mm wide, under the 1.0 mm rule: a bolder line breaks the mesh of the S, so this is the thickest clean setting; decorative | none | 2026-11-19 |
| Tray | Board standoffs | 5.2 mm diameter, pilot hole 0.6 mm above the floor | 4.0 mm diameter, pilot floor 0.8 mm (no wall under 0.8 mm) | none | 2026-11-18 |
| Tray | Columns under the stop walls (new) | none | 4 columns of 6 mm diameter, centred under the 2.4 mm walls, from the floor to the lid, to carry the lid where the stand pushes | none | 2026-11-18 |
| Stand | Concept and size | folding stand with hinge pin, about 54 x 68 x 3 mm | one loose plate, 30 x 71 x 4 mm (64.7 mm on the small face), leaning on a stop wall, serves landscape and portrait; no hinge, no clip | none | 2026-11-18 |
| Stand | Frame tilt | not defined | 20 degrees back, chosen by the owner after the assistant's stability estimate | none | 2026-11-18 |
| Reference model (not printed) | Mat of the IKEA frame | opening 141.8 x 91.8 mm, 1.84 mm thick, behind the screen | opening 140 x 99 mm (the owner reported on 2026-11-19 that the real height is 90 mm; the model is unchanged), 1.0 mm thick, in front of the screen against the glass (position a design value) | 6 | 2026-11-18 |
| Reference model (not printed) | Frame tabs | middle of each side, 12.6 mm behind the screen | owner's positions and 15 mm height | 7b, 7c, 7d | 2026-11-18 |

Values kept, because the model and the owner's tape readings differ by about
1 mm or less, which is the tape's resolution (owner instruction, 2026-11-18):
screen outline 170.2 x 111.2 x 0.91 mm (reading 170 x 111 x 0.9), rebate
(reading 133 x 183; the tray, lid and shim plates were then reduced from 132.6 x 182.6 to 132.0 x 182.0 mm after the audit, see the rows above), free depth 22.7 mm (reading 23),
battery bay 50 x 60 x 8 mm (reading 50 x 60 x 8), ribbon slot 4 x 28 mm (reading 24 mm
ribbon), tab length about 7.8 mm (reading 8).

## Design checks redone

Origin: computed by the assistant in Blender on the current model on 2026-11-18.
These are checks on the model, not measurements and not a slice. The owner has
not reported any check of his own yet. The thinnest wall and slot values are model values from Blender, not read from Bambu Studio (see Slice check).

| Check | Result | Date |
|---|---|---|
| Closed meshes | Tray, lid, stand and shim: all closed, 0 open edges | 2026-11-18 |
| No support needed | Tray, stand, shim: no face tilted under 45 degrees from the horizontal. Lid: 13 small groups, hole tops up to 3.0 mm across and bridges up to 4.5 mm; none needs support under the 4.5 mm rule | 2026-11-18 |
| No wall under 0.8 mm | No wall under 0.8 mm outside the engraved letters. 31 faces of 0.24 mm in the tray labels and 22 in the lid signature and logo: thin ridges between letter strokes and between the logo grooves, decorative, slicers drop them | 2026-11-18 |
| No slot under 1 mm | Narrowest slot: tray 1.09 mm, lid 1.0 mm (0.71 mm for the engraved board indications, decorative), stand none, shim none | 2026-11-18 |
| Bridges 4.5 mm at most | Longest bridge 4.5 mm (lid hook cavity); 3.0 mm for the lug holes | 2026-11-18 |
| Centre of gravity against the landscape hook axis (with the measured masses) | With the owner's masses (frame 173 g, screen 36 g, battery 49 g, board with antenna and cable 20 g) and the printed parts solid or at 40 % of solid (PETG 1.27 g/cm3, design value): x -3.6 to -2.6 mm, y +1.5 to +5.1 mm before the battery pocket was moved 10 mm (about -1.2 to -1.5 mm in y after it: roughly 0 to +3.9 mm, computed, not measured), total 328 to 403 g, without the stand plate. The landscape hook axis is at y = 0 with +-12 mm of adjustment | 2026-11-18 |
| Stand: foot on the desk at 20 degrees | Both lower corners of the plate at 0.00 mm above the desk, in landscape and in portrait; the top end lies flat on the lid against the stop wall | 2026-11-18 |
| Stand: forward-tipping margin | 7.5 degrees in landscape and 10.5 degrees in portrait, assuming the frame mass centre at 6 mm depth and the fibreboard edge (called wood in the model) at 74 mm from the lid origin (IKEA model, not measured); 5.4 and 8.9 degrees if the mass centre is at 3 mm depth. 1 mm of plate length changes the tilt by about 1.4 degrees | 2026-11-18 |

## Print-order spec

To use for the prints at the owner's workplace. It contains dimensions only: no device identifier,
address or secret.

| Item | Value |
|---|---|
| Parts | Tray, lid, stand, shim; quantity 1 each. File names: `skypane_tray`, `skypane_lid`, `skypane_stand`, `skypane_shim` (`.stl` or `.3mf`) |
| Orientation | Tray: floor down. Lid: inner face (against the tray) down. Stand plate: large face down. Shim: flat. No support. The machine, spool, plate and settings are recorded per round in the test-print log |
| Material | PETG Basic; any colour (decided by the owner on 2026-11-18; the previous proposal was black) |
| Nozzle | 0.4 mm, or another if needed (decided by the owner on 2026-11-18) |
| Layer height and infill | To record from the slice |
| Fit-critical dimensions | Fit in the frame rebate, tab pads and screw lugs, stop walls and stand plate, screw holes, battery bay, ribbon slot |
| To report back | Per round: the machine, spool, plate and settings actually used; no provider exists, so no cost per part |

## Slice check

Sliced by the owner on 2026-11-19 in Bambu Studio 2.9.1.70 for a Bambu Lab P2S, 0.4 mm nozzle,
textured PEI plate, PETG Basic, profile "0.20mm Standard @BBL P2S" with 3 walls and 20 % grid infill
(read on the owner's screenshots), supports switched off. Nothing has been printed. The tray, lid and
the stand and shim each went on their own plate. Times and costs are the owner's readings from the slicer;
the masses are the owner's readings too. The thinnest wall and slot are not shown by the slicer: they are the values computed by the assistant on the model in Blender (2026-11-18), not read from Bambu Studio. The owner reported on 2026-11-19 that no slicer alert remained once the parts were on separate plates (the first slice, with the tray and lid on top of each other, raised a toolpath conflict warning).

Slicer warnings per part: no slicer warnings, reported by the owner on 2026-11-19 ("non, pas d'avertissements"), not detailed per part and without any reading of thin walls.

| Part | File | Slicer and version | Layer height | Walls | Infill | Supports needed | Thinnest wall (mm) | Thinnest slot (mm) | Estimated mass (g) | Estimated print time |
|---|---|---|---|---|---|---|---|---|---|---|
| Tray | `skypane_tray.stl` | Bambu Studio 2.9.1.70 | 0.20 mm | 3 | 20 % grid | no (switched off) | 1.2 (service well and partition; letter ridges down to 0.24 excluded) | 1.09 | 56.29 | 1 h 32 min (cost 0.79) |
| Lid | `skypane_lid.stl` | Bambu Studio 2.9.1.70 | 0.20 mm | 3 | 20 % grid | no (switched off) | 0.4 (ridges between the hook notches; letters excluded) | 1.0 (0.71 for the engraved indications) | 51.56 | 1 h 22 min (cost 0.72) |
| Stand | `skypane_stand.stl` | Bambu Studio 2.9.1.70 | 0.20 mm | 3 | 20 % grid | no (switched off) | 4.0 (plate thickness) | none | 11.70 for stand and shim together | 29 min 8 s for stand and shim together (cost 0.16) |
| Shim | `skypane_shim.stl` | Bambu Studio 2.9.1.70 | 0.20 mm | 3 | 20 % grid | no (switched off) | 5.4 (narrowest bar of the frame, 1.0 thick) | none | (with the stand) | (with the stand, see above) |

## Files

Printable files are in `hardware/cad/export/`, one per part, exported by the
assistant from `hardware/cad/skypane_cassette.blend` on 2026-11-18 as binary STL
in millimetres, each part lying in its printing pose (lowest point at z = 0):

| File | Size of the part | Triangles | Exported (as reported) | Blend saved (as reported) |
|---|---|---|---|---|
| `skypane_tray.stl` | 132.0 x 182.0 x 11.0 mm | 7298 | 2026-11-18 per the previous record; export date to confirm (asked 2026-11-19) | to confirm |
| `skypane_lid.stl` | 132.0 x 182.0 x 11.2 mm | 8406 | as above | to confirm |
| `skypane_stand.stl` | 71.0 x 30.0 x 4.0 mm | 396 | as above | to confirm |
| `skypane_shim.stl` | 132.0 x 182.0 x 1.0 mm | 208 | as above | to confirm |
| `skypane_lid.3mf` | not read | not read | present in the export folder; its role is open (asked 2026-11-19) | to confirm |
| `skypane_cassette.blend1` (in `hardware/cad/`) | a Blender automatic backup copy, not a design source | not applicable | not applicable | not applicable |

The owner reported on 2026-11-19 that the exported STL match the final blend ("oui"). He gave no export date and did not say what `skypane_lid.3mf` is: the export date and the 3mf role stay open.

The files were checked in Python for size, bounding box and watertightness (every edge is shared by exactly two triangles); 2 triangles in the lid and 12 in the tray have a
near-zero area (under 1e-6 mm2), which slicers ignore. The owner sliced all four on 2026-11-19 (see Slice check) and nothing has been printed.

## Go condition for the print rounds

Round A starts when a calliper is in hand: this is blocking for the frame survey, and the owner has not yet said whether he has one, borrows or buys (explained to him on 2026-11-19). The answer on whether the exported STL match the final blend is recorded (owner, 2026-11-19: they match; the export date is still open). Each later round starts only when the previous round's clearance results are reported; the gates are in [ENCLOSURE-TEST-PRINT-LOG.md](ENCLOSURE-TEST-PRINT-LOG.md).
