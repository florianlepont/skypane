/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* HOST_TEST_DEPS: validate.c */
/* Host-side unit test for every OTA decision the device makes: version
 * parsing and floor comparison, the start/refuse decision, the
 * downloaded-image check, boot-outcome classification after a restart,
 * the confirm rule, and the result token/format the device reports.
 *
 *   cc -Wall -Wextra -std=c11 main/ota_policy.c main/validate.c \
 *      tests/test_ota_policy.c -o /tmp/top && /tmp/top
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../main/ota_policy.h"

static void version_parse_cases(void)
{
    uint16_t out[3];

    memset(out, 0xff, sizeof(out));
    assert(fp_ota_version_parse("fw-v1.2.3", out) == true);
    assert(out[0] == 1 && out[1] == 2 && out[2] == 3);

    memset(out, 0xff, sizeof(out));
    assert(fp_ota_version_parse("fw-v1.2.3-dev-panic", out) == true);
    assert(out[0] == 1 && out[1] == 2 && out[2] == 3);

    assert(fp_ota_version_parse("v1.2.3", out) == false);       /* no fw-v prefix */
    assert(fp_ota_version_parse("fw-v1.2", out) == false);      /* missing patch */
    assert(fp_ota_version_parse("fw-v01.2.3", out) == false);   /* leading zero */
    assert(fp_ota_version_parse("fw-v1.2.3x", out) == false);   /* trailing garbage */
    assert(fp_ota_version_parse("fw-v99999.0.0", out) == false); /* > 4 digits */
    assert(fp_ota_version_parse(NULL, out) == false);

    /* single-digit zero component is legitimate ("0" is not a
     * multi-digit leading zero). */
    memset(out, 0xff, sizeof(out));
    assert(fp_ota_version_parse("fw-v0.0.0", out) == true);
    assert(out[0] == 0 && out[1] == 0 && out[2] == 0);
}

static void version_at_or_above_floor_cases(void)
{
    assert(fp_ota_version_at_or_above_floor("fw-v1.0.0", "fw-v1.0.0") == true);
    assert(fp_ota_version_at_or_above_floor("fw-v0.9.9", "fw-v1.0.0") == false);
    assert(fp_ota_version_at_or_above_floor("abc1234", "fw-v1.0.0") == false);
    assert(fp_ota_version_at_or_above_floor("fw-v1.2.0", "fw-v1.0.0") == true);
    assert(fp_ota_version_at_or_above_floor("fw-v2.0.0", "fw-v1.9.9") == true);
    assert(fp_ota_version_at_or_above_floor("fw-v1.0.0", "abc1234") == false);
}

static void decide_cases(void)
{
    /* same offered and running: SKIP, checked before battery/floor/trial. */
    assert(fp_ota_decide("fw-v1.0.0", "fw-v1.0.0", "fw-v1.0.0", 0, false)
           == FP_OTA_SKIP_SAME_VERSION);

    /* same offered and running even while a trial is pending: still SKIP,
     * not REFUSE_TRIAL_PENDING - there is nothing to install either way. */
    assert(fp_ota_decide("fw-v1.0.0", "fw-v1.0.0", "fw-v1.0.0", 0, true)
           == FP_OTA_SKIP_SAME_VERSION);

    /* battery at the refusal threshold. */
    assert(fp_ota_decide("fw-v1.1.0", "fw-v1.0.0", "fw-v1.0.0", 3500, false)
           == FP_OTA_REFUSE_BATTERY);

    /* battery unknown (0 sentinel). */
    assert(fp_ota_decide("fw-v1.1.0", "fw-v1.0.0", "fw-v1.0.0", 0, false)
           == FP_OTA_REFUSE_BATTERY);

    /* battery fine, offered below the floor. */
    assert(fp_ota_decide("fw-v0.9.0", "fw-v1.0.0", "fw-v1.0.0", 3501, false)
           == FP_OTA_REFUSE_FLOOR);

    /* battery fine, offered above the floor but older than running:
     * a voluntary downgrade, still allowed. */
    assert(fp_ota_decide("fw-v1.0.0", "fw-v1.2.0", "fw-v1.0.0", 3501, false)
           == FP_OTA_START);

    /* one mV above the threshold, offered clears the floor: starts. */
    assert(fp_ota_decide("fw-v1.3.0", "fw-v1.2.0", "fw-v1.0.0", 3501, false)
           == FP_OTA_START);

    /* a different version offered while the running image is still on
     * trial: refused outright, before battery or floor are even looked
     * at - starting a second switch would make esp_ota_begin() refuse
     * and strand the trial's own confirm unconfirmed. */
    assert(fp_ota_decide("fw-v1.3.0", "fw-v1.2.0", "fw-v1.0.0", 3501, true)
           == FP_OTA_REFUSE_TRIAL_PENDING);

    /* trial pending also outranks a battery or floor refusal - the
     * result is always REFUSE_TRIAL_PENDING, never REFUSE_BATTERY or
     * REFUSE_FLOOR, when a different version is offered mid-trial. */
    assert(fp_ota_decide("fw-v0.9.0", "fw-v1.2.0", "fw-v1.0.0", 0, true)
           == FP_OTA_REFUSE_TRIAL_PENDING);
}

static void image_check_cases(void)
{
    assert(fp_ota_image_check("skypane", "fw-v1.2.0", "fw-v1.2.0", "fw-v1.0.0")
           == FP_OTA_IMAGE_OK);
    assert(fp_ota_image_check("other", "fw-v1.2.0", "fw-v1.2.0", "fw-v1.0.0")
           == FP_OTA_IMAGE_WRONG_PROJECT);
    assert(fp_ota_image_check("skypane", "fw-v1.2.1", "fw-v1.2.0", "fw-v1.0.0")
           == FP_OTA_IMAGE_VERSION_MISMATCH);
    assert(fp_ota_image_check("skypane", "fw-v0.9.0", "fw-v0.9.0", "fw-v1.0.0")
           == FP_OTA_IMAGE_BELOW_FLOOR);
}

static void boot_classify_cases(void)
{
    assert(fp_ota_boot_classify("", "fw-v1.2.0", true, NULL)
           == FP_OTA_BOOT_NONE);
    assert(fp_ota_boot_classify(NULL, "fw-v1.2.0", true, NULL)
           == FP_OTA_BOOT_NONE);

    assert(fp_ota_boot_classify("fw-v1.2.0", "fw-v1.2.0", true, NULL)
           == FP_OTA_BOOT_TRIAL);

    assert(fp_ota_boot_classify("fw-v1.2.0", "fw-v1.2.0", false, NULL)
           == FP_OTA_BOOT_INSTALLED); /* confirmed earlier, INSTALLED never recorded */

    assert(fp_ota_boot_classify("fw-v1.2.0", "fw-v1.1.0", true, "fw-v1.2.0")
           == FP_OTA_BOOT_ROLLED_BACK);

    assert(fp_ota_boot_classify("fw-v1.2.0", "fw-v1.1.0", true, NULL)
           == FP_OTA_BOOT_INTERRUPTED); /* no matching rollback record */

    assert(fp_ota_boot_classify("fw-v1.2.0", "fw-v1.1.0", true, "fw-v9.9.9")
           == FP_OTA_BOOT_INTERRUPTED); /* rollback record names a different version */
}

static void should_confirm_cases(void)
{
    assert(fp_ota_should_confirm(true, true) == true);
    assert(fp_ota_should_confirm(true, false) == false);
    assert(fp_ota_should_confirm(false, true) == false);
    assert(fp_ota_should_confirm(false, false) == false);
}

static void result_token_cases(void)
{
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_TRIAL), "trial") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_INSTALLED), "installed") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_ROLLBACK), "rollback") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_DEFERRED_BATTERY),
                  "deferred-battery") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_DOWNLOAD),
                  "fail-download") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_SIZE), "fail-size") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_HASH), "fail-hash") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_IMAGE), "fail-image") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_FLOOR), "fail-floor") == 0);
    assert(strcmp(fp_ota_result_token(FP_OTA_RESULT_FAIL_INTERRUPTED),
                  "fail-interrupted") == 0);
}

static void result_format_cases(void)
{
    char buf[FP_OTA_RESULT_BUF];

    memset(buf, 'x', sizeof(buf));
    assert(fp_ota_result_format(buf, sizeof(buf), FP_OTA_RESULT_FAIL_HASH,
                                "fw-v1.4.0") == true);
    assert(strcmp(buf, "fail-hash;fw-v1.4.0") == 0);

    memset(buf, 'x', sizeof(buf));
    assert(fp_ota_result_format(buf, sizeof(buf), FP_OTA_RESULT_INSTALLED,
                                "fw-v1.4.0") == true);
    assert(strcmp(buf, "installed;fw-v1.4.0") == 0);

    /* cap too small to hold the formatted string: false, out is "". */
    memset(buf, 'x', sizeof(buf));
    assert(fp_ota_result_format(buf, 5, FP_OTA_RESULT_FAIL_HASH,
                                "fw-v1.4.0") == false);
    assert(buf[0] == '\0');

    /* invalid version (fails fp_fw_version_valid): false, out is "". */
    memset(buf, 'x', sizeof(buf));
    assert(fp_ota_result_format(buf, sizeof(buf), FP_OTA_RESULT_FAIL_HASH,
                                "bad version") == false);
    assert(buf[0] == '\0');

    memset(buf, 'x', sizeof(buf));
    assert(fp_ota_result_format(buf, sizeof(buf), FP_OTA_RESULT_FAIL_HASH,
                                NULL) == false);
    assert(buf[0] == '\0');
}

int main(void)
{
    version_parse_cases();
    version_at_or_above_floor_cases();
    decide_cases();
    image_check_cases();
    boot_classify_cases();
    should_confirm_cases();
    result_token_cases();
    result_format_cases();
    printf("ota_policy: all cases pass\n");
    return 0;
}
