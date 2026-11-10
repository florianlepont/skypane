---
phase: 64-photo-pipeline-server-only
plan: 02
subsystem: photo
tags: [pillow, render, dither, crop, spectra6]
requires: ["64-01"]
provides:
  - "server.photo.crop.FitSetting (fill/bands, pos_x, pos_y)"
  - "server.photo.prep: PrepParams, DEFAULT_PREP (provisional), prepare"
  - "server.photo.render: render_photo, render_photo_packed, preview_png, BAND_INDEX"
  - "test-support/photo_scenes.py synthetic skin and scene builders"
affects: [64-03, 64-04, 64-05]
tech-stack:
  added: []
  patterns: ["ImageOps.fit with validated centering", "paste dithered P image on white palette canvas for bands"]
key-files:
  created:
    - server/photo/crop.py
    - server/photo/prep.py
    - server/photo/render.py
    - test-support/photo_scenes.py
    - server/test_photo_prep.py
    - server/test_photo_render.py
    - server/test_photo_boundaries.py
  modified:
    - pyproject.toml
key-decisions:
  - "DEFAULT_PREP = (cutoff 1.0, strength 0.8, saturation 1.2) stays provisional until the skin-tone record exists"
  - "PrepParams also validates cutoff in [0,49] and strength in [0,1], saturation ceiling 1.3"
requirements-completed: [PHOTO-02, PHOTO-03]
duration: 20min
completed: 2026-11-10
---

# Phase 64 Plan 02: Photo render path Summary

A stored JPEG renders through crop, tone-preserving boost and the shared six-colour dither to a mode-P image for any valid panel size (1200x1600 and 800x480 verified), with fill mode movable by `pos_x`/`pos_y` and bands mode pasted on an exactly-white canvas; the path imports no plane renderer or companion code.

## Tasks

1. Scene builders, FitSetting and provisional prep - commit bcb0dac
2. render_photo with fill and bands, packing, determinism, separation - commit f8bbe27

## Verification

- Photo tests, golden, render and dither tests: 373 passed (`pytest server/test_photo_normalize.py server/test_photo_render.py server/test_photo_prep.py server/test_photo_boundaries.py server/test_golden_render.py server/test_golden_giant_render.py server/test_render.py server/test_dither.py`)
- ruff clean, mypy clean (48 files), function-size gate (1086 functions, none over 80), comment-history gate rc=0
- `git diff --exit-code -- server/fixtures/golden server/plane server/panel_format.py hardware`: empty

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] mypy rejected `Image.LANCZOS` and the untyped dither return**
- **Found during:** Task 2
- **Fix:** used `Image.Resampling.LANCZOS`; added a typed `_dither` wrapper around `dither_to_full_panel_palette` (plane module not edited).
- **Commit:** f8bbe27

**2. [Rule 1 - Bug] Own test expectations wrong for the crop window**
- **Found during:** Task 2
- **Issue:** a square source on the 3:4 panel shows 3/4 of the width, so red is 2/3 (not >90%) at pos 0. Tests now assert 2/3, 1/2, 1/3.
- **Commit:** f8bbe27

### Other notes

- Red-first ordering was not strictly observed: tests and implementation were written together and first run green (same as plan 01).
- The bands histogram test compares the photo area to `dither(prepare(contain(src)))` computed independently, which pins that prep sees the photo area only.
- Extra tests beyond the plan: preview PNG round-trip, PNG stored copy rejected, bands corner markers map to the expected palette indices.

## Known Stubs

None. `DEFAULT_PREP` is intentionally provisional (documented in its comment); the skin-tone record fixes it in a later plan.

## Threat Flags

None. T-64-08 (size validation), T-64-09 (FitSetting rejects bad values), T-64-10 (JPEG-only allowlist, fixed error text) and T-64-11 (empty plane/golden diff) are covered by tests or gates.

## Self-Check: PASSED

Files and commits bcb0dac, f8bbe27 verified present.
