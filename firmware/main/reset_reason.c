/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "reset_reason.h"

bool fp_reset_is_abnormal(int reason)
{
    switch (reason) {
    case FP_RST_PANIC:
    case FP_RST_INT_WDT:
    case FP_RST_TASK_WDT:
    case FP_RST_WDT:
    case FP_RST_BROWNOUT:
    case FP_RST_PWR_GLITCH:
    case FP_RST_CPU_LOCKUP:
        return true;
    default:
        return false;
    }
}

const char *fp_reset_label(int reason)
{
    switch (reason) {
    case FP_RST_POWERON:
        return "poweron";
    case FP_RST_EXT:
        return "ext";
    case FP_RST_SW:
        return "sw";
    case FP_RST_PANIC:
        return "panic";
    case FP_RST_INT_WDT:
        return "int_wdt";
    case FP_RST_TASK_WDT:
        return "task_wdt";
    case FP_RST_WDT:
        return "wdt";
    case FP_RST_DEEPSLEEP:
        return "deepsleep";
    case FP_RST_BROWNOUT:
        return "brownout";
    case FP_RST_SDIO:
        return "sdio";
    case FP_RST_USB:
        return "usb";
    case FP_RST_JTAG:
        return "jtag";
    case FP_RST_EFUSE:
        return "efuse";
    case FP_RST_PWR_GLITCH:
        return "pwr_glitch";
    case FP_RST_CPU_LOCKUP:
        return "cpu_lockup";
    default:
        return "unknown";
    }
}

const char *fp_wake_reason_token(fp_wake_cause_t cause, int reset_reason)
{
    switch (cause) {
    case FP_WAKE_CAUSE_TIMER:
        return "rtc";
    case FP_WAKE_CAUSE_BUTTON:
        return "button";
    case FP_WAKE_CAUSE_NONE:
        /* No deep-sleep wake cause: this boot came from a reset. Only a
         * genuine power-on reset may still claim the power-on token -
         * every other reset, including the abnormal ones this module
         * flags, reports other instead of lying about the cause. */
        return reset_reason == FP_RST_POWERON ? "power-on" : "other";
    case FP_WAKE_CAUSE_OTHER:
    default:
        return "other";
    }
}
