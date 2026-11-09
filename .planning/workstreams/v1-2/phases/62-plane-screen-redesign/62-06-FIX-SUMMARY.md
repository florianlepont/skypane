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

# 62-06 Fix 2: whole-aircraft scale fixed, halves anchored on what is seen

**Defect:** with the half width fixed, the whole-aircraft scale varied with the
heuristic cut, so the nose looked smaller (more wing, smaller logo) and the tail
larger than in the validated mock-up.

**Fix:** the whole aircraft is sized at the mock-up widths again
(`NOSE_PLANE_WIDTH_FRAC = 2200/1200`, `REAR_PLANE_WIDTH_FRAC = 1250/1200`) and cut
at the heuristic fraction. The nose half is anchored by its cockpit end at
`NOSE_LEFT_X_FRAC = 130/1200` of the width, the rear half by its tail end at
`REAR_RIGHT_X_FRAC = 595/1200`; vertical fractions unchanged. The half-width
fractions and `nose_plane_width`/`rear_plane_width` are removed. `nose_cut` raises
the cut (and `rear_cut` lowers it) only when the half would otherwise end inside
the frame. All four fractions are parameters of `_paint_halves`/`nose_half`/
`rear_half` for the landscape plan.

**Clamped files (1200x1600):** nose cut raised to 0.5 for 14 illustrations (cuts
0.477-0.5, e.g. generic-a350, air-caraibes, klasjet; the rest at exactly 0.5);
rear cut lowered to 0.499 for 49 illustrations (cuts above 0.499, e.g.
air-france 0.685). Only invisible parts change.

**Tests:** 52 illustrations assert cockpit left 110-150 px, tail right end 570-620
px, cuts beyond both edges, bleed at most half a canvas, no overlap.

**Verification:** ruff, mypy, function-size, comment-history, giant tests and
`test_render.py` pass. Layouts a and a_diagonal (blue_light, AFR1006) compared by
eye with layouts-departing.png: same aircraft size, large AIRFRANCE logo on the
nose half, tail bottom-left.
