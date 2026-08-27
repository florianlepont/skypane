/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#include "api_client.h"

#include <stdio.h>
#include <string.h>

#include "cJSON.h"
#include "esp_app_desc.h"
#include "esp_crt_bundle.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "mbedtls/sha256.h"
#include "nvs.h"
#include "sdkconfig.h"

#include "battery.h"
#include "nvs_schema.h"
#include "secrets.h"
#include "wifi.h"

static const char *TAG = "fp_api";

#define RESP_MAX 2048               /* poll responses are <1 KB */
#define API_BASE_MAX 256            /* fits SKYPANE_API_BASE with room to spare */
#define URL_MAX (API_BASE_MAX + 24) /* base + "/device/v1/display" */

/* ---------------------------------------------------------------- helpers */

static esp_err_t nvs_get_string(const char *key, char *out, size_t cap)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(FP_NVS_NAMESPACE, NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    size_t len = cap;
    err = nvs_get_str(nvs, key, out, &len);
    nvs_close(nvs);
    return err;
}

bool fp_api_has_token(void)
{
    char token[80];
    return nvs_get_string(FP_NVS_DEVICE_TOKEN, token, sizeof(token)) == ESP_OK;
}

/* PROTOCOL.md §2: image_hash is exactly "sha256:" followed by 64
 * lowercase hex characters. Uppercase hex is rejected. */
static bool image_hash_valid(const char *hash)
{
    if (!hash || strncmp(hash, "sha256:", 7) != 0) {
        return false;
    }
    const char *hex = hash + 7;
    size_t len = strlen(hex);
    if (len != 64) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        char c = hex[i];
        bool lower_hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        if (!lower_hex) {
            return false;
        }
    }
    return true;
}

/* PROTOCOL.md §2: image/firmware URLs must be non-empty, fitting
 * http:// or https:// strings. */
static bool url_valid(const char *url, size_t cap)
{
    if (!url) {
        return false;
    }
    size_t len = strlen(url);
    if (len == 0 || len >= cap) {
        return false;
    }
    return strncmp(url, "http://", 7) == 0 || strncmp(url, "https://", 8) == 0;
}

/* Phase 1 base-URL resolution point (01-PATTERNS.md "Plain-HTTP BYOS
 * Local Stub Allowance"). Upstream resolves a hand-set NVS override,
 * falling back to a compiled default, through a versioned target blob
 * written only by provisioning flows (target_contract.h / identity.h,
 * deliberately not vendored here — see firmware/VENDOR.md). This
 * project has no provisioning this phase, so it targets SKYPANE_API_BASE
 * from the gitignored secrets.h directly.
 *
 * A plain http base is accepted here because PROTOCOL.md §5 explicitly
 * permits a hand-set target to be plain http. This is scoped to the
 * local stub server on the developer's own LAN and MUST NOT be carried
 * into the Phase 2 deployed-server firmware — that move is a
 * configuration change (SKYPANE_API_BASE moves to the VPS's https:// base),
 * not a code change, because the ESP-TLS + public CA bundle path below
 * (crt_bundle_attach) stays compiled in and reachable the whole time. */
static void api_base_get(char *out, size_t cap)
{
    strlcpy(out, SKYPANE_API_BASE, cap);
}

static void auth_header(esp_http_client_handle_t http)
{
    char token[80], bearer[96];
    if (nvs_get_string(FP_NVS_DEVICE_TOKEN, token, sizeof(token)) == ESP_OK) {
        snprintf(bearer, sizeof(bearer), "Bearer %s", token);
        esp_http_client_set_header(http, "Authorization", bearer);
    }
    memset(token, 0, sizeof(token));
    memset(bearer, 0, sizeof(bearer));
}

/* Every telemetry header PROTOCOL.md §2 names, sent unconditionally on
 * every /display and /log call (upstream sends X-Rssi only when nonzero;
 * this project always sends all four so the stub server's telemetry
 * line - and the battery-life measurement - never has a gap).
 * X-Battery-Mv carries one cached adc_oneshot + adc_cali read per wake,
 * taken off the EE02 driver board's own factory sense divider
 * (battery.h, DEVICE-04); zero is reported - PROTOCOL.md §2's unknown
 * sentinel - if the read fails, never a fabricated value. */
static void telemetry_headers(esp_http_client_handle_t http,
                              const char *boot_reason)
{
    char buf[16];
    int rssi = fp_wifi_rssi();
    snprintf(buf, sizeof(buf), "%d", rssi);
    esp_http_client_set_header(http, "X-Rssi", buf);

    snprintf(buf, sizeof(buf), "%u", (unsigned)fp_battery_mv());
    esp_http_client_set_header(http, "X-Battery-Mv", buf);

    esp_http_client_set_header(http, "X-Fw-Version",
                               esp_app_get_description()->version);
    esp_http_client_set_header(http, "X-Boot-Reason", boot_reason);
}

/* Perform a request whose response body fits in RESP_MAX. */
static esp_err_t small_request(esp_http_client_handle_t http,
                               const char *body, char *resp, int *resp_len)
{
    esp_err_t err = esp_http_client_open(http, body ? strlen(body) : 0);
    if (err != ESP_OK) {
        return FP_ERR_HTTP_TRANSPORT;
    }
    if (body) {
        esp_http_client_write(http, body, strlen(body));
    }
    esp_http_client_fetch_headers(http);
    int n = esp_http_client_read_response(http, resp, RESP_MAX - 1);
    int status = esp_http_client_get_status_code(http);
    esp_http_client_close(http);
    if (n < 0) {
        return FP_ERR_HTTP_TRANSPORT;
    }
    resp[n] = 0;
    *resp_len = n;
    if (status != 200) {
        /* Bodies can echo validation inputs; never log setup credentials
         * or bearer tokens. Status + length is enough to diagnose. */
        ESP_LOGW(TAG, "HTTP %d (%d-byte response)", status, n);
        return FP_ERR_HTTP_STATUS;
    }
    return ESP_OK;
}

/* ------------------------------------------------------------------ setup */

esp_err_t fp_api_setup(const char *provision_secret)
{
    if (!provision_secret) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    char mac_text[18];
    snprintf(mac_text, sizeof(mac_text),
             "%02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    cJSON *request = cJSON_CreateObject();
    if (!request) {
        return ESP_ERR_NO_MEM;
    }
    cJSON_AddStringToObject(request, "mac", mac_text);
    cJSON_AddStringToObject(request, "hw_rev", CONFIG_FP_HW_REV);
    cJSON_AddStringToObject(request, "provision_secret", provision_secret);
    char *body = cJSON_PrintUnformatted(request);
    cJSON_Delete(request);
    if (!body) {
        return ESP_ERR_NO_MEM;
    }

    char base[API_BASE_MAX], url[URL_MAX];
    api_base_get(base, sizeof(base));
    snprintf(url, sizeof(url), "%s/device/v1/setup", base);
    esp_http_client_config_t cfg = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 15000,
    };
    esp_http_client_handle_t http = esp_http_client_init(&cfg);
    if (!http) {
        memset(body, 0, strlen(body));
        cJSON_free(body);
        return ESP_ERR_NO_MEM;
    }
    esp_http_client_set_header(http, "Content-Type", "application/json");

    char resp[RESP_MAX];
    int n = 0;
    esp_err_t err = small_request(http, body, resp, &n);
    esp_http_client_cleanup(http);
    memset(body, 0, strlen(body));
    cJSON_free(body);
    if (err != ESP_OK) {
        memset(resp, 0, sizeof(resp));
        return err;
    }

    cJSON *json = cJSON_ParseWithLength(resp, (size_t)n);
    const cJSON *tok = json
        ? cJSON_GetObjectItemCaseSensitive(json, "device_token") : NULL;
    bool token_ok = cJSON_IsString(tok) && tok->valuestring &&
        strlen(tok->valuestring) == 64;
    if (token_ok) {
        for (const char *p = tok->valuestring; *p; p++) {
            if (!((*p >= '0' && *p <= '9') || (*p >= 'a' && *p <= 'f'))) {
                token_ok = false;
                break;
            }
        }
    }
    if (!token_ok) {
        if (cJSON_IsString(tok) && tok->valuestring) {
            memset(tok->valuestring, 0, strlen(tok->valuestring));
        }
        cJSON_Delete(json);
        memset(resp, 0, sizeof(resp));
        return FP_ERR_HTTP_JSON;
    }

    nvs_handle_t nvs = 0;
    err = nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err == ESP_OK) {
        err = nvs_set_str(nvs, FP_NVS_DEVICE_TOKEN, tok->valuestring);
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    if (nvs != 0) {
        nvs_close(nvs);
    }
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "setup accepted; device credential stored");
    }
    memset(tok->valuestring, 0, strlen(tok->valuestring));
    cJSON_Delete(json);
    memset(resp, 0, sizeof(resp));
    return err;
}

/* ---------------------------------------------------------------- display */

esp_err_t fp_api_get_display(const char *boot_reason, fp_display_t *out)
{
    if (!boot_reason || !out) {
        return ESP_ERR_INVALID_STATE;
    }
    char base[API_BASE_MAX], req_url[URL_MAX];
    api_base_get(base, sizeof(base));
    snprintf(req_url, sizeof(req_url), "%s/device/v1/display", base);
    esp_http_client_config_t cfg = {
        .url = req_url,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 20000,
    };
    esp_http_client_handle_t http = esp_http_client_init(&cfg);
    if (!http) {
        return ESP_ERR_NO_MEM;
    }
    auth_header(http);
    telemetry_headers(http, boot_reason);

    char resp[RESP_MAX];
    int n = 0;
    esp_err_t err = small_request(http, NULL, resp, &n);
    esp_http_client_cleanup(http);
    if (err != ESP_OK) {
        return err;
    }

    cJSON *json = cJSON_ParseWithLength(resp, (size_t)n);
    if (!cJSON_IsObject(json)) {
        cJSON_Delete(json);
        memset(resp, 0, sizeof(resp));
        return FP_ERR_HTTP_JSON;
    }
    const cJSON *url = cJSON_GetObjectItem(json, "image_url");
    const cJSON *hash = cJSON_GetObjectItem(json, "image_hash");
    const cJSON *sleep_s = cJSON_GetObjectItem(json, "sleep_s");
    const cJSON *reset = cJSON_GetObjectItem(json, "reset");

    /* sleep_s: an exact integer within 1..4294967295 (PROTOCOL.md §2).
     * Zero, fractional values and anything above UINT32_MAX are
     * rejected - this bound is what stops a hostile or buggy server
     * parking the device for years. */
    bool sleep_ok = cJSON_IsNumber(sleep_s) &&
        sleep_s->valuedouble >= 1.0 &&
        sleep_s->valuedouble <= 4294967295.0 &&
        sleep_s->valuedouble == (double)(uint32_t)sleep_s->valuedouble;

    fp_display_t parsed = {0};
    if (!cJSON_IsString(url) ||
        !url_valid(url->valuestring, sizeof(parsed.image_url)) ||
        !cJSON_IsString(hash) || !image_hash_valid(hash->valuestring) ||
        strlen(hash->valuestring) >= sizeof(parsed.image_hash) ||
        !sleep_ok || !cJSON_IsBool(reset)) {
        cJSON_Delete(json);
        memset(resp, 0, sizeof(resp));
        return FP_ERR_HTTP_JSON;
    }
    strlcpy(parsed.image_url, url->valuestring, sizeof(parsed.image_url));
    strlcpy(parsed.image_hash, hash->valuestring, sizeof(parsed.image_hash));
    parsed.sleep_s = (uint32_t)sleep_s->valuedouble;
    parsed.reset = cJSON_IsTrue(reset);

    /* `firmware` is null in Phase 1 (OTA is out of scope); no field of
     * it is read or stored regardless of what the server sends. */
    *out = parsed;
    cJSON_Delete(json);
    memset(resp, 0, sizeof(resp));
    return ESP_OK;
}

/* -------------------------------------------------------------------- log */

esp_err_t fp_api_post_logs(const char *body, const char *boot_reason)
{
    if (!body || !boot_reason) {
        return ESP_ERR_INVALID_STATE;
    }
    char base[API_BASE_MAX], req_url[URL_MAX];
    api_base_get(base, sizeof(base));
    snprintf(req_url, sizeof(req_url), "%s/device/v1/log", base);
    esp_http_client_config_t cfg = {
        .url = req_url,
        .method = HTTP_METHOD_POST,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 15000,
    };
    esp_http_client_handle_t http = esp_http_client_init(&cfg);
    if (!http) {
        return ESP_ERR_NO_MEM;
    }
    esp_http_client_set_header(http, "Content-Type", "application/json");
    auth_header(http);
    telemetry_headers(http, boot_reason);
    char resp[RESP_MAX];
    int n = 0;
    esp_err_t err = small_request(http, body, resp, &n);
    esp_http_client_cleanup(http);
    return err;
}

/* --------------------------------------------------------------- download */

esp_err_t fp_api_download(const char *url, const char *expected_hash,
                          uint8_t *buf)
{
    /* FP_IMAGE_BYTES (api_client.h) is exactly 960000 — 1200*1600 pixels,
     * two nibble-packed pixels per byte, PROTOCOL.md §1. The size check
     * below (`got != FP_IMAGE_BYTES`) is the gate that refuses to hand
     * `buf` to panel.c unless the download is exactly 960000 bytes. */
    if (!buf || !url_valid(url, sizeof(((fp_display_t *)0)->image_url)) ||
        !image_hash_valid(expected_hash)) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_http_client_config_t cfg = {
        .url = url,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 30000,
    };
    esp_http_client_handle_t http = esp_http_client_init(&cfg);
    if (!http) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t err = esp_http_client_open(http, 0);
    if (err != ESP_OK) {
        esp_http_client_cleanup(http);
        return err;
    }
    esp_http_client_fetch_headers(http);

    uint32_t got = 0;
    while (got < FP_IMAGE_BYTES) {
        int n = esp_http_client_read(http, (char *)buf + got,
                                     FP_IMAGE_BYTES - got);
        if (n <= 0) {
            break;
        }
        got += n;
    }
    /* Anything beyond the expected size is a protocol violation. */
    char extra;
    bool oversize = esp_http_client_read(http, &extra, 1) > 0;
    int status = esp_http_client_get_status_code(http);
    esp_http_client_close(http);
    esp_http_client_cleanup(http);

    if (status != 200 || got != FP_IMAGE_BYTES || oversize) {
        ESP_LOGW(TAG, "download bad: HTTP %d, %lu bytes%s", status,
                 (unsigned long)got, oversize ? " (oversize)" : "");
        return ESP_FAIL;
    }

    unsigned char digest[32];
    mbedtls_sha256(buf, FP_IMAGE_BYTES, digest, 0);
    char hex[7 + 64 + 1] = "sha256:";
    for (int i = 0; i < 32; i++) {
        snprintf(hex + 7 + i * 2, 3, "%02x", digest[i]);
    }
    if (strcmp(hex, expected_hash) != 0) {
        ESP_LOGW(TAG, "sha256 MISMATCH, dropping image");
        return FP_ERR_IMAGE_VERIFY; /* never blit an unverified buffer */
    }
    return ESP_OK;
}
