---
phase: 57-combined-legacy-frame-firmware-release
plan: 01
subsystem: firmware
tags: [c, host-tests, crc32, fault-screen, backoff]
requires: []
provides:
  - table-driven imgc_crc32
  - fp_body_len_plausible, fp_hw_type_valid, fp_imgfmt_announce, fp_imgfmt_latch_bad
  - fault-screen allow-list without auth and enrol
affects: [57-03]
key-files:
  modified:
    - firmware/main/image_container.c
    - firmware/main/validate.c
    - firmware/main/validate.h
    - firmware/main/fault_screen.c
    - firmware/main/fault_screen.h
    - firmware/tests/test_image_container.c
    - firmware/tests/test_validate.c
    - firmware/tests/test_fault_screen.c
    - firmware/tests/test_sleep_decision.c
requirements-completed: [OTA-04]
completed: 2026-11-14
---

# Phase 57 Plan 01: Pure firmware building blocks Summary

Table CRC32, four pure validation gates, and an auth/enrol-free fault-screen allow-list, all proven by host tests.

## Commits
- b585fc7e: table CRC with bitwise-reference test (960000-byte body, check vector, header_len 24 and 255)
- 4c1b5e61: validate.c gates with boundary tests (960023/960024/960255/960256, grammar, latch table)
- 80f5e230: fault screen no longer draws for auth/enrol; 12-failure backoff sequence reaches 21600 and one OK resets to 300 / n=0

## Verification
- `firmware/tests/run_host_tests.sh`: 15 suites passed, check_panel_diff PASS.
- `scripts/check_comment_history.py check`: exit 0.
- Only files in files_modified were changed.

## Deviations from Plan
None in scope. FP_CONTAINER_MIN_HEADER (24) is defined in validate.h because image_container.h does not export it. The mask size comment was corrected to ~157 KB (123 x 1275 bytes). test_sleep_decision.c already declares backoff.c, so run_host_tests.sh was not changed.

## Known Stubs
None.

## Self-Check: PASSED
