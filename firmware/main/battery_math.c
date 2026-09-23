/* SPDX-FileCopyrightText: 2026 Florian Lepont
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

uint32_t battery_math_average_mv(const int *samples, size_t n)
{
    if (samples == NULL || n == 0) {
        return 0;
    }
    /* uint64_t accumulation: eight samples of at most a few thousand mV
     * each cannot overflow, but the wider type costs nothing and keeps
     * this correct if the sample count ever grows. */
    uint64_t sum = 0;
    size_t valid = 0;
    for (size_t i = 0; i < n; ++i) {
        if (samples[i] >= 0) {
            sum += (uint64_t)samples[i];
            valid++;
        }
    }
    if (valid == 0) {
        return 0;
    }
    /* Round to nearest rather than truncate: +valid/2 before the
     * integer divide. */
    return (uint32_t)((sum + valid / 2) / valid);
}
