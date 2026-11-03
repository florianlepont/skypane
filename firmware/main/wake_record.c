/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#include "wake_record.h"

#include "esp_attr.h"

static RTC_DATA_ATTR fp_wake_record_t s_record;

void fp_wake_record_store(const fp_wake_record_t *rec)
{
    if (rec) {
        s_record = *rec;
    }
}

const fp_wake_record_t *fp_wake_record_previous(void)
{
    return &s_record;
}
