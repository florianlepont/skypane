---
phase: 50-common-image-format
plan: 02
subsystem: server
tags: [image-format, container, fixtures]
requires: []
provides:
  - server/image_container.py (encode_container, decode_container, negotiate_version, ImageContainerError)
  - golden fixtures and line manifest shared with the C reader
affects: [50-03, 50-04]
key-files:
  created:
    - server/image_container.py
    - server/test_image_container.py
    - firmware/tests/fixtures/image_container/ (22 .bin, manifest.txt, README.md, generate_fixtures.py)
  modified: [pyproject.toml]
requirements-completed: [IMG-01]
metrics:
  tasks: 3
  files: 28
completed: 2026-10-30
---

# Phase 50 Plan 02: Image container module and golden fixtures Summary

Stdlib-only 24-byte SPIM container codec (`<4sBBHHHBBHII`) with a decoder whose rejection classes are pinned by 22 committed fixtures and a manifest the C reader will iterate.

## Tasks and commits

1. `2eba46b` feat: image_container.py, registered in the mypy files list and strict override.
2. `f65e68d` test: deterministic generator, 22 .bin fixtures (including the 7x3 odd-pixel pair and the extended-header case), manifest.txt, README.
3. `7c6dc2c` test: server/test_image_container.py.

## Deviations from Plan

None in behaviour. Notes: fixture bytes total 760; `du -sk` reports 104 only because of 4 KiB filesystem blocks, so the plan's "under 20 KB" criterion is met on content size, not on `du` block size.

## Verification

- pytest server/test_image_container.py: 49 passed.
- ruff, mypy (17 files), check_function_size, check_comment_history: clean.
- Generator re-run leaves the tree unchanged; panel_format.py and byos_server.py untouched.

## Self-Check: PASSED
