---
phase: 64-photo-pipeline-server-only
plan: 01
subsystem: photo
tags: [pillow, upload-hardening, jpeg, icc, exif]
requires: []
provides:
  - "server.photo.normalize: PhotoRejected, StoredPhoto, normalize_upload and limit constants"
  - "test-support/photo_samples.py procedural upload builders"
affects: [64-02, 64-03, 64-04, 64-05]
tech-stack:
  added: []
  patterns: ["decoder allowlist via Image.open(formats=...)", "header-first pixel cap before load", "reason-code-only exceptions"]
key-files:
  created:
    - server/photo/__init__.py
    - server/photo/normalize.py
    - test-support/photo_samples.py
    - server/test_photo_normalize.py
  modified:
    - pyproject.toml
key-decisions:
  - "Stored copy: baseline sRGB JPEG, long edge <= 2048, <= 1,000,000 bytes via quality ladder then 0.85 shrink"
  - "EXIF orientation is applied inside the decode boundary so unreadable EXIF maps to corrupt"
requirements-completed: [PHOTO-01]
duration: 25min
completed: 2026-11-10
---

# Phase 64 Plan 01: Strict upload normaliser Summary

`normalize_upload(raw) -> StoredPhoto` turns untrusted bytes into one metadata-free baseline sRGB JPEG (long edge <= 2048, <= 1 MB) or raises `PhotoRejected` with a bare reason code; no file is written and the original is unreachable.

## Tasks

1. Procedural samples and rejection path - commit 812c562
2. Decode, orient, colour-manage, reduce, encode - commit 225473f

## Verification

- `pytest server/test_photo_normalize.py`: 53 passed
- ruff clean, mypy clean (45 files, module added to files and strict override list), function-size gate (none over 80), comment-history gate rc=0
- `git diff --stat` over server/plane, server/fixtures/golden, server/panel_format.py, hardware: empty

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Orientation helper direction for 6 and 8**
- **Found during:** Task 2
- **Issue:** `orient_for_exif` in the test builders used the inverse rotation for orientations 6 and 8, so the upright check failed.
- **Fix:** swapped ROTATE_90 / ROTATE_270 for those two cases.
- **Files modified:** test-support/photo_samples.py
- **Commit:** 225473f

### Other notes

- The third `except Exception` was avoided: `exif_transpose` runs inside `_decode`, so the broad catch stays at the two decode boundaries (`_open_checked`, `_decode`) as planned.
- Red-first ordering was not strictly observed for Task 1: the rejection tests and the implementation were written together and first run green.
- Test builders add `swapped_primaries_profile` (sRGB with red/green primaries exchanged) because Pillow cannot create a non-sRGB RGB profile; used to observe the ICC conversion.

## Known Stubs

None.

## Threat Flags

None. T-64-01 to T-64-06 are mitigated and covered by tests; T-64-07 (concurrency) is accepted and left to the route and the freeze doc.

## Self-Check: PASSED

Files and commits 812c562, 225473f verified present.
