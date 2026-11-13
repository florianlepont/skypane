---
phase: 65-photo-storage-privacy-and-quotas
plan: 04
subsystem: storage
tags: [photos, privacy, purge, lifecycle, audit]
requires: [65-01, 65-02, 65-03]
provides:
  - fleet_ops.unlink_photo_files (post-commit, never raises)
  - retire, reassign and account deletion purge photos on disk
  - audit label device.photo_purge (English and French)
affects: [65-05]
key-files:
  created:
    - server/test_photo_lifecycle.py
  modified:
    - server/fleet_ops.py
    - companion/console_users.py
    - companion/pages/audit_page.py
    - companion/i18n_fr/admin_lifecycle.py
requirements-completed: []
duration: 30min
completed: 2026-11-10
---

# Phase 65 Plan 04: Purge on retire, reassign and account deletion Summary

Retiring a frame, reassigning it (live frame included) and deleting an account now remove the photo rows inside the transaction, write one count-only `device.photo_purge` audit row per cause, and unlink the files after COMMIT; a failed unlink triggers one sweep and never propagates.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. Retire and reassign | 66176b8 | `_purge_photo_rows` (in transaction) and `unlink_photo_files` (after COMMIT) in `fleet_ops`; refused live retire keeps photos; `reactivate_frame` untouched |
| 2. Account deletion and audit label | ac2c8d8 | `handle_delete` unlinks the uploader's files after commit; "Photos purged" / "Photos supprimées"; lifecycle tests |

## Deviations from Plan

**1. [Rule 1 - Bug] Unlink must run before the response is sent.** The plan says to call `remove_files` after `_run_action` returns, but `_run_action` returns the already-sent redirect, so the client could see the page before the files were gone (the test failed on exactly this race). `_run_action` gained an optional `after_commit` callback that runs after the transaction commits and before the redirect; it is skipped for refused or rolled-back changes.

**2. [Interface choice] Helper location.** The post-commit step (`unlink_photo_files`) lives in `fleet_ops` and the companion calls it, instead of duplicating the remove-then-sweep logic. `fleet_ops` imports `photo_purge`; no cycle.

Tests were written together with the code, not as separate failing commits.

## Verification

- `pytest server/test_photo_lifecycle.py server/test_fleet_ops.py server/test_fleet_co_manager_cascades.py companion/test_audit_co_manager_detail.py companion/test_audit3_fixes.py server/test_fleet_delete_user.py`: 131 passed.
- `pytest companion -k "audit or users or i18n or delete or retire or reassign or account"`: 695 passed, 381 skipped (browser tests: Chromium not installed here).
- `pytest companion -k "i18n or french or fr"`: 1115 passed, 1001 skipped. `pytest server -k "fleet or photo or i18n"`: 557 passed.
- ruff clean, mypy clean (54 files), function-size gate clean, comment-history check clean.

## Known Stubs

None.

## Threat Flags

None. T-65-19 to T-65-21 mitigated: filesystem tests per path, `remove_files` re-checks the row is gone (refused delete test), audit detail holds count and cause only and the audit page test asserts no photo id in English and French.

## Self-Check: PASSED
