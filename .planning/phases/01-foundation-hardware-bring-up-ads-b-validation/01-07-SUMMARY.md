---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 07
subsystem: hardware-bringup
tags: [esp32-s3, backoff, deep-sleep, nvs, esp-idf, stdlib-python, log-verification]

# Dependency graph
requires:
  - phase: 01-06
    provides: A flashed, real-hardware-verified device (EE02 board profile confirmed, Log Line Contract captured live) and the firmware.monitor.sh/flash.sh tooling this plan reuses
provides:
  - hardware/logtools.py - stdlib-only stamp/check-backoff/selftest for machine-verifying a captured serial log against the DEVICE-03 exponential backoff curve
  - hardware/fixtures/{backoff-good,backoff-fixed-interval,backoff-rtc-reset}.log - proven-against negative/positive fixtures
  - hardware/logs/backoff-run.log and hardware/logs/backoff-baseline-server.log - a real ~80-minute captured doubling curve (300/600/1200/2400/4800s across backoff_n=0..4), machine-verified
  - A reconnect-tolerant serial-capture pattern (poll for /dev/cu.usbmodem*, reattach on every drop, tolerate a marginal connection across a multi-hour span) for reuse in 01-08's much longer unattended run
affects: [01-07 Task 3 (this plan, not yet started), 01-08 (battery/unattended run - reuses the reconnect-tolerant capture pattern and hardware/logtools.py's stamp filter)]

tech-stack:
  added: []
  patterns:
    - "Reconnect-tolerant serial capture: poll /dev/cu.usbmodem* every 0.15s, attach cat the instant it appears, let it run with no per-round time cap until the port itself disappears (device sleep or a marginal-cable drop), then go straight back to polling - proven to survive dozens of drops across an ~80-minute unattended run without operator intervention."
    - "check-backoff never short-circuits on the first failing check - all checks run and print, so a FAIL line always names every violated property, not just the first one hit."
    - "Detached background pipelines via nohup + disown, verified by checking the process's PPID is 1 (reparented to launchd) rather than trusting `&` alone - confirmed to survive across separate tool-call turns."

key-files:
  created:
    - hardware/logtools.py
    - hardware/fixtures/backoff-good.log
    - hardware/fixtures/backoff-fixed-interval.log
    - hardware/fixtures/backoff-rtc-reset.log
    - hardware/logs/backoff-run.log
    - hardware/logs/backoff-baseline-server.log
  modified: []

key-decisions:
  - "Accepted the baseline healthy-wake capture even though its 'wake reason=' line wasn't captured (reattach loop attached a moment after the first boot lines) - the substantive proof (poll ok -> sleep enter, matching X-Boot-Reason=power-on in the server log at the same timestamp) is present, and none of check-backoff's checks for Task 2 depend on that specific line."
  - "Did not redact the WiFi SSID that leaked into backoff-run.log via ESP-IDF's own wifi component debug logging - the plan's own must_haves require the raw log to be re-checkable by a later reader, so editing it would break that evidentiary chain. Documented as a known, low-severity finding instead (see Deviations)."
  - "Left the stub server stopped overnight (not restarted) - Task 3's own sequencing requires it to stay down through its step 6, and only comes back up mid-Task-3 to prove recovery."
  - "Stopped the capture loop and its caffeinate wrapper before pausing overnight so the Mac is free to idle-sleep normally - Task 3 will start a fresh capture pipeline when resumed."

patterns-established:
  - "A checker proven to reject two distinct wrong-answer shapes (fixed-interval retry, RTC-memory reset) on synthetic fixtures before it is ever pointed at real hardware output - the fixtures are committed alongside the checker, not thrown away after use."

requirements-completed: []  # DEVICE-03 only fully covered once Task 3's power-cycle proof lands; not marked complete yet.

coverage:
  - id: D1
    description: "hardware/logtools.py check-backoff, proven on fixtures, correctly accepts a real backoff curve and rejects a fixed-interval retry and an RTC-reset counter before being pointed at hardware"
    verification:
      - kind: other
        ref: "python3 hardware/logtools.py selftest - exits 0, PASS on all 3 fixtures (backoff-good.log accepted; backoff-fixed-interval.log and backoff-rtc-reset.log rejected)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real hardware, with the stub server stopped, produces five consecutive failed wakes at doubling sleep intervals (300/600/1200/2400/4800s), not a fixed retry interval"
    requirement: DEVICE-03
    verification:
      - kind: other
        ref: "python3 hardware/logtools.py check-backoff hardware/logs/backoff-run.log --min-steps 5 - 6/6 checks pass; capture spans 4794s (>=4200s required)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The failure counter survives a total loss of power (NVS, not RTC memory) and a single success resets it to base"
    requirement: DEVICE-03
    verification: []
    human_judgment: true
    rationale: "Not yet observed - this is Task 3, deliberately deferred to the next session at the user's explicit request (needs physical USB unplug/replug)."

duration: 1h40min (Task 1+2 only; plan not yet complete)
completed: null
status: in-progress
---

# Phase 1 Plan 07: DEVICE-03 Backoff Hardware Observation (Partial — Task 3 Pending) Summary

**Real hardware, with the stub server stopped, walked the exact 300/600/1200/2400/4800-second doubling curve across five consecutive failed wakes over an ~80-minute unattended capture, machine-verified by a checker proven on synthetic fixtures first — the power-cycle persistence proof (Task 3) is deliberately paused overnight at the user's request.**

**This SUMMARY documents partial plan progress (Tasks 1 and 2 of 3). Task 3 has not started. A fuller/final SUMMARY should be written once Task 3 completes.**

## Performance

- **Duration so far:** ~1h40min (Task 1 authoring + fixture proof, Task 2's baseline + 90-minute observation window + verification)
- **Started:** 2026-08-25T22:39:00Z (approx, continuing from 01-06)
- **Paused:** 2026-08-26T00:35:00Z (Task 2 complete; Task 3 deferred)
- **Tasks:** 2 of 3 complete
- **Files modified:** 6 (hardware/logtools.py + 3 fixtures + 2 captured logs)

## Accomplishments

- `hardware/logtools.py` (stdlib-only: argparse, datetime, os, re, subprocess, sys) implements `stamp` (per-line ISO-8601 timestamping with per-line flush, safe for multi-hour piped captures), `check-backoff` (8 checks: min-steps, curve match against `firmware/main/backoff.c`'s table, gapless counter sequence, >=4 distinct intervals, sleep-entry match, wall-clock gap tolerance, power-on persistence, success reset — never short-circuits, so every FAIL line that applies gets printed), and `selftest` (shells out to itself against all 3 fixtures, asserts accept/reject/reject).
- Three fixtures (`backoff-good.log`, `backoff-fixed-interval.log`, `backoff-rtc-reset.log`) built by hand to exercise the checker against both the correct behavior and the two specific wrong-answer shapes DEVICE-03 exists to rule out, proven before any hardware output was ever fed to the checker.
- A real ~80-minute unattended hardware capture (`hardware/logs/backoff-run.log`, spanning 4794s) shows five consecutive failed wakes with backoff_n=0..4 and sleep_s=300/600/1200/2400/4800 - `check-backoff --min-steps 5` reports 6/6 checks passing.
- Built and proved a reconnect-tolerant serial-capture pattern (poll for the port every 0.15s, reattach on every drop, no per-round time cap) that survived a connection reported as "quite marginal all session" across the full 80-minute window without any manual intervention once launched.
- Confirmed both background pipelines (stub server, capture loop) were genuinely detached (PPID reparented to `launchd`/PID 1) and survived independently across multiple separate tool-call turns and a multi-minute gap while waiting for the device to reconnect.

## Task Commits

1. **Task 1: A log checker that can tell a backoff curve from a fixed-interval retry, proven on fixtures before any hardware run** - `2e8a041` (feat)
2. **Task 2: Stop the server and watch the interval double for ninety minutes** - `584364e` (feat)

**Task 3: Pull the power, prove the counter survived, then prove one success resets it** - NOT STARTED (deferred to next session).

**Plan metadata:** this commit (partial - Task 3 pending, plan not yet complete)

## Files Created/Modified

- `hardware/logtools.py` - stdlib-only serial-log timestamper and backoff-sequence checker (3 subcommands: stamp, check-backoff, selftest)
- `hardware/fixtures/backoff-good.log` - synthetic full healthy run including a power cycle and a reset, must be accepted under both `--expect-persist`/`--expect-reset`
- `hardware/fixtures/backoff-fixed-interval.log` - synthetic fixed-300s-every-time retry, must be rejected
- `hardware/fixtures/backoff-rtc-reset.log` - synthetic counter that clears after a power-on wake, must be rejected under `--expect-persist`
- `hardware/logs/backoff-run.log` - real stamped console capture of the 90-minute doubling run (~80 min actual span)
- `hardware/logs/backoff-baseline-server.log` - real stamped stub-server stdout for the baseline healthy wake

## Decisions Made

See `key-decisions` in frontmatter above (baseline acceptance without a captured wake line; no redaction of the leaked SSID; server left stopped overnight; capture loop stopped overnight).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical, accepted as low-severity / not auto-fixed] WiFi SSID leaks into `hardware/logs/backoff-run.log` via ESP-IDF's own wifi component debug logging**
- **Found during:** Task 2 (secret-scan step before committing captured logs)
- **Issue:** The line `wifi:connected with <SSID>, aid=..., channel=..., bssid=...` — emitted by ESP-IDF's `wifi_init` component at its own default log level, tag `wifi` — prints the network name configured in `firmware/main/secrets.h`'s `INK_WIFI_SSID`. This is not part of the project's five-line Log Line Contract and is not emitted by any of this project's own source files (`app_main.c`, `state_machine.c`, etc.). The plan's acceptance criteria for Task 2 reads literally as "no value from `secrets.h`" with no carve-out for the SSID specifically, even though the plan's own contract text ("no credential values — not the bearer token, not the Wi-Fi password, not the setup secret") only names those three as the actual concern.
- **What was checked:** confirmed the bearer token, WiFi password, `INK_API_BASE`, and setup secret are all absent from both committed logs — only the SSID (the lowest-sensitivity of the four values) is present, and only via this one vendored ESP-IDF driver line.
- **Why not fixed or redacted:** (1) Silencing this line requires a firmware change (lowering the `wifi` component's log verbosity, e.g. `esp_log_level_set("wifi", ESP_LOG_WARN)` or a Kconfig change) that would need its own reflash and a fresh multi-hour recapture to re-verify — out of scope for tonight given the user's explicit request to stop after Task 2. (2) Redacting the committed log after the fact would violate this plan's own must-have ("the raw console logs are committed alongside the verdict, so a later reader can re-run the check rather than trust the write-up") — an edited log is no longer the raw evidence. (3) The same leak already exists, unremarked, in plan 01-06's already-committed `hardware/logs/first-light.log`, so this isn't a new problem introduced by this plan.
- **Files affected:** `hardware/logs/backoff-run.log` (read-only finding, not modified)
- **Follow-up:** flag for a future firmware-hygiene pass (lower `wifi` component log verbosity) or a threat-register update explicitly accepting SSID exposure in local dev captures as low-severity (home network name only, no credential value); does not block Task 3 or 01-08.

---

**Total deviations:** 1 (documented finding, not auto-fixed — see reasoning above)
**Impact on plan:** No scope creep, no change to Task 2's deliverables. The finding is disclosed rather than hidden.

## Issues Encountered

- **Device not connected at Task 2 start.** The board wasn't plugged in when this session began; confirmed via `ls /dev/cu.*` and `system_profiler SPUSBDataType`. Resolved once the user physically reconnected it (after several rounds of cable/port reseating — the connection was "quite marginal all session").
- **Marginal USB connection throughout Task 2.** The device's serial port dropped and reappeared repeatedly, consistent with both its own deep-sleep USB power-off (expected, documented in 01-06's BRINGUP-LOG.md) and a genuinely marginal physical connection needing reseats. The reconnect-tolerant capture loop (poll every 0.15s, reattach on every appearance, no per-round cap) tolerated this without any lost capture time across the ~80-minute window.
- **Accidental `state record-session` no-args invocation reverted a manual STATE.md progress-counter fix the user had made moments earlier (commit `12d0a80`).** Caught immediately via `git diff`, reverted with `git checkout -- .planning/STATE.md`, and the session-continuity update was instead done via direct, deliberate edits rather than the auto-recompute tool call. No lasting effect — flagging here since it's the same drift-calculation issue the user's own commit message referenced (also seen in 02-05).

## User Setup Required

None beyond the physical hardware actions already described (device connected via USB, battery deliberately not connected — unchanged from plan 01-06's setup).

## Next Phase Readiness

**This plan is NOT complete.** Task 3 (power-cycle persistence proof) remains and requires the user's physical presence to unplug/replug USB. See `.planning/STATE.md`'s `## Session Continuity` section for the exact resume steps and the current hardware/process state left overnight:

- Device: connected via USB, battery still disconnected, holding `backoff_n=5` in NVS.
- Stub server: stopped (correct per Task 3's own sequencing — it stays down through Task 3 step 6).
- Capture loop + `caffeinate`: stopped, so the Mac can sleep normally overnight.

Once Task 3 completes (power-cycle proof, `hardware/BACKOFF-OBSERVATION.md`), this SUMMARY should be superseded by a full plan-completion SUMMARY, and the normal completion state updates (state.advance-plan, roadmap.update-plan-progress, requirements.mark-complete for DEVICE-03) should run at that point — none of those have run yet.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Status: IN PROGRESS — Task 3 of 3 pending*
