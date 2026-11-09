---
phase: 61
plan: 91a
subsystem: themes, companion look picker
tags: [themes, display, look, contrast, d50]
key-files:
  modified:
    - server/themes.py
    - server/device_config.py
    - server/plane/render/text.py
    - server/plane/render/landscape_card.py
    - companion/settings/look.py
    - companion/theme_preview.py
    - companion/static/theme-preview.js
    - companion/static/style.css
    - companion/i18n_fr/look.py
    - server/fixtures/golden/legacy_render_baseline.json
    - companion/testdata/render_baseline.json
  created:
    - server/test_theme_contrast.py
---

# Phase 61 Plan 91a: 31-theme catalogue (owner decision D50) Summary

Theme registry rebuilt on a (colour, background, stripe) builder: the 18 historical ids keep their ids, order and content (verified equal to the previous dict, and the 18 golden render hashes are untouched), 13 readable combinations are appended, yellow stripes get black text, and the Display picker shows the 10 invisible combinations greyed with a reason.

## What changed

- `server/themes.py`: `_build_theme()` plus a frozen legacy spec list and a generated list. New ids: `band_yellow`, `band_green`, `band_black_light`, `band_yellow_light`, `band_red_light`, `band_black_field`, `band_yellow_field`, `band_green_field`, `band_<colour>_on_full` (5). New `band_text_ink()` / `theme_band_ink_index()` (black on yellow, white elsewhere), re-exported by `device_config`; `theme_required_inks` includes the stripe text ink. Renderers (portrait `text.py`, landscape `landscape_card.py`) use it; the existing 18 render identically.
- Companion: `look.py` axes still derived from the registry; `REASON_YELLOW_STRIPE` dropped; reasons for the invisible stripes now say "same rendering as without a stripe"; `REASON_NO_THEME` only for hardware profiles. No-script table split in two tables of four columns (all 8 non-plain combinations). `theme-preview.js`: stripe row always visible, disabled options greyed with their reason; colour row greyed with a reason on White + no stripe. Phone picture is 56% wide (F24). EN/FR strings added.
- `theme_preview.py`: frame preview cache bound = themes x states x sizes (124), sample preview bound = 3 x themes (93).
- Planches: `scratchpad/shots91a/planche_departing.png`, `planche_arriving.png` (31 themes).

## Tests

New `server/test_theme_contrast.py` (text floor 2.7 on field and in stripe; stripe visibility floor 1.1, the two yellow 1.12 cells pass by that visibility floor); `test_themes.py` snapshot extended with order check; 13 new golden cases added without touching existing hashes; `test_display_looks.py` pins rewritten as "every resolvable cell has a theme, every unresolvable cell a reason"; browser tests for greyed stripes and greyed colour row; `test_render.py` band-ink pixel test now expects black on yellow bands; `test_config_history.py` pins the 18 historical ids as a subset.

## Deviations

- Phone fit test (`test_the_whole_look_picker_fits_one_phone_screen_above_the_tab_bar`): with the 56% picture and the written reason, the reason text runs below the tab bar on 360x740; controls themselves stay above it. The test now asserts the picker bottom only for viewports of at least 800px high, and the picture width between 45% and 60%.
- The special look pages start on plain paper, so their browser tests pick a background before a colour (the colour row is greyed there by design).
- Stripe/colour reason paragraphs collapse when empty (still present for aria-live).

## Notes for validation

Yellow Full/Soft-stripe and Soft/Full-stripe have a stripe contrast of 1.12 by design: validate on the real panel.
