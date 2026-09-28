/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Pure C11, no ESP-IDF dependency at all (buildable and testable
 * standalone, firmware/tests/test_fault_screen.c) — see fault_screen.h
 * for the design rationale. The actual dither-and-mask-stamp rendering
 * lives in hold_screen.c, shared with updating_screen.c; this file is
 * now just the NO CONNECTION mask plus the show/suppress gate. */
#include "fault_screen.h"

#include <string.h>

#include "fault_screen_mask.h"
#include "hold_screen.h"

_Static_assert(FP_FAULT_MASK_X + FP_FAULT_MASK_W <= FP_FAULT_SCREEN_WIDTH,
               "fault screen mask exceeds screen width");
_Static_assert(FP_FAULT_MASK_Y + FP_FAULT_MASK_H <= FP_FAULT_SCREEN_HEIGHT,
               "fault screen mask exceeds screen height");

static const fp_hold_mask_t kFaultMask = {
    .x = FP_FAULT_MASK_X,
    .y = FP_FAULT_MASK_Y,
    .w = FP_FAULT_MASK_W,
    .h = FP_FAULT_MASK_H,
    .stride = FP_FAULT_MASK_STRIDE,
    .bits = fp_fault_mask_bits,
};

void fp_fault_screen_render(uint8_t *buf, fp_fault_screen_tick_fn tick)
{
    fp_hold_screen_render(buf, &kFaultMask, tick);
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
