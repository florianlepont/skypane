---
quick_id: 261003-dpf
slug: display-preview-first
date: 2026-10-03
branch: claude/display-preview-first
commits: [a4af4aa7, f5dfe835, 9f146d79, 8a7c3ce3, 58fd8e0d]
key-files:
  created:
    - companion/settings/look.py
    - companion/i18n_fr/look.py
    - companion/test_display_looks.py
    - companion/test_browser_display_looks.py
  modified:
    - companion/theme_preview.py
    - companion/app.py
    - companion/routes.py
    - companion/settings/theme.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/pages/config_page.py
    - companion/static/theme-preview.js
    - companion/static/style.css
    - companion/ui_base.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/registry.py
    - companion/i18n_fr/rules.py
    - companion/testdata/render_baseline.json
---

# Quick 261003-dpf: Display look card, Direction A "Preview-first"

The Display page's appearance card is now the approved Direction A mockup:
two large framed live pictures are the page, and the look is set through
three choices that always land on one of the 18 real themes.

## What shipped

- **Look model** (`companion/settings/look.py`): every registry theme read
  as Colour (black, yellow, red, green, blue) x Background (Paper, Full,
  Soft) x Diagonal stripe (None, Solid, Soft), derived from
  `server.themes.THEMES`, never a hand-written table. The 18 themes are 18
  distinct cells; plain paper fills its cell under every colour. Every other
  combination is a gap with a reason: a stripe on a full background, a soft
  stripe on a soft background, any yellow stripe (white text on yellow), or
  "the frame has no theme for this combination yet" (black soft stripe,
  black stripe on soft, red soft stripe, green solid stripe, green stripe
  on soft).
- **Full-frame preview route** `/frame-preview/{theme}.png?state=departing|arriving&size=large|small`:
  authenticated, theme/state/size validated against allow-lists (404
  otherwise), the whole `build_canvas()` canvas box-reduced (600x800 or
  120x160; a box filter averages the dither into its visible tint and keeps
  PNGs at ~50-150 KB), disk-cached per variant in its own bounded directory
  (`frame_previews/`, 96 files), `private, max-age=300`. The arriving variant
  mirrors the fixture (VY1523 arriving, AF1789 as the previous card).
- **Look card**: heading, caption and a "Previews use a sample flight" pill;
  the Departures and Arrivals pictures in a dark bezel with their read-back
  ("Red, stripe on soft", or "Same as departures") and a "Change" pill; the
  Special looks column beside them from 1200 px, below them under that.
- **Look sheet** (script only, `hidden` in the HTML): opened by clicking a
  picture or its "Change" control; a labelled modal dialog anchored beside
  the picture (a bottom sheet over a dimmed page under 700 px), with a
  "Same as departures" switch for Arrivals and Calendar flights, five colour
  dots, Background and Diagonal stripe segments, Reset and Done. Each choice
  checks the matching real theme radio and fires `change`, so the picture
  swaps live and the dirty bar counts it. Stripe options with no theme are
  disabled (struck through, skipped by arrow keys) and the reason is written
  under them in an `aria-live` line. Focus trap, Escape, scrim click and
  Done close it and return focus to the opener.
- **Special looks**: the calendar row (mini render, CALENDAR tag, read-back,
  connection verdict, "Change" chevron, and its connection block in a
  "Calendar connection" disclosure), one row per rule (mini render, kind
  tag, airline name for a known prefix, key, read-back, Remove), and "Add a
  special look". With scripts the add form is a dialog: Applies to
  (Flight / Aircraft / Airline), the key with recent suggestions per kind
  (callsigns, aircraft hex, airline prefixes with their names), the three
  choices, a mini render and "Add special look". The precedence line reads
  "Most specific wins: calendar, then flight, aircraft, airline."
- **No-script floor**: every look (Departures, Arrivals, Calendar flights,
  New special look) has a `<details>` holding a colour x style table of
  native radios, one per real theme id (plain paper above the table, "Same
  as departures" first where it applies), each gap marked with a footnote
  number and its reason listed under the table. The tables post the
  unchanged `theme` / `theme_arriving` / `calendar_theme_id` fields through
  the settings form, and `rule_kind` / `rule_key` / `rule_theme_id` to
  `/settings/rules/add`. On phones the colour names become ink dots so the
  table fits 360 px without scrolling.
- **Strict CSP kept**: no `style=""` anywhere in the card; colours are SVG
  presentation attributes from `PALETTE_RGB`. New tokens
  `--color-frame-bezel(-hi)` and `--shadow-pop` per theme; the look card's
  `:has()` rules live in the file's one `@supports` block.
- **i18n**: a new `look` French catalogue (look sheet, table, special looks)
  plus reworded `display.aspect` ("How your frame looks" / "L’allure de
  votre cadre"), `display.match_by` and `display.add_rule`. Registry theme
  names and the retired accordion/live-preview strings were removed in both
  languages.
- Quiet hours and Runway are unchanged.

## Tests

- New `companion/test_display_looks.py` (42): the 18 themes as distinct
  cells, every gap's reason, the served sheet model in EN/FR, the served
  no-script radios for all 18 ids per look, no style attribute or inline
  script in the card, the sheet as a hidden labelled dialog with
  script-only controls, EN/FR wording, each picture's state, a real HTTP
  save of each of the 18 themes for all three looks, the clear signal and
  refusal of an unknown id, a special look posted through the rules route,
  and the preview route (sizes, states, 404s, auth, cache).
- New `companion/test_browser_display_looks.py` (9): picture opens the
  sheet beside it and choices swap the picture live, disabled combinations
  with their reason, focus trap / Escape / return focus / Reset, save bar
  persisting departures, an arrivals override and "Same as departures",
  the add dialog posting a rule, phone bottom sheet with 44 px choices and
  no overflow at 390 and 360, and the 1280 layout in EN and FR.
- Retargeted, never skipped: the accordion/chip/palette checks in
  `test_config_page_01/03/04/04b/05`, `test_companion_app_01/03/04`,
  `test_route_table`, and `test_browser_ux_01/02/03/04` now assert the same
  behaviours on the look card (registry coverage, defaults, swatch facts,
  selection treatment, saved marker, rules list order and copy, calendar
  placement, no-script save, cancel restore, keyboard, hit targets, image
  boxes held before load, no overflow).
- `companion/testdata/render_baseline.json` regenerated after checking the
  diff: every page differs only by the three new sprite symbols, Display
  additionally only inside `<section id="display-look">`, and the
  unauthenticated set only gains `GET /frame-preview/white.png` (303 to
  login).

## Deviations

1. **Pictures use the fixed sample scene**, not "your last flight": a
   `runway_events` row has no city or IATA flight number, so a live
   full-frame render would show an incomplete card. The pill says "Previews
   use a sample flight".
2. **Quiet hours and Runway stay full sections** as before (the mockup
   showed them as collapsed link rows); their logic and markup are
   untouched, as asked.
3. **Picking a colour on plain paper switches the background to Full**, so
   the click visibly does something (plain paper has no colour).
4. **Soft swatches are translucent ink over paper** rather than a stipple
   pattern, which moired at swatch size.
5. **Rule rows keep Remove only** (no edit chevron): re-adding a key already
   replaces its look, as the precedence line says.
6. The live preview no longer crossfades or previews on hover; the picture
   swaps when a look is chosen. The old `/theme-preview/` crop route stays
   (still served and tested) but the page no longer uses it.
7. The "Same as departures" control in the sheet is a `role="switch"`
   button, so the page still has no checkbox-based override.

## Verification

- Full suite after the baseline regeneration, `SKYPANE_REQUIRE_BROWSER=1`:
  3661 passed, 8 skipped (the same 8 as on main), coverage 95.24% (floor
  93%).
- ruff, mypy, `check_comment_history.py check`, `check_function_size.py
  check --max 80 server stub-server`: all clean.
- Screenshots (not in the repo): 1280 and 390 px, light and dark, EN and
  FR, default / sheet on Departures / sheet on Arrivals with disabled
  stripes / adding a special look / special looks list / no-script, with
  every disclosure open.

## Self-Check: PASSED

All five commits exist on the branch; every created file is present.
