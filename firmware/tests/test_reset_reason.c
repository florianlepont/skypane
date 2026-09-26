/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for reset-reason classification and the honest
 * wake-reason token.
 *
 *   cc -Wall -Wextra -std=c11 main/reset_reason.c tests/test_reset_reason.c \
 *      -o /tmp/trr && /tmp/trr
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../main/reset_reason.h"

static void abnormal_set_matches_every_crash_wdt_and_glitch_reset(void)
{
    assert(fp_reset_is_abnormal(FP_RST_PANIC));
    assert(fp_reset_is_abnormal(FP_RST_INT_WDT));
    assert(fp_reset_is_abnormal(FP_RST_TASK_WDT));
    assert(fp_reset_is_abnormal(FP_RST_WDT));
    assert(fp_reset_is_abnormal(FP_RST_BROWNOUT));
    assert(fp_reset_is_abnormal(FP_RST_PWR_GLITCH));
    assert(fp_reset_is_abnormal(FP_RST_CPU_LOCKUP));
}

static void healthy_and_deliberate_resets_are_not_abnormal(void)
{
    assert(!fp_reset_is_abnormal(FP_RST_UNKNOWN));
    assert(!fp_reset_is_abnormal(FP_RST_POWERON));
    assert(!fp_reset_is_abnormal(FP_RST_EXT));
    assert(!fp_reset_is_abnormal(FP_RST_SW));
    assert(!fp_reset_is_abnormal(FP_RST_DEEPSLEEP)); /* healthy timer path - must never trigger backoff */
    assert(!fp_reset_is_abnormal(FP_RST_SDIO));
    assert(!fp_reset_is_abnormal(FP_RST_USB));
    assert(!fp_reset_is_abnormal(FP_RST_JTAG));
}

static void out_of_range_reasons_are_never_abnormal(void)
{
    /* An unrecognised value is not evidence of a crash - failing open
     * here would let a future ESP-IDF enum addition silently force
     * every device into backoff. */
    assert(!fp_reset_is_abnormal(-1));
    assert(!fp_reset_is_abnormal(99));
}

static void reset_label_covers_every_reason_and_falls_back_to_unknown(void)
{
    assert(strcmp(fp_reset_label(FP_RST_PANIC), "panic") == 0);
    assert(strcmp(fp_reset_label(FP_RST_INT_WDT), "int_wdt") == 0);
    assert(strcmp(fp_reset_label(FP_RST_TASK_WDT), "task_wdt") == 0);
    assert(strcmp(fp_reset_label(FP_RST_WDT), "wdt") == 0);
    assert(strcmp(fp_reset_label(FP_RST_BROWNOUT), "brownout") == 0);
    assert(strcmp(fp_reset_label(FP_RST_PWR_GLITCH), "pwr_glitch") == 0);
    assert(strcmp(fp_reset_label(FP_RST_CPU_LOCKUP), "cpu_lockup") == 0);
    assert(strcmp(fp_reset_label(FP_RST_POWERON), "poweron") == 0);
    assert(strcmp(fp_reset_label(FP_RST_SW), "sw") == 0);
    assert(strcmp(fp_reset_label(FP_RST_DEEPSLEEP), "deepsleep") == 0);
    assert(strcmp(fp_reset_label(FP_RST_EXT), "ext") == 0);
    assert(strcmp(fp_reset_label(FP_RST_USB), "usb") == 0);
    assert(strcmp(fp_reset_label(FP_RST_JTAG), "jtag") == 0);
    assert(strcmp(fp_reset_label(FP_RST_SDIO), "sdio") == 0);
    assert(strcmp(fp_reset_label(FP_RST_EFUSE), "efuse") == 0);
    assert(strcmp(fp_reset_label(FP_RST_UNKNOWN), "unknown") == 0);
    assert(strcmp(fp_reset_label(99), "unknown") == 0);
}

static void wake_reason_token_matches_the_log_line_contract(void)
{
    /* A timer or button wake cause wins outright, regardless of the
     * reset reason underneath it. */
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_TIMER,
                                       FP_RST_PANIC), "rtc") == 0);
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_BUTTON,
                                       FP_RST_BROWNOUT), "button") == 0);

    /* No wake cause: only a genuine power-on reset may claim
     * "power-on". Every other reset - abnormal or not - reports
     * "other" instead of lying about the cause. */
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_NONE,
                                       FP_RST_POWERON), "power-on") == 0);
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_NONE,
                                       FP_RST_PANIC), "other") == 0);
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_NONE,
                                       FP_RST_BROWNOUT), "other") == 0);
    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_NONE,
                                       FP_RST_USB), "other") == 0);

    assert(strcmp(fp_wake_reason_token(FP_WAKE_CAUSE_OTHER,
                                       FP_RST_POWERON), "other") == 0);
}

int main(void)
{
    abnormal_set_matches_every_crash_wdt_and_glitch_reset();
    healthy_and_deliberate_resets_are_not_abnormal();
    out_of_range_reasons_are_never_abnormal();
    reset_label_covers_every_reason_and_falls_back_to_unknown();
    wake_reason_token_matches_the_log_line_contract();
    printf("reset_reason: all cases pass\n");
    return 0;
}
