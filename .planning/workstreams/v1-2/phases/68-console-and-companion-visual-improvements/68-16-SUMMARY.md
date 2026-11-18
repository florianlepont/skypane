---
phase: 68-console-and-companion-visual-improvements
plan: 16
subsystem: companion
tags: [update, firmware, versions, dialog, i18n, golden]
requires: ["68-01", "68-04"]
provides:
  - Device and version card, flat Versions list and release notes as in the approved Update mockup (R16)
  - Install and Roll back question as a dialog (card on desktop, bottom sheet on phone), same card as a page without script (R17)
affects: ["68-22", "68-32"]
key-files:
  created:
    - companion/static/update-question.js
  modified:
    - companion/pages/update_page.py
    - companion/static/style-admin.css
    - companion/static/style.css
    - companion/static/style-c-console.css
    - companion/i18n_fr/update.py
    - companion/i18n_fr/admin_fleet.py
    - companion/console_fleet_view.py
    - companion/app.py
    - companion/static_files.py
    - companion/ui_base.py
    - companion/ui_shell.py
    - companion/layout.py
    - companion/testdata/update_page_one_type_golden.json
requirements: [CON-01]
decisions:
  - "The OWNER-APPROVED block of 68-MOCKUP-update.html replaced the plan wording: Install on the right of the card (full width on a phone), no 'On the frame' footer, notes cut at two lines, dialog on desktop and bottom sheet on a phone, the page replaces the markup of the standalone /update."
  - "The new module update_versions.py was not needed: update_page.py is 879 lines."
  - "The question dialog lives in its own script (update-question.js), not in confirm-submit.js, because the console pages are tested to ship no native confirm() and the calendar form still uses it."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 16: Update panel and install confirmation (R16, R17) Summary

The Device and version block of the Fleet page and the standalone `/update` page now share one set of builders and follow the approved mockup: one card per state (up to date, update available, scheduled, installing, failed) with an icon headline, the version in monospace, the release age, the release note cut at two lines and the one action on the right (full width under the text on a phone); under it a Versions label and one card of flat rows (status dot, monospace version, Newest or Running chip, date and age, notes behind one native disclosure, a quiet underlined Roll back). A rollback notice is a bordered warning card above the update card. Install and Roll back ask once in the shared dialog (card from 700 px, bottom sheet below) built by the new `update-question.js`; accepting posts the form with `confirm=yes`. With scripts off the form posts without `confirm` and the server answers with the confirmation page, now one card with the question, what will happen and Cancel beside Install (Roll back, with its own wording and three new French sentences). Routes, form fields, the CSRF field and the two-step server gate are unchanged.

## What changed

- `update_page.py` (979 to 879 lines): `_cta_card_html` is the one card; `_history_row_html` and `_versions_card_html` the one list; `confirm_copy`, `release_flags` and the `data-question-*` attributes carry the question; the old summary, offer card, details rows, `_versions_group_html`, the hand-built `banner__pill` and the "On the frame" footer are gone (`pill_html` everywhere, D-14). The hardware line "For <type>" replaces the model line of the summary.
- `console_fleet_view.py`: `render_parts` no longer takes a model text (the id `admin_fleet.block_model` is removed); the frame page loads `update-question.js`; the System view does not (the shell stays under its script ceiling).
- `app.py` (1493 to 1490 lines): the install handler asks `update_page.release_flags()` for bench and rollback.
- CSS only in the `update-*` block of `style-admin.css`, plus the removal of the old update rules in `style.css` and `style-c-console.css`.
- French: six ids removed (on the frame, up to date, on the frame footer, last installed, released on, installed chip) plus the native confirm question; four rollback ids added.

## Design-system divergences

- The Device and version block of the Fleet page is no longer one glass group: its group is made transparent and the update card and the version list are the two cards of the approved mockup. The console rule "each block is one flat glass group, no card surface inside" (`test_browser_console_groups.py`) is kept for the other four blocks and lifted for this one (the test exempts `fleet-block--device`); this is a divergence from the Fleet block pattern, taken because the approved mockup shows two cards.
- The mockup's page frame (back link "Back to Salon", a page title "Versions") is not built on the Fleet page: the block sits under the Fleet header and its own "Device and version" label. The standalone `/update` keeps the nav-matching title "Releases" (shown "Versions" in French) and gains the "For <hardware>" line; no back link.
- Rows that have both notes and a Roll back action show the chevron beside the action and put the note count on its own line under the date ("Notes (1)"), because the mockup only draws rows with one or the other and the real data has both. Rows without an action show "Notes (n)" and the chevron on the right as in the mockup.
- The row date line keeps the real format (day, month, time, then age) instead of the mockup's "17 Nov · 2 d". The running row shows "Installed <date>".
- The Running chip is the accent fill (ivory in dark) as in the mockup, drawn with a rule on the catalogue pill inside the `update-*` block; the Newest chip is the `ok` tone pill.
- The card headline icon is the existing `icon-upload` (the mockup draws a download arrow); no new icon was added.
- The question dialog heading is the 22 px heading token (the mockup uses 20 px), and Cancel is on the left of the primary at every width (the mockup's order), overriding the dialog's usual stacking on a phone for this dialog only.
- The old "Last installed <date>" and "Released <date>" lines of an opened row, and the "On the frame" footer, are gone. A running bench build is named only by the up-to-date card; while an update is on offer, scheduled or installing, the card no longer names it (the footer was its only place).
- The install confirmation with script is the dialog and posts `confirm=yes` directly (one question instead of the native confirm plus the server page); without script the server page is the question. The server still requires the exact `confirm=yes`.

## Golden

`companion/testdata/update_page_one_type_golden.json` was regenerated once from `one_type_golden_pages()` with a throwaway script kept in the scratchpad (not committed). Scope: all 14 existing page captures changed (the card, the rows and the confirmation page; both languages) and two keys were added (`confirm_rollback.en`, `confirm_rollback.fr`). The rule is now "identical to the newly approved render". `render_baseline.json` was not touched.

## Visual check

Mockup and real page were rendered with Playwright at 390 and 1280 px, English and French, light and dark (scratchpad `p16/`: `cmp_*`, `page_*`, `dlg_*`, `nojs_*`, `sa_*`, `rb_*`, `sched_ph.png`, `zoom_*`) and compared by eye: card, list, rollback notice, scheduled state, dialog (card and sheet) and the no-script page. Chips and buttons were measured and viewed at 3x: button text is centred in 44 px boxes; the 22 px chips centre their text within one pixel of font metrics. The icon buttons rule does not apply (no round icon button on this page). The phone layout follows the mockup's: card with a full-width button, then the list.

## Verification

- `SKYPANE_REQUIRE_BROWSER=1` pytest: `test_update_page`, `_non_live`, `test_update_actions`, `test_browser_update`, `test_browser_firmware_panel`, `test_browser_fleet_sections`, `test_browser_console`, `test_browser_console_groups`, `test_browser_overhaul_sweep` (fleet), `test_browser_fleet_page`, status/view pages, page styles and scripts, stylesheet structure, structure and suite guards, i18n, access matrix, csrf, contrast: all pass except the items below.
- ruff, `check_comment_history.py`, `check_function_size.py check --max 80 server stub-server` pass. `app.py` 1490 lines; no JS file near 1500 (`update-question.js` 88 lines). mypy: 13 existing errors (PIL stubs), none in touched files.
- `test_browser_console_groups.py::test_console_tables_have_the_quiet_header_and_tall_rows` fails 4 times on the airlines table header size (13 px against 12 px); it fails the same way before this plan (checked on `dfe338d0`), caused by plan 14.
- Render baseline: `test_rendered_pages_match_the_baseline` was already failing (plan 14, `/airlines`); 68 of 76 captures differ, including `/fleet`, `/fleet?flash=saved`, `/fleet?view=system` and the `/` pages. Not regenerated (plan 22).

## Deviations from Plan

- New script `update-question.js` and its registration (`static_files.py`, `ui_base.py`, `ui_shell.py`, `layout.py`) instead of changing `confirm-submit.js` [Rule 3: `test_console_pages_ship_no_confirm_and_dialogs_only_where_planned` forbids `confirm(` in console scripts].
- `console_fleet_view.py`, `app.py` and four registration files were touched although not in `files_modified` (needed for the above and for the model line).
- `test_browser_fleet_sections.py`, `test_browser_console_groups.py` and `test_companion_app_03.py` (script count 26 to 27) were updated for the new markup.
- `update_versions.py` was not created (not needed).

## Known Stubs

None.

## Self-Check: PASSED
