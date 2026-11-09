---
phase: 62-plane-screen-redesign
plan: 05
subsystem: render
tags: [lettering, anton, pairing-field, palette-check]
requires: [62-01, 62-03]
provides: ["lettering.line_mask/line_layer/paint_lines", "field.field_pattern/small_text_ink_pattern", "palette_check.assert_giant_palette"]
affects: [giant lettering layouts]
key-files:
  created:
    - server/plane/render/giant/lettering.py
    - server/plane/render/giant/field.py
    - server/plane/render/giant/palette_check.py
    - server/test_giant_lettering.py
decisions:
  - "Accents extend above the slot: line_mask is exactly (box_w, slot_h) while line_layer/paint_lines keep the overhang"
requirements-completed: [PSR-02, PSR-08]
completed: 2026-11-09
---

# Phase 62 Plan 05: Giant drawing primitives Summary

Stretched strictly binary Anton lines (optionally two-tone across a band), per-pairing field and small-text patterns using palette indices only, and a giant-family palette check that accepts the white-dominant yellow field.

## What was built
- `lettering.py`: lines drawn at the fixed supersample size, scaled so the cap height fills the slot and the width fills the box, thresholded at `MASK_THRESHOLD` (127). `line_layer` returns the layer plus accent overhang; `line_mask` is the exact-size capital band; `paint_lines` stacks 1-3 lines and, given a band mask and field shade, paints in-band lettering with the shade (multiply/subtract on hard masks). Optional `downsample_2x` switch for the glass check. `supported_lines` lets callers fall back to the airline name.
- `field.py`: `field_pattern` (dithered at 0.4/0.75, flat white for the white pairing), `small_text_ink_pattern` (yellow dithered 45% toward black, others flat ink), `ink_index`.
- `palette_check.py`: `assert_giant_palette(canvas, field_idx)`; legacy `_assert_legal_palette` untouched.

## Deviations from Plan
- Single-line proportions: lines are always stretched to the given box; callers choose the box (the mock's proportion-keeping single word is not built in).
- Letter overshoot of round glyphs (1 px) shows as overhang for plain lines; the accent test compares against it.
- Ink columns are measured from the rendered pixels, since font bbox left included side bearing.

## Verification
`server/test_giant_lettering.py` (28 tests) and `server/test_render.py` green (190 passed together), ruff, function-size gate, comment-history check, import-boundary test clean; mypy clean for the three new modules (existing `fonts.py`/`aircraft.py` mypy findings from earlier plans are outside this plan).

## Commits
- f46fe0c: lettering lines
- 7143964: fields and palette check

## Self-Check: PASSED
