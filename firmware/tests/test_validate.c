/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for every display-response validation rule and the
 * download gate (image hash, url, sleep_s, led_enabled, token, download
 * verdict). Both CONFIG_SKYPANE_ALLOW_HTTP modes are asserted in this one
 * binary, so a single run proves the validator in both the production
 * (https-only) and dev (http allowed) configurations.
 *
 *   cc -Wall -Wextra -std=c11 main/validate.c tests/test_validate.c \
 *      -o /tmp/tv && /tmp/tv
 */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "../main/validate.h"

static void hex_lower_valid_cases(void)
{
    assert(fp_hex_lower_valid("0123456789abcdef", 16) == true);
    assert(fp_hex_lower_valid("0123456789abcdeF", 17) == false); /* wrong len */
    assert(fp_hex_lower_valid("0123456789abcdeF", 16) == false); /* uppercase F */
    assert(fp_hex_lower_valid("Abcdef0123456789", 16) == false); /* uppercase A */
    assert(fp_hex_lower_valid("012345", 16) == false);           /* too short */
    assert(fp_hex_lower_valid(NULL, 16) == false);
}

static void image_hash_valid_cases(void)
{
    char hash[80] = "sha256:";
    memset(hash + 7, '0', 64);
    hash[7 + 64] = 0;
    assert(fp_image_hash_valid(hash) == true);

    char short_hash[80] = "sha256:";
    memset(short_hash + 7, '0', 63);
    short_hash[7 + 63] = 0;
    assert(fp_image_hash_valid(short_hash) == false); /* 63 hex chars */

    char long_hash[80] = "sha256:";
    memset(long_hash + 7, '0', 65);
    long_hash[7 + 65] = 0;
    assert(fp_image_hash_valid(long_hash) == false); /* 65 hex chars */

    char upper_prefix[80] = "SHA256:";
    memset(upper_prefix + 7, '0', 64);
    upper_prefix[7 + 64] = 0;
    assert(fp_image_hash_valid(upper_prefix) == false); /* "SHA256:" prefix */

    char upper_hex[80] = "sha256:";
    memset(upper_hex + 7, 'A', 64);
    upper_hex[7 + 64] = 0;
    assert(fp_image_hash_valid(upper_hex) == false); /* uppercase hex */

    assert(fp_image_hash_valid(NULL) == false);
}

static void token_valid_cases(void)
{
    char token[65];
    memset(token, '0', 64);
    token[64] = 0;
    assert(fp_token_valid(token) == true);

    token[10] = 'g';
    assert(fp_token_valid(token) == false); /* one bad char */

    assert(fp_token_valid("") == false); /* empty */
}

static void url_scheme_allowed_cases(void)
{
    /* allow_http=false: production shape, https only. */
    assert(fp_url_scheme_allowed("https://h", false) == true);
    assert(fp_url_scheme_allowed("http://h", false) == false);
    /* allow_http=true: dev-build opt-in (CONFIG_SKYPANE_ALLOW_HTTP=y). */
    assert(fp_url_scheme_allowed("http://h", true) == true);
    assert(fp_url_scheme_allowed("ftp://h", true) == false);
    assert(fp_url_scheme_allowed("HTTPS://h", false) == false); /* case-sensitive */
}

static void url_valid_cases(void)
{
    /* allow_http=false throughout this block unless noted otherwise. */
    assert(fp_url_valid(NULL, 32, false) == false);
    assert(fp_url_valid("", 32, false) == false);
    assert(fp_url_valid("https://", 32, false) == false); /* nothing after scheme */
    assert(fp_url_valid("https://h", 9, false) == false); /* length == cap */
    assert(fp_url_valid("https://h", 10, false) == true); /* length cap-1 */

    assert(fp_url_valid("http://h", 32, false) == false); /* http rejected, allow_http=false */
    assert(fp_url_valid("http://h", 32, true) == true);   /* http allowed, allow_http=true */
    assert(fp_url_valid("https://h", 32, true) == true);  /* https fine regardless of allow_http */
}

static void sleep_s_parse_cases(void)
{
    uint32_t out = 999;

    assert(fp_sleep_s_parse(1.0, &out) == true);
    assert(out == 1u);

    out = 999;
    assert(fp_sleep_s_parse(86400.0, &out) == true);
    assert(out == 86400u);

    out = 999;
    assert(fp_sleep_s_parse(86401.0, &out) == false);
    assert(out == 999u); /* untouched on rejection */

    out = 999;
    assert(fp_sleep_s_parse(0.0, &out) == false);
    assert(out == 999u);

    out = 999;
    assert(fp_sleep_s_parse(-5.0, &out) == false);
    assert(out == 999u);

    out = 999;
    assert(fp_sleep_s_parse(1.5, &out) == false);
    assert(out == 999u);

    out = 999;
    assert(fp_sleep_s_parse(4294967295.0, &out) == false); /* well past the day cap */
    assert(out == 999u);

    out = 999;
    assert(fp_sleep_s_parse(NAN, &out) == false);
    assert(out == 999u);
}

static void led_enabled_resolve_cases(void)
{
    assert(fp_led_enabled_resolve(false, false) == true); /* absent -> enabled */
    assert(fp_led_enabled_resolve(false, true) == true);  /* wrong type -> enabled */
    assert(fp_led_enabled_resolve(true, true) == true);
    assert(fp_led_enabled_resolve(true, false) == false); /* only explicit false disables */
}

static void download_verdict_cases(void)
{
    assert(fp_download_verdict(200, 100, 100, false, "h", "h") == FP_DOWNLOAD_OK);
    assert(fp_download_verdict(404, 100, 100, false, "h", "h")
           == FP_DOWNLOAD_BAD_TRANSFER);
    assert(fp_download_verdict(200, 99, 100, false, "h", "h")
           == FP_DOWNLOAD_BAD_TRANSFER); /* short transfer */
    assert(fp_download_verdict(200, 100, 100, true, "h", "h")
           == FP_DOWNLOAD_BAD_TRANSFER); /* oversize */
    assert(fp_download_verdict(200, 100, 100, false, "h", "j")
           == FP_DOWNLOAD_HASH_MISMATCH); /* hashes differ */
    assert(fp_download_verdict(200, 100, 100, false, NULL, "h")
           == FP_DOWNLOAD_HASH_MISMATCH); /* NULL computed hash fails closed */
    assert(fp_download_verdict(200, 100, 100, false, "h", NULL)
           == FP_DOWNLOAD_HASH_MISMATCH); /* NULL expected hash fails closed */
}

static void sha256_to_image_hash_cases(void)
{
    uint8_t zero_digest[32] = {0};
    char out[FP_IMAGE_HASH_BUF];
    fp_sha256_to_image_hash(zero_digest, out);
    char expected_zero[80] = "sha256:";
    memset(expected_zero + 7, '0', 64);
    expected_zero[7 + 64] = 0;
    assert(strcmp(out, expected_zero) == 0);

    uint8_t ab_digest[32];
    for (int i = 0; i < 32; i++) {
        ab_digest[i] = 0xab;
    }
    fp_sha256_to_image_hash(ab_digest, out);
    char expected_ab[80] = "sha256:";
    for (int i = 0; i < 64; i++) {
        expected_ab[7 + i] = 'a' + (i % 2); /* "abababab..." lowercase */
    }
    expected_ab[7 + 64] = 0;
    assert(strcmp(out, expected_ab) == 0);
}

int main(void)
{
    hex_lower_valid_cases();
    image_hash_valid_cases();
    token_valid_cases();
    url_scheme_allowed_cases();
    url_valid_cases();
    sleep_s_parse_cases();
    led_enabled_resolve_cases();
    download_verdict_cases();
    sha256_to_image_hash_cases();
    printf("validate: all cases pass\n");
    return 0;
}
