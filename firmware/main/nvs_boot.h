/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* What app_main.c does with the result of bringing NVS up at boot, and
 * how long it sleeps when NVS stays unusable. Pure, no ESP-IDF, no I/O:
 * host-compilable so the rules are asserted on every commit. NVS comes
 * up before the failure counter can be read, so a failure here cannot
 * go through the persisted backoff — it logs `poll fail step=nvs` and
 * sleeps a fixed interval instead of aborting, since an abort would
 * hot-loop a chip whose partition keeps failing. FP_NVS_ERR_* mirrors
 * ESP-IDF v5.3.1 (esp_err.h, nvs.h); app_main.c asserts the equality. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define FP_NVS_ERR_OK 0
#define FP_NVS_ERR_NO_FREE_PAGES 0x110d
#define FP_NVS_ERR_NEW_VERSION_FOUND 0x1110

typedef enum {
    FP_NVS_BOOT_READY,           /* NVS is usable, carry on booting          */
    FP_NVS_BOOT_ERASE_AND_RETRY, /* erase the partition, then init once more */
    FP_NVS_BOOT_UNUSABLE,        /* log step=nvs and sleep fp_nvs_fail_sleep_s() */
} fp_nvs_boot_action_t;

/* Decides what to do with one nvs_flash_init() result (`err`).
 *
 * ESP_OK is READY. The two "the partition layout itself is unusable"
 * codes (no free pages, new version found) are ERASE_AND_RETRY on the
 * first attempt only - never erase on an ordinary error, and never
 * twice in one boot. Every other code, and any failure after the erase
 * (`after_erase`), is UNUSABLE. */
fp_nvs_boot_action_t fp_nvs_init_action(int err, bool after_erase);

/* Seconds to deep-sleep when NVS is unusable: the first step of the
 * failure backoff (fp_backoff_seconds(0), 5 min). The counter that would
 * grow it lives in NVS, so it is fixed. 5 min matches what any other
 * first failure sleeps, lets a transient flash fault recover at the
 * normal pace, and turns a hot loop into a sub-second wake with the
 * radio off every 5 min. Never 0: a zero timer wake is the hot loop this
 * exists to prevent. */
uint32_t fp_nvs_fail_sleep_s(void);
