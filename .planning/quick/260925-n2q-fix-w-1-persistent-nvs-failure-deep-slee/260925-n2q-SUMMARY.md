---
phase: quick
plan: 260925-n2q
subsystem: firmware
status: complete
tags: [esp-idf, nvs, deep-sleep, backoff, log-contract]
key-files:
  created:
    - firmware/main/nvs_boot.c
    - firmware/main/nvs_boot.h
    - firmware/tests/test_nvs_boot.c
  modified:
    - firmware/main/app_main.c
    - firmware/main/fault_screen.h
    - firmware/main/fault_inject.c
    - firmware/main/fault_inject.h
    - firmware/main/Kconfig.projbuild
    - firmware/build.sh
    - firmware/tests/check_log_contract.sh
    - firmware/tests/check_production_config.sh
    - firmware/tests/test_fault_screen.c
    - firmware/VENDOR.md
    - .planning/phases/34-firmware-resilience-power-security-cleanup/34-VERIFICATION.md
---

# Quick task 260925-n2q: Phase 34 warning W-1 resolved

A persistent NVS failure at boot now deep-sleeps a fixed 300 s instead of
panic-looping.

## What changed

- **Decision helper** `nvs_boot.c` (pure, host-tested): `fp_nvs_init_action()`
  erases and retries once, and only on `ESP_ERR_NVS_NO_FREE_PAGES` /
  `ESP_ERR_NVS_NEW_VERSION_FOUND`. Every other code, and any failure after the
  erase, is UNUSABLE. `fp_nvs_fail_sleep_s()` = `fp_backoff_seconds(0)` = 300 s.
- **Fixed interval, why 300 s:** the backoff counter lives in NVS, so it
  cannot grow. 300 s is what any first failure sleeps. A transient flash fault
  recovers at the normal pace, and a permanent one costs a sub-second wake with
  the radio off every 5 min instead of a 100 % duty-cycle hot loop. It is never 0.
- **app_main.c**: the three `ESP_ERROR_CHECK`s (init, erase, open) are gone.
  `nvs_fail_and_sleep("nvs", err)` logs `fp_boot nvs unusable err=<name>`, then
  `poll fail step=nvs backoff_n=0 sleep_s=300`, then the timing line, and deep-sleeps.
  `fp_panel_on_boot()` (RTC only) moved above NVS init so the panel guard's
  accounting holds on that path. `_Static_assert`s pin the mirrored error codes.
- **Fault screen:** `nvs` is excluded, and `fault_screen.h` documents why: the
  "already shown" sentinel lives in NVS, so the screen would redraw on every
  wake. The path never calls `maybe_draw_fault_screen()`, and
  `test_fault_screen.c` asserts the exclusion.
- **Log Line Contract:** VENDOR.md lists `nvs` (14 tokens). `check_log_contract.sh`
  now extracts `nvs_fail_and_sleep("nvs", …)` and matches the row's `<a|b|…>`
  list exactly. Before this change it passed on substrings: `nvs` matched
  `nvs_flash_init` elsewhere in VENDOR.md.
- **Bench hook** `SKYPANE_FAULT=nvs` (dev only): `fp_fault_inject_nvs()` logs
  `SKYPANE-FAULT-INJECT nvs` and forces the init result to `ESP_FAIL`. It is
  refused in production by `check_production_config.sh`.

## Verification

- `run_host_tests.sh`: 10 suites pass (new `test_nvs_boot`).
- `check_log_contract.sh` PASS. Before VENDOR.md was updated it failed on `nvs`, which proves the tightened check is not vacuous.
- `check_production_config.sh static` PASS, `built firmware/build-ee02` PASS.
- `scripts/check_comment_history.py check` exit 0.
- `firmware/build.sh` built the production image locally in `espressif/idf:v5.3.1`.
  Dev builds: see the PR.

Not observed on hardware yet. A future bench session can flash
`SKYPANE_PROFILE=dev SKYPANE_FAULT=nvs` and expect `poll fail step=nvs backoff_n=0 sleep_s=300`
and then `sleep enter sleep_s=300` on every wake.
