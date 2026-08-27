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
affects: [Task 3 - the blocking hardware bring-up checkpoint that confirms the sense circuit exists on the real board and puts the icon on real glass, closing DEVICE-04]

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

key-decisions:
  - "battery_math_apply_divider() saturates to UINT32_MAX rather than wrapping on overflow (T-05-03-01) - a wrapped product would read as an implausibly small voltage and could spuriously arm the low-battery warning"
  - "s_cached_mv is a file-scope static sentinel (-1 = not yet read this wake) - deep sleep clears RAM, so this gives exactly one ADC read per wake with zero change to app_main.c"
  - "The calibration handle is deleted on every path after creation (both the error branch and the success branch), diverging from 05-RESEARCH.md's Pattern 1 example which intentionally leaked it - this plan's own action text and T-05-03-03 both require full release"
  - "A battery-telemetry failure degrades to the unknown (0) sentinel and never takes the device down - no ESP_ERROR_CHECK() on the enable-line gpio_config(), unlike epd13in3e.c's panel-pin setup which does abort"

requirements-completed: []  # DEVICE-04 is NOT complete yet - Task 3 (the blocking hardware checkpoint) closes it. Left empty deliberately.

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
        ref: "firmware/build.sh - could NOT be run in this sandbox (no Docker daemon); manual review confirms the code matches 05-RESEARCH.md Pattern 1 and this plan's action text exactly"
        status: unknown
    human_judgment: true
    rationale: "This module is ESP-IDF-dependent and has never been host-compiled or run - it can only be proven correct by the containerised ESP-IDF build (unavailable in this sandbox) and by real hardware bring-up. Task 3's blocking checkpoint is the actual verification gate; deferring to it rather than claiming false confidence here."
  - id: D3
    description: "A flashed device measures a real battery voltage, reports it in X-Battery-Mv, and the low-battery icon appears/disappears on real glass"
    requirement: "DEVICE-04"
    verification: []
    human_judgment: true
    rationale: "Task 3 is a blocking checkpoint:human-verify hardware task, not yet executed. Requires flashing the real board, reading the console, and confirming the icon on the physical 13.3\" panel - no automation can substitute for this."

# Metrics
duration: ~20min (Tasks 1-2 only; Task 3 not started)
completed: 2026-08-27
status: in-progress
---

# Phase 5 Plan 3: Real Battery-Voltage Measurement (DEVICE-04 device slice) Summary

**Host-tested divider-ratio conversion and a full ESP-IDF ADC driver module now enable the EE02 driver board's factory battery-sense circuit, replacing the compiled-in `X-Battery-Mv: 0` sentinel with a real one-cached-read-per-wake measurement — Tasks 1 and 2 complete, Task 3 (real hardware bring-up) is a blocking checkpoint not yet run.**

## Performance

- **Duration:** ~20 min (Tasks 1-2)
- **Started:** 2026-08-27T22:28:00+02:00 (approx.)
- **Completed (Tasks 1-2):** 2026-08-27T22:36:01+02:00
- **Tasks:** 2 of 3 (Task 3 is a blocking `checkpoint:human-verify` — real hardware, cannot run autonomously)
- **Files modified:** 10 (5 created, 5 modified)

## Accomplishments

- `battery_math_apply_divider()` (`firmware/main/battery_math.h`/`.c`) — a pure, saturating divider-ratio conversion mirroring `backoff.c`'s exact shape, pinned by nine host assertions tied directly to this codebase's existing 3400/3500/3600 mV thresholds (`hardware/logtools.py`'s cutoff, `05-CONTEXT.md`'s D-01 threshold, `05-UI-SPEC.md`'s clear point), full charge, the ADC ceiling, and `uint32_t` saturation with no wraparound. Executed as an explicit RED (genuinely failing compile, verified) → GREEN TDD cycle.
- `fp_battery_mv()` (`firmware/main/battery.h`/`.c`) — enables the EE02 board's factory sense divider (`CONFIG_FP_PIN_BATTERY_ADC_EN`, default GPIO6), settles 10ms, resolves the sense GPIO (`CONFIG_FP_PIN_BATTERY_ADC`, default GPIO1) to an ADC1 channel via `adc_oneshot_io_to_channel()`, reads a calibrated value via `adc_oneshot`/`adc_cali` curve-fitting, converts it, and caches the result for the rest of the wake. Every resource (ADC unit, calibration handle, enable line) is released on every path including every error return.
- `firmware/main/api_client.c`'s `telemetry_headers()` now sends `fp_battery_mv()`'s real reading in `X-Battery-Mv` instead of the compiled-in `"0"` literal; the head comment documenting the placeholder is rewritten to describe the real behavior.
- Two new `Kconfig.projbuild` options (`FP_PIN_BATTERY_ADC`, `FP_PIN_BATTERY_ADC_EN`) each document why the pin choice is non-obvious (EE02-vs-bare-module, divider purpose, ADC1-only). `sdkconfig.ee02.defaults` gets the two new pin values, explicitly marked **not yet confirmed on this board** pending Task 3.
- `hardware/BOM.md` is unchanged across both tasks — confirmed via `git diff --exit-code` — no hardware was added, matching the plan's explicit "no soldering, no external component" scope.

## Task Commits

1. **Task 1: Host-tested divider conversion** — `3b834be` (test, RED) → `fae05dc` (feat, GREEN)
2. **Task 2: Enable the board's sense circuit, read it, and put the value on the wire** — `499a0cb` (feat)

_Task 3 (the blocking hardware checkpoint) has not been executed. No commit exists for it yet._

## Files Created/Modified

- `firmware/main/battery_math.h` / `.c` — pure divider-ratio conversion, no I/O, no globals, no ESP-IDF headers
- `firmware/tests/test_battery_math.c` — nine host assertions
- `firmware/tests/run_host_tests.sh` — wired in the new suite (now runs four suites)
- `firmware/main/CMakeLists.txt` — added `battery_math.c` (Task 1), then `battery.c` + `esp_adc` (Task 2)
- `firmware/main/battery.h` / `.c` — the ESP-IDF ADC driver module
- `firmware/main/api_client.c` — `telemetry_headers()` sends the real reading; head comment rewritten
- `firmware/main/Kconfig.projbuild` — new "Battery sense" menu
- `firmware/sdkconfig.ee02.defaults` — the two new pin defaults, marked unconfirmed

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

---

**Total deviations:** 2 noted (1 environment limitation, 1 pre-existing verification-script quirk). Zero deviations required a code change beyond what the plan already specified.
**Impact on plan:** Neither affects the shipped code's correctness. Both are documented here so Task 3 (or a future session with Docker access) can independently confirm the containerised build, and so the acceptance-criteria script's quirk isn't mistaken for a regression in a future audit.

## Issues Encountered

None beyond the two auto-fixed/noted deviations above.

## User Setup Required

**The developer must run Task 3 themselves — it is a blocking `checkpoint:human-verify` hardware task that this executor cannot perform.** See the CHECKPOINT REACHED message accompanying this summary for the exact steps: flash `firmware/build.sh` + `firmware/flash.sh`, read the `fp_batt` console line via `firmware/monitor.sh`, confirm the reported millivolts are plausible, then force the low-battery state and confirm the icon appears/disappears on the real 13.3" Spectra 6 panel.

No soldering, no external component, and no hardware modification is required — only flashing firmware and reading numbers off the console/screen.

## Next Phase Readiness

- Tasks 1-2 give the device a genuinely real, host-tested-where-possible battery measurement path: the pure conversion is proven correct on the host, and the ESP-IDF ADC module compiles cleanly under strict `cc` for its host-testable half and follows every precedent this codebase already establishes for its ESP-IDF-dependent half.
- Task 3 is the sole remaining gate for DEVICE-04. It cannot be automated: it requires physically flashing the real EE02 board, reading its console output, and visually confirming the icon on the physical panel. `DEVICE-04` in `.planning/REQUIREMENTS.md` remains unchecked until Task 3 completes.
- No blockers beyond Task 3 itself. The server-side path (05-02) is already fully built, tested, and proven end-to-end against real protocol traffic — the only missing piece is a real, non-zero `X-Battery-Mv` value reaching it, which Task 2's code produces but Task 3 has not yet confirmed on real hardware.

---
*Phase: 05-low-battery-indicator*
*Completed: 2026-08-27 (Tasks 1-2 only — plan not yet closed)*

## Self-Check: PASSED

All created files confirmed present on disk (`battery_math.h`/`.c`, `test_battery_math.c`, `battery.h`/`.c`, this SUMMARY) and all four commit hashes (`3b834be`, `fae05dc`, `499a0cb`, `175b068`) confirmed present in `git log --oneline --all`.
