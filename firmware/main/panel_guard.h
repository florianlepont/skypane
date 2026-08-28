/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* The panel's refresh-spacing arithmetic, with no ESP-IDF in it.
 *
 * A full redraw is slow and visible (measured ~31.5 s) and it costs
 * battery, so this module exists to stop the frame redrawing more often
 * than it is worth redrawing. It lives apart from panel.c so it can be
 * reasoned about and tested on a host: panel.c owns the retained state
 * and the SPI, this owns the decisions.
 *
 * The spacing is a build option (CONFIG_FP_MIN_REFRESH_SPACING_S) - see
 * its help text for the full reasoning and the source citation. Short
 * version: the real panel is the Good Display GDEP133C02 (the part
 * behind Seeed SKU E-6569, the panel in the EE02 kit); its datasheet
 * documents no maximum refresh rate and no cycle-count endurance
 * rating, and its only refresh-frequency guidance points the other
 * way - refresh at least every 24 hours or risk ghosting or image sticking.
 * That is an absence in the document consulted, not proof
 * the glass never degrades. The spacing here is this project's own
 * conservative margin against needless redraws and the battery they
 * spend, not a vendor-mandated threshold.
 */

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
