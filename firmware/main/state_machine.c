/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#include "state_machine.h"

#include <string.h>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "api_client.h"
#include "fault_inject.h"
#include "led.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "panel.h"
#include "wake_guard.h"
#include "wifi.h"

static const char *TAG = "skypane";

/* Shared failure -> Log Line Contract step-token mapping for both
 * fp_api_setup() and fp_api_get_display(): each FP_ERR_* value maps to
 * exactly one token regardless of which call produced it, so the table
 * exists once (FW-14). A value neither call can actually return (e.g.
 * FP_ERR_HTTP_AUTH from fp_api_setup(), which only ever returns
 * FP_ERR_ENROL_REJECTED for a 401/403) simply never reaches this
 * function from that call site. */
static const char *step_for(esp_err_t err)
{
    switch (err) {
    case FP_ERR_NO_SECRET:
        return "secret";
    case FP_ERR_ENROL_REJECTED:
        return "enrol";
    case FP_ERR_CONFIG:
        return "config";
    case FP_ERR_HTTP_AUTH:
        return "auth";
    case FP_ERR_HTTP_STATUS:
        return "status";
    case FP_ERR_HTTP_JSON:
        return "json";
    default:
        return "http";
    }
}

static uint32_t elapsed_ms_since(int64_t start_us)
{
    return (uint32_t)((esp_timer_get_time() - start_us) / 1000);
}

fp_poll_result_t fp_poll_once(const char *boot_reason, uint32_t *sleep_s_out,
                              const char **fail_step_out,
                              fp_poll_timing_t *timing_out)
{
    if (!boot_reason || !sleep_s_out || !fail_step_out) {
        return FP_POLL_FAILED;
    }

    int64_t t_wifi = esp_timer_get_time();
    esp_err_t wifi_err = fp_wifi_connect(15000);
    if (timing_out) {
        timing_out->wifi_ms = elapsed_ms_since(t_wifi);
    }
    if (wifi_err != ESP_OK) {
        *fail_step_out = "wifi";
        return FP_POLL_FAILED;
    }
    fp_wake_checkpoint();
    fp_fault_inject_point();

    if (!fp_api_has_token()) {
        /* First wake ever (or the first wake after a 401/403 erased the
         * token): enrol before any /display poll can carry a bearer
         * token. The enrolment secret is this device's own, read from
         * its dedicated NVS partition by fp_api_setup() itself
         * (enrol_secret.h) — never a value this file supplies. */
        int64_t t_setup = esp_timer_get_time();
        esp_err_t setup_err = fp_api_setup();
        if (timing_out) {
            timing_out->setup_ms = elapsed_ms_since(t_setup);
        }
        if (setup_err != ESP_OK) {
            *fail_step_out = step_for(setup_err);
            return FP_POLL_FAILED;
        }
        fp_wake_checkpoint();
    }

    fp_display_t disp;
    int64_t t_display = esp_timer_get_time();
    esp_err_t err = fp_api_get_display(boot_reason, &disp);
    if (timing_out) {
        timing_out->display_ms = elapsed_ms_since(t_display);
    }
    if (err != ESP_OK) {
        *fail_step_out = step_for(err);
        return FP_POLL_FAILED;
    }
    *sleep_s_out = disp.sleep_s;
    fp_wake_checkpoint();

    /* DEVICE-05 bring-up LED toggle: this is the first instruction at
     * which a server answer exists, and it precedes every downstream
     * exit (the unchanged-hash early return, the download, the blit,
     * the deferred-draw return and every failure return below) - so
     * placing it here is what makes all of those inherit the decision
     * from one branch. Doing this after the blit instead would leave
     * the LED lit through the longest part of the wake, which is
     * exactly the part a server wanting to suppress it would want
     * suppressed. This call can only ever extinguish the LED earlier
     * than the unconditional pre-sleep call in app_main.c would - it is
     * not, and must not become, a substitute for that call. */
    if (!disp.led_enabled) {
        fp_led_off();
    }

    /* Hash-skip: if the returned image_hash equals the NVS copy, do not
     * download at all — PROTOCOL.md §2. */
    char last_hash[80] = "";
    fp_nvs_get_str(FP_NVS_IMAGE_HASH, last_hash, sizeof(last_hash));
    if (strcmp(last_hash, disp.image_hash) == 0) {
        ESP_LOGI(TAG, "image unchanged, skipping download");
        fp_api_release();
        return FP_POLL_OK_UNCHANGED;
    }

    uint8_t *buf = heap_caps_malloc(FP_IMAGE_BYTES,
                                    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGE(TAG, "no PSRAM for framebuffer");
        *fail_step_out = "download";
        return FP_POLL_FAILED;
    }
    int64_t t_download = esp_timer_get_time();
    err = fp_api_download(disp.image_url, disp.image_hash, buf);
    if (timing_out) {
        timing_out->download_ms = elapsed_ms_since(t_download);
    }
    if (err != ESP_OK) {
        heap_caps_free(buf);
        *fail_step_out = err == FP_ERR_IMAGE_VERIFY ? "verify" : "download";
        return FP_POLL_FAILED;
    }

    /* Radio down before the panel: the blit (and any wait the panel's
     * refresh spacing imposes) is the longest part of the wake, and
     * holding an association through it buys nothing. This is also the
     * last point at which ending the wake is safe — the panel is not
     * powered yet, so a checkpoint here (unlike anywhere between
     * epd_init() and epd_sleep()) can tear down cleanly through
     * app_main.c's single exit if the budget has expired. */
    fp_api_release();
    fp_wifi_stop();
    fp_wake_checkpoint();

    int64_t t_draw = esp_timer_get_time();
    err = fp_panel_draw(buf);
    if (timing_out) {
        timing_out->draw_ms = elapsed_ms_since(t_draw);
    }
    heap_caps_free(buf);

    /* The panel guard refused on spacing grounds, not because anything
     * is wrong: ESP_ERR_INVALID_STATE means a blit is already running,
     * ESP_ERR_TIMEOUT means the spacing outlasts this wake's awake
     * budget. Neither is a failure (PROTOCOL.md §3, panel_guard.h) — the
     * failure counter stays untouched and the hash is deliberately left
     * unrecorded below, so the next wake fetches this same picture and
     * draws it instead of a healthy panel being punished with backoff. */
    if (err == ESP_ERR_INVALID_STATE || err == ESP_ERR_TIMEOUT) {
        ESP_LOGI(TAG, "draw deferred by the panel guard");
        return FP_POLL_OK_DEFERRED;
    }
    if (err != ESP_OK) {
        *fail_step_out = "blit";
        return FP_POLL_FAILED;
    }

    ESP_LOGI(TAG, "blit ok bytes=960000 sha256_ok=1");

    /* Persist the new hash only after a successful blit — a blit that
     * never happened cannot cause the next wake to skip. */
    fp_nvs_set_str(FP_NVS_IMAGE_HASH, disp.image_hash);
    ESP_LOGI(TAG, "refreshed to %.23s...", disp.image_hash);
    return FP_POLL_OK_REFRESHED;
}
