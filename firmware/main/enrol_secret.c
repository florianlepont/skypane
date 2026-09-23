/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "enrol_secret.h"

#include <string.h>

#include "nvs_flash.h"

#include "nvs_schema.h"
#include "nvs_util.h"
#include "validate.h"

esp_err_t fp_enrol_secret_load(char *out, size_t cap)
{
    if (!out || cap < 65) {
        return ESP_ERR_INVALID_ARG;
    }
    out[0] = 0;

    /* A failure here (partition missing from the flashed table, or the
     * partition itself corrupt/unformatted) is a provisioning defect,
     * not something to repair by erasing — erasing would destroy the
     * one copy of this device's secret. Reflash (flash.sh) and
     * re-provision (provision.sh) instead; the caller logs the guidance. */
    esp_err_t err = nvs_flash_init_partition(FP_NVS_SECRET_PARTITION);
    if (err != ESP_OK) {
        return err;
    }

    err = fp_nvs_get_str_from(FP_NVS_SECRET_PARTITION, FP_NVS_ENROL_SECRET,
                              out, cap);
    nvs_flash_deinit_partition(FP_NVS_SECRET_PARTITION);
    if (err != ESP_OK) {
        return err;
    }
    if (!fp_token_valid(out)) {
        memset(out, 0, cap);
        return ESP_ERR_INVALID_RESPONSE;
    }
    return ESP_OK;
}
