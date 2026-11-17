---
phase: 57-combined-legacy-frame-firmware-release
plan: 03
subsystem: firmware
tags: [c, esp-idf, image-container, headers, ci]
requires: [57-01]
provides:
  - widened download with length gate and completeness output
  - X-Img-Fmt / X-Hw-Type on the display request only
  - imgc_parse before panel draw with sticky fallback flag
  - check_hw_type_key.sh drift guard, CI size step
affects: [firmware/main/api_client.c, firmware/main/state_machine.c]
key-files:
  created: [firmware/tests/check_hw_type_key.sh]
  modified:
    - firmware/main/api_client.h
    - firmware/main/api_client.c
    - firmware/main/state_machine.c
    - firmware/main/nvs_schema.h
    - firmware/main/Kconfig.projbuild
    - firmware/sdkconfig.ee02.defaults
    - .github/workflows/firmware.yml
requirements-completed: [OTA-04]
completed: 2026-11-14
---

# Phase 57 Plan 03: Wake-path wiring Summary

The wake path now accepts a legacy 960000-byte body or a container, validates it with `imgc_parse` after the radio is off and before the panel draw, announces the container and the hardware key on the display request, and stops announcing after a container failure.

## Commits
- ea0f1a03: download gate (`fp_body_len_plausible`), buffer 960256, SHA-256 over all received bytes, `body_len_out` / `complete_out` set on every path, `capability_headers`, both names deleted in `clear_request_headers`, `FP_NVS_IMGFMT_BAD`, `SKYPANE_HW_TYPE` Kconfig and EE02 default.
- b0b24226: `imgc_parse` before `fp_panel_draw(view.payload)`; fp_diag line (format, status, crc_ms); parse failure frees the buffer, sets the sticky flag, step `verify`, no hash write; latch on a complete rejected body via `fp_imgfmt_latch_bad`.
- 817fead5: `check_hw_type_key.sh`, `server/hardware.py` in both path filters, size step (limit 90 percent of 0x250000) after the build. No artifact upload.

## Verification (what ran locally)
- `firmware/tests/run_host_tests.sh`: 15 suites passed, panel-diff PASS.
- `check_production_config.sh static`: PASS. `check_log_contract.sh`: PASS (blit line unchanged, count 1). `check_panel_diff.sh`: PASS.
- `check_hw_type_key.sh`: PASS; with the Kconfig default temporarily changed it exited 1, then was restored.
- `scripts/check_comment_history.py check`: exit 0. Workflow YAML parses; 0 `upload-artifact`.

## NOT verified
No local ESP-IDF build exists (Docker not running). The C changes in `api_client.c`, `api_client.h` and `state_machine.c` were NOT compiled; they only touch ESP-IDF code, so the host tests do not cover them. `firmware.yml` in CI is the compile gate, and `check_production_config.sh built` plus the new size step run only there. Nothing was flashed or bench-tested.

## Deviations from Plan
- `complete_out` counts an oversize 200 response as complete (the network delivered it; only reading stopped). Otherwise the oversize rejection could never latch. Truncation or read errors give false.
- The download's `transfer_ok` does not require `esp_http_client_is_complete_data_received`; the hash still has to match, and requiring it could break HTTP/1.0 close-delimited legacy responses (the LAN stub). It is used only for `complete_out`.
- `fp_api_download` has no single goto label: early returns (before any transfer) report 0/false through initialisation at entry; every post-transfer path goes through one final assignment block.
- `check_production_config.sh` does not enumerate Kconfig symbols, so it was not changed.
- A `git checkout` used to revert a temporary Kconfig edit during the drift test also discarded my uncommitted Kconfig change; it was re-applied before committing.

## Known Stubs
None.

## Self-Check: PASSED
Commits ea0f1a03, b0b24226, 817fead5 exist; forbidden files untouched.
