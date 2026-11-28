---
phase: 67-project-and-code-optimisation
plan: 21
subsystem: persistence
tags: [sqlite, fleet-db, schema-5, sessions]
requires: ["67-17", "67-20"]
provides: ["fleet.db schema 5: sessions.principal is only 'user' and user_id is NOT NULL"]
affects: ["server/fleet_db.py", "server/fleet_sessions.py"]
key-files:
  created: [server/test_fleet_schema5.py, server/test_fleet_sessions_pinned.py]
  modified: [server/fleet_db.py, server/fleet_sessions.py, companion/app.py, test-support/access_matrix_support.py, companion/test_access_matrix.py, companion/test_sign_in_config.py, server/test_fleet_db.py, server/test_fleet_sessions.py, server/test_fleet_schema4.py, server/test_sqlite_migrations.py, deploy/tests/test_backup.py]
metrics:
  tasks: 3
  completed: 2026-11-28
---

# Phase 67 Plan 21: fleet.db schema 5, retire the legacy-admin principal Summary

Gate: 67-RETIREMENT-GATE.md has G3 and G6 APPROVED (owner, 2026-11-28; production check SAFE). Nothing was applied to production; the deploy stays manual.

## Commits (branch `phase-67-21-schema5`)

- 15e03c10 test: pin session rows, indexes and behaviour on a v4 file (6 tests, green on unmodified code, committed alone)
- fa72a120 feat: schema 5 step, tests, version pins, negative tests adapted
- bd1cffbb refactor: remove `PRINCIPAL_LEGACY_ADMIN` and the stale comment in `companion/app.py`

## Migration step 5 (`sessions-user-principal-only`), exact order, inside the step's BEGIN IMMEDIATE together with `PRAGMA user_version = 5`

1. `SELECT COUNT(*) FROM sessions` (before) and `... WHERE principal = 'legacy-admin'` (retired).
2. `CREATE TABLE sessions_new` (`id_hash TEXT PRIMARY KEY`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `principal TEXT NOT NULL CHECK (principal = 'user')`, `created_at`, `last_seen_at`, `expires_at` INTEGER NOT NULL).
3. `INSERT INTO sessions_new (cols) SELECT cols FROM sessions WHERE principal = 'user' ORDER BY rowid` (explicit column list, `_copy_user_sessions`).
4. In-transaction check: copied rows must equal before minus retired, else `FleetDbError` ("row count mismatch") and the runner ROLLBACKs.
5. `DROP TABLE sessions`; `ALTER TABLE sessions_new RENAME TO sessions`; `CREATE INDEX sessions_user ON sessions (user_id)`; `CREATE INDEX sessions_expires ON sessions (expires_at)` (same names and columns as before; sessions never had triggers).
6. Second check: count after rename equals copied; `PRAGMA foreign_key_check(sessions)` must be empty, else `FleetDbError`.
7. If retired > 0, one line with the count only is printed: `fleet.db schema 5: removed N legacy-admin session row(s)`.

Foreign keys: nothing references `sessions` (asserted by a test), so no `PRAGMA foreign_keys` toggle is needed (it is a no-op inside a transaction anyway); the connection keeps `foreign_keys=ON` throughout, and `foreign_key_check` proves the result. The redundant table CHECK `(principal='user') = (user_id IS NOT NULL)` is replaced by the stricter column rules.

Report: `fleet.db pending current=4 target=5 pending=1 step=5:sessions-user-principal-only:rebuilds-table:sessions,removes-legacy-admin-rows:N` on a v4 file (N = count, 0 if the table is absent); `fleet.db ok current=5 target=5 pending=0` on v5; a v6 file is `newer` and `connect` raises `FleetDbTooNew("fleet.db schema 6 is newer than supported 5")` before any write.

## Evidence

- Rollback and failure injection (`server/test_fleet_schema5.py`): a step that rebuilds and then raises leaves a v4 file byte-equal (bytes compared) with 6 rows and the legacy CHECK; a forced copy that loses a row trips the row-count check, the file content (dump + `user_version`) is unchanged at v4, no `sessions_new` remains, and a later normal open migrates to v5 with the 4 user rows. A spy proves the step runs while a second writer gets "database is locked".
- Row survival: 5 user rows byte/type-equal in every column; zero sessions; 3 user + 2 legacy-admin planted (legacy removed, count printed, 3 intact); indexes recreated with identical SQL.
- Idempotence: second open leaves bytes unchanged; v5 file refused by a 4-step runner (no write); v6 refused.
- CHECK: inserting `legacy-admin` (with or without user) or a null user raises IntegrityError; `fleet_sessions.create_session` with that principal raises and writes nothing.
- Backup round trip (`deploy/tests/test_backup.py::TestRestoreThenMigrate::test_schema_4_backup_with_sessions_migrates_to_5_and_is_stable`): v4 file with user and one legacy-admin row, `snapshot_db`, report shows pending step 5 (count 1), migrate, rows intact, report ok, third open byte-stable.
- Pinned characterisation (`server/test_fleet_sessions_pinned.py`, 6 tests): green before and after the migration.
- Checks: collected ids 17665 before, 17694 after (removed 1, added 30); core group `SKYPANE_COVERAGE=off JOBS=6 SKYPANE_TEST_GROUP=core`: 12945 passed, 7 skipped (root-permission and openssl skips); freeze test and goldens in that run, unchanged; access matrix file 1961 passed; mypy 57 files clean; ruff clean; function-size 3393 functions none over 80; comment-history check clean; exposure scan (tree and history) exit 0 with only the pre-existing placeholder findings.
- Browser: with a scratch `PLAYWRIGHT_BROWSERS_PATH` linking the installed 1243 headless shell as 1255, `test_browser_auth0.py`, `test_browser_users_page.py`, `test_browser_console.py` ran: 93 passed. A full browser-group run was cut off by my time limit at about 37 percent with no failure seen; the rest is left to CI.
- MIN_EXECUTED left at 17591: collected count rose, nothing dropped below it.

## Test ids removed or changed (D-05 relaxed only for these)

Removed (renamed, same assertions on the new version): `server/test_sqlite_migrations.py::test_fleet_target_version_is_four` -> `test_fleet_target_version_is_five`.

Same id, body changed:
- `server/test_fleet_db.py::test_sessions_principal_user_id_check` (a legacy-admin row with no user is now rejected too)
- `server/test_fleet_sessions.py::test_legacy_admin_row_never_authenticates_and_is_deleted` (row planted in a schema 4 shaped in-memory file; the lookup defence is still pinned)
- `companion/test_access_matrix.py::test_a_legacy_session_is_refused_whatever_the_retired_flag_says[None|0|1]` (row planted by `plant_legacy_session_row` in a schema 4 shaped table; same 303 and deletion expectations)
- `companion/test_sign_in_config.py::test_a_legacy_session_row_never_authenticates_and_is_deleted[None|1]` (same helper)
- Version pins 4 -> 5 / 5 -> 6 / report text (guarantees unchanged): `server/test_fleet_schema4.py::{test_fresh_database_is_at_schema_4_with_new_objects, test_older_databases_upgrade_without_touching_rows[1|2|3], test_migrating_again_is_a_noop_and_concurrent_upgraders_agree}`; `server/test_sqlite_migrations.py::{test_fleet_fresh_file_ends_at_current_with_all_tables, test_fleet_older_versions_end_at_current[1|2|3], test_fleet_current_file_reopen_changes_no_byte, test_fleet_newer_file_is_refused_before_any_write, test_fleet_migrate_schema_refuses_newer_with_same_error, test_fleet_two_threads_migrating_one_fresh_file_both_succeed, test_report_current_files_exit_zero_and_one_line_each, test_report_older_fleet_lists_pending_steps_and_exits_three, test_report_newer_fleet_is_flagged_not_pending, test_report_command_runs_as_a_module_and_writes_nothing, test_pending_steps_lists_only_steps_above_the_stamp}`; `deploy/tests/test_backup.py::TestRestoreThenMigrate::test_old_backup_is_reported_migrated_and_stable`.

Added (30 ids, one of them the rename above): the 20 in `server/test_fleet_schema5.py`, the 6 in `server/test_fleet_sessions_pinned.py`, `test_a_legacy_admin_session_cannot_be_created` (server/test_fleet_sessions.py), `test_the_database_refuses_to_store_a_legacy_session` (companion/test_access_matrix.py), the backup round trip above, and `test_fleet_target_version_is_five`.

## Deviations from plan

1. The plan listed `server/fleet_sessions.py` under files and `test_fleet_schema5.py` before `fleet_db.py`; the characterisation file is a new `server/test_fleet_sessions_pinned.py`, committed alone first, as the task required.
2. `_STEP_DETAILS` entries may now hold a function (read-only impact) instead of fixed text; needed for the legacy-row count in the report.
3. The count of removed rows is printed to stdout by the step (count only), the only way to report it from inside `connect`.
4. Branch: this worktree's commits were made directly on `phase-67-21-schema5` (the guard did not block it). Not pushed, no PR.
5. The row-count mismatch test compares file content, not bytes: `connect` switches the journal mode to WAL before migrating, which changes a header byte that is unrelated to the step.

## Lines for plan 23 (not edited here)

- `ARCHITECTURE.md:817` Stores table row: names `user_version` 4 for `fleet.db`; becomes 5.
- `ARCHITECTURE.md:855-856`: "The unification changed no schema, no version number..." is still true of plan 17; add a sentence for schema 5.
- `ARCHITECTURE.md:903-906`: item 5 "`legacy-admin` principal (rollback safety net)" is retired by schema 5.
- `deploy/README.md:338`: runbook sentence still lists the `legacy-admin` principal as in place.
- `deploy/README.md:1167-1181`: section "Schema v4 and rollback" needs a "Schema v5 and rollback" counterpart (the previous release refuses a schema 5 file with "newer than supported"; recovery is the nightly backup; `python3 -m server.sqlite_migrations report` shows `step=5:sessions-user-principal-only` with the legacy-admin count on a v4 file, and the activate dry-run line `upgrade fleet.db schema 4 -> 5`).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
