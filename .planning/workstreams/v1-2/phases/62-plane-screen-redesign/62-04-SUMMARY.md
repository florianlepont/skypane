---
phase: 62-plane-screen-redesign
plan: 04
subsystem: render
tags: [aircraft, crop-point, halo, giant-lettering]
requires: [62-01]
provides:
  - server/plane/render/giant/aircraft.py (cut_fraction, split_halves, nose_half, rear_half, whole_aircraft, paint_aircraft, load_content)
affects: [later giant layout plans (A, B, C, A+diagonal)]
key-files:
  created:
    - server/plane/render/giant/aircraft.py
    - server/test_giant_aircraft.py
key-decisions:
  - "Cut search window 0.40-0.70 of opaque width; among near-minimal columns (within 5% of the thinnest) the one nearest the middle wins, keeping halves balanced"
  - "Geometry is pure functions of canvas size and image size; portrait and landscape share them. Layout plans pass their own plane-width and vertical fractions"
requirements-completed: [PSR-05]
duration: short
completed: 2026-11-09
---

# Phase 62 Plan 04: Aircraft cut and placement Summary

Per-aircraft crop-point heuristic plus halved/whole placement geometry and halo painting, all hard-masked so only the six palette indices reach the canvas.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Crop-point heuristic | 605e25e | `cut_fraction(rgba)` on opaque column heights (paste threshold 127); `cut_fraction_for_path` cached per (path, mtime, size) through the safe loader; fallback 0.5 |
| 2 Placement and painting | c5e0743 | `nose_half`, `rear_half` (cut columns past the canvas edge by 2.5% of width), `whole_aircraft` fit-and-centre, `paint_aircraft` (thresholded white halo then quantised body) |

## Measurements

All 52 vendored PNGs (the directory also holds non-image files) pass: cut within 0.40-0.70 and cut-column height at most 1.3x the fuselage median (observed ratios 0.47-1.01). Outliers called out in the plan: `gendarmerie-nationale` cuts at 0.62 with ratio 0.47 (the median is inflated by large livery elements, the cut is thin), `air-corsica` cuts at 0.55 with ratio 1.02. No per-file window table was needed. Many files land on the upper window edge (0.70) because the plateau behind the wing is flat; the owner may want to eyeball those halves (rear half then shorter).

## Deviations from Plan

None in behaviour. Notes:
- The plan said "54 files"; the directory has 52 PNGs (54 entries including non-image files). The test asserts the visited set equals the directory's PNG listing.
- Task 1's commit contains the heuristic only; Task 2 added the rest of the module.
- Landscape (800x480) placement of the halves is geometry-only here: functions take `plane_width_frac`/vertical fractions as inputs, and the defaults are the portrait mock values. The landscape layout plan must pass its own fractions.

## Verification

pytest `server/test_giant_aircraft.py` (69 passed), `server/test_import_boundaries.py`, ruff, mypy (31 files), function-size gate, comment-history guard all pass. `aircraft.py` is not on the mypy list (plan 62-12 adds the giant modules). No golden fixtures, classic render code, Phase 47/47.1 files or hardware/ touched.

## Known Stubs

None.

## Self-Check: PASSED

Files exist; commits 605e25e and c5e0743 present.
