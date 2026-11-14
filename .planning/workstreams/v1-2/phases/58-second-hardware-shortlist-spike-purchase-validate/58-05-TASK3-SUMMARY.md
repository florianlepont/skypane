# Phase 58 Plan 05, Task 3: 800x480 fault and updating screen masks - Summary

Date: 2026-11-14. Scope: Task 3 only. Nothing flashed, deployed, pushed; nothing under `hardware/` touched.
Commits: `fd4028c` (generator, generated headers, Python drift tests), `15913c7` (C selection, C tests).

## What changed

Commit 1 (generator seam):
- `firmware/tools/gen_fault_screen.py`: `--panel 1200x1600|800x480` (default 1200x1600). `render_mask`,
  `render_header_text`, `firmware_equivalent_image` and `_write_preview` take a `panel` argument; the canvas size
  comes from it (source of truth still `status.build_status(kind, size, flat=True)`). Non-default panels write
  `<name>_800x480.h`, guard `FP_FAULT_SCREEN_MASK_800X480_H` / `FP_UPDATING_SCREEN_MASK_800X480_H`, same macro
  prefixes and array symbols; the banner's regeneration command carries `--panel 800x480`. Non-default previews go
  to the system temp dir. Dither spec and "implausibly large" guard untouched.
- New generated `fault_screen_mask_800x480.h` (bbox 33,33 404x418) and `updating_screen_mask_800x480.h`
  (33,33 368x418).
- `server/test_fault_screen_mask.py`, `server/test_updating_screen_mask.py`: per-panel byte-for-byte drift tests
  (both sizes), distinct-guard/same-symbol test, 800x480 two-colour and bbox-inside-panel test.

Commit 2 (C seam):
- `fault_screen.h`: width/height from `panel_geometry.h` (`FP_FAULT_SCREEN_BYTES` formula unchanged); comments.
- `fault_screen.c`, `updating_screen.c`: include the 800x480 header under `CONFIG_FP_PANEL_7IN3E`, else the
  existing one (the `#if` is reached after `fault_screen.h` has pulled in `sdkconfig.h`). `hold_screen.h`: comment
  only. `hold_screen.c` needed no edit.
- `test_fault_screen.c`, `test_updating_screen.c`: `HOST_TEST_PROFILES: second`, header selection by profile,
  geometry assertion, golden digests per size. Digests were computed from the generator's Python port
  (`firmware_equivalent_image`, nibble-packed, FNV-1a 64). The same snippet reproduces the existing EE02 digest
  `0x507fb0b85c6e7b20` exactly. Constants: no-connection 800x480 `0x84464bd56530b5d5`, updating 800x480
  `0xee1cfad06f63fbf4`, updating 1200x1600 `0x1db87d2c3218d65a` (new, extra coverage).

## Evidence

- Portrait headers regenerate byte-identically: `git diff` on `fault_screen_mask.h` / `updating_screen_mask.h`
  is empty after running the generator for both screens.
- Including both mask headers of one screen in one translation unit fails to compile (array redefinition).
- `pytest server/test_fault_screen_mask.py server/test_updating_screen_mask.py server/test_updating_screen.py
  stub-server/test_phase47_freeze.py -n 0 --no-cov`: 44 passed. ruff and mypy clean; comment-history check exit 0.
- `sh firmware/tests/run_host_tests.sh`: 20 suites passed (adds `test_fault_screen_second` and
  `test_updating_screen_second`). C second-profile run was seen failing before the C change (geometry/digest
  assertions), then passing. `check_log_contract.sh` PASS, `check_production_config.sh static` PASS.
- EE02 before/after, `espressif/idf:v5.3.1` (image id `sha256:55ab243e...`), before = `git archive fd4028c`
  (all of Task 3's generator work, no C change), after = working tree; both mounted at `/project`, builds in
  `/out` outside the repo, `PROJECT_VER=cmp-test`, `sdkconfig.defaults;sdkconfig.ee02.defaults`; both exit 0, zero
  warnings. `sdkconfig` identical; `size -A` identical; `nm -n` identical; `.flash.text` (730202 B),
  `.iram0.text` (104319 B), `.dram0.data` (21332 B), `.flash.rodata` (496696 B) byte-identical; no `epd7`/`800x480`
  symbol in the EE02 ELF. These sizes equal the Task 2 evidence. The line-neutral edits were sufficient (the
  edited C files have no `__LINE__` user and the multi-line `#if` additions changed nothing in the image).
- Second profile (`sdkconfig.defaults;sdkconfig.second.defaults`, same container): the build now passes
  `app_main.c:57` and the whole build exits 0 with zero warnings; `skypane.bin` 1114112 bytes; the ELF has 6
  `epd7`/800x480 symbols. Task 4 owns the formal proof (`check_production_config.sh built`, VENDOR.md).

## Deviations from Plan

- The Python tests were written after the generator rather than seen failing first (they exercise the new
  `panel` argument and new files). The C tests were seen failing before the C change.
- Added a golden digest for UPDATING at 1200x1600 as extra coverage (not required).

## Unresolved

- Task 4: built-mode production-config check on the second build, VENDOR.md inventory rows, final evidence.
- `fault_screen.c`'s and `updating_screen.c`'s `.h` rationale comments still say "960 KB" for the 13.3 inch
  rationale, deliberately left as the EE02 cost argument.

## Self-Check: PASSED

Commits `fd4028c` and `15913c7` exist on `milestone/v1.2-phase-58-second-hardware`.
