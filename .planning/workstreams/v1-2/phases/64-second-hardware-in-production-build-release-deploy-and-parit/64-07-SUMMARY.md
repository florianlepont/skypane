---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 07
subsystem: firmware
tags: [wake-budget, epd7in3e, host-tests]
requires: []
provides:
  - profile-conditional FP_WAKE_STAGE_BLIT_S (190 s second, 70 s live)
  - second profile wake budget 700 s
affects: [64-12, 64-13]
key-files:
  modified:
    - firmware/main/wake_deadline.h
    - firmware/main/Kconfig.projbuild
    - firmware/main/panel_guard.h
    - firmware/sdkconfig.second.defaults
    - firmware/tests/test_wake_deadline.c
    - firmware/tests/test_panel_guard.c
decisions:
  - "Second blit stage B = 3 * 60 + 10 = 190 s (formula-derived, unmeasured)"
  - "Second wake budget 700 s: normal 370 s, OTA 665 s with guard wait 90"
metrics:
  tasks: 2
  completed: 2026-11-14
---

# Phase 64 Plan 07: Second-profile wake budget Summary

The 7.3 inch profile now has a blit stage derived from the driver's three bounded busy waits and a wake budget of 700 s that the existing compile-time asserts check. The live frame's constants are unchanged.

## Commits
- 8dd35f1 test: failing second-profile cases (RED)
- a8ea3b6 feat: blit stage, budget, texts (GREEN)

## RED evidence
Before the header change, `test_wake_deadline_second` failed with `Assertion FP_WAKE_STAGE_BLIT_S == 190 failed`.

## Results
- `sh firmware/tests/run_host_tests.sh`: 22 suites, all passed, including test_wake_deadline_second and test_panel_guard_second. check_panel_diff passed.
- `check_production_config.sh static`: PASS.
- No change to main/panel.c or main/epd13in3e.c; no new `config` symbol in Kconfig.projbuild.
- The legacy branch of FP_WAKE_STAGE_BLIT_S is still 70u, and the ee02 host pass still pins 250 and 425.

## Not verified
- Docker daemon is not running here, so `firmware/build.sh` for ee02 and second was not run. The ee02 section-level identity proof is deferred to plan 64-13, and CI builds both boards.
- The 190 s and 700 s figures are formula-derived and unmeasured. The measured replacement is plan 64-12.

## Deviations from Plan
- [Rule 1 - adjustment] The legacy 70 s-based assertions in test_wake_deadline.c are now skipped in the second-profile run, since they only hold for the live board.
- test_panel_guard has no frame-size logic, so its second-profile case checks that CONFIG_FP_PANEL_BUFFER_BYTES is 192000 and that the guard's spacing decisions are unchanged.
- One earlier run of run_host_tests.sh showed check_provision_guard failures (exit 99). They did not reproduce on a re-run, and the cause is outside this plan's files. They were probably caused by parallel executors changing files in the shared working tree.

## Self-Check: PASSED
