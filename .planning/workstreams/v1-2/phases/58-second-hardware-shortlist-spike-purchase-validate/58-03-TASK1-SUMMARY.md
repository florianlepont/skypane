# Phase 58 Plan 03, Task 1: promote the driver and add the board profile - Summary

Date: 2026-11-14. Scope: Task 1 only (code, no hardware). Tasks 0, 2 and 3 are untouched: the
owner's "Oui" opened Task 1 only, and Tasks 2 and 3 need the unit on the bench. Nothing was flashed,
no hardware was used, nothing was deployed. Commit: `dc27263`.

## What changed

- `firmware/main/epd7in3e.[ch]` (new): the spiked trial driver promoted. Pure part (init table, refresh
  command, pin validator, 4 bpp packer) always compiled and host-tested; the SPI/GPIO layer exists only
  under `CONFIG_FP_PANEL_7IN3E`. The sleep path now also releases the SPI bus and drops the panel supply
  (the trial driver left both up); init failures free the bus.
- `firmware/main/Kconfig.projbuild`: `FP_PANEL` choice (default `FP_PANEL_13IN3E`) and
  `FP_PANEL_BUFFER_BYTES` (default 960000).
- `firmware/main/panel_driver.h` (new) and one added line in `firmware/main/panel.c`
  (`#include "panel_driver.h"`): with the default it defines nothing; with the 7.3" choice it maps
  `epd_init/epd_blit/epd_sleep` to the new driver. `firmware/tests/check_panel_diff.sh` now allows
  exactly that include (a removed or any other added line in panel.c still fails it).
- `firmware/sdkconfig.second.defaults` (new): `CONFIG_FP_HW_REV="proto-ee04"`, seven panel pins each with
  a source comment (Seeed_GFX2 `XIAO_ePaper_Board_Configs.h`), `CONFIG_FP_PANEL_BUFFER_BYTES=192000`,
  USB-Serial/JTAG console (GPIO43/44 are UART0), keys/battery/LED inherited from the EE02 profile and
  marked unmeasured. The signed-app lines are inherited from `sdkconfig.defaults` (layered on it only);
  project name stays `skypane`, one key (option S).
- `firmware/build.sh`: optional `SKYPANE_BOARD=second` (default `ee02` resolves to identical defaults and
  directories as before).
- `firmware/flash-second.sh` (new): refuses without a port; refuses a port equal to
  `SKYPANE_LIVE_FRAME_PORT` before touching it; reads and prints the chip MAC (read-only) before any
  write; refuses a MAC equal to `SKYPANE_LIVE_FRAME_MAC`; then needs the MAC typed back (a piped "yes"
  fails); then signature check, write, read-back. Refusal paths exercised with a fake `esptool` on PATH
  (port missing rc=1, live port rc=3, live MAC rc=3, wrong confirmation rc=3, unsigned image rc=1): the
  fake logged only `read-mac` calls, never a write.
- `firmware/tests/test_epd7in3e.c` (new, picked up by the naming convention): packed size 192000 and
  nibble order, init table order and lengths and resolution bytes, refresh command, rejection of wrong
  length / short buffer / null / invalid colours (including 4) with nothing written, pin validator.
- `firmware/tests/check_production_config.sh`: the static checks also cover `sdkconfig.second.defaults`
  and fail if `CONFIG_FP_PANEL_7IN3E=y` appears in `sdkconfig.defaults`, the EE02 profile or the dev overlay.
- `firmware/VENDOR.md`: new "Second hardware driver" section (Seeed_GFX2 source URL, branch/date/hash pin,
  MIT notice "Copyright (c) 2026 Seeed Studio", what was taken, what was not), rows for the changed vendored
  files, entries for every new file. The MIT notice is also reproduced in the `epd7in3e.c` header.
  The init table was re-compared on 2026-11-14: the raw `Driver_ED2208.cpp` still hashes to
  `7350cf3dc95d7116...`, the value recorded by the spike.

## Evidence

Image: `espressif/idf:v5.3.1`, image id and RepoDigest
`sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d` (local tag of
`mirror.gcr.io/espressif/idf:v5.3.1`, same image as the spike; not compared with Docker Hub's own digest
because Docker Hub rate-limits). The Docker daemon had to be started by hand (`dockerd` in the
background); the image was already present. All builds wrote to a directory outside the repository from
a copy of the sources, `idf.py build`, `PROJECT_VER=cmp-test` for both sides.

1. EE02 unchanged. Built the ee02 profile from `HEAD` before the change and from the working tree after it.
   `diff before/sdkconfig after/sdkconfig` reports exactly three added lines and nothing else:
   `CONFIG_FP_PANEL_13IN3E=y`, `# CONFIG_FP_PANEL_7IN3E is not set`, `CONFIG_FP_PANEL_BUFFER_BYTES=960000`
   (the new Kconfig symbols at their defaults; no existing line changed). `xtensa-esp32s3-elf-size -A`
   identical, `nm -n` symbol lists identical, `.flash.text`, `.iram0.text`, `.dram0.data` and
   `.flash.rodata` dumped with objcopy byte-identical, no `epd7` symbol in the image. `skypane.bin` has the
   same length (1376256) but not the same hash (`def41319...` vs `8fef3f5f...`): the file differs in its
   header/app-descriptor build metadata, not in code or data; this is why the proof is made at section level.
   `check_production_config.sh built` passes on the after build.
2. New profile builds. `sdkconfig.defaults;sdkconfig.second.defaults`: exit 0, "Project build complete",
   `skypane.bin` 0x150000 bytes (43 percent of the app partition free), zero warnings in the log,
   resolved config shows `CONFIG_FP_HW_REV="proto-ee04"`, `CONFIG_FP_PANEL_7IN3E=y`,
   `CONFIG_FP_PANEL_BUFFER_BYTES=192000`, the seven pins, the signed-app chain with no secure boot and no
   eFuse option; `epd7in3e_init/blit/sleep` linked, the 13.3" `epd_init/epd_blit` garbage-collected.
   `check_production_config.sh built` passes on it too.
3. Checks: `sh firmware/tests/run_host_tests.sh` 16 suites passed (incl. `epd7in3e: all cases pass` and the
   panel diff); `sh firmware/tests/check_production_config.sh static` PASS;
   `stub-server/test_phase47_freeze.py` 21 passed; `python3 scripts/check_comment_history.py check` exit 0;
   `scripts/check-attribution.sh` PASS (it covers `server/assets` only, so it does not see firmware files;
   the firmware attribution is `firmware/VENDOR.md`); also green: `server/test_wake_stats_firmware_agreement.py`,
   `stub-server/test_ota_offer.py`, `test-support/test_ci_shards.py`, `test-support/test_check_comment_history.py`,
   `server/test_fault_screen_mask.py`, `server/test_updating_screen.py` (194 passed).

## Deviations from Plan

1. [Rule 3 - Blocking] `firmware/tests/check_panel_diff.sh` (not in the plan's file list) would have failed on
   the one added include line in `panel.c`; its allow-list was widened by exactly
   `#include "panel_driver.h"`. Alternative considered: rewriting the header include in panel.c, rejected
   because a removed line fails the check by design.
2. [Rule 3 - Blocking] `firmware/build.sh` (not in the plan's file list) gained `SKYPANE_BOARD`; without it the
   second profile cannot be built by the documented script, which Task 2 needs.
3. `firmware/tests/check_production_config.sh` extended (not in the plan's file list) so the new defaults file
   is held to the same rules and cannot leak the 7.3" choice into the live frame's profile.
4. Binary-identity claim is at section/symbol level, not whole-file hash (see evidence 1).

## Unresolved / for later work

- The 7.3" data path is not done and is out of this task: `FP_IMAGE_BYTES` is 960000 in `api_client.c`,
  `state_machine.c` and the fault/updating screens are 1200x1600, and the server renders 1200x1600. On the
  second profile the device would reject an 800x480 download and `epd7in3e_blit` would be handed a 960000
  byte buffer. Task 2's "first successful panel refresh" needs either a tiny test-pattern path or the
  native-landscape layout work of 58-04; this needs a decision before the unit arrives.
- Sleep state between refreshes is a vendor disagreement (Seeed: power off only; Waveshare: deep sleep). The
  driver follows Waveshare (power off, deep sleep, full init next draw), which is the safe choice with a
  full init on every draw; its standby current is unmeasured.
- Nothing about the driver is hardware verified: SPI chip-select per row, BUSY polarity and timing, 10 MHz
  clock, the 60 s BUSY timeout. EE04 key GPIOs, battery divider and User LED are inherited from EE02 unmeasured.
- The paper-spike copy `firmware/spike-7in3/` is left in place as evidence for `SECOND-HARDWARE-SPIKE.md`;
  it duplicates the table now in `main/epd7in3e.c`.
- The `merge main into the branch before finishing` rule of the plan is for the end of the whole plan, not
  done here (branch was cut from the latest `origin/main`).

## Self-Check: PASSED

All listed files exist, commit `dc27263` exists on `milestone/v1.2-phase-58-second-hardware`, no file under
`hardware/` was touched.
