/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Trimmed from flightportrait/frame's `main/state_machine.c/.h`
 * (@ ce3335fc). Upstream's state machine dispatches boot -> provision |
 * pair | poll across BLE provisioning, possession-pairing re-registration,
 * OTA evaluation, remote reset, and button-driven branches — none of
 * which is compiled into this project this phase (see firmware/VENDOR.md
 * "Deliberately Not Vendored"). This is the Phase 1 path only: connect
 * Wi-Fi, ensure a bearer token exists, poll the display endpoint,
 * hash-skip or download+verify+blit, persist the new hash only after a
 * successful blit.
 */
#pragma once
#include <stdint.h>

#include "esp_err.h"

typedef enum {
    FP_POLL_OK_REFRESHED, /* new image on glass                        */
    FP_POLL_OK_UNCHANGED, /* hash matched, nothing downloaded          */
    FP_POLL_OK_DEFERRED,  /* fetched fine; the panel could not draw yet
                            * (refresh spacing). NOT a failure — see
                            * PROTOCOL.md §3 and panel_guard.h.         */
    FP_POLL_FAILED,       /* any failure — caller applies backoff      */
} fp_poll_result_t;

/* One wake's poll attempt: connect Wi-Fi, ensure a bearer token exists
 * (calls POST /device/v1/setup on the very first wake, or after an NVS
 * erase), GET /device/v1/display, hash-skip or download+verify+blit, and
 * persist the new image hash only after a successful blit — so a blit
 * that never happened cannot cause the next wake to skip.
 *
 * `boot_reason` feeds the X-Boot-Reason telemetry header. On any
 * FP_POLL_OK_* result, *sleep_s_out carries the server's sleep_s value.
 * On FP_POLL_FAILED, *fail_step_out is set to one of the Log Line
 * Contract's step tokens ("wifi", "http", "status", "json", "download",
 * "verify", "blit" — firmware/VENDOR.md § Log Line Contract) and
 * *sleep_s_out is left untouched. */
fp_poll_result_t fp_poll_once(const char *boot_reason, uint32_t *sleep_s_out,
                              const char **fail_step_out);
