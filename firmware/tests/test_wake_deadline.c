/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the whole-wake deadline arithmetic (FW-02):
 * expiry at the microsecond boundary and the worst-case-wake macro.
 *
 *   cc -Wall -Wextra -std=c11 main/wake_deadline.c tests/test_wake_deadline.c \
 *      -o /tmp/twd && /tmp/twd
 */
#include <assert.h>
#include <stdio.h>

#include "../main/wake_deadline.h"

static void expiry_is_exact_at_the_microsecond_boundary(void)
{
    uint64_t start = 1000000000ULL;
    uint32_t budget_s = 300;
    uint64_t budget_us = (uint64_t)budget_s * 1000000ULL;

    assert(fp_wake_deadline_expired(start + budget_us - 1, start,
                                    budget_s) == false);
    assert(fp_wake_deadline_expired(start + budget_us, start,
                                    budget_s) == true);
}

static void a_clock_that_has_not_advanced_never_expires(void)
{
    assert(fp_wake_deadline_expired(999, 1000, 300) == false);
}

static void a_zero_budget_expires_immediately(void)
{
    /* Zero seconds allowed means no time is allowed - expired at the
     * very start point. */
    assert(fp_wake_deadline_expired(1000, 1000, 0) == true);
}

static void wake_slice_caps_at_the_max_and_passes_through_below_it(void)
{
    assert(fp_wake_slice_s(90, 20) == 20);
    assert(fp_wake_slice_s(15, 20) == 15);
    assert(fp_wake_slice_s(0, 20) == 0);
}

static void a_zero_slice_max_means_unsliced(void)
{
    assert(fp_wake_slice_s(20, 0) == 20);
}

static void worst_case_macro_matches_the_stacked_stage_budgets(void)
{
    /* 15 + 10 + 15 + 20 + 30 + 70 = 160, plus the guard wait. */
    assert(FP_WAKE_WORST_CASE_S(90) == 250);
    assert(FP_WAKE_WORST_CASE_S(0) == 160);
    /* The configured deadline (300 s, see validate.c's FP_SLEEP_S_MAX
     * neighbourhood / app_main.c's deadline constant) must exceed the
     * default-guard worst case with margin. */
    assert(300 > FP_WAKE_WORST_CASE_S(90));
}

int main(void)
{
    expiry_is_exact_at_the_microsecond_boundary();
    a_clock_that_has_not_advanced_never_expires();
    a_zero_budget_expires_immediately();
    wake_slice_caps_at_the_max_and_passes_through_below_it();
    a_zero_slice_max_means_unsliced();
    worst_case_macro_matches_the_stacked_stage_budgets();
    printf("wake_deadline: all cases pass\n");
    return 0;
}
