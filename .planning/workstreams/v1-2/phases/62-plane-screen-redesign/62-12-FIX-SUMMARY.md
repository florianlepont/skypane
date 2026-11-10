# Phase 62 Fix 12: Browser test failures after the layout setting Summary

Fixes the 132 Playwright failures CI reported on design/plane-screen-exploration. Tests only, plus one small stylesheet fix for a real phone-width defect in the five-link Personalisation navigation.

## Causes and fixes

1. **Default layout is now B (about 100 of the failures).** Frames with no stored layout show the five pairing cards instead of the 18-theme picker. Pinned `layout="classic"`:
   - once in the shared `seed_state_dir` (`companion/test_browser_ux_helpers.py`), which about 43 browser files use;
   - in `test_browser_surfaces.py` (own seed wrapper around `seed_home_tile_variety`);
   - in `test_browser_overhaul_steps.py::test_u4b...` (the owned frame's state dir).
   `test_browser_personalisation_layout.py` still seeds its own layouts (classic or B) and covers the default behaviour explicitly.
2. **Navigation now has five links.** `test_browser_personalisation.py` and `test_browser_personalisation_selector.py` expect Departures, Arrivals, Layout, Special looks, Calendar (Départs, Arrivées, Disposition, Allures spéciales, Calendrier), the layout route in the view list, and the nth-of-type index shift.
3. **Real product defect (CSS).** With five labels, the French labels overflowed their segments at 360/390 px (`test_browser_segment_centring.py`, selector `clipped` check). `companion/static/style.css` now, below 700 px, uses an 11px label that may wrap, with 1px inline link padding. The navigation still fits without sideways scrolling, as `test_on_a_phone_the_navigation_fits_without_scrolling...` requires. Checked with a screenshot at 360 px in French.
4. **`test_browser_personalisation_layout.py::test_picking_layout_c_...` (our new test, 2 failures).** The test was wrong, not the product: the save bar shows the one message ("Unsaved changes" / "Modifications non enregistrées") and names areas only when several changed (`dirty-state.js`). The test now asserts that message and that the Layout view's own `data-dirty-section` is "Layout" / "Disposition". The Layout view works as designed.

5. **Render baseline.** The CSS fix changes the stylesheet cache-busting hash that `companion/testdata/render_baseline.json` records, so `test_render_baseline.py` failed. Regenerated with `test-support/companion_render_snapshot.py --write`; the diff is only the `style.css?v=` value (72 lines).

## Commits

- 2e9f238 fix: keep five Personalisation section labels unclipped on a phone
- 5ba93c1 test: pin the shared browser seeds to the classic layout
- e9b0701 test: expect the Layout view in the Personalisation navigation

## Deviations

- [Rule 1 - Bug] CSS fix above (production stylesheet, not the layout picker files).
- No assertion weakened, no test skipped or deleted. No classic golden fixtures, Phase 47/47.1 or hardware/ touched.

## Verification

- The 15 listed browser files: 382 passed, exit 0.
- Whole browser suite in three chunks (-n 6): chunk 1 636 passed exit 0; chunk 2 1346 passed, 1 failed exit 1 (`test_browser_motion_sheets.py::test_with_reduced_motion_a_drag_release_still_closes_instantly`, a 15 s timeout under load while another chunk ran in parallel; passes alone, unrelated to layout); chunk 3 684 passed exit 0.
- Non-browser companion suite (`-m "not browser"`): 6425 passed, 3 skipped, and 1 failed (`test_render_baseline.py`, fixed by the regeneration above, re-run green).
- ruff clean, mypy clean (44 files), function-size gate clean, comment-history check exit 0.
