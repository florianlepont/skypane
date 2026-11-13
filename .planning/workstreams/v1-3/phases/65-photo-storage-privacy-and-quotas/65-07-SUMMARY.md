---
phase: 65-photo-storage-privacy-and-quotas
plan: 07
subsystem: backup
tags: [photos, backup, privacy, docs]
requires: [65-02, 65-03]
provides:
  - photos in KNOWN_EXCLUDED of the backup script
  - docs/PHOTO-STORAGE.md decision record
affects: [66, 67]
key-files:
  created:
    - docs/PHOTO-STORAGE.md
  modified:
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py
    - deploy/tests/test_docs.py
    - deploy/README.md
key-decisions:
  - "Owner decision: photos are excluded from backups (privacy, deleted photos must disappear, disk size); restore relies on the sweep to drop rows without files"
requirements-completed: []
completed: 2026-11-10
---

# Phase 65 Plan 07: Backup exclusion and decision record Summary

Photos are never archived and never reported as drift; a restored fleet.db with photo rows but no files is reconciled to an empty list by the sweep; the decision, reasons and honest privacy limits are in docs/PHOTO-STORAGE.md and deploy/README.md.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. Exclude photos | 69f613e | `photos` in KNOWN_EXCLUDED; three tests (no archive members and no drift, restore plus sweep leaves empty list and a second sweep returns zeros, symlinked `photos` skipped) |
| 2. Decision record | b08f01d | docs/PHOTO-STORAGE.md, README Backups paragraph, two doc tests |

## Deviations from Plan

None in scope. Process slip: I ran `git stash` once to check that the new tests fail without the change (red check); it held only my own change, was popped immediately, and the stash list is empty again. Red confirmed: 2 of the 3 new tests failed without the exclusion (the restore test passes either way, as the sweep does not depend on it).

## Verification

- `pytest deploy/tests --no-cov -q -n auto`: 249 passed, 1 skipped (pre-existing openssl backdating skip).
- `pytest deploy/tests/test_backup.py`: 30 passed.
- ruff clean, mypy no issues in 54 files, `check_comment_history.py check` clean.
- Shipped docs contain no phase numbers or plan IDs.

## Hand-off (phase numbers allowed here)

- Phase 66 (photo serving): purge or ignore any derived serving cache on delete; render reader stays system-only.
- Phase 67 (companion photo UI): MANAGER_DEVICE on all photo routes plus matrix rows; body cap while reading; drop multipart filename; map frame_count, frame_bytes, server_bytes, disk_low to EN/FR text.

## Known Stubs

None.

## Threat Flags

None. T-65-26 to T-65-29 mitigated (exclusion plus archive-member test, application-level caveat stated, restore test).

## Self-Check: PASSED
