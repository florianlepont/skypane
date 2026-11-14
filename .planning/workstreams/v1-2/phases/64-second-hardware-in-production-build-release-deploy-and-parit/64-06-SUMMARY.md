---
phase: 64
plan: 06
subsystem: render
tags: [landscape, hold-screens, marks]
requirements: [HW2-04]
key-files:
  modified:
    - server/plane/render/landscape.py
    - server/test_render_landscape_hold.py
metrics:
  completed: 2026-11-14
---

# Phase 64 Plan 06: Landscape hold marks Summary

Battery-low and source-fault marks are now drawn on the landscape empty, quiet-hours and display-off holds, in the hold's own ink, while battery_empty stays byte-constant.

## What changed

- `landscape.py`: new `_with_marks` helper calls `landscape_card.draw_battery_low` / `draw_source_fault` after the hold builder returns (EMPTY_INK for empty, DIMMED_INK for the dimmed holds). battery_empty is untouched. `landscape_hold.py`, `hold_screens.py`, `layout.py` and portrait paths are not edited.
- Tests: flags-off identical to the bare hold, marks in the bottom-left clear of the glyph/text block and inside the canvas, marks use the hold ink, battery_empty identical for all four flag combinations.

## Verification

- New mark tests failed before the change (6 failures) and pass after.
- `pytest server/test_render_landscape_hold.py server/test_golden_render.py server/test_golden_giant_render.py`: 136 passed, no golden fixture edited.
- `pytest server -k "landscape or golden"`: 791 passed. `stub-server/test_phase47_freeze.py`: 21 passed.
- Function-size gate, comment-history guard and ruff pass.

## Deviations from Plan

None. (Test measures the glyph/text block on the white-field empty hold because the dimmed holds dither their field.)

## Self-Check: PASSED
