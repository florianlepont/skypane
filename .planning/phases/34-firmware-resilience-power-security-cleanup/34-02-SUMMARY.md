---
phase: 34-firmware-resilience-power-security-cleanup
plan: 02
subsystem: firmware
tags: [reset-reason, watchdog, sleep-decision, battery, host-tests, esp-idf]

requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-01's convention-based run_host_tests.sh discovery (test_<name>.c -> main/<name>.c) and SRC_DIRS \".\" CMakeLists.txt, which this plan's four new suites and three new main/*.c modules rely on with no runner or CMake edit"
provides:
  - "firmware/main/reset_reason.h/.c - pure classification of esp_reset_reason_t into abnormal/healthy, plus the Log Line Contract's honest wake-reason token (rtc|power-on|button|other), numerically mirroring ESP-IDF v5.3.1's esp_reset_reason_t (FW-01)"
  - "firmware/main/wake_deadline.h/.c - pure whole-wake deadline arithmetic (elapsed-microseconds vs. budget-seconds expiry, light-sleep slice sizing) plus FP_WAKE_WORST_CASE_S(guard_wait_s), which computes to 250s at the default 90s guard wait from the coded per-stage timeouts (FW-02)"
  - "firmware/main/sleep_decision.h/.c - the sleep-plan decision extracted from app_main.c's wake dispatcher as one pure, tested function: failure -> backoff, success -> server sleep_s, deferred -> panel wait + 5s when shorter, and a zero server sleep_s treated as failure under any outcome (FW-06)"
  - "firmware/main/battery_math.c's new battery_math_average_mv - rounded mean over non-negative samples, ignoring failed (negative) reads, 0 when none are valid (FW-11)"
  - "firmware/tests/test_reset_reason.c, test_wake_deadline.c, test_sleep_decision.c, and battery-averaging cases added to test_battery_math.c - all four discovered automatically by 34-01's run_host_tests.sh"
affects: [34-07, 34-08]

tech-stack:
  added: []
  patterns:
    - "Pure decision module split continues the backoff.c/panel_guard.c/validate.c template: #pragma once header carrying the full rationale, only stdbool.h/stdint.h/stddef.h, one function or enum-returning decision per rule, host-tested via RED (module absent, confirmed failing to compile) then GREEN (module restored, tests pass)"
    - "Numeric enum mirroring: reset_reason.h's FP_RST_* enum reproduces ESP-IDF v5.3.1's esp_reset_reason_t value order exactly, so the module needs no ESP-IDF include yet stays wire-compatible; a _Static_assert tying the two together is deferred to plan 34-08's app_main.c change, which is the first place esp_system.h is actually included"

key-files:
  created:
    - firmware/main/reset_reason.h
    - firmware/main/reset_reason.c
    - firmware/main/wake_deadline.h
    - firmware/main/wake_deadline.c
    - firmware/main/sleep_decision.h
    - firmware/main/sleep_decision.c
    - firmware/tests/test_reset_reason.c
    - firmware/tests/test_wake_deadline.c
    - firmware/tests/test_sleep_decision.c
  modified:
    - firmware/main/battery_math.h
    - firmware/main/battery_math.c
    - firmware/tests/test_battery_math.c

key-decisions:
  - "A zero server_sleep_s is treated as a failure (backoff) under every wake outcome, not only FP_WAKE_OUTCOME_OK - the plan's behavior spec only asserts this for OK, but the threat model (T-34-02-01) says \"no path yields a zero-second wake loop\", so fp_sleep_decide applies the rule uniformly via `outcome == FP_WAKE_OUTCOME_FAILED || server_sleep_s == 0` rather than special-casing OK."
  - "fp_wake_reason_token's inline comment avoids repeating the literal string \"power-on\" in quotes, so the module's single source-of-truth occurrence of that literal (the actual return statement) is unambiguous for the plan's `grep -c '\"power-on\"'` acceptance check - a one-word comment rewrite, not a behavior change."
  - "battery_math_average_mv accumulates in uint64_t and rounds with `(sum + valid/2) / valid`, matching the plan's exact rounding formula; validated against the container's real ESP-IDF build (not just host cc) since main/CMakeLists.txt's SRC_DIRS \".\" only re-globs new files on a CMake reconfigure, not on an ordinary incremental `ninja all` - the phase's build-ee02 directory had to be removed and rebuilt from scratch to prove the three new modules actually compile into the firmware image."

requirements-completed: [FW-01, FW-02, FW-06, FW-11]

duration: ~45m
completed: 2026-09-23
status: complete
---

# Phase 34 Plan 02: Reset Classification, Wake Deadline, Sleep Decision, Battery Averaging Summary

**Four pure, host-tested decision helpers (reset-reason classification with an honest wake-reason token, whole-wake deadline arithmetic sized from the coded per-stage timeouts, the sleep-plan decision extracted from app_main.c, and 8-sample battery averaging) landed with zero ESP-IDF includes, verified against both the host `cc` and a from-scratch real `espressif/idf:v5.3.1` container build.**

## Performance

- **Duration:** ~45m
- **Completed:** 2026-09-23
- **Tasks:** 2/2 completed
- **Files modified:** 12 (9 created, 3 modified)

## Accomplishments

- Created `firmware/main/reset_reason.h`/`.c`: `FP_RST_*` enum mirroring `esp_reset_reason_t` (ESP-IDF v5.3.1) value-for-value, `fp_reset_is_abnormal` (true for panic, both watchdogs, brownout, power glitch, CPU lockup; false for every deliberate/healthy reset and for out-of-range values), `fp_reset_label` (diagnostic string per reason, "unknown" fallback), and `fp_wake_reason_token` (the Log Line Contract's `rtc|power-on|button|other` token - "power-on" only for a genuine `FP_RST_POWERON`, "other" for every abnormal or unrecognised reset, so the label stops claiming power-on after a crash) (FW-01).
- Created `firmware/main/wake_deadline.h`/`.c`: `fp_wake_deadline_expired(now_us, start_us, budget_s)` (pure microseconds-vs-budget expiry, exact at the boundary, never expired if the clock hasn't advanced), `fp_wake_slice_s` (light-sleep slice sizing so a future TWDT feed can happen between slices), and `FP_WAKE_WORST_CASE_S(guard_wait_s)` summing the six coded per-stage timeouts (Wi-Fi 15s + SNTP 10s + setup 15s + display 20s + download 30s + blit 70s = 160s) plus the guard wait - `FP_WAKE_WORST_CASE_S(90) == 250` and `FP_WAKE_WORST_CASE_S(0) == 160`, both asserted in the test and usable in a future `_Static_assert` against the configured deadline (FW-02).
- Created `firmware/main/sleep_decision.h`/`.c`: `fp_sleep_decide` extracts app_main.c's failure/success/deferred sleep-plan branch verbatim in behavior (backoff via `backoff.c`'s `fp_backoff_seconds`, counter saturating at `UINT8_MAX`; server `sleep_s` on success with the counter reset to 0; panel-wait-plus-5 shortening on a deferred draw only when the wait is both non-zero and strictly shorter), plus the new defensive rule that a zero server `sleep_s` is always treated as a failure regardless of outcome, so no code path can arm a zero-second timer wake (FW-06).
- Extended `firmware/main/battery_math.h`/`.c` with `battery_math_average_mv`: `uint64_t`-accumulated, rounded mean over the non-negative entries of a sample array, excluding negative (failed-read) entries rather than dragging the average toward zero, returning 0 for `NULL`, `n == 0`, or an all-negative array - the same "0 means unknown" sentinel the existing divider path already uses (FW-11).
- Wrote all four host tests (`test_reset_reason.c`, `test_wake_deadline.c`, `test_sleep_decision.c`, and battery-averaging cases in `test_battery_math.c`) following the RED/GREEN cycle: each implementation `.c` file (or, for the battery case, the pre-task `battery_math.c`/`.h` pair) was temporarily moved aside/reverted, the corresponding direct `cc` command was confirmed to fail to compile, then the implementation was restored and the same command confirmed passing. `run_host_tests.sh` (from plan 34-01) picked up all four new/extended suites automatically with no runner edit - `8 suites, all hardware-free firmware suites passed`.
- Ran a from-scratch (`rm -rf build-ee02`) real `espressif/idf:v5.3.1` container build to confirm `reset_reason.c`, `wake_deadline.c`, and `sleep_decision.c` all compile into `skypane.bin` via `main/CMakeLists.txt`'s `SRC_DIRS "."` with zero warnings - an incremental build alone would not have proven this, since CMake only re-globs `main/` on reconfigure, not on an ordinary `ninja all`.

## Task Commits

1. **Task 1: reset_reason and wake_deadline pure modules with host tests** - `496ff23` (test, RED) + `b563ea8` (feat, GREEN)
2. **Task 2: sleep_decision pure module and battery sample averaging** - `50c4272` (test, RED) + `b55a09f` (feat, GREEN)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/main/reset_reason.h` / `.c` - Reset classification, diagnostic label, and the Log Line Contract's honest wake-reason token; no ESP-IDF includes
- `firmware/main/wake_deadline.h` / `.c` - Pure whole-wake deadline expiry, light-sleep slice sizing, and the `FP_WAKE_WORST_CASE_S` worst-case macro
- `firmware/main/sleep_decision.h` / `.c` - The sleep-plan decision extracted from `app_main.c`'s wake dispatcher, including the zero-`sleep_s`-is-failure defensive rule
- `firmware/main/battery_math.h` / `.c` - Adds `battery_math_average_mv`; `battery_math_apply_divider` untouched
- `firmware/tests/test_reset_reason.c` - Host test for classification, labels, and the wake-reason token
- `firmware/tests/test_wake_deadline.c` - Host test for expiry boundary conditions, slice sizing, and the worst-case macro
- `firmware/tests/test_sleep_decision.c` - Host test for the sleep-plan decision, `HOST_TEST_DEPS: backoff.c` to link the real backoff implementation
- `firmware/tests/test_battery_math.c` - Extended with `battery_math_average_mv` cases; existing divider asserts unchanged

## Decisions Made

- **Zero server `sleep_s` is a failure under any wake outcome**, not only `FP_WAKE_OUTCOME_OK` as the plan's behavior bullets literally enumerate - the threat model's own mitigation text ("no path yields a zero-second wake loop") reads as outcome-independent, so `fp_sleep_decide` checks `server_sleep_s == 0` unconditionally rather than gating it to one outcome. This is a superset of the required behavior and does not change any of the plan's stated test cases.
- **`fp_wake_reason_token`'s explanatory comment was reworded to avoid a second quoted occurrence of `"power-on"`** so the plan's `grep -c '"power-on"' firmware/main/reset_reason.c` acceptance check (expected: exactly 1) passes cleanly - a comment-only edit made during self-verification, not a behavior change.
- **Verified the real ESP-IDF container build from a clean `build-ee02` directory**, not an incremental one, after discovering that an incremental `ninja all` silently skips newly added `main/*.c` files until CMake reconfigures - this is a build-tooling property of `SRC_DIRS "."` worth knowing for future plans in this phase that add new `main/*.c` files (34-07, 34-08): a stale build directory can mask a missing source file.

## Deviations from Plan

None - plan executed exactly as written, including the RED-first TDD sequence for all four suites (each implementation file, or the pre-task battery_math pair, was moved aside/reverted, the compile failure confirmed, then restored) and the container-build verification beyond what the plan's own `<verify>` block strictly required.

## Issues Encountered

None. The incremental-build gap described above was caught and resolved by a full rebuild before it could hide anything from later plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `reset_reason.h`, `wake_deadline.h`, and `sleep_decision.h` are ready for plan 34-08 to wire into `app_main.c`: `_Static_assert`s tying `FP_RST_*` to `esp_reset_reason_t`, the `esp_timer`/`esp_task_wdt` glue arming `fp_wake_deadline_expired`'s budget, and `app_main.c`'s existing failure/success/deferred branch replaced by a single `fp_sleep_decide` call.
- `wake_deadline.h`'s per-stage macros and `FP_WAKE_WORST_CASE_S` give plan 34-07's `esp_timer`/`esp_task_wdt` setup a ready-made, drift-proof budget number (250s at the default 90s guard) instead of a hand-typed constant.
- `battery_math_average_mv` is ready for `battery.c`'s 8-sample read loop (FW-11) to call once per wake, before the divider conversion.
- Confirmed live that `main/CMakeLists.txt`'s `SRC_DIRS "."` needs a CMake reconfigure (a `rm -rf build-ee02` or `idf.py reconfigure`) to notice a brand-new `main/*.c` file - worth remembering for 34-07/34-08's own new files.
- No open blockers for the next wave.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/main/reset_reason.h`
- FOUND: `firmware/main/reset_reason.c`
- FOUND: `firmware/main/wake_deadline.h`
- FOUND: `firmware/main/wake_deadline.c`
- FOUND: `firmware/main/sleep_decision.h`
- FOUND: `firmware/main/sleep_decision.c`
- FOUND: `firmware/tests/test_reset_reason.c`
- FOUND: `firmware/tests/test_wake_deadline.c`
- FOUND: `firmware/tests/test_sleep_decision.c`
- FOUND: `firmware/main/battery_math.h` (modified)
- FOUND: `firmware/main/battery_math.c` (modified)
- FOUND: `firmware/tests/test_battery_math.c` (modified)
- FOUND commit `496ff23` (Task 1, RED)
- FOUND commit `b563ea8` (Task 1, GREEN)
- FOUND commit `50c4272` (Task 2, RED)
- FOUND commit `b55a09f` (Task 2, GREEN)
