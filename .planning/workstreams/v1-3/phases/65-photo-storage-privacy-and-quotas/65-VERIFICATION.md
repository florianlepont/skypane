---
phase: 65-photo-storage-privacy-and-quotas
verified: 2026-11-11T00:00:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
re_verification: false
gaps: []
---

# Phase 65: Photo Storage, Privacy and Quotas Verification Report

**Phase Goal:** Photos live in private per-frame storage that only the frame's owner and co-managers can reach, that is bounded, and that really forgets what is deleted.
**Branch:** `phase/65-photo-storage-privacy`
**Status:** passed (with the honest limits listed below)

## Test evidence

Run with `server/.venv/bin/python -m pytest ... --no-cov`: the photo tests, schema 4/5 and migrate tests, `companion/test_access*.py`, `test_photo_admin_surfaces.py`, `test_photo_sweep_startup.py`, `stub-server/test_fleet_cli_photos.py` and all of `deploy/tests`. Result: 2484 passed, 1 skipped (an openssl certificate backdating test, unrelated). `ruff check` is clean and `scripts/check_comment_history.py check` exits 0.

I also ran my own scripts in temp directories under the scratchpad, outside the repo.

## Success criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Owner and co-manager read; stranger, anonymous and non-manager admin refused; no admin surface exposes photos | VERIFIED | See below |
| 2 | Deleting a photo, retiring, reassigning or removing a frame, and deleting an account remove the files on disk | VERIFIED | See below |
| 3 | Quota refusal stores nothing; concurrent uploads cannot exceed the limit | VERIFIED | See below |
| 4 | Backup excludes photos, recorded in docs; restore and sweep behave | VERIFIED | See below |

### 1. Privacy (PRIV-01)

- Service layer: `photo_store.authorize_manager` grants a `FrameManager` capability only to the owner or an active co-manager. Every store function calls `_require`, which checks a module-private `_GRANT` object. Live results from my script:
  - Owner and co-manager were granted.
  - Other user, pure admin, disabled co-manager, `None`, `True`, a string id, a missing user and malformed device ids (`../x`, an empty string, `None`) all raised the same `PhotoAccessDenied`.
  - A hand-built `FrameManager` with no grant, and one with a forged `object()` grant, were both refused. No function takes a role, an admin flag or a path.
- Route kind: `companion.access.decide(..., route_types.MANAGER_DEVICE, ...)` returned allow for owner and co-manager, not-found for an admin who is neither, not-found for a stranger, and login for anonymous. The admin shortcut is bypassed only for `DEVICE_MANAGER_ARG`. The existing kinds are unchanged.
- Route guard: `test_every_photo_route_is_manager_only` is in `companion/test_access_matrix.py`. It also has a self-test showing the guard reports a mis-gated route.
- Admin surfaces: `companion/test_photo_admin_surfaces.py` stores photos on three frames and fetches every GET route with an admin session. It asserts no photo id, path or file size in any body, and nothing in the audit page, health page or fleet status JSON. The audit entry is count-only (`device.photo_purge` with `{count, cause}`). `fleet_cli photos sweep` prints integer counts only.
- Limit: no photo route exists yet, so the route guard passes vacuously. It starts to bite when Phase 67 adds routes. Privacy today rests on the service-layer capability, which is verified.

### 2. Deletion (PRIV-02)

Checked on the filesystem:

- **Delete one photo:** the row goes inside a transaction and the file is unlinked after COMMIT. The file was gone afterwards.
- **Retire and reassign:** `fleet_ops.retire_frame` and `reassign_frame` call `_purge_photo_rows` inside the transaction, then `unlink_photo_files` after commit. A failed unlink falls back to a sweep.
- **Frame removal:** `fleet_db.remove_device` clears the rows. The `byos_server.mirror_to_fleet("remove")` path and the `fleet_cli devices remove` path then run `sweep_photos_quietly`, which removes the files.
- **Account deletion:** `console_users.handle_delete` collects the refs of photos the user uploaded, `delete_user_guarded` deletes the rows (audited, count only), and `after_commit` unlinks the files. My scenario deleted a co-manager who had been removed from the frame. Their photo file was removed and the owner's photo stayed. Account deletion therefore removes everything the account uploaded, including on frames it no longer co-manages. This matches `docs/PHOTO-STORAGE.md`.
- **Rollback before unlink:** a transaction that raised after `delete_photo_rows` left both the row and the file. `remove_files` skips any ref whose row still exists.
- **Symlinks:**
  - A symlink planted in place of a photo file is refused on read (`O_NOFOLLOW`).
  - It is left alone by `delete_photo` and removed as a link by the sweep (`links=1`).
  - The link target outside the tree survived both the delete and the sweep.
  - A symlinked `photos` directory is refused by the sweep (`refused=1`), and `photo_paths` refuses symlinked components.
- **Path traversal:** photo ids are checked with `\Aph_[0-9a-f]{16}\Z`, so `../../fleet.db`, an uppercase id, a trailing newline and an unknown id all raised `PhotoNotFound`. Device ids are shape-checked before any join. The database also carries a CHECK on the id shape.

### 3. Quotas (PRIV-03)

- All four codes were reproduced by `photo_quota.check`: `frame_count`, `frame_bytes`, `server_bytes` and `disk_low`. The 21st upload raised `frame_count` and left exactly 20 files.
- Each refusal stored nothing (file listing and row count checked).
- Concurrency: eight threads, each with its own connection, tried to upload with the per-frame limit at 3. Three succeeded and five got `frame_count`. The result was 3 rows and 3 files. The check and insert run inside `BEGIN IMMEDIATE`, and the file is moved into place inside the same transaction.
- If COMMIT fails after the move, the final file is removed. Temp files are removed on failure.

### 4. Backup (PRIV-04)

- `deploy/backup/skypane_backup.py` lists `photos` in `KNOWN_EXCLUDED`, so it is neither archived nor reported as drift. `deploy/tests/test_backup.py` has behaviour tests for this, and `deploy/tests/test_docs.py` checks the docs.
- `deploy/README.md` (Backups) has a "Photos are not archived" paragraph. `docs/PHOTO-STORAGE.md` records the decision, the reason (a deleted photo must not live on in archives kept for a year) and the restore behaviour.
- Restore: `fleet.db` is restored without the files. `photo_purge.sweep` drops rows whose file is missing, and the companion runs it once at start (`_sweep_photos_at_start`). `fleet_cli photos sweep` runs it on demand. Covered by `server/test_photo_sweep.py` and `companion/test_photo_sweep_startup.py`.

## Protected paths and hygiene

- `git diff origin/explore/photo-mode-v1-3..HEAD` shows no change to `server/plane`, `server/fixtures/golden`, `server/panel_format.py`, `hardware`, `firmware`, phase 47 or 47.1 files, root `.planning/STATE.md`, root `.planning/ROADMAP.md` or the v1-2 workstream.
- No image or binary files were added.
- The only non-added files in the diff are the expected modifications. The only `.planning` edits are the v1-3 workstream's own `REQUIREMENTS.md`, `ROADMAP.md` and `STATE.md`.
- A grep of added code and docs (outside `.planning`) found no plan, phase or requirement IDs. `check_comment_history.py` passes.
- Migration v5 is expand-only: one `CREATE TABLE device_photos` and one index, and no existing table is touched. There is no cascade. Rows are cleared explicitly, and `uploaded_by` has no foreign key on purpose.

## Honest limits (not gaps)

- The admin is also the VPS root. Privacy is application-level only. Files are not encrypted at rest, and counts and timestamps in `fleet.db` are readable by anyone with file access. The docs say so.
- No photo route exists yet, so the `MANAGER_DEVICE` route guard passes vacuously. Phase 67 must use the `MANAGER_DEVICE` kind and call `authorize_manager` once per request.
- The capability is a snapshot and is not re-checked against `fleet.db` within a request. This is documented.

## Bookkeeping notes for the orchestrator

- ROADMAP still shows plan 65-08 unchecked, and PRIV-01..04 are still marked Pending in `REQUIREMENTS.md`. 65-08 is done (`test_photo_admin_surfaces.py` exists and passes). Tick these at phase close.
- No blockers.

_Verifier: Claude (gsd-verifier)_
