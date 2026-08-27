/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Pure divider-ratio conversion for the EE02 driver board's onboard
 * battery-voltage sense circuit (DEVICE-04). Host-compilable, standard
 * headers only. */
#pragma once
#include <stdint.h>

/* divider_mv: what the calibrated ADC measured at the sense pin, i.e. the
 * pack voltage AFTER the EE02 board's onboard divider has halved it.
 * Returns the real pack millivolts (saturates to UINT32_MAX rather than
 * wrapping on overflow). */
uint32_t battery_math_apply_divider(uint32_t divider_mv);
