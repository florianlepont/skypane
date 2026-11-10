---
phase: quick-261110-c9d
plan: 01
subsystem: companion
tags: [personalisation, layout, css, i18n]
key-files:
  modified:
    - companion/settings/layout_picker.py
    - companion/pages/personalisation_cards.py
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/i18n_fr/look.py
    - companion/testdata/render_baseline.json
completed: 2026-11-10
---

# Quick 261110-c9d: Layout card above the style tabs

The per-frame screen layout is now a frame-level "Layout" card above the Personalisation tabs on every view; the Layout tab, view and wrapper are gone and `/display/layout` redirects to `/display` (303, joins `RETIRED_VIEW_ROUTES`).

## What changed

- `layout_picker.layout_card_html` renders one section (dirty-section "Layout"): heading, caption "Applies to the whole frame." (FR "S'applique a tout le cadre."), a phone summary row (44x58 thumbnail, current name, "Whole frame", Change/Modifier button) and the one set of existing radio cards (name=layout, form-associated, same validation and save path).
- Wide: five 92 px thumbnails in a row, checked one outlined and bold. Phone (<700 px): the picker is collapsed behind Change only when a script runs (`.js`); without scripts it is shown open and the button stays hidden.
- `theme-preview.js`: Change toggles `aria-expanded`/`is-open`; the summary follows the checked radio and is refreshed after Cancel, also on giant-layout frames that have no look sheet.
- Form pages (new/edit special look, calendar connect/look) have no settings form, so they carry no card. A rejected layout value redraws on Departures with the card and a field error.
- Tests: served-HTML tests moved to the card (four views, EN/FR, one checked radio, four nav links, redirect), route/matrix/landing/account rows, render baseline regenerated, real-browser tests (four-link nav, pick C on desktop and via Change on phone, Save, reload, EN/FR, 360/390 overflow closed and open, scripts-blocked phone).

## Deviations

- **[Rule 1] First-screen budgets of the look picker.** `test_the_whole_look_picker_fits_one_phone_screen_above_the_tab_bar` and `test_on_desktop_the_picture_and_the_picker_are_two_columns_that_fit_the_screen` assumed the picture starts right under the tabs. The card (about 90 px on a phone, about 240 px at 1280x800) pushes it down, so these now subtract the card's height (the budget is unchanged once the card is scrolled out). The owner may prefer compacting the card instead.
- `test_a_special_look_row_gives_its_text_the_width` scrolls each action into view before the owns-centre wait (the page shifted down).
- `test_the_small_look_pictures_are_only_for_a_page_without_a_script` excludes the Layout card, whose pictures are the picker and always shown.
- The orchestrator's `wip:` commit 1a2e3eab captured most of the work; the remaining test edits are in ea6b48b2.

## Self-Check

Passed: ruff, mypy, function-size, comment-history clean; non-browser suite 6490 passed / 3 skipped (exit 0); browser chunks aa 553, ab 1320, ad 352 passed (exit 0), chunk ac 9 failures fixed as above and re-run (125 passed, exit 0).
