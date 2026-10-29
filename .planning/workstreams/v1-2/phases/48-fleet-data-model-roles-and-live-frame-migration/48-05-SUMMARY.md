---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 05
subsystem: deploy and backup
tags: [backup, fleet.db, activate.sh, migration, deploy]
requires: [48-02, 48-03]
provides:
  - fleet.db in the nightly archive via the sqlite3 online backup API
  - activate.sh backup, dry-run and migration before the symlink swap
  - operator documentation for the fleet database
affects: [deploy/backup/skypane_backup.py, deploy/activate.sh]
key-files:
  modified:
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py
    - deploy/activate.sh
    - deploy/tests/conftest.py
    - deploy/tests/test_activate.py
    - deploy/skypane.env.example
    - deploy/README.md
requirements: [DATA-05, DATA-02]
metrics:
  completed: 2026-10-29
  tasks: 3
---

# Phase 48 Plan 05: Fleet backup and deploy migration Summary

fleet.db is snapshotted into every nightly archive with a proven restore, and activate.sh now runs backup, `fleet_migrate --dry-run`, then `fleet_migrate` as the `skypane` user before the swap, aborting with the previous release current on any failure.

## What was built

- `skypane_backup.py`: `SNAPSHOT_DBS = ("history.db", "fleet.db")` loop through `snapshot_db`; the error message uses the source basename and wraps `sqlite3.DatabaseError`, so a corrupt file reports "snapshot failed" with `fleet.db` named and no partial archive. `fleet.db-wal`, `-shm` and `fleet_status.json` are known-excluded (no drift line).
- Tests: restore into an empty directory (integrity, schema version, joined device/owner/location rows, meta marker), exclusions, corrupt database, concurrent writer, state without fleet.db.
- `activate.sh`: `SKYPANE_BOOTSTRAP_ADMIN_EMAIL` read with `_extract_env`, validated against an anchored allow-list before any change, passed as one quoted argv element only when non-empty. New "Fleet database backup and migration" section after the firmware import; `fleet_migrate --help` added to the smoke chain. Plain-French action line when the dry-run exits 2 with no email configured.
- Fake `fleet_migrate` in the deploy harness (logs args and the `current` target at call time); ten tests covering order, omitted email, invalid email, each failure mode, French hint, same-sha redeploy and smoke failure.
- `deploy/README.md` (deploy flow, "Fleet database" section, backup and restore) and `deploy/skypane.env.example` (commented bootstrap entry; no simulation variable mentioned).

## Owner-confirmable exception to D-02

D-02 says the owner has no manual step. There is exactly one exception: the one-time `SKYPANE_BOOTSTRAP_ADMIN_EMAIL=<address>` line in `/opt/skypane/skypane.env`, needed before the first deploy that carries the fleet database (research Open Question 1). Without it the dry-run exits 2 and the deploy stops with a French instruction while the previous release keeps serving. The owner should confirm this is acceptable; the alternative would be hard-coding or deriving the address, which was rejected as guessing.

## Verification

- `server/.venv/bin/python3 -m pytest deploy/tests server/test_hardware.py`: 228 passed, 1 skipped (openssl backdating, pre-existing).
- `bash -n deploy/activate.sh` clean (shellcheck not installed).
- `check_comment_history.py check` and `check_function_size.py check --max 80 server stub-server` pass.
- No production host contacted; the full `./scripts/run-all-tests.sh` is left for the wave gate.

## Deviations from Plan

None - plan executed as written. `snapshot_db` additionally wraps `sqlite3.DatabaseError` so the file name appears in the failure line (required by the corrupt-database behaviour).

## Known Stubs

None.

## Commits

- 8bc8d15 feat(48-05): back up fleet.db with the online backup API
- 799cdc0 feat(48-05): back up and migrate the fleet database before the swap
- 13a3605 docs(48-05): document the fleet database, migration and bootstrap email

## Self-Check: PASSED
