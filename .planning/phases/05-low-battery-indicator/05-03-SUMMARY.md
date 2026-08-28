---
phase: 05-low-battery-indicator
plan: 03
subsystem: firmware
tags: [esp-idf, adc, esp32-s3, ee02, battery-telemetry]

# Dependency graph
requires:
  - phase: 05-low-battery-indicator (05-02)
    provides: server-side battery-low path (draw_battery_icon(), parse_battery_mv()/save_battery_state(), apply_battery_hysteresis()) - fully built and tested but exercised only by the compiled-in X-Battery-Mv=0 sentinel until this plan
provides:
  - battery_math_apply_divider() - pure, saturating divider-ratio conversion, host-tested against nine cases tied to the 3400/3500/3600 mV thresholds already used elsewhere in this codebase
  - fp_battery_mv() - one cached adc_oneshot + adc_cali read per wake off the EE02 driver board's factory sense divider, 0 = unknown sentinel on any failure
  - telemetry_headers() now sends the real measured X-Battery-Mv instead of a compiled-in "0" literal
  - Real hardware confirmation (hardware/BRINGUP-LOG.md) that the EE02's factory 2:1 battery-sense divider exists and reads correctly - battery mv=4156 pin_mv=2078
  - Real on-glass confirmation of the low-battery icon appearing/disappearing on the physical 13.3" Spectra 6 panel, exercising plan 05-02's server-side path end to end
affects: [DEVICE-04 is now fully closed - device measurement and server render both proven on real hardware]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-math/ESP-IDF-dependent module split (battery_math.c vs battery.c) mirrors backoff.c vs wifi.c exactly - the pure half gets nine host-tested boundary assertions, the ESP-IDF half is verified by real hardware bring-up instead (checkpoint:human-verify)"
    - "adc_oneshot_io_to_channel() resolves the Kconfig GPIO to a unit/channel rather than hardcoding a channel number, so the Kconfig value stays the single source of truth"
    - "Every ADC/enable-line resource is released on every path including every error return (T-05-03-03) - a leaked ADC unit or a divider left conducting across the pack through deep sleep is a real drain on a device that wakes thousands of times"

key-files:
  created:
    - firmware/main/battery_math.h
    - firmware/main/battery_math.c
    - firmware/tests/test_battery_math.c
    - firmware/main/battery.h
    - firmware/main/battery.c
  modified:
    - firmware/tests/run_host_tests.sh
    - firmware/main/CMakeLists.txt
    - firmware/main/api_client.c
    - firmware/main/Kconfig.projbuild
    - firmware/sdkconfig.ee02.defaults
    - hardware/BRINGUP-LOG.md
    - firmware/VENDOR.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "battery_math_apply_divider() saturates to UINT32_MAX rather than wrapping on overflow (T-05-03-01) - a wrapped product would read as an implausibly small voltage and could spuriously arm the low-battery warning"
  - "s_cached_mv is a file-scope static sentinel (-1 = not yet read this wake) - deep sleep clears RAM, so this gives exactly one ADC read per wake with zero change to app_main.c"
  - "The calibration handle is deleted on every path after creation (both the error branch and the success branch), diverging from 05-RESEARCH.md's Pattern 1 example which intentionally leaked it - this plan's own action text and T-05-03-03 both require full release"
  - "A battery-telemetry failure degrades to the unknown (0) sentinel and never takes the device down - no ESP_ERROR_CHECK() on the enable-line gpio_config(), unlike epd13in3e.c's panel-pin setup which does abort"
  - "Task 3's flash-and-observe on the real EE02 board needed zero code correction - polarity, settle delay, and the 2:1 divider ratio all matched the cookbook on the first attempt (pin_mv=2078, exactly half of battery mv=4156)"

requirements-completed: [DEVICE-04]

coverage:
  - id: D1
    description: "battery_math_apply_divider() converts a calibrated ADC sense-pin reading to real pack millivolts, saturating instead of wrapping on overflow"
    requirement: "DEVICE-04"
    verification:
      - kind: unit
        ref: "firmware/tests/test_battery_math.c - nine assertions (zero edge, 3400/3500/3600mV thresholds, full charge, ADC ceiling, uint32_t saturation boundary)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fp_battery_mv() enables the EE02's sense divider, performs one calibrated ADC1 read per wake, releases the ADC unit/calibration handle/enable line on every path, and telemetry_headers() sends the result instead of a compiled-in literal"
    requirement: "DEVICE-04"
    verification:
      - kind: other
        ref: "firmware/build.sh - re-run in this session with a Docker daemon available: exits 0, build-ee02/skypane.bin produced. Confirmed on real hardware by Task 3's flash-and-observe (hardware/BRINGUP-LOG.md's 'ADC Battery-Sense Bring-Up' section): battery mv=4156 pin_mv=2078, exactly the expected 2:1 ratio, no code correction needed."
        status: pass
    human_judgment: true
    rationale: "This module is ESP-IDF-dependent and can only be fully proven correct by the containerised ESP-IDF build plus real hardware bring-up. Both are now done: firmware/build.sh is green in this session, and the developer's own flash-and-observe confirmed the real reading."
  - id: D3
    description: "A flashed device measures a real battery voltage, reports it in X-Battery-Mv, and the low-battery icon appears/disappears on real glass"
    requirement: "DEVICE-04"
    verification:
      - kind: manual
        ref: "Developer-reported Task 3 checkpoint: console reported battery mv=4156 pin_mv=2078 (stable and repeatable over ~40 minutes of real polls, 4150-4200mV range in production battery_state.json/journalctl); icon confirmed appearing bottom-left and disappearing on the physical 13.3\" Spectra 6 panel across two forced-injection passes (original and 30%-shrunk geometry), with every other poster element unmoved"
        status: pass
    human_judgment: true
    rationale: "Task 3 was a blocking checkpoint:human-verify hardware task. The developer flashed the real board, read the console, and visually confirmed the icon on the physical panel - no automation can substitute for this, and none was used."

# Metrics
duration: ~20min (Tasks 1-2, prior session) + hardware bring-up session (developer-run, orchestrator-assisted) + ~15min (this session: documentation, verification, commit)
completed: 2026-08-28
status: complete
---

# Phase 5 Plan 3: Real Battery-Voltage Measurement (DEVICE-04) Summary

**Host-tested divider-ratio conversion and a full ESP-IDF ADC driver module enable the EE02 driver board's factory battery-sense circuit, replacing the compiled-in `X-Battery-Mv: 0` sentinel with a real one-cached-read-per-wake measurement — confirmed on real hardware (`battery mv=4156 pin_mv=2078`, exactly the expected 2:1 ratio) and the low-battery icon confirmed appearing/disappearing on the physical 13.3" Spectra 6 panel. DEVICE-04 is complete.**

## Performance

- **Duration:** ~20 min (Tasks 1-2, prior session) + a live hardware bring-up session (developer flashing/monitoring the real board, orchestrator-assisted) + ~15 min (this session: transcribing results, running full verification, committing, closing the plan)
- **Started:** 2026-08-27T22:28:00+02:00 (approx., Tasks 1-2)
- **Completed:** 2026-08-28 (Task 3 — hardware bring-up and documentation)
- **Tasks:** 3 of 3, all complete
- **Files modified:** 13 (5 created, 8 modified)

## Accomplishments

- `battery_math_apply_divider()` (`firmware/main/battery_math.h`/`.c`) — a pure, saturating divider-ratio conversion mirroring `backoff.c`'s exact shape, pinned by nine host assertions tied directly to this codebase's existing 3400/3500/3600 mV thresholds (`hardware/logtools.py`'s cutoff, `05-CONTEXT.md`'s D-01 threshold, `05-UI-SPEC.md`'s clear point), full charge, the ADC ceiling, and `uint32_t` saturation with no wraparound. Executed as an explicit RED (genuinely failing compile, verified) → GREEN TDD cycle.
- `fp_battery_mv()` (`firmware/main/battery.h`/`.c`) — enables the EE02 board's factory sense divider (`CONFIG_FP_PIN_BATTERY_ADC_EN`, default GPIO6), settles 10ms, resolves the sense GPIO (`CONFIG_FP_PIN_BATTERY_ADC`, default GPIO1) to an ADC1 channel via `adc_oneshot_io_to_channel()`, reads a calibrated value via `adc_oneshot`/`adc_cali` curve-fitting, converts it, and caches the result for the rest of the wake. Every resource (ADC unit, calibration handle, enable line) is released on every path including every error return.
- `firmware/main/api_client.c`'s `telemetry_headers()` now sends `fp_battery_mv()`'s real reading in `X-Battery-Mv` instead of the compiled-in `"0"` literal; the head comment documenting the placeholder is rewritten to describe the real behavior.
- Two new `Kconfig.projbuild` options (`FP_PIN_BATTERY_ADC`, `FP_PIN_BATTERY_ADC_EN`) each document why the pin choice is non-obvious (EE02-vs-bare-module, divider purpose, ADC1-only). `sdkconfig.ee02.defaults` gets the two new pin values — now **confirmed on this board** by Task 3.
- `hardware/BOM.md` is unchanged across all three tasks — confirmed via `git diff --exit-code` — no hardware was added, matching the plan's explicit "no soldering, no external component" scope.
- **Real hardware bring-up (Task 3):** flashed the real board (`firmware/build.sh` + `firmware/flash.sh`, byte-verified), read the console (`firmware/monitor.sh`): `fp_batt: battery mv=4156 pin_mv=2078` — exactly a 2:1 ratio, confirming the EE02's factory sense divider on the first attempt with no code correction needed. The wake/poll/sleep cycle and panel render were unaffected by the two newly driven GPIOs. Real telemetry proved stable over ~40 minutes of live production polls (4150-4200mV range).
- **Icon on real glass:** confirmed via two forced-injection passes against the live production server (`battery_mv=3400`, real device fetching the resulting render on its own next poll) — original icon geometry (developer feedback: too large) and the already-shrunk `260828-0qo` geometry (developer: "c'est parfait"). Appear-then-disappear transition directly observed on the physical panel both times.
- `hardware/BRINGUP-LOG.md` gets a new "ADC Battery-Sense Bring-Up (Phase 5, DEVICE-04)" section transcribing both steps. `firmware/VENDOR.md`'s `api_client.c` row, vendored-file table, and Log Line Contract section are updated to describe the real behavior instead of the placeholder. `.planning/REQUIREMENTS.md` marks DEVICE-04 complete.

## Task Commits

1. **Task 1: Host-tested divider conversion** — `3b834be` (test, RED) → `fae05dc` (feat, GREEN)
2. **Task 2: Enable the board's sense circuit, read it, and put the value on the wire** — `499a0cb` (feat)
3. **Task 3: Hardware bring-up — confirm the sense circuit, then the icon on real glass** — `4035449` (docs)

## Files Created/Modified

- `firmware/main/battery_math.h` / `.c` — pure divider-ratio conversion, no I/O, no globals, no ESP-IDF headers
- `firmware/tests/test_battery_math.c` — nine host assertions
- `firmware/tests/run_host_tests.sh` — wired in the new suite (now runs four suites)
- `firmware/main/CMakeLists.txt` — added `battery_math.c` (Task 1), then `battery.c` + `esp_adc` (Task 2)
- `firmware/main/battery.h` / `.c` — the ESP-IDF ADC driver module
- `firmware/main/api_client.c` — `telemetry_headers()` sends the real reading; head comment rewritten
- `firmware/main/Kconfig.projbuild` — new "Battery sense" menu
- `firmware/sdkconfig.ee02.defaults` — the two new pin defaults, now confirmed on real hardware
- `hardware/BRINGUP-LOG.md` — new "ADC Battery-Sense Bring-Up" section (Task 3)
- `firmware/VENDOR.md` — `api_client.c` row, vendored-file table, Log Line Contract section updated (Task 3)
- `.planning/REQUIREMENTS.md` — DEVICE-04 marked complete (Task 3)

## Decisions Made

See `key-decisions` in the frontmatter above. All decisions were already resolved by the plan itself (saturation over wraparound, one-read-per-wake caching via a file-scope static, full calibration-handle release on every path, no-abort-on-battery-failure) — none required a new decision during execution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `firmware/build.sh` (containerised ESP-IDF build) could not run — no Docker daemon in this sandbox**
- **Found during:** Task 1's acceptance criteria (`firmware/build.sh` exits 0) and Task 2's verification (`firmware/build.sh && sh firmware/tests/run_host_tests.sh`)
- **Issue:** This execution environment has the `docker` CLI installed but no running Docker daemon (`docker info` fails), so the pinned `espressif/idf:v5.3.1` containerised build this project standardizes on cannot execute here.
- **Fix:** Not fixable in this sandbox — this is an environment limitation, not a code defect. All host-testable evidence was gathered instead: `sh firmware/tests/run_host_tests.sh` passes (four suites), a strict `cc -Wall -Wextra -Werror -std=c11` compile of the pure-math module passes with zero warnings, and every new/changed line was manually reviewed against this codebase's own precedents (`backoff.c`/`.h` shape for the pure module; `wifi.c`'s resource-teardown discipline and `epd13in3e.c`'s GPIO-config idiom for the ESP-IDF module; `05-RESEARCH.md`'s Pattern 1 body for the ADC read itself, with the calibration-handle-release divergence noted below).
- **Files modified:** None (informational — no code change resulted)
- **Verification:** `sh firmware/tests/run_host_tests.sh` (4/4 suites pass); `cc -Wall -Wextra -Werror -std=c11` on the pure module (0 warnings)
- **Committed in:** Documented here; not a commit-worthy change. Task 3's real hardware bring-up requires flashing the device anyway, so confirming a real ESP-IDF 5.3.1 build succeeds on the developer's own machine (which does have Docker) is folded into that step rather than blocking Tasks 1-2 here.

**2. [Rule 1 - Bug, in the plan's own verification script, not in shipped code] The `X-Battery-Mv` non-comment grep filter in Task 2's acceptance criteria excludes ALL indented lines, not just comments**
- **Found during:** Task 2's acceptance criteria (`grep -vE '^\s*[ /*]' firmware/main/api_client.c | grep -c 'X-Battery-Mv'` expected to return 1)
- **Issue:** The regex `^\s*[ /*]` backtracks so that `\s*` can consume all-but-one leading whitespace character, leaving that last whitespace character to satisfy the `[ /*]` class — meaning it excludes every line with 2+ leading spaces, not just comment lines. Verified this is pre-existing and unrelated to this plan's change: the same filter applied to the untouched `X-Rssi` header line (present since Phase 1) also returns 0.
- **Fix:** None applied — this is a verification-script quirk, not a functional defect, and "fixing" it by de-indenting real C code inside a function body would break the codebase's own style for no benefit. Confirmed the actual intent (the literal header string appears exactly once in real executable code, not just in a comment) is satisfied: `grep -c 'X-Battery-Mv' firmware/main/api_client.c` returns 2 (one in the head-comment prose, one in the real `esp_http_client_set_header()` call).
- **Files modified:** None
- **Verification:** Manual grep comparison against the pre-existing `X-Rssi` line, shown above
- **Committed in:** N/A — no code change

**3. [Task 3 — no fix needed] Hardware bring-up required zero code correction**
- **Found during:** Task 3's Step 1 (flash and read the number)
- **Observation:** `battery mv=4156 pin_mv=2078` on the first flash attempt — exactly the expected 2:1 divider ratio, no polarity inversion, no settle-delay issue, no ratio mismatch. This is the "clean" branch of the plan's own decision tree in `<how-to-verify>` (not one of the two problem branches), so no change to `battery.c`, `battery_math.c`, or `test_battery_math.c` was needed or made.
- **Files modified:** None beyond the documentation files listed above.
- **Verification:** `sh firmware/tests/run_host_tests.sh` and `firmware/build.sh` both still green after the fact, confirming nothing in the ADC path needed touching.
- **Committed in:** N/A — no code change.

**4. [Rule 2 — documented honestly rather than fabricated] The plan's last acceptance criterion (`hardware/logtools.py check-battery` against a captured log) has no local file to run against**
- **Found during:** Task 3's final acceptance criterion, which itself is conditional: "run it only if a capture exists; record the outcome either way in the SUMMARY."
- **Issue:** Real, non-zero `X-Battery-Mv` telemetry (4156, 4192, 4196 mV) has genuinely flowed end-to-end in production over ~40 minutes of live device polls — this satisfies the criterion's actual intent, that plan 05-01's parked Tasks 2-3 now have a usable, confirmed-working data source. But that telemetry lives in the production VPS's `journalctl` (`skypane-byos.service`), not in a local file this repo checkout can run `hardware/logtools.py check-battery` against. No existing file under `hardware/logs/` or `hardware/fixtures/` captures tonight's session (confirmed: only the pre-existing `battery-good.log`/`battery-gap.log`/`battery-flat-mv.log`/`battery-journal.log` fixtures and `first-light.log`/`backoff-*.log` bring-up logs are present, none newly dated).
- **Fix:** None fabricated. Recording this plainly rather than inventing a local capture: the criterion's underlying question (does real telemetry now reach the server?) is answered YES, by direct production evidence, but the specific local-file-based command was not run because no local capture exists to run it against.
- **Files modified:** None.
- **Verification:** N/A — this is an honest gap note, not a fix.
- **Committed in:** N/A.

---

**Total deviations:** 4 noted (1 environment limitation from the prior session, 1 pre-existing verification-script quirk from the prior session, 1 "no correction needed" observation from Task 3, 1 honest gap on the local-capture acceptance criterion). Zero deviations required a code change beyond what the plan already specified.
**Impact on plan:** None affect the shipped code's correctness or DEVICE-04's completion. The local-capture gap is a documentation nuance, not a functional shortfall — the real question the criterion exists to answer is affirmatively closed by direct production evidence.

## Issues Encountered

None beyond the four documented deviations above. No blockers.

## User Setup Required

None remaining. Task 3's hardware bring-up is complete: the developer flashed the real board, read the console, and visually confirmed the icon on the physical 13.3" Spectra 6 panel across two passes. No soldering, no external component, and no hardware modification was involved.

## Next Phase Readiness

- All three tasks complete. The device now sends a genuinely real, host-tested-where-possible, and hardware-confirmed battery measurement: the pure conversion is proven correct on the host, the ESP-IDF ADC module builds clean under the pinned toolchain, and the real board's own console confirms the EE02's factory sense divider works exactly as documented.
- `DEVICE-04` is marked complete in `.planning/REQUIREMENTS.md`. `DEVICE-05` (the multi-day discharge run, plan 05-01's parked Tasks 2-3) is untouched by this plan and remains the only open item in Phase 5.
- The server-side path (05-02) and the device-side path (05-03) are now both proven end-to-end against real hardware and real production traffic — the battery glyph has been seen appearing and disappearing on the physical frame.
- No blockers.

---
*Phase: 05-low-battery-indicator*
*Completed: 2026-08-28 (all 3 tasks)*

## Self-Check: PASSED

All created files confirmed present on disk (`battery_math.h`/`.c`, `test_battery_math.c`, `battery.h`/`.c`, this SUMMARY). All five commit hashes confirmed present in `git log --oneline --all`: `3b834be` (Task 1 RED), `fae05dc` (Task 1 GREEN), `499a0cb` (Task 2), `175b068` / `f6b81de` (prior-session summary commits), `4035449` (Task 3 — hardware bring-up documentation, DEVICE-04 marked complete). `hardware/BRINGUP-LOG.md` contains the "ADC Battery-Sense Bring-Up" section with the `fp_batt` numbers transcribed verbatim; `firmware/VENDOR.md` and `.planning/REQUIREMENTS.md` updated as specified. `sh firmware/tests/run_host_tests.sh` (4/4 suites), `firmware/build.sh` (green, Docker available this session), and `scripts/run-all-tests.sh` (all harnesses green) all confirmed passing in this session.
