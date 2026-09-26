/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Real battery-voltage telemetry off the EE02 driver board's own factory
 * sense divider. */
#pragma once
#include <stdint.h>

/* Pack voltage in millivolts, measured once per wake as the mean of 8
 * calibrated ADC samples and cached for the remainder of the wake.
 * Call this before Wi-Fi starts: the radio's own current draw sags the
 * pack and couples noise into the ADC, so a read taken after Wi-Fi is
 * up is measuring a different (worse) condition than the pack's resting
 * voltage. Later calls in the same wake return the cached
 * value regardless of when they happen. Returns zero - PROTOCOL.md §2's
 * *unknown* sentinel - if the ADC is unavailable, every sample fails, or
 * the read otherwise fails, so a hardware fault degrades to "no battery
 * signal" rather than to a fabricated reading. The server's
 * parse_battery_mv() already rejects that sentinel, so an unknown value
 * can never arm the low-battery warning. */
uint32_t fp_battery_mv(void);
