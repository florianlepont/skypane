---
phase: 65-photo-storage-privacy-and-quotas
plan: 02
subsystem: storage
tags: [photos, privacy, quota, capability, sqlite]
requires: [65-01]
provides:
  - photo_paths (id shapes, symlink-refusing paths, 0700 dirs)
  - photo_quota (limits, QuotaExceeded codes, check)
  - photo_store (authorize_manager, FrameManager, add, list_photos, read_photo, delete_photo)
  - test-support/photo_fleet.seed_photo_fleet
affects: [65-03, 65-04, 66, 67]
tech-stack:
  added: []
  patterns: [capability object gating every function, quota check and insert in one BEGIN IMMEDIATE, stage then publish inside the transaction]
key-files:
  created:
    - server/photo_paths.py
    - server/photo_quota.py
    - server/photo_store.py
    - test-support/photo_fleet.py
    - server/test_photo_quota.py
    - server/test_photo_store.py
    - server/test_photo_privacy.py
  modified:
    - server/test_photo_boundaries.py
    - pyproject.toml
key-decisions:
  - "Store functions take the capability first, then conn and root: add(manager, conn, root, raw, now), read_photo(manager, conn, root, photo_id); the capability carries no connection or path"
  - "A FrameManager carries a module-private grant; one built by hand is refused by every function with PhotoAccessDenied"
  - "Temp files use mkstemp with the .up- prefix in the device directory so a later sweep can recognise them"
  - "delete_photo leaves a symlink planted in a photo's place alone (row removed, link untouched)"
requirements-completed: []
duration: 35min
completed: 2026-11-10
---

# Phase 65 Plan 02: Private photo store Summary

Manager-only photo storage: `authorize_manager` is the single door (owner and co-manager), every operation takes the resulting `FrameManager`, quotas are checked inside the insert transaction, and refusals or injected failures leave no row, file or temp.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. Path safety and quota | debfa11 | `photo_paths`, `photo_quota` (20 photos / 20 MB per frame, 500 MB server, 2 GB free floor; codes `disk_low`, `frame_count`, `frame_bytes`, `server_bytes`), `seed_photo_fleet` |
| 2. Store | 9c05d5f | capability store, bounded normalisation semaphore (2), stage/publish helpers, failure-injection and 8-thread tests |
| 3. Privacy matrix, boundary, mypy | 5f9ed3b | inspect-based signature matrix, authorize matrix, cross-frame and symlink tests, child-interpreter import test for `server.photo_store`, three modules in mypy `files` and the strict override list |

## Deviations from Plan

**1. [Interface choice] Argument order.** The behaviour text writes `add(conn, root, manager, ...)` and `list_photos(manager)`, while the matrix requires the capability as first parameter and the functions need a connection and root. Signatures are `add(manager, conn, root, raw, now)`, `list_photos(manager, conn)`, `read_photo/delete_photo(manager, conn, root, photo_id)`. `authorize_manager` is the one public function not taking a manager and is named in the test's `SYSTEM_ONLY` set.

**2. [Rule 1 - test bug] Quota tests** first used single rows above the schema's 1,000,000-byte per-row limit; fixed to use several rows. No source change.

Tests were written together with each module rather than as separate failing commits.

## Verification

- `pytest server/test_photo_store.py server/test_photo_privacy.py server/test_photo_quota.py server/test_photo_boundaries.py server/test_fleet_schema5.py --no-cov -q`: 58 passed.
- `mypy`: no issues in 53 source files. `ruff check server test-support`: clean. `check_function_size.py check --max 80 server stub-server`: none over 80. `check_comment_history.py check`: clean.
- Wider run `pytest server companion/test_suite_guards.py test-support -n auto --no-cov -q`: 4350 passed, 3 skipped.

## Hand-off

- Plan 03 extends `SYSTEM_ONLY` in `server/test_photo_privacy.py` for purge/sweep functions; temp files are `.up-*` in `photos/<device_id>/`.
- Phase 66: the render-for-device reader must be a system-only function returning rendered bytes (never the stored JPEG or a path). Any derived panel image or serving cache (content-addressed files under img/) must live under the same device directory or be purged and ignored when its photo is deleted. No render cache file under `photos/` exists in Phase 65.
- Phase 67: map the quota codes (`frame_count`, `frame_bytes`, `server_bytes`, `disk_low`) and `PhotoRejected.reason` to English and French text.

## Known Stubs

None.

## Threat Flags

None. T-65-09 to T-65-14 mitigated: capability type with no role parameter and one denial message; strict id regexes, symlink refusal and `O_NOFOLLOW` read; quotas and bounded normalisation; check and insert in one transaction (8-thread test ends at exactly the limit); errors carry codes only; explicit 0700/0600 modes.

## Self-Check: PASSED
