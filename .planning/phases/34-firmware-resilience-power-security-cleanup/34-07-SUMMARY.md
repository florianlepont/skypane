---
phase: 34-firmware-resilience-power-security-cleanup
plan: 07
subsystem: firmware
tags: [esp-timer, task-watchdog, light-sleep, epd-driver, battery, esp-idf]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-02's wake_deadline.h (fp_wake_deadline_expired, fp_wake_slice_s, FP_WAKE_WORST_CASE_S) and battery_math.h's battery_math_average_mv, both pure and host-tested"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-04's Kconfig symbols (CONFIG_SKYPANE_WAKE_BUDGET_S, CONFIG_FP_MAX_GUARD_WAIT_S) and sdkconfig.defaults' CONFIG_ESP_TASK_WDT_INIT/PANIC/TIMEOUT_S=60"
provides:
  - "firmware/main/wake_guard.h/.c - fp_wake_guard_start/fp_wake_feed/fp_wake_checkpoint/fp_wake_expired/fp_wake_elapsed_ms/fp_wake_light_sleep_s: the esp_timer + esp_task_wdt glue around wake_deadline.c's pure arithmetic, with two _Static_assert lines tying the configured wake budget and light-sleep slice size to their respective ceilings"
  - "epd13in3e.c: epd_init returns ESP_FAIL on any GPIO/SPI setup failure instead of aborting (spi_bus_free on partial failure); epd_sleep only touches pins/SPI it actually set up; busy_wait/send_half feed the task watchdog; epd_blit checks the POF timeout"
  - "panel.c: the refresh-spacing wait uses fp_wake_light_sleep_s instead of vTaskDelay"
  - "battery.c/.h: fp_battery_mv() averages FP_BATTERY_SAMPLES=8 calibrated ADC reads via battery_math_average_mv(); battery.h documents the before-Wi-Fi call-site requirement for plan 34-08"
affects: ["34-08", "34-09", "34-11"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "esp_timer callback does only a flag store; every side effect (logging, the registered on_expired callback, sleep ordering) runs later in the main task via fp_wake_checkpoint(), called at points the caller has chosen to be safe (mirrors the panel_guard.c/panel.c pure-decision-vs-I/O split)"
    - "Two independent _Static_assert lines wire a Kconfig-configured runtime value to a compile-time invariant derived from other coded timeouts (FP_WAKE_WORST_CASE_S, FP_WAKE_LIGHT_SLEEP_SLICE_S), so a future Kconfig default change that breaks the invariant fails the build rather than only failing on hardware"
    - "Driver setup functions (epd_init) track *what actually got initialised* in separate static bools (s_gpio_ready vs s_bus_ready) so the teardown path (epd_sleep) can safely act on a partially-initialised driver instead of assuming all-or-nothing setup"

key-files:
  created:
    - firmware/main/wake_guard.h
    - firmware/main/wake_guard.c
  modified:
    - firmware/main/epd13in3e.c
    - firmware/main/panel.c
    - firmware/main/battery.c
    - firmware/main/battery.h

key-decisions:
  - "fp_wake_guard_start()/fp_wake_feed()/fp_wake_checkpoint() are not called anywhere yet - app_main.c stays untouched in this plan (plan 34-08's job) - so the two-mechanism budget exists as a ready module, not yet armed. epd13in3e.c's busy_wait/send_half and panel.c's spacing wait already call fp_wake_feed()/fp_wake_light_sleep_s(), which are safe no-ops (fp_wake_feed) or fall back to vTaskDelay (fp_wake_light_sleep_s, if esp_light_sleep_start ever errors) before the guard is started, matching the header's documented 'safe to call before fp_wake_guard_start() has run' contract."
  - "epd_init's new gpio_config(out) failure path returns before configuring the input BUSY pin or touching SPI at all, so s_bus_ready stays false and s_gpio_ready is only ever true once the output pins are confirmed configured - epd_sleep's two independent guards (s_bus_ready for the DSLP command, s_gpio_ready for driving PIN_EN low) can never touch an uninitialised SPI handle or an unconfigured GPIO regardless of which setup call failed."
  - "battery.c's per-sample failure is logged at ESP_LOGD (not LOGW) - a single dropped sample out of 8 is expected noise, not a warning-worthy event; only an all-samples-failed read (battery_math_average_mv returning 0) logs a warning and takes the existing zero/unknown-sentinel failure path."

requirements-completed: [FW-01, FW-02, FW-05, FW-11, FW-12]

# Metrics
duration: ~20min
completed: 2026-09-23
---

# Phase 34 Plan 07: wake_guard, panel driver errors/POF/light sleep, 8-sample battery read Summary

**New `wake_guard.c/.h` glues `esp_timer`/`esp_task_wdt` around plan 34-02's pure wake-deadline arithmetic (two `_Static_assert`s tying the configured wake budget and light-sleep slice to their ceilings); `epd_init`/`epd_sleep` in `epd13in3e.c` now degrade to a checked `ESP_FAIL` instead of aborting on GPIO/SPI setup failure, `epd_blit` checks its POF timeout, and the panel's refresh-spacing wait sleeps lightly instead of staying fully awake; `battery.c` now averages 8 calibrated ADC samples per wake.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-23
- **Tasks:** 3/3 completed
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- Created `firmware/main/wake_guard.h`/`.c`: `fp_wake_guard_start(on_expired)` records the wake's start time, arms a one-shot `esp_timer` for `CONFIG_SKYPANE_WAKE_BUDGET_S` seconds whose callback only sets a `volatile bool` flag (no logging, no sleep, no NVS - verified by reading the callback body), and subscribes the calling task via `esp_task_wdt_add(NULL)`, degrading cleanly (logged, not aborted) if either fails. `fp_wake_feed()` resets the task watchdog only when this call actually subscribed the task (tracked in a static bool, so it is safe to call before `fp_wake_guard_start()` has run - the panel driver does exactly this). `fp_wake_checkpoint()` feeds, then calls the registered `on_expired` callback once (with a one-time warning log) if the timer flag is set or `fp_wake_deadline_expired()` independently confirms expiry - the elapsed-time fallback means the budget holds even if the timer itself failed to arm. `fp_wake_light_sleep_s()` slices a wait into `FP_WAKE_LIGHT_SLEEP_SLICE_S` (20 s) chunks via `esp_sleep_enable_timer_wakeup`/`esp_light_sleep_start`, feeding the watchdog and yielding to idle tasks between slices, falling back to `vTaskDelay` for a slice if light sleep itself errors, and re-disabling the timer wakeup source afterward so `app_main.c`'s deep-sleep path re-arms it cleanly. Two `_Static_assert` lines guard the sizing invariants: the wake budget must exceed `FP_WAKE_WORST_CASE_S(CONFIG_FP_MAX_GUARD_WAIT_S)` (holds at defaults: 300 > 250), and the task watchdog timeout must exceed the light-sleep slice size (holds: 60 > 20) (FW-02).
- `epd13in3e.c`: the four `ESP_ERROR_CHECK` calls inside `epd_init`'s GPIO/SPI setup are replaced with checked returns that log `ESP_LOGE` and return `ESP_FAIL` through the function's existing `esp_err_t` path; `spi_bus_free(SPI2_HOST)` releases the bus if `spi_bus_add_device` fails after `spi_bus_initialize` succeeded. `epd_sleep()` now tracks two independent static bools (`s_gpio_ready`, set once the output-pin `gpio_config` succeeds; `s_bus_ready`, set once the whole SPI setup succeeds) so it only sends the DSLP command if the bus is actually up and only drives `PIN_EN` low if the output pins were actually configured - it can never touch an uninitialised SPI handle regardless of which setup call failed (FW-01). `busy_wait()`'s polling loop and `send_half()`'s periodic yield now call `fp_wake_feed()` (the DRF wait alone allows up to 60 s, at the task watchdog's own ceiling). `epd_blit()` now checks `busy_wait("POF", 3000)` and returns `ESP_FAIL` on timeout instead of ignoring it, so the state machine reports `step=blit` (FW-05). The 800 µs per-row `esp_rom_delay_us` pacing is unchanged, with a new comment citing `Kconfig.projbuild`'s `FP_MIN_REFRESH_SPACING_S` datasheet note as the reason it is not shortened (FW-12).
- `panel.c`: the `FP_PANEL_DRAW_AFTER_WAIT` branch now calls `fp_wake_light_sleep_s(wait_s)` instead of `vTaskDelay(pdMS_TO_TICKS(wait_s * 1000U))`, with the comment above it rewritten to state the current reason (radio already down, panel not yet powered, PSRAM retained across light sleep) instead of a stale rationale; the surrounding `ESP_LOGI`/`account_awake_time()` calls are unchanged (FW-12).
- `battery.c`: added `#define FP_BATTERY_SAMPLES 8`; the single `adc_oneshot_get_calibrated_result()` call is replaced by an 8-iteration loop into a fixed `int samples[8]` array (a failed individual sample stores `-1` and logs at `ESP_LOGD`, not a warning - one dropped sample out of eight is expected noise), then `battery_math_average_mv()` (plan 34-02) computes the mean over the valid samples with no inter-sample delay (the divider has already settled via `FP_BATTERY_SETTLE_MS`, and oneshot conversions are microseconds apart). A zero average (no valid sample at all) takes the existing failure path unchanged: release the calibration scheme and ADC unit, drive the enable line low, cache 0, return 0. The `"battery mv=%u pin_mv=%d"` diagnostic log line keeps its exact shape - `pin_mv` is now the averaged value (FW-11). `battery.h`'s doc comment now states the 8-sample-mean measurement and the before-Wi-Fi call-site requirement (the radio's draw sags the pack and couples noise into the ADC); the actual call-site move happens in `app_main.c`, which is plan 34-08's job.
- Verified every task against the real `espressif/idf:v5.3.1` container: three from-scratch (`rm -rf build-ee02`) production builds (one per task) all compiled clean with zero warnings on the new/changed files, plus one `SKYPANE_PROFILE=dev SKYPANE_FAULT=task_wdt` build after Task 3 (also clean) as a sanity check that the dev/fault Kconfig overlay path still builds. `firmware/tests/check_production_config.sh built firmware/build-ee02` passed after Tasks 2 and 3. `sh firmware/tests/run_host_tests.sh` passed 8/8 suites (unaffected - none of this plan's files have a `test_*.c` counterpart) after every task.

## Task Commits

1. **Task 1: wake_guard - whole-wake budget timer and task-watchdog glue** - `70ca527` (feat)
2. **Task 2: Panel driver - errors instead of aborts, checked POF, fed waits, light-sleep spacing** - `fc3e4c2` (fix)
3. **Task 3: 8-sample averaged battery read** - `ae822ca` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/main/wake_guard.h`/`.c` - new: task-watchdog + wake-budget-timer glue, two `_Static_assert` sizing invariants, sliced light sleep
- `firmware/main/epd13in3e.c` - `epd_init`/`epd_sleep` degrade instead of abort; `busy_wait`/`send_half` feed the watchdog; `epd_blit` checks POF
- `firmware/main/panel.c` - refresh-spacing wait uses `fp_wake_light_sleep_s` instead of `vTaskDelay`
- `firmware/main/battery.c` - 8-sample averaged ADC read via `battery_math_average_mv`
- `firmware/main/battery.h` - doc comment updated for the 8-sample mean and the before-Wi-Fi call-site requirement

## Decisions Made

- `fp_wake_guard_start`/`fp_wake_feed`/`fp_wake_checkpoint` are not called anywhere in this plan - `app_main.c` is untouched, matching the plan's stated scope boundary (plan 34-08 wires the deadline in). The two call sites this plan *does* add (`epd13in3e.c`'s `fp_wake_feed()`, `panel.c`'s `fp_wake_light_sleep_s()`) are both safe to run before the guard is ever started: `fp_wake_feed()` is a no-op until a task has actually subscribed, and `fp_wake_light_sleep_s()` degrades to `vTaskDelay` only if `esp_light_sleep_start()` itself errors, otherwise it sleeps and returns exactly as designed regardless of whether the watchdog/budget are armed.
- `epd_init`'s GPIO/SPI setup failures return immediately rather than accumulating with `err |=` (unlike the register-write section below them) - each setup call gates the next one (there is no SPI bus to add a device to if `spi_bus_initialize` failed), so an early return is more correct than the accumulate-then-check idiom used for the independent register writes.
- Per-sample battery read failures log at `ESP_LOGD`, not `ESP_LOGW` - only a fully-failed read (all 8 samples invalid) is warning-worthy; the plan's own module boundary (`battery_math_average_mv`) already treats individual failed samples as expected, excluded entries rather than errors.

## Deviations from Plan

None - plan executed exactly as written. All acceptance-criteria greps pass, all three from-scratch container builds succeeded with zero warnings on the touched files, and `check_production_config.sh`/`run_host_tests.sh` both passed after every task.

## Issues Encountered

None. One self-correction during Task 1: the first draft of the `_Static_assert(CONFIG_SKYPANE_WAKE_BUDGET_S > FP_WAKE_WORST_CASE_S(...))` line was wrapped across two source lines for readability, which broke the plan's single-line grep acceptance check (`grep -q "_Static_assert(CONFIG_SKYPANE_WAKE_BUDGET_S > FP_WAKE_WORST_CASE_S"`); reformatted onto one line before committing, no behavior change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **What plan 34-08 needs to wire in `app_main.c`:** call `fp_wake_guard_start(on_expired)` early in `app_main()` (after NVS init, before the wake dispatcher), where `on_expired` is a `fp_wake_expired_fn` (`void (*)(void)`, must not return) that records the wake as a failure and calls `enter_deep_sleep()` - the same single exit every other path already uses. Call `fp_wake_checkpoint()` at each blocking-call boundary in `state_machine.c`'s poll (Wi-Fi connect, setup, display fetch, download) - each of those call sites is safe to sleep at (no panel power, no half-sent SPI transaction in flight). Use `fp_wake_elapsed_ms()` for the diagnostic wake-duration line FW-10 wants. Do **not** call `fp_wake_checkpoint()` from inside `fp_panel_draw()` or anywhere between `epd_init()` and `epd_sleep()` - that window is a hard exclusion, called out in `wake_guard.h`'s own doc comment, because tearing down mid-blit through the wrong exit path would corrupt a refresh in progress.
- Plan 34-09 (api_client keep-alive) can call `fp_wake_feed()`/`fp_wake_checkpoint()` from inside `api_client.c`'s download loop once the guard is armed by 34-08 - both functions are already safe to call unconditionally (no-op before the guard starts).
- **What the 34-11 hardware session needs to observe (no hardware attached to this session, so none of the following is proven yet):**
  1. Whether `CONFIG_ESP_TASK_WDT_TIMEOUT_S`'s tick-based countdown actually keeps advancing through `esp_light_sleep_start()` - RESEARCH.md flags this as an open, ESP-IDF-undocumented question. `fp_wake_light_sleep_s()`'s 20 s slice-with-feed-between-slices design assumes the *safe* answer (it might not need to), but this needs a real serial-log capture of a guard-wait light sleep with the watchdog armed to confirm no spurious `ESP_RST_TASK_WDT` reset occurs.
  2. Real wall-clock timing for `epd_init`'s new checked-failure paths - simulating a GPIO/SPI setup failure (e.g. by feeding a fault-injection-style bad pin config, or physically disconnecting a wire) to confirm `epd_init` returns cleanly instead of hanging or crashing, and that `epd_sleep()` afterward does not touch anything uninitialised.
  3. A real `busy_wait("POF", ...)` timeout (e.g. by interrupting the panel mid-refresh) to confirm `epd_blit` now returns `ESP_FAIL` and the state machine actually reports `step=blit`, not a silent success.
  4. Real ADC noise floor - comparing the 8-sample-averaged `battery mv=` line against a multimeter reading and, ideally, against the previous single-sample line's variance across several wakes, to confirm the averaging measurably reduces jitter.
  5. Actual light-sleep current draw during the refresh-spacing wait versus the previous full-`vTaskDelay` wait, to give FW-12's own success criterion a real number.
- No open blockers. `firmware/main/wake_guard.h`/`.c`, and the touched slices of `epd13in3e.c`, `panel.c`, `battery.c`/`.h` are single-owner for this plan; plan 34-08 owns `app_main.c` and the remaining slice of `state_machine.c`.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/main/wake_guard.h`
- FOUND: `firmware/main/wake_guard.c`
- FOUND: `firmware/main/epd13in3e.c` (modified)
- FOUND: `firmware/main/panel.c` (modified)
- FOUND: `firmware/main/battery.c` (modified)
- FOUND: `firmware/main/battery.h` (modified)
- FOUND commit `70ca527` (Task 1)
- FOUND commit `fc3e4c2` (Task 2)
- FOUND commit `ae822ca` (Task 3)
- FOUND commit `b52e2df` (SUMMARY.md)
