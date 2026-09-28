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
#include "esp_system.h"
#include "esp_timer.h"
#include "sdkconfig.h"

#include "api_client.h"
#include "battery.h"
#include "fault_inject.h"
#include "led.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "ota.h"
#include "ota_policy.h"
#include "panel.h"
#include "updating_screen.h"
#include "wake_guard.h"
#include "wifi.h"

static const char *TAG = "skypane";

/* Shared failure -> Log Line Contract step-token mapping for both
 * fp_api_setup() and fp_api_get_display(): each FP_ERR_* value maps to
 * exactly one token regardless of which call produced it, so the table
 * exists once. A value neither call can actually return (e.g.
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

/* Draws the on-device UPDATING hold screen for an OTA attempt that is
 * about to start, modelled on app_main.c's maybe_draw_fault_screen():
 * radio down before the panel (fp_api_release() is safe/idempotent with
 * no open session), a PSRAM framebuffer, the shared hold-screen
 * renderer, and the blit itself, which may legitimately wait out the
 * panel guard's spacing - accepted here exactly as it is on the healthy
 * poll path below. The image-hash sentinel is written whatever the draw
 * result (drawn, deferred, or skipped for no PSRAM): this screen is
 * shown regardless of quiet hours or display-off, and writing a
 * sentinel that can never match a real server hash guarantees the next
 * successful poll always redraws the current mode's picture rather than
 * treating this screen as already on glass. */
static void draw_updating_screen(void)
{
    fp_api_release();
    fp_wifi_stop();

    uint8_t *buf = heap_caps_malloc(FP_UPDATING_SCREEN_BYTES,
                                    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGW(TAG, "ota updating screen skipped: no PSRAM");
    } else {
        fp_updating_screen_render(buf, fp_wake_feed);
        esp_err_t err = fp_panel_draw(buf);
        heap_caps_free(buf);
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "ota updating screen drawn");
        } else if (err == ESP_ERR_TIMEOUT || err == ESP_ERR_INVALID_STATE) {
            ESP_LOGI(TAG, "ota updating screen deferred err=%s", esp_err_to_name(err));
        } else {
            ESP_LOGW(TAG, "ota updating screen failed err=%s", esp_err_to_name(err));
        }
    }

    fp_nvs_set_str(FP_NVS_IMAGE_HASH, FP_UPDATING_SCREEN_HASH);
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
        /* fp_wifi_connect() returns FP_ERR_CONFIG, with no radio activity
         * at all, when the provisioned credentials are missing or
         * invalid (wifi.h). That is a provisioning defect, not a radio
         * or AP problem, and the Log Line Contract's "wifi" token points
         * an operator at the wrong fix (radio/AP) instead of the right
         * one (provision.sh) if the two are conflated here. */
        *fail_step_out = wifi_err == FP_ERR_CONFIG ? "config" : "wifi";
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

    /* The bring-up LED toggle sits here because this is the first point
     * a server answer exists, and it precedes every downstream exit
     * (hash skip, download, blit, deferred-draw, and every failure
     * return below) — so every exit inherits the decision from this one
     * branch. This can only ever extinguish the LED earlier than
     * app_main.c's unconditional pre-sleep call — never a substitute
     * for it. */
    if (!disp.led_enabled) {
        fp_led_off();
    }

    /* OTA before the hash-skip below: an offer must land even on a wake
     * where the picture is unchanged. Every branch either falls through
     * to continue this wake's normal poll (skip/refuse) or ends the
     * wake itself (a real reboot into the trial image, or a failure
     * through the single failure exit with step token "ota"). Neither
     * a battery nor a floor refusal is a failure - both mean "try again
     * later", not backoff-worthy. */
    if (disp.fw.present) {
        fp_ota_decision_t decision = fp_ota_decide(
            disp.fw.version, fp_ota_running_version(),
            CONFIG_SKYPANE_OTA_FLOOR_VERSION, fp_battery_mv(),
            fp_ota_trial_pending());
        switch (decision) {
        case FP_OTA_SKIP_SAME_VERSION:
            break;
        case FP_OTA_REFUSE_TRIAL_PENDING:
            /* Never touch FP_NVS_OTA_RESULT here: fp_ota_boot_check()
             * may have just recorded "trial;<running>" earlier this same
             * wake, still waiting to be reported, and overwriting it
             * with anything else would lose that report. */
            ESP_LOGI(TAG, "ota refused reason=trial_pending");
            break;
        case FP_OTA_REFUSE_BATTERY:
            fp_ota_record_result(FP_OTA_RESULT_DEFERRED_BATTERY, disp.fw.version);
            ESP_LOGI(TAG, "ota refused reason=battery");
            break;
        case FP_OTA_REFUSE_FLOOR:
            fp_ota_record_result(FP_OTA_RESULT_FAIL_FLOOR, disp.fw.version);
            ESP_LOGI(TAG, "ota refused reason=floor");
            break;
        case FP_OTA_START: {
            fp_ota_mark_try(disp.fw.version);
            draw_updating_screen();
            fp_wake_checkpoint();

            esp_err_t ota_wifi_err = fp_wifi_connect(15000);
            if (ota_wifi_err != ESP_OK) {
                fp_ota_record_result(FP_OTA_RESULT_FAIL_DOWNLOAD, disp.fw.version);
                *fail_step_out = "ota";
                return FP_POLL_FAILED;
            }
            fp_wake_checkpoint();

            fp_ota_result_t ota_fail;
            esp_err_t apply_err = fp_ota_apply(&disp.fw, &ota_fail);
            if (apply_err == ESP_OK) {
                ESP_LOGI(TAG, "ota switched version=%s restarting", disp.fw.version);
                esp_restart();
            }
            fp_ota_record_result(ota_fail, disp.fw.version);
            *fail_step_out = "ota";
            return FP_POLL_FAILED;
        }
        }
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
