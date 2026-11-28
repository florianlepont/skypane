---
phase: 67-project-and-code-optimisation
plan: 23
subsystem: docs
tags: [architecture, deploy-runbook, schema-5, retirement]
requires: ["67-17", "67-19", "67-20", "67-21", "67-22"]
affects: ["ARCHITECTURE.md", "deploy/README.md"]
key-files:
  modified: [ARCHITECTURE.md, deploy/README.md]
metrics:
  tasks: 2
  completed: 2026-11-28
---

# Phase 67 Plan 23: Documentation update (final pass) Summary

Docs only. ARCHITECTURE.md and deploy/README.md now describe the state after plans 17 to 22, and deploy/README.md carries the owner's ordered retirement runbook. This replaces the first-pass summary; the first pass is superseded.

## ARCHITECTURE.md

- Module map: `fleet_artwork` and the merge half of `fleet_registries` gone (only `frame_state_dirs` remains, checked in `server/plane/fleet_registries.py`); `server/retire_legacy_state.py` and `server/sqlite_migrations.py` added; `devices_cli` removed from the operator CLI list.
- Device authentication: identity from fleet.db only, fail closed (403 setup, 401 display and log; `stub-server/test_byos_fleet_only.py`).
- Deploy rollback: the swap-back restores code, not data (schema 5).
- Stores table: `fleet.db` `user_version` 5 (`SCHEMA_VERSION = len(MIGRATIONS)` = 5 in `server/fleet_db.py`); legacy identity files retired; new `retired-legacy/` row (`QUARANTINE_DIRNAME`); migration markers split into the two still written (`fleet_default_types`, `fleet_set_defaults`) and the two nothing writes any more (read by `retire_legacy_state`); per-frame registry and override copies no longer read or backed up; `illustration_conflicts/` has no writer.
- Migrations: step 5 (`sessions-user-principal-only`), `history.db` stays at 1 (`HISTORY_SCHEMA_VERSION = 1`), report exit codes 0/3/2 (`EXIT_CURRENT/EXIT_PENDING/EXIT_UNREADABLE` in `server/sqlite_migrations.py`).
- Duplicated or overlapping data: rewritten. Items 1, 2, 3, 5, 6 marked retired/removed with the code evidence; item 4 `wake_epochs` kept by owner decision (G4); item 7 updated (REGISTRY_FILE no longer exists in the device server; MAC pattern locations listed from grep). New "quarantine directory" paragraph and "Schema 5 and the previous release" subsection.
- Backup coverage: `retired-legacy` and the per-device lists (`INCLUDE_DIRS`, `DEVICE_INCLUDE_FILES`, `DEVICE_INCLUDE_DIRS` in `deploy/backup/skypane_backup.py`).

## deploy/README.md

- "Device enrolment": rewritten around fleet.db and `fleet_cli` (`register-pending`, `replace-secret`, `revoke-token`; no restart needed, the server reads fleet.db per request).
- "Fleet database": expand-only bullet rewritten, new bullet for the two migration policies, `devices_cli` sentence removed.
- New "Retiring the legacy files (owner runbook)" with six steps: read-only checks, backup check with checksum, deploy, report + quarantine dry run + apply, verify, restore. Exit codes verified by running the commands on a scratch state directory (report 0 on absent and current; quarantine dry run, apply, second run `nothing to do`).
- Merge sections ("Fleet-wide airline names and artwork") reduced to the present behaviour; default-type sections lost the merge references; Backups text and per-device list updated; rollback caveats replaced by a schema 5 caveat; new "Schema v5 and rollback"; v2/v3/v4 sections marked historical; "Ship the code" and "Rolling back" carry the schema 5 qualification; remaining `devices.json` mentions removed.

## Checks

- `deploy/tests/test_docs.py`, `test_backup.py`, `test_units.py`: 90 passed.
- Backticked-path resolution script of the plan: ARCHITECTURE.md clean; deploy/README.md only reports its pre-existing deploy-relative names.
- `scripts/check_comment_history.py check`: clean. `scripts/exposure_scan.py tree`: no finding in either file. No `devices_cli` left in deploy/README.md.

## Not verified

- Production state (nothing run there). The gate document records that production predates `server.sqlite_migrations`, so step 1 of the runbook tells the owner to skip the report if the command is missing.
- The behaviour of the previous release on a schema 5 file is taken from `FleetDbTooNew` in the current code and the earlier README sections, not run.
- `server/retire_legacy_state.py` per-frame step and refusal cases are described from its docstring and the 67-20 summary, not run against per-frame copies.

## Deviations

- Plan said to re-run the path script "from plan 05"; the plan's inline script was used.
- Runbook step 1 also gives the `fleet_migrate --dry-run` from the old release only; it cannot show the schema 5 step before the deploy.
- The gate document says report exit 1 means pending; the code (`EXIT_PENDING = 3`) and the existing ARCHITECTURE text say 3. The docs follow the code.
- Branch: the commit guard allows `worktree-agent-*`, so commits are on the worktree branch and pushed as `phase-67-23-docs-final`.

## Self-Check: PASSED
