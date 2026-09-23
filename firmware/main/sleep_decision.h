/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* The sleep decision app_main.c's wake dispatcher makes on every wake:
 * given how the poll went, how many consecutive failures preceded it,
 * what the server asked for, and (for a deferred draw) how long the
 * panel guard still has to wait, decide how long to sleep and what the
 * next failure counter should be. Pure, no ESP-IDF, no NVS I/O: the
 * caller reads/writes FP_NVS_BACKOFF_N, this only decides the numbers
 * (FW-06).
 *
 * Division of labour: this module does not re-validate server_sleep_s's
 * upper bound - that is validate.c's fp_sleep_s_parse job, run before
 * this is ever called. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef enum {
    FP_WAKE_OUTCOME_OK,       /* poll succeeded and the panel may draw now  */
    FP_WAKE_OUTCOME_DEFERRED, /* poll succeeded but the panel guard is not clear yet */
    FP_WAKE_OUTCOME_FAILED,   /* poll failed, or the caller has already classified
                               * an abnormal reset / deadline expiry as a failure */
} fp_wake_outcome_t;

typedef struct {
    uint32_t sleep_s;        /* seconds to deep-sleep before the next wake */
    uint8_t next_backoff_n;  /* value to persist into FP_NVS_BACKOFF_N     */
    bool failed;             /* true means the caller logs the `poll fail` line */
} fp_sleep_plan_t;

/* Decides the sleep plan for one wake.
 *
 * FP_WAKE_OUTCOME_FAILED, or server_sleep_s == 0 under any outcome: a
 * zero-second timer wake would hot-loop the radio, so this is treated
 * as a failure too - exponential backoff (fp_backoff_seconds(backoff_n))
 * and the counter incremented (saturating at UINT8_MAX, never wrapping
 * back to 0).
 *
 * FP_WAKE_OUTCOME_OK with a non-zero server_sleep_s: sleep for exactly
 * server_sleep_s, reset the counter to 0.
 *
 * FP_WAKE_OUTCOME_DEFERRED with a non-zero server_sleep_s: sleep for
 * server_sleep_s, unless panel_wait_s is shorter and non-zero, in which
 * case sleep for panel_wait_s + 5 (wake again once the panel guard has
 * cleared, plus a small margin) - never longer than server_sleep_s. The
 * counter resets to 0: a deferred draw is a healthy wake, not a
 * failure. */
fp_sleep_plan_t fp_sleep_decide(fp_wake_outcome_t outcome, uint8_t backoff_n,
                                uint32_t server_sleep_s,
                                uint32_t panel_wait_s);
