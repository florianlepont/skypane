/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Quick task 260924-u7n (DEVICE-06) - see fault_screen.h for the full
 * design rationale. Pure C11, no ESP-IDF dependency at all (buildable and
 * testable standalone, firmware/tests/test_fault_screen.c), so the exact
 * same dither spec firmware/tools/gen_fault_screen.py's Python port
 * implements can be verified byte-for-byte against this file on a
 * developer machine with no hardware and no IDF toolchain.
 */
#include "fault_screen.h"

#include <string.h>

#include "fault_screen_mask.h"

_Static_assert(FP_FAULT_MASK_X + FP_FAULT_MASK_W <= FP_FAULT_SCREEN_WIDTH,
               "fault screen mask exceeds screen width");
_Static_assert(FP_FAULT_MASK_Y + FP_FAULT_MASK_H <= FP_FAULT_SCREEN_HEIGHT,
               "fault screen mask exceeds screen height");

/* The dither spec's one constant target level (server/plane/dither.py's
 * own round(255 * 0.4) lighten-toward-White blend) - see fault_screen.h /
 * gen_fault_screen.py's shared docstring for the full recipe. */
#define DITHER_TARGET_LEVEL 102

/* Two error-accumulator rows, WIDTH + 2 entries each, indexed x + 1 so
 * x - 1 and x + 1 never go out of bounds. static, not stack - the
 * app_main task stack is small (12 KiB, sdkconfig.defaults) and this is
 * 2 * 1202 * 2 bytes = ~4.7 KB, comfortably too large to put on it
 * safely alongside everything else a wake's call stack already holds.
 *
 * Range check: the maximum |e| a single pixel can produce is bounded by
 * the incoming error plus the level swing. v16 = level16 + cur[x+1];
 * level16 is a small constant (102*16 = 1632) and cur[x+1] is itself a
 * diffused fraction of a previous e, so the whole recurrence stays
 * bounded by the same order of magnitude as a single quantisation step:
 * |e| <= max(level16, 255*16 - level16) plus accumulated rounding, which
 * in practice never approaches the int16_t range (+-32767) for this
 * fixed, non-adversarial target level - verified empirically by
 * test_fault_screen.c's determinism/bounds checks across the whole
 * 1200x1600 field. int16_t is kept (not int32_t) to match
 * gen_fault_screen.py's own spec exactly, byte for byte. */
static int16_t s_cur[FP_FAULT_SCREEN_WIDTH + 2];
static int16_t s_nxt[FP_FAULT_SCREEN_WIDTH + 2];

/* Truncating (toward zero) integer division by 16 - C's `/` operator on
 * a signed integer already truncates toward zero, so this is here purely
 * to name the operation and keep every call site visually identical to
 * gen_fault_screen.py's `_trunc16()` Python port of the same spec. */
static inline int16_t trunc16(int32_t numerator)
{
    return (int16_t)(numerator / 16);
}

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

void fp_fault_screen_render(uint8_t *buf, fp_fault_screen_tick_fn tick)
{
    if (!buf) {
        return;
    }

    memset(s_cur, 0, sizeof(s_cur));
    memset(s_nxt, 0, sizeof(s_nxt));

    const int32_t level16 = DITHER_TARGET_LEVEL * 16;
    const int row_bytes = FP_FAULT_SCREEN_WIDTH / 2;

    for (int row = 0; row < FP_FAULT_SCREEN_HEIGHT; row++) {
        uint8_t *row_buf = buf + (size_t)row * row_bytes;
        for (int col = 0; col < FP_FAULT_SCREEN_WIDTH; col++) {
            int32_t v16 = level16 + s_cur[col + 1];
            bool is_white = v16 >= 128 * 16;
            int32_t q16 = is_white ? (255 * 16) : 0;
            int32_t e = v16 - q16;

            int16_t s7 = trunc16(e * 7);
            int16_t s3 = trunc16(e * 3);
            int16_t s5 = trunc16(e * 5);
            int16_t s1 = (int16_t)(e - (s7 + s3 + s5));

            s_cur[col + 2] = (int16_t)(s_cur[col + 2] + s7);
            s_nxt[col] = (int16_t)(s_nxt[col] + s3);
            s_nxt[col + 1] = (int16_t)(s_nxt[col + 1] + s5);
            s_nxt[col + 2] = (int16_t)(s_nxt[col + 2] + s1);

            bool white = mask_bit_set(col, row) ? true : is_white;

            /* Pack two pixels per byte, left pixel in the high nibble
             * (PROTOCOL.md §1); White = 0x1, Black = 0x0. */
            uint8_t nibble = white ? 0x1 : 0x0;
            uint8_t *out_byte = &row_buf[col / 2];
            if ((col & 1) == 0) {
                *out_byte = (uint8_t)(nibble << 4);
            } else {
                *out_byte = (uint8_t)(*out_byte | nibble);
            }
        }

        /* Row done: next row's accumulator becomes this row's, then a
         * fresh zeroed accumulator for the row after that. */
        memcpy(s_cur, s_nxt, sizeof(s_cur));
        memset(s_nxt, 0, sizeof(s_nxt));

        if (tick && (row % 64) == 0) {
            tick();
        }
    }
}

bool fp_fault_screen_should_draw(const char *step, uint8_t next_backoff_n, bool already_shown)
{
    if (!step || step[0] == '\0' || already_shown) {
        return false;
    }
    if (next_backoff_n < FP_FAULT_SCREEN_MIN_BACKOFF_N) {
        return false;
    }
    static const char *const kAllowed[] = {
        "wifi", "http", "status", "json", "auth",
        "enrol", "secret", "config", "download", "verify",
    };
    for (size_t i = 0; i < sizeof(kAllowed) / sizeof(kAllowed[0]); i++) {
        if (strcmp(step, kAllowed[i]) == 0) {
            return true;
        }
    }
    return false;
}
