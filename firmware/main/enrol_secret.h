/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Reads the per-device enrolment secret firmware/provision.sh writes into
 * its own NVS partition over USB — the image is identical for every
 * device, so nothing here is ever compiled in. */
#pragma once

#include <stddef.h>

#include "esp_err.h"

#include "creds.h"

/* Loads the enrolment secret into out (cap must be >= 65: 64 lowercase
 * hex chars + NUL). Never writes or erases the partition it reads from —
 * a device with no valid secret cannot enrol until provisioned, and the
 * application must never "repair" that by wiping the only copy. Returns
 * the underlying NVS-init/read error unchanged on failure, or
 * ESP_ERR_INVALID_RESPONSE (and zeroes out) if the stored value is not
 * 64 lowercase hex characters. Never logs the value. */
esp_err_t fp_enrol_secret_load(char *out, size_t cap);

/* Loads every provisioned device credential (Wi-Fi SSID/password, API
 * base, optional static-IP set) from the same "secret" NVS partition as
 * fp_enrol_secret_load, written there by firmware/provision.sh — so the
 * compiled image carries no credential of its own. Returns ESP_OK
 * only once every required key is present and passes its creds.h
 * validator; any missing or invalid value zeroes *out and returns
 * FP_ERR_CONFIG (api_client.h) without ever writing to the partition.
 * The static-IP set is all-or-nothing: if none of its four keys are
 * present, out->has_static is false and ip/mask/gw/dns stay empty; if
 * any one of the four is present, all four must be present and valid.
 * Never logs a credential value — only which key was missing or
 * invalid. */
esp_err_t fp_device_creds_load(fp_device_creds_t *out);
