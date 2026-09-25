/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "nvs_boot.h"

#include "backoff.h"

fp_nvs_boot_action_t fp_nvs_init_action(int err, bool after_erase)
{
    if (err == FP_NVS_ERR_OK) {
        return FP_NVS_BOOT_READY;
    }
    if (!after_erase && (err == FP_NVS_ERR_NO_FREE_PAGES ||
                         err == FP_NVS_ERR_NEW_VERSION_FOUND)) {
        return FP_NVS_BOOT_ERASE_AND_RETRY;
    }
    return FP_NVS_BOOT_UNUSABLE;
}

uint32_t fp_nvs_fail_sleep_s(void)
{
    return fp_backoff_seconds(0);
}
