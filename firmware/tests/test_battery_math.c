/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the one half of the battery path testable
 * without hardware: the divider-ratio conversion (DEVICE-04). The ADC
 * read itself is confirmed by Task 3's blocking human checkpoint on the
 * real board, the same way Phase 1's bring-up was.
 *
 *   cc main/battery_math.c tests/test_battery_math.c -o /tmp/tbm && /tmp/tbm
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../main/battery_math.h"

int main(void)
{
    assert(battery_math_apply_divider(0) == 0);                    /* zero edge: absent/un-enabled sense circuit reports unknown, not a fabricated voltage */
    assert(battery_math_apply_divider(1700) == 3400);              /* hardware/logtools.py --cutoff-mv "genuinely depleted" convention */
    assert(battery_math_apply_divider(1750) == 3500);              /* 05-CONTEXT.md D-01's low-battery threshold */
    assert(battery_math_apply_divider(1800) == 3600);              /* 05-UI-SPEC.md's BATTERY_LOW_CLEAR_MV re-arm point */
    assert(battery_math_apply_divider(2100) == 4200);              /* full-charge single-cell LiPo */
    assert(battery_math_apply_divider(1550) == 3100);              /* ESP32-S3's documented effective ADC ceiling */
    assert(battery_math_apply_divider(2147483647) == 4294967294u); /* largest input that still fits uint32_t after the multiply, boundary exact */
    assert(battery_math_apply_divider(2147483648u) == 4294967295u); /* saturation begins here, no wraparound */
    assert(battery_math_apply_divider(4294967295u) == 4294967295u); /* fully saturated input stays saturated */
    printf("battery_math: all cases pass\n");
    return 0;
}
