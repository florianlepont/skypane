---
phase: 51-per-device-config-image-and-state
plan: 12
subsystem: companion
tags: [device-scope, crawl, isolation, route-inventory]
requires: [51-03, 51-04, 51-08, 51-09, 51-10, 51-11]
provides:
  - Prefix crawl over every device page (route-table classified)
  - End-to-end isolation tests across the companion and the BYOS server
  - 51-DEVICE-SCOPED-ROUTES.md inventory for the auth phase
affects: [auth phase]
key-files:
  created: [companion/test_device_isolation.py, .planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-DEVICE-SCOPED-ROUTES.md]
  modified: [companion/test_device_routes.py, companion/device_scope.py, companion/pages/health_page.py]
requirements-completed: []
duration: 45min
completed: 2026-10-30
---

# Phase 51 Plan 12: Prefix Crawl, Isolation Tests and Route Inventory Summary

Cross-cutting tests prove prefix completeness and end-to-end device isolation, and the 27 device-scoped routes (13 GET, 14 POST) are handed over as a generated inventory. FLT-01 / FLT-02 are intentionally NOT marked complete.

## Commits
- 501e4ec refactor(51-12): make the device last check-in accessor public
- 29edaaa test(51-12): prefix crawl and end-to-end device isolation tests
- 54083c2 docs(51-12): device-scoped route inventory for the auth phase

## What changed
- `TestPrefixCrawl` (companion/test_device_routes.py): crawls the six device pages plus `?sheet=manage`, two `?resolve=` variants and two flash variants for dev A. Every href, src, form action (with the form's own method), data-* address and `return_to` value is classified through `routes.match`: device-scoped addresses must carry dev A's prefix, none may name dev B's, `return_to` stays un-prefixed, global targets (`/update`, `/static/*`, `/ui-theme`, `/ui-lang`, `/logout`, `/runway-image/*`) are never prefixed, and a one-device fleet's live pages contain no `/devices/` text.
- `companion/test_device_isolation.py`: the companion app (fake providers) and a BYOS server over one seeded state directory. Tests: poll isolation end to end, settings isolation (Martinique time zone), live frame unchanged (raw 960000 bytes, `/img/<hash>.bin`), unknown token 401, unknown device 404 (companion and `/img/d_00000000/...`), removed fleet row 401 with the token still in the legacy store, removed panel file 503.
- `device_scope.last_check_in_epoch` is now public; `health_page` uses it (cleanup candidate from the previous plan).
- `51-DEVICE-SCOPED-ROUTES.md`: generated from `routes.ROUTES` by a throwaway script kept outside the repository (not committed): both scoped tables with handler, access class and device-directory effect, an empty minimum-role column, the not-scoped table (login, logout, ui-theme, ui-lang, update and its install/cancel POSTs because the OTA registry is per hardware type at the root, runway diagrams, static assets), the annotation hook and the BYOS device endpoints (token-authenticated, not companion routes).

## Gaps found and fixed
None. The crawl and the isolation tests passed on first run against the existing emitting modules; no prefix gap or isolation leak was found, so no emitting module changed except the accessor rename above. Two false starts were in my own test code (a second BYOS poll in the same test changed dev B's battery file; data-* addresses have no method), fixed in the tests, not weakened.

## Verification
- `companion/test_device_routes.py`, `companion/test_device_isolation.py`: 113 passed.
- Full `companion test-support stub-server` run (serial): 2908 passed, 554 skipped, 0 failed. Skips are the Chromium browser tests (the available Playwright build here is 1243 but the installed package expects 1248) and root-permission tests.
- ruff, mypy (18 files), comment-history check and function-size gate (max 80) pass. `companion/testdata` and `stub-server` unmodified.

## Deviations from Plan
1. Isolation test fixtures: the removed row and removed panel tests use a function-scoped stack (they destroy state); the others share a module-scoped stack.
2. The inventory generator and the comparison with the document were done by the same script (counts asserted 13/14 and every row required a note entry) instead of a manual diff.

## Self-Check: PASSED
