---
phase: 44
plan: 01
subsystem: companion-browser-walkthrough
tags: [companion, playwright, bilingual, responsive, owner-review]
requires: []
provides: [authenticated walkthrough matrix, owner-review finding record]
affects: [phase-44-follow-up-planning]
tech-stack:
  added: []
  patterns: [isolated real-server browser matrix, owner-gated evidence record]
key-files:
  created:
    - companion/test_browser_phase44_walkthrough.py
    - .planning/phases/44-companion-walkthrough-and-focused-bilingual-polish/44-WALKTHROUGH.md
  modified: []
decisions:
  - "Automated walkthrough results do not select production UI changes; the owner reviews every candidate first."
metrics:
  focused_tests: 47
  regression_tests: 168
status: complete
---

# Phase 44 Plan 01: Companion Walkthrough Summary

Added a real-login, bilingual, responsive companion walkthrough and recorded
its results without authorising product changes.

## Delivered

- Added 42 route/language/viewport checks across all seven authenticated routes.
- Added owner-journey coverage for saved Display settings, keyboard-operated
  data disclosures, and separate Health warning/scheduled-sleep states.
- Added the versioned finding record with fixture provenance, route coverage,
  reproducible evidence, and an owner-review gate.

## Verification

- `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py` — 47 passed.
- `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py companion/test_browser_ux_01.py companion/test_browser_ux_02.py companion/test_browser_ux_03.py companion/test_browser_ux_04.py companion/test_browser_update.py` — 168 passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test contract] Replaced a URL-query assertion with the served flash-banner witness.**
- **Found during:** Task 2 verification.
- **Issue:** The test assumed the save response would retain `flash=saved` in
  the browser URL, while the user-facing contract is the rendered confirmation.
- **Fix:** Assert the served `.banner--flash[role="status"]` confirmation after
  the persisted save.
- **Files modified:** `companion/test_browser_phase44_walkthrough.py`.

## Owner Review Gate

No automated observation selected a UI fix. The owner must retain, adjust,
defer, or reject each candidate before a focused follow-up plan changes
production companion code.

## Known Stubs

None.

## Self-Check: PASSED

- `companion/test_browser_phase44_walkthrough.py` exists.
- `44-WALKTHROUGH.md` exists.
- No production companion source was modified.
