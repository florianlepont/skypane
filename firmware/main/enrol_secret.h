/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Reads the per-device enrolment secret firmware/provision.sh writes into
 * its own NVS partition over USB — the image is identical for every
 * device, so nothing here is ever compiled in. */
#pragma once

#include <stddef.h>

#include "esp_err.h"

/* Loads the enrolment secret into out (cap must be >= 65: 64 lowercase
 * hex chars + NUL). Never writes or erases the partition it reads from —
 * a device with no valid secret cannot enrol until provisioned, and the
 * application must never "repair" that by wiping the only copy. Returns
 * the underlying NVS-init/read error unchanged on failure, or
 * ESP_ERR_INVALID_RESPONSE (and zeroes out) if the stored value is not
 * 64 lowercase hex characters. Never logs the value. */
esp_err_t fp_enrol_secret_load(char *out, size_t cap);
