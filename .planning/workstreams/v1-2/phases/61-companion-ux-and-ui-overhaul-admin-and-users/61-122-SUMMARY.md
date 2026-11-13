# Phase 61 Plan 122: More panel, Console card and redesign Summary

**The phone More panel now has a grab handle, an account row with the person's initial, for an administrator a tinted Console card, a Settings group (Theme, Language) and a full-width soft Sign out button; while it is open the root's paint and the status-bar tint follow the scrim on every page.**

Owner decisions of Round 27 (no PLAN.md, the orchestrator's brief was the plan). `origin/main` was not ahead, so no merge was needed.

## Commits

- `ebc74fe6` feat(61-122): Console card for administrators in the More panel
- `b5a4538b` feat(61-122): account row with the person's initial and a grab handle
- `8935b5c7` feat(61-122): Settings group and a soft Sign out button in the More panel
- `cc8347fb` fix(61-122): dim the root and the status-bar tint with the open More sheet on every page

Step 4 (update the tests that pinned the old panel) was done inside each commit, because only green states are committed.

## What changed

- **Catalogue.** New `ui_components.link_card_html` (tinted card, accent border, accent icon tile, title, optional subtitle that wraps, accent chevron), listed in the Components page "cards" family (two states, EN/FR) and covered by `test_components_page.py`'s catalogue test. The Settings group is the existing `ui_groups.group` and `ui_groups.row` (no new component), restyled inside the panel.
- **Console card.** The space-switch row is that card: same `tab-bar__space-link` class, aria-label and target. Subtitle "Fleet, users, audit" / "Flotte, utilisateurs, audit" (new `nav.console_subtitle`). In the Console space the card leads back to "My frame" with no subtitle. A person who is not an administrator has no card.
- **Account row and grab.** Initial circle (44px; a person glyph when no e-mail), name over e-mail (ellipsis), chevron, 64px. Grab handle is the panel's first child, also on the Account page.
- **Settings and Sign out.** Uppercase "Settings"/"Réglages" label (`nav.settings`), bordered group, rows of 56px with a glyph (sun, globe), label left, segmented control right (360px FR: Auto/Clair/Sombre whole). Sign out is a 48px full-width button tinted with the existing error token, with a new sign-out glyph. Two new glyphs (`icon-globe`, `icon-sign-out`): ICON_IDS 52 to 54.
- **Root dim and status-bar tint (owner follow-up).** While `.tab-bar__more[open]`: `html` paints the scrim colour over its ground, `body` paints the sky gradient itself so the scrim still dims it once (no double dim in the window); Location's root is the map placeholder colour and gets the dim alone (`style-place.css`). `modal.js` (the file that already closes the sheet) sets every `theme-color` meta to the page ground under the same 55% dim on open and restores the originals on close. No new `backdrop-filter`; no transition (reduced motion unaffected). The closed-state top-edge work and the 61-121 lead/tail layers are untouched.

## Tests

New `companion/test_browser_more_panel_redesign.py` (47 cases, seen red first: 11 of 13 red for the card, 16 of 17 for the handle and account row, all for the Settings group): admin and non-admin, 360/390, EN/FR, light/dark; geometry, colours against tokens, whole text, hit-testing, links and forms. Extended `test_browser_more_scrim_cover.py` to nine pages (Home, Flights, Airlines, Style, Location, Account, Fleet, Users, Audit) and added 72 cases (red first, 72 of 72) for the root dim, the `theme-color` change and restore, 360/390, EN/FR, light/dark.

Updated in place: `test_browser_more_sheet` (order, e-mail, language label), `test_browser_space_switch`, `test_browser_tab_bar_roles`, `test_browser_update`, `test_companion_app_01` (sprite counts), `test_sign_in_surfaces` (shell and error-page digests, deliberately), render baseline (regenerated).

Run (cadence): ruff, mypy, `check_comment_history`, `check_function_size`, `test_phase47_freeze` (21 passed), `test_stylesheet_structure`, `test_stylesheet_load_order`, `test_components_page`, `test_browser_ux_02`, `test_render_baseline`, `test_page_scripts`, `test_i18n`, `test_suite_guards`, `test_shell_meta`, `test_ui_modal`, `test_browser_foundations`, `test_browser_status_bar_band`, `test_companion_app_03`, `test_browser_place_document_map`, `test_browser_location_full_bleed`, `test_browser_web_app_bar`, `test_browser_page_opening`, `test_browser_components_page`, `test_brand_logo`, `test_battery_charging`, `test_companion_app_04`, `test_flights_fragment`, plus every test file that mentions the panel's classes or the bar (see report). Not run: `run-all-tests.sh`.

## Verified headlessly / only an iPhone can confirm

Verified headless: all markup, geometry, colours, 44px targets, text fit at 360 FR, the scrim topmost at y=2 and innerHeight-2 (safe areas forced to 59px/34px, iPhone flag on), the root background gaining the dim layer and returning, `theme-color` equal to the dimmed ground (within 2 per channel) on open and exactly restored on close, on all nine pages.

Only a device can confirm: that iOS actually paints the root's dim in the zones under the status bar and the Safari bottom toolbar, and that iOS 26 re-samples the tint from the changed `theme-color` (or from the dimmed edge) while the sheet is open. Headless Chromium has no safe area and no Safari chrome. If a strip is still seen, the cause is outside the root's paint (the browser's own chrome tint); the next lever would be the tint alone.

## Deviations

- **Rule 3, stash.** I ran `git stash` once by mistake while investigating a test failure, then `git stash pop` straight away; the stash list was empty before, the working tree was restored in full and nothing was lost.
- Step 4 was spread over the three feature commits (green-only commits).
- `.tab-bar__nav-icon`, the old `.tab-bar__space-link` row styles, the `.tab-bar__links` separators and the `::after` e-mail were removed; `data-email` is no longer emitted (the e-mail is real text).
- The Console-space card has no subtitle (the owner's text is only for Console).

## Screenshots (360px FR, panel open)

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/plus-console/shots/`: `panel-360-fr-light-admin.png`, `panel-360-fr-dark-admin.png`, `panel-360-fr-light-user.png`, `panel-360-fr-dark-user.png`.

## Self-Check: PASSED

Broad run over every test file that mentions the panel or the bar: all green after fixing the tests that pinned the old rows (nav lists, parity, theme switch, sweep, accent budget, sky background); the new and the scrim files passed 3 runs in a row.
