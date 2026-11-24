# CAD files of the 7.3 inch enclosure

Rear enclosure of the Seeed EE04 frame (7.3 inch Spectra 6) for an IKEA RÖDALM
13 x 18 cm frame. The design record is `../ENCLOSURE-3D-DESIGN.md`; what to
print and what was decided is in `../ENCLOSURE-PRINT-ORDER.md`.

| Folder | What it holds | Edit it? |
|---|---|---|
| `source/` | `skypane_cassette.blend`: the one source file. The parts are built by the script stored inside it (text block `skypane_cassette.py`, Blender 5.3). It also holds the separate tray and shim, hidden, for the two-part alternative. | yes, this is the design |
| `print/` | The files to slice and print: `skypane_tray_shim.stl` (the one-part tray with the shim rim, chosen by the owner on 2026-11-24; its Bambu Studio project is `skypane_tray_shim.3mf`), `skypane_lid.stl` and `skypane_stand.stl`, each in its printing pose. `skypane_printing.3mf` is an older Bambu Studio project (three plates: shim and stand, lid, tray): use it for the lid and the stand, its tray and shim plates are the two-part design. `skypane_lid.3mf` is an older slicer project whose role is not stated by the owner. | no, they come from the blend |
| `reference/` | Models of real objects, only to check fits: `ee04_board.stl` (the board) and `ikea_rodalm_13x18_noir.glb` (the frame). | no |
| `alternatives/two-parts/` | The previous design, tray and shim as two separate parts (`skypane_tray.stl`, `skypane_shim.stl`), kept in case the owner goes back. | only if you go back |

## Changing the design

1. Open `source/skypane_cassette.blend` in Blender and change the parameters at
   the top of the script, or the geometry lines below it.
2. Run the script. It rebuilds `SkyPane_Bac` (tray) and `SkyPane_Cale` (shim) as separate parts, then unites them into `SkyPane_Bac_Cale`, the one-part tray to print (the two separate ones stay hidden), and `SkyPane_Couvercle` (lid) and `SkyPane_Bequille` (stand). Running it again replaces the one-part tray instead of adding a copy.
3. Export each part as STL (millimetres) into `print/`, with its lowest point at
   z = 0: the one-part tray is moved up by 1 mm (its rim goes down to z = -1 in
   the model), the lid is moved down by 11 mm, the stand is exported as it is.
   Hidden objects are not exported: show a part before exporting it.
4. Slice in Bambu Studio and note the result in `../ENCLOSURE-TEST-PRINT-LOG.md`.

Blender writes a copy of the previous save next to the file as `*.blend1`. These
copies are ignored by git and are not part of the project.

## Rules

- Every dimension here is a design value, not measured, until the test-print
  log says otherwise.
- The material of the current print is PLA (the owner dropped PETG on 2026-11-23).
