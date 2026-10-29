---
phase: 49-per-hardware-ota-registry
plan: 01
subsystem: ota
tags: [firmware, esp-image, validation, stdlib]
requires: []
provides:
  - server.firmware_image (CHIP_IDS, AppImage, parse_app_image, validate_for_target)
  - test-support/skypane_fw_image.build_image
  - FirmwareTarget.max_app_bytes
affects: [49-02, publish gate, CLI, CI manifest]
tech-stack:
  added: []
  patterns: [fixed-offset length-checked parsing, field-named ValueError]
key-files:
  created:
    - server/firmware_image.py
    - server/test_firmware_image.py
    - test-support/skypane_fw_image.py
  modified:
    - server/hardware.py
    - server/test_hardware.py
    - test-support/test_test_support.py
    - pyproject.toml
decisions:
  - "Segment count is bounded only by the segment walk staying inside the file: ESP_IMAGE_MAX_SEGMENTS could not be confirmed locally (no IDF headers), so no upper count was hard-coded"
  - "Descriptor string and structure errors surface from parse_app_image before the chip check in validate_for_target"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-02]
---

# Phase 49 Plan 01: Image parser and firmware size bound Summary

Stdlib ESP application image parser and per-target validator (chip id, project name, version, appended digest, signature sector structure, size), a synthetic image builder for tests, and a firmware size bound on FirmwareTarget separate from the display bound.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 Builder and parser | f9856f4b | firmware_image.py, skypane_fw_image.py, tests, mypy lists |
| 2 max_app_bytes | f9856f4b (field), 8f513586 (tests) | The field landed in the first commit because the validator needs it |

## Deviations from Plan

- The TDD red phase was not committed separately: implementation and tests were written together and went green at first run. Commits are therefore feat plus test, not test then feat.
- Task 2's field change is in the Task 1 commit (dependency), the Task 2 tests are in their own commit.
- Segment-count upper bound omitted (plan assumption A1 fallback).

## Verification (run)

- pytest server/test_firmware_image.py test-support/test_test_support.py server/test_hardware.py: 74 passed
- pytest server stub-server deploy/tests (-n auto, --no-cov): 1655 passed, 5 skipped (root permission bits, openssl backdating)
- server/.venv/bin/ruff check server test-support: pass
- server/.venv/bin/mypy: pass (16 files)
- scripts/check_function_size.py check --max 80 server stub-server: pass
- scripts/check_comment_history.py check: pass (rc 0)
- Not run: coverage gate, companion/hardware test suites.

## Known Stubs

None.

## Self-Check: PASSED

Files and commits f9856f4b, 8f513586 exist.
