---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 02
subsystem: firmware-ci
tags: [ci, firmware, second-hardware]
requires: []
provides: [board-aware built check, build-second CI job, partition bound test]
affects: [.github/workflows/firmware.yml]
key-files:
  created:
    - firmware/tests/fixtures/production_config/ee02/sdkconfig
    - firmware/tests/fixtures/production_config/second/sdkconfig
    - deploy/tests/test_production_config_board.py
    - server/test_firmware_partition_bound.py
  modified:
    - firmware/tests/check_production_config.sh
    - .github/workflows/firmware.yml
metrics:
  completed: 2026-11-14
---

# Phase 64 Plan 02: Second board in CI Summary

`check_production_config.sh built <dir> [ee02|second]` now asserts board identity (panel option, buffer bytes, revision, hardware key derived from server.hardware), and firmware.yml has a new `build-second` job with the same 90 percent OTA size gate.

## Commits
- 8452da8 test: board argument, fixtures, behaviour tests (14 cases)
- 8df60a7 ci: build-second job and partition-bound test

## Deviations from Plan
- Fixture sdkconfig files are matched by firmware/.gitignore (`sdkconfig`), so they were added with `git add -f`.
- The ee02 board check asserts the panel option unset and the legacy key only (no revision), as the plan specified.
- The partition-bound test additionally checks that the `0x... * 90 / 100` literal(s) in firmware.yml equal the ota_0 size.

## Not done
- The draft-PR run of `build-second` was not performed: this executor was told not to push. The `# CONFIG_FP_PANEL_7IN3E is not set` and `CONFIG_FP_PANEL_BUFFER_BYTES=192000` line forms remain unproven against a real build until the first CI run; run URL to be recorded then. The grep forms are all in `check_board`.

## Verification
- pytest deploy/tests + server/test_firmware_partition_bound.py: 260 passed, 1 skipped (pre-existing openssl skip)
- check_production_config.sh static: PASS; check_panel_diff.sh: PASS; ruff and comment-history guard clean
- firmware-release.yml untouched; firmware.yml diff is additions only.

## Self-Check: PASSED
