# Phase 64 audit: what the second hardware type cannot yet do that the first can

Date: 2026-11-14. Two read-only audits (server, companion and deploy; firmware, tooling, CI and release) of `main` at `007069237`, asked by the owner after the Phase 58 bench: "make sure there are no other holes; the aim is to manage the second screen the way the first one is". The findings marked **checked** were re-read by hand against `main`; the others are the auditors' reading and are to be re-checked when planning. The first type is the live frame (`xiao-ee02-13in3-spectra6`, 1200x1600); the second is `seeed-ee04-7in3-spectra6` (800x480).

## Gaps (the second type cannot do what the first can)

1. **The release pipeline publishes the live frame only** (checked). `.github/workflows/firmware-release.yml` hard-codes `build-ee02` (lines 99, 135-136, 165, 177), `--hardware-type xiao-ee02-13in3-spectra6` (175, 185) and the legacy asset names; it never sets `SKYPANE_BOARD=second`. The server reads a second type from `release-<key>.json` plus `skypane-<key>-<tag>.bin` (`server/firmware_cli.py` 127-131, 203-220; `deploy/README.md` 474-490) and nothing produces them. `scripts/fw_release_manifest.py` is itself type-aware.
2. **The deploy step fetches only the live frame's assets** (checked). `.github/workflows/ci.yml` 478-490 requires `skypane-<tag>.bin` and `release.json` and downloads only those, so a typed release would never reach the server.
3. **CI never builds the second board** (checked by reading `firmware.yml`). The job builds with no `SKYPANE_BOARD`, then checks `build-ee02`; the 7.3 inch driver is compiled in CI only as host tests, and `check_production_config.sh built` is never run on a second build.
4. **The second type is invisible in production** (checked). `server/hardware.py` `available_types` exposes a gated or simulated profile only when `SKYPANE_SIM_HARDWARE=1`. With the switch off, registering a frame fails in the console, `fleet_ops` and `fleet_cli`; the poll cycle skips the type; byos answers 503 for an existing row and offers no firmware; every registry function raises; and `apply_reconcile_all` does not reconcile the type. One switch also governs the two simulated types, so setting it in production would expose them.
5. **Theme and frame previews are portrait-only** (checked). `companion/theme_preview.py` renders without a profile (`FRAME_PREVIEW_CANVAS_SIZE = (1200, 1600)`, line 306, and a portrait crop box); `companion/preview_images.py` passes no device profile.
6. **The classic landscape hold screens drop the warning marks** (checked). `server/plane/render/landscape_hold.py` has no battery-low or source-fault drawing, while the portrait holds and the active-flight card have it. The default giant layout is not affected.
7. **`firmware/provision.sh` has no live-frame guard** (auditor; unverified in detail). `flash-second.sh` refuses the live frame by port, MAC and typed confirmation; `provision.sh` does not. It did work on the second board on the bench.

## Partial

- Only the live frame's cycle reconciles update results (checked): `server/fleet_cycle.py` passes `reconcile_firmware=device.is_live`. A second-type install result is recorded only when the gate is on and its registry file exists. The bench server needed a manual reconcile for the same reason.
- Several companion places call `battery.battery_percent(mv)` with the legacy curve (`companion/console_pairing.py`, `ui_shell.py`, `sign_in.py`); harmless while the second profile copies the legacy values, wrong once they are measured.
- `import-dir` treats an unavailable typed release as a failing item, so a typed release copied by hand would fail the activation while the gate is off.
- `scripts/fw_release_manifest.py` resolves the profile against `os.environ`, so building the second manifest in CI needs the gate.
- `check_production_config.sh` covers the second board statically for dangerous options only; it does not assert the panel selection, the buffer size or a non-empty hardware key, and no CI step runs it on a second build.
- Host tests with the second profile are thin (three suites declare it); the panel-guard and wake-deadline suites have no second profile.
- The Update page shows one frame's state per type, and install and cancel are per type, not per device (the same limit applies to several live frames).
- `SIGNING.md` is worded around the live frame and has no per-type release section; `README.md` has no second-board procedure; `hardware/SECOND-HARDWARE*.md` are a spike and a validation record, not a support guide.

## Risks (firmware assumptions calibrated on the 13.3 inch panel)

- **Wake budget** (partly checked): `firmware/main/wake_deadline.h` sets `FP_WAKE_STAGE_BLIT_S` to 70 s, written for the 13.3 inch driver, while the 7.3 inch driver waits up to `BUSY_TIMEOUT_MS` = 60000 ms several times in one blit; the 7.3 inch refresh time is unmeasured. The wake budget default is 460 s.
- **Refresh spacing**: `FP_MIN_REFRESH_SPACING_S` is 60 s with help text citing the 13.3 inch panel; the second profile does not override it. 60 s is a conservative margin, but nothing is validated for the second panel and the text is wrong for it.
- **Battery sense, LED and buttons**: the pins and the divider are inherited from the live frame's board and unmeasured on the second (`sdkconfig.second.defaults`); the server's battery profile for the type is a provisional copy. Phase 58 closed without a valid discharge sample, so the battery values are to come from production use (see the Phase 64 section of the roadmap).
- `panel_guard.h` still says the image is 960 KB; cosmetic.
- Unverified: that `partitions.csv` and the flash size are right for the second board, and `provision.sh` lines 300-527. (The second dev build compiles and the unit ran it, so the unconditional `epd13in3e.h` includes are not a build break.)
- Simulated types appear together with the gated one under the single switch (see gap 4); `companion/device_scope.profile_for` falls back to the legacy profile when a type is gated off, so a second-type row would show portrait previews while byos refuses it.

## Checked and fine

The hardware profile (800x480, six inks, validated, provenance provisional); render dispatch to the landscape builders at the profile size; quiet hours, display off, battery empty and empty on landscape; the poll cycle's battery thresholds from the profile; byos context, image size, container negotiation, claim handling and pairing and retired images by profile; per-type registries and offers; the Update page's per-type chooser; the deploy backup allow-list; `build.sh` board selection; `sdkconfig.second.defaults`; the hardware key check against the server; `firmware-chain-check.yml` (hardware independent); the status and pairing screens of both orientations (Phase 58, #397); the OTA path over http in the dev profile only (#395).

## What this means for the plan

Phase 57 releases the live frame only, and Phase 58 validates the board on throwaway-key bench images; neither builds, publishes, deploys or enables the second type in production. Phase 64 covers gaps 1 to 7, the partials that matter once the type is live (reconcile, battery curve, `import-dir`), and the firmware risks, with the values measured so far (full refresh time and flash size); the battery values stay provisional until production use provides them.
