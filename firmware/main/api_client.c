/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
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

#include "api_base.h"
#include "battery.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "secrets.h"
#include "validate.h"
#include "wifi.h"

static const char *TAG = "fp_api";

#define RESP_MAX 2048               /* poll responses are <1 KB */
#define API_BASE_MAX FP_API_BASE_MAX
#define URL_MAX (API_BASE_MAX + 24) /* base + "/device/v1/display" */

/* Dev builds only (CONFIG_SKYPANE_ALLOW_HTTP): the laptop stub server
 * has no TLS. Production leaves this option unset, so every URL this
 * file touches must be https. */
#ifdef CONFIG_SKYPANE_ALLOW_HTTP
static const bool s_allow_http = true;
#else
static const bool s_allow_http = false;
#endif

/* ---------------------------------------------------------------- helpers */

bool fp_api_has_token(void)
{
    char token[80];
    return fp_nvs_get_str(FP_NVS_DEVICE_TOKEN, token, sizeof(token)) == ESP_OK;
}

/* Resolves and validates the server base URL: the dev override when this
 * build allows plain http and one is configured, else the compiled
 * production default; normalized (fp_api_base_normalize collapses a
 * trailing slash so callers never build "//device...") and checked
 * against this build's scheme policy. Every caller propagates
 * FP_ERR_CONFIG unchanged rather than attempting a request with a
 * rejected base. */
static esp_err_t api_base_get(char *out, size_t cap)
{
#ifdef CONFIG_SKYPANE_ALLOW_HTTP
#ifdef SKYPANE_API_BASE_DEV
    const char *source = SKYPANE_API_BASE_DEV;
#else
    const char *source = SKYPANE_API_BASE;
#endif
#else
    const char *source = SKYPANE_API_BASE;
#endif
    if (fp_api_base_normalize(source, out, cap) != 0 || out[0] == 0 ||
        !fp_url_valid(out, cap, s_allow_http)) {
        ESP_LOGE(TAG, "API base URL rejected (this build requires https)");
        return FP_ERR_CONFIG;
    }
    return ESP_OK;
}

static void auth_header(esp_http_client_handle_t http)
{
    char token[80], bearer[96];
    if (fp_nvs_get_str(FP_NVS_DEVICE_TOKEN, token, sizeof(token)) == ESP_OK) {
        snprintf(bearer, sizeof(bearer), "Bearer %s", token);
        esp_http_client_set_header(http, "Authorization", bearer);
    }
    memset(token, 0, sizeof(token));
    memset(bearer, 0, sizeof(bearer));
}

/* Every telemetry header PROTOCOL.md §2 names, sent unconditionally on
 * every /display call (upstream sends X-Rssi only when nonzero; this
 * project always sends all four so the stub server's telemetry line -
 * and the battery-life measurement - never has a gap). X-Battery-Mv
 * carries one cached adc_oneshot + adc_cali read per wake, taken off the
 * EE02 driver board's own factory sense divider (battery.h, DEVICE-04);
 * zero is reported - PROTOCOL.md §2's unknown sentinel - if the read
 * fails, never a fabricated value. */
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

/* One esp_http_client config shape (crt_bundle_attach, timeout) shared by
 * setup, display and download — the three places this project opens an
 * HTTP connection (FW-14). */
static esp_http_client_handle_t http_client_new(const char *url,
                                                 esp_http_client_method_t method,
                                                 int timeout_ms)
{
    esp_http_client_config_t cfg = {
        .url = url,
        .method = method,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = timeout_ms,
    };
    return esp_http_client_init(&cfg);
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
        int written = esp_http_client_write(http, body, strlen(body));
        if (written != (int)strlen(body)) {
            esp_http_client_close(http);
            return FP_ERR_HTTP_TRANSPORT;
        }
    }
    if (esp_http_client_fetch_headers(http) < 0) {
        esp_http_client_close(http);
        return FP_ERR_HTTP_TRANSPORT;
    }
    int n = esp_http_client_read_response(http, resp, RESP_MAX - 1);
    int status = esp_http_client_get_status_code(http);
    esp_http_client_close(http);
    if (n < 0) {
        return FP_ERR_HTTP_TRANSPORT;
    }
    resp[n] = 0;
    *resp_len = n;

    fp_http_class_t cls = fp_http_status_classify(status);
    if (cls != FP_HTTP_CLASS_OK) {
        /* Bodies can echo validation inputs; never log setup credentials
         * or bearer tokens. Status + length is enough to diagnose. */
        ESP_LOGW(TAG, "HTTP %d (%d-byte response)", status, n);
        return cls == FP_HTTP_CLASS_AUTH ? FP_ERR_HTTP_AUTH : FP_ERR_HTTP_STATUS;
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
    esp_err_t err = api_base_get(base, sizeof(base));
    if (err != ESP_OK) {
        memset(body, 0, strlen(body));
        cJSON_free(body);
        return err;
    }
    snprintf(url, sizeof(url), "%s/device/v1/setup", base);
    esp_http_client_handle_t http =
        http_client_new(url, HTTP_METHOD_POST, 15000);
    if (!http) {
        memset(body, 0, strlen(body));
        cJSON_free(body);
        return ESP_ERR_NO_MEM;
    }
    esp_http_client_set_header(http, "Content-Type", "application/json");

    char resp[RESP_MAX];
    int n = 0;
    err = small_request(http, body, resp, &n);
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
    esp_err_t err = api_base_get(base, sizeof(base));
    if (err != ESP_OK) {
        return err;
    }
    snprintf(req_url, sizeof(req_url), "%s/device/v1/display", base);
    esp_http_client_handle_t http =
        http_client_new(req_url, HTTP_METHOD_GET, 20000);
    if (!http) {
        return ESP_ERR_NO_MEM;
    }
    auth_header(http);
    telemetry_headers(http, boot_reason);

    char resp[RESP_MAX];
    int n = 0;
    err = small_request(http, NULL, resp, &n);
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
    /* DEVICE-05 bring-up LED toggle - deliberately fetched here, outside
     * the rejection block below, and resolved after it. See its resolve
     * expression further down for why. */
    const cJSON *led = cJSON_GetObjectItem(json, "led_enabled");

    uint32_t sleep_val = 0;
    bool sleep_ok = cJSON_IsNumber(sleep_s) &&
        fp_sleep_s_parse(sleep_s->valuedouble, &sleep_val);

    fp_display_t parsed = {0};
    if (!cJSON_IsString(url) ||
        !fp_url_valid(url->valuestring, sizeof(parsed.image_url), s_allow_http) ||
        !cJSON_IsString(hash) || !fp_image_hash_valid(hash->valuestring) ||
        strlen(hash->valuestring) >= sizeof(parsed.image_hash) ||
        !sleep_ok) {
        cJSON_Delete(json);
        memset(resp, 0, sizeof(resp));
        return FP_ERR_HTTP_JSON;
    }
    strlcpy(parsed.image_url, url->valuestring, sizeof(parsed.image_url));
    strlcpy(parsed.image_hash, hash->valuestring, sizeof(parsed.image_hash));
    parsed.sleep_s = sleep_val;
    /* Permissive by design: a missing key yields NULL, and cJSON's type
     * predicates are NULL-safe and answer false, so an absent field
     * resolves to enabled; a null, string or number value is likewise
     * not a boolean, so a malformed value also resolves to enabled; only
     * an explicit JSON `false` yields disabled. Consequence: a server
     * that predates this field, or one with a future bug in it,
     * degrades to the LED behaving exactly as it always did, rather
     * than to a rejected poll and an exponential backoff - trading the
     * device's actual function for a debug LED's preference would be
     * the wrong failure direction, which is why this field is not
     * validated the way image_url/sleep_s are above. */
    parsed.led_enabled = fp_led_enabled_resolve(cJSON_IsBool(led), cJSON_IsTrue(led));

    /* `firmware` is out of scope (OTA is not implemented); no field of
     * it is read or stored regardless of what the server sends. */
    *out = parsed;
    cJSON_Delete(json);
    memset(resp, 0, sizeof(resp));
    return ESP_OK;
}

/* --------------------------------------------------------------- download */

esp_err_t fp_api_download(const char *url, const char *expected_hash,
                          uint8_t *buf)
{
    /* FP_IMAGE_BYTES (api_client.h) is exactly 960000 — 1200*1600 pixels,
     * two nibble-packed pixels per byte, PROTOCOL.md §1. The size check
     * below (`got != FP_IMAGE_BYTES`) is the gate that refuses to hand
     * `buf` to panel.c unless the download is exactly 960000 bytes. */
    if (!buf ||
        !fp_url_valid(url, sizeof(((fp_display_t *)0)->image_url), s_allow_http) ||
        !fp_image_hash_valid(expected_hash)) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_http_client_handle_t http = http_client_new(url, HTTP_METHOD_GET, 30000);
    if (!http) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t err = esp_http_client_open(http, 0);
    if (err != ESP_OK) {
        esp_http_client_cleanup(http);
        return err;
    }
    if (esp_http_client_fetch_headers(http) < 0) {
        esp_http_client_close(http);
        esp_http_client_cleanup(http);
        return ESP_FAIL; /* maps to step=download */
    }

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

    /* Compute the digest only once the transfer itself checks out -
     * hashing 960000 bytes is wasted work when the transfer is already
     * going to be rejected. fp_download_verdict re-checks the same
     * transfer facts regardless, so a BAD_TRANSFER verdict never
     * depends on hex being meaningful. */
    unsigned char digest[32] = {0};
    char hex[FP_IMAGE_HASH_BUF] = "";
    bool transfer_ok = status == 200 && got == FP_IMAGE_BYTES && !oversize;
    if (transfer_ok) {
        mbedtls_sha256(buf, FP_IMAGE_BYTES, digest, 0);
        fp_sha256_to_image_hash(digest, hex);
    }
    fp_download_verdict_t verdict = fp_download_verdict(
        status, got, FP_IMAGE_BYTES, oversize, hex, expected_hash);

    if (verdict == FP_DOWNLOAD_BAD_TRANSFER) {
        ESP_LOGW(TAG, "download bad: HTTP %d, %lu bytes%s", status,
                 (unsigned long)got, oversize ? " (oversize)" : "");
        return ESP_FAIL;
    }
    if (verdict == FP_DOWNLOAD_HASH_MISMATCH) {
        ESP_LOGW(TAG, "sha256 MISMATCH, dropping image");
        return FP_ERR_IMAGE_VERIFY; /* never blit an unverified buffer */
    }
    return ESP_OK;
}
