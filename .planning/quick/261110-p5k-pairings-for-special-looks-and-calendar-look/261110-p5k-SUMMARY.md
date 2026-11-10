---
phase: quick-261110-p5k
plan: 01
subsystem: companion
tags: [personalisation, pairings, special-looks, calendar, i18n]
key-files:
  modified:
    - companion/settings/layout_picker.py
    - companion/settings/rules.py
    - companion/settings/calendar.py
    - companion/settings/theme.py
    - companion/pages/config_page.py
    - companion/pages/personalisation_cards.py
    - companion/static/theme-preview.js
    - companion/testdata/render_baseline.json
  created:
    - companion/test_browser_personalisation_pairings.py
completed: 2026-11-10
---

# Quick 261110-p5k: five pairings for special looks and the Calendar look

On a frame using a giant layout (a, b, c, a_diagonal) the special look form (new and edit) and the Calendar look page offer the five pairing cards instead of the 18 themes; a classic frame keeps the 18 themes.

## What changed

- `layout_picker`: form-optional pairing cards, `pairing_group_html`, `calendar_look_html`, `look_label`, `preview_layout`, `offers_pairings`, `frame_layout_id`. Pairing availability still comes from `look.offered_pairing_ids()` (hardware filter).
- Rule form: five cards, layout-aware picture and preview template; the picture follows the picked card. Classic keeps the table and three-choice picker.
- Calendar look page: "Same as departures" plus five cards posting `calendar_theme_id` to the settings form.
- Rows: special look rows and the calendar row name a giant-layout frame's look by its pairing (a stored `green` reads "Grey") and use layout-aware pictures; classic rows are unchanged.
- A stored non-pairing theme shows `pairing_for_theme(stored)` checked; a GET never rewrites it. Saving posts the pairing id, validated by the existing allow-lists; a bad value is rejected and not echoed.
- `theme-preview.js`: the rule form no longer assumes the three-choice picker exists (suggestion chips still work).
- No new strings (pairing names exist in EN/FR), no new custom properties, no render or device-config change.

## Deviations

- [Rule 1] Four existing tests assumed the 18-theme picker on a default-layout (B) frame; pinned to `layout="classic"` (`test_companion_app_05`, `test_config_page_03`, `test_display_looks`, `test_personalisation_special_looks`). `test_the_special_looks_and_calendar_pickers_still_offer_every_theme` was replaced by giant (five) and classic (eighteen) tests.
- Render baseline regenerated: only the `theme-preview.js` content hash changed.
- The gsd-sdk has no quick-task handler; the STATE.md row was added by hand. ROADMAP.md untouched.

## Verification

- ruff, mypy, function-size gate, comment-history guard: clean.
- Non-browser companion suite: 6506 passed, 3 skipped (root permission tests), exit 0.
- Browser files (108, four chunks, `-n 4`): 2741 passed, 0 failed, exit 0 for every chunk.
- New: served-HTML tests in `companion/test_personalisation_layout.py` (57 in the file now); 8 browser tests (pick, save, reload; EN/FR; 1280 and 390 px).

## Known Stubs

None.

## Self-Check: PASSED
