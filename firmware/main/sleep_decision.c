/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "sleep_decision.h"

#include "backoff.h"

fp_sleep_plan_t fp_sleep_decide(fp_wake_outcome_t outcome, uint8_t backoff_n,
                                uint32_t server_sleep_s,
                                uint32_t panel_wait_s)
{
    fp_sleep_plan_t plan;

    /* A zero server sleep would arm a zero-second timer and hot-loop
     * the radio, so it is a failure regardless of which outcome
     * reported it. */
    bool treat_as_failure =
        outcome == FP_WAKE_OUTCOME_FAILED || server_sleep_s == 0;

    if (treat_as_failure) {
        plan.sleep_s = fp_backoff_seconds(backoff_n);
        plan.next_backoff_n =
            backoff_n < UINT8_MAX ? (uint8_t)(backoff_n + 1) : UINT8_MAX;
        plan.failed = true;
        return plan;
    }

    plan.next_backoff_n = 0;
    plan.failed = false;
    plan.sleep_s = server_sleep_s;

    if (outcome == FP_WAKE_OUTCOME_DEFERRED && panel_wait_s != 0 &&
        panel_wait_s < plan.sleep_s) {
        /* The image is already fetched; wake again once the panel
         * guard clears rather than waiting out the full server
         * interval, so a healthy frame does not appear to stall. */
        plan.sleep_s = panel_wait_s + 5;
    }

    return plan;
}
