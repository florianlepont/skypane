---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 06
subsystem: hardware-bringup
tags: [esp32-s3, esp-idf, esptool, e-paper, spectra6, usb-serial-jtag, deep-sleep, xiao-ee02]

# Dependency graph
requires:
  - phase: 01-05
    provides: The Phase 1 firmware image (wake -> poll -> download -> verify -> blit -> sleep dispatcher), the frozen Log Line Contract, and a stub server proven green by an automated protocol harness
provides:
  - A physically assembled XIAO ESP32-S3 Plus + EE02 driver board + 13.3" Spectra 6 panel, verified booting real firmware end to end
  - firmware/flash.sh - host-side flash with read-back byte verification against build-ee02/inkframe.bin
  - firmware/monitor.sh - serial console capture to hardware/logs/
  - hardware/logs/first-light.log - a captured, contract-matching wake -> poll -> blit -> sleep cycle
  - EE02 board profile (firmware/sdkconfig.ee02.defaults) verified against real hardware - no correction needed
  - A measured full-refresh duration (~31.5s) for Phase 2's rendering-cadence planning
  - A documented diagnosis that "device appears then disappears on USB" during this board's normal operation is deep-sleep cutting USB power, not a fault - resolves a multi-session-blocking false alarm for good
affects: [01-07, 01-08, 02-plane-view-end-to-end-slice (rendering-cadence UX given ~31.5s refresh), 04-low-battery-indicator (deep-sleep USB-power-off behavior matters for any future USB-power-based battery signal)]

tech-stack:
  added: [esptool (installed via Homebrew, not pip)]
  patterns:
    - "Race-capture serial diagnosis: poll `ls /dev/cu.usbmodem*` at ~150ms intervals and attach a background reader the instant the port appears, when a device's awake window is too short for a manually-timed `monitor.sh` invocation to reliably catch."
    - "Force a real (non-hash-skip) blit for verification by temporarily swapping the stub server's served image to the repository's own second deterministic test pattern (`make_test_panel.py --pattern quadrants`), then restoring the original afterward and triggering one more wake to redraw it - avoids touching NVS or the device's persisted state."
    - "esptool's own reset sequence (`firmware/flash.sh`, `--before default-reset --after hard-reset`) can be used as a repeatable, scriptable substitute for a physical reset-button press to force an immediate fresh boot on demand."
    - "Cross-reference macOS's own kernel-level USB enumeration log (`/usr/bin/log show --predicate 'eventMessage contains \"<VID>\"'` - note: `log` bare is a zsh builtin, not `/usr/bin/log`) against application-level evidence (a server's own request log) before concluding a USB device is crashing versus just power-cycling as designed."

key-files:
  created:
    - firmware/flash.sh
    - firmware/monitor.sh
    - hardware/logs/first-light.log
    - hardware/BRINGUP-LOG.md
  modified:
    - hardware/BOM.md

key-decisions:
  - "esptool installed via Homebrew rather than pip, keeping Phase 1's zero-pip-install property intact; flashing stays native (not containerised) because Docker Desktop's macOS USB passthrough is unreliable"
  - "The EE02 board profile required zero pin/config corrections - firmware/sdkconfig.ee02.defaults remains byte-identical to upstream after real-hardware verification"
  - "'Device appears then disappears on USB' is documented as expected deep-sleep behavior (esp_deep_sleep_start() powers off USB Serial/JTAG outside the RTC domain), not a defect - closes a symptom that looked like a boot loop across several prior sessions"

patterns-established:
  - "Pattern: when a USB-based embedded device's console capture window is too short to catch manually, race-poll for the port and attach a reader the instant it appears rather than assuming a hardware fault"
  - "Pattern: verify deep-sleep-driven USB disappearance is by design (not a crash) by checking for absence of Guru Meditation Error / Brownout detector panic text in a captured log, not just by the port vanishing from the host's device list"

requirements-completed: [DEVICE-03]

coverage:
  - id: D1
    description: "Device flashed with byte-for-byte read-back verification against the built firmware image"
    requirement: DEVICE-03
    verification:
      - kind: manual_procedural
        ref: "firmware/flash.sh verify_flash() - 'verify_flash: OK - flashed application region matches build-ee02/inkframe.bin byte-for-byte (1050368 bytes)', reproduced across two separate flashes this session"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full wake -> poll -> download -> verify -> blit -> deep-sleep cycle captured live on real hardware, matching the frozen Log Line Contract"
    requirement: DEVICE-03
    verification:
      - kind: manual_procedural
        ref: "hardware/logs/first-light.log - contains wake reason=power-on boot_count=17, poll ok sleep_s=300 hash_skip=0, blit ok bytes=960000 sha256_ok=1, sleep enter sleep_s=300 (all four contract lines, automated regex-verified against firmware/VENDOR.md's Log Line Contract)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Correct six-band palette image physically visible on the glass - colour order, seam continuity, full coverage, orientation, and clean sleep entry"
    requirement: DEVICE-03
    verification:
      - kind: manual_procedural
        ref: "Task 3 checkpoint - developer confirmed all five checks pass on the physical 13.3in Spectra 6 panel (2026-08-25)"
        status: pass
    human_judgment: true
    rationale: "Requires a human physically looking at real e-paper glass to judge colour accuracy, seam alignment, and coverage - no camera or sensor access to the device from this environment."

duration: 74min
completed: 2026-08-25
status: complete
---

# Phase 1 Plan 06: First Light Summary

**The XIAO ESP32-S3 Plus + EE02 board booted the Phase 1 firmware end to end for the first time, blitted a correct six-band palette image to the 13.3" Spectra 6 glass in ~31.5s, and entered deep sleep - with the multi-session "device appears then disappears" scare diagnosed as the device's own correct deep-sleep USB power-off, not a fault.**

## Performance

- **Duration:** 74 min (across Task 1 at 21:11 UTC through Task 3 at 22:25 UTC; spanned multiple sessions per the plan's own resume history - see Issues Encountered)
- **Started:** 2026-08-25T19:11:48Z
- **Completed:** 2026-08-25T20:25:22Z
- **Tasks:** 3
- **Files modified:** 5 (firmware/flash.sh, firmware/monitor.sh, hardware/logs/first-light.log, hardware/BRINGUP-LOG.md, hardware/BOM.md)

## Accomplishments

- First-ever real-hardware verification of the EE02 board profile: all eight panel pin values and the USB Serial/JTAG console routing are confirmed correct with zero corrections needed, closing a concern STATE.md had tracked since Phase 1 planning (the Spectra 6 dual-controller driver has no confirmed off-the-shelf ESP-IDF library, and this board profile's own authors never drove it against real hardware).
- A full wake -> Wi-Fi join -> SNTP sync -> poll -> download -> verify -> blit -> deep-sleep cycle captured live in `hardware/logs/first-light.log`, matching all four frozen Log Line Contract shapes.
- Diagnosed and permanently resolved the "device appears then disappears" symptom that had blocked first-boot console capture across several prior sessions: it is `esp_deep_sleep_start()` correctly cutting USB Serial/JTAG power outside the RTC domain, not a boot loop, brownout, or firmware panic.
- Measured the panel's real full-refresh duration (~31.5s, consistent across two independent captures) - concrete input for Phase 2's rendering-cadence UX decisions.
- `firmware/flash.sh` and `firmware/monitor.sh` are now reusable, battle-tested tools for the remaining hardware bring-up plans (01-07, 01-08).

## Task Commits

Each task was committed atomically:

1. **Task 1: Unbox, assemble, and connect the device** - `8b25ba0` (docs)
2. **Task 2: Flash the image, verify it back, and capture the first boot** - `b71e30e` (feat: flash + byte-verify), `b9bc408` (feat: first-light capture + diagnosis)
3. **Task 3: Confirm the picture on the glass and close out the board profile** - `afa88aa` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/flash.sh` - Host-side flash of the container-built image over USB, with post-flash read-back byte verification against `build-ee02/inkframe.bin`
- `firmware/monitor.sh` - Serial console capture to a timestamped log under `hardware/logs/`
- `hardware/logs/first-light.log` - The captured console output of the first successful end-to-end wake -> poll -> blit -> sleep cycle
- `hardware/BRINGUP-LOG.md` - Assembly record, serial device path, flashing steps, the full first-boot-capture diagnosis, Board Profile Verification (now VERIFIED), and Panel Observations
- `hardware/BOM.md` - `Arrived on` dates filled in for the EE02 kit and battery orders

## Decisions Made

- esptool installed via Homebrew (not pip) - keeps Phase 1's zero-pip-install property intact; flashing runs natively on the host rather than in the containerised build, since Docker Desktop's macOS USB passthrough is unreliable.
- The EE02 board profile needed zero pin or configuration corrections after real-hardware verification - `firmware/sdkconfig.ee02.defaults` stays byte-identical to upstream.
- "Device appears then disappears on USB" is documented in `hardware/BRINGUP-LOG.md` as expected, by-design deep-sleep behavior rather than a defect, so no future session re-investigates it as a hardware fault.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `timeout` (GNU coreutils) not present on stock macOS**
- **Found during:** Task 2 (building the race-capture diagnostic script)
- **Issue:** A capture-window script relying on `timeout 5 cat <port>` failed with `timeout: command not found`, since macOS ships BSD userland without GNU coreutils' `timeout` by default.
- **Fix:** Replaced with a background `cat <port> &` process plus a poll-and-`kill` loop that stops the reader when the port disappears or a time cap elapses.
- **Files modified:** scratch diagnostic scripts only (not committed - see Issues Encountered)
- **Verification:** The revised script successfully captured live serial output on the next attempt.

**2. [Rule 3 - Blocking] `log` invoked bare resolves to a zsh builtin, not the macOS system log tool**
- **Found during:** Task 2 (cross-referencing kernel-level USB enumeration events)
- **Issue:** `log show --predicate ...` failed with `too many arguments`, because `log` bare is zsh's built-in logarithm/math command in this shell, silently shadowing `/usr/bin/log`.
- **Fix:** Invoked the full path `/usr/bin/log show ...` explicitly.
- **Files modified:** none (diagnostic command only)
- **Verification:** The corrected invocation returned real `IOUSBHostFamily` enumerate/terminate events with timestamps.

---

**Total deviations:** 2 auto-fixed (both Rule 3, tooling/environment issues discovered while building the diagnostic capture path - no firmware or hardware defect found)
**Impact on plan:** No scope creep. Both fixes were necessary to complete the plan's own Task 2 instruction to capture the first boot; the underlying board profile and firmware needed no changes at all.

## Issues Encountered

- **The "device appears then disappears" symptom, and why it took real diagnostic work to close out.** Across several prior sessions, the USB serial connection dropping shortly after every appearance looked exactly like a boot loop or brownout - especially plausible given the EE02 board profile had never been driven on real hardware before this plan, and the panel's power draw during a blit was a specific candidate risk the resume notes called out. Closing this out required three independent evidence sources used together rather than more guessing: (1) macOS's own kernel-level `IOUSBHostFamily` enumerate/terminate log, which showed the pattern was a legitimate `hardware connection lost` at a consistent cadence rather than random; (2) the stub server's own request log, which showed successful device enrollment and repeated authenticated polls with real telemetry well before any console bytes were captured, proving Wi-Fi and HTTP were healthy; and (3) a race-capture script (poll `ls /dev/cu.usbmodem*` at ~150ms intervals, attach a reader the instant the port appears) that finally caught real serial text. The captured text showed a clean `poll ok` / `sleep enter` pair with no panic or brownout signature - conclusively resolving the question. This is now documented in `hardware/BRINGUP-LOG.md` so no future session re-investigates it as a hardware fault.
- **Capturing the actual `blit ok` line required forcing a non-hash-skip cycle.** By the time console capture worked, NVS already held the persisted hash from an earlier successful (but uncaptured) blit, so the device was hash-skipping on every subsequent wake - a healthy but short cycle that never reaches the blit path this task's acceptance criteria needed literal log text for. Rather than erasing NVS on the device (a destructive flash operation correctly declined by the environment's safety controls without explicit approval), the served image was temporarily swapped to the repository's own second deterministic test pattern (`make_test_panel.py --pattern quadrants`, already built for exactly this "hash-change check" purpose per its own docstring), forcing a real download+blit that was captured live. The image was restored to the correct `palette` pattern immediately afterward and the device woken again so the panel shows the correct picture for Task 3's visual check.
- **This plan's total elapsed time (21:11 to 22:25 UTC) reflects the tail end of a longer, multi-session effort** - per the resume context, Task 1 and the initial flash/verify happened in earlier sessions, and this session picked up specifically to resolve the blocked first-boot capture.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The Walking Skeleton stands: assembled hardware, verified firmware, and a correct picture on real e-paper glass, produced end to end by the device polling its own local stub server.
- The EE02 board profile is fully verified against real hardware with zero corrections - Phase 1's single largest hardware unknown is retired.
- `firmware/flash.sh` and `firmware/monitor.sh` are ready for reuse in plans 01-07 (real ADS-B data end to end) and 01-08 (battery-powered unattended operation).
- Phase 2's rendering work now has a real ~31.5s full-refresh measurement to design cadence/UX expectations around.
- No blockers carried forward from this plan.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-25*

## Self-Check: PASSED

All created files and all four task commit hashes verified present on disk / in git log.
