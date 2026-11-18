# Enclosure: print order

Decisions, design changes, checks and the spec sent to the print provider for
the rear enclosure of the 7.3 inch frame. The design record is
[ENCLOSURE-3D-DESIGN.md](ENCLOSURE-3D-DESIGN.md); the measurements are in
[ENCLOSURE-MEASUREMENTS.md](ENCLOSURE-MEASUREMENTS.md).

Rules: every number copied from the design record is a design value, not
measured, until the owner reports otherwise. Nothing here says a part was
exported, sliced or printed until the owner reports it.

Centring reference (owner decision, 2026-11-18): everything is centred on the
opening of the mat (140 x 99 mm today), not on the active area of the screen.

## Decisions

| Subject | Proposed value | Status | Date |
|---|---|---|---|
| Printer or means | First print on the printers at the owner's workplace: Bambu Lab X1 series (exact model to confirm). No printer purchase for now; the Bambu Lab X2D Combo (749 EUR noted, Black Friday offer until 2026-12-01, to recheck) stays an option after the first fit and is the owner's decision. | decided by the owner | 2026-11-18 |
| Provider | The owner's workplace (own access, no print service) | decided by the owner | 2026-11-18 |
| Material | PETG; any colour (changed by the owner on 2026-11-18; the previous proposal was black) | decided by the owner | 2026-11-18 |
| Nozzle | 0.4 mm, or another if needed | decided by the owner | 2026-11-18 |
| Filament brand | Bambu Lab filament (reference to confirm when known) | decided by the owner | 2026-11-18 |
| Build plate | Not stated yet; record when known | open | |
| Lid fixing | M2 self-tapping screws, pilot holes 1.7 mm, through holes 2.4 mm (design values, not measured). Heat-set inserts are a fallback if the printed threads wear. | decided by the owner | 2026-11-18 |
| Slicer | Bambu Studio | decided by the owner | 2026-11-18 |

## Design changes from the measurements

| Part | Dimension | Old design value (design value, not measured) | New value | Measurement row | Date |
|---|---|---|---|---|---|
| | | | | | |

## Design checks redone

| Check | Result as reported by the owner | Date |
|---|---|---|
| Closed meshes | | |
| No support needed | | |
| No wall under 0.8 mm | | |
| No slot under 1 mm | | |
| Bridges 4.5 mm at most | | |
| Centre of gravity against the landscape hook axis (with the measured masses) | | |

## Print-order spec

To use for the print at the owner's workplace. It contains dimensions only: no device identifier,
address or secret.

| Item | Value |
|---|---|
| Parts | Tray, lid, stand, shim; quantity 1 each. File names: `skypane_tray`, `skypane_lid`, `skypane_stand`, `skypane_shim` (`.stl` or `.3mf`) |
| Orientation | Flat face down, no support |
| Material | PETG; any colour (changed by the owner on 2026-11-18; the previous proposal was black) | decided by the owner | 2026-11-18 |
| Nozzle | 0.4 mm, or another if needed | decided by the owner | 2026-11-18 |
| Layer height and infill | To record from the slice |
| Fit-critical dimensions | Fit in the frame rebate, hinge, screw holes, battery bay, ribbon slot |
| To report back | Actual print settings, filament brand, cost per part |

## Slice check

| Part | File | Slicer and version | Layer height | Walls | Infill | Supports needed | Thinnest wall (mm) | Thinnest slot (mm) | Estimated mass (g) | Estimated print time |
|---|---|---|---|---|---|---|---|---|---|---|
| Tray | | | | | | | | | | |
| Lid | | | | | | | | | | |
| Stand | | | | | | | | | | |
| Shim | | | | | | | | | | |

## Files

Printable files go in `hardware/cad/export/`, one per part, with the names
above. None exists yet.
