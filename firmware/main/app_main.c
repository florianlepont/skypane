/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
/*
 * SkyPane wake dispatcher. On every wake: turn on the bring-up LED, arm
 * the wake budget timer and watchdog, let the panel guard account for
 * elapsed time, init NVS (an unusable NVS sleeps a fixed interval
 * instead, nvs_boot.h), increment the boot counter, and classify why
 * the chip last reset — an abnormal reset backs off without starting
 * the radio. A healthy wake reads the battery before Wi-Fi (its draw
 * sags the pack and couples noise into the ADC), runs one poll attempt
 * through state_machine.c, and lets fp_sleep_decide() turn the result
 * into a sleep plan. Every branch ends in deep sleep — a device that
 * stays awake on an unexpected path is a flat battery. The failure
 * counter (FP_NVS_BACKOFF_N) lives in NVS, not RTC memory, since RTC
 * survives deep sleep but not a brownout. Every `skypane`-tagged log
 * line is the frozen Log Line Contract (firmware/VENDOR.md); the
 * `fp_boot`/`fp_diag`-tagged lines are diagnostics outside it.
 */
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "api_client.h"
#include "battery.h"
#include "epd13in3e.h"
#include "fault_inject.h"
#include "fault_screen.h"
#include "led.h"
#include "nvs_boot.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "panel.h"
#include "reset_reason.h"
#include "sleep_decision.h"
#include "state_machine.h"
#include "wake_guard.h"
#include "wifi.h"

/* fp_fault_screen_render()'s buffer contract must match the panel's own
 * byte count exactly - if either side's dimensions ever drift, this
 * catches it at compile time rather than as a corrupted blit on real
 * glass. */
_Static_assert(FP_FAULT_SCREEN_BYTES == EPD_BYTES, "fault screen buffer size must match EPD_BYTES");

/* reset_reason.h's FP_RST_* enum mirrors esp_reset_reason_t
 * (ESP-IDF v5.3.1, components/esp_system/include/esp_system.h)
 * value-for-value so that header needs no ESP-IDF include; this asserts
 * the equality actually holds at compile time, so a future ESP-IDF enum
 * reorder fails the build instead of silently misclassifying resets. */
_Static_assert((int)ESP_RST_POWERON == FP_RST_POWERON, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_PANIC == FP_RST_PANIC, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_INT_WDT == FP_RST_INT_WDT, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_TASK_WDT == FP_RST_TASK_WDT, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_WDT == FP_RST_WDT, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_DEEPSLEEP == FP_RST_DEEPSLEEP, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_BROWNOUT == FP_RST_BROWNOUT, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_PWR_GLITCH == FP_RST_PWR_GLITCH, "reset_reason.h enum drift");
_Static_assert((int)ESP_RST_CPU_LOCKUP == FP_RST_CPU_LOCKUP, "reset_reason.h enum drift");

/* nvs_boot.h mirrors these ESP-IDF error codes for the same reason. */
_Static_assert(ESP_OK == FP_NVS_ERR_OK, "nvs_boot.h error code drift");
_Static_assert(ESP_ERR_NVS_NO_FREE_PAGES == FP_NVS_ERR_NO_FREE_PAGES, "nvs_boot.h error code drift");
_Static_assert(ESP_ERR_NVS_NEW_VERSION_FOUND == FP_NVS_ERR_NEW_VERSION_FOUND, "nvs_boot.h error code drift");

static const char *TAG = "skypane";

/* Per-stage poll timings for the diagnostic wake-duration line.
 * File-scope so fail_and_sleep() (reachable both from fp_poll_once()'s
 * own failure returns and, via on_wake_deadline(), from a budget expiry
 * mid-poll) can log whatever stages actually completed. Zero-initialised
 * by static storage duration - each wake is a fresh boot, so there is no
 * stale value from a previous wake to worry about. */
static fp_poll_timing_t s_timing;

static fp_wake_cause_t wake_cause_of(esp_sleep_wakeup_cause_t cause)
{
    switch (cause) {
    case ESP_SLEEP_WAKEUP_TIMER:
        return FP_WAKE_CAUSE_TIMER;
    case ESP_SLEEP_WAKEUP_EXT0:
    case ESP_SLEEP_WAKEUP_EXT1:
    case ESP_SLEEP_WAKEUP_GPIO:
        /* No button is wired up yet; this case exists so the log
         * contract's "button" token is exercised by the switch
         * statement from day one. */
        return FP_WAKE_CAUSE_BUTTON;
    case ESP_SLEEP_WAKEUP_UNDEFINED:
        return FP_WAKE_CAUSE_NONE;
    default:
        return FP_WAKE_CAUSE_OTHER;
    }
}

/* Reads and increments the boot counter in the already-open NVS handle.
 * Returns 0 on any NVS error rather than aborting boot, since a boot
 * counter is diagnostic, not safety-critical. */
static uint32_t nvs_increment_boot_count(nvs_handle_t nvs)
{
    uint32_t boot_count = 0;
    esp_err_t err = nvs_get_u32(nvs, FP_NVS_BOOT_COUNT, &boot_count);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGE(TAG, "nvs_get_u32 failed: %s", esp_err_to_name(err));
    }
    boot_count++;
    err = nvs_set_u32(nvs, FP_NVS_BOOT_COUNT, boot_count);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_set_u32 failed: %s", esp_err_to_name(err));
    }
    return boot_count;
}

/* The single exit from app_main. Radio off before sleep always (even on
 * a path where state_machine.c already stopped it - fp_wifi_stop() is
 * idempotent), then arm the timer and go. */
static void __attribute__((noreturn)) enter_deep_sleep(uint32_t seconds)
{
    fp_wifi_stop();
    fp_panel_before_sleep(seconds);
    esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
    ESP_LOGI(TAG, "sleep enter sleep_s=%" PRIu32, seconds);
    /* This function is the single, noreturn exit from app_main() - every
     * branch (abnormal reset, deadline expiry, poll failure, deferred
     * draw, healthy refresh) funnels through it, so one call here is
     * what covers every path there is. An LED left energised past this
     * point would draw single-digit-to-tens of mA against a
     * tens-of-µA sleep budget. It is deliberately not conditioned on
     * any server-supplied preference, because a value that arrives over
     * the network must never be able to hold a pin high through deep
     * sleep. */
    fp_led_off();
    esp_deep_sleep_start();
}

/* Diagnostic wake-duration line, tag fp_diag, outside the Log Line
 * Contract. total_ms is the whole wake so far
 * (fp_wake_elapsed_ms()); the per-stage fields are whatever
 * s_timing holds - 0 for a stage this wake never reached. */
static void log_wake_timing(void)
{
    ESP_LOGI("fp_diag",
             "wake timing total_ms=%" PRIu32 " wifi_ms=%" PRIu32
             " setup_ms=%" PRIu32 " display_ms=%" PRIu32
             " download_ms=%" PRIu32 " draw_ms=%" PRIu32,
             fp_wake_elapsed_ms(), s_timing.wifi_ms, s_timing.setup_ms,
             s_timing.display_ms, s_timing.download_ms, s_timing.draw_ms);
}

/* Draws the firmware-local NO CONNECTION hold screen on the 2nd+
 * consecutive failure of an allow-listed comm/data step — see
 * fault_screen.h for the rationale and
 * fp_fault_screen_should_draw()'s exact gate. No new NVS key is needed
 * for the once-per-outage sentinel: comparing FP_NVS_IMAGE_HASH against
 * FP_FAULT_SCREEN_HASH before drawing suppresses a redraw on every
 * later failing wake of the outage, and since that sentinel is never
 * shaped like a real server hash, the first healthy poll after
 * recovery always redraws the real picture rather than skipping it.
 * Never calls fp_wake_checkpoint() here: that could re-enter
 * fail_and_sleep() via on_wake_deadline(), and this helper is only
 * ever reached FROM fail_and_sleep(). */
static void maybe_draw_fault_screen(const char *step, uint8_t next_backoff_n)
{
    char last_hash[80] = "";
    bool already_shown =
        fp_nvs_get_str(FP_NVS_IMAGE_HASH, last_hash, sizeof(last_hash)) == ESP_OK &&
        strcmp(last_hash, FP_FAULT_SCREEN_HASH) == 0;

    if (!fp_fault_screen_should_draw(step, next_backoff_n, already_shown)) {
        return;
    }

    /* Radio down before the panel, same rule as state_machine.c's
     * healthy-poll path. fp_api_release() is safe/idempotent with no
     * open session (api_client.c: it only acts if its static handle is
     * non-NULL). */
    fp_api_release();
    fp_wifi_stop();

    uint8_t *buf = heap_caps_malloc(FP_FAULT_SCREEN_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGW("fp_diag", "fault screen skipped: no PSRAM");
        return;
    }

    fp_fault_screen_render(buf, fp_wake_feed);
    esp_err_t err = fp_panel_draw(buf);
    heap_caps_free(buf);

    if (err == ESP_OK) {
        fp_nvs_set_str(FP_NVS_IMAGE_HASH, FP_FAULT_SCREEN_HASH);
        ESP_LOGI("fp_diag", "fault screen drawn step=%s backoff_n=%u", step, next_backoff_n);
    } else if (err == ESP_ERR_TIMEOUT || err == ESP_ERR_INVALID_STATE) {
        /* Deferred by the panel guard, not a failure (PROTOCOL.md §3) -
         * do NOT write the sentinel, so the next failing wake retries. */
        ESP_LOGI("fp_diag", "fault screen deferred err=%s", esp_err_to_name(err));
    } else {
        ESP_LOGW("fp_diag", "fault screen failed err=%s", esp_err_to_name(err));
    }
}

/* The single failure exit: decides the backoff sleep plan (persisting
 * FP_NVS_BACKOFF_N via its own NVS handle - callable from
 * on_wake_deadline(), a bare function pointer with no access to
 * app_main()'s locals), logs the `poll fail` and diagnostic lines, and
 * sleeps. An NVS open failure still sleeps, using backoff_n 0 - a
 * missing NVS handle must never keep the radio on. */
static void __attribute__((noreturn)) fail_and_sleep(const char *step)
{
    nvs_handle_t nvs;
    uint8_t backoff_n = 0;
    esp_err_t err = nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        nvs_get_u8(nvs, FP_NVS_BACKOFF_N, &backoff_n);
    }
    fp_sleep_plan_t plan =
        fp_sleep_decide(FP_WAKE_OUTCOME_FAILED, backoff_n, 0, 0);
    if (err == ESP_OK) {
        nvs_set_u8(nvs, FP_NVS_BACKOFF_N, plan.next_backoff_n);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
    ESP_LOGW(TAG, "poll fail step=%s backoff_n=%u sleep_s=%" PRIu32, step,
             backoff_n, plan.sleep_s);
    log_wake_timing();
    maybe_draw_fault_screen(step, plan.next_backoff_n);
    enter_deep_sleep(plan.sleep_s);
}

/* The failure exit for an unusable NVS at boot. Unlike fail_and_sleep()
 * it has no counter to read or persist and draws no fault screen
 * (fault_screen.h), so it sleeps the fixed fp_nvs_fail_sleep_s() and
 * logs backoff_n=0. The radio has not started on this path. */
static void __attribute__((noreturn)) nvs_fail_and_sleep(const char *step, esp_err_t err)
{
    uint32_t sleep_s = fp_nvs_fail_sleep_s();
    ESP_LOGE("fp_boot", "nvs unusable err=%s", esp_err_to_name(err));
    ESP_LOGW(TAG, "poll fail step=%s backoff_n=%u sleep_s=%" PRIu32, step,
             0u, sleep_s);
    log_wake_timing();
    enter_deep_sleep(sleep_s);
}

/* Registered with fp_wake_guard_start(): called when the whole-wake
 * budget expires. Must not return (wake_guard.h's fp_wake_expired_fn
 * contract) - fail_and_sleep() never does. */
static void __attribute__((noreturn)) on_wake_deadline(void)
{
    fail_and_sleep("deadline");
}

void app_main(void)
{
    /* First statement of the wake cycle, above NVS init: the recovery
     * branch below can erase a whole partition and take seconds, and a
     * signal that only appears after that has already lost the race it
     * exists to win. This is the fastest point at which the developer
     * can learn the flash took. */
    fp_led_on();

    /* Arms the whole-wake budget timer and subscribes this task to the
     * task watchdog before anything that could plausibly hang - NVS
     * recovery included. */
    fp_wake_guard_start(on_wake_deadline);

    /* RTC memory only, no NVS: done first so the panel guard's timing
     * holds on the NVS failure path below too. */
    fp_panel_on_boot();

    /* Never recover NVS by erasing the whole partition on an ordinary
     * error, and never abort on a failure: an abort reboots at once and
     * would hot-loop on a partition that keeps failing (nvs_boot.h). */
    esp_err_t err = nvs_flash_init();
    if (fp_fault_inject_nvs()) {
        err = ESP_FAIL;
    }
    fp_nvs_boot_action_t nvs_action = fp_nvs_init_action((int)err, false);
    if (nvs_action == FP_NVS_BOOT_ERASE_AND_RETRY) {
        err = nvs_flash_erase();
        if (err == ESP_OK) {
            err = nvs_flash_init();
        }
        nvs_action = fp_nvs_init_action((int)err, true);
    }
    if (nvs_action != FP_NVS_BOOT_READY) {
        nvs_fail_and_sleep("nvs", err);
    }

    nvs_handle_t nvs;
    err = nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        nvs_fail_and_sleep("nvs", err);
    }
    uint32_t boot_count = nvs_increment_boot_count(nvs);
    nvs_commit(nvs);
    nvs_close(nvs);

    esp_sleep_wakeup_cause_t wake_cause = esp_sleep_get_wakeup_cause();
    esp_reset_reason_t rr = esp_reset_reason();
    const char *reason = fp_wake_reason_token(wake_cause_of(wake_cause), (int)rr);
    ESP_LOGI(TAG, "wake reason=%s boot_count=%" PRIu32, reason, boot_count);

    ESP_LOGI("fp_boot", "reset reason=%s", fp_reset_label((int)rr));
    if (fp_reset_is_abnormal((int)rr)) {
        /* The previous wake never reached deep sleep on its own - do
         * not start the radio again until backoff has elapsed. */
        fail_and_sleep("reset");
    }

    /* Before Wi-Fi: the radio's own current draw sags the pack and
     * couples noise into the ADC (battery.h). */
    fp_battery_mv();

    fp_wake_checkpoint();

    uint32_t sleep_s = 0;
    const char *fail_step = "wifi";
    fp_poll_result_t result =
        fp_poll_once(reason, &sleep_s, &fail_step, &s_timing);

    if (result == FP_POLL_FAILED) {
        fail_and_sleep(fail_step);
    }

    /* FP_POLL_OK_REFRESHED, FP_POLL_OK_UNCHANGED or FP_POLL_OK_DEFERRED:
     * all three are healthy wakes (PROTOCOL.md §3's "deferred != failed"
     * rule) - fp_sleep_decide() resets the failure counter for all of
     * them. */
    fp_wake_outcome_t outcome = result == FP_POLL_OK_DEFERRED
        ? FP_WAKE_OUTCOME_DEFERRED
        : FP_WAKE_OUTCOME_OK;
    /* The image is already fetched but, for a deferred draw, the panel
     * guard's spacing has not elapsed - fp_sleep_decide() sleeps only
     * until the panel may draw, not until the next edition, so a
     * healthy frame does not appear to do nothing for hours. */
    uint32_t panel_wait_s =
        result == FP_POLL_OK_DEFERRED ? fp_panel_wait_seconds() : 0;

    uint8_t backoff_n = 0;
    esp_err_t nerr = nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (nerr == ESP_OK) {
        nvs_get_u8(nvs, FP_NVS_BACKOFF_N, &backoff_n);
    }
    fp_sleep_plan_t plan =
        fp_sleep_decide(outcome, backoff_n, sleep_s, panel_wait_s);

    if (plan.failed) {
        /* Cannot happen after validate.c's fp_sleep_s_parse rejects a
         * sleep_s above its range, but fp_sleep_decide() guards a
         * zero server sleep_s under every outcome too - if that ever
         * changes, this is what actually holds, not a comment. */
        if (nerr == ESP_OK) {
            nvs_close(nvs);
        }
        fail_and_sleep("json");
    }

    if (nerr == ESP_OK) {
        nvs_set_u8(nvs, FP_NVS_BACKOFF_N, plan.next_backoff_n);
        nvs_commit(nvs);
        nvs_close(nvs);
    }

    uint8_t hash_skip = result == FP_POLL_OK_UNCHANGED ? 1 : 0;
    ESP_LOGI(TAG, "poll ok sleep_s=%" PRIu32 " hash_skip=%u",
             plan.sleep_s, hash_skip);
    log_wake_timing();
    enter_deep_sleep(plan.sleep_s);
}
