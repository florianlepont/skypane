/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Every decision the device makes about a firmware update: whether an
 * offered release should be started, whether a downloaded image is the
 * one that was offered and above the floor, what a restart after a
 * trial boot means, whether the running image should be confirmed
 * valid, and the result token reported back to the server. Pure, no
 * ESP-IDF, no I/O, compiled and asserted on a host by
 * firmware/tests/test_ota_policy.c - ota.c and state_machine.c call
 * these, they do not re-derive the rules themselves. Offer fields
 * (version, sha256, size, URL) are validated by validate.c's
 * fp_fw_version_valid / fp_fw_size_parse / fp_image_hash_valid /
 * fp_url_valid before any function here sees them. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* The device refuses to start an update at or below this measured
 * battery voltage, and when the battery reading is unknown (reported
 * as 0 by battery.c). Mirrors server/device_policy.py's
 * BATTERY_LOW_THRESHOLD_MV activation level - not a new threshold, the
 * existing battery-low alert already means "do not spend extra energy
 * right now". */
#define FP_OTA_MIN_BATTERY_MV 3500u

/* "<token>;<version>" plus room to spare; FP_FW_VERSION_BUF (32) is the
 * largest legitimate version, "fail-interrupted" (16) the longest
 * token, ';' and a NUL. */
#define FP_OTA_RESULT_BUF 64

/* Parses v as "fw-v<major>.<minor>.<patch>", optionally followed by
 * "-<anything>" (an untagged/bench suffix, not itself validated).
 * Each component is 1-4 decimal digits with no leading zero (except
 * the single digit "0"). Rejects a missing "fw-v" prefix, a missing
 * component, a leading zero, a component over 4 digits, trailing bytes
 * that are neither '\0' nor '-', and NULL. out is written only on
 * success. An untagged dev build's version (a bare git hash, no
 * "fw-v" prefix) always fails to parse - by design, it can never
 * compare as at-or-above a floor. */
bool fp_ota_version_parse(const char *v, uint16_t out[3]);

/* True iff v parses and is >= floor by (major, minor, patch). False if
 * either fails to parse - fail closed, never treat an unparseable
 * version as clearing the floor. */
bool fp_ota_version_at_or_above_floor(const char *v, const char *floor);

typedef enum {
    FP_OTA_START,             /* start the update                         */
    FP_OTA_SKIP_SAME_VERSION, /* offered == running: nothing to do        */
    FP_OTA_REFUSE_BATTERY,    /* battery at/below the floor, or unknown   */
    FP_OTA_REFUSE_FLOOR,      /* offered version is below the floor       */
} fp_ota_decision_t;

/* Decides whether to start an offered update. Checked in order: same
 * version as running (SKIP, regardless of battery or floor - there is
 * nothing to install); battery at or below FP_OTA_MIN_BATTERY_MV,
 * including the unknown-battery sentinel 0 (REFUSE_BATTERY); offered
 * below floor (REFUSE_FLOOR); otherwise START. A voluntary downgrade
 * (offered older than running) is allowed as long as it still clears
 * the floor - only the floor is compared, never offered against
 * running. NULL offered/running/floor never starts an update
 * (REFUSE_FLOOR, the safest of the two refusal states to fail into). */
fp_ota_decision_t fp_ota_decide(const char *offered, const char *running,
                                const char *floor, uint32_t battery_mv);

typedef enum {
    FP_OTA_IMAGE_OK,               /* project, version and floor all check out */
    FP_OTA_IMAGE_WRONG_PROJECT,    /* app descriptor's project_name isn't ours */
    FP_OTA_IMAGE_VERSION_MISMATCH, /* descriptor version != the offered one    */
    FP_OTA_IMAGE_BELOW_FLOOR,      /* descriptor version is below the floor    */
} fp_ota_image_verdict_t;

/* Checks a downloaded image's app descriptor against what was offered,
 * after signature and hash verification have already passed. Re-checks
 * the version against the floor from the signed descriptor itself, not
 * just the offer, so a compromised VPS cannot bypass the floor by
 * lying in the offer alone. */
fp_ota_image_verdict_t fp_ota_image_check(const char *desc_project,
                                          const char *desc_version,
                                          const char *offered,
                                          const char *floor);

typedef enum {
    FP_OTA_BOOT_NONE,         /* no trial was in progress                    */
    FP_OTA_BOOT_TRIAL,        /* running the just-installed image, unconfirmed */
    FP_OTA_BOOT_ROLLED_BACK,  /* bootloader reverted a failed trial          */
    FP_OTA_BOOT_INTERRUPTED,  /* a trial was recorded but this boot is neither
                               * that image nor its recorded rollback target */
} fp_ota_boot_outcome_t;

/* Classifies what happened across a restart, from state persisted
 * before the reboot (ota_try: the version that was started;
 * last_invalid_version: the version the bootloader marked invalid, if
 * any) compared against what is running now. ota_try NULL or empty
 * means no trial was recorded: NONE. ota_try == running: TRIAL if the
 * app has not confirmed itself valid yet, NONE if it already has
 * (an earlier wake already classified and confirmed this boot).
 * ota_try != running: ROLLED_BACK if last_invalid_version == ota_try
 * (the bootloader's own record agrees this is why we rolled back),
 * INTERRUPTED otherwise (the image changed for some other reason - a
 * power loss mid-trial, for example - and neither a confirm nor a
 * rollback was recorded). */
fp_ota_boot_outcome_t fp_ota_boot_classify(const char *ota_try,
                                           const char *running,
                                           bool running_pending_verify,
                                           const char *last_invalid_version);

/* The confirm rule: mark the running image valid only when it is still
 * pending verification and this wake's poll succeeded. Never confirm
 * on a failed poll - a pending image that cannot even reach the server
 * should be left to the bootloader's own rollback on the next reset,
 * not marked good by the app. */
bool fp_ota_should_confirm(bool running_pending_verify, bool poll_ok);

typedef enum {
    FP_OTA_RESULT_TRIAL,             /* wake N: booted the image, awaiting confirm */
    FP_OTA_RESULT_INSTALLED,         /* wake N+1: confirmed valid                  */
    FP_OTA_RESULT_ROLLBACK,          /* bootloader reverted a failed trial         */
    FP_OTA_RESULT_DEFERRED_BATTERY,  /* offer withdrawn/held: battery too low      */
    FP_OTA_RESULT_FAIL_DOWNLOAD,     /* transfer failed (status/length/oversize)   */
    FP_OTA_RESULT_FAIL_SIZE,         /* offer's size field failed fp_fw_size_parse */
    FP_OTA_RESULT_FAIL_HASH,         /* downloaded bytes did not match sha256      */
    FP_OTA_RESULT_FAIL_IMAGE,        /* signature check or descriptor check failed */
    FP_OTA_RESULT_FAIL_FLOOR,        /* offered or descriptor version below floor  */
    FP_OTA_RESULT_FAIL_INTERRUPTED,  /* restart with neither a confirm nor a
                                      * recorded rollback (see BOOT_INTERRUPTED)   */
} fp_ota_result_t;

/* The wire token for each result - must equal
 * server/firmware_registry.py's RESULT_TOKENS exactly, since the
 * server parses this string back out of the device's report. */
const char *fp_ota_result_token(fp_ota_result_t r);

/* Formats "<token>;<version>" into out. False, and out set to the
 * empty string, if version fails fp_fw_version_valid or the formatted
 * result does not fit in cap bytes including the NUL. */
bool fp_ota_result_format(char *out, size_t cap, fp_ota_result_t r,
                          const char *version);
