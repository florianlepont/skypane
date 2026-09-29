---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 16
subsystem: hardware
tags: [ota, esp32s3, hardware-session, signing, rollback, secure-boot-v2]

# Dependency graph
requires:
  - phase: 42-01 .. 42-15
    provides: "the whole OTA pipeline: registry, byos offer and /fw/ route, firmware OTA with rollback and signed-app verification, UPDATING screen, notifications, release workflow, gated deploy import, chain guard, firmware_cli"
provides:
  - "hardware/BRINGUP-LOG.md 'OTA hardware session': per-row results (H42-00a .. H42-12), measured facts, deviations and not-observed items, and a corrected procedure sheet for the next run"
  - "hardware/logs/phase42/: redacted serial captures, eFuse before/after, and server-side evidence (server-evidence.txt, H42-01-release.txt, H42-05-chain-guard.txt)"
  - "42-VALIDATION.md manual-only rows closed with their H42 evidence"
affects: [phase-42-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bench images are signed with a throwaway bench key and flashed with SKYPANE_BENCH_PUBKEY; the real key only signs release and refusal-test images"
    - "Server-side registry/device_report evidence backs rows whose serial capture falls in the USB re-enumeration window"

key-files:
  created:
    - hardware/logs/phase42/ (42 files: 37 serial captures, efuse-before/after, H42-01-release.txt, H42-05-chain-guard.txt, server-evidence.txt)
  modified:
    - hardware/BRINGUP-LOG.md
    - .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-VALIDATION.md

key-decisions:
  - "Closed the validation record rather than reporting gaps: H42-06 .. H42-12 all passed, with the non-observations kept explicit (no serial capture for H42-06, confirm-before-sleep proven indirectly by H42-07)"
  - "Captures were redacted in place before the first commit: SSID replaced with <ssid>, Wi-Fi BSSIDs with <bssid>, LAN ip/mask/gateway with <lan-*>, ANSI escapes stripped; the device MAC (already public) is kept"
  - "Procedure text of the sheet was corrected where the session proved it wrong; pass criteria and expectations were not edited"

requirements-completed: [OTA-02, OTA-03, OTA-04, OTA-07, OTA-10, OTA-11, OTA-12]

coverage:
  - id: D1
    description: "Signed update installs on the real frame and survives the following deep-sleep wake; UPDATING screen seen on the glass"
    requirement: "OTA-02, OTA-03, OTA-07"
    verification:
      - kind: hardware
        ref: "H42-00a (bench-cycle-01 serial), H42-06 and H42-07 (server evidence, developer observation)"
        status: pass
    human_judgment: true
    rationale: "H42-06 has no serial capture; confirm-before-sleep is proven indirectly by H42-07"
  - id: D2
    description: "Unsigned, tampered and wrongly signed images are refused at step=finish and the release reaches Failed after three attempts"
    requirement: "OTA-04"
    verification:
      - kind: hardware
        ref: "H42-08, H42-09a, H42-09b serial captures plus registry events"
        status: pass
    human_judgment: false
  - id: D3
    description: "A crashing trial image rolls back; recovery from factory works; eFuses untouched"
    requirement: "OTA-03, OTA-12, OTA-04"
    verification:
      - kind: hardware
        ref: "H42-10 (server rollback events, companion banner), H42-11, H42-12 (efuse-before.txt == efuse-after.txt)"
        status: pass
    human_judgment: true
    rationale: "The panic line and the rollback boot were not captured on serial; the UPDATING screen during the display-off install was not confirmed on glass"
  - id: D4
    description: "Real tag, gated signing, gated deploy and firmware import, and the chain guard against the production host"
    requirement: "OTA-10, OTA-11"
    verification:
      - kind: other
        ref: "H42-01 (release run 36575555701, deploy run 36575975888, fw-v1.0.1 runs 36581150646 / 36581557153), H42-05 (run 36578611110)"
        status: pass
    human_judgment: false

# Metrics
duration: ~5h hardware session (2026-09-29, about 13:20 to 17:50 UTC) plus results recording
completed: 2026-09-29
status: complete
---

# Phase 42 Plan 16: OTA hardware session Summary

**OTA-12 proven on the real EE02 frame: signed fw-v1.0.1 installs and survives deep sleep, unsigned/tampered/wrong-key images are refused, a crashing trial image rolls back, factory recovery works, and the eFuses are byte-identical before and after**

## Performance

- **Duration:** about 5 h of hardware session with the developer, plus recording
- **Completed:** 2026-09-29
- **Tasks:** 3 (Task 1 sheet, Task 2 hardware session run by the developer and the orchestrator, Task 3 record and close)
- **Files:** 2 modified, 42 evidence files added

## Accomplishments

- Every row of the session passed except H42-00b, which is not measurable without a code change (the firmware logs no stack high-water mark; no stack-overflow fault appeared in any capture). H42-00a, 01, 02, 03, 04, 05, 06, 07, 08, 09a, 09b, 10, 11 and 12 are PASS, several with recorded non-observations (below).
- The first real releases went through the whole pipeline: `fw-v1.0.0` on `c9acfb51` (release run 36575555701, five assets, image sha256 equal to `release.json`, signature verified against the committed public key, deploy run 36575975888 printed `added fw-v1.0.0` on a same-sha redeploy) and `fw-v1.0.1` on `4be7351c` (release run 36581150646, deploy run 36581557153).
- The signed `fw-v1.0.0` was flashed over USB once (bootloader, partition table, otadata, `factory` at 0x20000 and `ota_0` at 0x270000, both read-backs match); `fw-v1.0.1` then installed over the air: offered 14:29:48, trial 14:31:26, installed 14:33:02 UTC, and kept reporting across many deep-sleep wakes with no rollback.
- The Wi-Fi stop-then-connect fix ran on hardware for the first time: `H42-00a-bench-cycle-01.log` shows the UPDATING screen, the Wi-Fi driver re-init, a fresh `sta ip:`, the whole `ota step=` sequence, "Signature verified successfully" and `ota switched`, with no assert or abort.
- Refusals: the unsigned image fails at `step=finish` (`ESP_ERR_OTA_VALIDATE_FAILED`), the tampered image (signed with the real offline key, then a byte flipped) fails the image checksum, and an intact image signed with a throwaway key fails with "image valid, signature bad". Each reached Failed after three attempts and the device stayed on `fw-v1.0.1`.
- The forced-crash image (`fw-v1.0.1-crash`, signed with the real key) was rolled back three times (server events 17:22:54, 17:29:31, 17:32:32) and the companion showed the rollback banner. After erasing `otadata` the frame booted `factory` (`fw-v1.0.0`) and installed `fw-v1.0.1` from there with the display off.
- `efuse-before.txt` and `efuse-after.txt` are identical (192 lines, 112 fuse lines); no `burn_*` command was run. The private key was only decrypted inside a `--network none` container for the tamper and crash images, and removed afterwards (verified).
- Measured: an OTA wake takes about 62 s from wake to `ota switched` (62062 ms in H42-00a cycle 01, 62973 ms to `step=finish` in H42-09b); battery 4188 mV on USB at first boot and 3984 mV before H42-06.

## Task Commits

1. **Task 1: Preflight and session sheet** - `68b7705e` (docs)
2. **Task 2: Hardware session** - no commit; run by the developer with the orchestrator, results supplied for Task 3 (the defect it found was fixed separately in PR #159, `4be7351c`)
3. **Task 3: Record results and close the validation record** - `e451b7d8` (docs)

## Files Created/Modified

- `hardware/BRINGUP-LOG.md` - the "OTA hardware session" section: results table with Observed and Evidence per row, measured facts, deviations and not-observed items, and the corrected procedure text
- `.planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-VALIDATION.md` - Manual-Only rows closed with H42 evidence, plan 42-16 rows marked green
- `hardware/logs/phase42/` - redacted serial captures (`H42-00a-*`, `H42-04-*`, `H42-06-ota-*`, `H42-08-unsigned-*`, `H42-09a-tampered-*`, `H42-09b-wrongkey-*`, `H42-10-crash-*`), `efuse-before.txt`, `efuse-after.txt`, `H42-01-release.txt`, `H42-05-chain-guard.txt`, `server-evidence.txt`

## Decisions Made

- The validation record is closed, not reported as gaps: no failing row. Items that could not be observed stay listed explicitly in the sheet and in 42-VALIDATION.md.
- Redaction happened before anything was committed (SSID, BSSIDs, LAN addresses, ANSI colour codes); the device MAC is kept because BRINGUP-LOG.md already publishes it. No bearer token, enrolment secret or Wi-Fi password is present.
- The sheet's procedure text was corrected wherever the session showed it wrong (hosts, `firmware_cli` invocation, signed bench images, RESET-only board, literal commands, backoff notes), without touching the pass criteria.

## Deviations from Plan

### Real defects found by the session

**1. [Rule 1 - Bug] An unsigned image does not boot at all**
- **Found during:** H42-00a (`H42-00a-first-boot.log`)
- **Issue:** `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` makes the running app check its own signature at startup: `E secure_boot_v2: No signatures were found for the running app`, `abort()`, a reboot loop (74 reboots in the capture). The sheet had assumed an unsigned dev image was exempt.
- **Fix:** PR #159 (`4be7351c`, merged before this record): `firmware/flash.sh` and `firmware/SIGNING.md` refuse an unsigned image in every profile. H42-00a was redone with both bench images signed by a throwaway bench key (kept outside the repo, deleted with `rm -P`) and flashed with `SKYPANE_BENCH_PUBKEY`; the sheet text is corrected.

**2. [Rule 3 - Blocking] Wrong device host and `PRODUCTION_HOST` secret**
- **Found during:** H42-00a (HTTP 404 "Cannot GET", `H42-00a-first-poll.log`) and H42-05
- **Issue:** the api-base and the `PRODUCTION_HOST` GitHub secret named `cortege.algernon.ovh`, an unrelated app on the same VPS. The device host is `vps-1440bce3.vps.ovh.net`.
- **Fix:** the secret was corrected during the session, the frame was re-provisioned (with `devices_cli --replace`), and the sheet names the hosts.

**3. [Rule 3 - Blocking] The sheet's `firmware_cli` invocation failed**
- **Issue:** `ubuntu` cannot `cd /opt/skypane/current`, so `FWCLI` and `bench_import` did not work.
- **Fix:** the `cd` now runs inside the service user's shell (`sudo -u skypane /bin/sh -c 'cd ... && exec ...' firmware_cli <sub>`); the sheet is corrected.

**4. [Deferred - follow-up] The UPDATING screen stays on the glass after a failed OTA attempt** until the next successful poll redraws. Not fixed here; recorded as a follow-up.

### Other deviations (all accepted, all recorded in the sheet)

- First provisioning stored a truncated Wi-Fi password; the frame was re-provisioned twice, each time re-registered with `--replace`.
- H42-03 was done during H42-00a (the H42-04 USB flash does not touch the `secret` partition); the `H42-03-provision.txt` extract was not saved.
- H42-00b is N/A (not measurable without a code change).
- After a crash rollback, the rolled-back `fw-v1.0.1` sees `reset reason=panic` and backs off without polling, so the rollback is reported only at the next wake (300/600/1200 s). The developer pressed RESET to skip the waits, and the same for the refusal rows' backoff.
- Commands from the app's "Run" buttons open new terminal tabs (variables lost); the board has only a RESET button and `esptool --after no-reset read-mac` parks the chip in the loader. The sheet says to use literal commands.
- Capture naming: `H42-06-ota-02` .. `-04` are the same wakes as `H42-08-unsigned-01` .. `-03`.

### Not observed

- H42-04: `ota boot outcome=none` on the first boot (lost in the USB re-enumeration window).
- H42-06: no serial capture (USB was unplugged); the `ota confirmed` before `sleep enter` ordering was not seen on serial, proven indirectly by H42-07. Battery mV after the OTA wake not recorded.
- H42-07: `reset reason=deepsleep` and `ota boot outcome=none` not captured; the server shows `fw-v1.0.1` over many wakes with no rollback.
- H42-08: the failure push was not checked on the phone. The poll journal shows no notification error (`notify.py` logs only on failure): recorded as sent, not seen by the developer.
- H42-10: the panic line and the `ota boot outcome=rollback` boot not captured (about 2 s window during USB re-enumeration); rollback is proven by server events and the companion banner. The display-off UPDATING check moved to H42-11.
- H42-11: the UPDATING screen during the display-off install was not confirmed on the glass.
- Free heap and main-task stack high-water mark: not logged by the firmware. The wake interval before the session was not recorded.

**Total deviations:** 3 auto-fixed defects (one fixed in PR #159), 1 deferred follow-up.
**Impact on plan:** none on the outcome; the defects were found by exactly the kind of check this session exists for.

## Issues Encountered

None beyond the deviations above. Bench releases (`fw-v9.9.9-bench`, `fw-v1.0.1-unsigned`, `-tampered`, `-wrongkey`, `-crash`) remain in the VPS store by design (every release is kept, T-42-73 accepted). No `fw-v*` tag exists other than `fw-v1.0.0` and `fw-v1.0.1`.

## Known Stubs

None. This plan adds documentation and evidence only.

## Threat Flags

None. Mitigations held: T-42-70 (only `espefuse.py summary` run; before/after identical), T-42-71 (captures redacted, secret greps clean), T-42-72 (offline key decrypted only inside a `--network none` container and removed).

## Next Phase Readiness

Phase 42 is ready for verification. Open follow-ups: clear the UPDATING screen after a refused OTA attempt, and consider polling before backing off after a panic reset so a rollback is reported at the first wake.

## Self-Check: PASSED

- `hardware/BRINGUP-LOG.md`, `42-VALIDATION.md`, `hardware/logs/phase42/efuse-after.txt` exist; every evidence path in the results table exists.
- Commits `68b7705e` and `e451b7d8` are in the log.
- Redaction greps (SSID, BSSID, LAN addresses, `61913e6b`, 64-hex bearer pattern) are clean; `check_comment_history.py check` passes.
