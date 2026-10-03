---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 11
subsystem: ui
tags: [companion, update, firmware, i18n, accessibility]
requires:
  - phase: 44-09
    provides: Shared page-width and verdict-hierarchy conventions.
provides:
  - One installed-software summary (icon, running version, one relevant time, state when in flight).
  - Owner-facing release list that never includes bench builds, filtered at the page boundary.
  - Full-size Install targets and real-browser coverage at 1280/390/360 px in EN/FR.
affects: [companion-update]
tech-stack:
  added: []
  patterns: [Presentation filter at the page renderer; registry classification untouched.]
key-files:
  created: []
  modified:
    - companion/pages/update_page.py
    - companion/i18n_fr/update.py
    - companion/static/style.css
    - companion/test_update_page.py
    - companion/test_browser_update.py
    - companion/testdata/render_baseline.json
key-decisions:
  - "Bench releases are dropped from the list only; a running bench build is still named (with its Bench badge) in the summary and a scheduled one keeps its Scheduled state and version."
  - "The summary shows one time: the last device report while nothing is in flight, otherwise the time the current state began."
  - "Route label stays Update, pending the owner's navigation naming decision."
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-03
status: complete
---

# Phase 44 Plan 11: Update Summary and Owner Releases Summary

Updates now leads with a single "Installed software" summary and lists only real releases, with Install and Cancel flows unchanged.

## Tasks

1. Summary and release filter (16ec8106): headline with icon and running version, one timestamp, state row only while a schedule exists; "Available versions" list with a small icon before each version; bench rows and their badge removed from the list. French parity for the new headings. Tests retargeted from the retired bench-row contract to served absence plus truthful running/scheduled bench state, and a one-timestamp check.
2. Styling and browser coverage (a0c195e1): token-based summary and version-label styling; Install buttons keep a 44 px target in the table and phone cards (real finding: they measured 31-37 px). New browser test at 1280/390/360 px in EN/FR: one summary, bench version absent from the page, no overflow, hit target, focus ring, JS confirm to server confirmation page, Cancel link returns with nothing scheduled. Update page render baseline regenerated.

## Deviations from Plan

- **[Rule 1 - Bug]** Install buttons were under the 44 px touch floor; fixed in CSS.
- The bench badge in the list was removed (rows no longer exist); the badge now appears only on a running bench build in the summary.
- The "Available" state word is no longer rendered (nothing is in flight); only the time is shown. Version history heading renamed "Available versions" (Versions disponibles).

## Known Stubs

None.

## Verification

Full `./scripts/run-all-tests.sh` (Chromium required): only the Update render baseline failed before regeneration, then passed; coverage gate met (94.92%). ruff, mypy, comment-history check and function-size gate green.

## Self-Check: PASSED
