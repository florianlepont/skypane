/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#include "wake_telemetry.h"

#include <stdio.h>
#include <string.h>

#define WAKE_RECORD_MAGIC 0x57414B45u /* "WAKE" */

static uint32_t clamp_u32(uint32_t v, uint32_t max)
{
    return v > max ? max : v;
}

static uint32_t rotl32(uint32_t v, unsigned n)
{
    return (v << n) | (v >> (32u - n));
}

/* Mixes every field after the magic; the magic is nonzero and checked
 * separately, so zeroed and all-ones memory both fail. */
static uint32_t record_checksum(const fp_wake_record_t *rec)
{
    uint32_t sum = rec->magic ^ 0xA5C3E17Bu;
    const uint32_t fields[] = {
        rec->seq,         rec->awake_ms, rec->request_ms, rec->download_ms,
        rec->draw_ms,     rec->spi_ms,   rec->tls_ms,     rec->redraw,
    };
    for (size_t i = 0; i < sizeof fields / sizeof fields[0]; i++) {
        sum = rotl32(sum, 5) ^ (fields[i] + (uint32_t)i * 0x9E3779B9u);
    }
    for (size_t i = 0; i < sizeof rec->outcome; i++) {
        sum = rotl32(sum, 3) ^ (uint32_t)(unsigned char)rec->outcome[i];
    }
    return sum;
}

void fp_wake_record_encode(fp_wake_record_t *rec, uint32_t seq,
                           uint32_t awake_ms, uint32_t request_ms,
                           uint32_t download_ms, uint32_t draw_ms,
                           uint32_t spi_ms, uint32_t tls_ms, uint32_t redraw,
                           const char *outcome)
{
    memset(rec, 0, sizeof *rec);
    rec->magic = WAKE_RECORD_MAGIC;
    rec->seq = seq;
    rec->awake_ms = awake_ms;
    rec->request_ms = request_ms;
    rec->download_ms = download_ms;
    rec->draw_ms = draw_ms;
    rec->spi_ms = spi_ms;
    rec->tls_ms = tls_ms;
    rec->redraw = redraw;
    if (outcome == NULL) {
        outcome = "unknown";
    }
    strncpy(rec->outcome, outcome, FP_WAKE_OUTCOME_MAX);
    rec->outcome[FP_WAKE_OUTCOME_MAX] = '\0';
    rec->checksum = record_checksum(rec);
}

bool fp_wake_record_valid(const fp_wake_record_t *rec)
{
    if (rec == NULL || rec->magic != WAKE_RECORD_MAGIC) {
        return false;
    }
    if (rec->redraw > FP_WAKE_REDRAW_MAX) {
        return false;
    }
    return rec->checksum == record_checksum(rec);
}

/* The outcome token the server accepts: 1 to 16 of a-z, 0-9, hyphen. Anything
 * else is replaced by "unknown". */
static const char *safe_outcome(const char *outcome, char *buf)
{
    size_t n = 0;
    while (n <= FP_WAKE_OUTCOME_MAX && outcome[n] != '\0') {
        char c = outcome[n];
        bool ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
        if (!ok) {
            return "unknown";
        }
        buf[n] = c;
        n++;
    }
    if (n == 0 || n > FP_WAKE_OUTCOME_MAX) {
        return "unknown";
    }
    buf[n] = '\0';
    return buf;
}

int fp_wake_telemetry_format(char *out, size_t out_len,
                             const fp_wake_current_t *cur,
                             const fp_wake_record_t *prev,
                             bool require_sequential)
{
    if (out == NULL || out_len == 0 || cur == NULL) {
        return -1;
    }
    bool with_prev = fp_wake_record_valid(prev);
    if (with_prev && require_sequential
        && (cur->seq == 0 || prev->seq != cur->seq - 1u)) {
        with_prev = false;
    }

    int n = snprintf(out, out_len, "v=1;seq=%lu;bt=%lu;wf=%lu;att=%lu",
                     (unsigned long)cur->seq,
                     (unsigned long)clamp_u32(cur->boot_ms, FP_WAKE_MS_MAX),
                     (unsigned long)clamp_u32(cur->wifi_ms, FP_WAKE_MS_MAX),
                     (unsigned long)clamp_u32(cur->wifi_attempts,
                                              FP_WAKE_ATT_MAX));
    if (n < 0 || (size_t)n >= out_len) {
        out[0] = '\0';
        return -1;
    }

    if (with_prev) {
        char tok[FP_WAKE_OUTCOME_MAX + 1];
        const char *outcome = safe_outcome(prev->outcome, tok);
        int m = snprintf(out + n, out_len - (size_t)n,
                         ";p_seq=%lu;p_aw=%lu;p_rq=%lu;p_dl=%lu;p_dr=%lu"
                         ";p_sp=%lu;p_tls=%lu;p_rd=%lu;p_out=%s",
                         (unsigned long)prev->seq,
                         (unsigned long)clamp_u32(prev->awake_ms, FP_WAKE_MS_MAX),
                         (unsigned long)clamp_u32(prev->request_ms, FP_WAKE_MS_MAX),
                         (unsigned long)clamp_u32(prev->download_ms, FP_WAKE_MS_MAX),
                         (unsigned long)clamp_u32(prev->draw_ms, FP_WAKE_MS_MAX),
                         (unsigned long)clamp_u32(prev->spi_ms, FP_WAKE_MS_MAX),
                         (unsigned long)clamp_u32(prev->tls_ms, FP_WAKE_MS_MAX),
                         (unsigned long)prev->redraw, outcome);
        if (m < 0 || (size_t)m >= out_len - (size_t)n) {
            out[0] = '\0';
            return -1;
        }
        n += m;
    }

    if (n > FP_WAKE_STATS_MAX_LEN) {
        out[0] = '\0';
        return -1;
    }
    return n;
}
