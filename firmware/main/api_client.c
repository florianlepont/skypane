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
#include "esp_timer.h"
#include "esp_transport_ssl.h"
#include "mbedtls/sha256.h"
#include "sdkconfig.h"

#include "api_base.h"
#include "battery.h"
#include "enrol_secret.h"
#include "nvs_schema.h"
#include "nvs_util.h"
#include "secrets.h"
#include "tls_session.h"
#include "validate.h"
#include "wake_guard.h"
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

/* ------------------------------------------------------- shared per-wake client
 *
 * One esp_http_client handle (and, when the server allows it, one
 * TCP+TLS connection) is reused for every request of a wake - setup,
 * display, and a same-origin image download - instead of a fresh
 * connection per request. This is FW-10's mandatory half; tls_session.c
 * carries the TLS session across deep sleep as a best-effort addition on
 * top of it. s_connects/s_first_connect_ms are read once, in
 * fp_api_release(), for the diagnostic line the hardware session uses to
 * explain the per-cycle overhead. */
static esp_http_client_handle_t s_http;
static esp_transport_handle_t s_tls; /* NULL for the dev http:// path */
static char s_origin[API_BASE_MAX];  /* scheme://host[:port] of s_http */
static unsigned s_connects;
static uint32_t s_first_connect_ms;
static int64_t s_connect_started_us;
static bool s_tls_saved; /* fp_tls_session_save() runs at most once/wake */

/* Every telemetry/auth header any request on the shared handle can carry.
 * Deleting all of them before setting only what the next request needs
 * is what keeps a bearer token or a battery reading from leaking onto a
 * request it was never meant for (T-34-09-01) - esp_http_client does not
 * clear headers on its own between esp_http_client_set_url() calls. */
static void clear_request_headers(esp_http_client_handle_t http)
{
    esp_http_client_delete_header(http, "Authorization");
    esp_http_client_delete_header(http, "Content-Type");
    esp_http_client_delete_header(http, "X-Rssi");
    esp_http_client_delete_header(http, "X-Battery-Mv");
    esp_http_client_delete_header(http, "X-Fw-Version");
    esp_http_client_delete_header(http, "X-Boot-Reason");
}

/* Extracts "scheme://host[:port]" from url, stopping at the first '/'
 * after the scheme - the part esp_http_client keys a TCP+TLS connection
 * on. Used to decide whether a download URL can share s_http (same
 * origin) or needs its own one-shot client. Truncates rather than
 * overruns if url's origin is implausibly long; a truncated result only
 * ever causes the conservative (one-shot, no shared headers) path to be
 * taken, never a wrong match. */
static void url_origin(const char *url, char *out, size_t cap)
{
    if (!cap) {
        return;
    }
    const char *scheme_end = strstr(url, "://");
    const char *scan = scheme_end ? scheme_end + 3 : url;
    const char *slash = strchr(scan, '/');
    size_t len = slash ? (size_t)(slash - url) : strlen(url);
    if (len >= cap) {
        len = cap - 1;
    }
    memcpy(out, url, len);
    out[len] = 0;
}

static void session_connect_noted(void)
{
    if (s_connects == 0) {
        int64_t elapsed_us = esp_timer_get_time() - s_connect_started_us;
        s_first_connect_ms = elapsed_us > 0 ? (uint32_t)(elapsed_us / 1000) : 0;
    }
    s_connects++;
}

static esp_err_t session_event_handler(esp_http_client_event_t *evt)
{
    if (evt->event_id == HTTP_EVENT_ON_CONNECTED) {
        session_connect_noted();
    }
    return ESP_OK;
}

/* Serializes s_tls's current session into RTC memory for the next wake,
 * once per wake - called right after the first request on s_http this
 * wake has returned any HTTP status (esp_http_client's own
 * save_client_session machinery has already captured the session by the
 * time a connect completes, so this just has to run once to persist
 * it). A no-op on the dev http:// path (s_tls is NULL there) and on
 * every call after the first. */
static void maybe_save_tls_session(void)
{
    if (s_tls && !s_tls_saved) {
        fp_tls_session_save(s_tls, s_origin);
        s_tls_saved = true;
    }
}

/* Replaces the plan-34-06 http_client_new() for every request that
 * shares s_http: the first call this wake creates the handle (attaching
 * a custom SSL transport for https so tls_session.c has something to
 * offer a saved session to before the first connect); every later call
 * just retargets the existing handle. Never calls esp_http_client_open()
 * itself - callers open, and never close after success, so a server that
 * allows it keeps the connection alive across requests. */
static esp_err_t session_client(const char *url, esp_http_client_method_t method,
                                int timeout_ms, esp_http_client_handle_t *out)
{
    if (!s_http) {
        url_origin(url, s_origin, sizeof(s_origin));
        bool https = strncmp(url, "https://", 8) == 0;
        esp_http_client_config_t cfg = {
            .url = url,
            .method = method,
            .crt_bundle_attach = esp_crt_bundle_attach,
            .timeout_ms = timeout_ms,
            .event_handler = session_event_handler,
        };
        if (https) {
            s_tls = esp_transport_ssl_init();
            if (!s_tls) {
                return ESP_ERR_NO_MEM;
            }
            esp_transport_ssl_crt_bundle_attach(s_tls, esp_crt_bundle_attach);
            esp_transport_set_default_port(s_tls, 443);
#if CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS
            cfg.save_client_session = true;
#endif
#if CONFIG_ESP_HTTP_CLIENT_ENABLE_CUSTOM_TRANSPORT
            cfg.transport = s_tls;
#endif
            /* Offered before the transport's first connect, so a session
             * saved by a previous wake gets a chance to abbreviate this
             * wake's very first handshake (FW-10, best effort). */
            fp_tls_session_offer(s_tls, s_origin);
        }
        s_http = esp_http_client_init(&cfg);
        if (!s_http) {
            if (s_tls) {
                esp_transport_destroy(s_tls);
                s_tls = NULL;
            }
            return ESP_ERR_NO_MEM;
        }
    } else {
        if (esp_http_client_set_url(s_http, url) != ESP_OK ||
            esp_http_client_set_method(s_http, method) != ESP_OK ||
            esp_http_client_set_timeout_ms(s_http, timeout_ms) != ESP_OK) {
            return FP_ERR_HTTP_TRANSPORT;
        }
    }
    *out = s_http;
    return ESP_OK;
}

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

/* One esp_http_client config shape (crt_bundle_attach, timeout) for the
 * one case that still needs a fresh, one-shot handle: a download whose
 * URL is not on s_origin (a presigned CDN URL on a different host, say)
 * - carrying the API handle's keep-alive connection or its headers over
 * to an unrelated origin would be pointless and, for the headers, a
 * credential leak (T-34-09-01). setup/display/same-origin download all
 * go through session_client() instead. */
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

/* Perform a request whose response body fits in RESP_MAX, on the shared
 * s_http handle. If the connection turns out to have been closed by the
 * peer (an HTTP/1.0 server like the LAN stub closes after every
 * response), retries once on a fresh connection - but only once, and
 * only if s_http has already connected successfully at least once this
 * wake (s_connects > 0): a handle's very first connect failing is a real
 * problem no retry fixes, while a later one failing on a handle that
 * already worked is exactly the "server closed the keep-alive" case
 * (T-34-09-06). Never retries once a response status has been read
 * (esp_http_client_fetch_headers succeeded) - only a transport-level
 * failure before that point is retried. */
static esp_err_t small_request(esp_http_client_handle_t http,
                               const char *body, char *resp, int *resp_len)
{
    bool retry_ok = s_connects > 0;
    bool retried = false;

open_again:
    s_connect_started_us = esp_timer_get_time();
    esp_err_t err = esp_http_client_open(http, body ? strlen(body) : 0);
    if (err != ESP_OK) {
        if (retry_ok && !retried) {
            retried = true;
            esp_http_client_close(http);
            goto open_again;
        }
        if (s_connects == 0 && fp_tls_session_offered()) {
            fp_tls_session_forget();
        }
        return FP_ERR_HTTP_TRANSPORT;
    }
    if (body) {
        int written = esp_http_client_write(http, body, strlen(body));
        if (written != (int)strlen(body)) {
            esp_http_client_close(http);
            if (retry_ok && !retried) {
                retried = true;
                goto open_again;
            }
            if (s_connects == 0 && fp_tls_session_offered()) {
                fp_tls_session_forget();
            }
            return FP_ERR_HTTP_TRANSPORT;
        }
    }
    if (esp_http_client_fetch_headers(http) < 0) {
        esp_http_client_close(http);
        if (retry_ok && !retried) {
            retried = true;
            goto open_again;
        }
        if (s_connects == 0 && fp_tls_session_offered()) {
            fp_tls_session_forget();
        }
        return FP_ERR_HTTP_TRANSPORT;
    }
    maybe_save_tls_session();
    int n = esp_http_client_read_response(http, resp, RESP_MAX - 1);
    int status = esp_http_client_get_status_code(http);
    /* Never close here on a successful read - that is what forced a
     * fresh TCP+TLS connection per request before this plan. The handle
     * stays open (even on a read failure below, which is never retried)
     * for the wake's next request or for fp_api_release()'s eventual
     * cleanup. */
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

esp_err_t fp_api_setup(void)
{
    char secret[65];
    esp_err_t err = fp_enrol_secret_load(secret, sizeof(secret));
    if (err != ESP_OK) {
        ESP_LOGE(TAG,
                 "no enrolment secret in the '%s' partition; provision "
                 "this device with firmware/provision.sh",
                 FP_NVS_SECRET_PARTITION);
        return FP_ERR_NO_SECRET;
    }

    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    char mac_text[18];
    snprintf(mac_text, sizeof(mac_text),
             "%02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    cJSON *request = cJSON_CreateObject();
    if (!request) {
        memset(secret, 0, sizeof(secret));
        return ESP_ERR_NO_MEM;
    }
    cJSON_AddStringToObject(request, "mac", mac_text);
    cJSON_AddStringToObject(request, "hw_rev", CONFIG_FP_HW_REV);
    cJSON_AddStringToObject(request, "provision_secret", secret);
    char *body = cJSON_PrintUnformatted(request);
    cJSON_Delete(request);
    memset(secret, 0, sizeof(secret));
    if (!body) {
        return ESP_ERR_NO_MEM;
    }

    char base[API_BASE_MAX], url[URL_MAX];
    err = api_base_get(base, sizeof(base));
    if (err != ESP_OK) {
        memset(body, 0, strlen(body));
        cJSON_free(body);
        return err;
    }
    snprintf(url, sizeof(url), "%s/device/v1/setup", base);
    esp_http_client_handle_t http;
    err = session_client(url, HTTP_METHOD_POST, 15000, &http);
    if (err != ESP_OK) {
        memset(body, 0, strlen(body));
        cJSON_free(body);
        return err;
    }
    clear_request_headers(http);
    esp_http_client_set_header(http, "Content-Type", "application/json");

    char resp[RESP_MAX];
    int n = 0;
    err = small_request(http, body, resp, &n);
    memset(body, 0, strlen(body));
    cJSON_free(body);
    if (err == FP_ERR_HTTP_AUTH) {
        /* Nothing to erase here: setup never had a token to begin with.
         * The secret itself is not at fault for a retry - it stays put
         * for the next wake, which tries again after normal backoff. */
        ESP_LOGW(TAG, "enrolment refused by the server (secret not "
                      "accepted or device not registered)");
        memset(resp, 0, sizeof(resp));
        return FP_ERR_ENROL_REJECTED;
    }
    if (err != ESP_OK) {
        memset(resp, 0, sizeof(resp));
        return err;
    }

    cJSON *json = cJSON_ParseWithLength(resp, (size_t)n);
    const cJSON *tok = json
        ? cJSON_GetObjectItemCaseSensitive(json, "device_token") : NULL;
    bool token_ok = cJSON_IsString(tok) && tok->valuestring &&
        fp_token_valid(tok->valuestring);
    if (!token_ok) {
        if (cJSON_IsString(tok) && tok->valuestring) {
            memset(tok->valuestring, 0, strlen(tok->valuestring));
        }
        cJSON_Delete(json);
        memset(resp, 0, sizeof(resp));
        return FP_ERR_HTTP_JSON;
    }

    err = fp_nvs_set_str(FP_NVS_DEVICE_TOKEN, tok->valuestring);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "setup accepted; device credential stored");
    }
    memset(tok->valuestring, 0, strlen(tok->valuestring));
    cJSON_Delete(json);
    memset(resp, 0, sizeof(resp));
    return err;
}

/* Ends the wake's shared connection: logs the diagnostic line the
 * hardware session uses to explain the per-cycle overhead (tls_offered/
 * tls_saved_len come from tls_session.c; both are 0/false whenever the
 * TLS-session-persistence config isn't active), then tears down the
 * handle and, since esp_http_client_cleanup() only destroys its own
 * transport_list and never a custom transport handed in via
 * config.transport (confirmed against esp_http_client.c: the custom
 * transport is kept in a separate client->transport field cleanup()
 * never frees), the custom SSL transport too. Safe to call more than
 * once or when nothing was ever opened. */
void fp_api_release(void)
{
    if (s_http) {
        ESP_LOGI(TAG,
                 "http connects=%u first_connect_ms=%u tls_offered=%d tls_saved_len=%u",
                 s_connects, (unsigned)s_first_connect_ms,
                 (int)fp_tls_session_offered(),
                 (unsigned)fp_tls_session_saved_len());
        esp_http_client_cleanup(s_http);
        s_http = NULL;
    }
    if (s_tls) {
        esp_transport_destroy(s_tls);
        s_tls = NULL;
    }
    s_origin[0] = 0;
    s_connects = 0;
    s_first_connect_ms = 0;
    s_connect_started_us = 0;
    s_tls_saved = false;
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
    esp_http_client_handle_t http;
    err = session_client(req_url, HTTP_METHOD_GET, 20000, &http);
    if (err != ESP_OK) {
        return err;
    }
    clear_request_headers(http);
    auth_header(http);
    telemetry_headers(http, boot_reason);

    char resp[RESP_MAX];
    int n = 0;
    err = small_request(http, NULL, resp, &n);
    if (err == FP_ERR_HTTP_AUTH) {
        fp_nvs_erase_key(FP_NVS_DEVICE_TOKEN);
        ESP_LOGW(TAG, "device token rejected; erased, re-enrolling on "
                      "the next wake");
        return FP_ERR_HTTP_AUTH;
    }
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

    char origin[API_BASE_MAX];
    url_origin(url, origin, sizeof(origin));
    bool shared = s_http != NULL && strcmp(origin, s_origin) == 0;

    esp_http_client_handle_t http;
    if (shared) {
        esp_err_t err = session_client(url, HTTP_METHOD_GET, 30000, &http);
        if (err != ESP_OK) {
            return err;
        }
        clear_request_headers(http); /* the image request carries none */
    } else {
        http = http_client_new(url, HTTP_METHOD_GET, 30000);
        if (!http) {
            return ESP_ERR_NO_MEM;
        }
    }

    bool retry_ok = shared && s_connects > 0;
    bool retried = false;

open_again:
    if (shared) {
        s_connect_started_us = esp_timer_get_time();
    }
    esp_err_t err = esp_http_client_open(http, 0);
    if (err != ESP_OK) {
        if (retry_ok && !retried) {
            retried = true;
            esp_http_client_close(http);
            goto open_again;
        }
        if (shared && s_connects == 0 && fp_tls_session_offered()) {
            fp_tls_session_forget();
        }
        if (!shared) {
            esp_http_client_cleanup(http);
        }
        return err;
    }
    if (esp_http_client_fetch_headers(http) < 0) {
        esp_http_client_close(http);
        if (retry_ok && !retried) {
            retried = true;
            goto open_again;
        }
        if (shared && s_connects == 0 && fp_tls_session_offered()) {
            fp_tls_session_forget();
        }
        if (!shared) {
            esp_http_client_cleanup(http);
        }
        return ESP_FAIL; /* maps to step=download */
    }
    if (shared) {
        maybe_save_tls_session();
    }

    uint32_t got = 0;
    while (got < FP_IMAGE_BYTES) {
        int n = esp_http_client_read(http, (char *)buf + got,
                                     FP_IMAGE_BYTES - got);
        /* FW-02: bounds a trickling transfer by the whole-wake budget,
         * not just this read's own per-call timeout - a download that
         * dribbles in a few bytes at a time, just under the timeout on
         * every single read, would otherwise never end. */
        fp_wake_checkpoint();
        if (n <= 0) {
            break;
        }
        got += n;
    }
    /* Anything beyond the expected size is a protocol violation. */
    char extra;
    bool oversize = esp_http_client_read(http, &extra, 1) > 0;
    int status = esp_http_client_get_status_code(http);
    if (!shared) {
        esp_http_client_cleanup(http);
    }
    /* shared: never close - this is always the wake's last request, so
     * fp_api_release() tears the connection down at the end of the wake;
     * closing it here early would discard a session tls_session.c is
     * about to spend effort saving for nothing. */

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
