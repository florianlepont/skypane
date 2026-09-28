/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "ota_policy.h"

#include <stdio.h>
#include <string.h>

#include "validate.h"

/* Matches CMakeLists.txt's project(skypane) - the name esp_app_desc_t's
 * project_name field carries for every image this firmware builds. */
#define FP_OTA_PROJECT_NAME "skypane"

/* Consumes 1-4 decimal digits from *p with no leading zero (unless the
 * component is exactly "0"), writes the value to *out, and advances *p
 * past the digits. False, with *p and *out both untouched, otherwise. */
static bool parse_version_component(const char **p, uint16_t *out)
{
    const char *s = *p;
    size_t len = 0;
    while (s[len] >= '0' && s[len] <= '9') {
        len++;
    }
    if (len == 0 || len > 4) {
        return false;
    }
    if (len > 1 && s[0] == '0') {
        return false; /* multi-digit leading zero */
    }
    unsigned val = 0;
    for (size_t i = 0; i < len; i++) {
        val = val * 10 + (unsigned)(s[i] - '0');
    }
    *out = (uint16_t)val;
    *p = s + len;
    return true;
}

bool fp_ota_version_parse(const char *v, uint16_t out[3])
{
    if (!v || strncmp(v, "fw-v", 4) != 0) {
        return false;
    }
    const char *p = v + 4;
    uint16_t major, minor, patch;

    if (!parse_version_component(&p, &major)) {
        return false;
    }
    if (*p != '.') {
        return false;
    }
    p++;
    if (!parse_version_component(&p, &minor)) {
        return false;
    }
    if (*p != '.') {
        return false;
    }
    p++;
    if (!parse_version_component(&p, &patch)) {
        return false;
    }
    if (*p != '\0' && *p != '-') {
        return false; /* trailing garbage that isn't a "-suffix" */
    }
    if (out) {
        out[0] = major;
        out[1] = minor;
        out[2] = patch;
    }
    return true;
}

bool fp_ota_version_at_or_above_floor(const char *v, const char *floor)
{
    uint16_t vv[3];
    uint16_t ff[3];

    if (!fp_ota_version_parse(v, vv) || !fp_ota_version_parse(floor, ff)) {
        return false; /* fail closed: an unparseable version never clears the floor */
    }
    if (vv[0] != ff[0]) {
        return vv[0] > ff[0];
    }
    if (vv[1] != ff[1]) {
        return vv[1] > ff[1];
    }
    return vv[2] >= ff[2];
}

fp_ota_decision_t fp_ota_decide(const char *offered, const char *running,
                                const char *floor, uint32_t battery_mv)
{
    if (!offered || !running || !floor) {
        return FP_OTA_REFUSE_FLOOR; /* malformed input never starts an update */
    }
    if (strcmp(offered, running) == 0) {
        return FP_OTA_SKIP_SAME_VERSION;
    }
    if (battery_mv <= FP_OTA_MIN_BATTERY_MV) {
        return FP_OTA_REFUSE_BATTERY; /* covers the unknown-battery 0 sentinel too */
    }
    if (!fp_ota_version_at_or_above_floor(offered, floor)) {
        return FP_OTA_REFUSE_FLOOR;
    }
    return FP_OTA_START;
}

fp_ota_image_verdict_t fp_ota_image_check(const char *desc_project,
                                          const char *desc_version,
                                          const char *offered,
                                          const char *floor)
{
    if (!desc_project || !desc_version || !offered || !floor) {
        return FP_OTA_IMAGE_WRONG_PROJECT; /* fail closed on malformed input */
    }
    if (strcmp(desc_project, FP_OTA_PROJECT_NAME) != 0) {
        return FP_OTA_IMAGE_WRONG_PROJECT;
    }
    if (strcmp(desc_version, offered) != 0) {
        return FP_OTA_IMAGE_VERSION_MISMATCH;
    }
    if (!fp_ota_version_at_or_above_floor(desc_version, floor)) {
        return FP_OTA_IMAGE_BELOW_FLOOR;
    }
    return FP_OTA_IMAGE_OK;
}

fp_ota_boot_outcome_t fp_ota_boot_classify(const char *ota_try,
                                           const char *running,
                                           bool running_pending_verify,
                                           const char *last_invalid_version)
{
    if (!ota_try || ota_try[0] == '\0' || !running) {
        return FP_OTA_BOOT_NONE;
    }
    if (strcmp(ota_try, running) == 0) {
        return running_pending_verify ? FP_OTA_BOOT_TRIAL : FP_OTA_BOOT_NONE;
    }
    if (last_invalid_version && strcmp(ota_try, last_invalid_version) == 0) {
        return FP_OTA_BOOT_ROLLED_BACK;
    }
    return FP_OTA_BOOT_INTERRUPTED;
}

bool fp_ota_should_confirm(bool running_pending_verify, bool poll_ok)
{
    return running_pending_verify && poll_ok;
}

const char *fp_ota_result_token(fp_ota_result_t r)
{
    switch (r) {
    case FP_OTA_RESULT_TRIAL:
        return "trial";
    case FP_OTA_RESULT_INSTALLED:
        return "installed";
    case FP_OTA_RESULT_ROLLBACK:
        return "rollback";
    case FP_OTA_RESULT_DEFERRED_BATTERY:
        return "deferred-battery";
    case FP_OTA_RESULT_FAIL_DOWNLOAD:
        return "fail-download";
    case FP_OTA_RESULT_FAIL_SIZE:
        return "fail-size";
    case FP_OTA_RESULT_FAIL_HASH:
        return "fail-hash";
    case FP_OTA_RESULT_FAIL_IMAGE:
        return "fail-image";
    case FP_OTA_RESULT_FAIL_FLOOR:
        return "fail-floor";
    case FP_OTA_RESULT_FAIL_INTERRUPTED:
        return "fail-interrupted";
    }
    return "fail-interrupted"; /* unreachable for a valid enum value; fail-safe default */
}

bool fp_ota_result_format(char *out, size_t cap, fp_ota_result_t r,
                          const char *version)
{
    if (!out || cap == 0) {
        return false;
    }
    out[0] = '\0';
    if (!fp_fw_version_valid(version)) {
        return false;
    }
    const char *token = fp_ota_result_token(r);
    int n = snprintf(out, cap, "%s;%s", token, version);
    if (n < 0 || (size_t)n >= cap) {
        out[0] = '\0';
        return false;
    }
    return true;
}
