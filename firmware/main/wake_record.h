/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#pragma once

#include "wake_telemetry.h"

/* Owner of the previous-wake record kept in RTC memory (it survives deep
 * sleep, never touches flash). RTC memory is cleared on power loss and
 * reinitialised by esp_restart(), so a reader must run the record through
 * fp_wake_record_valid() before using it. */

/* Overwrites the record. Called only from the single deep-sleep exit. */
void fp_wake_record_store(const fp_wake_record_t *rec);

/* The record the previous wake stored. Never NULL; it may be zeroed,
 * stale or corrupt, so check fp_wake_record_valid() before use. */
const fp_wake_record_t *fp_wake_record_previous(void);
