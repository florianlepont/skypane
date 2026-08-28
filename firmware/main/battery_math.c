/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#include "battery_math.h"

/* The EE02 driver board's own factory-populated 2:1 battery-voltage
 * divider (Seeed's EE0x reference code names the same ratio as 2.0). This
 * is an existing circuit on the board, not something this project builds
 * or adds. If the board's real ratio ever turns out to differ, retuning
 * it is a change to these two constants plus their test cases and
 * nothing else. */
#define FP_BATTERY_DIVIDER_NUM 2u
#define FP_BATTERY_DIVIDER_DEN 1u

uint32_t battery_math_apply_divider(uint32_t divider_mv)
{
    /* Saturating rather than wrapping: a wrapped product reads as an
     * implausibly small voltage and would spuriously arm the low-battery
     * warning. */
    if (divider_mv > UINT32_MAX / FP_BATTERY_DIVIDER_NUM) {
        return UINT32_MAX;
    }
    return divider_mv * FP_BATTERY_DIVIDER_NUM / FP_BATTERY_DIVIDER_DEN;
}
