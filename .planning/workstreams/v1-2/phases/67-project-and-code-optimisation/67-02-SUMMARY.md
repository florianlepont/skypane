---
phase: 67-project-and-code-optimisation
plan: 02
subsystem: docs-state
tags: [architecture, persistent-state, backup, migrations]
requires: [67-01]
provides:
  - verified persistent-state map in ARCHITECTURE.md (owners, migrations, duplicates, backup coverage, locking)
  - cross-reference from the deploy README backup section
affects: [67 ARCHITECTURE.md rewrite plan]
key-files:
  modified:
    - ARCHITECTURE.md
    - deploy/README.md
decisions:
  - Two SQLite migration mechanisms are documented, not unified (provisional default, owner may override)
  - Duplicated data is documented as rollback net, planned data or leftover; retirement needs an owner decision on the end of the rollback period (provisional default: document, do not retire)
metrics:
  completed: 2026-11-27
  tasks: 2
  files: 2
requirements: [QUAL-01]
---

# Phase 67 Plan 02: Persistent state map Summary

New "Persistent state" section in ARCHITECTURE.md answering each D-06 question, verified against the code, plus a pointer from the deploy README. No code, schema or behaviour change.

## Commits

- 5a136fb: docs(67-02): add Persistent state section to ARCHITECTURE.md
- 568aeaa: docs(67-02): point the backup section at the Persistent state map

## Verification

- Research state map re-checked by grep: `user_version` 4 (`fleet_db.MIGRATIONS`, four steps) and 1 (`HISTORY_SCHEMA_VERSION`); table lists; lock files; backup `INCLUDE_FILES`, `DEVICE_INCLUDE_FILES`, `KNOWN_EXCLUDED`; unused meta keys, `wake_epochs`, `legacy-admin`, location helpers.
- `deploy/tests/test_docs.py`, `deploy/tests/test_backup.py`, `server/test_fleet_migrate.py`: 114 passed.
- Backticked repo paths in ARCHITECTURE.md all resolve in `git ls-files`.
- `scripts/exposure_scan.py tree`: no finding in the two edited files. `check_comment_history.py check` clean.

## Deviations from Plan

### Corrections to the research map

**1. [Accuracy] Caddy log offset gap stated precisely.** The research marked post-restore behaviour as assumed benign. The code (`history_db.read_caddy_battery_log`) resets the offset to 0 when the log is smaller than the stored offset, and `device_health` is unique on timestamp and battery value, so a re-read is harmless. The section states this instead of an open question.

**2. [Accuracy] Gallery writer.** Research listed the companion as a writer of `gallery/`; the code shows only the poll cycle writes it, so the table lists the poll process.

Otherwise the plan was executed as written. STATE.md and ROADMAP.md were not touched (orchestrator owns them).

## Known Stubs

None.

## Threat Flags

None. Only file and column names are written; no values, hosts or addresses.

## Self-Check: PASSED
