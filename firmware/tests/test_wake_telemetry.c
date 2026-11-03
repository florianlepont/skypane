/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the X-Wake-Stats formatter and the previous-wake
 * record. The golden strings here are the ones the Python side feeds to
 * server/wake_stats.parse_wake_stats, so a grammar disagreement shows up.
 *
 *   cc main/wake_telemetry.c tests/test_wake_telemetry.c \
 *      -o /tmp/tw && /tmp/tw
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../main/wake_telemetry.h"

#define GOLDEN_TYPICAL                                                       \
    "v=1;seq=42;bt=310;wf=1180;att=1;p_seq=41;p_aw=1530;p_rq=60;p_dl=0;"     \
    "p_dr=0;p_sp=0;p_tls=97;p_rd=0;p_out=ok"
#define GOLDEN_NO_PREV "v=1;seq=42;bt=310;wf=1180;att=1"
#define GOLDEN_WORST                                                         \
    "v=1;seq=4294967295;bt=3600000;wf=3600000;att=16;p_seq=4294967295;"      \
    "p_aw=3600000;p_rq=3600000;p_dl=3600000;p_dr=3600000;p_sp=3600000;"      \
    "p_tls=3600000;p_rd=2;p_out=abcdefghijklmnop"

static fp_wake_current_t typical_cur(void)
{
    fp_wake_current_t c = {42, 310, 1180, 1};
    return c;
}

static void typical_record_formats_to_the_golden_string(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 41, 1530, 60, 0, 0, 0, 97, 0, "ok");
    fp_wake_current_t cur = typical_cur();
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    int n = fp_wake_telemetry_format(out, sizeof out, &cur, &rec, true);
    assert(n == (int)strlen(GOLDEN_TYPICAL));
    assert(strcmp(out, GOLDEN_TYPICAL) == 0);
    assert(strncmp(out, "v=1;", 4) == 0);
}

static void absent_or_invalid_record_omits_every_p_key(void)
{
    fp_wake_current_t cur = typical_cur();
    char out[FP_WAKE_STATS_MAX_LEN + 1];

    int n = fp_wake_telemetry_format(out, sizeof out, &cur, NULL, true);
    assert(n == (int)strlen(GOLDEN_NO_PREV));
    assert(strcmp(out, GOLDEN_NO_PREV) == 0);

    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 41, 1530, 60, 0, 0, 0, 97, 0, "ok");

    fp_wake_record_t bad = rec;
    bad.magic ^= 1u;
    fp_wake_telemetry_format(out, sizeof out, &cur, &bad, false);
    assert(strcmp(out, GOLDEN_NO_PREV) == 0);

    bad = rec;
    bad.checksum ^= 1u;
    fp_wake_telemetry_format(out, sizeof out, &cur, &bad, false);
    assert(strcmp(out, GOLDEN_NO_PREV) == 0);

    /* A valid record from the wrong wake is dropped when the caller asks for
     * the sequential check, and kept when it does not. */
    cur.seq = 44;
    fp_wake_telemetry_format(out, sizeof out, &cur, &rec, true);
    assert(strcmp(out, "v=1;seq=44;bt=310;wf=1180;att=1") == 0);
    fp_wake_telemetry_format(out, sizeof out, &cur, &rec, false);
    assert(strstr(out, ";p_seq=41;") != NULL);
}

static void redraw_state_above_two_invalidates_the_record(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 41, 1, 1, 1, 1, 1, 1, 3, "ok");
    assert(!fp_wake_record_valid(&rec));
    fp_wake_current_t cur = typical_cur();
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    fp_wake_telemetry_format(out, sizeof out, &cur, &rec, true);
    assert(strstr(out, "p_") == NULL);
}

static void zeroed_and_all_ones_memory_are_invalid(void)
{
    fp_wake_record_t rec;
    memset(&rec, 0x00, sizeof rec);
    assert(!fp_wake_record_valid(&rec));
    memset(&rec, 0xFF, sizeof rec);
    assert(!fp_wake_record_valid(&rec));
    assert(!fp_wake_record_valid(NULL));
}

static void encoder_output_validates_and_round_trips(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 7, 11, 22, 33, 44, 55, 66, 2, "tls-connect");
    assert(fp_wake_record_valid(&rec));
    assert(rec.seq == 7 && rec.awake_ms == 11 && rec.request_ms == 22);
    assert(rec.download_ms == 33 && rec.draw_ms == 44 && rec.spi_ms == 55);
    assert(rec.tls_ms == 66 && rec.redraw == 2);
    assert(strcmp(rec.outcome, "tls-connect") == 0);

    fp_wake_record_encode(&rec, 1, 0, 0, 0, 0, 0, 0, 0, NULL);
    assert(strcmp(rec.outcome, "unknown") == 0);
    assert(fp_wake_record_valid(&rec));

    /* A changed field breaks the checksum. */
    fp_wake_record_encode(&rec, 7, 11, 22, 33, 44, 55, 66, 2, "ok");
    rec.draw_ms += 1;
    assert(!fp_wake_record_valid(&rec));
}

static void bad_outcome_tokens_become_unknown(void)
{
    fp_wake_current_t cur = typical_cur();
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    const char *bad[] = {"OK", "wifi fail", "a;b", "a=b", "", "caf\xc3\xa9"};
    for (size_t i = 0; i < sizeof bad / sizeof bad[0]; i++) {
        fp_wake_record_t rec;
        fp_wake_record_encode(&rec, 41, 1, 1, 1, 1, 1, 1, 0, bad[i]);
        /* Encode-time truncation is not a validity rule; tokens are screened
         * when formatted. */
        fp_wake_telemetry_format(out, sizeof out, &cur, &rec, true);
        assert(strstr(out, ";p_out=unknown") != NULL);
    }

    /* Longer than 16 is cut by the encoder to 16 valid characters. */
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 41, 1, 1, 1, 1, 1, 1, 0,
                          "abcdefghijklmnopqrstuvwxyz");
    fp_wake_telemetry_format(out, sizeof out, &cur, &rec, true);
    assert(strstr(out, ";p_out=abcdefghijklmnop") != NULL);

    /* A record whose token slot lost its terminator is screened too. */
    fp_wake_record_encode(&rec, 41, 1, 1, 1, 1, 1, 1, 0, "ok");
    memset(rec.outcome, 'a', sizeof rec.outcome);
    rec.checksum = 0;
    assert(!fp_wake_record_valid(&rec));
}

static void worst_case_is_173_bytes_and_within_the_cap(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 4294967295u, 3600000, 3600000, 3600000,
                          3600000, 3600000, 3600000, 2, "abcdefghijklmnop");
    fp_wake_current_t cur = {4294967295u, 3600000, 3600000, 16};
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    int n = fp_wake_telemetry_format(out, sizeof out, &cur, &rec, false);
    assert(n == 173);
    assert(n <= FP_WAKE_STATS_MAX_LEN);
    assert(strcmp(out, GOLDEN_WORST) == 0);
}

static void values_above_their_bounds_clamp_to_the_worst_case(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 4294967295u, 4000000000u, 4294967295u,
                          3600001, 99999999, 3600001, 4294967295u, 2,
                          "abcdefghijklmnop");
    fp_wake_current_t cur = {4294967295u, 4294967295u, 3600001, 17};
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    int n = fp_wake_telemetry_format(out, sizeof out, &cur, &rec, false);
    assert(n == 173);
    assert(strcmp(out, GOLDEN_WORST) == 0);
}

static void small_buffer_errors_and_never_overruns(void)
{
    fp_wake_record_t rec;
    fp_wake_record_encode(&rec, 41, 1530, 60, 0, 0, 0, 97, 0, "ok");
    fp_wake_current_t cur = typical_cur();
    size_t full = strlen(GOLDEN_TYPICAL);

    /* Every size below the needed one fails and leaves the guard bytes. */
    for (size_t len = 1; len <= full; len++) {
        char buf[FP_WAKE_STATS_MAX_LEN + 16];
        memset(buf, 0x7E, sizeof buf);
        int n = fp_wake_telemetry_format(buf, len, &cur, &rec, true);
        assert(n < 0);
        for (size_t i = len; i < sizeof buf; i++) {
            assert(buf[i] == 0x7E);
        }
    }
    char buf[FP_WAKE_STATS_MAX_LEN + 1];
    assert(fp_wake_telemetry_format(buf, full + 1, &cur, &rec, true)
           == (int)full);
    assert(fp_wake_telemetry_format(buf, 0, &cur, &rec, true) < 0);
    assert(fp_wake_telemetry_format(NULL, 10, &cur, &rec, true) < 0);
}

int main(void)
{
    typical_record_formats_to_the_golden_string();
    absent_or_invalid_record_omits_every_p_key();
    redraw_state_above_two_invalidates_the_record();
    zeroed_and_all_ones_memory_are_invalid();
    encoder_output_validates_and_round_trips();
    bad_outcome_tokens_become_unknown();
    worst_case_is_173_bytes_and_within_the_cap();
    values_above_their_bounds_clamp_to_the_worst_case();
    small_buffer_errors_and_never_overruns();
    printf("wake_telemetry: all tests passed\n");
    return 0;
}
