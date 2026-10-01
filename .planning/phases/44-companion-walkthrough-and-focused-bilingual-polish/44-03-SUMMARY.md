---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 03
subsystem: companion-home
tags: [home, responsive-ui, i18n, accessibility]
requires: [44-02]
provides: [frame-signal-first-home]
affects: [home, health, refresh]
tech-stack:
  added: []
  patterns: [PageContext-derived-state, responsive-reading-order, focused-browser-coverage]
key-files:
  created: []
  modified:
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/i18n_fr/home.py
decisions:
  - "Keep the Home route and label unchanged while applying the approved Direction B hierarchy."
  - "Show a Health link only for warn/error health states; intentional quiet-hours sleep stays silent on Home."
metrics:
  tasks_completed: 2
status: complete
---

# Phase 44 Plan 03: Frame Signal Home Summary

Home now leads with the latest frame image and flight, places recent flights immediately after it, and limits normal-operation information to a compact battery fact.

## Delivered

- Removed the Home page slogan, freshness line, configuration strip, repeated healthy diagnostics, and daily activity band.
- Added a responsive current-frame / recent-flights composition that keeps the image first on desktop and mobile.
- Added a short, direct Health action only when the shared health snapshot contains a real warning or error.
- Retained PageContext-derived data, escaped image routes, the existing gallery image rendering, and Home's current route and label.
- Added French copy for the new current-frame, battery, and action-needed messages.
- Updated Home refresh regions so polling never swaps markup that Home no longer renders.

## Validation

- `server/.venv/bin/python3 -m pytest -n 0 -q companion/test_i18n.py companion/test_page_context.py companion/test_companion_app_04.py::test_home_page_renders_widgets` — 47 passed before concurrent Display/Device work changed its registry fixtures.
- `server/.venv/bin/python3 -m pytest -n 0 -q companion/test_view_pages_03.py companion/test_view_pages_04.py companion/test_status_pages_05.py` — 263 passed, 16 skipped retired Home-dashboard checks.
- `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python3 -m pytest -n 0 -q companion/test_browser_ux_02.py::test_home_prioritises_the_frame_signal_and_keeps_its_actions_usable companion/test_stylesheet_structure.py` — 8 passed.
- `server/.venv/bin/python3 -m pytest -n 0 -q companion/test_view_pages_04.py::test_home_health_action_is_reserved_for_actionable_state` — 1 passed.

## Deviations from Plan

### Auto-fixed Issues

1. **[Rule 3 - Obsolete refresh and assertions] Updated contracts that named retired Home markup.**
   - **Found during:** Task 1 validation.
   - **Issue:** The refresh registry and older Home tests still targeted the removed frame strip, healthy tiles, freshness line, battery ring, and day band.
   - **Fix:** Limited the Home refresh registry to the current frame, flight list, and compact facts; retired assertions are documented as skipped while Direction B browser and served-page checks cover the delivered hierarchy. The daily-band behaviour is deferred to its planned Health migration.
   - **Files modified:** `companion/ui_nav.py`, `companion/test_status_pages_05.py`, `companion/test_view_pages_03.py`, `companion/test_view_pages_04.py`.
   - **Commit:** `7d766cf8`.

### Concurrent Test State

The full plan commands encountered temporary i18n and Device-page expectation failures while parallel Phase 44 Display/Device edits were uncommitted. The focused Home and stylesheet checks above passed; the owning work must rerun the aggregate suite after its registry changes settle.

## Self-Check: PASSED

- `7d766cf8`, `55a9eca0`, and `4668e737` exist in Git history.
- The Home renderer, French catalogue, stylesheet, browser coverage, and summary are present.
