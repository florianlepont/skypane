---
phase: 68-console-and-companion-visual-improvements
plan: 17
subsystem: companion
tags: [routes, removal, access-matrix]
requires: ["68-01", "68-10"]
provides: ["the Locations console routes are gone and answer the standard 404"]
affects: ["68-22 (baseline regeneration)", "68-24 (nav.py)"]
key-files:
  created: [companion/test_route_removed_locations.py]
  deleted: [companion/console_locations.py, companion/pages/locations_page.py, companion/i18n_fr/admin_locations.py, companion/test_console_locations.py, test-support/matrix_rows_locations.py, test-support/locations_page_support.py]
decisions:
  - "nav.locations (and its French entry) removed here; plan 24 must not re-add it"
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 17: Remove the /locations page Summary

GET /locations and POST /locations/add, /{id}/edit, /{id}/delete now answer the same 404 as an unknown path for administrator, user and anonymous; the `locations` table, `detection_actions` and the audit target kind `location` are untouched (`git diff --stat -- server` is empty).

## What changed

- Deleted the console module, the page, its French strings, its 34 tests, the matrix row module and the browser helper.
- `console_routes.py`: `LOCATIONS_*` constants, the import, the ROUTES concatenation and `LOCATIONS_LABEL` removed. `page_styles.py` lost its `/locations` entry; `i18n_fr/nav.py` lost `nav.locations`.
- Tests: new `test_route_removed_locations.py` (3 principals x 6 method/path pairs compared with an unknown path, plus Place page still opens; Place save and detection tests still pass). Matrix: only the `matrix_rows_locations` import and its two uses removed (rows file deleted); no other row changed. Route table test: the four `/locations*` entries removed and a `_REMOVED_ROUTES` set added so the still-recorded baseline keys are asserted to match no route. Browser, nav, i18n, empty-state, account and user-view tests dropped their Locations cases; the "admin URLs are the unknown-path page for a user" test keeps `/locations` and now asserts the 404.
- A CSS comment and one skill reference line that named the Locations page were reworded.

## Render baseline (not regenerated)

`companion/test_render_baseline.py`: the unauthenticated half differs in exactly four records and nothing else: `GET /locations` (303 to login, now 404), `POST /locations/add`, `/locations/1/edit`, `/locations/1/delete` (303 `?expired=1`, now 404). Plan 22 regenerates. The pages half already differs from earlier plans (static asset hashes, e.g. `/airlines|en|dark`); not caused by this plan.

## Verification

1340 tests passed in the focused run (route table, removal test, overhaul sweep, console, nav spaces, empty-state browser tests with SKYPANE_REQUIRE_BROWSER=1, suite/structure guards, audit page, motion budget); 2614 passed in the first wide run apart from the three baseline-related failures above (route-table one fixed). Golden render and Phase 47 freeze pass, ruff clean, mypy clean (no new errors), comment-history guard clean, no function over 80 lines, app.py 1490 lines (not edited).

## Deviations from Plan

None beyond: `test_route_table.py` also needed the `_REMOVED_ROUTES` allowance because the baseline is deliberately not regenerated; `test_browser_nav_spaces.py` lost its Locations field-fit test; `test_account_page.py` lost `/locations` from its allowed-target list (all mechanical).

## Design-system divergences

None. No screen changes: the Locations page was already redirect-only and was not in any navigation, so no capture comparison was applicable.

## Known Stubs

None.

## Self-Check: PASSED
