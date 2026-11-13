# Phase 61 Plan 120: One bottom tab bar for everyone Summary

**The phone tab bar is Home, Flights, Airlines, Style, Place, More (Accueil, Vols, Compagnies, Style, Lieu, Plus) for an administrator and a user alike; the administrator's space switch is a row of the Plus panel beside Account. "Compagnies" fits at 360px in French and at 320px without shortening the label.**

Owner decision (Round 26). There was no PLAN.md: the orchestrator's brief was the plan. The branch was merged with `origin/main` first (`f91eaad2`, render baseline conflict resolved by regenerating).

## What changed

- **Bar content.** `_PERSONAL_BAR_PAGES` is Home, Flights, Airlines, Style, Place. The short labels are "Flights" / "Place" in English (were "History" / "Location"); French stays "Vols" / "Lieu". Airlines uses its full name ("Airlines" / "Compagnies").
- **Plus panel.** Account, then (administrator only) the space switch row (`.tab-bar__space-link`, same label, aria-label and destination as the old cell), then theme, language, Sign out. The page-row block, its separator and their CSS are gone; Airlines and Place are not in the panel.
- **Console space.** The Console bar keeps its four pages (Fleet, Users, Editor, Audit) plus Plus and loses the switch cell: five cells. The panel's switch row there leads back to "My frame". Decision for the owner below.
- **Warning dot.** It only ever sat on the Fleet cell of the Console bar (the personal bar and sidebar never carried it). Fleet is still a bar cell in the Console, so the dot is unchanged and still the only one; no dot was added to Plus.
- **Fit.** `.tab-bar__link` is `flex: 1 1 auto; min-width: 44px`: each cell is as wide as its label and the free width is shared equally. At 360px FR the label is 65px at 11px (measured) and the cell about 89px; the shortest cell stays 45px. Font stays 11px. Works at 320px too (below the contract floor, measured anyway).
- **Not-found page of a frame.** More alone gets `tab-bar__more--alone` (96px, far end) because the script's slider element made `:only-child` unusable.
- **Kept:** selected-state pill and its view-transition name, the bar's `skypane-tab-bar` name, 56px cells, reduced motion, motion.js slider (its `--switch` exclusions removed), both themes.

## Tests

New `companion/test_browser_tab_bar_roles.py` (47 cases; seen red before the change, 21 failed of 23 then 12 of 24 for the fit test): bar content per role in EN/FR, light/dark, 360 and 1280; console bar without a switch cell; Plus panel content per role and space (links, forms, sign out, 44px, hit-tested); a tap on the switch row moves between spaces; every label whole, single line, 44px cell, inside the viewport at 320, 360 and 390.

Updated in place (they pinned the old bar): `test_companion_app_02`, `test_nav_spaces`, `test_console_shell`, `test_user_nav`, `test_update_page`, `test_space_switch`, `test_nav_personal_console`, `test_personal_space_parity`, `test_device_routes`, `test_device_links`, `test_sign_in_surfaces` (shell digest, deliberately), `test_status_pages_06` and `_07` (the old equal-cell arithmetic became a six-cell fit arithmetic), the render baseline, and the browser files `test_browser_nav_spaces`, `_space_switch`, `_more_sheet`, `_update`, `_tab_bar_float`, `_round8_fixes`, `_nav_alignment`, `_overhaul_steps` (step counts S1 1 to 2, V1-phone 2 to 1), `_overhaul_sweep`, `_small_fit_fixes`, `_location_polish`, `_home_title`, `_console_shell`, `_console`, `_airline_collection`, plus stale `--switch` selectors in `_motion`, `_page_opening`, `_tab_pill_transition`, and `test-support/nav_spaces_support.py`.

Run: ruff, mypy, `check_comment_history.py`, `check_function_size.py`, `test_phone47_freeze` (21 passed), and 72 test files that mention the bar plus `test_stylesheet_structure`, `test_components_page`, `test_browser_ux_02`, `test_render_baseline`, `test_page_scripts`, `test_i18n`, `test_suite_guards`: 3,216 passed, 2 skipped, 1 failed. The failure, `test_browser_overhaul_steps.py::test_l1_pick_an_airport_from_the_list`, passed 3 of 3 alone (load flake). `test_browser_home_title.py::test_the_home_cards_come_in_one_after_the_other` failed once under load and passed 3 of 3 alone. Not run: `run-all-tests.sh`, per the cadence.

## Deviations

- **One feature commit, not one per step.** The bar change, the panel move and the fit are one stylesheet and one markup change, and each step on its own would leave pinned tests red (the executor rule is green commits only). Tests were still written red first.
- **Step 5 skipped on purpose.** The components catalogue lists tab names from `NAV_SHORT_LABELS` and needs no change; the sketch skill's Navigation section was not edited (it was already behind lots A to E).
- **Unequal cells.** The bar's cells are no longer equal width (labels differ), so the equal-width assertions in several tests became "cells fill the bar, each at least 44px".
- **Remote moved.** While this ran, `origin/milestone/v1.2-phase-61-companion-ux` gained `69ea84f2` (Merge main, round 34 Location). The local branch holds an equivalent merge `f91eaad2`; they will need reconciling (merge or rebase) before the next push.

## For the owner

- In the Console space the bar cannot be the personal six cells without making Users, Audit and the Editor unreachable on a phone, so it keeps those pages (five cells) and the switch back to "My frame" is in Plus. Say if you want the Console pages moved into Plus instead.
- Screenshots (360px, FR) in `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/tabbar/shots/`: `bar-360-fr-{dark,light}-{admin,user}.png` and `bar-plus-open-360-fr-{dark,light}-{admin,user}.png`.

## Self-Check: PASSED

Commit `df89e2b9` exists; `companion/test_browser_tab_bar_roles.py` exists; ROADMAP, STATE, REQUIREMENTS, `hardware/`, `deploy/`, phase 47 files and the frame protocol were not touched; `companion/app.py` is 1497 lines; nothing was pushed.
