/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host test of the pure parts of the 7.3" trial driver: pixel packing, the
 * init command table and the pin maps. No ESP-IDF, no hardware.
 *
 *   sh run-spike-host-test.sh
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "epd7in3e_trial.h"

#define PIXELS (EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT)

static void test_pack_size_and_nibble_order(void)
{
    uint8_t *in = malloc(PIXELS);
    uint8_t *out = malloc(EPD_TRIAL_PACKED_BYTES);
    assert(in && out);
    assert(EPD_TRIAL_PACKED_BYTES == 192000);

    for (size_t i = 0; i < PIXELS; i++) {
        in[i] = EPD_TRIAL_WHITE;
    }
    in[0] = EPD_TRIAL_BLACK;   /* high nibble of byte 0 */
    in[1] = EPD_TRIAL_GREEN;   /* low nibble of byte 0  */
    in[2] = EPD_TRIAL_BLUE;    /* high nibble of byte 1 */
    in[3] = EPD_TRIAL_YELLOW;  /* low nibble of byte 1  */
    in[PIXELS - 2] = EPD_TRIAL_RED;
    in[PIXELS - 1] = EPD_TRIAL_BLACK;

    memset(out, 0xEE, EPD_TRIAL_PACKED_BYTES);
    assert(epd_trial_pack_4bpp(in, PIXELS, out, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_OK);
    assert(out[0] == 0x06);
    assert(out[1] == 0x52);
    assert(out[2] == 0x11);
    assert(out[EPD_TRIAL_PACKED_BYTES - 1] == 0x30);
    for (size_t i = 2; i < EPD_TRIAL_PACKED_BYTES - 1; i++) {
        assert(out[i] == 0x11);
    }
    free(in);
    free(out);
}

static void test_init_table_order(void)
{
    /* Command order and data lengths of the vendor init sequence. */
    static const struct { uint8_t cmd; uint8_t len; } expect[] = {
        {0xAA, 6}, {0x01, 6}, {0x00, 2}, {0x03, 4}, {0x05, 4}, {0x06, 4},
        {0x08, 4}, {0x13, 2}, {0x30, 1}, {0x41, 1}, {0x50, 1}, {0x60, 2},
        {0x61, 4}, {0x82, 1}, {0x84, 1}, {0x86, 1}, {0xE3, 1}, {0xE0, 1},
        {0xE6, 1}, {0x04, 0},
    };
    size_t count = 0;
    const epd_trial_cmd_t *t = epd_trial_init_table(&count);
    assert(t != NULL);
    assert(count == sizeof(expect) / sizeof(expect[0]));
    for (size_t i = 0; i < count; i++) {
        assert(t[i].cmd == expect[i].cmd);
        assert(t[i].len == expect[i].len);
        assert(t[i].len <= sizeof(t[i].data));
    }
    /* Resolution register carries 800x480 big-endian. */
    assert(t[12].data[0] == 0x03 && t[12].data[1] == 0x20);
    assert(t[12].data[2] == 0x01 && t[12].data[3] == 0xE0);
    assert(t[0].data[0] == 0x49 && t[0].data[5] == 0x18);

    const epd_trial_cmd_t *r = epd_trial_refresh_cmd();
    assert(r != NULL && r->cmd == EPD_TRIAL_CMD_REFRESH);
    assert(r->len == 1 && r->data[0] == 0x00);
}

static void test_rejects_bad_input(void)
{
    uint8_t *in = calloc(PIXELS, 1);
    uint8_t *out = malloc(EPD_TRIAL_PACKED_BYTES);
    assert(in && out);

    /* Wrong pixel count. */
    memset(out, 0xEE, EPD_TRIAL_PACKED_BYTES);
    assert(epd_trial_pack_4bpp(in, PIXELS - 1, out, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_ERR_LENGTH);
    assert(epd_trial_pack_4bpp(in, PIXELS + 1, out, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_ERR_LENGTH);
    /* Output buffer too small. */
    assert(epd_trial_pack_4bpp(in, PIXELS, out, EPD_TRIAL_PACKED_BYTES - 1) == EPD_TRIAL_ERR_LENGTH);
    /* Null pointers. */
    assert(epd_trial_pack_4bpp(NULL, PIXELS, out, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_ERR_ARG);
    assert(epd_trial_pack_4bpp(in, PIXELS, NULL, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_ERR_ARG);

    /* Colour codes outside the six valid ones, including the unused 4. */
    static const uint8_t bad[] = {4, 7, 15, 16, 255};
    for (size_t b = 0; b < sizeof(bad); b++) {
        in[PIXELS - 1] = bad[b];
        assert(epd_trial_pack_4bpp(in, PIXELS, out, EPD_TRIAL_PACKED_BYTES) == EPD_TRIAL_ERR_COLOR);
    }
    /* Nothing was written by any rejected call. */
    for (size_t i = 0; i < EPD_TRIAL_PACKED_BYTES; i++) {
        assert(out[i] == 0xEE);
    }
    free(in);
    free(out);
}

static void test_pin_maps(void)
{
    /* EE04 values match the EE02 overlay already used on the real kit. */
    assert(EPD_TRIAL_PINS_EE04.sck == 7 && EPD_TRIAL_PINS_EE04.mosi == 9);
    assert(EPD_TRIAL_PINS_EE04.cs == 44 && EPD_TRIAL_PINS_EE04.dc == 10);
    assert(EPD_TRIAL_PINS_EE04.rst == 38 && EPD_TRIAL_PINS_EE04.busy == 4);
    assert(EPD_TRIAL_PINS_EE04.en == 43);
    assert(EPD_TRIAL_PINS_PHOTOPAINTER.mosi == 11 && EPD_TRIAL_PINS_PHOTOPAINTER.sck == 10);
    assert(EPD_TRIAL_PINS_PHOTOPAINTER.dc == 8 && EPD_TRIAL_PINS_PHOTOPAINTER.cs == 9);
    assert(EPD_TRIAL_PINS_PHOTOPAINTER.rst == 12 && EPD_TRIAL_PINS_PHOTOPAINTER.busy == 13);
    assert(EPD_TRIAL_PINS_PHOTOPAINTER.en == -1);
}

int main(void)
{
    test_pack_size_and_nibble_order();
    test_init_table_order();
    test_rejects_bad_input();
    test_pin_maps();
    printf("epd7in3e_trial: all cases pass\n");
    return 0;
}
