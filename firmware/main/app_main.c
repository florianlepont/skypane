/* SPDX-License-Identifier: Apache-2.0 */
/*
 * Ink Frame - minimal boot-and-sleep skeleton.
 *
 * This is deliberately the smallest possible app_main: it proves the
 * toolchain, the linker, the partition table, NVS persistence and the
 * deep-sleep API all work together, before any hardware exists. Plan
 * 01-05 replaces this body with the real wake -> poll -> display ->
 * deep-sleep loop; this file's only job is to make a binary exist and
 * to start proving the "no path out of app_main that does not enter
 * deep sleep" invariant (01-SKELETON.md) from day one.
 *
 * The two log lines below already match the frozen Log Line Contract
 * (01-SKELETON.md "Log Line Contract") that the hardware bring-up
 * plans will later grep captured serial output for. Plan 01-05 emits
 * the remaining three line shapes (poll ok / poll fail / blit ok);
 * this task only ever reaches "wake" and "sleep enter".
 */
#include <inttypes.h>
#include <stdint.h>

#include "esp_log.h"
#include "esp_sleep.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "inkframe";

#define INK_NVS_NAMESPACE "inkframe"
#define INK_NVS_KEY_BOOT_COUNT "boot_count"
#define INK_WAKE_TIMER_S 60

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

/* Reads and increments the boot counter in NVS (not RTC memory, which
 * does not survive power loss - see 01-SKELETON.md's Durable State
 * decision). Returns 0 on any NVS error rather than aborting boot,
 * since a boot counter is diagnostic, not safety-critical. */
static uint32_t nvs_increment_boot_count(void)
{
    nvs_handle_t handle;
    uint32_t boot_count = 0;

    esp_err_t err = nvs_open(INK_NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_open failed: %s", esp_err_to_name(err));
        return 0;
    }

    /* ESP_ERR_NVS_NOT_FOUND on first boot is expected, not an error. */
    err = nvs_get_u32(handle, INK_NVS_KEY_BOOT_COUNT, &boot_count);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGE(TAG, "nvs_get_u32 failed: %s", esp_err_to_name(err));
    }

    boot_count++;

    err = nvs_set_u32(handle, INK_NVS_KEY_BOOT_COUNT, boot_count);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_set_u32 failed: %s", esp_err_to_name(err));
    }

    err = nvs_commit(handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_commit failed: %s", esp_err_to_name(err));
    }

    nvs_close(handle);
    return boot_count;
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    uint32_t boot_count = nvs_increment_boot_count();

    ESP_LOGI(TAG, "wake reason=%s boot_count=%" PRIu32,
             wake_reason_string(cause), boot_count);

    /* Plan 01-05 replaces everything below this line with the real
     * poll -> hash-skip -> download -> verify -> blit sequence and its
     * own backoff / server-supplied sleep interval. A fixed 60 s wake
     * here only proves the deep-sleep timer API works end to end. */
    esp_sleep_enable_timer_wakeup((uint64_t)INK_WAKE_TIMER_S * 1000000ULL);

    ESP_LOGI(TAG, "sleep enter sleep_s=%d", INK_WAKE_TIMER_S);
    esp_deep_sleep_start();
}
