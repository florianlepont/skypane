# Photo storage

## Purpose

This document records how uploaded photos are stored, who can see them,
what limits apply, how they are deleted, and why they are not part of the
backups. How a stored photo is rendered to the panel is in
`docs/PHOTO-RENDERING.md`.

## Storage

- Layout: `photos/<device_id>/<photo_id>.jpg` under the state directory.
  Photo ids are random; nothing about a file name derives from the upload.
- Directories are created with mode 0700 and files with mode 0600.
- Only the reduced copy described in `docs/PHOTO-RENDERING.md` is kept. The
  original upload and its metadata (including the original file name) are
  never written anywhere.
- The `device_photos` table in `fleet.db` holds the metadata: frame, photo
  id, size, dimensions, creation time and an upload sequence number. It
  holds no file names.

## Who can see photos

- Only the frame's owner and its co-managers. The admin has no view of
  photos and none is built.
- Access is a capability issued by the storage service layer after checking
  the frame's owner or co-manager role. The companion routes for photos use
  the `MANAGER_DEVICE` route kind, so the same check applies to every route.
- An unknown frame, a frame the caller does not manage and a malformed id
  all get the same refusal, so a caller cannot probe for existence.
- The audit log records a count only, never photo ids. The health page shows
  no photo numbers.

### Honest limits

The admin is also the root user of the VPS. The privacy described here is
application-level: there is no admin screen, no admin route, and photos
appear in no backup and no log. It is not cryptographic. Photo files are
not encrypted at rest, so anyone with root on the VPS can read them from
disk. Row counts and timestamps in `fleet.db` are visible to anyone who can
read that file.

## Quotas

- At most 20 photos and 20 MB per frame.
- At most 500 MB of photos on the server in total.
- An upload is refused when the disk has less than 2 GB free.
- Refusals carry stable codes: `frame_count`, `frame_bytes`, `server_bytes`
  and `disk_low`. A refused upload stores nothing, neither a file nor a row.

## Deletion

A photo's row is removed first, its file afterwards, and a failure to remove
a file never leaves a row pointing at it. Photos go when:

- the user deletes one photo;
- the frame is retired, reassigned to another owner or removed;
- the account that uploaded them is deleted. A co-manager who is only
  removed from a frame, or who leaves it, does not take their photos with
  them: the photos stay on the frame.

An orphan sweep makes the photo tree and the table agree again: it removes
directories of frames that no longer exist, files without a row, stale
upload temp files and symlinks, and drops rows whose file is missing. Young
files (inside a 15 minute grace) are left alone because an upload may be in
flight. The sweep runs:

- when the companion starts;
- on demand with `fleet_cli photos sweep`, which prints the counts;
- after a file removal fails.

There is no timer.

## Backups

**Decided by the owner: photos are excluded from backups.**

Reasons:

- Privacy. The archives are pulled to the admin's Mac, and the admin must
  never receive users' photos.
- Deleted photos must really disappear. Archives are kept for up to a year
  (14 on the VPS, plus 30 recent and 12 monthly copies on the Mac), so a
  photo in an archive would outlive its deletion.
- Disk size on the 40 GB VPS.

`photos` is listed as a known exclusion in `deploy/backup/skypane_backup.py`,
so it is neither archived nor reported as drift.

Consequence on restore: if the server is lost, its photos are lost. A
restored `fleet.db` still has photo rows but no files; the orphan sweep
drops those rows at the next companion start and the photo list is
consistently empty. Users upload their photos again from their phones.

To revisit the decision, add an include entry for `photos` in the backup
script and update this section, the Backups section of `deploy/README.md`
and the backup tests together. Doing so reverses all three reasons above.

## Deploy notes

The photo table is schema version 5. It is an expand-only change: a new
table, created at the first start of the release that contains it. Rolling
back to an older release is refused by the schema version check, which is
the existing behaviour for every schema migration.

## Hand-offs

For the photo-serving work:

- Any serving cache derived from a photo must be purged, or ignored, when
  the photo is deleted.
- The render reader is system-only and returns rendered bytes only; it must
  stay out of reach of request handlers.

For the companion photo UI:

- All photo routes use `MANAGER_DEVICE` and add rows to the access matrix.
- The request body size cap is applied while the body is being read, not
  after.
- The upload parser drops the multipart file name.
- The UI maps the refusal codes (`frame_count`, `frame_bytes`,
  `server_bytes`, `disk_low`) to English and French text.
