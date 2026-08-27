/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Real battery-voltage telemetry off the EE02 driver board's own factory
 * sense divider (DEVICE-04). */
#pragma once
#include <stdint.h>

/* Pack voltage in millivolts, measured once per wake and cached for the
 * remainder of the wake. Returns zero - PROTOCOL.md §2's *unknown*
 * sentinel - if the ADC is unavailable or the read fails, so a hardware
 * fault degrades to "no battery signal" rather than to a fabricated
 * reading. The server's parse_battery_mv() already rejects that sentinel,
 * so an unknown value can never arm the low-battery warning. */
uint32_t fp_battery_mv(void);
