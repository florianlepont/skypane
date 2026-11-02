---
phase: 60-device-co-management
plan: 07
subsystem: testing
tags: [access-matrix, co-managers, live-frame, render-baseline]
requires:
  - phase: 60-03
    provides: access.decide with is_co_manager and the owner-only device kind
  - phase: 60-05
    provides: the three /co-managers/* routes
provides:
  - Co-manager column and owner-only kind in the route x role x owner matrix
  - Live-frame immutability proof with co-managers on the Orly frame
affects: [60-08, 60-09]
tech-stack:
  added: []
  patterns: [per-area matrix rows module, membership seeded in the rig fixture not the shared seed]
key-files:
  created:
    - test-support/matrix_rows_co_managers.py
    - stub-server/test_co_manager_live_frame.py
  modified:
    - companion/test_access_matrix.py
    - test-support/companion_render_snapshot.py
key-decisions:
  - "Co-manager user and membership are created in the rig fixture; shared seeds are untouched"
requirements-completed: [AUTH-08]
duration: ~25min
completed: 2026-11-01
---

# Phase 60 Plan 07: Access matrix co-manager column and live-frame proof Summary

The route x role x owner matrix now has a co-manager principal for every route in both the pure and the HTTP layer, an owner-only-device kind with the three `/co-managers/*` rows, and an integration test shows co-managers leave the live Orly frame byte for byte unchanged.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| Extra: baseline capture list | 51330dd | `POST /co-managers/add`, `/remove`, `/leave` added to `_UNAUTH_POST_REQUESTS` |
| 1: matrix co-manager column, owner-only kind, rows | 800097c | 1577 matrix/access/guard tests pass |
| 2: live-frame immutability | 0a56ff5 | 3 new tests plus the freeze suite pass |

## What changed

- `companion/test_access_matrix.py`: `OWNER_ONLY` kind (`owner-only-device`, min role user, device arg `device-owner`), `co-manager` in `PRINCIPAL_NAMES`, a co-manager cell in every outcome kind and in the un-prefixed outcomes, user id 4 with a pure membership lookup forwarded to `access.decide`, the three routes in `DEVICE_SCOPED`, the new rows module merged in both spots, and an HTTP rig user with a membership row on the owner's device. The unknown-id, malformed-id and poll-now loops include the co-manager, and a new test checks that a co-manager gets the unknown-path 404 on every OWNER_DEVICE route of a frame they do not co-manage.
- `test-support/matrix_rows_co_managers.py`: ROWS for the three routes, empty SAMPLES.
- `stub-server/test_co_manager_live_frame.py`: after migrating a live-like state, adding two co-managers (an admin and a never-signed-in user) and then removing them leaves the poll response (incl. image hash), the state directory (every file except fleet.db and the server log, hash and mtime), the legacy files and the `devices` row (id, owner, MAC, secret, token, state_path, name, location, hardware type) identical; the byos loaders read the same registry and state.

## Deviations from Plan

**1. [Rule 3 - Blocking] Render baseline capture list lacked the co-manager routes**
- **Found during:** orchestrator-added scope
- **Issue:** `companion/testdata/render_baseline.json` (plan 05) holds `POST /co-managers/add|remove|leave` entries but `UNAUTH_REQUESTS` had no samples, so `test_unauthenticated_responses_match_the_baseline` failed.
- **Fix:** added the three paths to the capture list in `test-support/companion_render_snapshot.py`; the baseline entries and the assertion are untouched.
- **Commit:** 51330dd

Otherwise the plan was executed as written.

## Verification

- `pytest companion server stub-server -n auto` (browser tests skipped, no Chromium installed in this sandbox): 7455 passed, 12 skipped (Playwright browser missing, root permission-bit tests), 0 failed. This includes the access matrix completeness tests, `test_render_baseline.py` and `stub-server/test_phase47_freeze.py` (unedited).
- ruff: clean. mypy: no issues in 28 files. `check_function_size.py check --max 80 server stub-server`: none over 80. `check_comment_history.py check`: clean.
- `git diff` of `test-support/access_matrix_support.py`, `test-support/fleet_console_support.py`, `stub-server/byos_server.py`, `stub-server/test_phase47_freeze.py` and `hardware/` is empty.

## Known Stubs

None.

## Touches Phase 55 code

None. Only test files and test support were edited; `companion/test_access_matrix.py` and `test-support/matrix_rows_*.py` are the matrix infrastructure that the Phase 55 handoff (section B) directs this phase to extend. No Phase 55 planning lines were edited.

## Self-Check: PASSED

Files and commits 51330dd, 800097c, 0a56ff5 verified present.
