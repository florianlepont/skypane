# Phase 61 Plan 123: Style unsaved layout dialog (W5-18) Summary

**Tapping another Style sub-tab with an unsaved layout now opens the app's own dialog (Save and continue / Discard / Stay here) instead of the browser's generic leave prompt.**

## What changed

- `ui_modal.choice_dialog_html`: a closed `dialog.modal` with three non-form buttons (primary, secondary, quiet "Stay here" with `autofocus` and `data-modal-close`). Catalogued on `/components` (sample trigger, EN/FR strings); `test_components_page.py` passes unchanged.
- `layout_picker.leave_dialog_html` renders it in every Style view that has the Layout card (after the view, so the card-then-nav order is unchanged). Strings `look.layout_leave_*` with French in `companion/i18n_fr/look.py`.
- `modal.js`: `window.SkyPaneModal.open(dialog, returnTo)` so a script can open a dialog with no opener link and name the control that gets the focus back.
- `dirty-state.js`: a click on a `[data-pers-view]` link while the layout radio differs from its loaded value opens the dialog. Save and continue sets the form's existing `return_to` to the tapped view and submits through the bar's Save button (server whitelists the route; no server change). Discard disarms the guard and navigates. Stay here / Escape close and focus returns to the tapped link. A bfcache restore closes a dialog left open. Only layout changes ask; other unsaved values keep the browser prompt; without script nothing changes; Back is untouched.

## Tests

`companion/test_browser_layout_leave.py` (23 tests, 360 and 1280, EN and FR, both themes for geometry): dialog opens on tap with a layout change and not otherwise (clean page and look-colour-only change navigate, the latter with the browser prompt), words in both languages, focus on Stay here, 44 px targets, no cut text, no overflow; Save and continue (stored layout `c`, destination radio `c`); Discard (nothing stored, no browser prompt); Stay here and Escape (page, picked layout, bar and focus); scripts blocked. Seen red first by running the file with the two JS files at HEAD (22 of 23 failed), then green; run 3 times in a row green.

## Deviations

- Commits: steps 1 to 4 share one code commit (`b4d733f2`) because the dialog, the three actions and their tests are one small script change; step 5 needed no edits (no existing test pinned the old behaviour: the broad runs below pass). Two existing tests failed on first run and were fixed in code, not weakened: the French catalogue needs U+00A0 before "?" and the Layout card must be followed directly by the nav (dialog moved after the view).
- A transient uncommitted edit to `ui_groups.py`/`ui_nav.py` appeared in the tree mid-run (not mine, gone after a minute); the render baseline was regenerated after it vanished and contains only this plan's change.

## Tests run

ruff, mypy, check_comment_history, check_function_size, `stub-server/test_phase47_freeze.py`, render snapshot `--write`, test_stylesheet_structure, test_stylesheet_load_order, test_components_page, test_browser_ux_02, test_companion_app_0*, test_render_baseline, test_sign_in_surfaces, test_suite_guards, test_i18n, test_ui_modal, test_page_scripts, test_config_page_0*, test_personalisation*, the browser files for personalisation, save bar, cancel focus, display looks, ux_01/03/04, audit3, round8/11, overhaul steps, page opening, segment centring, surfaces, components page. Final state green (1,567 + 436 + 100 passed across runs; the 10 failures of the first run were the two fixed issues above).

## Self-Check: PASSED
