---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 02
subsystem: fleet-db
tags: [schema, migration, audit, pairing, locations, auth]
requires: []
provides:
  - fleet.db schema 3 (migration index 3) with pending_devices, audit_log, locations.owner_user_id
  - fleet_db API for pending frames, audit, user guards, owner-aware locations, get_device
  - device_dirs.wipe_device_dir
affects: [55-03, 55-05, 55-06, 55-07, 55-08, 55-09, 55-10, 55-11, 55-12]
tech-stack:
  added: []
  patterns:
    - check-then-write helpers join the caller's transaction or open BEGIN IMMEDIATE themselves (_atomic)
    - listings select explicit columns, never secret hash, token, code salt/hash or issuer/subject
key-files:
  created:
    - server/test_fleet_schema3.py
  modified:
    - server/fleet_db.py
    - server/device_dirs.py
    - server/test_fleet_db.py
    - server/test_fleet_migrate.py
    - server/test_device_dirs.py
key-decisions:
  - "Migration index 3 belongs to this phase; Phases 52/53/56 must append v4 and later."
  - "Guards and location helpers use _atomic so they hold the write lock even when a caller forgets transaction()."
  - "delete_location_if_unused raises LocationInUse (returns False only for an unknown id)."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~30min
completed: 2026-10-31
---

# Phase 55 Plan 02: Schema 3 and the typed fleet_db API Summary

One expand-only migration takes fleet.db to schema 3 (pending_devices, append-only audit_log enforced by triggers, nullable locations.owner_user_id), and fleet_db now exposes the typed pending, audit, user-guard and owner-aware location API that plans 05 to 12 call.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 1d294dd | `_migrate_v3`, `AuditActor`/`audit_append`/`list_audit`/`count_audit`/`AUDIT_CATEGORIES`, `list_devices` carries `owner_user_id`, `add_device` refuses a pending MAC, version-pinned tests follow `SCHEMA_VERSION` |
| 2 | c20a1a9 | pending API (`register_pending` .. `reactivate_pending`, `park_retired`, registry views), `get_device`, last-admin/self-action guards, `list_users_with_frame_counts`, location API, `wipe_device_dir` |

## Verification

- `pytest server/test_fleet_schema3.py server/test_device_dirs.py server/test_fleet_db.py server/test_fleet_migrate.py stub-server/test_phase47_freeze.py` : 173 passed; first run with fleet auth/cli: 188 passed.
- `ruff check server`, `mypy` (23 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (759 functions, none over 80): all clean.
- Concurrency tests use real threads on separate connections (three concurrent v2 upgraders end at `[3, 3, 3]`; two admins demoting each other leave exactly one `ok` and one `LastAdminError`).

## Deviations from Plan

- **[Rule 2 - Safety]** `_atomic` helper added: the guards, `delete_location_if_unused`, `set_device_location_checked`, `register_pending` and `park_retired` open `BEGIN IMMEDIATE` when the caller has no transaction, so the check and write can never run unlocked. Inside a caller's `transaction()` they simply join it.
- `register_pending` takes a trailing optional `environ` (hardware simulation gate) like `add_device`; `park_retired(conn, device_id, now)` takes the device id and returns the new pending id (or None); `get_pending*` return the code salt/hash (the pairing check needs them) but never `secret_sha256` or `token`; `list_pending` exposes only `has_code`.
- `_downgrade_to_v1` in `test_fleet_migrate.py` drops the v3 triggers/tables and the new column via `ALTER TABLE ... DROP COLUMN`.

## Notes for the owner

- Rollback caveat: the previous release's byos refuses schema 3 (`FleetDbTooNew`); expand-only, so data is intact, but the old code will not start against an upgraded file.
- Phases 52/53/56 that add migrations must append v4+.
- The live-frame guard for `park_retired` (refusing state_path ".") is deliberately left to the ops layer.

## Known Stubs

None.

## Self-Check: PASSED

Files present: server/test_fleet_schema3.py, server/fleet_db.py, server/device_dirs.py. Commits 1d294dd and c20a1a9 exist.
