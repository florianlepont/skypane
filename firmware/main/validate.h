/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Every rule a display-response field or a downloaded image must satisfy
 * before it is trusted, kept apart from api_client.c so each rule is a
 * pure function: no ESP-IDF, no I/O, compiled and asserted on a host by
 * firmware/tests/test_validate.c. api_client.c calls these; it does not
 * re-derive the rules itself. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* sleep_s bounds: one day is the longest legitimate sleep a server can
 * hand out. Anything larger is a hostile or buggy response, not a value
 * to honor. */
#define FP_SLEEP_S_MIN 1u
#define FP_SLEEP_S_MAX 86400u

/* "sha256:" (7) + 64 lowercase hex chars + NUL. */
#define FP_IMAGE_HASH_BUF 72

/* True iff s is exactly expected_len lowercase hex characters (0-9, a-f).
 * NULL, wrong length, or any uppercase/non-hex byte is false. The one
 * hex-shape check every other validator in this module is built from. */
bool fp_hex_lower_valid(const char *s, size_t expected_len);

/* True iff hash is "sha256:" followed by exactly 64 lowercase hex chars. */
bool fp_image_hash_valid(const char *hash);

/* True iff token is exactly 64 lowercase hex chars (the device bearer
 * token and the enrolment secret share this shape). */
bool fp_token_valid(const char *token);

/* True iff url's scheme is allowed: "https://" always; "http://" only
 * when allow_http is set (CONFIG_SKYPANE_ALLOW_HTTP, dev builds only).
 * Case-sensitive - the server and fp_api_base_normalize both emit
 * lowercase schemes, so an uppercase scheme is never legitimate. */
bool fp_url_scheme_allowed(const char *url, bool allow_http);

/* True iff url is non-NULL, fits in cap bytes including the NUL, has an
 * allowed scheme, and has at least one byte of content after the scheme. */
bool fp_url_valid(const char *url, size_t cap, bool allow_http);

/* Parses value as sleep_s: must be an exact integer in
 * FP_SLEEP_S_MIN..FP_SLEEP_S_MAX. Rejects NaN, negatives and fractions.
 * *out is written only on success; left untouched on rejection. */
bool fp_sleep_s_parse(double value, uint32_t *out);

/* Resolves the led_enabled field. Permissive by design: an absent field
 * or a value of the wrong JSON type is not a boolean, so it resolves to
 * enabled (the LED's prior behavior); only an explicit JSON `false`
 * disables it. A debug LED's preference must never cost a rejected poll. */
bool fp_led_enabled_resolve(bool is_bool, bool value);

typedef enum {
    FP_DOWNLOAD_OK,            /* transfer and hash both check out       */
    FP_DOWNLOAD_BAD_TRANSFER,  /* wrong status, wrong length, or oversize */
    FP_DOWNLOAD_HASH_MISMATCH, /* transfer fine, sha256 does not match    */
} fp_download_verdict_t;

/* Gate for a completed image download. Checks the transfer (status,
 * exact byte count, no trailing bytes) before comparing hashes, and
 * fails closed as HASH_MISMATCH if either hash is NULL. */
fp_download_verdict_t fp_download_verdict(int http_status, uint32_t got,
                                          uint32_t expected_len, bool oversize,
                                          const char *computed_hash,
                                          const char *expected_hash);

/* Renders a 32-byte SHA-256 digest as "sha256:" + 64 lowercase hex
 * chars into out (must be at least FP_IMAGE_HASH_BUF bytes). */
void fp_sha256_to_image_hash(const uint8_t digest[32],
                             char out[FP_IMAGE_HASH_BUF]);

typedef enum {
    FP_HTTP_CLASS_OK,    /* 200                                         */
    FP_HTTP_CLASS_AUTH,  /* 401 or 403 - this device's credential is no
                          * longer accepted                             */
    FP_HTTP_CLASS_OTHER, /* any other status                            */
} fp_http_class_t;

/* Classifies an HTTP status code for the caller's retry/erase decision.
 * AUTH is its own class, distinct from every other non-200 status,
 * because only AUTH means "this credential is dead" - a 5xx or 404 says
 * nothing about the credential and must never erase it. */
fp_http_class_t fp_http_status_classify(int status);
