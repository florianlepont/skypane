/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#include "state_machine.h"

#include <string.h>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "nvs.h"

#include "api_client.h"
#include "led.h"
#include "nvs_schema.h"
#include "panel.h"
#include "secrets.h"
#include "wifi.h"

static const char *TAG = "skypane";

fp_poll_result_t fp_poll_once(const char *boot_reason, uint32_t *sleep_s_out,
                              const char **fail_step_out)
{
    if (!boot_reason || !sleep_s_out || !fail_step_out) {
        return FP_POLL_FAILED;
    }

    if (fp_wifi_connect(15000) != ESP_OK) {
        *fail_step_out = "wifi";
        return FP_POLL_FAILED;
    }

    if (!fp_api_has_token()) {
        /* First wake ever (or the first wake after an NVS erase): enrol
         * before any /display poll can carry a bearer token. Phase 1 has
         * no BLE provisioning, so the setup secret comes straight from
         * the gitignored secrets.h — see api_client.c's base-URL
         * resolution comment for the same Phase-1-only scoping. */
        if (fp_api_setup(SKYPANE_SETUP_SECRET) != ESP_OK) {
            *fail_step_out = "http";
            return FP_POLL_FAILED;
        }
    }

    fp_display_t disp;
    esp_err_t err = fp_api_get_display(boot_reason, &disp);
    if (err != ESP_OK) {
        *fail_step_out = err == FP_ERR_HTTP_STATUS ? "status"
            : err == FP_ERR_HTTP_JSON ? "json" : "http";
        return FP_POLL_FAILED;
    }
    *sleep_s_out = disp.sleep_s;

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
    nvs_handle_t nvs;
    if (nvs_open(FP_NVS_NAMESPACE, NVS_READONLY, &nvs) == ESP_OK) {
        size_t len = sizeof(last_hash);
        nvs_get_str(nvs, FP_NVS_IMAGE_HASH, last_hash, &len);
        nvs_close(nvs);
    }
    if (strcmp(last_hash, disp.image_hash) == 0) {
        ESP_LOGI(TAG, "image unchanged, skipping download");
        return FP_POLL_OK_UNCHANGED;
    }

    uint8_t *buf = heap_caps_malloc(FP_IMAGE_BYTES,
                                    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        ESP_LOGE(TAG, "no PSRAM for framebuffer");
        *fail_step_out = "download";
        return FP_POLL_FAILED;
    }
    err = fp_api_download(disp.image_url, disp.image_hash, buf);
    if (err != ESP_OK) {
        heap_caps_free(buf);
        *fail_step_out = err == FP_ERR_IMAGE_VERIFY ? "verify" : "download";
        return FP_POLL_FAILED;
    }

    /* Radio down before the panel: the blit (and any wait the panel's
     * refresh spacing imposes) is the longest part of the wake, and
     * holding an association through it buys nothing. */
    fp_wifi_stop();
    err = fp_panel_draw(buf);
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
    if (nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_str(nvs, FP_NVS_IMAGE_HASH, disp.image_hash);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
    ESP_LOGI(TAG, "refreshed to %.23s...", disp.image_hash);
    return FP_POLL_OK_REFRESHED;
}
