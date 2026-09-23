/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "wake_guard.h"

#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#include "wake_deadline.h"

static const char *TAG = "fp_wake";

static int64_t s_start_us;
static volatile bool s_expired;
static bool s_task_subscribed;
static bool s_warned_once;
static esp_timer_handle_t s_timer;
static fp_wake_expired_fn s_on_expired;

/* The wake budget must exceed the worst-case legitimate wake at the
 * configured guard wait, or a healthy device would trip its own
 * deadline - see wake_deadline.h's FP_WAKE_WORST_CASE_S. */
_Static_assert(CONFIG_SKYPANE_WAKE_BUDGET_S > FP_WAKE_WORST_CASE_S(CONFIG_FP_MAX_GUARD_WAIT_S),
               "wake budget must exceed the worst legitimate wake");

/* Whether the task watchdog timer keeps counting through light sleep is
 * not guaranteed by ESP-IDF, so no single light-sleep slice may
 * approach the watchdog's timeout. */
_Static_assert(CONFIG_ESP_TASK_WDT_TIMEOUT_S > FP_WAKE_LIGHT_SLEEP_SLICE_S,
               "light-sleep slice must stay well under the task watchdog timeout");

/* esp_timer dispatch-task context (not the main task's): the only safe
 * thing to do here is set a flag and return. Every side effect (the
 * warning log, the failure record, the actual sleep) happens later, in
 * fp_wake_checkpoint(), called from the main task at a point it has
 * chosen to be safe. */
static void wake_budget_timer_cb(void *arg)
{
    (void)arg;
    s_expired = true;
}

void fp_wake_guard_start(fp_wake_expired_fn on_expired)
{
    s_start_us = esp_timer_get_time();
    s_on_expired = on_expired;
    s_expired = false;
    s_warned_once = false;

    const esp_timer_create_args_t args = {
        .callback = wake_budget_timer_cb,
        .name = "wake_budget",
    };
    esp_err_t err = esp_timer_create(&args, &s_timer);
    if (err == ESP_OK) {
        err = esp_timer_start_once(
            s_timer, (uint64_t)CONFIG_SKYPANE_WAKE_BUDGET_S * 1000000ULL);
    }
    if (err != ESP_OK) {
        /* Degrades: fp_wake_checkpoint() still compares elapsed time
         * against the budget directly via fp_wake_deadline_expired(),
         * so the budget itself holds even without the timer armed. */
        ESP_LOGE(TAG, "wake budget timer failed to arm: %s",
                 esp_err_to_name(err));
    }

    err = esp_task_wdt_add(NULL);
    s_task_subscribed = (err == ESP_OK);
    if (!s_task_subscribed) {
        ESP_LOGE(TAG, "task watchdog subscription failed: %s",
                 esp_err_to_name(err));
    }
}

void fp_wake_feed(void)
{
    /* Only reset when this call actually subscribed the task: ESP-IDF
     * logs an error for every esp_task_wdt_reset() from an unsubscribed
     * task, and this is called from the panel driver before the guard
     * exists in unit bring-up or early boot. */
    if (s_task_subscribed) {
        esp_task_wdt_reset();
    }
}

bool fp_wake_expired(void)
{
    return s_expired ||
           fp_wake_deadline_expired((uint64_t)esp_timer_get_time(),
                                     (uint64_t)s_start_us,
                                     CONFIG_SKYPANE_WAKE_BUDGET_S);
}

void fp_wake_checkpoint(void)
{
    fp_wake_feed();
    if (!fp_wake_expired()) {
        return;
    }
    if (!s_warned_once) {
        ESP_LOGW(TAG, "wake budget of %us exceeded",
                 (unsigned)CONFIG_SKYPANE_WAKE_BUDGET_S);
        s_warned_once = true;
    }
    if (s_on_expired) {
        s_on_expired();
    }
}

uint32_t fp_wake_elapsed_ms(void)
{
    int64_t now = esp_timer_get_time();
    if (now < s_start_us) {
        return 0;
    }
    return (uint32_t)((now - s_start_us) / 1000);
}

void fp_wake_light_sleep_s(uint32_t seconds)
{
    uint32_t remaining = seconds;
    bool warned_fallback = false;

    while (remaining > 0) {
        uint32_t slice = fp_wake_slice_s(remaining, FP_WAKE_LIGHT_SLEEP_SLICE_S);

        esp_err_t err =
            esp_sleep_enable_timer_wakeup((uint64_t)slice * 1000000ULL);
        if (err == ESP_OK) {
            err = esp_light_sleep_start();
        }
        if (err != ESP_OK) {
            if (!warned_fallback) {
                ESP_LOGW(TAG, "light sleep failed (%s), falling back to "
                              "vTaskDelay for this slice",
                         esp_err_to_name(err));
                warned_fallback = true;
            }
            vTaskDelay(pdMS_TO_TICKS(slice * 1000U));
        }

        /* Idle tasks also reset their own watchdog entries when they
         * get to run - vTaskDelay(1) gives them that chance alongside
         * the explicit feed. */
        fp_wake_feed();
        vTaskDelay(1);

        remaining -= slice;
    }

    /* Re-disable the timer wakeup source so the deep-sleep path
     * (app_main.c's enter_deep_sleep()) re-arms it cleanly rather than
     * inheriting a stale slice-sized timer. */
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_TIMER);
}
