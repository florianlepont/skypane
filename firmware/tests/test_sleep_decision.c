/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* HOST_TEST_DEPS: backoff.c */
/* Host-side unit test for the sleep decision extracted from
 * app_main.c's wake dispatcher: backoff on failure, honour the
 * server's interval on success, shorten a deferred wait, and never let
 * a zero server sleep through as if it were a real interval.
 *
 *   cc -Wall -Wextra -std=c11 main/sleep_decision.c main/backoff.c \
 *      tests/test_sleep_decision.c -o /tmp/tsd && /tmp/tsd
 */
#include <assert.h>
#include <stdio.h>

#include "../main/sleep_decision.h"

static void failure_backs_off_from_zero(void)
{
    fp_sleep_plan_t plan = fp_sleep_decide(FP_WAKE_OUTCOME_FAILED, 0, 999,
                                           0);
    assert(plan.sleep_s == 300);       /* fp_backoff_seconds(0) = 5 min */
    assert(plan.next_backoff_n == 1);
    assert(plan.failed == true);
}

static void failure_caps_at_six_hours_and_saturates_at_uint8_max(void)
{
    fp_sleep_plan_t capped = fp_sleep_decide(FP_WAKE_OUTCOME_FAILED, 7, 0, 0);
    assert(capped.sleep_s == 21600); /* 6 h cap */
    assert(capped.next_backoff_n == 8);
    assert(capped.failed == true);

    fp_sleep_plan_t saturated =
        fp_sleep_decide(FP_WAKE_OUTCOME_FAILED, 255, 0, 0);
    assert(saturated.next_backoff_n == 255); /* never wraps to 0 */
}

static void ok_honours_the_server_interval_and_resets_the_counter(void)
{
    fp_sleep_plan_t plan = fp_sleep_decide(FP_WAKE_OUTCOME_OK, 3, 600, 0);
    assert(plan.sleep_s == 600);
    assert(plan.next_backoff_n == 0);
    assert(plan.failed == false);
}

static void a_zero_server_sleep_is_a_failure_even_on_a_healthy_outcome(void)
{
    /* Same backoff_n as the FAILED case, and it must produce the exact
     * same plan - a zero-second wake is never legitimate no matter
     * which outcome reported it. */
    fp_sleep_plan_t zero_ok = fp_sleep_decide(FP_WAKE_OUTCOME_OK, 0, 0, 0);
    assert(zero_ok.sleep_s == 300);
    assert(zero_ok.next_backoff_n == 1);
    assert(zero_ok.failed == true);
}

static void deferred_shortens_to_the_panel_wait_plus_five(void)
{
    fp_sleep_plan_t shortened =
        fp_sleep_decide(FP_WAKE_OUTCOME_DEFERRED, 2, 3600, 40);
    assert(shortened.sleep_s == 45);
    assert(shortened.next_backoff_n == 0);
    assert(shortened.failed == false);
}

static void deferred_keeps_the_server_interval_when_the_wait_is_zero(void)
{
    fp_sleep_plan_t no_wait =
        fp_sleep_decide(FP_WAKE_OUTCOME_DEFERRED, 0, 3600, 0);
    assert(no_wait.sleep_s == 3600);
}

static void deferred_keeps_the_server_interval_when_the_wait_is_not_shorter(void)
{
    fp_sleep_plan_t not_shorter =
        fp_sleep_decide(FP_WAKE_OUTCOME_DEFERRED, 0, 3600, 3600);
    assert(not_shorter.sleep_s == 3600); /* equal, not "shorter" - not adjusted */
}

int main(void)
{
    failure_backs_off_from_zero();
    failure_caps_at_six_hours_and_saturates_at_uint8_max();
    ok_honours_the_server_interval_and_resets_the_counter();
    a_zero_server_sleep_is_a_failure_even_on_a_healthy_outcome();
    deferred_shortens_to_the_panel_wait_plus_five();
    deferred_keeps_the_server_interval_when_the_wait_is_zero();
    deferred_keeps_the_server_interval_when_the_wait_is_not_shorter();
    printf("sleep_decision: all cases pass\n");
    return 0;
}
