---
phase: 65-photo-storage-privacy-and-quotas
plan: 01
subsystem: database
tags: [sqlite, fleet_db, migration, photos, privacy]
requires: []
provides:
  - fleet.db schema v5 with the device_photos table
  - photo row helpers in fleet_db (insert, usage, list, get, delete, refs, is_user_active)
  - photo row cleanup hooks in remove_device, park_retired, delete_user_guarded
affects: [65-02, 65-03, 65-04, 65-05]
tech-stack:
  added: []
  patterns: [explicit row clearing before parent DELETE, count-only audit rows]
key-files:
  created:
    - server/test_fleet_schema5.py
    - server/test_fleet_photo_rows.py
  modified:
    - server/fleet_db.py
    - server/test_fleet_schema4.py
    - server/test_fleet_migrate.py
key-decisions:
  - "Photo id shape is enforced in the schema by a GLOB prefix, a length of 19 and a no-non-hex-character check on the suffix"
  - "Photos uploaded by a deleted account are removed with it on any frame; co-manager removal keeps them"
requirements-completed: [PRIV-02, PRIV-03]
duration: 20min
completed: 2026-11-10
---

# Phase 65 Plan 01: Photo metadata layer Summary

Schema v5 adds the expand-only `device_photos` table (no cascade, no FK on `uploaded_by`), with row helpers and hooks so frame removal, retirement and account deletion neither fail on nor leave behind photo rows.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. Migration v5 and row helpers | ff90444 | `_migrate_v5`, `insert_photo`, `photo_usage`, `server_photo_bytes`, `list_photo_rows`, `get_photo_row`, `delete_photo_row`, `all_photo_refs`, `is_user_active`, `delete_photo_rows`, `photo_refs_uploaded_by`, `delete_photo_rows_uploaded_by`, `audit_photo_purge`, `ACTION_PHOTO_PURGE` |
| 2. Hooks | de7dac2 | `delete_photo_rows` in `remove_device` and `park_retired`; `_purge_user_photos` in `delete_user_guarded` (one `device.photo_purge` row with `{count, cause}` only) |

The helper functions that task 2 names were written alongside task 1 in the same file region; task 1's commit contains the migration, the row-level helpers and their tests, task 2's commit contains the hooks and the hook tests.

## Deviations from Plan

**1. [Rule 1 - Bug] Id CHECK too weak** (Task 1). The plan's DDL `id GLOB 'ph_[0-9a-f]*'` only checks the first character after the prefix, so an id with uppercase or non-hex later characters was accepted, contradicting the required behaviour (`ph_` plus 16 lowercase hex). Fix: `id GLOB 'ph_*' AND length(id) = 19 AND substr(id, 4) NOT GLOB '*[^0-9a-f]*'`. Covered by `test_id_shape_is_enforced_by_the_schema`. Commit ff90444.

**2. [Rule 3 - Blocking] Existing tests hard-coded schema 4** (Tasks 1 and 2). `server/test_fleet_schema4.py` asserted version 4 literally (5 failures), and `server/test_fleet_migrate.py::_downgrade_to_v1` did not drop the new table, so the re-upgrade failed with "table already exists". The first now compares to `fleet_db.SCHEMA_VERSION`; the second also drops `device_photos`. No assertion about behaviour was weakened. The plan said "no existing test changed"; these are the minimum edits needed. Commits ff90444, de7dac2.

## Verification

- `pytest server/test_fleet_schema5.py server/test_fleet_photo_rows.py server/test_fleet_schema4.py server/test_fleet_db.py server/test_fleet_delete_user.py server/test_fleet_co_manager_cascades.py server/test_fleet_ops.py server/test_fleet_migrate.py --no-cov`: all pass (147 for the plan list, 44 for migrate).
- Full `pytest server -n auto --no-cov`: 3619 passed, 3 skipped, 1 failed (`test_fleet_migrate`, fixed afterwards and re-run green).
- `ruff check server`: clean. `mypy`: no issues in 50 files. `check_function_size.py check --max 80 server stub-server`: none over 80. `check_comment_history.py check`: clean.

## Issues Encountered

- `gsd-sdk query state.advance-plan --ws v1-3` fails: "Cannot parse Current Plan or Total Plans in Phase from STATE.md". Not worked around by hand. `state.record-metric` was not recorded (needs a duration argument form not resolved). `state.update-progress`, `state.record-session`, `roadmap.update-plan-progress` and `requirements.mark-complete PRIV-02 PRIV-03` ran. Note PRIV-02/03 are marked complete from the plan frontmatter although later plans still implement the file layer and quotas.

## Known Stubs

None.

## Threat Flags

None. T-65-01 to T-65-05 mitigated as planned (no names in the table, parameterised SQL, id CHECK, rows cleared before the devices DELETE, count-only audit detail, expand-only migration). The rollback caveat (an older release refuses a v5 database) is left for the docs plan.

## Self-Check: PASSED
