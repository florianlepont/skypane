---
phase: 51-per-device-config-image-and-state
plan: 03
subsystem: backup
tags: [backup, device-dirs, sqlite-snapshot]
requires: []
provides:
  - per-device archive walk in deploy/backup/skypane_backup.py
affects: [deploy/README.md]
key-files:
  modified:
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py
    - deploy/README.md
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 03: Per-device backup Summary

The nightly backup now archives every `devices/<id>/` directory (config, state, calendar/colour/manual data, illustration overrides, gallery, and a WAL-safe `history.db` snapshot) and never `panel.bin`, `img/`, locks, WAL/SHM, temp files or symlinks. The script stays standalone with a duplicated id regex.

## Commits

- 658e4fc: per-device archive walk, drift reporting, 7 new tests
- 1afc8d9: README layout and expand-only rollback note

## Verification

- pytest deploy/tests/test_backup.py + test_docs.py: 37 passed (7 new device tests: include/exclusions, bad-name drift, unexpected-entry drift, symlink refusal, restore round trip, concurrent writer, corrupt history.db). Existing tests unmodified (additions only).
- full deploy suite: 234 passed, 1 skipped. ruff check deploy: clean; check_comment_history: clean. mypy reports one missing-import error in server/panel_format.py:14 (not touched by this plan; out of scope).

## Deviations from Plan

None. Added two extra tests beyond the six required (unexpected-entry drift, corrupt device db).

## Known Stubs

None.

## Self-Check: PASSED
