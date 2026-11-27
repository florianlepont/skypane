# Enclosure: print order

Decisions, design changes, checks and the spec sent to the print provider for
the rear enclosure of the 7.3 inch frame. The design record is
[ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md); the measurements are in
[ENCLOSURE-MEASUREMENTS.md](ENCLOSURE-MEASUREMENTS.md).

Rules: every number copied from the design record is a design value, not
measured, until the owner reports otherwise. Nothing here says a part was
exported, sliced or printed until the owner reports it.

Centring reference (owner decision, 2026-11-18): everything is centred on the
opening of the mat (140.93 mm wide and 90.27 mm high per the owner's reading of 2026-11-23, confirmed by the owner on 2026-11-23 as the mat window, tool not stated; first read as 140 x 99 mm), not on the active area of the screen.

## Decisions

| Subject | Proposed value | Status | Date |
|---|---|---|---|
| Printer or means | The parts were sliced for a Bambu Lab P2S profile (owner's slice of 2026-11-19). The owner reported on 2026-11-23 that the print is made on a Bambu Lab X1 Carbon (workplace printer). The purchase of another printer (the X2D Combo, 749 EUR noted, offer until 2026-12-01 to recheck) is not decided and is the owner's. | reported by the owner | 2026-11-23 |
| Provider | The owner's workplace (own access, no print service) | decided by the owner | 2026-11-18 |
| Material | PLA (changed by the owner on 2026-11-23: the owner does not want PETG; previous decision PETG Basic from the slice of 2026-11-19). Brand, colour and spool not stated yet and recorded per round in the test-print log. All clearances found on this print hold for PLA only: PLA shrinks, creeps under constant load and softens with heat differently from PETG, so the fit and hook results are to be read as results for PLA | changed by the owner | 2026-11-23 |
| Nozzle | 0.4 mm, or another if needed | decided by the owner | 2026-11-18 |
| Filament | PLA, brand and colour not stated yet (owner's report of 2026-11-23); recorded per round in the test-print log; do not change brand between rounds | reported by the owner (brand open) | 2026-11-23 |
| Build plate | PEI plate, as reported by the owner on 2026-11-23 (smooth or textured not stated); keep the same plate every round | reported by the owner | 2026-11-23 |
| Lid fixing | M2 self-tapping screws, pilot holes 1.7 mm, through holes 2.4 mm (design values, not measured). Heat-set inserts would need a redesign of the bosses (standoffs are 4.0 mm across, lid corner wall about 3.2 mm), so they are not a drop-in swap; decided only after the screw reuse test (5 removal and insertion cycles per lid screw, a design value the owner may adjust). Lengths from the model, assuming a pan head: lid corners M2 x 6 to x 8 (pilot 7 mm deep under a 1.5 mm lid); board standoffs M2 x 4 at most (a 6 mm screw would pierce the 0.8 mm pilot floor). Screw head type: open, asked on 2026-11-19 | decided by the owner; lengths computed by the assistant | 2026-11-19 |
| Magnets | 6 x 2 mm, pocket 6.2 x 2.2 mm (design value, not measured). Arrival: the magnets arrived (reported by the owner on 2026-11-20); the M2 screws also arrived (reported by the owner on 2026-11-20; head type and lengths not reported yet); the JST extensions are still awaited. Real size by calliper, pocket ladder and polarity marking: open, to be filled by the owner | open | 2026-11-19 |
| Printer purchase | Not decided; the owner's call. Offer noted until 2026-12-01 to recheck; the first fit result arrives after that date. The X2D Combo (749 EUR noted) is not bought | not decided | 2026-11-19 |
| Measuring tool | Calliper: none used so far (all readings so far are tape measure). The owner reported on 2026-11-19 that he did not know what a calliper is; it was explained to him on 2026-11-19 (a pied a coulisse, about 0.02 mm reading, 10 to 20 EUR or easy to borrow). On 2026-11-19 he reported that he has no calliper; whether he buys or borrows one is not decided (asked on 2026-11-19). Round A is blocked until a calliper is in hand | open: no calliper (reported by the owner on 2026-11-19); to buy or borrow, not decided | 2026-11-19 |
| Lid opening | No tool-free latch; a PH0 or PH00 screwdriver opens the lid. A recommendation the owner may overrule | proposed | 2026-11-19 |
| Slicer | Bambu Studio (2.9.1.70, used 2026-11-19) | decided by the owner | 2026-11-18 |

### Superseded and out-of-scope notes

(a) The mat opening of about 158 x 94 mm to cut, written in the first measurement plan and the first decision record, is superseded by the owner's decision to keep the mat's existing opening (140 x 99 mm as first read, tape measure). The height is 90.27 mm according to the owner's reading of 2026-11-23 (the 99 was a typing error, reported on 2026-11-19); confirmed by the owner on 2026-11-23 as the mat window, tool not stated. (b) The pack enclosed in this design is the single Kubii 3000 mAh unit (8 x 50 x 60 mm). The frame in production uses the 10000 mAh Soldered pack (11 x 60 x 100 mm per the battery records), which does not fit this pocket, and a replacement of the Kubii pack may differ in size (the vendor listing showed out of stock on 2026-11-01).

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

### Owner decisions of 2026-11-23 after the first fit of the printed tray (PLA)

Decided by the owner after trying the first print; the Blender file is not
changed yet (the owner changes it in his own session). The values below are
design values, not measured. The tray is reprinted once with all of them. On the same day the owner asked the assistant to make the change in the Blender file; the assistant did it by editing the generating script stored in the blend and regenerating the parts (see "What was changed in the Blender file" below).

| Part | Dimension | Old design value (design value, not measured) | New value (decided by the owner) | Reason (reported by the owner) | CAD status |
|---|---|---|---|---|---|
| Tray | Screen ribbon slot | 4 x 28 mm | 34 mm on the long side and 8 mm on the other | The ribbon is pinched in both directions of the slot; the owner moved from the first suggestion of 32 mm to 34 mm and accepted 8 mm | done in the script by the assistant on 2026-11-23, to be opened and reviewed by the owner |
| Tray | Battery pocket length | 60 mm cell in the pocket, 0.5 mm clearance (design value) | 2 mm more in length, by moving the lower wall of the pocket | The cell fits only just in length, a very slight gap is missing | done in the script by the assistant on 2026-11-23, to be opened and reviewed by the owner |
| Shim and tray | One part or two | two parts: a 1.0 mm shim and the tray | stays two parts; the owner will glue the shim to the tray (changed by the owner later on 2026-11-23: first decided as one single part "for the assembly", then dropped after the assistant pointed at the printing risk) | The one-part idea would put a rim around the screen on the screen-side face, which may need supports; the owner chose to keep two parts and glue them | no CAD change needed |

#### What was changed in the Blender file

Made by the assistant on 2026-11-23 at the owner's request, in the generating
script stored in `hardware/cad/source/skypane_cassette.blend` (text block
`skypane_cassette.py`), then the parts were regenerated and the tray exported
again (`hardware/cad/print/skypane_tray.stl`). The assistant used Blender as a
Python module (version 5.3), not the owner's Blender session. The lid, the shim
and the stand plate were regenerated too and came out identical (same triangle
counts and volumes as the previous export), and the reproduction of the
previous tray before the change matched the previous STL exactly (7298
triangles, same volume), which is how the method was checked.

- Ribbon slot: the box that cuts the slot in the tray floor now spans x 51.2 to
  59.2 mm and y -17 to +17 mm (8 x 34 mm), around the same centre as before
  (x 55.2, y 0). The two engraved lines of the board outline east side now stop
  at y +-18 mm (they stopped at +-15 mm) so they do not run into the larger slot.
- Battery pocket: a new parameter `bat_extra` of 2.0 mm moves the lower
  partition and the lower end of the right wall of the pocket 2 mm away from the
  cell. The engraved cell outline and the label stay where they were.
- Not changed: the shim and its ribbon passage (29 x 1.7 mm), the lid, the stand
  plate, the standoffs, the antenna block.

Checks done on the regenerated tray, by computation on the model (not a slicer
and not a print): the mesh is closed (every edge shared by two triangles, 7292
triangles); the volume dropped by about 172 mm3, which is the removed slot
material (about 192 mm3) less the added wall and engraving material, as
expected; probes inside the mesh show the floor open over x 51.2 to 59.2 and
y +-17 and solid just outside, and the partition solid at y about -44.7 and
open at the old position y about -42.8. The nearest standoff is about 3.6 mm
from a corner of the new slot, so no wall under 0.8 mm appears around the slot.

Done on 2026-11-24: the owner looked at the tray in Blender and the tray was
sliced (see "Slice check, 2026-11-24" below). Still to do: the tray is reprinted
in PLA on the same machine and plate; the fit of the ribbon, of the battery and
of the board is tried again; then the lid is printed.

#### Tray and shim in one part (the main design since 2026-11-24)

Asked for by the owner on 2026-11-24 as an alternative version. The main design
stays two parts that the owner glues; this variant is only a file to look at and
slice. Files (moved on 2026-11-24, see the paragraph on the layout below): `hardware/cad/source/skypane_cassette.blend` (the blend with a
union of the tray and the shim, the separate objects kept and hidden) and
`hardware/cad/print/skypane_tray_shim_merged.stl` (one part, 132.0 x 182.0 x
12.0 mm: 1.0 mm rim in front of the 11.0 mm tray). Made by the assistant in the
generating script, like the tray change above.

- The ribbon passage of the former shim has the same footprint as the new slot of
  the tray (8 x 34 mm), so nothing covers the slot mouth.
- The mesh is closed (7408 triangles); the volume is the tray plus the shim minus
  the larger ribbon passage, as expected.
- Printing, by computation on the model and not by a slicer: in the pose with the
  rim on the plate, the ceiling of the screen pocket (112 x 171 mm, about 19 000
  mm2, at 1.0 mm above the plate) faces downward over a span far too long to
  bridge, so supports are needed across the whole pocket (five layers of 0.2 mm).
  The separate tray has no downward-facing surface at all. The supports touch the
  face that lies against the back of the screen and are removed through the open
  front of the pocket; the finish of that face and the effort to remove them are
  not known. The opposite pose (floor up) would need supports under the whole floor,
  which is worse.
- Sliced once on 2026-11-24 (see "Slice check, 2026-11-24" below): the slicer
  does add support under the pocket ceiling.
- Owner report of 2026-11-24, first version: the variant was printed once and
  the owner could not get a clean print; he first thought the support was too
  thin and said the work would continue with the main design.
- Owner report of 2026-11-24, correction: he has the same print problem with the
  main part (the tray), so he thinks the cause may be the printer and not the
  design. The cause is not determined and the defect is not yet described or
  photographed. The earlier line that the design was abandoned is withdrawn: the
  variant is only set aside, not decided either way. The files stay in
  `hardware/cad/alternatives/` at that time; no fit trial of this variant.
- Owner report of 2026-11-24, reprint: before the reprint the owner purged the
  nozzle and changed nothing else he mentioned (no change to the file or the
  settings reported); the print started without a problem and, in his words, the
  piece is "top". No photo of the supported face was sent, and how easily the
  supports came off and the finish of that face are not reported. The cause of
  the earlier failed prints is not determined: the purge is the only change
  reported, and one good print does not prove it was the nozzle. No fit trial of
  this variant yet.
- Owner report of 2026-11-24, after the reprint: the supports came off "super
  facilement" (the owner's words); no photo or measurement. Owner decision of
  2026-11-24: the design goes to one part, tray and shim together. This replaces
  the earlier lines of this section that said the variant was set aside or not
  decided. The layout change that followed is described below. The one-part design has not been fitted
  in the frame, the lid has not been tried on it, and no go/no-go is recorded.
- Photos sent by the owner on 2026-11-24 (two photos, not stored in the repo),
  read by the assistant by eye, nothing measured: the face that lies against the
  screen is flat and even with fine parallel lines, with no visible hole, string
  or torn area, and the ribbon slot is clear; inside, the engraved texts
  BATTERIE, CARTE and ANTENNE are readable, and the four board standoffs, the
  walls, the corner screw posts and the shim pegs are present, with no visible
  string or lifted corner. Photos cannot show dimensions: fit is still to be tried.
- Layout change, 2026-11-24, made by the assistant at the owner's request ("le
  modele alternatif doit devenir le principal", folder `old` chosen by the
  owner): `source/skypane_cassette.blend` is now the blend with the union; the
  previous blend is `old/skypane_cassette_separate.blend`; the separate tray and
  shim STL moved to `old/`; the merged STL and its 3mf moved to `print/`. No
  geometry changed (the files were moved, not re-exported). The old files stay
  until the one-part design has been fitted in the frame. The file table and the
  slice rows below name the separate tray and shim as they were at the time.

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
| Material | PLA (changed by the owner on 2026-11-23; previously PETG Basic); colour recorded per round |
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

### Slice check, 2026-11-24 (reprinted tray and merged variant)

Nothing has been printed in this round. Two checks, both on the model:

**Blender (owner looking, 2026-11-24).** The assistant opened
`hardware/cad/source/skypane_cassette.blend` (saved with Blender 5.3.0) in the
owner's Blender, showed the tray `SkyPane_Bac` seen from the back and read the
model. The owner looked at the screen and reported ("oui, tout est bon") that
the ribbon slot looks wider and longer, the battery pocket looks longer, and
nothing looks wrong around the slot. What the assistant read on the model (model
values, design values, not measured): the floor is open over x 51.2 to 59.2 mm
and y -17 to +17 mm (8 x 34 mm); the lower partition sits at y -45.35 to -44.15
mm; the nearest standoff edge is about 3.6 mm from the slot corner; the antenna
block (y from 63.4 mm) and the stand magnet bosses on the lid (x 26 to 36 mm) are
far from the slot; the floor is 1.2 mm thick and the partition 1.2 mm, so no wall
under 0.8 mm is added by the change. The four parts are closed meshes (0 open
edges) and their volumes equal those of the exported STL files (tray 52246 mm3,
lid 42494, stand 8010.5, shim 4767); the lid, stand and shim STL files have not
changed since the first export (git history). The lid has 8408 triangles in
Blender and 8406 in the STL; the difference is not explained (the volumes agree to 0.1 mm3, so it is
not a design change; probably the near-zero-area triangles the export drops).

**Slicer (assistant, command line).** Sliced by the assistant on 2026-11-24 with
Bambu Studio 2.9.1.70 run from the command line on the owner's Mac, not in the
window: the owner did not see these slices on screen, and the values below are
read from the G-code header and the result file the slicer wrote. Profile:
Bambu Lab X1 Carbon, 0.4 mm nozzle, "0.20mm Standard @BBL X1C", filament
"Bambu PLA Basic @BBL X1C" (PLA, density 1.26 g/cm3 in the profile), no
plate-specific setting chosen (the profile says Cool Plate; the owner's plate is
not stated). Layer height 0.20 mm. The system profile has 2 walls and 15 % grid
infill; the main rows use 3 walls and 20 % grid infill, as in the first slice of
2026-11-19, so the rows can be compared. The slicer reported no error or warning
in its result file (the command line does not show the on-screen alerts of the
window).

| Part | File | Walls | Infill | Supports | Estimated mass (g) | Estimated print time |
|---|---|---|---|---|---|---|
| Tray, reprint | `skypane_tray.stl` | 3 | 20 % grid | off | 58.42 | 1 h 19 min 56 s |
| Tray, reprint | `skypane_tray.stl` | 3 | 20 % grid | auto (normal) | 58.42 | 1 h 19 min 56 s (no support generated) |
| Tray, reprint | `skypane_tray.stl` | 2 (system profile) | 15 % grid | off | 56.58 | 1 h 15 min 2 s |
| Tray and shim in one part | `skypane_tray_shim_merged.stl` | 3 | 20 % grid | off | 62.89 | 1 h 38 min 43 s |
| Tray and shim in one part | `skypane_tray_shim_merged.stl` | 3 | 20 % grid | auto (normal) | 73.21 | 2 h 8 min 5 s |

Reading of the rows:

- Tray: no overhang needing support. With automatic supports switched on, the
  slicer wrote no support at all and the mass and time are the same as without.
  The slicer still prints bridge lines (61 s in total, as in the first slice of
  the tray), which is normal for the layers over the infill. Against the first
  slice (56.29 g, 1 h 32 min, P2S, PETG, 0.20 mm): the mass is 2.1 g higher with
  the same walls and infill (the longer slot removes material, the PLA density
  and the profile differ, so no comparison of cause is made) and the estimated
  time is shorter on the X1 Carbon.
- Merged variant: with supports the mass grows by 10.32 g (62.89 to 73.21 g) and
  the time by 29 min 22 s. The slicer put the supports in layers 0.2 to 0.8 mm
  (four layers) in the pose of the file, which is the rim on the plate; the
  supported face is the ceiling of the screen pocket, the face that lies against
  the back of the screen, as expected from the computation above. The finish of
  that face after removal is not known. The merged part costs 14.8 g and about
  48 min more than the tray alone, plus the shim to print apart (stand and shim
  were 11.70 g and 29 min together in the first slice).
- The thinnest wall and slot are not read from the slicer; they stay the model
  values of 2026-11-18 above (no wall under 0.8 mm outside the engraved letters).
- Masses and times are estimates of the slicer (design values), not weighed and
  not measured on a print.

**Slicer projects saved by the owner (2026-11-24).** The owner saved two Bambu
Studio projects and the assistant read them (unzipped, not opened in the
slicer; nothing was sliced from them): `hardware/cad/print/skypane_printing.3mf`
and `hardware/cad/print/skypane_tray_shim_merged.3mf` (then in `alternatives/`). Contents:

| Project | Plates | Parts and check against the repo STL |
|---|---|---|
| `skypane_printing.3mf` | 3: shim and stand; lid; tray | The four meshes have the same triangle counts and volumes as the STL in `print/` (tray 7292 triangles, 52246 mm3: the version with the 8 x 34 mm slot; lid 8406; stand 396; shim 208) |
| `skypane_tray_shim_merged.3mf` | 1: the merged part | Same mesh as `print/skypane_tray_shim_merged.stl` (7408 triangles, 56954 mm3) |

Settings stored in both: Bambu Lab X1 Carbon, 0.4 mm nozzle, "0.20mm Standard @BBL
X1C", 3 walls, 20 % grid infill, Textured PEI Plate, filament "Bambu PLA Matte
@BBL X1C" (density 1.32 g/cm3 in the profile), auto brim. Supports: off in the
printing project, automatic (normal) in the merged project. No per-part override
was found. So the owner's plate is a textured PEI plate and the spool is PLA
Matte, as stored in the projects (the slice figures above used PLA Basic, 1.26
g/cm3, so masses differ a little). The projects hold no slice result.

### First assembly and the screw lugs removed, 2026-11-24

Reported by the owner on 2026-11-24, after mounting the lid on the rest of the
case, which completes the first assembly (nothing measured):

- The screws that fix the case to the frame are useless: the tabs on the tab
  pads hold the case on the frame. Screwing to the frame is not practical for
  the assembly. The owner asked to remove the four screw lugs of the lid.
- The stand does not work: the frame slides directly. Which surface it stands
  on, the angle, and whether it slides on the stand or the stand slides are not
  reported yet. No change was made to the stand.

Change made by the assistant in the generating script on 2026-11-24 (Blender
5.3.0, background mode): the four lugs of the lid (4 x 8 mm, z 12.5 to 22 mm,
with their 2.2 mm hole and head recess) and their parameters are removed. The
tab pads, hooks, stand stops and every other part are unchanged. Check: the
one-part tray and the stand regenerate with the same volume (56954.0 and 8010.5
mm3, the stand STL byte-identical); the lid volume goes from 42583.8 to 41487.5
mm3 (-1096.3 mm3), 8408 to 7552 triangles, and keeps its size (132.0 x 182.0 x
11.2 mm). Only `print/skypane_lid.stl` was re-exported. The lid must be
reprinted, and `skypane_printing.3mf` and any other project still hold the lid
with lugs. Design value, not measured, not printed.

The 4 M2 screws of the lid on the tray corners (the corner posts) are not part
of this change.

Owner report of 2026-11-24 (evening): the owner saved the Blender file after
deleting the two duplicate copies of the one-part tray that the assistant's
regeneration had left in it (`SkyPane_Bac_Cale.001` and `.002`; the old separate
tray and shim objects are visible again in the file). The meshes are unchanged
(checked by the assistant on 2026-11-24: same vertex hashes, the stand still at
its 20 degree design, same script). The owner also recreated the Bambu Studio
project as `print/skypane_lid.3mf` (renamed `print/skypane_print_project.3mf` on 2026-11-25), holding the lid with no lugs (7552
triangles), the one-part tray and shim (7408) and the stand (396), and removed
the two earlier projects `skypane_printing.3mf` and
`skypane_tray_shim_merged.3mf`. Read by the assistant from the files (triangle
counts), not sliced or printed.

### Print project renamed and read, 2026-11-25

At the owner's request the Bambu Studio project `print/skypane_lid.3mf` is now
`print/skypane_print_project.3mf` (the old name came from the first project, which held only the
lid). The owner had recreated it with the three current STL; read by the assistant from the file
(not sliced, not printed): three objects with 8010 triangles (lid), 524 (stand) and 6644 (tray and
shim), the same counts as the three STL, on two plates. Settings in the file: printer Bambu Lab X1
Carbon, layer height 0.2 mm, Textured PEI plate, automatic brim, no raft, and **supports switched off**
(`enable_support` = 0, type "normal(auto)", threshold 30 degrees, no per-object override). The
one-part tray has a pocket ceiling facing down over about 19 000 mm2 (see above): with supports
off, that ceiling is not supported unless the slicer bridges it; the owner's earlier print of the
one-part tray used supports on automatic (reported on 2026-11-24). To be confirmed by the owner
before printing.

### State of the files after the full check, 2026-11-24 (evening)

Checked by the assistant on 2026-11-24, on the model and the STL files, not on a print:

| File in `hardware/cad/print/` | Triangles | Volume | Size (mm) | Checks |
|---|---|---|---|---|
| `skypane_tray_shim_merged.stl` | 6644 | 55855.2 mm3 | 132.0 x 182.0 x 12.0 | closed, no degenerate triangle |
| `skypane_lid.stl` | 8010 | 39981.2 mm3 | 132.0 x 182.0 x 11.2 | closed, no degenerate triangle |
| `skypane_stand.stl` | 524 | 15789.0 mm3 | 119.0 x 152.4 x 4.0 | closed, one piece, no degenerate triangle |

- The three STL are byte for byte what the script stored in `source/skypane_cassette.blend` produces when it is run again.
- Interference of the leg, folded and open at 48 degrees, with the tray and shim, the wooden frame, its glass, mat and tabs, the board, the battery, the antenna, the screen and its ribbon: none. With the lid: 0.56 mm3 folded and 0.57 mm3 open, the intended crush ribs on the pins.
- The lowest point of the open leg is at 12.50 mm, the lid back face at 12.50 mm; it rests on the desk along a flat edge in portrait (tilt 26 degrees) and in landscape (tilt 27 degrees).
- Found and corrected during this check: the saved blend file in the working folder contained the owner's demonstration scene (copies of the parts standing on a desk); it was restored to the committed version. The Bambu Studio project `print/skypane_lid.3mf` still holds the earlier meshes of the three parts (lid with 7552 triangles, tray and shim 7408, stand 396): the three STL above must be imported again before slicing.
- Not checked, because nothing is printed: the fit of the pins in the lugs, the grip of the crush ribs, the strength of the stop, the stiffness of the 4 mm ring in PLA, the friction of the foot, the fit of the lid on the frame and the letters on a real print. The stability margins use an estimated centre of gravity.

### Stand redesigned as one leg on a diagonal hinge, 2026-11-24

Owner request of 2026-11-24, after the loose plate and then the two-socket leg did
not satisfy: one stand that works in landscape and in portrait without moving it or
taking anything apart, like the original IKEA easel leg; the magnet bosses and the
two U-shaped stop walls of the lid can go, the folded leg may cover the USB access,
and the hinge may start where the logo is. Nothing measured; every number is a
design value.

Research (web search, 2026-11-24, not a proof of any mechanism): the patents
[US 6163998](https://patents.google.com/patent/US6163998) and
[US 10376078](https://patents.google.com/patent/US10376078) describe one leg whose
foot has two edges, each resting on the table in one orientation, so the same leg
serves both; the IKEA frame model in the Blender file has the same shape (a leg
with a diagonal hinge edge and a foot corner near the lower corner of the back).
The assistant checked on the model that such a leg stands the frame in both
orientations.

- Hinge: one axis along a diagonal of the lid back, from (-51, 31) at 45 degrees,
  38 mm long, near the logo, with a lug at each end (5 x 7 mm, 6 mm high, hole 3.4 mm
  with three small crush ribs, snap-in throat 2.7 mm open upward). The old two pairs
  of sockets, the stop walls, the support columns under them in the tray and the
  magnet bosses are removed.
- Leg (`print/skypane_stand.stl`): owner request of 2026-11-24 for the prettiest shape
  with very strong stability and the least material (the USB cut-out of the previous
  version is dropped at the owner's request). A light frame ring, 10 mm wide and 4 mm
  thick, around a leaf-shaped outline with rounded corners: the hinge edge on the
  diagonal near the logo, a rounded shoulder clear of the hook block, a long edge down
  to a bottom foot edge (50 mm) and a right foot edge (50 mm) that meet at a lower right
  corner, and a chamfer back to the hinge. About 3700 mm2 of material, a volume of
  15789.0 mm3 (about 20 g in PLA at 1.3 g/cm3), against 27044.8 mm3 for the previous
  panel; 524 triangles, closed mesh in one piece, 119.0 x 152.4 x 4.0 mm. A 4 mm ear and a 3 mm pin at
  each end of the axis. The stop is a triangular wedge behind the axis of each ear (owner request: the first
  stop was a tab of 1.6 mm): its inclined face, 5.4 mm long and 6 mm wide, lies flat on the
  lid back when the leg is open at 48 degrees (8 vertices of the open leg on the lid
  face on the model), the wedge stays within the 4 mm thickness of the leg and does not
  protrude when the leg is folded. The resultant of the contact is about 3.4 mm from
  the axis instead of 1.6 mm, so a forced push loads the lid about 2.2 times less, over
  about 32 mm2 per ear instead of an edge (computed, not tested; the lid plate is still
  only 1.5 mm).
- How the shape was found, by computation on the model: the frame tilt is chosen in
  each orientation (26 degrees in portrait and 27 in landscape) and the line where the desk plane meets the
  open leg is then a foot edge of the leg, in a different place for portrait (about
  horizontal in the folded plan) and landscape (about vertical), each cut flat by its
  desk plane. With the centre of gravity of the frame and case estimated at (-3.5, 3,
  17) mm (design estimate from the earlier design notes, not weighed), the margin of the
  centre of gravity inside the support polygon (lower edge of the frame plus the foot
  edge) is about 39 mm in portrait and 30 mm in landscape at 48 degrees (45 and 33 mm at the first opening of 54 degrees, with a tilt of 29.5 degrees), and it hardly changes
  with the length of the foot edge (40 to 100 mm gave the same margins), which is why
  the leg needs no large panel: the stability comes from the position of the foot,
  not from its size. The ring carries the load along its sides.
- Fault found on 2026-11-24 from the owner's screen recording and corrected: the two
  hinge ears had been built on the wrong side of the axis (8 mm away from the leg
  instead of toward it), so that, once the leg was opened, they swung through the lid and
  came out 4 mm on the screen side, and they were not joined to the leg. The ears are now
  on the leg side, with only the 1.6 mm stop overhang behind the axis; checked on the
  model: the lowest point of the open leg is at 12.49 mm, the lid back face being at
  12.50 mm, and the leg mesh is one piece.
- Owner remark of 2026-11-24 (a small step of 0.3 mm under the stop wedge, left by the 0.3 mm overlap used to join the wedge to the ear): the ear and the wedge are now one profile, so the underside of the ear runs straight into the inclined face (no step). The wedge cannot start at the axis, because its inclined face would then go below the underside of the leg and into the lid when the leg is folded; it starts at 1.56 mm.
- Visual defect reported by the owner on 2026-11-24 and corrected: the hinge ears were 0.01 mm thicker than the leg (a step of 0.01 mm, shown as a jagged line on the faces) and a small triangular hole was left in the top face next to the ear. The ears now have exactly the thickness of the leg, the coplanar faces are merged and the hole is closed; checked on the model: no vertex at 12.99 or 17.01 mm any more and no open edge.
- Owner decision of 2026-11-24: the opening is 48 degrees instead of 54, to lean the frame less (the owner asked for a stop at 15 to 20 degrees, which a leg folded on the lid cannot give: the foot would have to touch the desk 10 to 15 mm beyond the lower edge of the lid; the computed minimum is about 23 degrees at an opening of 30, with a closing torque that grows as the tilt falls). Open at 48 degrees, the frame tilts 26 degrees in portrait and 27 in landscape by choice; the
  foot edges are cut flat by the two desk planes and the lowest points of the open leg
  are at height 0 of each desk plane on the model.
- Folded, the leg lies on the lid back 0.5 mm above it; the only overlap with the lid
  is the 0.56 mm3 of the crush ribs on the pins (intended, to add friction).
- Checked by the assistant (Blender 5.3.0, background): lid, tray/shim and leg meshes
  closed; lid 8010 triangles, volume 39981.2 mm3 (with the logo moved and the letters); leg volume 15789.0 mm3; tray/shim
  part unchanged since the columns were removed (6644 triangles, 55855.2 mm3).
- Open risk, by computation: the load on the foot tends to close the leg with a torque
  of about 22 N.mm per newton of load at a foot friction of 0.4 (about 45 N.mm for 2 N; it was about 15 at an opening of 54 degrees)
  and tends to open it against the stop at a friction of 0.2; the narrow leg of the
  first version closed with about 27 N.mm per newton. Only the friction of the pins on
  the crush ribs holds it; this is the first thing to test. If it closes under the
  frame, the owner has 6 x 2 mm magnets: a pair in the ear and in the lid would hold it,
  but that was not designed.
- Not done: nothing printed or fitted; whether the pins snap in and stay, the
  stiffness of 4 mm PLA, the friction of the foot on the laminate (the owner has
  anti-slip pads), the hanging with the leg folded. The lid, the tray and the leg
  must be reprinted.

### Hinge lugs reinforced after both snapped at assembly, 2026-11-27

Reported by the owner on 2026-11-27 with a photo: at assembly both hinge lugs of the
printed PLA lid broke off cleanly, and the two small fragments lay loose on the
lid plate. The lugs were thin vertical walls (5 x 7 mm, 6 mm high) standing on a
plate of only 1.5 mm, with the hole 0.8 mm above the plate, and the print layers lie
across their height, so a sideways load tries to split the layers apart at the base.
What the owner was doing at the moment of the break, and which load did it, is not
stated; the first assembly of 2026-11-26 had snapped the pins in without breakage.
The owner asked for both fixes together: thicker lugs with fillets or triangular ribs
at the base, and a socle under them that spreads the load over the 1.5 mm plate.
Nothing is measured; every number below is a design value.

- Kept as they were: the 3.4 mm pin hole with its three crush ribs, the 2.7 mm snap-in
  throat open upward, the 6 mm height of the lug, the axis (from (-51, 31) at 45 degrees,
  38 mm long, hole centre 2.5 mm above the lid back). The leg (`print/skypane_stand.stl`)
  is not changed: its volume (15789.0 mm3) and 524 triangles are the same as before.
- Thicker lug: 6 mm along the axis instead of 5, grown outward only, so the inner face
  stays 0.4 mm from the leg ear and the leg swing is unchanged (pin engagement 4.2 mm of
  the 6 mm). It could not grow more: the lug at the start of the axis has the hook rail
  block about 2 mm from its corner, and the lug at the far end about 1.5 mm from the
  portrait hook block.
- Socle under each lug: 1.5 mm high, 10 mm each side of the axis and 8 mm along it
  (6 mm of lug and 2 mm beyond the outer face), flush with the inner face of the lug,
  with 3 mm rounded corners. It is trimmed where something else is close: the socle of the
  first lug stops at y = 21.5 mm (1.5 mm from the hook rail block, which ends at y = 20) and
  at x = -64 mm (2 mm from the lid edge); the socle of the second lug stops at x = -13.5 mm
  (1.0 mm from the portrait hook block, which starts at x = -12.5). Nothing touches the logo,
  the engraved letters, the footprint grooves or the hooks (checked on a height map of the
  lid around both lugs).
- Base fillets: on both sides of each lug, a concave quarter circle of 3 mm radius blends
  the socle into the lug wall (it starts 6.5 mm off the axis and meets the wall at 4.5 mm
  high). The throat arms keep their original width (2.15 mm each side of the throat), so
  the force needed to snap a pin in is not raised more than the thicker lug alone does.
  The top edges of the lug have a 0.5 mm chamfer.
- No rib on the outer face: the load of the leg goes through the pins across the axis, which the socle and the side fillets carry; the leg ear only pushes on the inner face of the lug if the leg slides along the axis, and it has 0.4 mm of play. A first version had two ribs there; they were removed on the same day because they carried no real load and brought the socle closer to the hook blocks.
- Design values for the base, compared with the previous lug (same load direction,
  rectangular section; not measured, no material data used): section modulus across the
  axis at the top of the socle about 169 mm3 against 41 mm3 (4 times); at the foot of the
  throat arms the gain is only about 1.3 times, because the arms were deliberately left
  as they were. Contact area on the lid up to about 155 mm2 before trimming against 35 mm2.
- Checked on the model (Blender 5.3.0, local MCP session): the leg swept from folded to
  open (every 6 degrees up to 48) touches the lid only in the pin hole zone, as before
  (the crush ribs); no contact with the socle, fillets or ribs. Lid: 8712 triangles,
  volume 40306.8 mm3 (+325.6 mm3, about +0.4 g in PLA at 1.3 g/cm3), mesh closed with no
  open edge (also checked on the exported STL and on the mesh in the 3mf); bounding box
  unchanged (132 x 182 x 11.2 mm). Tray and shim part (6644 triangles, 55855.2 mm3) and leg
  unchanged.
- Printing (PLA, Bambu X1 Carbon, PEI plate), same pose as before: the lid lies face
  down and the lugs grow upward. The socle is 1.5 mm (about 7 layers of 0.2 mm), the
  fillets and the ribs are concave curves that face upward, so no support and
  no new overhang; the only bridge is the 3.4 mm pin hole, as before. No new wall thinner
  than 3 mm (the throat arms, 2.15 mm, are unchanged). The layers still lie across the
  height of the lug, which is why the base is widened instead of relying on the layer
  bond; four or more wall loops on the lugs are advisable (a slicer choice, not tested).
- Found while reading the geometry, not changed: the pins are forced through a 2.7 mm
  throat with a 3 mm pin, an interference of 0.3 mm that only the two thin throat arms
  absorb; by the beam formula (an estimate with PLA at about 3.5 GPa) that bends the arms
  well past what PLA usually survives, so the break may have come from forcing the pins
  in rather than from the later load. The owner asked to keep the 2.7 mm throat, so it
  stays; if the new lugs also break during snap-in, widen the throat to about 3.0 mm and
  rely on the crush ribs for the hold.
- To reprint: the lid only (`print/skypane_lid.stl`, or the updated project
  `print/skypane_print_project.3mf`). The tray and shim part and the leg are unchanged.
- Not checked, because nothing is printed: whether the new lugs survive the snap-in of
  the pins and use, the real strength of the layers at the base, the clearance of the
  trimmed socles against the hook blocks on a real print, the friction and the snap-in force
  with the thicker lug, and the fit of the pins.
- The 3mf was updated with the new lid mesh only; its stored preview images and slicing
  summary still show the earlier lid and must be refreshed by slicing again in Bambu Studio.

### Stand redesigned with a wide foot, 2026-11-24

Superseded the same day by the hinged leg described just above (owner request); kept as the record of the intermediate design, which was merged but is no longer in the files.

Reported by the owner on 2026-11-24: the stand does not hold, because its foot
slides backward on the laminate desk (both landscape and portrait), and the
plate also comes out of its housing on the lid. The owner asked for a new stand
design, without changing the lid, and has adhesive anti-slip pads of no defined
size. Nothing was measured; the numbers below are computed on the model.

- Cause, by computation on the model: the plate is about 20 degrees from
  vertical, so the frame pushes the foot backward with about 0.36 times its
  weight on the stand; the foot holds only if the friction coefficient is above
  about 0.36, which smooth PLA on laminate barely reaches (design reasoning, not
  a measurement). The end of the old plate that touches the desk is only about
  4 mm deep by 30 mm wide, too narrow for a round pad.
- Change, made by the assistant in the generating script (Blender 5.3.0,
  background): a foot rib of 14 mm along the desk plane, away from the frame,
  3 mm thick at the tip and rooted 8 mm along the plate, so that the contact
  with the desk is about 18 mm by 30 mm. The plate is now printed on its small
  face, the one with the two magnet pockets (the face that lies on the lid
  when stored), so the rib stands on the other face and does not touch the lid
  when the plate is stored; no overhang on the strut, the rib leans 20 degrees
  from vertical. The pockets are now open on the bed face (2.2 mm deep, 6.2 mm).
  The plate length, width, thickness, tilt (20 degrees) and the lid are
  unchanged.
- Check on the model: closed mesh (0 non-manifold edges), 408 triangles, volume
  10342.3 mm3, print size 75.8 x 30.0 x 18.2 mm; the tray and the lid keep the
  same vertex hashes. `print/skypane_stand.stl` re-exported; the owner's
  `skypane_lid.3mf` project still holds the old stand.
- Not done: printed, fitted, or tried on the desk; the housing on the lid is
  unchanged, so whether the plate still comes out of it is not known. The
  assistant did not pick a pad size: the pads stick under the flat foot face.

### Texts next to the buttons aligned on the left, 2026-11-24

At the owner's request, RESET, OFF, ON and the letters A, B and C start on one line at
x = 14 mm (the texts were centred on x = 24 mm), keeping their heights (y) and sizes. The
small down arrow between OFF and ON moved 4.5 mm to the left to stay next to the words.
The left edge is 2 mm from the access opening (its edge is at about x = 12 mm). Lid mesh
closed; `print/skypane_lid.stl` re-exported (8010 triangles); the lid must be reprinted.
Design values, not measured, not printed.

### Letters on the three other buttons, 2026-11-24

At the owner's request, so that they can be used later: the letters A, B and C are engraved
next to the RESET, OFF and ON texts, in front of the three other buttons of the board, 7 mm
high, 0.4 mm deep, at x = 24 mm and y = 4.7, 14.1 and 23.4 mm (the centres of the buttons
read in the board model, spacing 9.3 mm; RESET is at y = -4.6). Which letter goes with
which key (KEY0 on GPIO5, KEY1 on GPIO3, KEY2 on GPIO2 in the firmware notes) is not known:
the letters only name the positions, from the one nearest RESET upward. The letters are
engraved without the thickening of the other texts, because the B of the font breaks the
mesh with it (181 open edges on the model). `print/skypane_lid.stl` re-exported (8006
triangles); the lid must be reprinted. Design values, not measured, not printed.

### Logo moved to the top right, 2026-11-24

At the owner's request ("en haut à droite") the engraved emblem and the text SKYPANE on
the back of the lid moved from the top left, next to the hinge of the stand leg, to the
top right, seen from the back: emblem centre from (-43, 64) to (38, 62) mm, text from
(-43, 45) to (38, 43) mm. Nothing else changed (same size, same depth). The new place is
free of raised features, clear of the hook block, the wide part of the access opening
and the top tab pad by at least 2 mm on the model, and the folded leg does not cover it.
`print/skypane_lid.stl` re-exported (7142 triangles, closed mesh); the lid must be
reprinted. Design values, not measured, not printed.

### Lid tab pads moved, 2026-11-24

First trial of the lid on the frame (photos from the owner, lid not yet screwed):
the folded tabs of the left and right sides land beside their pad, just beyond
its end, and the top and bottom tabs land on their pad about 4 mm off its centre.
The frame holds anyway (reported by the owner). The owner asked the assistant to
change the model from its visual estimates of the photos (not measured, about
plus or minus 3 mm).

- Left pad (x- side) centre moved from y -3.5 to +9.5 mm (+13 mm); right pad
  (x+ side) centre from y -7.5 to +1.5 mm (+9 mm). Seen from the back with the
  logo at the top left, both pads move toward the top of the frame. Top and
  bottom pads, size (20 x 8 mm, top at 15.0 mm) and all other parts: unchanged.
- Made in the generating script (parameters `tab_c_left` and `tab_c_right`),
  regenerated and re-exported on 2026-11-24 with Blender 5.3.0 in the
  background. Check: the tray, stand and shim regenerate with the same volume
  (the stand and shim STL are byte-identical to the previous export); the lid
  volume grows by 90 mm3, exactly the right pad no longer cut short by the stand
  stop (4.5 mm x 8 mm x 2.5 mm); the lid keeps its size (132.0 x 182.0 x 11.2
  mm). No slicer run, no print of the new lid.
- The owner's Bambu Studio project `print/skypane_printing.3mf` still holds the
  previous lid mesh: the lid has to be re-imported in the project before the
  reprint. Design values, not measured.

## Files

Printable files are in `hardware/cad/print/`, one per part, exported by the
assistant from `hardware/cad/source/skypane_cassette.blend` on 2026-11-18 as binary STL
in millimetres, each part lying in its printing pose (lowest point at z = 0):

| File | Size of the part | Triangles | Exported (as reported) | Blend saved (as reported) |
|---|---|---|---|---|
| `skypane_tray.stl` | 132.0 x 182.0 x 11.0 mm | 7292 (re-exported on 2026-11-23 with the 8 x 34 mm ribbon slot and the 2 mm longer battery pocket; 7298 before) | 2026-11-18 per the previous record; export date to confirm (asked 2026-11-19) | to confirm |
| `skypane_lid.stl` | 132.0 x 182.0 x 11.2 mm | 8408 (re-exported on 2026-11-24 with the left and right tab pads moved; 8406 before) | as above | to confirm |
| `skypane_stand.stl` | 71.0 x 30.0 x 4.0 mm | 396 | as above | to confirm |
| `skypane_shim.stl` | 132.0 x 182.0 x 1.0 mm | 208 | as above | to confirm |
| `skypane_lid.3mf` | not read | not read | present in the export folder; its role is open (asked 2026-11-19) | to confirm |
| `skypane_cassette.blend1` | removed on 2026-11-24: a Blender automatic backup copy, not a design source (still in the git history) | not applicable | not applicable | not applicable |

The owner reported on 2026-11-19 that the exported STL match the final blend ("oui"). He gave no export date and did not say what `skypane_lid.3mf` is: the export date and the 3mf role stay open.

The files were checked in Python for size, bounding box and watertightness (every edge is shared by exactly two triangles); 2 triangles in the lid and 12 in the tray have a
near-zero area (under 1e-6 mm2), which slicers ignore. The owner sliced all four on 2026-11-19 (see Slice check) and nothing has been printed.

## Go condition for the print rounds

The shim (1.0 mm) may be printed and tried in the frames before a calliper is in hand (owner approved on 2026-11-20); the owner has no calliper (reported on 2026-11-19) and has not decided whether to buy or borrow one. Fit results from that first try are by feel and tape measure only, with the tool written next to each reading. The coupon plate, the clearance measurements and the tray round need a calliper. The answer on whether the exported STL match the final blend is recorded (owner, 2026-11-19: they match; the export date is still open). Each later round starts only when the previous round's clearance results are reported; the gates are in [ENCLOSURE-TEST-PRINT-LOG.md](ENCLOSURE-TEST-PRINT-LOG.md).
