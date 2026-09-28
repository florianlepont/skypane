/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the UPDATING hold screen:
 * fp_updating_screen_render()'s on-device dither + mask stamp, drawn via
 * the same shared hold_screen.c renderer the NO CONNECTION screen uses.
 *
 *   cc -Wall -Wextra -std=c11 main/updating_screen.c main/hold_screen.c \
 *      main/fault_screen.c tests/test_updating_screen.c -o /tmp/tus && /tmp/tus
 *
 * Also links main/fault_screen.c (not just hold_screen.c): one test
 * below renders NO CONNECTION for comparison, to prove the two hold
 * screens' masks are not accidentally swapped.
 */
/* HOST_TEST_DEPS: hold_screen.c fault_screen.c */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../main/fault_screen.h"
#include "../main/updating_screen.h"
#include "../main/updating_screen_mask.h"

static uint8_t *alloc_buf(void)
{
    uint8_t *buf = malloc(FP_UPDATING_SCREEN_BYTES);
    assert(buf != NULL);
    return buf;
}

static bool nibble_at(const uint8_t *buf, int row, int col)
{
    int row_bytes = FP_FAULT_SCREEN_WIDTH / 2;
    uint8_t byte = buf[(size_t)row * row_bytes + col / 2];
    uint8_t nibble = (col & 1) == 0 ? (uint8_t)(byte >> 4) : (uint8_t)(byte & 0x0F);
    return nibble == 0x1;
}

/* Mirrors hold_screen.c's own mask_bit_set(), reading directly from the
 * generated header so this test proves the render output against the
 * real committed mask, not a hand-rolled fixture. */
static bool mask_bit_set(int col, int row)
{
    int mx = col - FP_UPDATING_MASK_X;
    int my = row - FP_UPDATING_MASK_Y;
    if (mx < 0 || mx >= FP_UPDATING_MASK_W || my < 0 || my >= FP_UPDATING_MASK_H) {
        return false;
    }
    uint8_t byte = fp_updating_mask_bits[my * FP_UPDATING_MASK_STRIDE + mx / 8];
    return (byte & (0x80 >> (mx % 8))) != 0;
}

static void render_is_deterministic_and_fully_overwrites(void)
{
    uint8_t *a = alloc_buf();
    uint8_t *b = alloc_buf();
    memset(a, 0x00, FP_UPDATING_SCREEN_BYTES);
    memset(b, 0xFF, FP_UPDATING_SCREEN_BYTES);

    fp_updating_screen_render(a, NULL);
    fp_updating_screen_render(b, NULL);

    assert(memcmp(a, b, FP_UPDATING_SCREEN_BYTES) == 0);
    free(a);
    free(b);
}

static void every_nibble_is_black_or_white(void)
{
    uint8_t *buf = alloc_buf();
    memset(buf, 0xAA, FP_UPDATING_SCREEN_BYTES);
    fp_updating_screen_render(buf, NULL);

    for (size_t i = 0; i < FP_UPDATING_SCREEN_BYTES; i++) {
        uint8_t hi = (uint8_t)(buf[i] >> 4);
        uint8_t lo = (uint8_t)(buf[i] & 0x0F);
        assert(hi == 0x0 || hi == 0x1);
        assert(lo == 0x0 || lo == 0x1);
    }
    free(buf);
}

static void masked_pixels_are_always_white(void)
{
    uint8_t *buf = alloc_buf();
    fp_updating_screen_render(buf, NULL);

    for (int row = 0; row < FP_FAULT_SCREEN_HEIGHT; row++) {
        for (int col = 0; col < FP_FAULT_SCREEN_WIDTH; col++) {
            if (mask_bit_set(col, row)) {
                assert(nibble_at(buf, row, col) == true);
            }
        }
    }
    free(buf);
}

/* Proves the two hold screens actually differ - a regression that wired
 * the wrong mask into fp_updating_screen_render() (e.g. the fault mask by
 * mistake) would otherwise pass every other test in this file. */
static void updating_output_differs_from_no_connection_output(void)
{
    uint8_t *updating = alloc_buf();
    uint8_t *no_connection = malloc(FP_FAULT_SCREEN_BYTES);
    assert(no_connection != NULL);

    fp_updating_screen_render(updating, NULL);
    fp_fault_screen_render(no_connection, NULL);

    assert(memcmp(updating, no_connection, FP_UPDATING_SCREEN_BYTES) != 0);
    free(updating);
    free(no_connection);
}

static int s_tick_count;
static void count_tick(void)
{
    s_tick_count++;
}

static void tick_is_invoked_enough_times_and_null_tick_is_accepted(void)
{
    uint8_t *buf = alloc_buf();

    s_tick_count = 0;
    fp_updating_screen_render(buf, count_tick);
    assert(s_tick_count >= FP_FAULT_SCREEN_HEIGHT / 64);

    /* Must not crash with a NULL tick. */
    fp_updating_screen_render(buf, NULL);
    free(buf);
}

static void hash_sentinel_is_not_a_server_hash_shape(void)
{
    assert(strcmp(FP_UPDATING_SCREEN_HASH, "ota:updating") == 0);
    assert(strncmp(FP_UPDATING_SCREEN_HASH, "sha256:", 7) != 0);
}

int main(void)
{
    render_is_deterministic_and_fully_overwrites();
    every_nibble_is_black_or_white();
    masked_pixels_are_always_white();
    updating_output_differs_from_no_connection_output();
    tick_is_invoked_enough_times_and_null_tick_is_accepted();
    hash_sentinel_is_not_a_server_hash_shape();
    printf("test_updating_screen: all tests passed\n");
    return 0;
}
