---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 02
subsystem: ui
tags: [companion, navigation, responsive, accessibility, i18n]
requires:
  - phase: 44-01
    provides: Walkthrough evidence and owner-approved navigation scope.
provides:
  - Destination-focused desktop and mobile navigation without repeated frame state.
  - A fully contained, keyboard-operable theme selector at 360 px and 390 px.
affects: [44-03, companion-navigation]
tech-stack:
  added: []
  patterns: [Native theme form retained across responsive navigation variants.]
key-files:
  created: []
  modified:
    - companion/ui_nav.py
    - companion/static/style.css
    - companion/test_browser_ux_02.py
    - companion/test_browser_update.py
key-decisions:
  - "Keep existing route names and paths pending the separate owner naming decision."
  - "Remove duplicate screen and quiet-hours state instead of introducing a new global status token."
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-01
status: complete
---

# Phase 44 Plan 02: Navigation Cleanup Summary

Navigation now contains destinations and preferences only. The screen and quiet-hours reminder was removed from both responsive variants, while the health alert, active-route semantics, language choice, and native theme form remain intact.

## Verification

- `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python3 -m pytest -n 0 -q companion/test_browser_ux_02.py companion/test_browser_update.py companion/test_stylesheet_structure.py` — 62 passed.
- The browser checks cover English and French at 360 px and 390 px, including keyboard activation of every theme choice.

## Next Phase Readiness

Plan 03 can reshape the Home page on the simplified shared navigation shell.
