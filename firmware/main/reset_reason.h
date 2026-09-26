/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Classifies why the chip last reset and turns that, plus the ESP-IDF
 * wake cause, into the Log Line Contract's honest wake-reason token.
 * Pure, no ESP-IDF, no I/O: host-compilable so the classification rules
 * are asserted on every commit instead of only observed on hardware.
 * The enum below mirrors esp_reset_reason_t (ESP-IDF v5.3.1) value-for-
 * value so this header needs no ESP-IDF include; app_main.c asserts
 * that equality at compile time, so a future ESP-IDF enum reorder fails
 * the build instead of silently misclassifying resets. */
#pragma once
#include <stdbool.h>

enum {
    FP_RST_UNKNOWN = 0,
    FP_RST_POWERON,
    FP_RST_EXT,
    FP_RST_SW,
    FP_RST_PANIC,
    FP_RST_INT_WDT,
    FP_RST_TASK_WDT,
    FP_RST_WDT,
    FP_RST_DEEPSLEEP,
    FP_RST_BROWNOUT,
    FP_RST_SDIO,
    FP_RST_USB,
    FP_RST_JTAG,
    FP_RST_EFUSE,
    FP_RST_PWR_GLITCH,
    FP_RST_CPU_LOCKUP,
};

/* Wake cause, independent of reset reason: was this wake driven by the
 * RTC timer, a button, some other ESP-IDF wake cause, or none at all
 * (this boot came from a reset, not a deep-sleep wake). */
typedef enum {
    FP_WAKE_CAUSE_NONE,
    FP_WAKE_CAUSE_TIMER,
    FP_WAKE_CAUSE_BUTTON,
    FP_WAKE_CAUSE_OTHER,
} fp_wake_cause_t;

/* True iff reason is a reset the device did not choose: a crash, either
 * watchdog, a brownout, a power glitch or a CPU lockup. Every one of
 * these means the previous wake failed to reach deep sleep on its own,
 * so the caller must treat it like a poll failure (backoff) rather than
 * poll again immediately. FP_RST_DEEPSLEEP is the healthy timer-wake
 * path and is deliberately false here - it must never trigger backoff.
 * An out-of-range value is also false: an unrecognised reason is not
 * evidence of a crash, and failing closed here would let a future
 * ESP-IDF enum addition silently force every device into backoff. */
bool fp_reset_is_abnormal(int reason);

/* Short lowercase label for `reason`, for diagnostic logging outside
 * the Log Line Contract (the contract's own wake-reason token comes
 * from fp_wake_reason_token below). "unknown" for FP_RST_UNKNOWN and
 * any out-of-range value. */
const char *fp_reset_label(int reason);

/* The Log Line Contract's `wake reason=` token: exactly one of
 * "rtc"|"power-on"|"button"|"other" (firmware/VENDOR.md). A timer or
 * button wake cause wins outright. With no wake cause, "power-on" is
 * reported only for a genuine power-on reset (FP_RST_POWERON); every
 * other reset - including every abnormal one this module classifies -
 * reports "other", so the label stops claiming "power-on" for a crash
 * or a brownout. */
const char *fp_wake_reason_token(fp_wake_cause_t cause, int reset_reason);
