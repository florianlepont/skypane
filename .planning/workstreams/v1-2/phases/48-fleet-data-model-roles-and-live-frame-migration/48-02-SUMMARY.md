---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 02
subsystem: server
tags: [sqlite, fleet, roles, migrations]
requires: ["48-01"]
provides:
  - server/fleet_db.py (connect/connect_readonly/connect_memory, migrate_schema, transaction, user/location/device CRUD, meta, status file)
affects: [migration CLI, byos auth, backup, health page]
tech-stack:
  added: []
  patterns: [PRAGMA user_version atomic migrations, 0600 pre-created db file, change-only status file]
key-files:
  created: [server/fleet_db.py, server/test_fleet_db.py]
  modified: [pyproject.toml]
key-decisions:
  - Journal mode is set only after the too-new check so a newer database is never written
  - Reading devices never consults the hardware simulation gate; only add_device does
requirements-completed: [DATA-01, DATA-03]
duration: 15min
completed: 2026-10-29
---

# Phase 48 Plan 02: Fleet Database Layer Summary

Stdlib-sqlite3 `server/fleet_db.py`: schema v1 (users, locations, devices with NOT NULL owner foreign key, meta), atomic `user_version` migrations, 0600 file creation, read-only and in-memory variants, local-only role reader, device CRUD with hardware registry validation, and a change-only status file.

## Tasks

1. Connection layer, migrations, status file: 4d17d6a
2. Users, roles, locations, devices and mypy registration: 737c9e1

## Verification

- pytest server/test_fleet_db.py, test_hardware.py, test_import_boundaries.py: 61 passed
- mypy: clean (14 files); ruff: clean
- check_function_size (max 80): 500 functions, none over
- check_comment_history: clean

## Deviations from Plan

None in behaviour. `connect` checks the schema version before enabling WAL (the plan's order would have rewritten the header of a too-new file).

## Known Stubs

None.

## Self-Check: PASSED
