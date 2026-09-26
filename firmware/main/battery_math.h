/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Pure divider-ratio conversion for the EE02 driver board's onboard
 * battery-voltage sense circuit. Host-compilable, standard headers
 * only. */
#pragma once
#include <stddef.h>
#include <stdint.h>

/* divider_mv: what the calibrated ADC measured at the sense pin, i.e. the
 * pack voltage AFTER the EE02 board's onboard divider has halved it.
 * Returns the real pack millivolts (saturates to UINT32_MAX rather than
 * wrapping on overflow). */
uint32_t battery_math_apply_divider(uint32_t divider_mv);

/* Mean of the non-negative entries in samples[0..n), rounded to nearest.
 * A negative entry marks a failed ADC read
 * for that sample and is excluded rather than dragging the average
 * toward zero. Returns 0 if samples is NULL, n is 0, or every entry is
 * negative - the same "0 means unknown" sentinel the divider path
 * already uses, so a caller with no valid sample never reports a
 * fabricated voltage. */
uint32_t battery_math_average_mv(const int *samples, size_t n);
