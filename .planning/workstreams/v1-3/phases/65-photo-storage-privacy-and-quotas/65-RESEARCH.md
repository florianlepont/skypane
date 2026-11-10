# Phase 65: Photo Storage, Privacy and Quotas - Research

**Researched:** 2026-11-10
**Domain:** per-frame private file storage on the existing fleet model (SQLite fleet.db + state directory), manager-only access, real deletion, quotas, backup scope
**Confidence:** HIGH on the codebase facts (all read in this session), MEDIUM on the quota numbers and the backup recommendation (they are owner decisions)

No CONTEXT.md exists for this phase. The decisions in `.planning/notes/photo-mode-concept.md` (item 4) are treated as locked and are not reopened: admin never sees user photos, reduced copy only, real deletion, account-deletion cleanup, starting quota 20 photos of about 1 MB per frame, backup decision to settle.

<user_constraints>
## User Constraints (from the concept note and ROADMAP, no CONTEXT.md)

### Locked Decisions
- Photos are visible only to the frame owner and its co-managers. The admin never sees user photos and no admin view of them is built (PRIV-01).
- Only the reduced, normalised copy from Phase 64 is stored; the original is never kept.
- Deleting a photo removes its file from disk; deleting an account removes all its photos (PRIV-02).
- Starting quota: 20 photos per frame, about 1 MB each; plus a server-wide ceiling (PRIV-03).
- Whether photos are in the backup is decided explicitly and recorded in repository docs; backup and restore behave as decided (PRIV-04).
- Forward-only, expand-only changes; plane-mode behaviour of the live frame unchanged; no frame is in photo mode until the owner sets it.

### Claude's Discretion
- Storage layout, naming, metadata table shape, enforcement mechanism, sweep design, test strategy, exact quota numbers (to be confirmed by the owner), backup recommendation (owner decision).

### Deferred Ideas (OUT OF SCOPE)
- Companion routes and screens (Phase 67), mode/rotation/serving (Phase 66), wake interval (Phase 68), provided collections (v1.3.x), schedule, smart crop.
- Do not touch `server/plane`, `server/fixtures/golden`, `hardware/`, `firmware/`, phases 47/47.1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRIV-01 | Photos visible only to owner and co-managers; no admin view | Manager-only service layer (no admin bypass), new `Access` kind for Phase 67 routes, admin-leak audit, section "Privacy enforcement" |
| PRIV-02 | Delete removes file; account deletion removes all photos | Lifecycle hooks (delete, retire, reassign, remove_device, user delete), orphan sweep, filesystem tests |
| PRIV-03 | Per-frame quota and server-wide ceiling | Quota check inside a `BEGIN IMMEDIATE` transaction, numbers proposed, refusal codes |
| PRIV-04 | Backup decision recorded | Options table, recommendation (exclude), docs + backup-script + test changes |
</phase_requirements>

## Summary

The fleet model already gives everything needed except two things. (1) Every existing access path lets an **admin reach any device**: `companion/access.py::authorized_device_id` admits `ADMIN` for every existing device, and `fleet_db._require_frame_manager` has an `is_admin` bypass. Photos therefore need their own stricter rule (owner or co-manager only), implemented once in a service module and mirrored by a new route `Access` kind so Phase 67 routes cannot pick the permissive one by accident. (2) There is **no cleanup hook for files** anywhere: `fleet_db` is a filesystem-free leaf, `remove_device` (used by the byos mirror and `fleet_cli`) deletes the row without touching the directory, and `retire_frame` deliberately "keeps its data". Photo deletion must be wired into every path that ends or changes a frame's ownership, plus an orphan sweep as the safety net.

Recommended shape: a new leaf module `server/photo_store.py` (stdlib + Pillow-free; uses `fleet_db`, `device_dirs`, `atomic_io`, `server.photo.normalize`) owning a new table `device_photos` (migration v5, expand-only) and files at `<state>/photos/<device_id>/<photo_id>.jpg` with server-generated random ids. Every public operation takes a `FrameManager` capability obtained only from `authorize_manager(conn, device_id, user_id)`; there is no role parameter and no admin path. Quota is checked and the row inserted in one `fleet_db.transaction` (`BEGIN IMMEDIATE`), after normalisation and a same-directory temp write, so concurrent uploads cannot overshoot and a refusal stores nothing.

For backup the recommendation is **exclude photos** (OWNER DECISION, see Open Questions). The backup archives are pulled to the admin's Mac and kept 30 + 12 monthly, so including photos would hand the admin every user photo (violating PRIV-01 in spirit) and would keep "deleted" photos for up to a year (violating PRIV-02 in spirit). The allow-list backup already leaves `photos/` out by default but prints a drift line each night; the change is a `KNOWN_EXCLUDED` entry, a docs paragraph and a test.

**Primary recommendation:** build `server/photo_store.py` with capability-gated, manager-only operations, a `device_photos` table (v5), `<state>/photos/<device_id>/` storage, transactional quota, explicit purge hooks in `remove_device`, `park_retired`/`retire_frame`, reassign and user deletion, plus a two-way sweep; exclude `photos/` from the backup and record that in `deploy/README.md` and `docs/`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Who may touch a frame's photos | API / Backend (service layer `photo_store`) | Route table `Access` kind | Must hold even if a route is wrong; route gate is the second wall |
| Photo bytes on disk | Database / Storage (state dir `photos/`) | — | Private files outside any static route and outside the backup allow-list |
| Photo metadata and quota counters | Database / Storage (fleet.db `device_photos`) | — | Same transaction as the quota check; survives restart; no names stored |
| Upload validation and reduction | API / Backend (`server.photo.normalize`, exists) | — | Already done in Phase 64; 65 only wraps it with a bound on concurrency |
| Deletion on frame/account end | API / Backend (`fleet_ops`, `console_users` call `photo_store`) | Sweep | `fleet_db` is a filesystem-free leaf, so files are removed one layer up |
| Backup scope | Ops (`deploy/backup/skypane_backup.py`, docs) | — | Allow-list script is the single authority |

## Standard Stack

No new dependency. Stack stays stdlib + Pillow + requests (`server/requirements.txt`). No package install in this phase, so no slopcheck run was needed. [VERIFIED: CLAUDE.md "Technology Stack"; `server/photo/normalize.py` already imports Pillow]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Python 3.13 here / 3.14 in prod | `device_photos` table, quota transaction | Same engine as the fleet; `fleet_db.transaction` is `BEGIN IMMEDIATE` [VERIFIED: server/fleet_db.py:406] |
| `server.atomic_io` | in repo | Temp-then-rename writes with explicit mode (`atomic_write(path, data, mode=0o600)`) | Existing project primitive; no torn files, no leftover temp on failure [VERIFIED: server/atomic_io.py] |
| `server.device_dirs` | in repo | Device id shape (`d_[0-9a-f]{8}`), symlink/escape refusal pattern | Reuse its validation style for the photos tree [VERIFIED: server/device_dirs.py] |
| `server.photo.normalize` | in repo (Phase 64) | `normalize_upload(bytes) -> StoredPhoto(jpeg, width, height)`; stored copy is at most `STORE_MAX_BYTES = 1_000_000` | Gives a hard per-photo byte bound, so 20 photos is at most 20 MB per frame [VERIFIED: server/photo/normalize.py:22] |
| `secrets` (stdlib) | — | Photo ids (`secrets.token_hex(8)`) | No user-supplied names anywhere |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Top-level `photos/<device_id>/` | `devices/<id>/photos/` | The latter is wiped for free by `wipe_device_dir`/`_reset_directory`, but the live frame has `state_path "."` and has no `devices/<id>` directory, and the live frame is the owner's own Orly frame. The top-level tree works for every frame; the cost is explicit purge hooks (needed anyway for `remove_device` and `retire_frame`). |
| Files named by DB id | BLOBs in SQLite | BLOBs would put photos inside `fleet.db`, which is in every backup archive and is read by admin tooling (`dump_logical`, `fleet_cli`). Files keep photos out of those paths. |
| New table | JSON sidecar per frame | A table gives transactional quota counting; JSON needs its own locking. |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed or recommended in this phase. Table omitted on purpose.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Phase 67 route (future)                 byos render path (Phase 66, future)
   |  principal (user_id)                   |  device id from authenticated device token
   v                                         v
 route Access kind MANAGER_DEVICE        system-only reader (no user, rendered
 (owner|co-manager, admin NOT admitted)   bytes only, never the stored copy)
   |                                         |
   v                                         |
 photo_store.authorize_manager(conn, device_id, user_id) --> FrameManager (or PhotoAccessDenied)
   |
   +-- list / read / delete(manager, photo_id) ----------------------+
   |                                                                 |
   +-- add(manager, raw_bytes):                                      |
         semaphore(2) -> normalize_upload(raw)   [Phase 64]          |
         -> atomic_write temp in photos/<device_id>/.up-<rand> (0600)|
         -> fleet_db.transaction:                                    |
              count/bytes per frame, SUM bytes server-wide           |
              refuse (QuotaExceeded code) -> unlink temp, store nothing
              insert device_photos row                               |
              os.replace(temp, <photo_id>.jpg)                       |
         -> commit                                                   v
                                                      <state>/photos/<device_id>/<photo_id>.jpg
 Lifecycle (all call photo_store.purge_*):
   delete one photo | retire_frame / remove_device / reassign (frame ends or changes hands)
   | user deletion (co-manager uploads) | sweep (orphan files, rows without files, stale temp)
 Backup: photos/ in KNOWN_EXCLUDED (never archived); restore -> sweep drops rows whose files are gone
```

### Recommended Project Structure
```
server/
├── photo_store.py        # NEW leaf: capability, quota, add/list/read/delete, purge, sweep
├── fleet_db.py           # + _migrate_v5 (device_photos), row-level helpers, remove_device hook
├── fleet_ops.py          # retire_frame / reassign call photo_store purge after COMMIT
├── test_photo_store.py   # NEW: behaviour tests on tmp state dir (filesystem assertions)
└── test_photo_privacy.py # NEW: manager matrix at the service layer, admin-leak sweep
companion/
├── access.py, route_types.py  # + DEVICE_MANAGER_ARG / MANAGER_DEVICE (no admin)
└── console_users.py           # user delete calls photo_store purge for uploaded_by
test-support/
└── matrix_rows_*.py / access_matrix_support.py  # policy vocabulary extended (see Validation)
deploy/backup/skypane_backup.py  # photos in KNOWN_EXCLUDED (if "exclude")
deploy/README.md, docs/PHOTO-STORAGE.md (NEW)  # decision record
```

### Pattern 1: capability object instead of role checks
**What:** `authorize_manager(conn, device_id, user_id) -> FrameManager` is the only way to get a `FrameManager(device_id, user_id)`; every public function takes it as first argument. The check is `owner_user_id == user_id or is_co_manager(...)`, and the user must exist and not be disabled. There is no `is_admin`/role parameter, so a future route cannot "pass admin through". Unknown device, foreign device and malformed id raise the same `PhotoAccessDenied` (mirrors the existing NOT_FOUND-for-everything stance in `access.py`).
**When to use:** all user-facing photo operations.
**Example:**
```python
# Source: pattern derived from companion/access.py and fleet_db.is_co_manager (this repo)
def authorize_manager(conn, device_id: str, user_id: int | None) -> FrameManager:
    if user_id is None or not device_dirs.is_valid_device_id(device_id):
        raise PhotoAccessDenied
    owner = fleet_db.get_device_owner(conn, device_id)
    if owner is None:
        raise PhotoAccessDenied
    if owner != user_id and not fleet_db.is_co_manager(conn, device_id, user_id):
        raise PhotoAccessDenied
    return FrameManager(device_id, user_id)   # also reject a disabled user here
```
Note: do NOT reuse `fleet_db._require_frame_manager` (it lets admins through).

### Pattern 2: quota inside the write lock, file made before the row, name published after the row
**What:** normalise first (CPU heavy, outside the lock, bounded by a process-wide `threading.BoundedSemaphore(2)` per the Phase 64 follow-up), write the bytes to a same-directory temp file (`atomic_io`), then inside `fleet_db.transaction` read count and sums, refuse or insert the row, `os.replace` temp to its final id name, commit. On any exception or refusal the temp file is unlinked in `finally`.
**Why:** two concurrent uploads serialise on `BEGIN IMMEDIATE`, so the count cannot be overshot. A crash can leave only (a) a stale temp or (b) a final file without a row. Both are invisible to users and removed by the sweep. A row without a file is the bad case, hence the file is made first.

### Pattern 3: files removed after COMMIT, rows removed with the cause
**What:** same ordering as `fleet_ops` (`_move_aside` ... delete after COMMIT). Row deletion happens in the caller's transaction (`fleet_db.delete_photo_rows(conn, device_id) -> list[photo_id]`, in the style of `clear_co_managers` called from `remove_device` and `park_retired`); the returned ids are unlinked after the commit. A failure after commit leaves orphans that the sweep removes.

### Anti-Patterns to Avoid
- **Reusing `authorized_device_id` or `_require_frame_manager` for photos:** both admit admins.
- **Any user-supplied filename (multipart `filename`, `Content-Disposition`) reaching disk, DB, log or audit:** names are server-generated; the upload parser must drop the filename. The Phase 64 `normalize_upload(raw: bytes)` already takes bytes only.
- **Serving photos through `static_files` or `gallery`-style listing:** `companion/page_context.py` and `companion/app.py` list `gallery/` with `os.scandir`; never put photos under a directory that code lists.
- **Putting photo ids or counts into `audit_log.detail`:** the audit page is an admin surface.
- **Hard-delete of the device row with photo rows present and a FK:** it fails `remove_device` (byos mirror path). Clear the rows first, like co-managers.

## Storage design (details the planner needs)

**Layout.** `<state>/photos/` (0700) `/<device_id>/` (0700) `/<photo_id>.jpg` (0600). `photo_id = "ph_" + secrets.token_hex(8)`; validate with a strict regex (`\Aph_[0-9a-f]{16}\Z`, `\Z` not `$`, same as `DEVICE_ID_RE`) before any path join. The device id comes from the DB row, never request text (same invariant as `device_dirs`). Resolve with a helper like `resolve_state_dir`: refuse a symlinked `photos`, device directory or file (`os.path.islink`, `O_NOFOLLOW` on read), and check `commonpath` of the realpath. [CITED: server/device_dirs.py security invariant]

**Table (migration `_migrate_v5`, appended to `MIGRATIONS`; expand-only, one new table + index, nothing existing touched):**
```sql
CREATE TABLE device_photos (
  id TEXT PRIMARY KEY CHECK (id GLOB 'ph_[0-9a-f]*' AND length(id) = 19),
  device_id TEXT NOT NULL REFERENCES devices(id),
  size_bytes INTEGER NOT NULL CHECK (size_bytes BETWEEN 1 AND 1000000),
  width INTEGER NOT NULL, height INTEGER NOT NULL,
  uploaded_by INTEGER,            -- no FK: the row must outlive a user row, and user deletion keys on it
  created_at INTEGER NOT NULL,    -- epoch seconds, like sessions/co-managers
  seq INTEGER NOT NULL            -- per-device upload order; Phase 66 "upload order"
);
CREATE INDEX device_photos_device ON device_photos (device_id, seq);
```
Per-photo fit settings (crop/bands, position from `FitSetting`) are deliberately left out: `ALTER TABLE ADD COLUMN` is expand-only and Phase 66/67 own them. `fleet_db.SCHEMA_VERSION = len(MIGRATIONS)` updates itself. A v5 database is refused by an older release (`_refuse_if_too_new`), which is the existing rollback caveat for any migration; call it out in the deploy notes. The class docstring invariant "Nothing cascades" stays true: no `ON DELETE CASCADE`.

**Metadata holds no names.** Only random id, sizes, time, uploader id. So `fleet.db` (which is in every backup archive and shown through `dump_logical`) exposes no photo name or content. Row counts and timestamps are visible to anyone who reads `fleet.db`; that is accepted as non-content metadata (flag in the decision record).

**Live frame.** It has `state_path "."` but a normal `devices.id`; the photos tree is keyed by device id, so it works unchanged.

**Permissions.** `UMask=0027` and group `skypane` on the service units mean default files are group-readable. Photos get explicit 0700/0600. The `skypane-backup` user is deliberately not in group `skypane` [CITED: deploy/README.md Backups; provision.sh comment]. Honest limit: the VPS operator and the admin is the same person with root; the guarantee is application-level (no UI, no route, not in backups/logs), not cryptographic. Say so in the decision record.

## Privacy enforcement (PRIV-01)

1. **Service layer (the real wall):** capability gate above. Tests enumerate every public function of `photo_store` and assert each requires a `FrameManager` (signature check via `inspect`, not source text) except the explicit system-only functions (`sweep`, `purge_*`, and a render-only reader for Phase 66 that returns rendered pixels, never the stored JPEG and never a path).
2. **Route layer (for Phase 67):** add `DEVICE_MANAGER_ARG = "device-manager"` in `companion/access.py` and `MANAGER_DEVICE = Access(USER, DEVICE_MANAGER_ARG)` in `route_types.py`. In `decide`, this kind admits only owner or co-manager, **not** admin (the existing `DEVICE_OWNER_ARG` branch shows how `allow_co_manager` is threaded; add an `allow_admin` flag to `authorized_device_id`, default True so every existing caller is unchanged). Phase 65 adds no route, so the matrix test cannot cover it yet; add a pure-layer test of `decide`/`authorized_device_id` for the new kind now, and extend the matrix vocabulary (`ROUTE_POLICY` values in `companion/test_access_matrix.py`, a new `MANAGER_DEVICE` policy and its expected outcomes) so Phase 67 only has to add rows. Also add a matrix guard: any route whose path contains `photo` must have `MANAGER_DEVICE` (assertion on the route table, behaviour-level, not source text). An admin who is also the owner or a co-manager of a frame is a manager and is admitted; a pure admin gets the same 404 as an unknown path.
3. **Admin surfaces audited (nothing found today, lock it with tests):**
   - Fleet console / frame pages: no directory listing of device dirs exists (`os.scandir`/`listdir` in `companion/` only touch `gallery/`, theme previews, firmware) [VERIFIED: grep this session]. A test creates photos then fetches every admin GET route with an admin cookie and asserts no photo id, file size line or photos path appears in any body.
   - Health page and `fleet_status.json`: must not gain a photo count per user. A server-wide total is acceptable only as one aggregate number (see Open Question on whether to show it at all; recommended: show nothing in v1.3).
   - Audit log (admin page): record at most `photo.purge` with a count and the frame id; no photo ids, no filenames, no upload events. Recommended default: no audit row for upload/delete, one row per purge on frame retire/user delete with `{"count": n}`.
   - Logs: `Handler.log_message` and Caddy's access log record request lines; photo URLs must carry only random ids (never a user filename or a query string with one). Upload parsing must not log the multipart filename.
   - Export API (`/api/export/battery-history`): unrelated, unchanged.
   - `fleet_cli` and `dump_logical`: no new command prints photo rows by owner; if a `photos-sweep` CLI subcommand is added it prints counts only.
   - Backups: photos excluded (below).
   - Error messages: refusal reasons are fixed codes, never echo the filename or path.

## Real deletion (PRIV-02)

Paths where photos must go (each needs a test on the filesystem):

| Event | Today's code | Required photo action |
|-------|--------------|-----------------------|
| Owner/manager deletes one photo | new | delete row in a transaction, `os.unlink` after commit; missing file is fine |
| Owner retires own frame (`handle_remove_frame` -> `fleet_ops.retire_frame` -> `park_retired`) | keeps data (`previous_state_path`), deletes the devices row | `park_retired` clears photo rows (FK would otherwise block the DELETE); `retire_frame` unlinks the files after COMMIT |
| Admin reassigns a frame (`fleet_ops` reassign, `_reset_directory` wipes the device dir) | row kept, directory reset | purge photo rows + files in the same operation; new owner starts empty |
| `fleet_db.remove_device` (byos mirror, `fleet_cli`) | row delete only, directory untouched | clear photo rows (like `clear_co_managers`); files left to the sweep (leaf cannot touch the filesystem; callers with a root may call `photo_store.purge_frame`) |
| Account deletion (`delete_user_guarded` via `console_users.handle_delete`) | refuses while the user owns a frame (`UserOwnsFrame`), removes co-manager rows | owner case is covered because their frames were retired first. For photos a deleted user uploaded to frames they co-managed, delete rows with `uploaded_by = user_id` in the same transaction and unlink after COMMIT. `delete_user_guarded` stays filesystem-free; the companion handler calls `photo_store.purge_uploaded_by(conn, root, user_id)` around it, or the function is invoked by the handler right after commit with the id list captured inside. |
| User disabled | co-managers of their frames removed | co-managers lose access automatically (the gate checks membership); photos stay with the frame |
| Co-manager removed / leaves | membership row removed | photos stay with the frame; access gone via the gate |

**Orphan sweep** `photo_store.sweep(conn, root)`: (a) delete `photos/<id>` directories whose device id is not in `devices` (retired/removed frames), (b) delete files in a device directory with no row, (c) delete `.up-*` temp files older than 15 minutes (in-flight uploads are younger; never delete by "no row" alone while a temp is fresh), (d) delete rows whose file is missing (covers a restore of `fleet.db` without photos, and a partial failure), (e) never follow symlinks; remove symlinks found inside the tree, never their targets. Returns counts only. Run it at companion start and after any purge failure; also expose `fleet_cli photos-sweep`. Whether to also run it from the 30 s poll oneshot is a planner choice (listing one directory is cheap, but keep poll untouched if possible; recommended: companion start + CLI + nightly via an existing cheap hook only if the owner wants unattended cleanup).

**Temp files and derived renders.** Phase 64 renders are in memory (`render_photo`, `preview_png` return values; no cache on disk exists). Phase 65 must keep it so: no render cache file under `photos/`. If Phase 66 adds a derived panel image, it must live under the same device directory and be deleted by the same purge (document this as a constraint for Phase 66). Uploads never touch `/tmp` (`PrivateTmp=true` would hide them anyway); temp files are in the device directory so a purge removes them with the directory.

## Quotas (PRIV-03)

Proposed numbers (OWNER DECISION to confirm):

| Limit | Proposed | Basis |
|-------|----------|-------|
| Per frame, photos | 20 | concept note |
| Per frame, bytes | 20 MB (= 20 x the 1,000,000-byte stored-copy cap) | `STORE_MAX_BYTES` already bounds each photo, so a separate byte ceiling is a backstop, not the binding limit |
| Server-wide photos bytes | 500 MB | 40 GB NVMe VPS [CITED: deploy/README.md]; about 25 full frames; leaves the disk untouched for logs, DB, gallery and 14 local backup archives |
| Free-disk guard | refuse if free space on the state filesystem < 2 GB | protects fleet.db/WAL writes, which share the disk; one `shutil.disk_usage` call |

Refusal: `QuotaExceeded(code, limit)` with stable codes `frame_count`, `frame_bytes`, `server_bytes`, `disk_low` (plus Phase 64's `PhotoRejected` codes for bad files). Nothing is stored: the temp file is unlinked and no row is inserted. The Phase 67 UI maps codes to English/French text; Phase 65 only returns codes (no user-facing strings here).

Concurrency: count, `SUM(size_bytes)` per frame and global are read inside `fleet_db.transaction` (`BEGIN IMMEDIATE`), the same lock that takes the insert, so the check-then-insert is atomic across the companion's threads and across processes. `busy_timeout` is 5 s (`_BUSY_TIMEOUT_MS`); a busy error maps to a retryable `busy` code, not a quota refusal. The server-wide sum is computed from the table (small), not from the filesystem; the sweep keeps the two honest.

Worst case: a malicious co-manager can fill their frame's quota only; the server ceiling stops many frames. Only managers can upload, which bounds abuse to known accounts.

## Backup decision (PRIV-04) - OWNER DECISION

Facts [VERIFIED: deploy/backup/skypane_backup.py, deploy/README.md]:
- Backup is an **allow-list**: `photos/` is not in `INCLUDE_DIRS`, so it is already not archived; the nightly job would print `not in include list: photos` every night (drift line) until it is added to `KNOWN_EXCLUDED` or `INCLUDE_DIRS`.
- Archives: nightly, 14 kept on the VPS; pulled to the admin's Mac which keeps 30 newest + one per month for 12 months.
- `fleet.db` is always included (the metadata table, no names).
- Stored JPEGs are already compressed, so gzip does not shrink them; per-device `devices/<id>/` dirs are archived by name, but a top-level `photos/` is not.

| Option | Privacy | Deletion honesty | Size on this VPS | Restore |
|--------|---------|------------------|------------------|---------|
| A. Exclude (recommended) | Admin's Mac never holds user photos | Deleted means deleted (nothing keeps a copy) | none | After a restore, rows point to missing files; sweep drops them; users re-upload (their originals are on their phones) |
| B. Include | Admin receives every user's photos in each archive: contradicts "admin never sees user photos" | A deleted photo survives in up to 14 local + 30 + 12 monthly Mac archives (up to a year) | up to 500 MB x 14 archives = ~7 GB local, on a 40 GB disk, plus Mac storage | Full restore |
| C. Include only for owner-consented | Needs a per-owner consent flag, a UI, and a per-user archive that excludes non-consenting frames; the pulled archive still reaches the admin | Same retention problem for consenting users | smaller | partial; complex, more code in the backup that "runs without the server package" |

Recommendation: **A, exclude.** Implement as: add `"photos"` to `KNOWN_EXCLUDED` in `skypane_backup.py` (silences drift, documents intent), a short section in `deploy/README.md` "Backups" and a new `docs/PHOTO-STORAGE.md` decision record (decision, date, reason, consequence on restore, how to revisit), and a `deploy/tests/test_backup.py` test that builds a state dir with `photos/d_xxxxxxxx/ph_*.jpg`, runs the backup, and asserts the archive has no member under `photos/` and no drift line for it; plus a restore-side test (extract archive, run sweep, rows without files are dropped, no error). "Backup and restore behave as decided" (success criterion 4) is those two tests. Note that restored `fleet.db` may contain `device_photos` rows; the sweep reconciles.

The decision must be recorded as made by the owner, not assumed: the plan should include a `checkpoint:decision` task that records the owner's choice before the doc and the backup test are written (default A).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image validation and reduction | new checks | `server.photo.normalize.normalize_upload` | Already hardened, bytes-only, no original kept |
| Safe file write | open/write/rename | `server.atomic_io.atomic_write(path, data, mode=0o600)` / `staged_write` | Temp in same dir, fsync, no leftover on failure |
| Device-id path safety | ad-hoc `..` filters | `device_dirs.is_valid_device_id` + realpath/commonpath/islink pattern from `resolve_state_dir` | Shape check first, join only validated ids |
| Cross-process write lock for quota | new lock file | `fleet_db.transaction` (BEGIN IMMEDIATE) | Already serialises companion threads and processes |
| Ownership/co-manager lookup | SQL in the new module | `fleet_db.get_device_owner`, `fleet_db.is_co_manager` | Single source of truth, no secret columns |
| Random ids | `uuid`/time-based names | `secrets.token_hex` | Unguessable, no information in names |

## Common Pitfalls

### Pitfall 1: admin passes the gate through the generic helper
**What goes wrong:** reusing `authorized_device_id` / `_require_frame_manager` admits admins. **How to avoid:** new capability function and a separate route kind; test that a pure admin is refused at both layers. **Warning sign:** any new photo code importing `access.ADMIN`.

### Pitfall 2: `remove_device` / `park_retired` blow up on the new FK
**What goes wrong:** `DELETE FROM devices` raises IntegrityError once photo rows exist, breaking owner "remove frame" and the byos mirror. **How to avoid:** clear photo rows inside those functions (same pattern as `clear_co_managers`); add tests that remove a frame that has photos through each path.

### Pitfall 3: file left behind after a failed or refused upload
**How to avoid:** `try/finally` unlinks the temp; row-before-publish ordering; sweep for temp older than 15 min. Test with an injected failure after the temp write and after the insert.

### Pitfall 4: sweep deletes a file that is mid-upload
**How to avoid:** a file with no row is only removed when older than a grace period (15 min); temp names carry a fixed prefix (`.up-`).

### Pitfall 5: path traversal and symlinks
**How to avoid:** ids validated by regex before join, `\Z` anchors, no user text in paths, refuse symlinked `photos`/device dir/files, `O_NOFOLLOW` on reads, tests that plant a symlink to a file outside the state dir and assert it is neither read nor followed on delete (target survives, link removed).

### Pitfall 6: deleted photo still readable from derived data
**How to avoid:** no render cache on disk in 65; the Phase 66 serving cache (content-addressed by SHA-256 under `img/`) is derived from photos: Phase 66 must purge or ignore it on delete. Put this in the Phase 66 hand-off (Open Questions).

### Pitfall 7: the quota race
**How to avoid:** count and insert in one `BEGIN IMMEDIATE`; a concurrency test with N threads uploading against a quota of K ends with exactly K rows and K files.

### Pitfall 8: restore drift
A restored `fleet.db` with rows but no photos (option A) shows broken entries. Sweep (d) drops them; also run it at companion start.

### Pitfall 9: logs and audit
Do not log the multipart filename, the photo ids in `audit_log.detail`, or exception messages containing paths from upload code. Refusal codes only.

## Code Examples

### Quota check and publish in one transaction
```python
# Sketch only; derived from fleet_db.transaction (BEGIN IMMEDIATE ... COMMIT/ROLLBACK)
def add(conn, root, mgr: FrameManager, raw: bytes, now: int) -> str:
    with _NORMALIZE_SLOTS:                      # BoundedSemaphore(2)
        stored = normalize.normalize_upload(raw)   # raises PhotoRejected(code)
    tmp = _write_temp(root, mgr.device_id, stored.jpeg)   # atomic_io, 0600, ".up-<rand>"
    published = False
    try:
        with fleet_db.transaction(conn):
            _check_quota(conn, root, mgr.device_id, len(stored.jpeg))  # raises QuotaExceeded(code)
            photo_id = new_photo_id()
            fleet_db.insert_photo(conn, photo_id, mgr.device_id, len(stored.jpeg),
                                  stored.width, stored.height, mgr.user_id, now)
            os.replace(tmp, _final_path(root, mgr.device_id, photo_id))
            published = True
        return photo_id
    finally:
        if not published:
            _unlink_quiet(tmp)
```
If `os.replace` succeeds and COMMIT then fails, the file is orphaned and the sweep removes it; write the cleanup so a failed commit also unlinks the final path when known.

### Filesystem deletion test shape
```python
def test_delete_removes_the_file_from_disk(tmp_path):
    ...  # add via photo_store, assert path exists under tmp_path/"photos"/dev/...
    photo_store.delete(mgr, photo_id)
    assert not os.path.exists(path)
    assert os.listdir(frame_dir) == []          # no temp, no derived file
```

## Runtime State Inventory

Not a rename/refactor phase. New state only: `<state>/photos/` tree and `device_photos` table. Nothing existing is renamed. Existing production has no photos (Phase 64 wired nothing), so no data migration; v5 is an empty table.

## State of the Art

Nothing version-sensitive here; the work is project-internal. One relevant fact: production deploys on every merge to `main` [CITED: ROADMAP Coordination], so v5 will apply to the live `fleet.db` at first start of the new release; it is a pure `CREATE TABLE`, safe, and the previous release will refuse the newer schema on rollback (existing behaviour for any migration, `_refuse_if_too_new`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 500 MB server ceiling and 2 GB free-disk guard are reasonable for the 40 GB VPS | Quotas | Too low blocks users; too high risks disk. Owner confirms. |
| A2 | The admin and the VPS root are the same person, so the guarantee is application-level | Storage design | If a separate operator exists, stronger controls (encryption at rest) may be wanted. |
| A3 | Photos uploaded by a deleted co-manager should be deleted with the account | Deletion table | Owner may prefer photos to stay with the frame. |
| A4 | No audit rows for upload/delete is acceptable | Privacy | Owner may want an audit trail of purges. |
| A5 | Sweep trigger (companion start + CLI) is enough without a timer | Real deletion | Orphans persist until restart after a crash. Low impact. |
| A6 | Row counts and timestamps in `fleet.db` are acceptable non-content metadata | Storage design | If counts must also be hidden from admin, a different store would be needed. |

## Open Questions

1. **Quota numbers.** Proposed: 20 photos and 20 MB per frame, 500 MB server-wide, refuse below 2 GB free disk. Confirm or change.
2. **Backup (OWNER DECISION).** Recommended A (exclude), recorded in `deploy/README.md` and `docs/PHOTO-STORAGE.md`. Needs an explicit owner answer before the doc is written.
3. **Co-manager uploads on account deletion.** Recommended: delete photos uploaded by the deleted account on frames they co-managed; keep them when the co-manager is only removed.
4. **Audit and health visibility.** Recommended: no per-photo audit rows; one purge row with a count; no photo numbers on the health page in v1.3.
5. **Phase 66 hand-off.** Any serving cache derived from a photo (content-addressed `img/` files) must be deleted or ignored when the photo is deleted; the render-for-device reader must return rendered bytes only and be system-only (no user principal).
6. **Phase 67 hand-off.** All photo routes use `MANAGER_DEVICE`; the matrix policy rows are added with the routes; file input accepts JPEG/PNG/WebP and the body cap is applied while reading (Phase 64 follow-ups).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | tests | yes | 3.13.18 locally (prod 3.14) | — |
| SQLite (stdlib) | table, transaction | yes | stdlib | — |
| Pillow | normalize (Phase 64) | yes (in repo requirements) | pinned in `server/requirements.txt` | — |
| pytest, xdist, cov | tests | yes per CLAUDE.md | — | — |

No external service needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-xdist + pytest-cov, pytest-socket loopback guard [CITED: CLAUDE.md] |
| Config file | `pyproject.toml` (also holds the `[tool.mypy]` module list: add `server.photo_store`) |
| Quick run command | `pytest server/test_photo_store.py server/test_photo_privacy.py server/test_fleet_schema5.py --no-cov` |
| Full suite command | `./scripts/run-all-tests.sh` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRIV-01 | owner and co-manager read/list/add/delete; other user, anonymous (None), pure admin, disabled user, removed co-manager, unknown/malformed device id all refused with the same error | unit matrix | `pytest server/test_photo_privacy.py --no-cov` | Wave 0 |
| PRIV-01 | `decide`/`authorized_device_id` for `MANAGER_DEVICE`: admin refused unless owner/co-manager; existing kinds unchanged | unit | `pytest companion/test_access.py --no-cov` | extend existing |
| PRIV-01 | matrix vocabulary knows the manager policy; a route with "photo" in its path must be `MANAGER_DEVICE` | matrix | `pytest companion/test_access_matrix.py --no-cov` | extend existing |
| PRIV-01 | with photos present, every admin GET route body (admin cookie, in-process server) contains no photo id/path; audit page and health page too | integration | `pytest companion/test_photo_admin_surfaces.py --no-cov` | Wave 0 |
| PRIV-02 | delete removes the file; directory has no leftovers | filesystem | `pytest server/test_photo_store.py -k delete` | Wave 0 |
| PRIV-02 | retire, reassign, remove_device, user deletion each leave no photo file and no row | filesystem | `pytest server/test_photo_lifecycle.py` | Wave 0 |
| PRIV-02 | sweep: orphan dir, orphan file, stale temp, row without file, planted symlink (target survives) | filesystem | `pytest server/test_photo_sweep.py` | Wave 0 |
| PRIV-03 | 21st photo refused with `frame_count`, nothing stored (no row, no file, no temp); bytes and server ceilings; disk-low; N-thread race ends at exactly K | unit/concurrency | `pytest server/test_photo_quota.py` | Wave 0 |
| PRIV-03 | failure injected after temp write and after insert leaves no file | unit | `pytest server/test_photo_store.py -k failure` | Wave 0 |
| schema | v5 migration: fresh and upgraded v4 DB, user_version 5, existing rows untouched, FK enforced, older code refuses | unit | `pytest server/test_fleet_schema5.py` | Wave 0 (pattern: `test_fleet_schema4.py`) |
| PRIV-04 | archive has no `photos/` member and no drift line; restore + sweep reconciles rows | backup | `pytest deploy/tests/test_backup.py -k photos` | extend existing |
| PRIV-04 | decision doc exists and states the choice | docs | `pytest deploy/tests/test_docs.py` | extend existing; assert behaviour (README section served/parsed), not `.planning/` text |
| guard | `server.photo_store` import leaves `server.plane.render` and `companion` unloaded | import boundary | `pytest server/test_photo_boundaries.py` | extend existing |

All tests assert behaviour (filesystem state, HTTP bodies, archive members) per the behaviour-over-source rule; fixtures build photos with `test-support/photo_samples.py` (procedural, no binary files).

### Sampling Rate
- **Per task commit:** the quick run command above.
- **Per wave merge:** `pytest server companion/test_access*.py deploy/tests --no-cov -n auto`.
- **Phase gate:** `./scripts/run-all-tests.sh` green, ruff, mypy, `scripts/check_function_size.py` (80-line max), `scripts/check_comment_history.py check`.

### Wave 0 Gaps
- [ ] `server/test_photo_store.py`, `test_photo_privacy.py`, `test_photo_quota.py`, `test_photo_lifecycle.py`, `test_photo_sweep.py`, `test_fleet_schema5.py`
- [ ] `companion/test_photo_admin_surfaces.py` (uses existing `InProcessAppServer` fixtures)
- [ ] fleet fixture helper that seeds owner, co-manager, other user, admin, device (see `access_matrix_support.seed_matrix_fleet`)
- [ ] `pyproject.toml` mypy module entry for `server.photo_store`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no new auth) | existing sessions |
| V3 Session Management | no | existing |
| V4 Access Control | **yes** | capability-gated service layer + `MANAGER_DEVICE` route kind, default deny, same 404 for unknown and forbidden |
| V5 Input Validation | yes | `normalize_upload` (Phase 64), strict id regexes, bounded concurrency, body cap while reading (Phase 67) |
| V6 Cryptography | no | random ids via `secrets`; no encryption at rest (A2) |
| V12 Files and Resources | yes | server-generated names, 0700/0600, symlink refusal, no static serving, quota |
| V7 Logging | yes | no filenames or photo ids in logs/audit |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Admin or other user reads a photo | Information disclosure | manager-only capability, route kind without admin, same 404 |
| Path traversal / symlink via ids or planted links | Tampering | validated ids, realpath/commonpath, islink refusal, O_NOFOLLOW |
| Storage exhaustion by many or large uploads | DoS | per-frame and server-wide quotas inside the write lock, free-disk guard, bounded normalisation slots |
| Race on quota | Tampering | `BEGIN IMMEDIATE` check-and-insert |
| Deleted photo survives (backup, cache, orphan) | Information disclosure | backup exclusion, purge hooks, sweep, no on-disk render cache |
| Filename leakage via logs | Information disclosure | drop multipart filename, fixed error codes |
| Enumeration of other users' photo ids | Information disclosure | unguessable ids, uniform refusal |

## Sources

### Primary (HIGH confidence, read in this session)
- `server/fleet_db.py` (schema v1 to v4, `transaction`, `delete_user_guarded`, `remove_device`, `park_retired`, co-manager helpers, `_require_frame_manager`)
- `server/device_dirs.py`, `server/atomic_io.py`, `server/fleet_ops.py` (retire, reassign, aside/restore pattern)
- `companion/access.py`, `companion/route_types.py`, `companion/routes.py`, `companion/test_access_matrix.py`, `test-support/access_matrix_support.py`, `companion/co_managers.py`, `companion/console_users.py`
- `deploy/backup/skypane_backup.py`, `deploy/README.md` (Backups, Restore), `deploy/skypane-*.service` (users, UMask, ReadWritePaths)
- `server/photo/normalize.py`, `server/photo/__init__.py`, `server/test_photo_boundaries.py`, Phase 64 VERIFICATION, `docs/PHOTO-RENDERING.md` follow-ups
- `.planning/notes/photo-mode-concept.md`, ROADMAP and REQUIREMENTS of workstream v1-3, `.claude/CLAUDE.md`

### Secondary / Tertiary
- None; no web sources were needed (all facts are internal to the repository).

## Project Constraints (from CLAUDE.md)
- stdlib + Pillow + requests only; no new dependency.
- Code, comments, docs and commit messages in English; companion UI strings bilingual (Phase 67, not here).
- Comments explain what/why; no plan, ticket, phase or review IDs in comments (`scripts/check_comment_history.py check` in CI).
- Function-size gate: max 80 lines over `server`/`stub-server`.
- Tests: behaviour-over-source (assert served HTML/CSS/JS, filesystem, archives; never source text or `.planning/`); pytest-socket loopback guard; coverage floor; ruff; mypy module list in `pyproject.toml`.
- Every merge to `main` deploys: migration must be expand-only; plane output and `server/fixtures/golden` unchanged.
- Start work through a GSD command (this research is part of `/gsd:plan-phase`).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new packages, all primitives exist and were read.
- Architecture: HIGH for access/deletion/quota mechanics (grounded in code), MEDIUM for sweep trigger choice.
- Pitfalls: HIGH, each traced to a concrete code path (`remove_device` FK, admin bypass, `retire_frame` keeping data).
- Quota numbers and backup: MEDIUM, owner decisions.

**Research date:** 2026-11-10
**Valid until:** 30 days (internal code; invalidated if `fleet_db` schema moves past v4 before planning)
