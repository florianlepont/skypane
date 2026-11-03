/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Wake telemetry for the X-Wake-Stats request header, with no ESP-IDF in
 * it: the value formatter and the record that carries the previous wake's
 * phase timings across deep sleep in RTC memory.
 *
 * The value is a semicolon-separated key=value list starting with v=1; the
 * server (server/wake_stats.py) drops the whole header on any rule
 * violation, so this module clamps every number to the server's bound and
 * never emits a value the server would refuse. It formats only counters and
 * durations: no credential and no identifier. */

/* Largest header value in bytes, terminator excluded. Must equal
 * WAKE_STATS_MAX_BYTES in server/wake_stats.py; a CI check compares them.
 * The worst case with every field at its bound is 173 bytes. */
#define FP_WAKE_STATS_MAX_LEN 192

/* Server-side bounds, inclusive. */
#define FP_WAKE_MS_MAX      3600000u
#define FP_WAKE_ATT_MAX     16u
#define FP_WAKE_REDRAW_MAX  2u
#define FP_WAKE_OUTCOME_MAX 16u /* characters, terminator excluded */

/* Previous-wake record kept in RTC memory. RTC memory is cleared on power
 * loss and reinitialised after some restarts, so the record carries a magic
 * and a checksum: anything that fails them is dropped, never reported. */
typedef struct {
    uint32_t magic;
    uint32_t seq;
    uint32_t awake_ms;
    uint32_t request_ms;
    uint32_t download_ms;
    uint32_t draw_ms;
    uint32_t spi_ms;
    uint32_t tls_ms;
    uint32_t redraw;                              /* 0 none, 1 drawn, 2 deferred */
    char outcome[FP_WAKE_OUTCOME_MAX + 1];        /* NUL-terminated token */
    uint32_t checksum;
} fp_wake_record_t;

/* Measurements of the wake that is sending the header. */
typedef struct {
    uint32_t seq;
    uint32_t boot_ms;
    uint32_t wifi_ms;
    uint32_t wifi_attempts;
} fp_wake_current_t;

/* Fills `rec` from the measured values at sleep entry and seals it with the
 * magic and checksum. `outcome` is copied up to FP_WAKE_OUTCOME_MAX
 * characters; NULL becomes "unknown". Values are stored as measured; the
 * formatter clamps them. */
void fp_wake_record_encode(fp_wake_record_t *rec, uint32_t seq,
                           uint32_t awake_ms, uint32_t request_ms,
                           uint32_t download_ms, uint32_t draw_ms,
                           uint32_t spi_ms, uint32_t tls_ms, uint32_t redraw,
                           const char *outcome);

/* True when the record carries the magic, a matching checksum and a redraw
 * state within 0 to 2. Zeroed and all-ones memory are invalid. */
bool fp_wake_record_valid(const fp_wake_record_t *rec);

/* Writes the NUL-terminated header value into `out` and returns its length
 * (at most FP_WAKE_STATS_MAX_LEN), or a negative value when `out_len` is too
 * small; nothing is written past `out_len`. The p_ keys are present only
 * when `prev` is non-NULL and valid and, if `require_sequential`, its seq is
 * the current seq minus one; otherwise they are omitted entirely. */
int fp_wake_telemetry_format(char *out, size_t out_len,
                             const fp_wake_current_t *cur,
                             const fp_wake_record_t *prev,
                             bool require_sequential);
