# 62-06 Fix: halved aircraft sized by half width, not whole-aircraft width

**Defect:** the nose half was cut from an aircraft of fixed width (2200/1200 of
the canvas), so its width grew with the cut fraction (0.70 gave 1540 px at
1200 px) and the cockpit fell off the left edge.

**Fix:** each aircraft is now sized so its half has the validated width:
`nose_plane_width = NOSE_HALF_WIDTH_FRAC / cut`, `rear_plane_width =
REAR_HALF_WIDTH_FRAC / (1 - cut)` with 1100/1200 and 625/1200 of the canvas
width. Overshoot and vertical fractions are unchanged; the fractions are
parameters of `_paint_halves` (portrait defaults) for the landscape plan.
The cockpit tip lands at about 130 px for every illustration.

**Tests:** all 52 illustrations at 1200x1600 assert nose left 100-200 px, nose
cut column past the right edge, rear cut column past the left edge, rear right
end 570-700 px, bleed bounded, no overlap. Old width constants removed from tests.

**Also:** mypy annotations in `fonts.py` and `aircraft.py` (`_font_cache`,
`_cut_cache`; `Image.Resampling.BOX`).

**Verification:** ruff, mypy, function-size, comment-history, giant tests and
`test_render.py` pass (576 tests). Renders checked by eye.
