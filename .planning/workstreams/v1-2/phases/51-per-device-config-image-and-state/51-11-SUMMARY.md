---
phase: 51-per-device-config-image-and-state
plan: 11
subsystem: companion
tags: [device-scope, home, health, flights, empty-states, i18n]
requires: [51-06]
provides:
  - Per-device Home, Health and Flights pages with the approved empty and unreachable states
  - Device-prefixed gallery, illustration, resolve, flights, health and display links on those pages
affects: [51-10 baselines]
key-files:
  created: [companion/test_device_pages.py]
  modified: [companion/pages/home_page.py, companion/pages/health_page.py, companion/pages/history_page.py, companion/health_sections.py, companion/flight_card.py, companion/page_context.py, companion/i18n_fr/health.py, companion/i18n_fr/flights.py, companion/i18n_fr/home.py]
requirements-completed: []
duration: 60min
completed: 2026-10-30
---

# Phase 51 Plan 11: Per-device Home, Health and Flights Summary

A selected non-live device's Home, Health and Flights pages read only its own directory, render the approved empty and unreachable states, and keep every link inside `/devices/<id>`. The live frame's pages are unchanged and the committed baselines are untouched.

FLT-01 / FLT-02 are intentionally NOT marked complete.

## Commits
- f0c1172 feat(51-11): per-device Home, Health and Flights pages with empty and unreachable states
- The `companion/flight_card.py` edit (device-prefixed illustration URL) was swept into plan 51-08's commit 7e5d283 by the parallel executor.

## What changed
- Health: a never-seen device renders the full-card empty state and nothing else; a device silent for more than two of its own wake intervals gets the docked warning toast "No signal since {time}" and keeps its data; a device with check-ins but no battery reading gets the compact "No battery reading" state. The live frame path is untouched.
- Nav dot: `page_context._lazy_health_severity` returns "ok" for a never-seen device, so no tab carries a dot for it.
- Flights: a non-live device with no rows shows the "No history for this frame yet" empty state; gallery, illustration and resolve links go through `device_scope.scoped`.
- Home: the preview slot shows the device's own newest picture through the prefixed gallery URL, or the compact "No picture yet" state (never the live image); flights, health, display and action-needed links are prefixed.
- English and French messages added for every new string.

## Verification
- `companion/test_device_pages.py`: 21 tests (isolation in both directions plus live, empty states in EN and FR, unreachable toast and its absence online and on live, no nav dot for a never-seen device, prefixed links, markup escaping, corrupt history.db renders without a 500).
- Plan verify set (status pages, health signals, view pages, render baseline, i18n, home tests, suite guards, i18n ids): 461 passed. Full `companion` suite: 2362 passed, 553 skipped (no Chromium here). `git diff --stat companion/testdata` empty.
- ruff, mypy, comment-history check, function-size gate (max 80), stub-server freeze and negotiation tests all pass.

## Deviations from Plan
1. [Rule 3] `companion/page_context.py` and `companion/flight_card.py` were edited though not in the plan's file list: the nav dot is derived in `page_context`, and the Flights phone-card illustration URL is built in `flight_card`.
2. [Rule 3] `health_page` calls `device_scope._last_check_in_epoch` (private) for the toast time, because `device_scope.py` was being edited concurrently by another executor and a public accessor could not be committed cleanly. A public accessor is a candidate cleanup.
3. `companion/health_signals.py` needed no change: signals were already total for an empty directory.

## Notes
- Home's "Something needs attention" toast can still appear on a never-seen device (it follows the shared health state); the spec did not cover it.
- A corrupt history.db shows the existing "history unavailable" wording rather than the empty state.

## Self-Check: PASSED
