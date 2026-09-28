/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#include "ota.h"

#include <string.h>

#include "esp_app_desc.h"
#include "esp_crt_bundle.h"
#include "esp_https_ota.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "mbedtls/sha256.h"
#include "sdkconfig.h"

#include "nvs_schema.h"
#include "nvs_util.h"
#include "validate.h"
#include "wake_guard.h"

static const char *TAG = "fp_ota";

/* Read-back hash chunk size: a compromise between call overhead (one
 * esp_partition_read() per chunk) and stack usage - matches the 4 KiB
 * sector size esp_https_ota itself erases in, so a chunk never spans a
 * write boundary the flash driver cares about. */
#define HASH_CHUNK_BYTES 4096u

const char *fp_ota_running_version(void)
{
    return esp_app_get_description()->version;
}

esp_err_t fp_ota_apply(const fp_fw_offer_t *offer, fp_ota_result_t *fail_out)
{
    if (!fail_out) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!offer || !offer->present) {
        *fail_out = FP_OTA_RESULT_FAIL_DOWNLOAD;
        return ESP_ERR_INVALID_ARG;
    }

    esp_http_client_config_t http_config = {
        .url = offer->url,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 30000,
        .keep_alive_enable = true,
    };
    esp_https_ota_config_t ota_config = {
        .http_config = &http_config,
    };

    esp_https_ota_handle_t handle = NULL;
    esp_err_t err = esp_https_ota_begin(&ota_config, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ota step=begin result=fail err=%s", esp_err_to_name(err));
        *fail_out = FP_OTA_RESULT_FAIL_DOWNLOAD;
        return err;
    }
    ESP_LOGI(TAG, "ota step=begin result=ok");

    /* The signed descriptor's own project/version, checked against the
     * offer and the compiled-in floor before a single byte is written -
     * a compromised server cannot bypass the floor by lying only in the
     * offer, since this check re-derives both from the image itself. */
    esp_app_desc_t desc;
    err = esp_https_ota_get_img_desc(handle, &desc);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ota step=desc result=fail err=%s", esp_err_to_name(err));
        *fail_out = FP_OTA_RESULT_FAIL_DOWNLOAD;
        esp_https_ota_abort(handle);
        return err;
    }
    fp_ota_image_verdict_t verdict = fp_ota_image_check(
        desc.project_name, desc.version, offer->version,
        CONFIG_SKYPANE_OTA_FLOOR_VERSION);
    if (verdict != FP_OTA_IMAGE_OK) {
        ESP_LOGW(TAG, "ota step=desc result=fail err=%s",
                 verdict == FP_OTA_IMAGE_BELOW_FLOOR ? "below_floor" : "mismatch");
        *fail_out = verdict == FP_OTA_IMAGE_BELOW_FLOOR
            ? FP_OTA_RESULT_FAIL_FLOOR : FP_OTA_RESULT_FAIL_IMAGE;
        esp_https_ota_abort(handle);
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "ota step=desc result=ok");

    /* Bounded by the whole-wake budget, not any single read's own
     * timeout - a download that dribbles in just under the per-read
     * timeout on every call would otherwise never end. On budget
     * expiry the wake ends through the single deep-sleep exit; the
     * trial version already recorded by fp_ota_mark_try() makes the
     * next boot report this attempt as interrupted. */
    do {
        err = esp_https_ota_perform(handle);
        fp_wake_checkpoint();
    } while (err == ESP_ERR_HTTPS_OTA_IN_PROGRESS);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ota step=download result=fail err=%s", esp_err_to_name(err));
        *fail_out = FP_OTA_RESULT_FAIL_DOWNLOAD;
        esp_https_ota_abort(handle);
        return err;
    }
    if (!esp_https_ota_is_complete_data_received(handle) ||
        (uint32_t)esp_https_ota_get_image_len_read(handle) != offer->size) {
        ESP_LOGW(TAG, "ota step=size result=fail");
        *fail_out = FP_OTA_RESULT_FAIL_SIZE;
        esp_https_ota_abort(handle);
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "ota step=download result=ok");

    /* Read back exactly what esp_https_ota just wrote to the inactive
     * slot and hash it, before any boot-partition switch - the cheaper
     * of the two authenticity gates runs first, ahead of the
     * signature check finish() performs below. */
    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    esp_err_t hash_err = update_partition ? ESP_OK : ESP_ERR_NOT_FOUND;
    uint8_t digest[32] = {0};
    if (update_partition) {
        mbedtls_sha256_context sha_ctx;
        mbedtls_sha256_init(&sha_ctx);
        mbedtls_sha256_starts(&sha_ctx, 0);
        uint8_t chunk[HASH_CHUNK_BYTES];
        uint32_t offset = 0;
        while (offset < offer->size) {
            uint32_t take = offer->size - offset;
            if (take > sizeof(chunk)) {
                take = sizeof(chunk);
            }
            hash_err = esp_partition_read(update_partition, offset, chunk, take);
            if (hash_err != ESP_OK) {
                break;
            }
            mbedtls_sha256_update(&sha_ctx, chunk, take);
            offset += take;
            fp_wake_checkpoint();
        }
        mbedtls_sha256_finish(&sha_ctx, digest);
        mbedtls_sha256_free(&sha_ctx);
        memset(chunk, 0, sizeof(chunk));
    }
    char hex[FP_IMAGE_HASH_BUF] = "";
    bool hash_ok = hash_err == ESP_OK;
    if (hash_ok) {
        fp_sha256_to_image_hash(digest, hex);
        hash_ok = strcmp(hex, offer->sha256) == 0;
    }
    if (!hash_ok) {
        ESP_LOGW(TAG, "ota step=hash result=fail err=%s",
                 hash_err == ESP_OK ? "mismatch" : esp_err_to_name(hash_err));
        *fail_out = FP_OTA_RESULT_FAIL_HASH;
        esp_https_ota_abort(handle);
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "ota step=hash result=ok");

    /* The single commit point: esp_ota_end() plus the boot-partition
     * switch happen inside this one call. Only ESP_OK here means the
     * signature verified and the switch happened - every earlier check
     * above may only abort, never switch. */
    err = esp_https_ota_finish(handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ota step=finish result=fail err=%s", esp_err_to_name(err));
        *fail_out = err == ESP_ERR_OTA_VALIDATE_FAILED
            ? FP_OTA_RESULT_FAIL_IMAGE : FP_OTA_RESULT_FAIL_DOWNLOAD;
        return err;
    }
    ESP_LOGI(TAG, "ota step=finish result=ok");
    return ESP_OK;
}

void fp_ota_record_result(fp_ota_result_t r, const char *version)
{
    char formatted[FP_OTA_RESULT_BUF];
    if (!fp_ota_result_format(formatted, sizeof(formatted), r, version)) {
        ESP_LOGW(TAG, "ota result not recorded: version does not fit/validate");
        return;
    }
    fp_nvs_set_str(FP_NVS_OTA_RESULT, formatted);
}

void fp_ota_mark_try(const char *version)
{
    if (version) {
        fp_nvs_set_str(FP_NVS_OTA_TRY, version);
    }
}

bool fp_ota_result_pending(char *out, size_t cap)
{
    if (!out || !cap) {
        return false;
    }
    return fp_nvs_get_str(FP_NVS_OTA_RESULT, out, cap) == ESP_OK;
}

void fp_ota_result_clear(void)
{
    fp_nvs_erase_key(FP_NVS_OTA_RESULT);
}

bool fp_ota_trial_pending(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t state = ESP_OTA_IMG_VALID;
    return running != NULL &&
        esp_ota_get_state_partition(running, &state) == ESP_OK &&
        state == ESP_OTA_IMG_PENDING_VERIFY;
}

void fp_ota_boot_check(void)
{
    char ota_try[FP_FW_VERSION_BUF] = "";
    fp_nvs_get_str(FP_NVS_OTA_TRY, ota_try, sizeof(ota_try));

    const esp_partition_t *invalid = esp_ota_get_last_invalid_partition();
    char last_invalid_version[FP_FW_VERSION_BUF] = "";
    if (invalid) {
        esp_app_desc_t invalid_desc;
        if (esp_ota_get_partition_description(invalid, &invalid_desc) == ESP_OK) {
            strlcpy(last_invalid_version, invalid_desc.version,
                    sizeof(last_invalid_version));
        }
    }

    fp_ota_boot_outcome_t outcome = fp_ota_boot_classify(
        ota_try[0] ? ota_try : NULL, fp_ota_running_version(),
        fp_ota_trial_pending(),
        last_invalid_version[0] ? last_invalid_version : NULL);

    const char *outcome_name = "none";
    switch (outcome) {
    case FP_OTA_BOOT_TRIAL:
        /* Kept until fp_ota_confirm_if_pending() confirms it later this
         * same wake - erasing it here would lose the version to report
         * if this wake's poll then fails before confirming. */
        outcome_name = "trial";
        fp_ota_record_result(FP_OTA_RESULT_TRIAL, ota_try);
        break;
    case FP_OTA_BOOT_INSTALLED:
        /* The confirm itself already happened on some earlier wake (the
         * running image is no longer pending verification), but that
         * confirm's own INSTALLED result never reached the server -
         * catch up on it now rather than silently dropping it (see
         * ota_policy.h's FP_OTA_BOOT_INSTALLED doc). */
        outcome_name = "installed";
        fp_ota_record_result(FP_OTA_RESULT_INSTALLED, ota_try);
        fp_nvs_erase_key(FP_NVS_OTA_TRY);
        break;
    case FP_OTA_BOOT_ROLLED_BACK:
        outcome_name = "rollback";
        fp_ota_record_result(FP_OTA_RESULT_ROLLBACK, ota_try);
        fp_nvs_erase_key(FP_NVS_OTA_TRY);
        break;
    case FP_OTA_BOOT_INTERRUPTED:
        outcome_name = "interrupted";
        fp_ota_record_result(FP_OTA_RESULT_FAIL_INTERRUPTED, ota_try);
        fp_nvs_erase_key(FP_NVS_OTA_TRY);
        break;
    case FP_OTA_BOOT_NONE:
    default:
        if (ota_try[0]) {
            fp_nvs_erase_key(FP_NVS_OTA_TRY);
        }
        break;
    }
    ESP_LOGI(TAG, "ota boot outcome=%s", outcome_name);
}

void fp_ota_confirm_if_pending(void)
{
    /* Called only on the path where this wake's poll has already
     * succeeded (see this file's header comment and ota.h) - poll_ok is
     * therefore always true here; the false branch of
     * fp_ota_should_confirm() is exercised only by its own host test. */
    if (!fp_ota_should_confirm(fp_ota_trial_pending(), true)) {
        return;
    }
    esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "ota confirm failed err=%s", esp_err_to_name(err));
        return;
    }
    const char *running = fp_ota_running_version();
    fp_ota_record_result(FP_OTA_RESULT_INSTALLED, running);
    fp_nvs_erase_key(FP_NVS_OTA_TRY);
    ESP_LOGI(TAG, "ota confirmed version=%s", running);
}
