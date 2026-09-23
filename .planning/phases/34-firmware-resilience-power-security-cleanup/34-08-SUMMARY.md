---
phase: 34-firmware-resilience-power-security-cleanup
plan: 08
subsystem: firmware
tags: [esp-idf, reset-reason, task-watchdog, fault-injection, dhcp, static-ip, esp-timer]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-02's reset_reason.h (FP_RST_*, fp_reset_is_abnormal, fp_reset_label, fp_wake_reason_token) and sleep_decision.h (fp_sleep_decide, fp_wake_outcome_t, fp_sleep_plan_t), both pure and host-tested"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-07's wake_guard.h (fp_wake_guard_start/fp_wake_feed/fp_wake_checkpoint/fp_wake_expired/fp_wake_elapsed_ms/fp_wake_light_sleep_s) and battery.h's fp_battery_mv(), the esp_timer/task-watchdog glue this plan arms"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-06's api_client.h (FP_ERR_HTTP_AUTH/FP_ERR_ENROL_REJECTED/FP_ERR_NO_SECRET/FP_ERR_CONFIG, fp_api_setup(void)/fp_api_release(void)) and nvs_util.h (fp_nvs_get_str/fp_nvs_set_str)"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-04's CONFIG_SKYPANE_FAULT_INJECT_* Kconfig choice and CONFIG_SKYPANE_WAKE_BUDGET_S"
provides:
  - "firmware/main/fault_inject.h/.c - bench-only fault triggers (panic, task-watchdog hang, interrupt-watchdog spin, past-budget slow wake) selected by CONFIG_SKYPANE_FAULT_INJECT_*, compiled to nothing (not even the SKYPANE-FAULT-INJECT string) when NONE is selected"
  - "firmware/main/state_machine.c wired into the wake budget: fp_wake_checkpoint() after Wi-Fi/setup/display and again immediately before the panel draws (never after); per-stage wall-clock timings written directly into the caller's fp_poll_timing_t as each stage completes; a single step_for(esp_err_t) table mapping every FP_ERR_* to its Log Line Contract token (auth, enrol, secret, config, plus the existing tokens); hash-skip read/write moved onto nvs_util.c (no more nvs_open in this file)"
  - "firmware/main/app_main.c rewritten: reset-reason gate (nine _Static_asserts tying reset_reason.h's FP_RST_* mirror to esp_reset_reason_t) that backs off without starting the radio on any abnormal reset; fp_wake_guard_start()/fp_wake_checkpoint() arming the wake budget and task watchdog; fp_battery_mv() called before Wi-Fi; fp_sleep_decide() replacing the inline failure/success/deferred branch; a diagnostic `wake timing` line (tag fp_diag) before every deep sleep; the five Log Line Contract lines unchanged byte-for-byte"
  - "firmware/main/wifi.c's optional SKYPANE_STATIC_IP fallback (D-34-03) - compiled out entirely unless all four macros (SKYPANE_STATIC_IP/_NETMASK/_GW/_DNS) are defined in secrets.h; a #error catches a partially-configured set"
affects: ["34-09", "34-10", "34-11"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bench-only fault hook compiled entirely out of production via an #if !CONFIG_SKYPANE_FAULT_INJECT_NONE guard around the whole .c body, with the header's own default branch providing a static inline no-op - no Kconfig-conditional call sites needed at the one call site in state_machine.c"
    - "Diagnostic per-stage timing written directly into the caller-owned struct at each measurement point (not accumulated locally and copied at return) so a wake-budget expiry mid-poll still reports whatever stages actually completed, since the deadline callback's fail_and_sleep() never returns control to fp_poll_once() to do a final copy"
    - "fail_and_sleep() as a self-contained, independently-NVS-opening failure exit, reachable both from app_main()'s own control flow and from a bare wake_guard.h function-pointer callback with no access to app_main()'s locals"

key-files:
  created:
    - firmware/main/fault_inject.h
    - firmware/main/fault_inject.c
  modified:
    - firmware/main/app_main.c
    - firmware/main/state_machine.h
    - firmware/main/state_machine.c
    - firmware/main/wifi.c
    - firmware/main/secrets.example.h

key-decisions:
  - "fp_poll_timing_t's fields are written directly into *timing_out at each stage boundary inside fp_poll_once(), not accumulated in a local struct and copied at return - the wake-budget deadline callback (on_wake_deadline, invoked from inside fp_wake_checkpoint() partway through a poll) is noreturn and never lets fp_poll_once() reach a return statement, so a copy-at-return design would silently show every stage as 0 on a deadline-triggered sleep; writing live means only the stages actually reached before expiry are non-zero, matching the plan's own 'stage fields 0 when not reached' wording literally."
  - "app_main() opens and closes its own NVS handle twice (once for the boot counter, once for the final backoff read/write) rather than keeping one handle open across the whole function as the pre-plan code did - fail_and_sleep() (reachable from on_wake_deadline(), a bare function pointer with no access to app_main()'s locals) has to open its own handle regardless, so app_main() closing its own handle promptly between uses is simpler than threading a shared handle through fail_and_sleep()'s independent call sites, and matches nvs_util.c's project-wide 'never crash on an NVS failure' convention by treating the second open's failure as a soft degrade (backoff_n stays 0) rather than an ESP_ERROR_CHECK."
  - "The wake reason token is computed from a single esp_reset_reason() read taken once, early, and reused both for the wake reason=... log line and the later fp_boot reset reason=... diagnostic line - the plan's prose lists the boot-count/wake-reason line before the reset-reason read, but fp_wake_reason_token(cause, reset_reason) needs the reset reason value as an input, so the two statements are necessarily reordered relative to the plan's prose while preserving every grep-checked ordering constraint (guard-start before nvs_flash_init, abnormal-reset branch before battery/poll)."
  - "Verified directly against the ESP-IDF v5.3.1 container's esp_netif source (esp_netif_handlers.c's esp_netif_action_connected()) rather than assuming: with the DHCP client stopped and a valid static IP set, esp_netif itself posts IP_EVENT_STA_GOT_IP once WIFI_EVENT_STA_CONNECTED fires - no extra CONNECTED_BIT-on-WIFI_EVENT_STA_CONNECTED fallback was needed, so fp_wifi_connect()'s existing xEventGroupWaitBits() wait is untouched by the static-IP path."

requirements-completed: [FW-01, FW-02, FW-03, FW-06, FW-08, FW-09, FW-10, FW-11, FW-14]

# Metrics
duration: ~55min
completed: 2026-09-23
---

# Phase 34 Plan 08: app_main/state_machine wiring — reset backoff, deadline, step tokens, timing line, fault hooks, static IP Summary

**A crash, brownout or watchdog reset now backs off without ever starting the radio, a hung or over-budget wake ends deterministically at its deadline (bench-verifiable via a new dev-only fault hook compiled out of production), every new failure path gets its own Log Line Contract step token, a diagnostic per-stage timing line reports before every sleep, and an optional off-by-default static IP exists for the hardware session to measure against DHCP.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-23
- **Tasks:** 3/3 completed
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- **`fault_inject.h`/`.c`** (new): `fp_fault_inject_point()` is a `static inline` no-op when `CONFIG_SKYPANE_FAULT_INJECT_NONE` is selected (the header's own branch), and `fault_inject.c`'s entire body is excluded from the translation unit in that case — confirmed by grepping a production build's `skypane.bin` for `SKYPANE-FAULT-INJECT` (0 occurrences) versus a `SKYPANE_FAULT=slow_wake` dev build's `skypane.bin` (1 occurrence). The four non-NONE branches: `PANIC` calls `abort()`; `TASK_WDT` spins in `vTaskDelay` without ever feeding the task watchdog, so it panics within the 60 s `CONFIG_ESP_TASK_WDT_TIMEOUT_S` ceiling; `INT_WDT` disables interrupts and spins, starving the interrupt watchdog; `SLOW_WAKE` keeps calling `fp_wake_checkpoint()` every second so only the wake budget — never the 60 s task watchdog — ends it, verifying the `step=deadline` path specifically. Called once, right after Wi-Fi connects in `state_machine.c`.
- **`state_machine.h`/`.c`**: `fp_poll_timing_t` (five `uint32_t` stage fields) added to the header; `fp_poll_once()`'s signature gained a `fp_poll_timing_t *timing_out` parameter (NULL-safe). `state_machine.c` calls `fp_wake_checkpoint()` after Wi-Fi connects, after setup (when it runs), after the display fetch, and once more immediately before `fp_panel_draw()` — never after, since the panel being powered is a hard exclusion `wake_guard.h` itself documents. `esp_timer_get_time()` brackets each stage and writes straight into `timing_out`'s matching field the instant that stage finishes, rather than being accumulated locally and copied at the function's return — a deliberate choice so a wake-budget expiry mid-poll (which diverts through `on_wake_deadline()`, a `noreturn` callback that never lets `fp_poll_once()` reach any of its own `return` statements) still reports the stages that actually completed. A new `step_for(esp_err_t)` helper — the single table `FP_ERR_NO_SECRET`→`"secret"`, `FP_ERR_ENROL_REJECTED`→`"enrol"`, `FP_ERR_CONFIG`→`"config"`, `FP_ERR_HTTP_AUTH`→`"auth"`, `FP_ERR_HTTP_STATUS`→`"status"`, `FP_ERR_HTTP_JSON`→`"json"`, else `"http"` — replaces the two inline ternary chains for setup and display failures (FW-14). The hash-skip read and the post-blit hash write now go through `fp_nvs_get_str`/`fp_nvs_set_str` (`nvs_util.h`, plan 34-06) instead of hand-rolled `nvs_open`/`nvs_close` pairs — `state_machine.c` no longer calls `nvs_open` at all (FW-14). `fp_api_release()` is called on the hash-skip early return (in addition to its existing call site before `fp_wifi_stop()`).
- **`app_main.c`** rewritten around the wake budget and reset classification: nine `_Static_assert`s (`ESP_RST_POWERON`, `PANIC`, `INT_WDT`, `TASK_WDT`, `WDT`, `DEEPSLEEP`, `BROWNOUT`, `PWR_GLITCH`, `CPU_LOCKUP`) tie `reset_reason.h`'s pure `FP_RST_*` mirror to the real `esp_reset_reason_t` at compile time, so a future ESP-IDF enum reorder fails the build instead of silently misclassifying resets. `fp_wake_guard_start(on_wake_deadline)` is the first action after the LED, ahead of `nvs_flash_init()`. `esp_reset_reason()` is read once, early, and used both for the `wake reason=` token (via `fp_wake_reason_token`, whose "power-on" branch is now honest — a crash reports "other") and the `fp_boot`-tagged `reset reason=` diagnostic line; `fp_reset_is_abnormal(rr)` routes straight to `fail_and_sleep("reset")` before `fp_battery_mv()` or `fp_poll_once()` ever run (FW-01). `fp_battery_mv()` is called before Wi-Fi (FW-11, matching `battery.h`'s own documented requirement). The old inline failure/success/deferred branch is gone; both the failure path and the success/deferred path now call `fp_sleep_decide()` (plan 34-02) to get a `fp_sleep_plan_t`, including a guard for the "pure helper says this succeeded wake actually has a zero-second server sleep_s" edge case (`step=json`, via `fail_and_sleep`). A new `log_wake_timing()` (tag `fp_diag`) emits `wake timing total_ms=... wifi_ms=... setup_ms=... display_ms=... download_ms=... draw_ms=...` immediately before every `enter_deep_sleep()` call, using `fp_wake_elapsed_ms()` for the total and the file-scope `s_timing` (populated live by `fp_poll_once()`) for the per-stage breakdown. The five Log Line Contract lines (`wake reason=`, `poll ok`, `poll fail`, `blit ok`, `sleep enter`) are byte-identical to before; `fp_backoff_seconds()` is no longer called directly in this file (the decision now lives entirely in `fp_sleep_decide`).
- **`wifi.c`**: kept the netif pointer from `esp_netif_create_default_wifi_sta()` in a new static; under `#ifdef SKYPANE_STATIC_IP` only, a new `apply_static_ip()` stops the DHCP client (tolerating "already stopped"), sets a fixed IP/netmask/gateway via `esp_netif_set_ip_info`, and sets the DNS server via `esp_netif_set_dns_info(..., ESP_NETIF_DNS_MAIN, ...)`; a `#error` fires if `SKYPANE_STATIC_IP` is defined without all three of `SKYPANE_STATIC_NETMASK`/`_GW`/`_DNS`. Confirmed directly against the ESP-IDF v5.3.1 container's `esp_netif_handlers.c` source that `esp_netif_action_connected()` posts `IP_EVENT_STA_GOT_IP` itself once `WIFI_EVENT_STA_CONNECTED` fires when the DHCP client is stopped and a valid static IP is configured — `fp_wifi_connect()`'s existing `xEventGroupWaitBits(..., CONNECTED_BIT, ...)` wait needed no change, so no fallback bit-setting on `WIFI_EVENT_STA_CONNECTED` was added.
- **`secrets.example.h`**: documents `SKYPANE_STATIC_IP`/`_NETMASK`/`_GW`/`_DNS` as a commented-out block with example values, explaining it is off by default (DHCP restore-last-IP is the default join path) and should only be enabled if the hardware measurement shows DHCP is still too slow, with the address kept outside the router's DHCP pool.
- Verified against the real `espressif/idf:v5.3.1` container throughout: a from-scratch production build after each task (all three succeeded, 59% flash free each time); `check_production_config.sh static`/`built build-ee02` both `PASS` after the final task; `sh firmware/tests/run_host_tests.sh` 8/8 after every task (none of this plan's files have a host-test counterpart — `app_main.c`/`state_machine.c`/`wifi.c`/`fault_inject.c` all depend on ESP-IDF); a scratch build with the four static-IP macros appended to `secrets.h` compiled clean under `SKYPANE_PROFILE=dev` (macros removed and `secrets.h` restored to its pre-task content afterward, confirmed via `diff`, never committed); all four `SKYPANE_FAULT={panic,task_wdt,int_wdt,slow_wake}` dev builds compiled clean.

## Task Commits

1. **Task 1: Fault hooks and state-machine orchestration (checkpoints, step mapping, timings)** - `b875d19` (feat)
2. **Task 2: app_main — reset-reason gate, wake guard, battery first, pure sleep decision, diagnostic line** - `a6ef76e` (feat)
3. **Task 3: Optional static IP fallback (off by default)** - `3f26164` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/main/fault_inject.h`/`.c` - new: bench-only fault triggers, compiled to nothing when `CONFIG_SKYPANE_FAULT_INJECT_NONE`
- `firmware/main/state_machine.h` - `fp_poll_timing_t` added; `fp_poll_once()` signature gained `timing_out`; doc comment's step-token list updated
- `firmware/main/state_machine.c` - checkpoints, `step_for()`, per-stage timings, `nvs_util.h` for hash-skip read/write, `fp_fault_inject_point()` call site
- `firmware/main/app_main.c` - reset-reason gate, wake guard, battery-before-Wi-Fi, `fp_sleep_decide()`, diagnostic timing line, nine `_Static_assert`s
- `firmware/main/wifi.c` - optional `SKYPANE_STATIC_IP` fallback, off by default, `#error` on a partial config
- `firmware/main/secrets.example.h` - documents the four static-IP macros, commented out

## Decisions Made

See `key-decisions` in the frontmatter — repeated here for visibility:

- Per-stage timing fields are written live into the caller's `fp_poll_timing_t` as each stage completes, not accumulated locally and copied at `return`, because the wake-budget deadline callback is `noreturn` and would otherwise leave every field reading 0 on a deadline-triggered sleep.
- `app_main()` opens/closes its own NVS handle twice (boot counter, then backoff) rather than holding one handle across the whole function, since `fail_and_sleep()` — reachable from a bare function-pointer callback with no access to `app_main()`'s locals — has to open its own handle regardless; the second open degrades softly (backoff_n stays 0) rather than crashing, matching `nvs_util.c`'s project-wide convention.
- `esp_reset_reason()` is read once, early, and reused for both the wake-reason token and the diagnostic reset-reason line, reordering two of the plan's prose-listed statements relative to each other (while preserving every grep-checked ordering constraint) because `fp_wake_reason_token()` needs the reset reason as an input.
- The static-IP `IP_EVENT_STA_GOT_IP` question the plan asked the executor to confirm was resolved by reading the ESP-IDF v5.3.1 container's own `esp_netif_handlers.c` source rather than assuming — no extra event-bit fallback was needed.

## Deviations from Plan

None — plan executed exactly as written, including the one explicit "confirm and record the finding" instruction in Task 3 (the `esp_netif_action_connected()` source read, now recorded above and in `key-decisions`).

## Issues Encountered

None. Docker (`espressif/idf:v5.3.1`) was available throughout, so every build-gated verification in the plan's task and phase-level `<verification>` blocks ran for real:
- Three from-scratch production builds (one per task), all clean, `skypane.bin` produced each time, 59% flash free.
- `sh firmware/tests/check_production_config.sh static` and `built firmware/build-ee02` — both `PASS` after the final task.
- `sh firmware/tests/run_host_tests.sh` — 8/8 suites, unaffected by this plan's files (none has a host-test counterpart).
- All four `SKYPANE_PROFILE=dev SKYPANE_FAULT={panic,task_wdt,int_wdt,slow_wake}` builds compiled clean.
- Production `skypane.bin` contains 0 occurrences of `SKYPANE-FAULT-INJECT`; the `slow_wake` dev build's `skypane.bin` contains exactly 1.
- A scratch build with all four `SKYPANE_STATIC_*` macros appended to the local (gitignored) `secrets.h` compiled clean under `SKYPANE_PROFILE=dev`; the macros were removed and `secrets.h` restored to its exact pre-task content (`diff` confirmed) before committing — never appeared in any commit.
- All build directories (`firmware/build-ee02`, `firmware/build-ee02-dev`) removed after verification, matching `firmware/.gitignore`; `git status` confirmed clean before each commit.

## User Setup Required

None — no external service configuration required. `firmware/main/secrets.h` (gitignored) is present and unchanged from before this plan.

## Next Phase Readiness

- **What the 34-11 hardware session needs to observe (no hardware attached to this session, so none of the following is proven on real silicon yet):**
  1. `SKYPANE_FAULT=panic`/`task_wdt`/`int_wdt` on real hardware: confirm the next boot's `wake reason=other`, `reset reason=<label>` and `poll fail step=reset backoff_n=<n> sleep_s=<backoff>` lines actually appear, and that the device deep-sleeps for the backoff without ever joining Wi-Fi.
  2. `SKYPANE_FAULT=slow_wake`: confirm it ends at `CONFIG_SKYPANE_WAKE_BUDGET_S` (default 300 s) with `step=deadline`, not the 60 s task watchdog — this is the one fault mode designed to be caught by the *other* mechanism, so it is the sharpest test that the two are actually independent.
  3. Whether `CONFIG_ESP_TASK_WDT_TIMEOUT_S`'s countdown keeps advancing through `esp_light_sleep_start()` — flagged as an open question by plan 34-07's own SUMMARY, still unresolved (no hardware in either session).
  4. A real 401/403 on `/display` (server-side token revocation) → confirm `step=auth`, the token erased, and the next wake re-enrolling cleanly with the device's own secret (success criterion 2's full device-side path, now wired end to end by plans 34-06 and this one).
  5. The `wake timing total_ms=... wifi_ms=...` diagnostic line's actual numbers on real hardware, to validate the ~248.7 s worst-case sum `34-RESEARCH.md` derived from code-declared timeouts, and to give FW-10's per-cycle-overhead investigation a real per-stage breakdown instead of a single wall-clock total.
  6. `SKYPANE_STATIC_IP` wall-clock timing against the default DHCP path (`CONFIG_LWIP_DHCP_RESTORE_LAST_IP`), per D-34-03 — this plan only proves the static-IP code compiles and reasons from ESP-IDF source about event ordering; the actual join-time comparison is hardware-only.
- **What plan 34-09 (api_client keep-alive, TLS session persistence) needs:** it touches only `api_client.c`/`tls_session.*`/`main/CMakeLists.txt`, none of which this plan modified — `fp_wake_checkpoint()` is now armed by the time `api_client.c` runs (via `app_main.c`'s `fp_wake_guard_start()` and `state_machine.c`'s own checkpoints around each `api_client.c` call), so 34-09 can call `fp_wake_feed()`/`fp_wake_checkpoint()` from inside its own download loop if useful, exactly as plan 34-07's SUMMARY anticipated.
- **What plan 34-10 needs:** the Log Line Contract's new step tokens (`auth`, `enrol`, `secret`, `config`, now joined by `reset` and `deadline`, both emitted from `app_main.c`) are live in the firmware now but not yet documented in `firmware/VENDOR.md`'s Log Line Contract table — that documentation update, plus a description of the `fp_boot`/`fp_diag` diagnostic tags, is plan 34-10's job per the environment notes.
- No open blockers. `firmware/main/app_main.c`, `state_machine.c`/`.h`, `fault_inject.c`/`.h` and the touched slice of `wifi.c`/`secrets.example.h` are single-owner for this plan.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/main/fault_inject.h`
- FOUND: `firmware/main/fault_inject.c`
- FOUND: `firmware/main/app_main.c` (modified)
- FOUND: `firmware/main/state_machine.h` (modified)
- FOUND: `firmware/main/state_machine.c` (modified)
- FOUND: `firmware/main/wifi.c` (modified)
- FOUND: `firmware/main/secrets.example.h` (modified)
- FOUND commit `b875d19` (Task 1)
- FOUND commit `a6ef76e` (Task 2)
- FOUND commit `3f26164` (Task 3)
