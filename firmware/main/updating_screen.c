/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Pure C11, no ESP-IDF dependency at all (buildable and testable
 * standalone, firmware/tests/test_updating_screen.c) — see
 * updating_screen.h for the design rationale. The actual dither-and-
 * mask-stamp rendering lives in hold_screen.c, shared with
 * fault_screen.c; this file is just the UPDATING mask. */
#include "updating_screen.h"

#include "updating_screen_mask.h"

_Static_assert(FP_UPDATING_MASK_X + FP_UPDATING_MASK_W <= FP_FAULT_SCREEN_WIDTH,
               "updating screen mask exceeds screen width");
_Static_assert(FP_UPDATING_MASK_Y + FP_UPDATING_MASK_H <= FP_FAULT_SCREEN_HEIGHT,
               "updating screen mask exceeds screen height");

static const fp_hold_mask_t kUpdatingMask = {
    .x = FP_UPDATING_MASK_X,
    .y = FP_UPDATING_MASK_Y,
    .w = FP_UPDATING_MASK_W,
    .h = FP_UPDATING_MASK_H,
    .stride = FP_UPDATING_MASK_STRIDE,
    .bits = fp_updating_mask_bits,
};

void fp_updating_screen_render(uint8_t *buf, fp_hold_screen_tick_fn tick)
{
    fp_hold_screen_render(buf, &kUpdatingMask, tick);
}
