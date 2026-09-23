/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Every open -> operate -> commit (writes only) -> close NVS sequence this
 * project needs, in one place, so api_client.c, state_machine.c and
 * enrol_secret.c stop each hand-rolling the same nvs_open()/nvs_close()
 * pairs. A handle is never left open on any path, and none of these
 * functions call ESP_ERROR_CHECK — an NVS failure degrades to an
 * esp_err_t return, never a crash. */
#pragma once

#include <stddef.h>

#include "esp_err.h"

/* Reads a string value from the FP_NVS_NAMESPACE namespace on the
 * default NVS partition. */
esp_err_t fp_nvs_get_str(const char *key, char *out, size_t cap);

/* Same read, from an explicitly named partition. partition == NULL means
 * the default partition (equivalent to fp_nvs_get_str). */
esp_err_t fp_nvs_get_str_from(const char *partition, const char *key,
                              char *out, size_t cap);

/* Writes and commits a string value in the FP_NVS_NAMESPACE namespace on
 * the default NVS partition. */
esp_err_t fp_nvs_set_str(const char *key, const char *value);

/* Erases key from the FP_NVS_NAMESPACE namespace on the default NVS
 * partition and commits. A key that is already absent
 * (ESP_ERR_NVS_NOT_FOUND) counts as success — the caller wants the key
 * gone, and it already is. */
esp_err_t fp_nvs_erase_key(const char *key);
