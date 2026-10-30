/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the image container reader.
 *
 * The golden fixtures in tests/fixtures/image_container/ are shared with the
 * Python decoder, so both sides must classify every file identically.
 * FIXTURE_DIR names that directory (run_host_tests.sh exports it); the test
 * exits non-zero if it is unset or a fixture cannot be read.
 *
 *   cc -fsanitize=address,undefined main/image_container.c \
 *      tests/test_image_container.c -o /tmp/ti && \
 *      FIXTURE_DIR=tests/fixtures/image_container /tmp/ti
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../main/image_container.h"

#define PANEL_W 1200u
#define PANEL_H 1600u
#define FULL_PAYLOAD 960000u
#define HEADER 24u

static const char *fixture_dir;

static void die(const char *msg, const char *detail)
{
    fprintf(stderr, "test_image_container: %s%s%s\n", msg,
            detail != NULL ? ": " : "", detail != NULL ? detail : "");
    exit(1);
}

/* Exactly-sized heap copy so a sanitizer sees any read past `len`. */
static uint8_t *exact_copy(const uint8_t *src, size_t len)
{
    uint8_t *p = malloc(len > 0 ? len : 1);
    if (p == NULL) {
        die("out of memory", NULL);
    }
    if (len > 0) {
        memcpy(p, src, len);
    }
    return p;
}

static uint8_t *read_file(const char *name, size_t *len_out)
{
    char path[1024];
    if (snprintf(path, sizeof path, "%s/%s", fixture_dir, name) >=
        (int)sizeof path) {
        die("fixture path too long", name);
    }
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        die("cannot open fixture", path);
    }
    size_t cap = 4096, len = 0;
    uint8_t *buf = malloc(cap);
    if (buf == NULL) {
        die("out of memory", NULL);
    }
    for (;;) {
        if (len == cap) {
            cap *= 2;
            buf = realloc(buf, cap);
            if (buf == NULL) {
                die("out of memory", NULL);
            }
        }
        size_t n = fread(buf + len, 1, cap - len, f);
        if (n == 0) {
            break;
        }
        len += n;
    }
    fclose(f);
    uint8_t *exact = exact_copy(buf, len);
    free(buf);
    *len_out = len;
    return exact;
}

static imgc_status_t status_for_class(const char *cls)
{
    static const struct {
        const char *name;
        imgc_status_t status;
    } table[] = {
        {"ok", IMGC_OK},
        {"legacy", IMGC_LEGACY_OK},
        {"magic", IMGC_ERR_MAGIC},
        {"version", IMGC_ERR_VERSION},
        {"header_len", IMGC_ERR_HEADER_LEN},
        {"flags", IMGC_ERR_FLAGS},
        {"reserved", IMGC_ERR_RESERVED},
        {"pixel_format", IMGC_ERR_FORMAT},
        {"palette", IMGC_ERR_PALETTE},
        {"dimensions", IMGC_ERR_DIMENSIONS},
        {"length", IMGC_ERR_LENGTH},
        {"crc", IMGC_ERR_CRC},
        {"truncated", IMGC_ERR_TRUNCATED},
    };
    for (size_t i = 0; i < sizeof table / sizeof table[0]; i++) {
        if (strcmp(table[i].name, cls) == 0) {
            return table[i].status;
        }
    }
    die("unknown expected class in manifest", cls);
    return IMGC_ERR_ARG;
}

static int view_is_zero(const imgc_view_t *v)
{
    return v->payload == NULL && v->payload_len == 0 && v->palette_id == 0 &&
           !v->legacy;
}

static uint32_t manifest_hex(const char *key)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/manifest.txt", fixture_dir);
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        die("cannot open manifest", path);
    }
    char line[512], k[64];
    unsigned value;
    while (fgets(line, sizeof line, f) != NULL) {
        if (sscanf(line, "%63s %x", k, &value) == 2 && strcmp(k, key) == 0) {
            fclose(f);
            return (uint32_t)value;
        }
    }
    fclose(f);
    die("manifest key missing", key);
    return 0;
}

static void manifest_cases_match_the_declared_class(void)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/manifest.txt", fixture_dir);
    FILE *f = fopen(path, "r");
    if (f == NULL) {
        die("cannot open manifest", path);
    }
    unsigned panel_w = 0, panel_h = 0;
    int cases = 0;
    char line[512];
    while (fgets(line, sizeof line, f) != NULL) {
        char file[256], cls[64], word[64];
        unsigned palette, payload, ow, oh;
        if (line[0] == '#' || line[0] == '\n') {
            continue;
        }
        if (sscanf(line, "panel %u %u", &panel_w, &panel_h) == 2) {
            continue;
        }
        if (sscanf(line, "%255s %63s %u %u", file, cls, &palette,
                   &payload) != 4 ||
            strstr(file, ".bin") == NULL) {
            continue;
        }
        unsigned w = panel_w, h = panel_h;
        if (sscanf(line, "%*s %*s %*u %*u %63s %u %u", word, &ow, &oh) == 3 &&
            strcmp(word, "panel_override") == 0) {
            w = ow;
            h = oh;
        }
        if (w == 0 || h == 0) {
            die("manifest case before panel line", file);
        }
        size_t len;
        uint8_t *body = read_file(file, &len);
        imgc_view_t view;
        memset(&view, 0xA5, sizeof view);
        imgc_status_t got = imgc_parse(body, len, w, h, &view);
        if (got != status_for_class(cls)) {
            fprintf(stderr, "%s: expected %s got status %d\n", file, cls,
                    (int)got);
            abort();
        }
        if (got == IMGC_OK || got == IMGC_LEGACY_OK) {
            assert(view.palette_id == palette);
            assert(view.payload_len == payload);
            assert(view.legacy == (got == IMGC_LEGACY_OK));
            assert(view.payload >= body && view.payload + view.payload_len <=
                                               body + len);
        } else {
            assert(view_is_zero(&view));
        }
        free(body);
        cases++;
    }
    fclose(f);
    assert(cases >= 20);
}

static void crc32_matches_the_standard_check_value(void)
{
    const uint8_t digits[] = "123456789";
    assert(imgc_crc32(digits, 9) == 0xCBF43926u);
    assert(imgc_crc32(digits, 9) == manifest_hex("check_crc32"));
    assert(imgc_crc32(NULL, 0) == 0u);
}

static void fill_full_pattern(uint8_t *buf)
{
    static const uint8_t legal[6] = {0, 1, 2, 3, 5, 6};
    for (size_t i = 0; i < FULL_PAYLOAD; i++) {
        buf[i] = (uint8_t)((legal[(i * 5) % 6] << 4) | legal[(i * 3 + 1) % 6]);
    }
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16);
    p[3] = (uint8_t)(v >> 24);
}

static void write_header(uint8_t *h, uint32_t payload_len, uint32_t crc)
{
    memset(h, 0, HEADER);
    memcpy(h, "SPIM", 4);
    h[4] = 1;
    h[5] = HEADER;
    h[8] = (uint8_t)PANEL_W;
    h[9] = (uint8_t)(PANEL_W >> 8);
    h[10] = (uint8_t)PANEL_H;
    h[11] = (uint8_t)(PANEL_H >> 8);
    h[12] = 1;
    h[13] = 1;
    put32(h + 16, payload_len);
    put32(h + 20, crc);
}

static void full_size_legacy_and_container(void)
{
    uint8_t *pattern = malloc(FULL_PAYLOAD + 1);
    if (pattern == NULL) {
        die("out of memory", NULL);
    }
    fill_full_pattern(pattern);
    pattern[FULL_PAYLOAD] = 0;
    uint32_t crc = imgc_crc32(pattern, FULL_PAYLOAD);
    assert(crc == manifest_hex("full_size_crc32"));

    imgc_view_t v;
    uint8_t *legacy = exact_copy(pattern, FULL_PAYLOAD);
    assert(imgc_parse(legacy, FULL_PAYLOAD, PANEL_W, PANEL_H, &v) ==
           IMGC_LEGACY_OK);
    assert(v.legacy && v.payload_len == FULL_PAYLOAD && v.palette_id == 1);
    free(legacy);

    uint8_t *short_body = exact_copy(pattern, FULL_PAYLOAD - 1);
    assert(imgc_parse(short_body, FULL_PAYLOAD - 1, PANEL_W, PANEL_H, &v) ==
           IMGC_ERR_MAGIC);
    assert(view_is_zero(&v));
    free(short_body);
    uint8_t *long_body = exact_copy(pattern, FULL_PAYLOAD + 1);
    assert(imgc_parse(long_body, FULL_PAYLOAD + 1, PANEL_W, PANEL_H, &v) ==
           IMGC_ERR_MAGIC);
    assert(view_is_zero(&v));
    free(long_body);

    /* A body that starts with the magic is never the legacy form. */
    uint8_t *spim = exact_copy(pattern, FULL_PAYLOAD);
    memcpy(spim, "SPIM", 4);
    imgc_status_t st = imgc_parse(spim, FULL_PAYLOAD, PANEL_W, PANEL_H, &v);
    assert(st != IMGC_LEGACY_OK && st != IMGC_OK);
    assert(view_is_zero(&v));
    free(spim);

    uint8_t *container = malloc(HEADER + FULL_PAYLOAD);
    if (container == NULL) {
        die("out of memory", NULL);
    }
    write_header(container, FULL_PAYLOAD, crc);
    memcpy(container + HEADER, pattern, FULL_PAYLOAD);
    uint8_t *exact = exact_copy(container, HEADER + FULL_PAYLOAD);
    assert(imgc_parse(exact, HEADER + FULL_PAYLOAD, PANEL_W, PANEL_H, &v) ==
           IMGC_OK);
    assert(!v.legacy && v.payload == exact + HEADER &&
           v.payload_len == FULL_PAYLOAD);
    free(exact);
    free(container);
    free(pattern);
}

static void hostile_headers_never_read_past_the_buffer(void)
{
    imgc_view_t v;
    uint8_t good[HEADER + 4];
    memset(good, 0, sizeof good);

    /* payload_len 0xFFFFFFFF must be rejected, not wrapped around. */
    write_header(good, 0xFFFFFFFFu, 0);
    uint8_t *b = exact_copy(good, HEADER + 4);
    assert(imgc_parse(b, HEADER + 4, PANEL_W, PANEL_H, &v) == IMGC_ERR_LENGTH);
    assert(view_is_zero(&v));
    free(b);

    /* header_len beyond the buffer. */
    write_header(good, 4, 0);
    good[5] = 255;
    b = exact_copy(good, HEADER + 4);
    assert(imgc_parse(b, HEADER + 4, PANEL_W, PANEL_H, &v) ==
           IMGC_ERR_HEADER_LEN);
    assert(view_is_zero(&v));
    free(b);

    /* header_len 255 on a body that is just the fixed header. */
    b = exact_copy(good, HEADER);
    assert(imgc_parse(b, HEADER, PANEL_W, PANEL_H, &v) == IMGC_ERR_HEADER_LEN);
    free(b);

    /* header_len below the fixed size. */
    write_header(good, 4, 0);
    good[5] = 23;
    b = exact_copy(good, HEADER + 4);
    assert(imgc_parse(b, HEADER + 4, PANEL_W, PANEL_H, &v) ==
           IMGC_ERR_HEADER_LEN);
    free(b);
}

static void every_prefix_of_a_valid_fixture_is_rejected_safely(void)
{
    size_t len;
    uint8_t *full = read_file("valid_v1_8x4.bin", &len);
    for (size_t n = 0; n < len; n++) {
        uint8_t *prefix = exact_copy(full, n);
        imgc_view_t v;
        imgc_status_t st = imgc_parse(prefix, n, 8, 4, &v);
        assert(st != IMGC_OK && st != IMGC_ERR_ARG);
        if (st != IMGC_LEGACY_OK) {
            assert(view_is_zero(&v));
        }
        free(prefix);
    }
    imgc_view_t v;
    assert(imgc_parse(full, len, 8, 4, &v) == IMGC_OK);
    free(full);
}

static void odd_pixel_count_pads_one_nibble(void)
{
    uint8_t payload[11];
    for (size_t i = 0; i < sizeof payload; i++) {
        payload[i] = (uint8_t)(0x12 + i);
    }
    imgc_view_t v;
    uint8_t *legacy = exact_copy(payload, sizeof payload);
    assert(imgc_parse(legacy, sizeof payload, 7, 3, &v) == IMGC_LEGACY_OK);
    assert(v.payload_len == 11);
    free(legacy);

    uint8_t framed[HEADER + 11];
    write_header(framed, 11, imgc_crc32(payload, sizeof payload));
    framed[8] = 7;
    framed[9] = 0;
    framed[10] = 3;
    framed[11] = 0;
    memcpy(framed + HEADER, payload, sizeof payload);
    uint8_t *b = exact_copy(framed, sizeof framed);
    assert(imgc_parse(b, sizeof framed, 7, 3, &v) == IMGC_OK);
    assert(v.payload_len == 11);
    free(b);
}

static void argument_errors(void)
{
    imgc_view_t v;
    uint8_t one = 0;
    assert(imgc_parse(&one, 1, 8, 4, NULL) == IMGC_ERR_ARG);
    assert(imgc_parse(&one, 1, 0, 4, &v) == IMGC_ERR_ARG);
    assert(view_is_zero(&v));
    assert(imgc_parse(&one, 1, 8, 0, &v) == IMGC_ERR_ARG);
    assert(imgc_parse(NULL, 1, 8, 4, &v) == IMGC_ERR_ARG);
    assert(imgc_parse(NULL, 0, 8, 4, &v) == IMGC_ERR_TRUNCATED);
    assert(view_is_zero(&v));
}

int main(void)
{
    fixture_dir = getenv("FIXTURE_DIR");
    if (fixture_dir == NULL || fixture_dir[0] == '\0') {
        die("FIXTURE_DIR is not set", NULL);
    }
    manifest_cases_match_the_declared_class();
    crc32_matches_the_standard_check_value();
    full_size_legacy_and_container();
    hostile_headers_never_read_past_the_buffer();
    every_prefix_of_a_valid_fixture_is_rejected_safely();
    odd_pixel_count_pads_one_nibble();
    argument_errors();
    printf("test_image_container: all passed\n");
    return 0;
}
