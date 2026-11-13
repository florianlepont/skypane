# Phase 61 Plan 128: Audit 6, lot G (polish, workflows, motion) Summary

**Eighteen audit 6 findings handled: sixteen fixed with a behaviour or browser test each (seen red first), one verified as already correct (V6-07), one fixed in part (W6-08); four skipped for an owner choice.**

## Fixed

### Visual
- **V6-04** (0fd57b8c): the More cell no longer draws the base summary chevron over its dots (`content: none`); one glyph like every other cell. Test: `test_browser_more_sheet.py::test_the_more_cell_is_one_glyph_like_every_other_cell` (light and dark, closed and open). Two older tests that pinned the caret were updated in place (946ea1a1 `test_status_pages_07`, 443102d0 `test_browser_audit3_fixes` / `test_browser_audit4_fixes`: dots centred, glyph clear of the bar edge).
- **V6-06** (0893743c): the Theme and Language rows share one label-column width (6.5rem), so both segmented controls have the same left and right edge in EN and FR at 360 and 390; labels and options still fit. Test: `test_the_theme_and_language_controls_share_one_left_and_right_edge`.
- **V6-09** (121efdc0): the plain-words licence lines of `/credits` (open data, free crowdsourced, public domain, the two OpenStreetMap lines) go through `i18n_fr/credits.py`; licence identifiers (CC0, BSD-2-Clause) stay as written. Test: `test_credits_page.py::test_every_licence_line_is_in_the_page_language`.
- **V6-11** (744f763d): the direction label of a recent-flight detail joins its words with a no-break space ("Au départ", "À l'arrivée" never split). Test: `test_browser_home_recent_tiles.py::test_a_french_state_phrase_is_never_split_across_two_lines` (360 and 390).

### Workflows
- **W6-04** (e684a43d): a dialog the address opened can name the control it came from (`data-modal-return-focus`, `ui_modal.dialog_html(return_focus_id=...)`); the role confirmation names the row's select, so Escape or "Keep as user" returns focus there. Test: `test_closing_the_role_confirmation_returns_the_focus_to_that_roles_select` (Escape and Keep, EN and FR).
- **W6-05** (62ec2b19): the kept-code cookie now also marks a refusal whose text was not storable (an empty code, never any of the text), and the error shows only on the showing that carries the cookie. A reload is a plain form, so the page no longer blames a code it no longer shows. The code is still never stored beyond the existing two-minute cookie. Tests: `test_user_pairing.py` (new odd-value test; reload shows no error; the odd-value assertion now expects the empty marker instead of no cookie) and `test_browser_user_pairing.py` (reload: no error, empty field).
- **W6-06** (a22a5eb9): `current_space()` puts an administrator with no frame in scope (a page outside both spaces, the 404) in the Console, so the sidebar lists the Console destinations and the space switch marks Console instead of "My frame", matching the tab bar. Test: `test_browser_page_opening.py::test_the_administrators_not_found_page_keeps_the_console_navigation_on_a_desktop`.
- **W6-07** (74ab2cca): picture refusals add `artwork=<key>` and the anchor `#airline-<key>` to the redirect; the flash resolves the key against the airlines the editor lists (new `companion/artwork_airline.py`, never echoes the value) and reads "Air France: Couldn't use that file ..." (FR "Air France : Impossible d'utiliser ce fichier ..."). The editor's airline groups carry `id="airline-<key>"`. Tests: `test_airline_editor.py` (HTTP, EN and FR, type picture, unknown key) and `test_browser_airline_table.py::test_a_refused_picture_names_its_airline_and_the_page_opens_on_that_row`.
- **W6-08** (dd537490, partial): the short tab label "Place" is now "Location" (EN), the first word of "Location and detection"; FR "Lieu" already started "Lieu et détection". Test: `test_nav_personal_console.py::test_the_location_tab_is_named_by_the_first_word_of_its_page_title`; the four tests listing the tab names and the sign-in surface digest were updated deliberately.

### Animation
- **A6-04** (834d6bc5): the collapsed title-search rules (`.filter-bar--title`) match `.js-early` too, so Flights at 768 no longer re-flows after the scripts load (layout shift 0.035 to under 0.01). Test: `test_the_flights_filter_bar_opens_in_its_final_layout` (768 and 1024, reduced motion and not).
- **A6-05** (64a433b8): the More scrim and the `dialog.modal` / `.lightbox` backdrops fade in on `--motion-fast` / `--ease-out`; closing stays instant. The backdrop animation sits in the single `prefers-reduced-motion: no-preference` block because the global reduced-motion override cannot reach `::backdrop` (an existing test pins that). The dim strength itself (55 percent scrim, scrim token for dialogs) is unchanged: no owner value was given. Test: `test_the_dim_behind_the_sheet_and_behind_a_dialog_fades_in_with_what_opens`.
- **A6-06** (64fdcf67): the Home ambient loops (status dot, halo, picture glow, glint, breathing) have `animation-iteration-count: 0` while `.tab-bar__more[open]`, and resume on close. Test: `test_the_home_loops_stand_still_while_the_sheet_is_open_and_resume_after`.
- **A6-07** (e0077e97): the tab pill's glide starts in a zero-delay timeout after every other click handler, and only if the click was not cancelled, so the leave dialog's guard no longer lets the pill set off toward the tapped cell and come back (peak 14 px seen). Test: `test_browser_style_leave.py::test_the_tab_pill_stays_put_while_the_dialog_holds_the_navigation`.
- **A6-08** (8de9ebae): a toast whose dwell ends takes the `is-leaving` state (180 ms fade, 220 ms safety net; reduced motion removes at once) instead of being deleted at opacity 1. Test: `test_a_toast_that_times_out_fades_out_before_it_goes`.
- **A6-10** (27203665): `:where(details[open]) > :not(summary)` fades in on `--motion-fast` (zero specificity on the details part, so panels with their own entrance keep it). Test: `test_a_disclosure_row_fades_its_content_in_when_it_opens`.
- **A6-12** (4e021eda): the `skypane-tab-bar` and `skypane-sidebar` view-transition groups use `--motion-view-transition` and `--ease-out`; the pull spinner reads a new `--motion-spin: 700ms` token; every entrance or exit that said `ease-out` now says `var(--ease-out)`. Kept on the plain keyword and documented in the test: the status halo decay, the switch ring glow, the press scale. The `ease` hover colour transitions (about 35 rules) were not converted: they are hover feedback, not entrances. Tests: `test_companion_app_04.py` (new `test_every_entrance_and_exit_shares_the_one_ease_out_token`, `test_the_tab_bar_and_sidebar_view_transition_groups_spend_the_motion_tokens`, token list now includes the script-read `--motion-spin`) and the spinner duration assertion in `test_browser_motion_live.py`.
- **A6-13** (c3ea1aca): when Load more adds a whole new day, the section no longer enters as one block; its first three rows take the entrance. Test: `test_load_more_animates_the_new_rows_never_a_whole_day_section`.

## Verified, no change needed

- **V6-07** (e8e5cf20 adds a guard test only): the quiet-hours link's element box is 20 px by design (a pinned test requires the keyboard ring to hug its text), but its `::after` already owns a 44 px square. A hit-test at 360, 390, 600, 768, 1280 and 1440, EN and FR, finds at least 44 px of hit area in height and width, so the test was not red. The audit measured the element box, not the hit area. A first attempt to make the box itself 44 px broke the ring test (`test_the_ring_hugs_the_link...`), so it was backed out. If the owner wants a 44 px box, the ring then has to be drawn on a pseudo-element, which is a design change.

## Skipped (no change)

- **W6-09, V6-10, A6-09, A6-11**: need an owner design choice or a performance trade-off (as briefed).
- **A5-15, A5-16, A5-20, A5-21, W5-12, W5-13, W5-17, W5-22, X13, P5-\***: set aside by the owner (as briefed).

## Deviations from Plan

- Earlier commits of this lot left tests red that I had not run at the time; fixed in later commits, no history rewrite: caret tests after V6-04 (946ea1a1, 443102d0), and a render baseline taken with a backed-out style (f8553466).
- A6-05: the first version also animated `.lightbox::backdrop` outside the reduced-motion guard, which `test_view_pages_04` forbids; the backdrop animation moved into the single no-preference block (the stylesheet test allows exactly one such block).
- W6-08: "Flights" tab versus "Flight history" title left as is: a test pins "Flight history" as the sidebar label and page title (the tab is its short form). Renaming that page is an owner naming choice.
- W6-05: the existing assertion that an odd refused value sets no cookie was changed to expect a cookie that holds the session marker and none of the text (the marker is what lets the error show once).

## Tests run

Per commit: ruff, mypy, `check_comment_history`, `check_function_size`, `stub-server/test_phase47_freeze.py` (all green), the render snapshot regenerated, and the core set (test_device_routes, test_page_structure, test_companion_app_02/03/04, test_components_page, test_stylesheet_structure, test_stylesheet_load_order, test_sign_in_surfaces, test_suite_guards: 715 passed at HEAD) plus the files of each area: more sheet, more panel, theme switch, French fit, home state card, quiet hours modal, display time zone, one toast one sheet, motion sheets, navigation assist, home recent tiles, flights cards and search, credits, users pages and cards and rows, pairing (every file mentioning pair_code, refused=1 or pair-frame: 327 passed), nav spaces and roles, page opening, console, airline table, editor, sheet and collection (432 passed), toasts, style leave and leave dialog pages, tab pill, motion and live motion, view pages 02-04, every browser test mentioning backdrop, scrim or lightbox, every browser test mentioning details, row-menu or health-row. Known load flake: `test_browser_ux_02.py::test_the_live_preview_crossfade_settles_correct_through_its_own_listener` failed once in a long parallel run and passed twice alone (also noted in lot F). The new and modified browser tests were run 4 times in parallel processes: 4 x 42 passed, 0 failures. The full suite was not run locally (cadence).

## File sizes

`companion/app.py` untouched (1493); `motion.js`, `modal.js`, `list-filter.js`, `toast.js` stay under 1500 lines. New module `companion/artwork_airline.py` (about 45 lines).

## Self-Check: PASSED
