/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the NO CONNECTION hold screen:
 * fp_fault_screen_render()'s on-device dither + mask stamp (now a thin
 * call into the shared hold_screen.c renderer), and
 * fp_fault_screen_should_draw()'s allow-list/counter/already-shown
 * gate.
 *
 *   cc -Wall -Wextra -std=c11 main/fault_screen.c main/hold_screen.c \
 *      tests/test_fault_screen.c -o /tmp/tfs && /tmp/tfs
 */
/* HOST_TEST_DEPS: hold_screen.c */
/* HOST_TEST_PROFILES: second */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../main/fault_screen.h"
#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#include "../main/fault_screen_mask_800x480.h"
#else
#include "../main/fault_screen_mask.h"
#endif

static uint8_t *alloc_buf(void)
{
    uint8_t *buf = malloc(FP_FAULT_SCREEN_BYTES);
    assert(buf != NULL);
    return buf;
}

static void every_nibble_is_black_or_white(void)
{
    uint8_t *buf = alloc_buf();
    memset(buf, 0xAA, FP_FAULT_SCREEN_BYTES);
    fp_fault_screen_render(buf, NULL);

    for (size_t i = 0; i < FP_FAULT_SCREEN_BYTES; i++) {
        uint8_t hi = (uint8_t)(buf[i] >> 4);
        uint8_t lo = (uint8_t)(buf[i] & 0x0F);
        assert(hi == 0x0 || hi == 0x1);
        assert(lo == 0x0 || lo == 0x1);
    }
    free(buf);
}

static bool nibble_at(const uint8_t *buf, int row, int col)
{
    int row_bytes = FP_FAULT_SCREEN_WIDTH / 2;
    uint8_t byte = buf[(size_t)row * row_bytes + col / 2];
    uint8_t nibble = (col & 1) == 0 ? (uint8_t)(byte >> 4) : (uint8_t)(byte & 0x0F);
    return nibble == 0x1;
}

/* Mirrors fault_screen.c's own mask_bit_set(), reading directly from the
 * generated header so this test proves the render output against the
 * real committed mask, not a hand-rolled fixture. */
static bool mask_bit_set(int col, int row)
{
    int mx = col - FP_FAULT_MASK_X;
    int my = row - FP_FAULT_MASK_Y;
    if (mx < 0 || mx >= FP_FAULT_MASK_W || my < 0 || my >= FP_FAULT_MASK_H) {
        return false;
    }
    uint8_t byte = fp_fault_mask_bits[my * FP_FAULT_MASK_STRIDE + mx / 8];
    return (byte & (0x80 >> (mx % 8))) != 0;
}

static void masked_pixels_are_always_white(void)
{
    uint8_t *buf = alloc_buf();
    fp_fault_screen_render(buf, NULL);

    for (int row = 0; row < FP_FAULT_SCREEN_HEIGHT; row++) {
        for (int col = 0; col < FP_FAULT_SCREEN_WIDTH; col++) {
            if (mask_bit_set(col, row)) {
                assert(nibble_at(buf, row, col) == true);
            }
        }
    }
    free(buf);
}

static void dither_field_is_roughly_forty_percent_white_and_black_dominant(void)
{
    uint8_t *buf = alloc_buf();
    fp_fault_screen_render(buf, NULL);

    /* Every row from five below the mask bbox to the bottom edge, all
     * columns (the mask ends at row 1395 on the 1200x1600 panel and at row
     * 451 on the 800x480 panel), so this region is pure dithered field. */
    long white = 0;
    long total = 0;
    for (int row = FP_FAULT_MASK_Y + FP_FAULT_MASK_H + 5; row < FP_FAULT_SCREEN_HEIGHT; row++) {
        for (int col = 0; col < FP_FAULT_SCREEN_WIDTH; col++) {
            if (nibble_at(buf, row, col)) {
                white++;
            }
            total++;
        }
    }
    double frac = (double)white / (double)total;
    assert(frac >= 0.37 && frac <= 0.43);

    long whole_white = 0;
    long whole_total = (long)FP_FAULT_SCREEN_WIDTH * FP_FAULT_SCREEN_HEIGHT;
    for (int row = 0; row < FP_FAULT_SCREEN_HEIGHT; row++) {
        for (int col = 0; col < FP_FAULT_SCREEN_WIDTH; col++) {
            if (nibble_at(buf, row, col)) {
                whole_white++;
            }
        }
    }
    assert(whole_white < whole_total - whole_white); /* black is dominant */
    free(buf);
}

static void render_is_deterministic_and_fully_overwrites(void)
{
    uint8_t *a = alloc_buf();
    uint8_t *b = alloc_buf();
    memset(a, 0xAA, FP_FAULT_SCREEN_BYTES);
    memset(b, 0x00, FP_FAULT_SCREEN_BYTES);

    fp_fault_screen_render(a, NULL);
    fp_fault_screen_render(b, NULL);

    assert(memcmp(a, b, FP_FAULT_SCREEN_BYTES) == 0);
    free(a);
    free(b);
}

static int s_tick_count;
static void count_tick(void)
{
    s_tick_count++;
}

static void tick_is_invoked_and_null_tick_is_accepted(void)
{
    uint8_t *buf = alloc_buf();

    s_tick_count = 0;
    fp_fault_screen_render(buf, count_tick);
    assert(s_tick_count > 0);

    /* Must not crash with a NULL tick. */
    fp_fault_screen_render(buf, NULL);
    free(buf);
}

static void should_draw_matches_the_spec_table(void)
{
    assert(fp_fault_screen_should_draw("wifi", 1, false) == false);
    assert(fp_fault_screen_should_draw("wifi", 2, false) == true);
    assert(fp_fault_screen_should_draw("wifi", UINT8_MAX, false) == true);
    assert(fp_fault_screen_should_draw("wifi", 2, true) == false);
    assert(fp_fault_screen_should_draw("blit", 2, false) == false);
    assert(fp_fault_screen_should_draw("reset", 2, false) == false);
    assert(fp_fault_screen_should_draw("deadline", 5, false) == false);
    assert(fp_fault_screen_should_draw("nvs", 5, false) == false);
    assert(fp_fault_screen_should_draw(NULL, 2, false) == false);
    assert(fp_fault_screen_should_draw("", 2, false) == false);
    assert(fp_fault_screen_should_draw("bogus", 2, false) == false);

    static const char *const kIncluded[] = {
        "wifi", "http", "status", "json", "auth",
        "enrol", "secret", "config", "download", "verify",
    };
    for (size_t i = 0; i < sizeof(kIncluded) / sizeof(kIncluded[0]); i++) {
        assert(fp_fault_screen_should_draw(kIncluded[i], 2, false) == true);
    }

    assert(fp_fault_screen_should_draw("wifi", 0, false) == false);
}

static void hash_sentinel_is_not_a_server_hash_shape(void)
{
    assert(strcmp(FP_FAULT_SCREEN_HASH, "fault:no-connection") == 0);
    assert(strncmp(FP_FAULT_SCREEN_HASH, "sha256:", 7) != 0);
}

static uint64_t fnv1a64(const uint8_t *buf, size_t len)
{
    uint64_t h = 0xcbf29ce484222325ULL;
    for (size_t i = 0; i < len; i++) {
        h ^= buf[i];
        h *= 0x100000001b3ULL;
    }
    return h;
}

/* Digest of fp_fault_screen_render()'s output with the committed mask.
 * It changes whenever the selected mask header is regenerated or the shared
 * dither + mask renderer changes; recompute it from a run in the former
 * case and investigate the renderer in the latter. The 800x480 value is
 * the FNV-1a 64 of the generator's firmware_equivalent_image("no-connection",
 * "800x480") packed two pixels per byte, left pixel in the high nibble
 * (Black 0x0, White 0x1). */
#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#define FP_FAULT_SCREEN_GOLDEN_DIGEST 0x84464bd56530b5d5ULL
#else
#define FP_FAULT_SCREEN_GOLDEN_DIGEST 0x507fb0b85c6e7b20ULL
#endif

static void screen_geometry_follows_the_selected_panel(void)
{
#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
    assert(FP_FAULT_SCREEN_WIDTH == 800 && FP_FAULT_SCREEN_HEIGHT == 480);
    assert(FP_FAULT_SCREEN_BYTES == 192000);
#else
    assert(FP_FAULT_SCREEN_WIDTH == 1200 && FP_FAULT_SCREEN_HEIGHT == 1600);
    assert(FP_FAULT_SCREEN_BYTES == 960000);
#endif
}

static void render_output_matches_golden_digest(void)
{
    uint8_t *buf = alloc_buf();
    fp_fault_screen_render(buf, NULL);
    uint64_t digest = fnv1a64(buf, FP_FAULT_SCREEN_BYTES);
    assert(digest == FP_FAULT_SCREEN_GOLDEN_DIGEST);
    free(buf);
}

int main(void)
{
    screen_geometry_follows_the_selected_panel();
    every_nibble_is_black_or_white();
    masked_pixels_are_always_white();
    dither_field_is_roughly_forty_percent_white_and_black_dominant();
    render_is_deterministic_and_fully_overwrites();
    tick_is_invoked_and_null_tick_is_accepted();
    should_draw_matches_the_spec_table();
    hash_sentinel_is_not_a_server_hash_shape();
    render_output_matches_golden_digest();
    printf("test_fault_screen: all tests passed\n");
    return 0;
}
