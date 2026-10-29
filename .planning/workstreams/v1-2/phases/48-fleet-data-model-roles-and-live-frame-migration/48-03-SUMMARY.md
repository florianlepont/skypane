---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 03
subsystem: server
tags: [migration, cli, sqlite, fleet]
requires: ["48-01", "48-02"]
provides:
  - server/fleet_migrate.py (read_legacy, plan_migration, migrate, main with --state-dir/--owner-email/--dry-run)
  - stub-server/fleet_cli.py (users, locations, devices, hardware verbs with legacy mirroring)
  - test-support/skypane_live_state.py (seed_live_like_state, snapshot_dir)
affects: [deploy migration step, byos auth switch, companion fleet pages]
tech-stack:
  added: []
  patterns: [expand-only idempotent migration, read-only snapshot then single write transaction, legacy mirroring inside the DB transaction]
key-files:
  created: [server/fleet_migrate.py, server/test_fleet_migrate.py, stub-server/fleet_cli.py, stub-server/test_fleet_cli.py, test-support/skypane_live_state.py]
  modified: [pyproject.toml]
key-decisions:
  - Migration never opens a write connection when nothing is pending, so fleet.db bytes are unchanged on a re-run
  - Strict legacy reader aborts on any malformed present file, the opposite of byos fail-closed-to-empty
  - Reconcile is legacy-wins on secret and token only, never deletes, never clears a token
  - fleet_cli runs the legacy register_device write inside the DB transaction so a legacy failure rolls back the insert
requirements-completed: [DATA-01, DATA-02, DATA-03]
duration: 25min
completed: 2026-10-29
---

# Phase 48 Plan 03: Migration and Operator Tooling Summary

Idempotent, dry-run capable `server/fleet_migrate.py` that imports the live frame (MAC, secret hash, token, state_path ".") into fleet.db as an admin-owned Orly device without touching any other file, plus `stub-server/fleet_cli.py` for users, locations and one-owner devices with every device change mirrored into the legacy files, and a synthetic production-shaped state fixture generator.

## Tasks

1. Fixture generator and fleet_migrate: cab27cc
2. fleet_cli operator tool: bd73eea

## Verification

- pytest server/test_fleet_migrate.py stub-server/test_fleet_cli.py server/test_fleet_db.py: green
- ./scripts/run-all-tests.sh: 3920 passed, 539 skipped (Chromium not installed in this sandbox, non-root permission test)
- mypy, ruff, check_function_size (max 80), check_comment_history: clean

## Deviations from Plan

None - plan executed as written. One test-side adjustment: the dry-run-on-migrated-directory snapshot comparison excludes empty `fleet.db-wal`/`-shm` side files, which a read-only WAL connection may leave behind (the plan allows comparing the main file only for these). The main file sha256 and mtime are asserted unchanged.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model.

## Self-Check: PASSED
