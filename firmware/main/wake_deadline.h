/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Whole-wake deadline arithmetic, kept apart from the esp_timer
 * plumbing that arms it so the arithmetic itself is host-testable. The
 * task watchdog (fed at each blocking-call boundary) is a short hang
 * detector, capped at 60 s, so it can only catch one stage wedging,
 * never bound a whole wake. This deadline is a longer, one-shot budget
 * covering every stage a legitimate wake can stack; FP_WAKE_WORST_CASE_S
 * and FP_WAKE_OTA_WORST_CASE_S compute those worst cases (a normal wake
 * and an OTA wake - alternatives, never both in the same wake) from the
 * timeouts already coded elsewhere, so the numbers cannot silently
 * drift apart. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* Per-stage budgets a single legitimate wake can stack, in seconds
 * (mirrors the timeouts coded in api_client.c/panel.c). */
#define FP_WAKE_STAGE_WIFI_S     15u /* state_machine.c fp_wifi_connect(15000) */
#define FP_WAKE_STAGE_SNTP_S     10u /* wifi.c pdMS_TO_TICKS(10000), only after a brownout */
#define FP_WAKE_STAGE_SETUP_S    15u /* api_client.c .timeout_ms = 15000, only first wake / re-enrol */
#define FP_WAKE_STAGE_DISPLAY_S  20u /* api_client.c .timeout_ms = 20000 */
#define FP_WAKE_STAGE_DOWNLOAD_S 30u /* api_client.c .timeout_ms = 30000 */
#define FP_WAKE_STAGE_BLIT_S     70u /* epd13in3e.c: send_half x2 + PON/DRF/POF busy-waits */
/* ota.c's esp_https_ota download of one full firmware image into the
 * inactive OTA slot, assuming a conservative minimum throughput of
 * about 12 KB/s over the ISRG-only certificate bundle for a ~1.05 MB
 * release image - well below the LAN/VPS path this device actually
 * uses, so the budget still has real margin at that assumed floor. */
#define FP_WAKE_STAGE_OTA_S      90u

/* Worst-case legitimate whole wake: every stage stacked, plus the
 * panel-guard spacing wait (CONFIG_FP_MAX_GUARD_WAIT_S, passed in as
 * guard_wait_s). Usable in a _Static_assert against the configured
 * deadline (app_main.c) so a shrunk deadline fails the build instead
 * of only failing on hardware. */
#define FP_WAKE_WORST_CASE_S(guard_wait_s) \
    (FP_WAKE_STAGE_WIFI_S + FP_WAKE_STAGE_SNTP_S + FP_WAKE_STAGE_SETUP_S + \
     FP_WAKE_STAGE_DISPLAY_S + FP_WAKE_STAGE_DOWNLOAD_S + \
     FP_WAKE_STAGE_BLIT_S + (guard_wait_s))

/* Worst-case legitimate OTA wake: an alternative to FP_WAKE_WORST_CASE_S
 * above, not an addition on top of it. An OTA wake either restarts into
 * the trial image or, when the attempt fails, carries on with the
 * normal poll in the same wake (so the UPDATING screen is replaced by
 * the current picture); the failing one is the longer, and is what this
 * macro stacks: Wi-Fi, SNTP, setup and display (the normal poll that
 * carried the offer), the panel-guard spacing wait, the UPDATING-screen
 * blit, a second Wi-Fi join, the firmware image download itself, and
 * then the picture download and its blit. The panel-guard spacing owed
 * before that second blit is at most CONFIG_FP_MIN_REFRESH_SPACING_S
 * (60 s by default), it starts counting when the UPDATING blit ends, and
 * FP_WAKE_STAGE_OTA_S already covers it, so it adds nothing here. A
 * failed second Wi-Fi join that is retried once is bounded by the same
 * FP_WAKE_STAGE_WIFI_S plus the (then absent) OTA stage. The configured
 * wake budget (CONFIG_SKYPANE_WAKE_BUDGET_S) must exceed both worst
 * cases - see wake_guard.c's two _Static_assert lines. */
#define FP_WAKE_OTA_WORST_CASE_S(guard_wait_s) \
    (FP_WAKE_STAGE_WIFI_S + FP_WAKE_STAGE_SNTP_S + FP_WAKE_STAGE_SETUP_S + \
     FP_WAKE_STAGE_DISPLAY_S + (guard_wait_s) + FP_WAKE_STAGE_BLIT_S + \
     FP_WAKE_STAGE_WIFI_S + FP_WAKE_STAGE_OTA_S + \
     FP_WAKE_STAGE_DOWNLOAD_S + FP_WAKE_STAGE_BLIT_S)

/* True iff now_us is at or past start_us + budget_s worth of
 * microseconds - i.e. the whole-wake budget has expired. now_us before
 * start_us (a clock that has not advanced) is never expired. A zero
 * budget expires immediately at start_us, since a zero-second budget
 * means "no time is allowed". */
bool fp_wake_deadline_expired(uint64_t now_us, uint64_t start_us,
                              uint32_t budget_s);

/* The next light-sleep slice to take out of `remaining_s`, capped at
 * `slice_max_s`, so the caller can feed the task watchdog between
 * slices instead of light-sleeping through its whole timeout in one
 * call. slice_max_s == 0 means unsliced: take the whole remainder in
 * one slice. */
uint32_t fp_wake_slice_s(uint32_t remaining_s, uint32_t slice_max_s);
