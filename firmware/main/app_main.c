/* SPDX-License-Identifier: Apache-2.0 */
/*
 * SkyPane - Phase 1 wake dispatcher.
 *
 * On every wake: init NVS, let the panel guard account for elapsed
 * awake/sleep time, classify why we woke, run one poll attempt through
 * state_machine.c, then either reset the failure counter and sleep for
 * the server-supplied interval, or read the failure counter, compute
 * the exponential backoff interval, increment it, and sleep that
 * instead. Every branch below ends in deep sleep - there is no path out
 * of app_main that does not enter it, because a device that stays awake
 * on an unexpected path is a flat battery (01-SKELETON.md's Sleep
 * Invariant).
 *
 * The failure counter (FP_NVS_BACKOFF_N) is persisted in NVS, not RTC
 * memory: RTC memory survives deep sleep but not power loss or a
 * brownout, and a counter that resets on brownout is exactly the
 * counter that lets a device hot-loop until the battery is flat.
 *
 * Every log line below matches the frozen Log Line Contract
 * (firmware/VENDOR.md § Log Line Contract) that plans 01-06, 01-07 and
 * 01-08 grep captured serial output for. Their token spelling is a
 * contract, not a style choice.
 */
#include <inttypes.h>
#include <stdint.h>

#include "esp_log.h"
#include "esp_sleep.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "backoff.h"
#include "nvs_schema.h"
#include "panel.h"
#include "state_machine.h"
#include "wifi.h"

static const char *TAG = "skypane";

static const char *wake_reason_string(esp_sleep_wakeup_cause_t cause)
{
    switch (cause) {
    case ESP_SLEEP_WAKEUP_TIMER:
        return "rtc";
    case ESP_SLEEP_WAKEUP_UNDEFINED:
        return "power-on";
    case ESP_SLEEP_WAKEUP_EXT0:
    case ESP_SLEEP_WAKEUP_EXT1:
    case ESP_SLEEP_WAKEUP_GPIO:
        /* No button is wired up in Phase 1 (that's Phase 4, DEVICE-01);
         * this case exists so the log contract's "button" token is
         * exercised by the switch statement from day one. */
        return "button";
    default:
        return "other";
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
    esp_deep_sleep_start();
}

void app_main(void)
{
    /* Never recover NVS by erasing the whole partition on an ordinary
     * error - only on the two specific "the partition itself is
     * unusable" codes below. */
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
        err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    fp_panel_on_boot();

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    const char *reason = wake_reason_string(cause);

    nvs_handle_t nvs;
    ESP_ERROR_CHECK(nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs));
    uint32_t boot_count = nvs_increment_boot_count(nvs);
    nvs_commit(nvs);

    ESP_LOGI(TAG, "wake reason=%s boot_count=%" PRIu32, reason, boot_count);

    uint32_t sleep_s = 0;
    const char *fail_step = "wifi";
    fp_poll_result_t result = fp_poll_once(reason, &sleep_s, &fail_step);

    if (result == FP_POLL_FAILED) {
        uint8_t backoff_n = 0;
        nvs_get_u8(nvs, FP_NVS_BACKOFF_N, &backoff_n);
        uint32_t backoff_s = fp_backoff_seconds(backoff_n);
        if (backoff_n < UINT8_MAX) {
            nvs_set_u8(nvs, FP_NVS_BACKOFF_N, backoff_n + 1);
        }
        nvs_commit(nvs);
        nvs_close(nvs);
        ESP_LOGW(TAG, "poll fail step=%s backoff_n=%u sleep_s=%" PRIu32,
                 fail_step, backoff_n, backoff_s);
        enter_deep_sleep(backoff_s);
    }

    /* FP_POLL_OK_REFRESHED, FP_POLL_OK_UNCHANGED or FP_POLL_OK_DEFERRED:
     * all three are healthy wakes (PROTOCOL.md §3's "deferred != failed"
     * rule) - reset the failure counter for all of them. */
    nvs_set_u8(nvs, FP_NVS_BACKOFF_N, 0);
    nvs_commit(nvs);

    if (result == FP_POLL_OK_DEFERRED) {
        /* The image is already fetched but the panel guard's spacing
         * has not elapsed. Sleep only until the panel may draw, not
         * until the next edition - otherwise a healthy frame would
         * appear to do nothing for hours. */
        uint32_t wait_s = fp_panel_wait_seconds();
        if (wait_s != 0 && wait_s < sleep_s) {
            sleep_s = wait_s + 5;
        }
    }
    nvs_close(nvs);

    uint8_t hash_skip = result == FP_POLL_OK_UNCHANGED ? 1 : 0;
    ESP_LOGI(TAG, "poll ok sleep_s=%" PRIu32 " hash_skip=%u",
             sleep_s, hash_skip);
    enter_deep_sleep(sleep_s);
}
