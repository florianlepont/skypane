---
phase: 51-per-device-config-image-and-state
plan: 05
subsystem: companion
tags: [routing, device-scope, fleet]
requires: [51-01]
provides:
  - Route.device_scoped flag and prefix-aware routes.match()
  - companion/device_scope.py leaf module
affects: [companion handlers migrated in later plans, auth annotation]
key-files:
  created: [companion/device_scope.py, companion/test_device_routes.py, companion/test_device_scope.py]
  modified: [companion/routes.py]
requirements-completed: [FLT-01, FLT-02]
duration: 25min
completed: 2026-10-30
---

# Phase 51 Plan 05: Device-scoped routes and device_scope module Summary

Per-device routes are declared once in the route table (`device_scoped`) and resolve under `/devices/<id>/...`; `companion/device_scope.py` turns an id into a `Device` and carries the per-request scope.

## Commits
- e93becd feat(51-05): device_scoped routes and /devices/<id> prefix matching
- 1645aac feat(51-05): device_scope leaf module with lookup, poll locks and request scope

## Device-scoped route set (27)

GET (13): `/` (Home), `/display`, `/device`, `/flights`, `/health`, `/airlines`, `/settings` (redirect), `/history` (redirect), `/preview` (redirect), `/gallery/<x>`, `/illustration/<x>.png`, `/theme-preview/<x>.png`, `/frame-preview/<x>.png`.

POST (14): `/settings`, `/poll-now`, `/quick/display`, `/quick/quiet-hours`, `/quick/led`, `/airlines/resolve`, `/airlines/rename`, `/airlines/rename/reset`, `/airlines/manual-resolutions/<x>/delete`, `/illustration/<x>.png`, `/settings/rules/add`, `/settings/rules/<x>/delete`, `/settings/calendar/connect`, `/settings/calendar/disconnect`.

Never matched under a prefix: login, logout, ui-theme, ui-lang, all static assets, `/runway-image/*`, `/update`, update install and cancel.

## Decisions
- The flag is applied from two explicit key tuples in `routes.py` (`_PAGE_AND_IMAGE_KEYS`, `_ACTION_KEYS`) via `_replace` instead of editing 27 route literals; the table still declares it once, and the test pins the exact set.
- A device with no wake interval set is judged against 3600 s (the byos `--sleep` default) for the offline rule.
- `device_status` reads the device's own `history.db` only if the file exists (so a status check never creates one), falling back to `battery_state.json` `received_at`.
- A fleet-less live frame gets id `"live"`.

## Deviations from Plan
None beyond the decisions above. No handler lambda changed.

## Verification
- `pytest companion/test_device_scope.py companion/test_device_routes.py companion/test_route_table.py companion/test_structure_guards.py companion/test_suite_guards.py`: 276 passed
- `ruff check .` clean; `mypy` clean; `scripts/check_comment_history.py check` clean
- `companion/test_route_table.py` and `companion/testdata` untouched

## Known Stubs
None.

## Self-Check: PASSED
