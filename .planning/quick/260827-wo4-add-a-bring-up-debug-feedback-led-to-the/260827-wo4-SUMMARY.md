---
phase: 05-low-battery-indicator
plan: 260827-wo4
subsystem: firmware
tags: [esp-idf, gpio, cjson, poll-protocol, bring-up]

# Dependency graph
requires:
  - phase: 01-walking-skeleton
    provides: app_main.c wake dispatcher, api_client.c display-response parse, state_machine.c poll cycle
provides:
  - fp_led module (fp_led_on/fp_led_off) driving the XIAO ESP32-S3's built-in GPIO21 User LED
  - Two unconditional wake-cycle call sites (boot-time on, pre-sleep off) making every flash/power-cycle visibly observable
  - led_enabled wire field end-to-end (stub server -> firmware parse -> conditional off-early consumer), the firmware-side half of a future remote toggle
affects: [05-low-battery-indicator's Task 3 hardware bring-up session, any future companion-web-interface work (CFG-01..CFG-04)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy per-wake GPIO module (led_configure()) mirroring battery.c's never-take-the-device-down error discipline (warn+return, no fatal abort macro)"
    - "Server-optional protocol field parsed permissively (absent/null/wrong-typed all resolve to a safe default) so a stale or buggy server degrades gracefully instead of triggering exponential backoff"

key-files:
  created:
    - firmware/main/led.h
    - firmware/main/led.c
  modified:
    - firmware/main/app_main.c
    - firmware/main/CMakeLists.txt
    - firmware/main/Kconfig.projbuild
    - firmware/sdkconfig.ee02.defaults
    - firmware/main/api_client.h
    - firmware/main/api_client.c
    - firmware/main/state_machine.c
    - firmware/VENDOR.md
    - stub-server/byos_server.py
    - stub-server/test_poll_cycle.py
    - hardware/BRINGUP-LOG.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "GPIO21 (built-in XIAO ESP32-S3 User LED, active-low) pinned in the EE02 board profile under a NOT-YET-CONFIRMED banner, same confidence posture as the battery-sense pins, resolved by flash-and-observe rather than further research"
  - "led_enabled shipped on the wire now (hardcoded True in the stub server), even though real per-device configuration is deferred to the companion web interface - because the firmware's reading half can only be changed by a physical reflash, while the server's setting half can be redeployed any afternoon"
  - "led_enabled parsed permissively (never rejects the display response) - trading the device's actual function for a debug LED's preference would be the wrong failure direction"

patterns-established:
  - "A future server-optional boolean field: fetch above the rejection block, never add a clause for it to that block, resolve with `!cJSON_IsBool(x) || cJSON_IsTrue(x)` after the block"

requirements-completed: []
# DEVICE-05 (battery life) is NOT marked complete by this plan - this plan
# adds an unrelated bring-up/debug LED under the DEVICE-05 phase umbrella
# but the requirement's own completion still depends on 05-01's multi-day
# discharge run and 05-03's real-hardware ADC bring-up, neither touched here.

coverage:
  - id: D1
    description: "fp_led module (fp_led_on/fp_led_off) added, lazily configures GPIO21, polarity-driven by CONFIG_FP_LED_ACTIVE_LOW, never aborts the device on GPIO failure"
    verification:
      - kind: unit
        ref: "sh firmware/tests/run_host_tests.sh (regression gate - led.c is ESP-IDF-only, not host-testable)"
        status: pass
      - kind: other
        ref: "structural greps: led.h exports exactly fp_led_on/fp_led_off; led.c contains zero ESP_ERROR_CHECK, >=1 ESP_LOGW, >=1 CONFIG_FP_LED_ACTIVE_LOW reference; no CONFIG_FP_PIN_* duplicate in sdkconfig.ee02.defaults"
        status: pass
    human_judgment: true
    rationale: "GPIO21's identity as the real User LED is an unconfirmed web-sourced claim; only a real flash-and-observe session (bundled into 05-03's checkpoint) confirms it lights, extinguishes correctly, and doesn't collide with the panel. firmware/build.sh (the containerised ESP-IDF compile) also could not run - no Docker daemon in this sandbox - so the ESP-IDF-dependent half is unverified by any build in this session."
  - id: D2
    description: "fp_led_on() unconditional as app_main()'s first statement (above NVS init); fp_led_off() unconditional as the last statement before esp_deep_sleep_start() inside the single noreturn exit enter_deep_sleep()"
    verification:
      - kind: unit
        ref: "awk-extracted statement-order check on enter_deep_sleep() prints exactly 'fp_led_off();esp_deep_sleep_start();'; second awk check on app_main() confirms fp_led_on(); precedes nvs_flash_init("
        status: pass
      - kind: other
        ref: "grep -c 'led_enabled' firmware/main/app_main.c == 0 (file never reads the server field, so the toggle structurally cannot weaken the sleep-safety invariant); Log Line Contract 4/4 tokens unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "led_enabled boolean carried end-to-end: stub server emits it (hardcoded true), fp_display_t declares it, fp_api_get_display() parses it permissively (absent/null/wrong-typed all resolve to enabled, no clause added to the rejection block), state_machine.c consumes it once immediately after the display poll succeeds"
    verification:
      - kind: integration
        ref: "python3 stub-server/test_poll_cycle.py -> poll-cycle: 20/20 checks pass (check 5 now also asserts led_enabled:true is genuinely on the wire)"
        status: pass
      - kind: other
        ref: "awk-scoped rejection-block grep for 'led_enabled' == 0; hard-required clause count (!sleep_ok/cJSON_IsBool(reset)/url_valid) == 3; disp.led_enabled appears exactly once in state_machine.c, before the hash-skip lookup"
        status: pass
    human_judgment: false
  - id: D4
    description: "hardware/BRINGUP-LOG.md pre-registered 'User LED Bring-Up (GPIO21)' section (not-yet-confirmed banner, 4-row results table, written failure-outcome responses); REQUIREMENTS.md's Status-LEDs exclusion extended (not removed) to scope out this hidden bring-up aid"
    verification:
      - kind: other
        ref: "grep checks: 'NOT YET CONFIRMED' and 'GPIO21' and 'CONFIG_FP_LED_ACTIVE_LOW' present in the new BRINGUP-LOG.md section; 'Status LEDs' and 'bring-up/reflash aid' and 'ambient art' all present in REQUIREMENTS.md; git diff --name-only HEAD~1 lists only these two files"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-27
status: complete
---

# Quick Task 260827-wo4: Bring-Up Debug LED Summary

**GPIO21 built-in User LED wired unconditionally into the wake cycle (boot-time on, pre-sleep off) plus a permissively-parsed `led_enabled` protocol field end-to-end from the stub server through the firmware, so every flash/power-cycle is visibly observable and the toggle's firmware half never needs a future reflash**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-27T21:20:00Z (approx, from `PLAN_START_TIME`)
- **Completed:** 2026-08-27T21:56:39Z
- **Tasks:** 4/4 completed
- **Files modified:** 14

## Accomplishments

- `firmware/main/led.c`/`led.h`: a two-function `fp_led_on()`/`fp_led_off()` module driving GPIO21 (XIAO ESP32-S3's built-in User LED), lazily configured, polarity-driven by `CONFIG_FP_LED_ACTIVE_LOW`, and modelled directly on `battery.c`'s "never take the device down" error discipline
- Both wake-cycle call sites are now unconditional and structurally verified: `fp_led_on();` is the first statement of `app_main()` (above the NVS recovery branch that can erase a whole partition), and `fp_led_off();` is the statement immediately preceding `esp_deep_sleep_start();` inside `enter_deep_sleep()`, the single noreturn exit every branch funnels through
- The board profile gained `CONFIG_FP_PIN_LED=21`/`CONFIG_FP_LED_ACTIVE_LOW=y` under an honest NOT-YET-CONFIRMED banner, with zero collision against the project's existing 13 claimed GPIOs
- `led_enabled` now flows end to end: `stub-server/byos_server.py` emits it (hardcoded `true`), `fp_display_t`/`fp_api_get_display()` declare and parse it permissively (never rejects the response), and `state_machine.c`'s `fp_poll_once()` consumes it exactly once, immediately after the display poll succeeds and before every downstream exit - so the toggle can only ever extinguish the LED earlier, never keep it lit through sleep
- `hardware/BRINGUP-LOG.md` gained a pre-registered "User LED Bring-Up (GPIO21)" section (results table + written failure-outcome responses, written before the flash) that bundles into the developer's next flash session (already scheduled for plan 05-03's checkpoint); `REQUIREMENTS.md`'s Status-LEDs exclusion was scoped, not weakened, so shipped firmware and the requirements table stop contradicting each other

## Task Commits

1. **Task 1: Add the fp_led module and pin it in the EE02 board profile** - `7a2284a` (feat)
2. **Task 2: Wire the LED into the wake cycle at both ends, unconditionally** - `56b1dbd` (feat)
3. **Task 3: Carry led_enabled from the stub server to the firmware and act on it** - `4e2624b` (feat)
4. **Task 4: Record the unconfirmed pin claim and scope the Status-LEDs exclusion** - `13508ef` (docs)

_No TDD tasks in this plan (device-side GPIO/ESP-IDF logic isn't host-testable; the plan's own precedent for `battery.c` treats the host suite as a regression gate here, not a coverage gate)._

## Files Created/Modified

- `firmware/main/led.h` - Two-function public interface (`fp_led_on`/`fp_led_off`) and its wake-window-only contract
- `firmware/main/led.c` - Lazy GPIO configuration + polarity-aware on/off, no fatal abort-on-error macro
- `firmware/main/app_main.c` - Unconditional boot-time-on / pre-sleep-off call sites, `#include "led.h"`
- `firmware/main/CMakeLists.txt` - `led.c` registered in `SRCS`
- `firmware/main/Kconfig.projbuild` - New "Bring-up LED" menu (`FP_PIN_LED`, `FP_LED_ACTIVE_LOW`)
- `firmware/sdkconfig.ee02.defaults` - `CONFIG_FP_PIN_LED=21`/`CONFIG_FP_LED_ACTIVE_LOW=y` under a NOT-YET-CONFIRMED banner
- `firmware/main/api_client.h` - `fp_display_t.led_enabled`, documented as the struct's one optional field
- `firmware/main/api_client.c` - Permissive `led_enabled` fetch/resolve outside the rejection block
- `firmware/main/state_machine.c` - Conditional `fp_led_off()` call, `#include "led.h"`
- `firmware/VENDOR.md` - `api_client.c` vendor-delta row extended with the new field
- `stub-server/byos_server.py` - `/device/v1/display` response now emits `"led_enabled": True`
- `stub-server/test_poll_cycle.py` - Display-shape check (5) now also asserts `led_enabled:true` on the wire; validator docstring notes the deliberate non-validation
- `hardware/BRINGUP-LOG.md` - New "User LED Bring-Up (GPIO21)" pre-registered section
- `.planning/REQUIREMENTS.md` - Status-LEDs exclusion row scoped with a clarifying sentence

## Decisions Made

- GPIO21/active-low sourced from web aggregation (not an official schematic), same confidence posture as the battery-sense pins earlier in this phase - resolved by the same cheap mechanism (flash and observe) rather than more research, and explicitly recorded as such in both `Kconfig.projbuild`'s help text and `hardware/BRINGUP-LOG.md`
- `led_enabled` ships on the wire now, in both directions, even though real per-device configuration (NVS, web UI) is explicitly deferred - because the firmware's *reading* half can only change via a physical reflash, while the server's *setting* half can be redeployed any afternoon; shipping only the reading half now means the eventual real setting is a server-only change with zero firmware impact
- The field is parsed permissively rather than validated like `image_url`/`sleep_s`/`reset`: an absent, null or wrong-typed value must never turn a healthy poll into a rejected one and an exponential-backoff spiral over a purely cosmetic preference

## Deviations from Plan

None - plan executed exactly as written. Two comment-wording adjustments were made mid-Task-1 to keep the plan's own acceptance greps honest (not deviations from scope, just satisfying the plan's literal grep-based acceptance criteria):
- `led.c`'s error-discipline comment was reworded from naming the fatal abort macro literally to describing it in prose, since the literal spelling would have self-defeated the plan's own "grep -c '<macro>' returns 0" check
- Confirmed via `grep -c 'led_configure()'` that the plan's own comment referencing the lazy initialiser by name satisfies its "3 or more" acceptance count alongside the two real call sites

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All structural/automated verification in the plan's `<verification>` block passes: 4-suite host regression, the pre-sleep statement-order invariant, zero duplicate board-profile pins, the intact 4-line Log Line Contract, unchanged dependency manifest/`REQUIRES` list, this plan's own 14-file scope containment (`git diff --name-only HEAD~4..HEAD`), `poll-cycle: 20/20`, and `led_enabled` absent from `app_main.c` (the toggle structurally cannot reach the sleep-safety invariant)
- `firmware/build.sh` (containerised ESP-IDF 5.3.1 build) could not run - no Docker daemon reachable in this sandbox, exactly as plan 05-03 Task 2 recorded for the same reason. Rollback if a compile error surfaces: revert the one `led.c` line in `CMakeLists.txt`'s `SRCS` plus the two call sites in `app_main.c`
- The developer's next real flash - already scheduled for plan 05-03's blocking `checkpoint:human-verify` hardware task - now also carries this plan's `<human-check>`: watch for the LED lighting at boot, staying lit through the poll/refresh, and going fully dark through deep sleep (the outcome that matters most, since a lit-during-sleep LED is a real DEVICE-05 regression and must be treated as a defect before any battery discharge run)
- `led_enabled` reading the wire now means Phase 5's future companion-web-interface work (CFG-01..CFG-04) can add a real per-device toggle as a server-only change, with no further firmware work or reflash required

---
*Phase: 05-low-battery-indicator*
*Completed: 2026-08-27*

## Self-Check: PASSED

All 14 files_modified paths confirmed present on disk; all four task commit hashes (`7a2284a`, `56b1dbd`, `4e2624b`, `13508ef`) confirmed present in `git log --oneline --all`.
