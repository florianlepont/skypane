/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#pragma once

/* Bring-up and reflash aid, not a shipped user-facing indicator: drives
 * the module's built-in User LED, behind the frame, only during the
 * active wake window — must be off before deep sleep, since a lit LED
 * costs orders of magnitude more current than the sleep budget. Both
 * functions are safe to call in any order and never fail visibly. Three
 * call sites exist: unconditional on at wake start, unconditional off
 * before sleep, and a third conditional-off driven by the server's
 * per-poll answer, which can only turn it off earlier, never keep it on. */

/* Lights the built-in User LED. Call as the very first statement of the
 * wake cycle, before anything that could delay a visible signal. */
void fp_led_on(void);

/* Extinguishes the built-in User LED. Correct even if fp_led_on() never
 * ran this wake (lazy pad configuration happens here too). */
void fp_led_off(void);
