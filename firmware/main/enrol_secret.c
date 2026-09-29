/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "enrol_secret.h"

#include <string.h>

#include "esp_log.h"
#include "nvs_flash.h"

#include "api_client.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "validate.h"

static const char *TAG = "fp_creds";

esp_err_t fp_enrol_secret_load(char *out, size_t cap)
{
    if (!out || cap < 65) {
        return ESP_ERR_INVALID_ARG;
    }
    out[0] = 0;

    /* A failure here (partition missing from the flashed table, or the
     * partition itself corrupt/unformatted) is a provisioning defect,
     * not something to repair by erasing — erasing would destroy the
     * one copy of this device's secret. Reflash (flash.sh) and
     * re-provision (provision.sh) instead; the caller logs the guidance. */
    esp_err_t err = nvs_flash_init_partition(FP_NVS_SECRET_PARTITION);
    if (err != ESP_OK) {
        return err;
    }

    err = fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_ENROL_SECRET,
                              out, cap);
    nvs_flash_deinit_partition(FP_NVS_SECRET_PARTITION);
    if (err != ESP_OK) {
        return err;
    }
    if (!fp_token_valid(out)) {
        memset(out, 0, cap);
        return ESP_ERR_INVALID_RESPONSE;
    }
    return ESP_OK;
}

esp_err_t fp_device_creds_load(fp_device_creds_t *out)
{
    if (!out) {
        return ESP_ERR_INVALID_ARG;
    }
    memset(out, 0, sizeof(*out));

    esp_err_t err = nvs_flash_init_partition(FP_NVS_SECRET_PARTITION);
    if (err != ESP_OK) {
        return FP_ERR_CONFIG;
    }

    char ssid[33] = {0}, pass[65] = {0}, api_base[128] = {0};
    char ip[16] = {0}, mask[16] = {0}, gw[16] = {0}, dns[16] = {0};
    bool ok = true;
    const char *bad_key = NULL;

    esp_err_t rerr = fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION,
                                         FP_NVS_WIFI_SSID, ssid, sizeof(ssid));
    if (rerr != ESP_OK || !fp_wifi_ssid_valid(ssid)) {
        ok = false;
        bad_key = FP_NVS_WIFI_SSID;
    }

    if (ok) {
        /* A missing key and a stored empty string are not the same
         * thing here: an open network is deliberately provisioned as
         * "", while a missing key means provision.sh was never run for
         * this device and the wake must fail rather than silently join
         * an open network nobody asked for. */
        rerr = fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_WIFI_PASS,
                                   pass, sizeof(pass));
        if (rerr != ESP_OK || !fp_wifi_pass_valid(pass)) {
            ok = false;
            bad_key = FP_NVS_WIFI_PASS;
        }
    }

    if (ok) {
        /* The https-only production rule is enforced later, by
         * api_client.c's api_base_get() through fp_url_valid(); only
         * "present and non-empty" is checked here. */
        rerr = fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_API_BASE,
                                   api_base, sizeof(api_base));
        if (rerr != ESP_OK || api_base[0] == 0) {
            ok = false;
            bad_key = FP_NVS_API_BASE;
        }
    }

    if (ok) {
        /* Absent static-IP keys read back as "" (the local buffers were
         * zeroed above), the same shape fp_static_ip_set_valid treats as
         * "not provisioned" — so a genuinely missing key and a key
         * holding "" reach the validator identically. */
        (void)fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_STATIC_IP,
                                  ip, sizeof(ip));
        (void)fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_STATIC_MASK,
                                  mask, sizeof(mask));
        (void)fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_STATIC_GW,
                                  gw, sizeof(gw));
        (void)fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_STATIC_DNS,
                                  dns, sizeof(dns));
        if (!fp_static_ip_set_valid(ip, mask, gw, dns)) {
            ok = false;
            bad_key = "static_ip_set";
        }
    }

    nvs_flash_deinit_partition(FP_NVS_SECRET_PARTITION);

    if (!ok) {
        ESP_LOGE(TAG,
                 "provisioned credential missing or invalid (%s); "
                 "re-provision with firmware/provision.sh",
                 bad_key ? bad_key : "static_ip_set");
        memset(out, 0, sizeof(*out));
        memset(ssid, 0, sizeof(ssid));
        memset(pass, 0, sizeof(pass));
        memset(api_base, 0, sizeof(api_base));
        return FP_ERR_CONFIG;
    }

    strlcpy(out->ssid, ssid, sizeof(out->ssid));
    strlcpy(out->pass, pass, sizeof(out->pass));
    strlcpy(out->api_base, api_base, sizeof(out->api_base));
    out->has_static = ip[0] != 0 || mask[0] != 0 || gw[0] != 0 || dns[0] != 0;
    if (out->has_static) {
        strlcpy(out->ip, ip, sizeof(out->ip));
        strlcpy(out->mask, mask, sizeof(out->mask));
        strlcpy(out->gw, gw, sizeof(out->gw));
        strlcpy(out->dns, dns, sizeof(out->dns));
    }

    memset(ssid, 0, sizeof(ssid));
    memset(pass, 0, sizeof(pass));
    memset(api_base, 0, sizeof(api_base));
    return ESP_OK;
}
