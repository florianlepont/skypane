/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* The panel's refresh-spacing arithmetic, with no ESP-IDF in it. A full
 * redraw is slow (~31.5 s measured) and costs battery, so this exists to
 * limit how often the frame redraws. Lives apart from panel.c (which
 * owns the retained state and SPI) so it can be reasoned about on a
 * host. The spacing (CONFIG_FP_MIN_REFRESH_SPACING_S) is this project's
 * own conservative margin, not a vendor threshold — the real panel
 * (Good Display GDEP133C02) documents no refresh-rate limit, only
 * "refresh at least every 24 hours or risk ghosting". */

typedef enum {
    FP_PANEL_DRAW_NOW,        /* guard clear: blit immediately         */
    FP_PANEL_DRAW_AFTER_WAIT, /* wait out the remainder, then blit     */
    FP_PANEL_DRAW_BUSY,       /* a blit is already running: do nothing */
} fp_panel_draw_plan_t;

/* What to do with an image that is ready to go on the glass.
 *
 * `wait_s` is set for FP_PANEL_DRAW_AFTER_WAIT and zeroed otherwise. Waiting
 * is bounded by `max_wait_s`: past that the answer is still AFTER_WAIT with
 * wait_s clamped, because the caller holds the image in PSRAM and PSRAM does
 * not survive deep sleep — dropping the image to sleep it out would mean
 * downloading 960 KB again for the same picture. */
fp_panel_draw_plan_t fp_panel_guard_plan(uint32_t remaining_s, bool drawing,
                                         uint32_t max_wait_s,
                                         uint32_t *wait_s);

/* Guard left after `elapsed_s` of being awake. Saturates at zero. */
uint32_t fp_panel_guard_after_awake(uint32_t remaining_s, uint32_t elapsed_s);

/* Guard left after a deep sleep.
 *
 * Only a timer wake may claim the full planned sleep: a button wake happens
 * at an unknown earlier moment, and crediting the whole planned interval
 * would let an impatient press walk the guard down to nothing — which is
 * precisely the needless-redraw churn and battery cost this module exists
 * to prevent. */
uint32_t fp_panel_guard_after_sleep(uint32_t remaining_s,
                                    uint32_t planned_sleep_s,
                                    bool timer_wake);
