---
phase: 49-per-hardware-ota-registry
plan: 04
subsystem: ota
tags: [tests, fixtures, firmware-image]
requires: [49-01, 49-03]
provides:
  - every release-publishing test fixture builds a valid synthetic ESP image via build_image(version)
affects: [49-05 publish-time image validation]
tech-stack:
  added: []
  patterns: [shared synthetic image builder instead of a production bypass flag]
key-files:
  created: []
  modified:
    - server/test_firmware_registry.py
    - server/test_firmware_reconcile.py
    - server/test_firmware_cli.py
    - server/test_retired_notifications.py
    - stub-server/test_ota_offer.py
    - deploy/tests/test_release_manifest.py
    - companion/test_update_page.py
    - companion/test_update_actions.py
    - companion/test_browser_update.py
    - companion/test_browser_ux_helpers.py
decisions:
  - "No bypass flag; fixtures import build_image from test-support/skypane_fw_image.py (already on pythonpath)"
  - "Descriptor version equals the manifest version in every publishing fixture"
  - "Tests needing a different image for the same version use build_image(version, size=16384); the default image is already 8192 bytes, so size=8192 yields identical bytes"
  - "Rejection tests that do not reach image content (symlink, release-tag, bad commit, no git commit) keep junk payloads"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-02]
---

# Phase 49 Plan 04: Valid synthetic images in publishing fixtures Summary

All ten test files that publish releases now publish structurally valid synthetic images (signed, descriptor version equal to the manifest version) with sha256 and size computed from the built bytes, so plan 05's publish-time validation lands on a green suite. Tests only; no production code changed and no bypass flag exists.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Server-side fixtures | ed01e6b7 | server/test_firmware_registry.py, test_firmware_reconcile.py, test_firmware_cli.py, test_retired_notifications.py |
| 2 Offer, manifest, companion fixtures | 90208c09 | stub-server/test_ota_offer.py, deploy/tests/test_release_manifest.py, companion/test_update_page.py, test_update_actions.py, test_browser_update.py, test_browser_ux_helpers.py |

## Deviations from Plan

- test_release_manifest.py: `_make_image` no longer takes `fill` and exact size. A signed synthetic image is at least 8192 bytes, so the two assertions that compared the manifest size to a literal (2048, 512) now compare against the image file's real length. The oversized-image test still requests MAX_IMAGE_BYTES + 1 bytes via `size=`. Intent is unchanged.
- test_ota_offer.py streaming test: the random payload became `build_image(..., size=3 * chunk + 100)`; the multi-chunk read property is still exercised.
- No shared conftest changed (companion fixtures live in the listed test files). No production code changed.
- The plan's verify subset reports 305 tests at baseline (not 207); all pass before and after.

## Verification (run)

- Touched files together (`-n auto --no-cov`, with Playwright browsers from the scratchpad and SKYPANE_REQUIRE_BROWSER=1): 346 passed.
- Full `pytest server stub-server deploy/tests test-support companion -n auto --no-cov -q` with the same browser env: 4473 passed, 8 skipped (root-euid permission-bit skips), 0 failed.
- ruff check .: passed. mypy: no issues in 16 source files. check_function_size.py check --max 80 server stub-server: 568 functions, none over 80. check_comment_history.py check: exit 0.

## Known Stubs

None.

## Self-Check: PASSED

Commits ed01e6b7 and 90208c09 exist; all ten modified files are in those commits.
