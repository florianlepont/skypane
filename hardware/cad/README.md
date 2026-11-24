# CAD files of the 7.3 inch enclosure

Rear enclosure of the Seeed EE04 frame (7.3 inch Spectra 6) for an IKEA RÖDALM
13 x 18 cm frame. The design record is `../ENCLOSURE-3D-DESIGN.md`; what to
print and what was decided is in `../ENCLOSURE-PRINT-ORDER.md`.

| Folder | What it holds | Edit it? |
|---|---|---|
| `source/` | `skypane_cassette.blend`: the one source file. The parts are built by the script stored inside it (text block `skypane_cassette.py`, Blender 5.3). | yes, this is the design |
| `print/` | The files to slice and print: `skypane_tray.stl`, `skypane_lid.stl`, `skypane_stand.stl`, `skypane_shim.stl`, each in its printing pose. `skypane_printing.3mf` is the Bambu Studio project of the owner (2026-11-24): three plates, shim and stand, lid, tray. `skypane_lid.3mf` is an older slicer project whose role is not stated by the owner. | no, they come from the blend |
| `reference/` | Models of real objects, only to check fits: `ee04_board.stl` (the board) and `ikea_rodalm_13x18_noir.glb` (the frame). | no |
| `alternatives/` | Variants that are not the current design: tray and shim in one part (`skypane_cassette_merged.blend`, `skypane_tray_shim_merged.stl`, and its Bambu Studio project `skypane_tray_shim_merged.3mf`). Not decided, set aside on 2026-11-24: the one print was not clean, and the owner reports the same problem on the main part (cause not determined). | only if you try the variant |

## Changing the design

1. Open `source/skypane_cassette.blend` in Blender and change the parameters at
   the top of the script, or the geometry lines below it.
2. Run the script. It rebuilds `SkyPane_Bac` (tray), `SkyPane_Couvercle` (lid),
   `SkyPane_Bequille` (stand) and `SkyPane_Cale` (shim).
3. Export each part as STL (millimetres) into `print/`. The tray and the lid are
   exported as they are in the model; the shim is moved up by 1 mm so that its
   lowest point is at z = 0; the lid is moved down by 11 mm for the same reason.
4. Slice in Bambu Studio and note the result in `../ENCLOSURE-TEST-PRINT-LOG.md`.

Blender writes a copy of the previous save next to the file as `*.blend1`. These
copies are ignored by git and are not part of the project.

## Rules

- Every dimension here is a design value, not measured, until the test-print
  log says otherwise.
- The material of the current print is PLA (the owner dropped PETG on 2026-11-23).
