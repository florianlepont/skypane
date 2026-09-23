/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "validate.h"

#include <stdio.h>
#include <string.h>

bool fp_hex_lower_valid(const char *s, size_t expected_len)
{
    if (!s) {
        return false;
    }
    size_t len = strlen(s);
    if (len != expected_len) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        char c = s[i];
        bool lower_hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        if (!lower_hex) {
            return false;
        }
    }
    return true;
}

bool fp_image_hash_valid(const char *hash)
{
    if (!hash || strncmp(hash, "sha256:", 7) != 0) {
        return false;
    }
    return fp_hex_lower_valid(hash + 7, 64);
}

bool fp_token_valid(const char *token)
{
    return fp_hex_lower_valid(token, 64);
}

bool fp_url_scheme_allowed(const char *url, bool allow_http)
{
    if (!url) {
        return false;
    }
    if (strncmp(url, "https://", 8) == 0) {
        return true;
    }
    return allow_http && strncmp(url, "http://", 7) == 0;
}

bool fp_url_valid(const char *url, size_t cap, bool allow_http)
{
    if (!url) {
        return false;
    }
    size_t len = strlen(url);
    if (len == 0 || len >= cap) {
        return false;
    }
    if (!fp_url_scheme_allowed(url, allow_http)) {
        return false;
    }
    size_t scheme_len = strncmp(url, "https://", 8) == 0 ? 8 : 7;
    return len > scheme_len;
}

bool fp_sleep_s_parse(double value, uint32_t *out)
{
    if (value != value) {
        return false; /* NaN never equals itself */
    }
    if (value < (double)FP_SLEEP_S_MIN || value > (double)FP_SLEEP_S_MAX) {
        return false;
    }
    if (value != (double)(uint32_t)value) {
        return false; /* not an exact integer */
    }
    if (out) {
        *out = (uint32_t)value;
    }
    return true;
}

bool fp_led_enabled_resolve(bool is_bool, bool value)
{
    return !is_bool || value;
}

fp_download_verdict_t fp_download_verdict(int http_status, uint32_t got,
                                          uint32_t expected_len, bool oversize,
                                          const char *computed_hash,
                                          const char *expected_hash)
{
    if (http_status != 200 || got != expected_len || oversize) {
        return FP_DOWNLOAD_BAD_TRANSFER;
    }
    if (!computed_hash || !expected_hash) {
        return FP_DOWNLOAD_HASH_MISMATCH;
    }
    if (strcmp(computed_hash, expected_hash) != 0) {
        return FP_DOWNLOAD_HASH_MISMATCH;
    }
    return FP_DOWNLOAD_OK;
}

void fp_sha256_to_image_hash(const uint8_t digest[32],
                             char out[FP_IMAGE_HASH_BUF])
{
    memcpy(out, "sha256:", 7);
    for (int i = 0; i < 32; i++) {
        snprintf(out + 7 + i * 2, 3, "%02x", digest[i]);
    }
}

fp_http_class_t fp_http_status_classify(int status)
{
    if (status == 200) {
        return FP_HTTP_CLASS_OK;
    }
    if (status == 401 || status == 403) {
        return FP_HTTP_CLASS_AUTH;
    }
    return FP_HTTP_CLASS_OTHER;
}
