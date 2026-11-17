# Phase 58 Plan 05, Task 2: image size from the panel Kconfig value - Summary

Date: 2026-11-14. Scope: Task 2 only (firmware device side, code only). Tasks 1 (commit 2efbebc), 3 and 4
are not part of this pass. Nothing was flashed, deployed, pushed or ordered. Commit: `499ff4b`.

## What changed

- `firmware/main/panel_geometry.h` (new): pure C, includes `sdkconfig.h` only when `__has_include` finds it;
  `FP_PANEL_WIDTH/HEIGHT` (800x480 under `CONFIG_FP_PANEL_7IN3E`, else 1200x1600), `FP_PANEL_BYTES` =
  width*height/2, `_Static_assert` against the formula and against `CONFIG_FP_PANEL_BUFFER_BYTES` when defined.
- `firmware/main/api_client.h`: `FP_IMAGE_BYTES` is `((unsigned)FP_PANEL_BYTES)` (960000, unsigned, on EE02);
  includes `panel_geometry.h`.
- `firmware/main/api_client.c`: two comments only (the 960000 wording); same line count, no executable change.
- `firmware/main/state_machine.c`: `#if CONFIG_FP_PANEL_BUFFER_BYTES == 960000` keeps the literal
  `blit ok bytes=960000 sha256_ok=1` line; otherwise `blit ok bytes=%u sha256_ok=1` with `FP_IMAGE_BYTES`.
  The file has no `__LINE__` user (no `ESP_ERROR_CHECK`/`assert`), so the added lines are neutral.
- `firmware/main/app_main.c`: line 57 replaced in place, now `FP_FAULT_SCREEN_BYTES == FP_PANEL_BYTES`
  (same line count; `panel_geometry.h` arrives through the existing `api_client.h` include).
- `firmware/tests/run_host_tests.sh`: opt-in `HOST_TEST_HEADER_ONLY` and `HOST_TEST_PROFILES: second` markers.
  The second run is named `<suite>_second` and counted as a suite. Suites without markers run as before.
- `firmware/tests/test_panel_geometry.c` (new, written first and seen failing with the header missing).

## Evidence

Host gates (all run after the change):
- `sh firmware/tests/run_host_tests.sh`: 18 suites passed (16 before plus `test_panel_geometry` and
  `test_panel_geometry_second`); default 1200x1600=960000, second 800x480=192000=`EPD7_PACKED_BYTES`.
- `sh firmware/tests/check_log_contract.sh` (unmodified): PASS.
- `sh firmware/tests/check_production_config.sh static`: PASS.
- `stub-server/test_phase47_freeze.py` (`-n 0 --no-cov`): 21 passed.
- `python3 scripts/check_comment_history.py check`: exit 0.

EE02 before/after, `espressif/idf:v5.3.1` container (image id
`sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d`, local tag of
`mirror.gcr.io/espressif/idf:v5.3.1`; dockerd was already up). Before = `git archive HEAD` (2efbebc, before
any firmware change of this plan), after = working tree with this task; both mounted at `/project` so embedded
paths match, fresh build directories outside the repository, `idf.py build` with `PROJECT_VER=cmp-test`,
`sdkconfig.defaults;sdkconfig.ee02.defaults`. Both exit 0, zero warnings.
- `diff before/sdkconfig after/sdkconfig`: no output (identical; the new Kconfig symbols were added by 58-03).
- `xtensa-esp32s3-elf-size -A`: identical apart from the first header line (the ELF path).
- `nm -n`: identical.
- `.flash.text` (730202 B), `.iram0.text` (104319 B), `.dram0.data` (21332 B), `.flash.rodata` (496696 B)
  dumped with objcopy: byte-identical.
- No `epd7` or `800x480` symbol in the EE02 image.
- `skypane.bin`: same length 1376256, 67 bytes differ (build metadata of the image header/app descriptor),
  as in the 58-03 Task 1 evidence; the proof is at section level.
- `check_production_config.sh built <after build dir>`: PASS.
- The line-neutral edits were sufficient; no fallback comparison was needed.

`hardware/logtools.py` (read only): it contains no reference to `blit`, `sha256_ok`, `bytes=` or `960000`; it does
not parse the `blit ok` line, so `bytes=192000` cannot be rejected by it (nothing to accept or refuse).

## Second profile at this point

Built `sdkconfig.defaults;sdkconfig.second.defaults` as a probe: it fails by design at `app_main.c:57`
(`FP_FAULT_SCREEN_BYTES == FP_PANEL_BYTES`), because the fault and updating screens are still 1200x1600 until
Task 3. Everything else compiled (`api_client.c`, `epd7in3e.c`, no other error). The full second-profile build
and its evidence belong to Task 4 after Task 3.

## Deviations from Plan

None. The `HOST_TEST_PROFILES` run is named `<suite>_second`. `FP_IMAGE_BYTES` is `((unsigned)FP_PANEL_BYTES)`
rather than a literal, which the section-level proof shows compiles to the same image.

## Unresolved

- Second-profile build fails until Task 3 supplies 800x480 screen masks (expected, and the assertion is the
  mechanism that stops a mismatched build).
- `firmware/VENDOR.md` inventory entries for the new files are Task 4's.

## Self-Check: PASSED

Files exist, commit `499ff4b` exists on `milestone/v1.2-phase-58-second-hardware`, nothing under `hardware/` touched.
