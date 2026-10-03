---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 06
subsystem: ui
tags: [companion, flights, i18n, accessibility, browser-tests]
requires:
  - phase: 44-05
    provides: Display swatches and Quiet hours.
provides:
  - Flights as a compact history (when, flight, route, direction) with one direct "View picture" link per row and card.
  - A real-link picture action that works without script and opens the shared lightbox when script runs.
  - Browser checks for keyboard, pointer, 390/360 px, English/French and scripts-blocked use.
affects: [companion-flights]
key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/static/style.css
    - companion/ui_time.py
    - companion/layout.py
    - companion/app.py
    - companion/ui_shell.py
    - companion/ui_base.py
    - companion/static_files.py
    - companion/i18n_fr/flights.py
    - companion/test_browser_ux_01.py
    - companion/test_browser_ux_02.py
    - companion/test_browser_ux_03.py
    - companion/test_view_pages_01.py
    - companion/test_view_pages_02.py
    - companion/test_view_pages_03.py
    - companion/testdata/render_baseline.json
  deleted:
    - companion/static/flight-rows.js
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-03
status: complete
---

# Phase 44 Plan 06: Flights direct picture action Summary

Flights now shows only what is needed to recognise a flight, and every row and phone card carries a labelled "View picture" link straight to the image.

## Task Commits

1. Task 1 markup, styles, scripts: `6d84d6b0`
2. Task 2 retargeted and new browser/served tests: `0f8a7eac`

## Accomplishments

- Removed the page description and visible freshness line, the corroboration column, the expandable hex/full-timestamp/runway details, the copy buttons and the card disclosure. The filter bar stays, relabelled "Filter flights" (hint about callsign/hex removed).
- The picture action is `<a href="/gallery/...">` with the existing `data-view-panel-*` contract, so `panel-lookup.js` still intercepts it for the lightbox and the no-script path serves the PNG. Its accessible name adds the flight ("View picture of AFR135"), and it has a 44 px tap floor.
- A flight older than every archived render falls back to the earliest render (`earliest_gallery_entry`), so every rendered flight has the action whenever the gallery holds anything.
- `flight-rows.js` had no remaining hooks, so the script, its route, shell constant and per-page entry were removed (the shell now has 14 scripts). The copy-button script is no longer loaded on Flights.
- Background refresh is preserved through `layout.refresh_marker_html()`: a hidden pill carrying `data-loaded-at` in the existing `.page-header__freshness` swap target, with no visible clock.
- French catalogue updated: new `flights.filter_flights`, `flights.picture`, `flights.view_picture_of`; retired ids removed.

## Deviations from Plan

- [Rule 3] `flight-rows.js` was deleted rather than adapted: nothing it served remained. This touched `companion/app.py`, `static_files.py`, `ui_base.py`, `ui_shell.py`, `layout.py`, `test-support/companion_render_snapshot.py` and `freshness.js` (comment) beyond the listed files.
- [Rule 1] Added `refresh_marker_html()` in `ui_time.py` (re-exported by `layout.py`) so removing the freshness line did not silently stop Flights' live list refresh (the plan requires refresh behaviour be preserved).
- [Rule 1] `style.css`: removed detail-row, row-toggle, clickable-row and card-disclosure rules; added `.history-card__action` and the picture link rule.
- Retired tests (row toggle, copy buttons, corroboration copy, detail row, flight-rows.js contract, collapsed-row focus, card disclosure tap) were deleted or rewritten as new-contract tests; no skips added. `test_browser_ux_02` disclosure sweep floor for `/flights` lowered to the shared tab-bar disclosure. Render baseline regenerated.
- The Flights summary is placed in `test_browser_ux_01.py`; `test_browser_ux_03.py` keeps the refresh check (retargeted to picture links surviving a swap).

## Known Stubs

None.

## Threat Flags

None. The picture link targets the existing session-gated `/gallery/` route; markup stays escaped and the script remains page-local.

## Self-Check: PASSED

Commits `6d84d6b0`, `0f8a7eac` present; full suite, ruff, mypy, comment-history and function-size gates green (see final report).
