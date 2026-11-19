# Rear enclosure: audit of the design (2026-11-18)

Audit of the rear enclosure for the 7.3 inch frame, done by the assistant at the owner's request after
the design session. It looks for what was missed, what may not be feasible, and what may not print.
The design record is [ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md); changes and checks are in
[ENCLOSURE-PRINT-ORDER.md](ENCLOSURE-PRINT-ORDER.md).

Findings are model- and report-based; status updates are recorded in the test-print log as the rounds proceed.

**Limits.** Everything here comes from the Blender model, from calculations and from the owner's readings.
Nothing was printed, sliced or fitted on the real frame. A figure marked "estimate" rests on an assumption
that is not measured. Severity: **High** = the design may fail or damage something; **Medium** = likely
to need a change after the first fit; **Low** = precaution; **Info** = checked and fine, or for the record.

## What was checked and found fine

| Check | Result |
|---|---|
| Closed meshes | Tray, lid, stand, shim: 0 open edges in Blender, and in the exported STL every edge is shared by exactly two triangles |
| Collisions | No collision between the printed parts, the electronics (board, battery, antenna, ribbon, screen) and the IKEA frame (fibreboard frame, polystyrene front sheet and inner frame, mat, tabs). Contacts are intended: lid on tray walls, board on its standoffs, antenna on its block |
| Depth | Highest point of the lid is 22.2 mm; the fibreboard edge (called wood in the model) is at 23.1 mm (IKEA model), so nothing sticks out |
| Overhangs, walls, slots | No support needed (longest bridge 4.5 mm); no wall under 0.8 mm outside the engraved letters and logo; narrowest slot 1.0 mm |
| Bed size | Largest part 132.0 x 182.0 mm; the Bambu Lab X1 bed is larger |
| Clearance, lid to electronics | Battery 1.75 mm, antenna 2.2 mm, board 0.41 mm (see F-08) |
| Hook strength (estimate) | The printed hook roof carries the whole load (3.2 to 4.0 N from the owner's masses, 328 to 403 g times 9.81, design values; an earlier figure of 5.8 N was noted without its derivation and is kept only as a conservative load for the hook test, the coupon test using about 1 kg) with a very large margin in shear and bearing; it is not the weak link (see F-02) |

## Findings

| Id | Severity | Finding | Evidence | Proposed action |
|---|---|---|---|---|
| F-01 | High | The plates barely fit the rebate. Nominal clearance is 0.2 mm per side. The model's smallest clearance is 0.07 mm at a tray corner and 0.14 mm at a lid corner (median 0.42 mm). The real rebate is known to about 1 mm (tape), and printing tolerance plus first-layer flare add about 0.2 mm | Blender clearance scan, owner's 133 x 183 reading | **Applied 2026-11-18** (owner choice): plates reduced to 132.0 x 182.0 mm, smallest clearance in the model now 0.37 mm (tray) and 0.44 mm (lid). Still to do at slicing: first-layer compensation or a small chamfer on the first layer edge; decided in the first print round: chamfer in CAD or the slicer's first-layer compensation |
| F-02 | Medium (High if the grip is not checked) | The frame itself (fibreboard frame, polystyrene front sheet, mat, 173 g) is held to the cassette only by the friction of four metal tabs on four pads. The hook hangs the cassette, not the frame. If the friction slips, the frame can drop with its glass. The original IKEA frame relies on the same mechanism with its cardboard back, where the tabs bite into the board; what is not known is the grip on smooth printed PETG pads. The tabs' spring force is not measured: with an assumed 2 N per tab and a friction coefficient of 0.3 the margin is only about 1.4; with 5 N it is 3.5 | Load path analysis; tab force unknown | Test at the first fit: with the cassette in the real frame, hold the cassette vertical, shake gently and pull on the frame. If it moves, raise the pads or add the screw lugs (a second lug on each top side, 6 in total: x- side at y = +-40 mm and y+ side at x = -30 and +32 mm, M2 self-tapping screws of about 10 mm into the fibreboard). Screw lugs bite into fibreboard, which holds less than solid wood (an assumption, tested on the frames in the print rounds), so the lugs are an anti-shift aid and not a load path. **Open: no change made; the owner decided on 2026-11-18 to wait for the test** |
| F-03 | Medium | In landscape the hook is only 47.5 mm above the centre of gravity, so a lateral offset of the centre of gravity tilts the frame by 1.2 degrees per mm. The offset is estimated at +0.6 to +5.2 mm, so 0.7 to 6.3 degrees. The portrait hook is 72 mm above, with an offset of 0 to 1.3 mm | Mass calculation with the owner's masses | **Applied 2026-11-18** (owner choice): rail centre moved to y = +3 mm, adjustment kept at +-12 mm; the owner then asked for a way to hold the setting, so the slot edge has 12 V notches (2 mm pitch) and the block has graduations every 2 mm. Still to do: weigh and balance the real assembly; the grip of the notches is not tested |
| F-04 | Medium | The tab pads give no known preload. The pads are at 15.0 mm, the tab underside at 15.0 to 15.4 mm in the model; the owner's reading has about 1 mm of uncertainty. If the real tab is 1 mm higher, nothing presses; if 1 mm lower, the tabs bend the lid | Owner's reading 7b | **Open.** Make the pad height a tested parameter: print the lid, check the contact, add a thin shim if loose; consider 15.6 mm for a small preload |
| F-05 | Medium | The battery cable cannot leave the pocket at the top-right corner: the cell is 0.5 mm from the wall there. The route that stays inside the box is about 105 mm for a 95 mm cable | Owner's photo, model | **Applied 2026-11-18 (owner approved): battery pocket moved 10 mm, corner exit about 10 mm free; the JST-PH extension is still needed (route about 105 to 110 mm, estimated).** First analysis: An exit corridor does not solve it: the wires leave the cell along the protection board, so they need about 8 mm free beyond the corner, and the pocket has 0.6 mm on the right and 1.8 mm on the left (with the 132.0 mm plate). A route that stays inside the box also goes round the USB-C well, about 105 mm. Real options: move the battery pocket into the free area under the partition (longer extension, bigger rework), or wait for the first fit with the real parts | 
| F-06 | Medium | The antenna route is 46 to 47 mm for the far corner against a 50 mm cable. The mated battery plug reaches y about 60 mm and the antenna block starts at y = 63.4 mm. Radio performance behind the lid is untested | Model, owner's cable length | Keep a U.FL extension as a fallback; test reception before closing the box |
| F-07 | Medium | Polarity of the battery extension. A reversed pack destroys the board (see the battery connector section of BOM.md). Some JST-PH extension cables are wired straight, some reversed | BOM.md | Check with a multimeter before the first connection |
| F-08 | Medium | Only 0.41 mm between the highest board component (the battery socket, 10.59 mm) and the lid underside (11.0 mm). The mated plug may be taller than the socket | Model of the board | Check with the real board; if tight, add a local recess under the lid |
| F-09 | Medium | The screen ribbon passes through a 4 x 28 mm slot and bends. Its bend radius at the slot edge is not known, and a flat flex cable creases easily | Design record | Dry-fit with the real ribbon before closing; widen the slot or round its edge if needed |
| F-10 | Medium | The stand's forward-tipping margin at 20 degrees is 7.5 degrees (landscape) and 10.5 degrees (portrait), assuming the mass centre at 6 mm depth and the fibreboard edge (called wood in the model) 74 mm from the lid origin (both unmeasured). With the mass centre at 3 mm, the margins are 5.4 and 8.9 degrees. One millimetre of plate length changes the tilt by about 1.4 degrees. The plate is loose, has no storage place, and its foot may slip | Calculation | Balance-test the real frame; add a rubber pad to the foot; decide on storage after the first fit |
| F-11 | Low | The M2 pilot holes are 1.7 mm. Printed PETG holes often come out 0.1 to 0.2 mm small. Checked on the model 2026-11-19: the four lid corners and four board standoffs have coaxial holes (corner pilot 1.7 mm, wall around it 3.2 mm or more; standoff pilot 1.6 to 1.8 mm, 1.15 mm of wall); screw length limits are in the print order | Common experience, not tested | Print the tray first, try a screw in a standoff, and ream if needed |
| F-12 | Low | Two large flat plates (132.0 x 182.0 mm) can warp or lift at the corners in PETG | Common experience | Brim, textured plate, glue stick, enclosure closed, first layer slow |
| F-13 | Low | The design source is a script inside a binary .blend (5.5 MB), so a change cannot be reviewed as text. The script has French names and comments, while the repository convention is English | Repository convention | Export a text copy of the script next to the .blend; rename objects and translate comments in a later pass |
| F-14 | Info | Wall screw requirement for the hook: head up to 9.5 mm diameter, shank 3.0 to 4.3 mm, head underside 2.1 mm or more from the wall. One screw is a single hanging point | Model | Put it in the hanging instructions |
| F-15 | Info | The hanging, stand and clearance figures all depend on the IKEA 3D model of the frame (fibreboard edge, called wood in the model, at 74 mm, outer size 148 x 198 mm, rebate profile). None of it is measured on the real frame | Model | Measure the outer size and the rebate at the four corners with a caliper if one becomes available |
| F-16 | Medium | The shim was 0.8 mm thick while the screen is 0.92 mm in the model, so the mat (back at 1.1 mm) would rest on the screen glass, not on the shim | Model; owner readings 2 and 6 (tape measure, about 0.1 to 0.2 mm uncertain) | **Applied** (owner approved, 2026-11-18): shim 1.0 mm. Confirm at the first fit with a strip of paper between mat and shim |

## Values the design rests on and that nobody has measured

- Fibreboard edge (called wood in the model) at 74 mm from the lid origin, outer size 148 x 198 mm, rebate wall profile and corners.
- Mass centre depth of the assembly (6 mm, an estimate) and the real position of the battery and board in the box.
- Spring force of the frame tabs and the friction between them and the pads.
- Height of the mated battery plug and shape of the ribbon bend.
- Mass of the printed parts (solid volume at 1.27 g/cm3 used as an upper bound).

## Suggested order for the first fit

1. Measure the frame: rebate at the four corners and outer size (calipers if possible), the tabs once more.
2. Print the shim and the tray; try the tray in the rebate and with the real board and battery on the table.
3. Print the lid; check the tab pads, the screw lugs and the two hooks on the real frame.
4. Check the cables: battery extension polarity, antenna reach, ribbon bend.
5. Balance the assembly and test the stand plate; adjust the plate length from the real tilt.
6. Only then hang it, with the top lugs screwed.
