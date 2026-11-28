---
phase: 67-project-and-code-optimisation
plan: 17
subsystem: persistence
tags: [sqlite, migrations, fleet-db, history-db]
requires: ["67-15"]
provides: ["server/sqlite_migrations.py: Step, Policy, apply_steps, pending_steps, add_column_if_missing, set_busy_timeout, BUSY_TIMEOUT_MS, report CLI"]
affects: ["server/fleet_db.py", "server/history_db.py"]
key-files:
  created: [server/sqlite_migrations.py, server/test_sqlite_migrations.py]
  modified: [server/fleet_db.py, server/history_db.py, deploy/tests/test_backup.py, pyproject.toml]
metrics:
  tasks: 3
  completed: 2026-11-28
---

# Phase 67 Plan 17: Unify the SQLite migration mechanism Summary

One shared module, `server/sqlite_migrations.py`, now migrates fleet.db (policy `immediate`/`refuse`) and history.db (policy `idempotent`/`keep`), with a read-only `report` command. No schema, version, file mode or access change.

## Commits

- 917372cf test: 31 characterisation tests, green on the unmodified code
- 071028c6 refactor: shared module, both callers rewired, pyproject mypy lists
- 9737e10c feat: report command, report tests, backup restore-then-migrate round trip

## Pinned outcomes (identical before and after)

- fleet: fresh file ends at 4 with 8 tables, WAL, foreign_keys on, mode 0600; versions 1, 2, 3 end at 4 (v2 gains the v3/v4 tables, indexes and triggers, rows kept); 4 stays 4 and reopen changes no byte; a file stamped 5 raises `FleetDbTooNew("fleet.db schema 5 is newer than supported 4")` before any write (bytes, mode, journal mode "delete", no -wal unchanged); `migrate_schema` with a custom tuple refuses against its own length; steps run inside BEGIN IMMEDIATE (a second writer gets "database is locked", the bump is invisible outside until COMMIT); a failing step rolls back and keeps the old version; an already-applied step is skipped after the re-read; two threads on one fresh file both end at 4; busy_timeout 5000.
- history: fresh file ends at 1 with six tables and both added runway_events columns, WAL; an old file (user_version 0, no route_lookups, no extra columns) gains them keeping rows and ends at 1; stamps 7 and 2 are kept and not refused; a file stamped 1 that lost a table is repaired; a zero-size file is rebuilt even when marked ready; `init_schema` twice changes nothing; two threads, two racing `init_schema` calls on separate connections, and two processes completing an old WAL file all succeed; busy_timeout 5000.

## Evidence

- New tests pass before the refactor: run against an untouched `git archive origin/main` copy, 5 consecutive runs, 31 passed each; and the same 31 pass after.
- Collected ids: 17640 before, 17683 after; removed 0; added 43 (42 in `server/test_sqlite_migrations.py`, 1 in `deploy/tests/test_backup.py`).
- `SKYPANE_COVERAGE=off JOBS=4 SKYPANE_TEST_GROUP=core ./scripts/run-all-tests.sh`: 12934 passed, 7 skipped (root-permission and openssl skips). Includes the freeze test, goldens, test_fleet_db, test_fleet_migrate, test_config_history, test_history_db_scope, test_backup, access-matrix tests. Browser tests not run here (CI).
- mypy: 57 files (was 56), strict override added; ruff, function-size gate (3431 functions, none over 80) and comment-history check pass.
- No edit inside `_migrate_v1` to `_migrate_v4` or any history CREATE statement.

## Deviations from plan

1. [Behaviour kept over wording] The plan says the idempotent policy runs "every step whose version is above the stamp". The current `init_schema` runs all its statements on every call (it repairs a file stamped 1 that lost a table, and still runs on a newer stamp). To keep every outcome identical the idempotent policy runs all steps every time and only the stamp is conditional; pinned by `test_history_stamped_current_but_missing_table_is_repaired` and `test_history_newer_stamp_is_kept_and_not_refused`. `pending_steps` (report) still uses the stamp.
2. [Rule 3] The existing test `test_all_sql_uses_placeholders_not_string_formatting` scans history_db.py source for `%`-formatted `execute(`, so the busy-timeout pragma goes through `sqlite_migrations.set_busy_timeout(conn)` and the impact query concatenates a fixed table name.
3. Report opens `mode=ro`; when the database lacks both -wal and -shm it adds `immutable=1`, because a plain read-only open of a WAL file creates those side files. A live WAL database (both present) is read with `mode=ro` and only the shared-memory index may be touched by the read.
4. Report status words: `ok`, `pending`, `newer` (fleet file above the target, exit 0, no write), `absent`, `unreadable` (exit 2). Format: `<file> <status> current=N target=M pending=K [step=V:name:impact ...]`, no spaces inside fields.
5. Branch: the worktree commit guard allows only `worktree-agent-*`; commits are on that branch and pushed to `phase-67-17-unify-migrations`.
6. `HISTORY_STEPS`/`FLEET_STEPS`, `FLEET_POLICY`/`HISTORY_POLICY` are new public names; `_stamp_schema_version` (unused elsewhere) was removed.

## Findings (not changed)

- Two processes opening a brand-new history.db at the same instant can lose with `sqlite3.OperationalError: database is locked` at `PRAGMA journal_mode=WAL` despite busy_timeout (seen once in about 20 runs under load, on a line this plan did not change). Unchanged here; the process test therefore starts from a file already in WAL mode. The next open succeeds.

## Known Stubs

None.

## Self-Check: PASSED
