/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "wake_deadline.h"

bool fp_wake_deadline_expired(uint64_t now_us, uint64_t start_us,
                              uint32_t budget_s)
{
    if (now_us < start_us) {
        /* A clock that has not advanced past the start point cannot
         * have used up the budget. */
        return false;
    }
    uint64_t budget_us = (uint64_t)budget_s * 1000000ULL;
    return (now_us - start_us) >= budget_us;
}

uint32_t fp_wake_slice_s(uint32_t remaining_s, uint32_t slice_max_s)
{
    if (slice_max_s == 0) {
        /* Unsliced: the caller wants the whole remainder in one wait. */
        return remaining_s;
    }
    return remaining_s < slice_max_s ? remaining_s : slice_max_s;
}
