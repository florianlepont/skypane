/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
/* SkyPane device-protocol client — trimmed from upstream's
 * api_client.c/.h. Upstream implements the full production surface: OTA
 * firmware offers, possession-pairing signed headers, and a versioned
 * target-blob (BYOS override) resolution chain written only by
 * provisioning flows — none of that is compiled here. This project's
 * server is addressed via SKYPANE_API_BASE (secrets.h), with the
 * per-device enrolment secret read separately (enrol_secret.h). Kept:
 * the two endpoints, all four telemetry headers, and the streamed
 * download with SHA-256 + exact-byte-count verification before any
 * buffer reaches panel.c — PROTOCOL.md §2-3. */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

/* 1200*1600 pixels, two nibble-packed pixels per byte — PROTOCOL.md §1. */
#define FP_IMAGE_BYTES 960000u

/* Distinct failure classifications the Log Line Contract's step tokens
 * need (firmware/VENDOR.md § Log Line Contract): api_client.c already
 * knows exactly where a request failed, so it reports that here instead
 * of state_machine.c re-deriving it from a single generic esp_err_t.
 * Values are outside every ESP-IDF component's documented error-base
 * range — they are compared for equality only, never passed to
 * ESP_ERROR_CHECK or interpreted by IDF internals. */
#define FP_ERR_HTTP_TRANSPORT  ((esp_err_t)0x00600001) /* couldn't open/connect */
#define FP_ERR_HTTP_STATUS     ((esp_err_t)0x00600002) /* non-200 response */
#define FP_ERR_HTTP_JSON       ((esp_err_t)0x00600003) /* malformed/invalid response body */
#define FP_ERR_IMAGE_VERIFY    ((esp_err_t)0x00600004) /* sha256/size mismatch on download */
#define FP_ERR_HTTP_AUTH       ((esp_err_t)0x00600005) /* server rejected this device's bearer token (401/403); it has been erased */
#define FP_ERR_ENROL_REJECTED  ((esp_err_t)0x00600006) /* setup refused with 401/403: secret wrong or device not registered */
#define FP_ERR_NO_SECRET       ((esp_err_t)0x00600007) /* no valid enrolment secret in the secret partition */
#define FP_ERR_CONFIG          ((esp_err_t)0x00600008) /* API base URL rejected by this build */

typedef struct {
    char image_url[768];   /* presigned URLs are long */
    char image_hash[80];   /* "sha256:<64 hex>" */
    uint32_t sleep_s;
    /* The bring-up LED toggle. The struct's one *optional* field,
     * unlike the three above it: those three are hard-required and a
     * bad value in any of them rejects the whole response, while this
     * one defaults to true whenever it is absent, null or the wrong JSON
     * type. See fp_api_get_display()'s doc comment below. */
    bool led_enabled;
} fp_display_t;

/* True once POST /device/v1/setup has stored a bearer token in NVS. */
bool fp_api_has_token(void);

/* POST /device/v1/setup, sending this device's own enrolment secret
 * (read from its dedicated NVS partition — enrol_secret.h). Stores the
 * returned device token in NVS only after validating the complete
 * response (PROTOCOL.md §2: device_token is exactly 64 lowercase hex
 * chars). Returns FP_ERR_NO_SECRET before any network activity if no
 * valid secret is present, or FP_ERR_ENROL_REJECTED if the server
 * refuses the secret with 401/403. */
esp_err_t fp_api_setup(void);

/* Releases any connection kept open between calls in this wake; safe to
 * call when none is open. */
void fp_api_release(void);

/* GET /device/v1/display. Sends the Authorization bearer header and all
 * four telemetry headers on every call. Rejects the whole response
 * before copying any field if image_hash, sleep_s or image_url fails
 * its PROTOCOL.md §2 validation rule. `led_enabled` is deliberately
 * outside that list: it is optional, and no value it can take rejects
 * the response. */
esp_err_t fp_api_get_display(const char *boot_reason, fp_display_t *out);

/* Stream image_url into buf (FP_IMAGE_BYTES). Returns ESP_OK only when
 * the response is exactly FP_IMAGE_BYTES long AND its SHA-256 matches
 * expected_hash ("sha256:<hex>") — the gate that keeps an unverified
 * buffer from ever reaching panel.c. */
esp_err_t fp_api_download(const char *url, const char *expected_hash,
                          uint8_t *buf);
