# Phase 58 Plan 05: the 800x480 data path for the evaluation unit - Summary

Date: 2026-11-14. Code only, no hardware. Nothing was flashed, deployed, pushed or ordered. Nothing under
`hardware/` and no Phase 57 file was touched. Per-task write-ups: `58-05-TASK1-SUMMARY.md` (server profile and
BYOS path, commits `2efbebc`), `58-05-TASK2-SUMMARY.md` (image size from the panel Kconfig value, `499ff4b`,
`2ed3724`), `58-05-TASK3-SUMMARY.md` (800x480 fault and updating masks, `fd4028c`, `15913c7`, `b9b6876`).
Task 4 (this evidence) changes only `firmware/VENDOR.md` inventory rows.

One-liner: the Seeed EE04 7.3 inch unit now has a simulation-gated server profile that serves 192000-byte
frames, a firmware profile whose download size, fault screen and updating screen follow the panel Kconfig
choice, and a section-level proof that the EE02 image did not change.

## Evidence

### 1. EE02 before and after (T-58-13)

Image `espressif/idf:v5.3.1`, id `sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d`
(local tag of `mirror.gcr.io/espressif/idf:v5.3.1`). `dockerd` was already up. Both sides were built with
`idf.py -B build-ee02 -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.ee02.defaults" -DPROJECT_VER=cmp-test`
from a `git archive` copy under the session scratchpad (outside the repo): before = `2efbebc` (the plan's first
commit, which has no firmware change), after = `HEAD` of Task 3 (clean working tree). Both exit 0.

- Resolved `sdkconfig`: `diff` reports no difference at all.
- `xtensa-esp32s3-elf-size -A`: identical (only the file name on the header line differs).
- `xtensa-esp32s3-elf-nm -n`: identical.
- `objcopy -O binary --only-section` dumps, byte-identical (`cmp`): `.flash.text` 730202 bytes, `.iram0.text`
  104319, `.dram0.data` 21332, `.flash.rodata` 496696.
- No `epd7` or `800x480` symbol in the EE02 image; the portrait `fp_fault_mask_bits` and `fp_updating_mask_bits`
  (0x26499 = 156825 bytes each) are linked, `blit ok bytes=960000 sha256_ok=1` is present as the literal.
- `skypane.bin` has the same length (1376256, 0x150000, 43 percent of the app partition free) but not the same
  hash (`37e01803...` vs `2cf331da...`), as already seen in the earlier proof: the file header and app descriptor
  carry build metadata; the code and data sections are identical, which is why the proof is made at section level.
- `sh firmware/tests/check_production_config.sh built <after build dir>`: PASS.

No difference to explain. The line-neutrality fallback of the plan was not needed.

### 2. Second profile (T-58-14)

`sdkconfig.defaults;sdkconfig.second.defaults`, PROJECT_VER cmp-test, same container, built from a clean
`git archive` of `HEAD`: exit 0, "Project build complete", zero warnings in the log. Resolved config:
`CONFIG_FP_PANEL_7IN3E=y`, `# CONFIG_FP_PANEL_13IN3E is not set`, `CONFIG_FP_PANEL_BUFFER_BYTES=192000`.
`skypane.bin` 0x110000 bytes, 0x140000 (54 percent) of the 0x250000 app partition free (EE02: 0x150000, 43 percent).

- Masks: `nm -S` shows `fp_fault_mask_bits` of size 0x5346 = 21318 bytes (51 x 418, the 404 x 418 NO CONNECTION mask
  of `fault_screen_mask_800x480.h`) and `fp_updating_mask_bits` of size 0x4b1c = 19228 bytes; the portrait ones
  (0x26499 each) are absent. `.flash.rodata` falls from 496696 (EE02) to 223704 bytes.
- Driver: `epd7in3e_init`, `epd7in3e_blit`, `epd7in3e_sleep`, `epd7_init_table`, `epd7_pins_valid` are linked;
  the `blit ok bytes=%u sha256_ok=1` format (byte count from FP_IMAGE_BYTES) is present and the `bytes=960000`
  literal is not.
- `sh firmware/tests/check_production_config.sh built <second build dir>`: PASS.
- Nothing was flashed.

### 3. Gates

| Gate | Result |
|------|--------|
| `sh firmware/tests/run_host_tests.sh` | 20 suites passed (includes `test_panel_geometry` and both profiles) |
| `sh firmware/tests/check_production_config.sh static` | PASS |
| `sh firmware/tests/check_log_contract.sh` | PASS (unmodified) |
| `pytest stub-server/test_phase47_freeze.py -q -n 0 --no-cov` | 21 passed |
| `pytest server/test_hardware.py stub-server/test_evaluation_unit_image.py stub-server/test_device_fleet.py server/test_fault_screen_mask.py server/test_updating_screen_mask.py -q -n 0 --no-cov` | 82 passed |
| Full suite, gate OFF: `pytest server stub-server companion -q -n auto --no-cov` | 10815 passed, 3649 skipped, 401 s (6m41) |
| Full suite, gate ON: `SKYPANE_SIM_HARDWARE=1 ...` same command | 10815 passed, 3649 skipped, 400 s (6m40) |
| `server/.venv/bin/ruff check server stub-server test-support firmware/tools` | All checks passed |
| `server/.venv/bin/mypy` (module list of `pyproject.toml`) | no issues in 45 source files |
| `python3 scripts/check_function_size.py check --max 80 server stub-server` | 1093 functions, none over 80 |
| `python3 scripts/check_comment_history.py check` | exit 0 |

Why the two full runs are identical: both really ran (two separate 6.5-minute runs, the user CPU time differs by
5 seconds). The tests that exercise the registry gate set or clear `SKYPANE_SIM_HARDWARE` themselves (monkeypatch
or the subprocess environment), so the ambient value changes neither the collected set nor the result.
The 3649 skips are all environmental: 3642 browser tests skip because the Playwright headless shell is not
installed in this sandbox, 7 need a non-root euid. In CI a missing browser fails the job (see CLAUDE.md), so
browser tests were NOT run here. `playwright install --only-shell chromium` was attempted; a third run with
browsers did not finish within 30 minutes and was stopped, so there is no browser-enabled result. This plan
changes no companion file (`git diff ca91b40..HEAD` outside `firmware`/`.planning` touches only `server/`, a `stub-server/` test and
`test-support/`), so the risk is low but the claim "full suite incl. browser" is not made. The coverage gate
(`./scripts/run-all-tests.sh`) was not run; the suite was run with `--no-cov` as requested.

## Deviations from Plan

- [Rule 3 - environment] The plan names `./scripts/run-all-tests.sh` for the whole suite; the orchestrator
  instruction was the `--no-cov` form, so the coverage floor was not re-measured here.
- The plan said the new Kconfig symbols were added by the previous plan; indeed before/after sdkconfig is
  identical (no added lines), unlike the 58-03 proof which compared against a commit without them.

## Known Stubs

None. The 7.3 inch path is not hardware verified (no unit yet); the battery values of the new profile stay
provisional until 58-04.

## Unresolved

- Browser-enabled full-suite run (needs the Playwright shell; CI covers it).
- Coverage floor not re-measured locally.
- Plan 58-05 does not wire the Phase 50 image container into the firmware (Phase 57).
- 58-03 Tasks 2 and 3 and 58-04 still need the unit on the bench.

## Self-Check: PASSED

Build artefacts and dumps are in the session scratchpad (not in the repo). Commits `2efbebc`, `499ff4b`,
`fd4028c`, `15913c7` exist on `milestone/v1.2-phase-58-second-hardware`; only `firmware/VENDOR.md` and this
summary changed in Task 4.
