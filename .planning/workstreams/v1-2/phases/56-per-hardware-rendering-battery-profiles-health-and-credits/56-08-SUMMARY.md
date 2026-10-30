---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 08
subsystem: render
tags: [landscape, card, entry-point]
requires: ["56-06"]
provides:
  - landscape_card.build_card_canvas (departing/arriving card)
  - landscape.build_landscape_canvas (one entry point for every state)
key-files:
  created:
    - server/plane/render/landscape_card.py
    - server/plane/render/landscape.py
    - server/test_render_landscape_card.py
requirements: [HWR-01]
metrics:
  tasks: 2
  completed: 2026-10-30
---

# Phase 56 Plan 08: Landscape card and entry point Summary

Native landscape active card (illustration left, fitted/wrapped/ellipsized text column right, previous-flight strip, right-hand parallelogram for band themes, battery-low and source-fault overlays in the bottom-left corner) plus `build_landscape_canvas(profile, ...)` dispatching all six states.

## Commits
- 179e5bcd: landscape_card.py and card tests
- Task 2 commit: landscape.py, entry-point tests, test lint fixes

## Notes
- All 18 registered themes render (7 are band themes); geometry derives from canvas size, tests also cover 640x384 and 1024x600.
- Band themes shrink the text column's right edge to clear the band; tag and text honour it.
- Long strings: shrink to fit, then wrap, then ellipsize (T-56-19); bounds asserted against the margins.
- Reuses geometry-free illustration helpers from layout.py read-only; no portrait module edited. Golden and Phase 47 freeze tests pass.
- Landscape hold screens draw no battery/fault overlays (portrait does); out of this plan's scope.
- mypy file list in pyproject.toml not extended (shared file).

## Deviations from Plan
Task 1 commit left two unused test imports, fixed in the task 2 commit. Plan said 16 themes; the registry has 18.

## Self-Check: PASSED
