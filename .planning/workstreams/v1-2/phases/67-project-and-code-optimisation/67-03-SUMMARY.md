---
phase: 67-project-and-code-optimisation
plan: 03
subsystem: backup
tags: [backup, drift-guard, tests]
requires: ["67-01"]
provides:
  - "Test guard that fails when production-written state is neither backed up nor explicitly excluded"
affects: [deploy/tests/test_backup.py]
key-files:
  modified:
    - deploy/tests/test_backup.py
decisions:
  - "No leftover constant removed: every candidate has a reference (see Task 2)"
requirements: [QUAL-01]
---

# Phase 67 Plan 03: Backup drift guard Summary

One additive test class (`TestDriftGuard`) now ties the backup allow-list to the production writers; no production code changed and no constant was removed.

## Task 1: drift guard (done)

Three tests added to `deploy/tests/test_backup.py`:

1. Seeds the fleet root and one `devices/<id>/` frame only through production writers (`state_store.save_poll_state`, `device_config.save_device_config`, `history_db.connect` plus `record_device_health`, and the existing `_seed_fleet_db` helper using `fleet_db`) with placeholder data. Runs `skypane_backup.main`: return 0, no "not in include list" line, and both databases plus the config and poll-state files at root and per device are in the archive.
2. A stray file in the state root is reported as "not in include list: ..." (proves the guard bites).
3. Every `*_FILENAME` string constant of `server.device_dirs`, `server.state_store` and `server.device_config` is in the allow-list or matches `KNOWN_EXCLUDED`.

`deploy/backup/skypane_backup.py` is untouched. Collected ids before: 32 in this file; after: 35, a superset.

Owner findings: none from the guard. An additional one-off scan (not committed) over the `*_FILENAME` / `*_FILE` constants of the other persistent-state modules (`fleet_db`, `history_db`, `request_budget`, `check_interval`, `plane/*` registries and markers, `firmware_registry`, `fleet_migrate`) found every file classified, except `registry.json` and `device_report.json`, which live inside `firmware/` and are covered by the `firmware` directory entry. No allow-list change is needed.

## Task 2: leftover constants (nothing removed)

Word-boundary search outside `.planning` over tracked files:

| Constant | Result | Decision |
|----------|--------|----------|
| `BATTERY_FULL_MV`, `BATTERY_EMPTY_MV` | imported by `companion/battery.py`, asserted in several companion tests, named in `hardware/BATTERY-RUN.md` | keep (referenced) |
| `POLL_INTERVAL_S` | used by `server/test_poll_loop.py` (`poll_cycle.POLL_INTERVAL_S`), cited in `companion/health_signals.py` and `freshness.js` comments | keep (referenced) |
| `META_PROVIDER_LAST_CALL_PREFIX` | used by `server/test_provider_rate.py` and by `export_status_meta` | keep (referenced) |
| `META_LAST_POLL_TRIGGER` | only its definition and the `_STATUS_META_KEYS` filter; no writer in the current tree | keep (see below) |

`META_LAST_POLL_TRIGGER` is technically unreferenced, but git history is squashed, so a `last_poll_trigger` row written by an older release cannot be ruled out in the production `history.db`. Dropping it from the status filter would hide such a row from the status export, an observable change. Left in place as an owner decision (candidate: remove together with confirmation that no live `history.db.meta` has that key). No schema, `user_version` or written key was touched.

## Checks run

- `deploy/tests/test_backup.py`: 35 passed; `deploy/tests` full: 402 passed, 1 skipped (pre-existing: local openssl cannot backdate a certificate, unrelated).
- `ruff check deploy/tests/test_backup.py`: clean; `companion/test_suite_guards.py`: 430 passed; `scripts/check_comment_history.py check`: clean.
- Task 2 freeze/golden/mypy checks not needed (no source change).

## Deviations from Plan

None in behaviour. Task 2 produced no commit because no constant met the zero-reference condition.

## Self-Check: PASSED
