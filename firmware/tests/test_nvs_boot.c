/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* HOST_TEST_DEPS: backoff.c */
/* Host-side unit test for the boot-time NVS decision: erase only on the
 * two layout codes and only once, treat everything else as unusable,
 * and sleep a fixed, non-zero interval when NVS stays unusable.
 *
 *   cc -Wall -Wextra -std=c11 main/nvs_boot.c main/backoff.c \
 *      tests/test_nvs_boot.c -o /tmp/tnb && /tmp/tnb
 */
#include <assert.h>
#include <stdio.h>

#include "../main/backoff.h"
#include "../main/nvs_boot.h"

/* ESP_FAIL, ESP_ERR_NVS_NOT_INITIALIZED, ESP_ERR_NVS_NOT_FOUND and
 * ESP_ERR_FLASH_OP_FAIL in ESP-IDF v5.3.1: ordinary errors that must
 * never trigger an erase. */
static const int kOrdinaryErrors[] = {-1, 0x1101, 0x1102, 0x6002};

static void ok_is_ready_before_and_after_an_erase(void)
{
    assert(fp_nvs_init_action(FP_NVS_ERR_OK, false) == FP_NVS_BOOT_READY);
    assert(fp_nvs_init_action(FP_NVS_ERR_OK, true) == FP_NVS_BOOT_READY);
}

static void layout_codes_erase_once(void)
{
    assert(fp_nvs_init_action(FP_NVS_ERR_NO_FREE_PAGES, false) ==
           FP_NVS_BOOT_ERASE_AND_RETRY);
    assert(fp_nvs_init_action(FP_NVS_ERR_NEW_VERSION_FOUND, false) ==
           FP_NVS_BOOT_ERASE_AND_RETRY);
    /* Still failing after the erase: never erase a second time. */
    assert(fp_nvs_init_action(FP_NVS_ERR_NO_FREE_PAGES, true) ==
           FP_NVS_BOOT_UNUSABLE);
    assert(fp_nvs_init_action(FP_NVS_ERR_NEW_VERSION_FOUND, true) ==
           FP_NVS_BOOT_UNUSABLE);
}

static void ordinary_errors_are_unusable_and_never_erase(void)
{
    for (size_t i = 0; i < sizeof(kOrdinaryErrors) / sizeof(kOrdinaryErrors[0]); i++) {
        assert(fp_nvs_init_action(kOrdinaryErrors[i], false) == FP_NVS_BOOT_UNUSABLE);
        assert(fp_nvs_init_action(kOrdinaryErrors[i], true) == FP_NVS_BOOT_UNUSABLE);
    }
}

static void fail_sleep_is_the_first_backoff_step_and_never_zero(void)
{
    assert(fp_nvs_fail_sleep_s() == fp_backoff_seconds(0));
    assert(fp_nvs_fail_sleep_s() == 300);
    assert(fp_nvs_fail_sleep_s() > 0);
}

int main(void)
{
    ok_is_ready_before_and_after_an_erase();
    layout_codes_erase_once();
    ordinary_errors_are_unusable_and_never_erase();
    fail_sleep_is_the_first_backoff_step_and_never_zero();
    printf("nvs_boot: all cases pass\n");
    return 0;
}
