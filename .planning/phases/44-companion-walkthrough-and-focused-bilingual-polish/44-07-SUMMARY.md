---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 07
subsystem: ui
tags: [companion, airlines, i18n, accessibility, browser-tests]
requires:
  - phase: 44-06
    provides: Flights picture action and the shared lightbox contract.
provides:
  - Airlines cards with one section per known aircraft type and a labelled native selector (script-enhanced, all types visible without script).
  - Separate "From SkyPane" and "Your changes" rows per type, with a visible add/replace-artwork action.
  - Framed drop surface with its hint inside the frame; outcome-first delete wording.
affects: [companion-airlines]
key-files:
  created:
    - companion/static/airline-types.js
  modified:
    - companion/pages/airlines_page.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/display.py
    - companion/static/style.css
    - companion/static_files.py
    - companion/ui_base.py
    - companion/ui_shell.py
    - companion/layout.py
    - companion/app.py
    - test-support/companion_render_snapshot.py
    - companion/testdata/render_baseline.json
    - companion/test_status_pages_05b.py
    - companion/test_status_pages_06.py
    - companion/test_companion_app_03.py
    - companion/test_browser_ux_01.py
    - companion/test_browser_ux_04.py
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-03
status: complete
---

# Phase 44 Plan 07: Airlines types and source-versus-owner clarity Summary

Every airline now exposes all of its known aircraft types (both Transavia France types, all four Air Caraibes ones) through a native selector, and each type separates what SkyPane ships from what the owner changed.

## Task Commits

1. Task 1 markup, French copy, script wiring, retargeted served tests: `7caeda40`
2. Task 2 styles and browser tests: `4ae32932`

## Accomplishments

- One section per type (`data-airline-type`, stable id: `any` or the fleet-variant shape). Airlines with more than one type get a labelled `<select>`; `airline-types.js` only toggles `hidden`. Without script the selector stays hidden and every section renders in source order with its own title. Single-type airlines show no selector, no title and no chips.
- Each section has a `From SkyPane` row (built-in artwork or none) and a `Your changes` row (no changes / your artwork shown instead / your artwork / no artwork yet, plus the "Resolved by hand" chip or "Built-in name used instead of yours" for a superseded entry), then a 44 px "Replace artwork" / "Add artwork" action reusing the existing lightbox trigger vocabulary and upload routes.
- Removed: the page description, the "<name> illustration" caption/alt, the bare "Superseded" badge, the framing-preview sentence. The drop frame now carries its hint inside the frame.
- Delete control reads "Delete my name" with "Flights with this prefix become unidentified again. Your artwork stays."; no new routes, fields or handlers.
- French catalogue updated; retired ids removed (including the now orphaned `display.delete`).

## Deviations from Plan

- [Rule 3] `airline-types.js` needed the usual script wiring (`static_files.py`, `ui_base.py`, `ui_shell.py` (15 scripts), `layout.py`, `app.py` page scripts, render snapshot route list); `test_companion_app_03` renamed to the fifteen-script contract.
- [Rule 1] Render baseline regenerated; `test_airlines_grid_renders_two_cards_per_row_at_390px` height ceiling raised from 3800 to 6600 px (measured about 6200 with the richer cards; the two-per-row and equal-column checks are unchanged).
- Retired tests (type chips, superseded badge, one-trigger-per-airline counts, illustration caption) were retargeted to the new contracts; no skips added.
- A type with no artwork file renders a placeholder and the add-artwork upload path; the airline-level section does the same, which is a small improvement over a broken image.

## Known Stubs

None.

## Threat Flags

None. Artwork actions reuse the existing authenticated upload/delete routes; all rendered names and labels are escaped once.

## Self-Check: PASSED
