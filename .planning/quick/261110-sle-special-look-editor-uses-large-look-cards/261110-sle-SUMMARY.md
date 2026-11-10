---
phase: quick-261110-sle
plan: 01
subsystem: companion
tags: [personalisation, special-looks, look-cards]
key-files:
  modified:
    - companion/settings/rules.py
    - companion/settings/layout_picker.py
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/i18n_fr/look.py
    - companion/testdata/render_baseline.json
completed: 2026-11-10
---

# Quick 261110-sle: the special look editor uses the large look cards

The new and edit special look pages are one column: the "Applies to" summary, the "Look" section of large look cards (same markup and styles as Departures, Arrivals and Calendar, wrapping grid, selected card outlined with its check), then the docked Cancel/Save bar. The big left-hand preview and its "Edit special look / Matching flights will look like this." caption are gone; the selected card is the preview.

## What changed

- `rules.rule_form_html`: single column (`form-page--single`), no preview column, no look target attributes. Giant layouts show the five pairing cards (layout-aware previews, as in the Calendar view); the classic layout shows one card per theme the hardware offers (`layout_picker.theme_group_html`, same card markup).
- `theme-preview.js`: removed the three-choice-picker handling of the special look form; suggestion chips and the kind change handler remain, other pages untouched.
- `style.css`: removed the unused `form-page__preview/caption/name/sentence` rules.
- i18n: removed the unused "Matching flights will look like this." string (EN source and FR).
- Behaviour unchanged: stored non-pairing theme preselects its pairing without rewriting, rejected value not echoed, no-script posting, phone layout.
- Tests: served-HTML tests (cards, one checked, no big preview, classic themes, layout b five, stored green shows grey, bytes unchanged, rejected value, EN/FR) and browser tests updated (the title now asserts on the bar message); render baseline regenerated.

## Deviations

- The classic layout no longer shows the colour x style table and three-choice picker in the editor; it shows theme cards, as the owner specified ("classic: the 18 themes").
- Five existing tests asserted on the removed preview or table (`test_config_page_03/04b/05`, `test_companion_app_04`); updated to assert the new structure.
- The gsd-sdk has no quick-task handler; the STATE.md row was added by hand. ROADMAP.md untouched.

## Verification

ruff, mypy, function-size gate, comment-history guard all clean. Non-browser suite: 6506 passed, 3 skipped, exit 0. Browser files in four chunks (-n 4): 553, 1320, 514, 354 passed, all exit 0.
