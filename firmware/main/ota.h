/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. Upstream's own
 * ota.c/.h (removed when this project's firmware was first vendored,
 * see VENDOR.md) established the call-site ordering this file
 * re-derives — apply before the hash-skip check, confirm-before-deep-sleep
 * on the very next wake, never deferred — and this file keeps that
 * ordering, but replaces upstream's hand-rolled esp_http_client_read
 * loop with esp_https_ota, and adds the signed-app verification
 * (firmware/SIGNING.md) upstream never had. */
/* The device-side OTA glue: downloads and verifies an offered release,
 * classifies what happened across a trial-boot restart, and confirms a
 * pending trial as valid. Every actual decision (should this offer
 * start, is a downloaded image the right one, what does a restart
 * after a trial mean, should the running image be confirmed, what
 * result token to report) lives in ota_policy.c — this file is glue
 * over esp_https_ota/esp_ota_ops plus the read-back hash check, it does
 * not re-derive any of those rules itself. state_machine.c/app_main.c
 * (a later plan) call these; this file makes no wake-loop decisions of
 * its own about when to call them. */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#include "api_client.h"  /* fp_fw_offer_t */
#include "ota_policy.h"  /* fp_ota_result_t */

/* The running image's version, straight from esp_app_get_description() -
 * the same string api_client.c already sends as X-Fw-Version. */
const char *fp_ota_running_version(void);

/* Downloads, verifies and switches to the offered release. On ESP_OK the
 * boot partition has been switched to the new image and the caller must
 * call esp_restart() to boot it - nothing here restarts on its own.
 * On any other return, *fail_out explains why and nothing was written
 * to the boot partition: the running image is untouched and this wake
 * continues normally. offer must be a present, already-decided offer
 * (fp_ota_decide() returned START) - this function does not re-check
 * the battery or same-version rules, only the downloaded image's own
 * authenticity (descriptor, size, hash, signature). NULL offer/fail_out
 * or offer->present == false is treated as FAIL_DOWNLOAD without
 * attempting a request. */
esp_err_t fp_ota_apply(const fp_fw_offer_t *offer, fp_ota_result_t *fail_out);

/* Classifies what happened across a restart (fp_ota_boot_classify,
 * against FP_NVS_OTA_TRY and the bootloader's own rollback state),
 * records the outcome as the next X-Ota-Result (fp_ota_record_result),
 * and erases FP_NVS_OTA_TRY once that outcome has been recorded - except
 * for a fresh trial, which keeps FP_NVS_OTA_TRY set until
 * fp_ota_confirm_if_pending() confirms it later this same wake. Call
 * once per wake, right after NVS init, before anything else touches
 * FP_NVS_OTA_TRY or the running partition's pending-verify state. */
void fp_ota_boot_check(void);

/* True iff the running image is still ESP_OTA_IMG_PENDING_VERIFY - a
 * fresh trial boot that has not yet been confirmed valid or rolled
 * back. */
bool fp_ota_trial_pending(void);

/* The rollback-safety call site (see this file's own header comment):
 * marks the running image valid, cancelling the bootloader's rollback,
 * only when it is still pending verification. Must run after this
 * wake's poll has already succeeded and before this same wake's deep
 * sleep - never deferred to a later wake, or a healthy update is rolled
 * back by the bootloader the very next time this device wakes from
 * deep sleep, re-entering the bootloader's own pending-verify check. A
 * no-op, cheap enough to call unconditionally, when there is nothing
 * pending. */
void fp_ota_confirm_if_pending(void);

/* Records "<token>;<version>" (fp_ota_result_format) as the OTA outcome
 * still waiting to be reported, overwriting any earlier unreported one -
 * only the latest outcome matters to the server, which counts attempts
 * from its own event log, not from this string. A version that fails
 * fp_fw_version_valid is logged and not recorded, rather than sending a
 * malformed header. */
void fp_ota_record_result(fp_ota_result_t r, const char *version);

/* Records version as the trial currently being attempted (FP_NVS_OTA_TRY),
 * to be read back by fp_ota_boot_check() after the restart fp_ota_apply()
 * leads to. Call this before esp_restart(), once fp_ota_apply() returns
 * ESP_OK. A NULL version is a no-op. */
void fp_ota_mark_try(const char *version);

/* True and out filled iff an OTA result is currently waiting to be
 * reported (api_client.c's telemetry_headers() calls this to decide
 * whether to send X-Ota-Result). False, out untouched, when nothing is
 * pending. */
bool fp_ota_result_pending(char *out, size_t cap);

/* Clears the pending OTA result - api_client.c calls this once a
 * display response carrying X-Ota-Result comes back 200, never before. */
void fp_ota_result_clear(void);
