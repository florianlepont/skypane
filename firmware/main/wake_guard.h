/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* ESP-IDF glue for the two-mechanism wake bound (FW-02): the task
 * watchdog and the whole-wake budget timer are two separate mechanisms
 * with two separate jobs, and this module owns both so app_main.c has
 * one place to arm them and one place to feed them.
 *
 * The task watchdog (esp_task_wdt, CONFIG_ESP_TASK_WDT_TIMEOUT_S,
 * Kconfig-capped at 60 s) is a short hang detector: if the main task
 * stops calling fp_wake_feed()/fp_wake_checkpoint() for that long, it
 * panics, and the next boot's abnormal reset reason drives backoff
 * (FW-01). It cannot bound an entire wake - 60 s is not enough for a
 * legitimate blit alone.
 *
 * The wake budget (CONFIG_SKYPANE_WAKE_BUDGET_S, wake_deadline.h's
 * fp_wake_deadline_expired) bounds a wake that is still making forward
 * progress and feeding the watchdog, but has been running too long
 * end to end. On expiry, fp_wake_checkpoint() calls the registered
 * fp_wake_expired_fn, which records a failure and deep-sleeps through
 * the single exit in app_main.c - never a second, independent exit
 * path. The one-shot esp_timer that detects the expiry runs in the
 * esp_timer dispatch task's context, not the main task's, so its
 * callback body does only the minimum safe under that context: it sets
 * a flag and returns. Every side effect (logging, sleep ordering,
 * radio/panel/LED power-down) stays in the main task, driven by
 * fp_wake_checkpoint() at a point the caller has chosen because it is
 * safe to sleep there (never while the panel is powered).
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* Called when the wake budget has expired (or the checkpoint sees the
 * elapsed-time fallback trip even without the timer). Must not return -
 * the implementation (app_main.c, plan 34-08) records the failure and
 * calls the single deep-sleep exit. */
typedef void (*fp_wake_expired_fn)(void);

/* Starts the whole-wake clock: records esp_timer_get_time() as the
 * wake's start, arms a one-shot esp_timer for
 * CONFIG_SKYPANE_WAKE_BUDGET_S seconds whose callback only sets a flag
 * (no logging, no sleep, no NVS - see the header comment above), and
 * subscribes the calling task to the task watchdog via
 * esp_task_wdt_add(NULL). Call once, early in app_main(), from the task
 * that will call fp_wake_feed()/fp_wake_checkpoint() throughout the
 * wake.
 *
 * Timer creation/start or watchdog subscription failure is logged and
 * degrades rather than aborting: fp_wake_checkpoint() still compares
 * elapsed time against the budget via fp_wake_deadline_expired(), so
 * the budget itself holds even if the timer could not be armed; a
 * failed watchdog subscription just means fp_wake_feed() has nothing to
 * reset (tracked internally so it never calls esp_task_wdt_reset() from
 * an unsubscribed task, which ESP-IDF logs as an error on every call). */
void fp_wake_guard_start(fp_wake_expired_fn on_expired);

/* Resets the task watchdog if fp_wake_guard_start() subscribed the
 * calling task. Safe to call before fp_wake_guard_start() has run (unit
 * bring-up, early boot) and safe to call from inside a blit - it never
 * ends the wake by itself, unlike fp_wake_checkpoint(). Call this from
 * every bounded wait that could plausibly run past the watchdog
 * timeout: the panel busy-wait poll loop, the row-send yield, and
 * inside each light-sleep slice. */
void fp_wake_feed(void);

/* Feeds the watchdog, then - if the budget timer's flag is set, or
 * fp_wake_deadline_expired() independently confirms the budget has run
 * out - logs a warning once and calls the on_expired callback passed to
 * fp_wake_guard_start(). Call only at a point where entering deep sleep
 * is safe (never while the panel is powered - a checkpoint mid-blit
 * would tear down the panel through the wrong exit path). */
void fp_wake_checkpoint(void);

/* True once the wake budget has expired, independent of whether
 * fp_wake_checkpoint() has run yet. */
bool fp_wake_expired(void);

/* Milliseconds elapsed since fp_wake_guard_start() was called, for the
 * diagnostic wake-duration log line. */
uint32_t fp_wake_elapsed_ms(void);

/* Longest a single light-sleep slice may run before the watchdog is fed
 * again: whether the task watchdog timer keeps counting through light
 * sleep is not guaranteed by ESP-IDF, so no single sleep call may
 * approach CONFIG_ESP_TASK_WDT_TIMEOUT_S's 60 s ceiling. */
#define FP_WAKE_LIGHT_SLEEP_SLICE_S 20u

/* Sleeps `seconds` lightly (radio and panel already down at every call
 * site this is used from), in slices of at most
 * FP_WAKE_LIGHT_SLEEP_SLICE_S, feeding the task watchdog and yielding
 * to the idle task between slices. Falls back to vTaskDelay() for a
 * slice, logging once, if esp_light_sleep_start() itself errors.
 * Re-disables the timer wakeup source before returning, so the deep-
 * sleep path (app_main.c's enter_deep_sleep()) re-arms it cleanly
 * rather than inheriting a stale slice-sized timer. */
void fp_wake_light_sleep_s(uint32_t seconds);
