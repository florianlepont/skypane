---
phase: 50-common-image-format
plan: 01
subsystem: stub-server
tags: [regression, image-format, byos]
requires: []
provides:
  - legacy byte-identity regression with committed reference constants
affects: [50-02, 50-04]
key-files:
  created: [stub-server/test_image_negotiation.py]
  modified: []
requirements-completed: [IMG-02]
metrics:
  tasks: 2
  files: 1
completed: 2026-10-30
---

# Phase 50 Plan 01: Legacy reference regression Summary

Legacy display response and 960,000-byte panel are pinned to constants (REFERENCE_PANEL_SHA256 = 46d99bcb...8378, REFERENCE_DISPLAY) captured from the unmodified byos_server.py (git-diff guard passed first).

## Tasks

1. Reference capture and three `test_legacy_*` tests (bytes, hash and JSON, key set vs freeze list).
2. Junk X-Img-Fmt matrix (8 cases) and state-files-unaffected tests.

Both tasks touch the same new file and were committed together in one commit: see git log for `test(50-01)`.

## Deviations from Plan

- [Rule 1 - Bug] The state-file comparison blanks `*_at` timestamps (`received_at`, `reported_at`), because those fields change on every poll and made a byte-for-byte comparison fail. Everything else is compared exactly.
- Tasks 1 and 2 share one commit rather than two.

## Verification

- test_image_negotiation.py plus test_phase47_freeze.py: 34 passed (run twice).
- ruff, check_comment_history, check_function_size: clean.
- byos_server.py and server/ unmodified.

## Self-Check: PASSED
