/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "nvs_util.h"

#include "nvs.h"

#include "nvs_schema.h"

static esp_err_t open_handle(const char *partition, nvs_open_mode_t mode,
                             nvs_handle_t *out)
{
    if (partition) {
        return nvs_open_from_partition(partition, FP_NVS_NAMESPACE, mode, out);
    }
    return nvs_open(FP_NVS_NAMESPACE, mode, out);
}

esp_err_t fp_nvs_get_str(const char *key, char *out, size_t cap)
{
    return fp_nvs_get_str_from(NULL, key, out, cap);
}

esp_err_t fp_nvs_get_str_from(const char *partition, const char *key,
                              char *out, size_t cap)
{
    nvs_handle_t nvs;
    esp_err_t err = open_handle(partition, NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    size_t len = cap;
    err = nvs_get_str(nvs, key, out, &len);
    nvs_close(nvs);
    return err;
}

esp_err_t fp_nvs_set_str(const char *key, const char *value)
{
    nvs_handle_t nvs;
    esp_err_t err = open_handle(NULL, NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_set_str(nvs, key, value);
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}

esp_err_t fp_nvs_erase_key(const char *key)
{
    nvs_handle_t nvs;
    esp_err_t err = open_handle(NULL, NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_erase_key(nvs, key);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        err = ESP_OK; /* already absent is the caller's desired end state */
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}
