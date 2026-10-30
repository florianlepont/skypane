---
phase: 50-common-image-format
plan: 04
subsystem: stub-server
tags: [image-format, negotiation, byos]
requires: [50-01, 50-02]
provides:
  - BYOS serves the SPIM container to frames announcing X-Img-Fmt
key-files:
  modified: [stub-server/byos_server.py, stub-server/test_image_negotiation.py]
requirements-completed: [IMG-02]
metrics:
  tasks: 2
  files: 2
completed: 2026-10-30
---

# Phase 50 Plan 04: BYOS image negotiation Summary

The display handler now selects the served bytes with one helper, `_served_image`, built on `server.image_container` (imported, not duplicated). An announcing frame gets the 960,024-byte container. Every other frame gets the unmodified 960,000-byte panel file.

## Changes

- `byos_server.py`: imports `image_container` and `HEIGHT, WIDTH` from `server.panel_format`. Adds `_served_image(announced, image)`. `do_GET` gets one new line, and `served` replaces `image` in the sha256 and `_publish_image` calls. The header value is never stored or logged. No new display JSON key.
- `test_image_negotiation.py`: new `test_announce_*` tests. They cover the container for X-Img-Fmt 1, 2 and 999, the hash and URL over the served bytes, the frozen key set, dual fetch of the announcing and legacy URLs, state files unchanged, and an identity check that the BYOS module uses the shared encoder.

The announce tests failed before the handler edit and passed after.

## Commit

- 7cc142e feat(50-04): serve the image container to announcing frames

## Verification

- Negotiation, freeze, poll-cycle, hardening and OTA tests: 126 passed, 1 skipped (root ignores directory permission bits).
- Plan 01 legacy tests and their constants are unchanged and green. The Phase 48 freeze test is green.
- Full `./scripts/run-all-tests.sh`: 4281 passed, 548 skipped. The skips are Playwright Chromium not installed in this sandbox, plus root-permission skips.
- ruff, mypy (17 files), function-size (606 functions, none over 80) and comment-history are clean.

## Deviations from Plan

None. The `from server.panel_format import WIDTH, HEIGHT` amendment was applied.

## Fallback note

`server/` ships beside `stub-server/` (the existing `from server import ...` line), so the import is expected to work when deployed. If it does not, the fallback is a duplicated encoder pinned by a behaviour test. No deploy was performed.

## Self-Check: PASSED
