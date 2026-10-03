---
quick_id: 261003-dpf
slug: display-preview-first
date: 2026-10-03
branch: claude/display-preview-first
---

# Quick 261003-dpf: Display page look configuration, Direction A "Preview-first"

## Goal

Rebuild the Display page's appearance card after the approved Direction A
mockup (`scratchpad/sketches-display/display-A*.png`): two large framed live
previews (Departures, Arrivals) are the page. Tapping one opens a popover
(a bottom sheet on phones) with three independent choices (Colour,
Background Paper/Full/Soft, Diagonal stripe None/Solid/Soft) that updates
the big picture live. Calendar flights and per-flight rules become a
"Special looks" list with mini renders and an "Add a special look" dialog
(Applies to Airline/Flight/Aircraft, value with recent suggestions, the
same look controls). Quiet hours and Runway are untouched.

## Hard constraints

- The three choices always resolve to one of the 18 real theme ids. The
  axes are derived from the registry (`server.themes.THEMES`), never a
  hand-written list. Cells with no theme are shown disabled with a reason.
- The POST contract is unchanged: `theme`, `theme_arriving` (empty = same
  as departures), `calendar_theme_id` (empty = same as departures),
  `/settings/rules/add` with `rule_kind`, `rule_key`, `rule_theme_id`.
  `handle_post()` validation stays the source of truth.
- No-JS floor: every look is a native radio table (colour x style, all 18
  ids) inside a `<details>`, posting through the existing settings form.
  Popover, live swap and click-the-picture are progressive enhancement.
- Faithful previews: a new authenticated full-frame route
  `/frame-preview/{theme}.png?state=departing|arriving&size=large|small`,
  rendered by `build_canvas()`, validated against allow-lists, disk-cached
  like `/theme-preview/`.
- No `style=""` in new markup (SVG presentation attributes only), strict
  keyboard support (focus trap, Escape, return focus, aria-labelledby,
  44 px targets), EN and FR, dark theme, dirty-save bar.

## Tasks

1. **Frame preview route** (`companion/theme_preview.py`, `companion/app.py`,
   `companion/routes.py`): full-canvas render per state and size, cache
   keyed by theme/state/size/live event, separate bounded cache dir;
   tests for validation, caching, auth.
2. **Look model** (`companion/settings/look.py`): registry-derived axes,
   resolver, gap reasons; the colour x style radio table renderer.
3. **Markup** (`companion/settings/theme.py`, `calendar.py`, `rules.py`,
   `companion/pages/config_page.py`, `companion/i18n_fr/`): the preview
   card, special looks list, add dialog, shared look sheet; EN/FR strings.
4. **Script and styles** (`companion/static/look-picker.js` replacing
   `theme-preview.js`, `companion/static/style.css`).
5. **Tests**: retarget the old accordion/chip-grid tests; new behaviour
   and browser tests; regenerate `companion/testdata/render_baseline.json`
   after inspecting the diff.
6. Visual verification (scratchpad `shots-dpf/`), full suite, ruff, mypy,
   comment-history and function-size gates; push.
