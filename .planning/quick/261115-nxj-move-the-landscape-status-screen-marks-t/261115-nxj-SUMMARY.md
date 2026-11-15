---
quick_id: 261115-nxj
status: complete
---

# Quick task 261115-nxj: landscape status marks at the top right

The battery-low glyph and the source-fault badge of the landscape giant status screens (empty/watching,
quiet hours, display off) now sit at the top right, right-aligned to the margin, stacked (battery first,
badge below it; the badge alone takes the first row). The badge caption is no longer ellipsized.

## Changes

- `server/plane/render/landscape_card.py`: `draw_battery_low` and `draw_source_fault` take an optional
  `top_right` anchor (defaults unchanged); new helpers `battery_low_extent` and `source_fault_height`.
- `server/plane/render/giant/status.py`: landscape branch of `_paint_marks` only.
- `server/test_giant_status_marks_landscape.py`: behaviour tests on the rendered image (visible top right,
  blank pixels only, nothing bottom-left, marks apart, caption whole, portrait marks still at the bottom).
  33 tests; 27 failed before the fix.

## Goldens

None changed. The portrait paths, active flight card, classic holds and battery_empty are untouched.

## Verification

Full `server` and `stub-server` suites: 4074 passed, 4 skipped (root permission skips). ruff, mypy,
function-size gate (max 80) and comment-history guard pass.

## Regenerate PNGs

`PYTHONPATH=.:test-support server/.venv/bin/python3 -c "from server.plane.render.giant import status; status.build_status('display_off', (800, 480), source_fault=True, battery_low=True).convert('RGB').save('out.png')"`
