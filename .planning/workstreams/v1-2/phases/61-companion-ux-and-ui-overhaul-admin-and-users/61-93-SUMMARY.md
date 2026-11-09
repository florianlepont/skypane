# Phase 61 Plan 93: Location, accessibility, navigation, overflow Summary

Location search caption, radius slider name and clamp, runway card text, Console tab bar labels at 360 px, 360 px overflow, type floor and Home banner spacing (audit 2 batch 14).

## Done

- W144/F05: the privacy caption under the Location search now shows only while the field is focused and empty, so it never sits over the suggestions or the mode chips (type-ahead already existed).
- F14 / radius 999: `#place-radius-range` has `aria-labelledby` on the "Radius (km)" label and a spoken `aria-valuetext` ("9 km"); it is no longer `aria-hidden`/`tabindex=-1`. A typed radius outside the limits is pulled back to the limit when the field is left (`place-card.js`; `place-map.js` untouched at 1483 lines). No-JS still posts the typed value and gets the server error.
- F20: runway card detail is two unbreakable parts (length, surface) stacked on two lines; the " · " separator is hidden in the sheet and kept in the DOM for the plain form. `overflow-wrap: anywhere` removed there.
- F13: Console tab bar at 360 px: pill gets a 2 px inset, the space switch cell is 69 px, cells stay equal. FR "Cies" -> "Éditeur", FR "Membres" -> "Équipe", EN "Airlines" tab of the editor -> "Editor" (the page keeps "Airline editor"). Every label fits its pill with at least 1.5 px each side in EN and FR.
- F27 glossary: console tab short names now start the full names (Éditeur / Editor, Journal / Audit, Flotte / Fleet); no abbreviation remains.
- F16: the airline collection grid clips sideways overflow (unlock sparks) with a 16 px clip margin so the page never widens; names break only when a word does not fit (`break-word` + `hyphens: auto`); the filter placeholder is a shorter string ("Filtrer" / "Filter") so it no longer clips.
- F31: the Quiet hours dialog tiles show the 24-hour time under the field on a browser with a 12-hour clock (same twin as the Personalisation page).
- F32: sparkline legend, axis labels, drawing axis labels and `<sup>` marks are at least 12 px.
- F22: on desktop the Home banner starts 32 px under the greeting row, clear of the frame button (was 2 px).
- Render baseline and the shell digest in `test_sign_in_surfaces.py` regenerated.

## Not done / notes

- F17 filter chips stay a horizontal strip (a test pins its geometry); the stray "TN" map label (F20) was not reproducible in the audit seed; F28 (sidebar "Éditeur de compagnies" wrapping) measured on one line (44 px) in the audit seed so was left; the Personalisation/Style and Flight history/History short names are unchanged (full names are pinned in many tests and the tab cells cannot hold them).
- The Home banner test cannot reproduce the 2 px gap in its seed (its greeting row is taller); it guards the invariant, the fix was measured on the audit seed (banner top 94 -> 102 px, button bottom 92).
- Pre-existing failure, not from this plan (fails identically on HEAD in a clean worktree): `test_browser_round8_fixes.py::test_the_users_self_row_is_not_wide_and_frames_never_wrap_on_desktop` (Users self row 89 px vs 64 px, from the Users table work).

## Deviations

- [Rule 1] Existing tests that pinned the old structure were updated in place: `test_detection_page.py` (runway detail text now split by tags, whitespace-tolerant), `test_nav_personal_console.py` (console bar FR/EN labels), `test_browser_ux_health_drawings.py` (legend 12 px).
- Equal-cell bar (`test_browser_more_sheet`, 16 px switch tolerance) forced the switch cell to 69 px and the label choices above, instead of content-sized cells.

## Tests run

ruff, mypy, check_comment_history, check_function_size, stub-server/test_phase47_freeze.py; render snapshot rewrite; 97 non-browser companion files mentioning touched modules plus test_companion_app_0*, test_stylesheet_structure, test_suite_guards, test_structure_guards, test_sign_in_surfaces, test_render_baseline and test-support tests (5338 passed); 56 browser files mentioning location/place/radius/tab bar/nav/banner/quiet/sparkline/runway/collection plus test_browser_overhaul_sweep and test_page_scripts (1935 passed, 1 pre-existing failure above); after the last CSS edit: 21 Home/frame-menu browser files, tab-bar files (39), sign-in surfaces, render baseline, stylesheet structure, suite guards (only the same pre-existing failure); the new tests 4x in parallel (13 passed each).

Screenshots: `scratchpad/shots93/` (before_*, after_*).

## Self-Check: PASSED
