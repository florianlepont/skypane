/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* SkyPane device-protocol client — trimmed from flightportrait/frame's
 * `main/api_client.c/.h` (@ ce3335fc). Upstream implements the full
 * production surface: OTA firmware offers, possession-pairing signed
 * headers, and a versioned target-blob (BYOS override) resolution chain
 * written only by provisioning flows. None of that is compiled here —
 * Phase 1's only server is the local stub in stub-server/, addressed
 * directly via the SKYPANE_API_BASE macro in the gitignored secrets.h.
 *
 * Kept: the three endpoints, all four telemetry headers, and the
 * streamed download with SHA-256 + exact-byte-count verification before
 * any buffer reaches panel.c — PROTOCOL.md §2-3 at the pinned commit.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

/* 1200*1600 pixels, two nibble-packed pixels per byte — PROTOCOL.md §1. */
#define FP_IMAGE_BYTES 960000u

/* Distinct failure classifications the Log Line Contract's step tokens
 * need (firmware/VENDOR.md § Log Line Contract, 01-05-PLAN.md Task 3):
 * api_client.c already knows exactly where a request failed, so it
 * reports that here instead of state_machine.c re-deriving it from a
 * single generic esp_err_t. Values are outside every ESP-IDF component's
 * documented error-base range — they are compared for equality only,
 * never passed to ESP_ERROR_CHECK or interpreted by IDF internals. */
#define FP_ERR_HTTP_TRANSPORT ((esp_err_t)0x00600001) /* couldn't open/connect */
#define FP_ERR_HTTP_STATUS    ((esp_err_t)0x00600002) /* non-200 response */
#define FP_ERR_HTTP_JSON      ((esp_err_t)0x00600003) /* malformed/invalid response body */
#define FP_ERR_IMAGE_VERIFY   ((esp_err_t)0x00600004) /* sha256/size mismatch on download */

typedef struct {
    char image_url[768];   /* presigned URLs are long */
    char image_hash[80];   /* "sha256:<64 hex>" */
    uint32_t sleep_s;
    bool reset;
} fp_display_t;

/* True once POST /device/v1/setup has stored a bearer token in NVS. */
bool fp_api_has_token(void);

/* POST /device/v1/setup. Stores the returned device token in NVS only
 * after validating the complete response (PROTOCOL.md §2: device_token
 * is exactly 64 lowercase hex chars). */
esp_err_t fp_api_setup(const char *provision_secret);

/* GET /device/v1/display. Sends the Authorization bearer header and all
 * four telemetry headers on every call. Rejects the whole response
 * before copying any field if image_hash, sleep_s, reset or image_url
 * fails its PROTOCOL.md §2 validation rule. */
esp_err_t fp_api_get_display(const char *boot_reason, fp_display_t *out);

/* Stream image_url into buf (FP_IMAGE_BYTES). Returns ESP_OK only when
 * the response is exactly FP_IMAGE_BYTES long AND its SHA-256 matches
 * expected_hash ("sha256:<hex>") — the gate that keeps an unverified
 * buffer from ever reaching panel.c. */
esp_err_t fp_api_download(const char *url, const char *expected_hash,
                          uint8_t *buf);

/* POST /device/v1/log with a prebuilt {"logs":[...]} body. Fire-and-
 * forget transport: the caller decides what to do (nothing) on failure. */
esp_err_t fp_api_post_logs(const char *body, const char *boot_reason);
