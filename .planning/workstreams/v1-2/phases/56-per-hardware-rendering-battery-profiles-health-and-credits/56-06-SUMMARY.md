---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 06
subsystem: render
tags: [geometry, landscape, hold-screens, dither]
requires: ["56-01", "56-02"]
provides:
  - size-aware new_canvas, pack_panel, dithered_state_background
  - landscape_common geometry helpers
  - landscape hold composer and builders
affects: [landscape layout family]
key-files:
  created:
    - server/plane/render/landscape_common.py
    - server/plane/render/landscape_hold.py
    - server/test_geometry_primitives.py
    - server/test_render_landscape_hold.py
  modified:
    - server/panel_format.py
    - server/plane/dither.py
requirements: [HWR-01]
metrics:
  tasks: 2
  completed: 2026-10-30
---

# Phase 56 Plan 06: Size-aware primitives and landscape hold screens Summary

Optional size on canvas, packing and dithered background (legacy bytes unchanged), plus a native landscape hold-screen composer whose geometry derives entirely from the canvas size.

## Commits
- fc9c9368: size-aware new_canvas / pack_panel / dithered_state_background (cache keyed by size)
- 3aaafdf9: landscape_common.py, landscape_hold.py and tests

## Notes
- pack_panel rejects odd or non-positive widths with ValueError.
- Hold builders: empty (white field), quiet hours, display off, battery empty, no-connection, updating (dimmed dithered field). Glyph in left column, tracked heading, rule and wrapped body in right column; heading fitted with tracking-aware sizing.
- Tests cover 800x480 (192000 bytes) and 1024x600, palette legality, determinism, margins, cache non-poisoning.
- Portrait modules and golden fixtures untouched.

## Deviations from Plan
None. Initial heading fit ignored tracking and overflowed at 1024x600; switched to the tracking-aware fit before commit.

## Self-Check: PASSED
