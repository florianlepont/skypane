# Phase 61 Plan 84: Round 9 straight fixes Summary

Fifteen straight fixes from the owner's round 9 production review (W116, W119, W121, W125, W126, W127, W128, W132, W133, W136-W141), each with a behaviour test; everything else in round 9 waits for the owner's decisions on the mockups.

## What changed

- **W116 Home switches in place.** The Screen and Quiet hours rows are quick-switch regions that ask for a refresh. `quick-switch.js` flips the switch under the finger, posts the form over fetch (same CSRF, access rules and `/quick/*` routes), and on the 204 asks `freshness.js` for one refresh cycle, which repaints the headline and the next-update line through the existing swap. A refusal (anything but 204) rolls the switch back and shows the failure toast. The native POST form is still the no-script path.
- **W119 Quiet hours dialog.** The "Always on" card is gone (the Home switch is the off control). Night and Day stay. A schedule stored off, or on with any custom hours, opens with no card selected and the stored hours in the time fields, nothing crashes.
- **W121 Picture dialog z-order.** The tab bar and its sliding pill were named view-transition groups, painted above the page snapshot that holds the dialog during the grow/shrink transition, then dropped under it. `panel-lookup.js` now holds `is-picture-transition` on `<html>` for the length of the transition and the stylesheet drops those names meanwhile.
- **W125 Calendar view.** The owner gave no detail. Reproduced on the list, the connect page and the edit (replace) page, connected and not, 360 and 1280, EN/FR, light/dark, with console errors captured. Findings: no console errors, no overflow, no clipped controls; one real defect: on the connect/edit page the floating bar's Save used 13-14 px type while Cancel used 15 px (different sizes side by side). Fixed (same size, 44 px). The "offscreen look-table" the probe reports is the closed look disclosure, not a bug. At 360 px in French the status row wraps its text over three lines (functional, left as is).
- **W126 Look tile.** The picker no longer renders Save, Reset or a footer; the floating bar's Save and Cancel are the only ones (Cancel restores every look through the existing reset hook). I could not reproduce the "Comme les départs" card clipped at its top edge at 1100-1440 px wide (card top is clean, no sticky element near it); the extra Save row that made the column taller is gone. Reported, not guessed at.
- **W127 Airlines cards.** More padding in the card and around the picture (inset picture box), wider grid gap.
- **W128 Floating bar label.** "Save" / "Enregistrer" replaces "Save settings" / "Enregistrer les réglages" in every settings bar (the `display.save_settings` key is retired). On a phone the count sits on its own line and Save and Cancel share the line below at equal width; every bar button is now 44 px tall.
- **W132 Tab pill reliability.** Cause: on a page change the new page has no slider element at its first frame (the script that creates it is deferred), so the browser only faded the old pill out. The server-rendered active pill now carries the slider's view-transition name until the script places the slider, so the browser glides old pill to new pill natively every time. The active pill's entrance animation (opacity 0 at first frame) was removed since it would have captured an invisible pill. A second cause showed under load: the first paint can happen while the page is still parsing, before the tab bar exists, so the shell's head now carries `<link rel="expect" href="#tab-bar-end" blocking="render">` and an empty marker follows the bar (only on pages that have a tab bar; browsers without rel=expect ignore it). Verified 16/16 under 8 parallel workers (it failed 3/12 before the marker).
- **W133 Light-blue footer.** Most likely the strip below the page snapshot during a page change showing the canvas colour (the gradient's lighter top stop). `::view-transition` now carries the gradient's last stop. I could not reproduce this on a desktop Chromium (it is a phone-toolbar effect), so this is a best-evidence fix; the owner should confirm on the phone.
- **W136 Users row menu.** Items are `nowrap` and the panel is as wide as its longest label, phone included.
- **W137 Users list.** The section around the list is plain layout (no longer a glass `page-section` with a border), so the count line sits above the single table/card surface.
- **W138 Airline resolve rows.** Name field 280 px, type select 180 px, buttons follow them.
- **W139 Audit log.** The target's id is no longer glued to the address: it is its own labelled secondary item, "Internal ID" / "Identifiant interne", in the expanded detail only.
- **W140/W141 Airlines header.** Title on its row, progress/counter below with room. The sentence read "38 of 36" because the total counted curated airlines only while spotted included uncurated ones; the total is now every listed airline (the figure of the "All" chip): "3 compagnies repérées sur 36" / "3 of 36 airlines spotted". The progress track is visible now.

## Tests

New or adapted in place: Home switches (in place, rollback, keyboard, row tap), Quiet hours (two cards, stored-off dialog), picture transition names, tab pill glide on random tab changes (fails without the fix), Look picker without Save/Reset and floating bar short Save on one line, calendar bar type size, Users menu one line and single surface, airline resolve widths, audit id item, airlines header and sentence and picture inset, `::view-transition` colour.

Screenshots: `scratchpad/shots84/` (users, airlines, quiet hours, personalisation arrivals, calendar probes under `cal/`).

## Existing tests changed in place

Their subject changed deliberately: Quiet hours dialog tests (two cards), Look picker tests (no Save/Reset), the Home switch tests (in place instead of navigating), Airlines header/sentence tests, config page tests ("Save"), the motion-token spender list (the pill's entrance animation is gone), the shell digest and render baseline (head link and marker), `test_browser_ux_02` (a `none` opt-out is not a declared name) and `_display_page_height` in `test_browser_ux_helpers.py` (the Display page can now fit a phone exactly, so equality with the client height is accepted when the Look section's measured bottom edge proves the document is Display's).

## Tests run

ruff, mypy, check_comment_history, check_function_size, stub-server/test_phase47_freeze.py; render snapshot rewritten. 93 non-browser companion test files that mention the changed pages plus `test_companion_app_0*.py`, `test_stylesheet_structure.py`, `test_suite_guards.py`, `test_sign_in_surfaces.py`, `test_render_baseline.py`, `test_page_scripts.py`; 77 whole `test_browser_*.py` files for every touched page plus `test_browser_overhaul_sweep.py` (2291 passed, 1 failed: `test_browser_place_search.py::test_the_lock_holds_for_a_second_and_a_half...`, a 1.5 s timing test on the Location page that I did not touch; passes alone 3/3). New browser tests stressed 4 processes in parallel, zero failures.

## Deviations

- Rule 2: every `.dirty-bar` button is now at least 44 px (the plain floating bar had 30-36 px buttons).
- The "Save settings" wording change touches the Fleet and Location bars too (they already used the short word or wrapped).
