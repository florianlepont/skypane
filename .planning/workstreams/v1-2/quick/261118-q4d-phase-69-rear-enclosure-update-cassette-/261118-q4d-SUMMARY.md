---
quick_id: 261118-q4d
status: complete
date: 2026-11-18
---

# Summary

Rear enclosure, 7.3 inch frame: the Blender design was reworked with the owner in a local session,
checked on the model, and exported. Nothing was sliced or printed.

## Done

- Design reworked in `hardware/cad/skypane_cassette.blend` (script `skypane_cassette.py` inside it), scene grouped
  into three collections: IKEA frame, SkyPane electronics, SkyPane mechanics.
- Owner readings and decisions applied: frame tabs (height 15 mm, width 4 mm, positions along the sides), mat of the
  reference model, antenna moved above the board (owner's cable is 50 mm), tray interior reorganised and labelled,
  four screw lugs and four wide tab pads on the lid, signature engraved on the lid, frame tilt 20 degrees.
- Stand: after several designs (hinged, clipped, sunken) the owner chose the simplest: one loose plate that leans against
  a stop wall on the lid, in landscape or portrait. No storage place yet (it does not fit with the two stop walls).
- Checks redone on the model (closed meshes, overhangs, walls, slots, bridges, centre of gravity, stand foot on the
  desk, forward-tipping margin), listed in `hardware/ENCLOSURE-PRINT-ORDER.md`.
- Four STL exported to `hardware/cad/export/` in their printing pose, size and bounding box verified.
- Tables of `ENCLOSURE-PRINT-ORDER.md` filled with what was done and reported, with date and origin; measurement
  sheet gained the owner's new readings (rows 7b to 7d and 13); design record updated where it had become wrong.

## Not done, to report

- No slice, no print, no fit test. Every new number is a design value, not measured, unless a measurement row says so.
- Cables: battery cable 95 mm is shorter than the route inside the box (about 105 mm), so a JST-PH extension is needed;
  the 50 mm antenna cable is tight; the battery pocket leaves no room for the cable to leave on its top-right corner.
- The stand plate has no storage place. The portrait stop wall and the landscape stop wall columns are unverified
  precautions that can be removed.
- The IKEA wood edge (x = 74 mm) and the mass centre depth (6 mm) behind the tilt and stability figures are not measured.
- The wood profile behind the screw lugs is not measured.
- During the session the .blend in this worktree was once rewritten with an intermediate state at 21:27 for a reason not
  identified; the final save replaced it.

## Files

`hardware/cad/skypane_cassette.blend`, `hardware/cad/export/*.stl`, `hardware/ENCLOSURE-PRINT-ORDER.md`,
`hardware/ENCLOSURE-MEASUREMENTS.md`, `hardware/ENCLOSURE-3D-DESIGN.md`.
