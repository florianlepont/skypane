# Phase 61 Plan 127: Audit 6, lot F (bugs and regressions) Summary

**Ten audit 6 findings fixed with a browser or behaviour test each: the `flip` page error, the Style layout shift, Save and continue landing, Discard then Back, a More sheet focus trap, error pages without a selected cell, French accents on tab labels, primary and danger button styles on every page, a non-overshooting tab pill, and a listener guard (leak not reproducible).**

## Per finding

### A6-01 / V6-03: `flip is not defined` (43647d5f)
- Cause: `playUnlock()` in `motion.js` ended with `return flip;` after the variable was removed.
- Fix: the stray return is gone.
- Test: `test_browser_motion_unlock.py::test_the_first_airlines_visit_unlocks_cards_without_any_page_error` (390 and 1280, listens to `pageerror` and console errors). Red first (2/2), green after.

### A6-03: Style preview jumps 221 px (74110adf)
- Cause: the look view became a grid only when the deferred scripts added the `js` class, so the picture was laid out as a block (centred) and re-flowed into the left column about 150 ms in. Reproduced: CLS 0.0385 (Departures) and 0.0478 (Arrivals).
- Fix: the look-view grid rules in `style-display.css` also apply under `js-early`, which the synchronous head script sets before the first paint (`:is(.js, .js-early)`). The stylesheet test parser (`test-support/companion_markup.py`) now splits selector lists only at top-level commas, so `:is(a, b)` is one selector.
- Test: `test_browser_page_opening.py::test_the_style_page_opens_on_a_wide_screen_without_the_picture_moving` (Departures and Arrivals, reduced motion and not, CLS <= 0.01). Red first (4/4), green after.

### W6-01: Save and continue lands on the wrong page (02c37213)
- Fix: the settings save's return allow-list gains `/account`, `/airlines/manage`, `/fleet`, `/users`, `/audit` (exact membership against a fixed tuple, never a prefix or parsed value; same-origin paths only). `config_page.shell_route` now wraps a rejected save as Device or Style only (it would have raised for the new routes). The page-side list is matched with and without a `/devices/<id>` prefix in the script (Console links to a frame's pages carry no prefix); the unprefixed address is what the server checks.
- The frame rename page always carries a `return_to` field (`data-leave-any`); the script fills it with the tapped path and query and the server still checks it with the sign-in `next` validator.
- Where a save cannot land on the tapped page, the dialog now says so: the primary reads plain "Save" ("Enregistrer") and a note "After saving you stay on this page." appears (new `choice_dialog_html` options `alt_primary_label` and `note`, EN/FR strings).
- Per page:
  - Style (all views): lands on the tapped page for Style views, Device, nav tabs, Account, Airline editor, Users, Audit, Fleet (plain `/fleet`). A link with a query (for example `/fleet?frame=...`) is not accepted: Save and stay, with the note.
  - Fleet settings: same list; Users, Audit, Editor and Account now land where tapped.
  - Frame rename: lands on any tapped in-app page (also without `return_to`).
  - New special look, Edit special look, Calendar connect, calendar look, Location and detection: their save routes always return to their own parent view, so they cannot honour the tapped page. They now show "Save" and the stay note instead of a silent wrong landing (not changed to honour: a design change to those save handlers).
- Tests: `test_browser_leave_dialog_pages.py` (new: Account/Audit/Editor landing, query link says so, rename lands on Flights and stores the name; the table row for Fleet flipped to honoured; `_change_wake` made independent of earlier saves), `test_config_page_04b.py` (allow-list and equality with `console_routes`), `test_frame_rename_and_users_switch.py` and `test_browser_home_title.py` updated in place for the always-present field (see deviations).

### W6-03: Discard then Back restores the edit (c8952434)
- Cause: the browser restores a form as it stood when the page was left.
- Fix: `discard()` in `dirty-state.js` resets the guarded form before leaving. Works for form restoration and bfcache without server markup.
- Test: `test_browser_style_leave.py::test_discard_then_the_browsers_back_shows_the_saved_values_and_no_bar` (browser Back and `history.back()`). Red first, green after; run 4 times in parallel, 0 failures.

### W6-02: More sheet has no focus trap (fd791df8)
- Fix: the Tab handler in `modal.js` that traps dialogs also traps the open `details.tab-bar__more` (its cell and panel are the only stops); closing the sheet while focus is inside it (or lost to the body) returns focus to the More cell. Escape and outside tap unchanged.
- Tests: `test_browser_more_sheet.py` (Tab and Shift+Tab stay inside, focus returns on Escape and on second tap). Trap tests red first; the focus-return test already held for Escape and stays as a guard.

### V6-05: More selected on 404 and 500 (8bc496b1)
- Fix: new `no_tab` flag on `page_shell` and `_tab_bar_html`, set by the 404, 403 and 500 pages: no cell is selected, More included (Credits and the catalogue keep More as their pill cell, as decided in 61-120). An administrator with no frame in scope gets the Console destinations bar (no Health dot, as the existing 404 test requires) instead of a lone More cell. A plain user without a frame still gets no bar.
- Tests: `test_nav_spaces.py` (two unit tests, red first), `test_browser_page_opening.py::test_the_not_found_page_selects_no_cell_and_keeps_a_whole_bar`; the pill-on-every-page test no longer lists the 404.

### V6-02: French tab label accents clipped (a5295253)
- Fix: `.tab-bar__label` gets `padding-block: 2px; margin-block: -2px` so the clip box covers the glyph box and the cell keeps its 56 px height.
- Test: `test_browser_more_sheet.py::test_no_french_tab_label_loses_its_accent_or_its_descender_to_the_clip` (glyph range inside the clip box, 360 FR, Console bar). Red first.

### V6-01 / V6-08: Save and continue faint, danger painted as primary (29576e54)
- Cause: the base `.btn--primary` and `.btn--danger` rules lived in `style-c-console.css`, which Flights, Airlines and the airline editor do not link; there a danger submit fell back to the filled `button[type=submit]` style, and the leave dialog's primary had no class at all.
- Fix: both base rules moved to `style.css` beside the other variants (one rule per selector); the choice dialog's primary carries `btn btn--primary` (the /components sample and the real dialog are the same function).
- Tests: new `test_browser_button_variants.py` (primary and danger on 5 pages in both themes, leave dialog primary equals the Save bar's Save, catalogue sample primary). Red first (Airlines, Flights, airline editor, leave dialog).

### A6-02: Tab pill overshoot (16a6ceba)
- Cause: the tap glide and the view transition group both used the spring easing (+45 px overshoot over 227 px), so on a late page the pill rested on More.
- Fix: both use `--ease-out`: one straight glide that waits on the tapped cell. The cross-fade stays the only page motion.
- Test: `test_browser_tab_pill_transition.py::test_the_pill_never_overshoots_the_tapped_cell_while_the_page_is_late` (destination request held, pill samples via an exposed binding; forward and back). Red first (24 px and 17 px past the cell), green after; 4 parallel runs, 0 failures.

### More sheet listener leak: skipped as a leak, guard added (5bddc56b)
- Not reproducible: with CDP `JSEventListeners` after a forced GC, 100 cycles (toggle, outside tap, Escape; also at CPU x4 with the audit's 60 ms waits, on Flights) left 66 listeners before and after. The audit's +13 listeners on a data-heavy page (209 to 222) are likely the page's own refresh adding cards, not the sheet; the code has no per-open listener (the sheet's only handlers are bound once on `document`).
- Added `test_opening_and_closing_the_sheet_leaves_no_event_listener_behind` (50 cycles, toggle and Escape) as a guard. It cannot be seen red.

## Deviations from Plan

- Two earlier commits of this plan left tests red that I had not run: the rename page tests (`test_frame_rename_and_users_switch.py`, `test_browser_home_title.py`, broken by 02c37213) were fixed in later commits (8bc496b1 and a5295253), and `test_browser_detection.py::test_accent_budget` (broken by 29576e54) in 16a6ceba. Final HEAD is green for them. History was not rewritten.
- Merged `origin/main` (one docs-only commit) with no conflict.

## Tests run

ruff, mypy, `check_comment_history`, `check_function_size`, `test_phase47_freeze` (green at every commit); render baseline regenerated per commit. Per commit the core set (test_device_routes, test_page_structure, test_companion_app_02/03/04, test_components_page, test_stylesheet_structure, test_stylesheet_load_order, test_browser_ux_02, test_sign_in_surfaces, test_suite_guards: 760 passed) plus the touched areas: leave dialog, style leave, fleet dirty bar, detection, save bar, cancel focus, page restore, quiet hours modal, components page, contrast edges, foundations, airline editor, more sheet, more panel, scrim cover, frame menu, nav spaces, audit3/4 fixes, motion, motion unlock, page opening, tab bar float, tab pill transition, french fit, overhaul sweep, round8, small fit, surfaces, every test file that mentions `leave`, `return_to`, `page_shell(` or `choice_dialog` (79 files, 4909 passed), every browser test mentioning `frame/name` (225 passed), every browser test mentioning accent or `btn--primary` (463 passed, 1 load flake: `test_browser_sky_motion.py::test_cards_enter_in_a_short_stagger...` passed twice alone). `test_browser_ux_02.py::test_the_live_preview_crossfade_settles_correct_through_its_own_listener` failed once under `-n 6` and passed 3 times alone. The full suite was not run locally (cadence).

## File sizes

`companion/app.py` untouched (1493); `dirty-state.js` about 900, `modal.js` about 650, `motion.js` 1081 (all under 1500).

## Self-Check: PASSED
