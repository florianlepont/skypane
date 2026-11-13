---
phase: 65-photo-storage-privacy-and-quotas
plan: 03
subsystem: storage
tags: [photos, privacy, purge, sweep, filesystem]
requires: [65-01, 65-02]
provides:
  - photo_purge (remove_files, purge_frame, sweep, SweepCounts, PurgeResult)
affects: [65-04, 65-05]
tech-stack:
  added: []
  patterns: [rows first then files after COMMIT, lstat-only no-follow deletion, counts-only results]
key-files:
  created:
    - server/photo_purge.py
    - server/test_photo_purge.py
    - server/test_photo_sweep.py
  modified:
    - server/test_photo_privacy.py
    - pyproject.toml
key-decisions:
  - "remove_files and purge_frame return PurgeResult(purged_or_removed, failed) so callers can trigger a sweep when failed > 0"
  - "SweepCounts has a sixth field, refused, for a symlinked photos directory; when set the sweep does nothing else (no row reconcile either)"
  - "A symlinked entry is always unlinked as a link, even one standing in for a row's file; the row is then dropped as missing in the same sweep"
requirements-completed: []
duration: 20min
completed: 2026-11-10
---

# Phase 65 Plan 03: Photo removal and orphan sweep Summary

`server/photo_purge.py` removes photo files after their rows are gone, purges a whole frame, and sweeps the tree so files and `device_photos` rows agree (vanished-device directories, old unrowed files, stale `.up-*` temps, rows without files, symlinks), never following a link and never cutting off a young upload.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. remove_files, purge_frame | 1900c49 | row-checked unlink, device dir removal, links removed as links, failure counting; privacy matrix names the three functions as system-only; module in both mypy lists |
| 2. Orphan sweep | f169912 | five rules as small helpers, 15 minute injectable grace, restore scenario, silence test |

`sweep` was written in the same file as Task 1, so the Task 1 commit contains the complete module; the Task 2 commit adds its tests.

## Deviations from Plan

**1. [Interface choice] Result types.** The plan says `remove_files` returns "a count" and also "a small result tuple" for failures; both return `PurgeResult(count, failed)`.

**2. [Interface choice] `SweepCounts.refused`.** The plan lists five fields; a sixth defaulted field reports the refused symlinked `photos` directory, since "reported" needed somewhere to go without printing.

**3. SYSTEM_ONLY.** The set in `test_photo_privacy.py` only gates `photo_store`; the three names were added as asked, and a new test also asserts that `photo_purge` exposes exactly these public functions, with no `manager` or role parameter.

Tests were written together with the module rather than as separate failing commits.

## Verification

- `pytest server/test_photo_sweep.py server/test_photo_purge.py server/test_photo_store.py server/test_photo_privacy.py --no-cov -q`: 51 passed.
- `mypy`: no issues in 54 source files. `ruff check server test-support`: clean. `check_function_size.py check --max 80 server stub-server`: none over 80. `check_comment_history.py check`: clean.

## Hand-off

- Plans 04/05: call `purge_frame` / `remove_files` after the COMMIT that removes rows (never inside the transaction); when `failed > 0`, run `sweep`. The sweep writes no audit rows and prints nothing; the CLI prints the counts.
- `remove_files` decides "row gone" by reading the table on the same connection, so calling it inside an uncommitted transaction would be wrong.

## Known Stubs

None.

## Threat Flags

None. T-65-15 to T-65-18 mitigated: lstat/unlink and `scandir` without following links, grace period tests with an injected clock, orphan rules plus failure counts for callers, integer-only silent output.

## Self-Check: PASSED
