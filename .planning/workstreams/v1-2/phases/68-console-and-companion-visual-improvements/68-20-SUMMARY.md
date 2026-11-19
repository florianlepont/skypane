---
phase: 68-console-and-companion-visual-improvements
plan: 20
subsystem: companion
tags: [flights, css, accessibility, i18n]
requires: ["68-01", "68-08"]
provides:
  - "Flights rows per the owner-approved mockup (airline, route line with direction icon, time and age)"
affects: ["68-22"]
key-files:
  modified:
    - companion/pages/history_page.py
    - companion/static/style-flights.css
    - companion/static/style.css
    - companion/ui_base.py
    - companion/i18n_fr/flights.py
decisions:
  - "Direction is an aria-hidden icon plus a visually hidden word; other states (overhead) are only spoken."
  - "The desktop table is led by the thumbnail link (the row's picture control); the State column and the View picture button are gone."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 20: Flights history rows Summary

Flights phone rows and the desktop table follow the approved mockup: thumbnail, airline over one route line (arrow-over-runway icon, two codes, chevron), time over age; aircraft type only in the desktop table.

## What was built

- Phone row: 56x36 thumbnail (44px-tall target), airline, route line with `icon-departure` / `icon-arrival` (new symbols in `ui_base.py`), time (bold) over age. No "Departing/Arriving" visible text; the word stays as `visually-hidden` text. A row with no route shows only the direction on the phone (unchanged rule) and "Route unavailable" in the desktop table.
- Desktop table: columns Picture (72x46 thumbnail link, `aria-label` "View picture of ...") / Flight (airline over call sign) / Route / Aircraft / When. The header row stays for screen readers but is not drawn (as in the mockup). Day separators are unchanged.
- i18n: `flights.aircraft` ("Avion") added; `flights.state` and `flights.view_picture` removed with their French.
- D-05: the header already kept search and title on one row at 320, 360, 480, 768 and 1280 px in both languages; a width-sweep browser test now pins it (no CSS change was needed).
- Thumbnail rule (90 s before, 10 s after), stand-ins, query, cache and fragment contract untouched.

## Commits

- 65569452 feat(68-20): rows and desktop table
- ed0b92c9 test(68-20): header width sweep

## Captures (scratchpad p20)

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p20/`: `before_{ph,dk}_{en,fr}_{light,dark}.png`, `after_*` (full app screen at 390 and 1280), `mock_*` (mockup), `cmp_{ph,dk}_{en,fr}_{light,dark}.png` (mockup left, built page right). Scripts: `shot.py`, `mock.py`, `cmp.py`, `seed.py`.

## Design-system divergences

- Mockup lists the call sign under the airline on desktop; this reverses the earlier "no visible call sign" rule for the desktop table only (phone rows still hide it). Mockup wins.
- Row title and time use `--weight-semibold` (600) where the mockup uses `<b>` (700), per the design-system type scale.
- The thumbnail corner radius is `--radius-chip` (9px); the mockup draws 10 and 12px.
- Rows use `--space-3xl + --space-xs` (68px) as the fixed card height token expression; mockup min-height is 68px.
- The chevron between codes is a CSS-drawn corner, not an SVG, to keep each row's markup small (see below).
- Long airline names are cut with an ellipsis on one line (mockup behaviour) instead of wrapping to two lines.
- Flights day-label rows stay inside the desktop table (the mockup draws the label above a card); not part of this plan.
- Unchanged by the owner decision: search, All/Departures/Arrivals filter and sort.

## Deviations from Plan

1. **[Rule 3] style.css edited.** The plan says no edit to `style.css`, but `test_stylesheet_structure` forbids one selector declared in two rules across sheets. The Flights-only table rules (`col-*` widths, cell padding, `td` height, `.history-card .row__label`) moved from `style.css` to `style-flights.css`.
2. **Load-more weight test relaxed (0.75 to 0.85).** `test_load_more_downloads_only_the_next_flights` compares the fragment to the whole page; rows now carry a thumbnail in the table too (baseline 88 KB per 50 rows, now about 127 KB), so the ratio rose from 0.73 to about 0.80.
3. Existing tests updated for the new markup (no State column, no View picture button text, thumbnail 56x36, call sign visible on desktop only, icon-and-hidden-word direction).

## Gates

ruff, mypy, `check_comment_history.py check`, function size (max 80), app.py 1490 lines, history_page.py 1122. Focused run (flights, view/status pages, page_styles, stylesheet_structure, i18n, structure and suite guards, overhaul sweep, audit/ux browser tests, contrast): all pass after two test fixes. `test_render_baseline.py` differs on every page (stylesheet hashes, icon defs, and earlier plans); not regenerated, plan 22 does that. `/flights` differences are mine.

## Self-Check: PASSED
