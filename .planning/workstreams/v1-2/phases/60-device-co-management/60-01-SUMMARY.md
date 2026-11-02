---
phase: 60-device-co-management
plan: 01
subsystem: fleet-db
tags: [sqlite, migration, co-management, schema-v4]
requires: []
provides:
  - fleet.db schema 4 with device_co_managers
  - fleet_db co-manager API, typed errors, audit action names
affects: [60-02, 60-03, 60-04, 60-05]
tech-stack:
  added: []
  patterns: [expand-only migration, in-transaction eligibility re-check via _atomic, defence-in-depth triggers]
key-files:
  created: [server/test_fleet_schema4.py]
  modified: [server/fleet_db.py, server/test_fleet_schema3.py, deploy/README.md]
key-decisions:
  - "Owner exclusion is enforced by two triggers as well as Python"
  - "One SQL predicate defines eligible for both the candidate list and the typed-address lookup"
requirements-completed: [AUTH-08]
duration: short
completed: 2026-11-01
---

# Phase 60 Plan 01: Schema v4 and co-manager API Summary

Expand-only migration v4 (table `device_co_managers`, one index, two owner-exclusion triggers) plus the `fleet_db` co-manager API with in-transaction eligibility.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Migration v4 and API | 2b59cd6 | server/fleet_db.py, server/test_fleet_schema4.py |
| 2 Version-relative schema-3 tests, rollback docs | 099d2ca | server/test_fleet_schema3.py, deploy/README.md |

## Touches Phase 55 code

- `server/fleet_db.py`: migration entry and co-manager helpers only (v1-v3 migrations and `park_retired` unchanged).
- `deploy/README.md`: new "Schema v4 and rollback" section only.

## Verification

- `pytest server/test_fleet_schema3.py server/test_fleet_schema4.py server/test_fleet_db.py stub-server/test_phase47_freeze.py deploy/tests/test_backup.py`: 140 passed.
- ruff on touched Python files, mypy `server/fleet_db.py`, `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check`: clean.
- `stub-server/test_phase47_freeze.py` unedited and green.

## Deviations from Plan

None in behaviour. Note: the in-place upgrade test compares `locations` rows only when starting at schema 3, because upgrading from schema 1 or 2 also runs the earlier v3 column addition, which legitimately widens those rows. `devices` and `users` rows are compared for every start.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_downgrade_to_v1` helper in `server/test_fleet_migrate.py` did not drop v4 objects**
- **Found during:** full server run after Task 2
- **Issue:** the helper rebuilds a schema-1 database by dropping later objects; the new table and trigger on `devices` blocked the re-upgrade (OperationalError).
- **Fix:** the helper also drops `devices_owner_not_co_manager` and `device_co_managers`. No assertion changed.
- **Files modified:** server/test_fleet_migrate.py

## Known Stubs

None.

## Self-Check: PASSED
