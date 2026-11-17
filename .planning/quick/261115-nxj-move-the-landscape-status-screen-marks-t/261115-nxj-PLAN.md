---
quick_id: 261115-nxj
description: Landscape status screen marks go to the top right and never overlap the text
---

# Quick task 261115-nxj: marks of the landscape status screens at the top right

## Problem (found while rendering the EE04's holds for the owner, 2026-11-15)

In the default (giant) layout, in landscape (the EE04, 800x480), the status screens (empty, quiet hours,
display off) draw the battery-low glyph and the source-fault badge in the bottom-left corner
(`server/plane/render/giant/status.py::_paint_marks`, landscape branch: `landscape_card.draw_battery_low`
and `landscape_card.draw_source_fault` with `overlay_right = size[0] * 0.5`). That corner already holds the
last line of the body text, so the battery glyph overlaps "The display updates the moment one is." and the
source-fault badge and its caption print over it, unreadable. Portrait is unaffected and must not change.

## Owner decision

Put the marks at the TOP RIGHT of the landscape status screens.

## Task 1: failing tests first

Behaviour tests on the rendered image (see the existing giant status tests, e.g. `server/test_giant_*`, and
`server/plane/render` tests): for the EE04 profile (800x480; enable the second type for the test the way
existing tests do), for each status kind that takes marks (empty, quiet_hours, display_off) render the screen
WITHOUT marks and WITH battery_low, with source_fault, and with both. Assert (a) a mark is visible in the
top-right region (some pixels differ there), (b) the marks only paint on pixels that are blank in the same
screen without marks (no overlap with any text or icon), (c) nothing is painted in the bottom-left region
that differs from the no-marks render. The source-fault caption must be readable: not truncated with an
ellipsis at 800 px if there is room (check what `landscape_card.draw_source_fault` does with its right limit
and use the free top-right width), and the two marks must not overlap each other when both are set.
These must fail before the fix. Also a portrait test that the portrait status screens are byte for byte the
same as before (the existing goldens cover it).

## Task 2: the fix

Change only the landscape branch of `_paint_marks` (and, if needed, small helpers in `landscape_card.py`
or `landscape_common.py` that take an anchor or position, keeping their current defaults so the active
flight card and the classic landscape holds do not change). Right-align to the margin (`margin_for(size)`),
stack or place side by side so both marks fit and neither overlaps the headline/icon. Keep the ink of the
screen. Do not change the classic layout's landscape holds (`server/plane/render/landscape.py`), the
portrait paths, the active flight cards or battery_empty (its bytes must stay constant).

## Constraints

- No Phase 47 or 47.1 file. Do not edit `.github/workflows/`, STATE.md, ROADMAP.md or the walk-through.
- The goldens of the live frame and of every legacy render must not change: run `server/test_golden_render.py`,
  the giant goldens and `stub-server/test_phase47_freeze.py`. If a golden of a landscape giant status screen
  with marks exists and changes, update it on purpose and say so.
- ./CLAUDE.md conventions (English comments, no plan or phase IDs, behaviour tests, ruff, mypy list,
  function size gate, comment-history guard).
- Run the FULL server and stub-server test suites (not only targeted files) plus `scripts/check_function_size.py`.

## Done when

The new tests fail before and pass after; the full suites pass; the SUMMARY states which goldens (if any)
changed and why, and includes the path of PNGs rendered for the owner to look at (write them under the task dir
as `marks-*.png` only if small, otherwise report how to regenerate them).
