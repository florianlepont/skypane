/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#pragma once

/* Bring-up and reflash aid, not a shipped user-facing indicator
 * (REQUIREMENTS.md's "Status LEDs" exclusion is about a permanently
 * wall-visible indicator; this module drives the module's own built-in
 * User LED, physically behind the frame, only during the active wake
 * window).
 *
 * This must be lit ONLY inside the active wake window and never through
 * deep sleep: a lit LED draws single-digit-to-tens of mA against a
 * tens-of-µA deep-sleep budget, so leaving it energised through sleep
 * would cost DEVICE-05 an order of magnitude of battery life. Both
 * functions below are safe to call in any order and never fail visibly
 * to the caller - a bring-up aid must never be able to take the device
 * down.
 *
 * Three call sites exist across this project, and their conditionality
 * differs - the asymmetry a future editor is most likely to flatten by
 * accident:
 *   - `app_main()`'s first statement calls fp_led_on() unconditionally.
 *   - `enter_deep_sleep()` (app_main.c's single, noreturn exit) calls
 *     fp_led_off() unconditionally, immediately before sleep - a
 *     battery-life invariant, not a preference.
 *   - `state_machine.c`'s fp_poll_once() calls fp_led_off() a third time,
 *     conditionally on the server's per-poll `led_enabled` answer. That
 *     path may only ever turn the LED off EARLIER than it would
 *     otherwise go off - it can never keep it on, and nothing it returns
 *     reaches the pre-sleep call above.
 */

/* Lights the built-in User LED. Call as the very first statement of the
 * wake cycle, before anything that could delay a visible signal. */
void fp_led_on(void);

/* Extinguishes the built-in User LED. Correct even if fp_led_on() never
 * ran this wake (lazy pad configuration happens here too). */
void fp_led_off(void);
