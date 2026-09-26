/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the one half of the battery path testable
 * without hardware: the divider-ratio conversion. The ADC read itself
 * is confirmed on the real board by a hardware bring-up checkpoint.
 *
 *   cc main/battery_math.c tests/test_battery_math.c -o /tmp/tbm && /tmp/tbm
 */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../main/battery_math.h"

static void average_mv_cases(void)
{
    /* Eight steady, all-valid samples: exact rounded mean, the
     * 8-sample average. */
    int steady[8] = {2000, 2002, 2004, 2006, 2008, 2010, 2012, 2014};
    assert(battery_math_average_mv(steady, 8) == 2007);

    /* Negative entries mark a failed ADC read for that sample and are
     * excluded, not averaged in as if they were real voltages. */
    int mixed[5] = {2000, -1, 2010, -1, 2020};
    assert(battery_math_average_mv(mixed, 5) == 2010); /* (2000+2010+2020)/3 */

    int all_failed[4] = {-1, -1, -1, -1};
    assert(battery_math_average_mv(all_failed, 4) == 0);

    assert(battery_math_average_mv(NULL, 8) == 0);
    assert(battery_math_average_mv(steady, 0) == 0);
}

int main(void)
{
    assert(battery_math_apply_divider(0) == 0);                    /* zero edge: absent/un-enabled sense circuit reports unknown, not a fabricated voltage */
    assert(battery_math_apply_divider(1700) == 3400);              /* hardware/logtools.py --cutoff-mv "genuinely depleted" convention */
    assert(battery_math_apply_divider(1750) == 3500);              /* the low-battery threshold */
    assert(battery_math_apply_divider(1800) == 3600);              /* BATTERY_LOW_CLEAR_MV re-arm point */
    assert(battery_math_apply_divider(2100) == 4200);              /* full-charge single-cell LiPo */
    assert(battery_math_apply_divider(1550) == 3100);              /* ESP32-S3's documented effective ADC ceiling */
    assert(battery_math_apply_divider(2147483647) == 4294967294u); /* largest input that still fits uint32_t after the multiply, boundary exact */
    assert(battery_math_apply_divider(2147483648u) == 4294967295u); /* saturation begins here, no wraparound */
    assert(battery_math_apply_divider(4294967295u) == 4294967295u); /* fully saturated input stays saturated */
    average_mv_cases();
    printf("battery_math: all cases pass\n");
    return 0;
}
