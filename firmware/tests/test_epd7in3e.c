/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host test of the pure parts of the 7.3" driver: pixel packing, the init
 * command table and the pin validator. No ESP-IDF, no hardware; run by
 * tests/run_host_tests.sh. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../main/epd7in3e.h"

#define PIXELS (EPD7_WIDTH * EPD7_HEIGHT)

static void test_pack_size_and_nibble_order(void)
{
    uint8_t *in = malloc(PIXELS);
    uint8_t *out = malloc(EPD7_PACKED_BYTES);
    assert(in && out);
    assert(EPD7_PACKED_BYTES == 192000);

    for (size_t i = 0; i < PIXELS; i++) {
        in[i] = EPD7_WHITE;
    }
    in[0] = EPD7_BLACK;   /* high nibble of byte 0 */
    in[1] = EPD7_GREEN;   /* low nibble of byte 0  */
    in[2] = EPD7_BLUE;    /* high nibble of byte 1 */
    in[3] = EPD7_YELLOW;  /* low nibble of byte 1  */
    in[PIXELS - 2] = EPD7_RED;
    in[PIXELS - 1] = EPD7_BLACK;

    memset(out, 0xEE, EPD7_PACKED_BYTES);
    assert(epd7_pack_4bpp(in, PIXELS, out, EPD7_PACKED_BYTES) == EPD7_OK);
    assert(out[0] == 0x06);
    assert(out[1] == 0x52);
    assert(out[2] == 0x11);
    assert(out[EPD7_PACKED_BYTES - 1] == 0x30);
    for (size_t i = 2; i < EPD7_PACKED_BYTES - 1; i++) {
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
    const epd7_cmd_t *t = epd7_init_table(&count);
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

    const epd7_cmd_t *r = epd7_refresh_cmd();
    assert(r != NULL && r->cmd == EPD7_CMD_REFRESH);
    assert(r->len == 1 && r->data[0] == 0x00);
}

static void test_rejects_bad_input(void)
{
    uint8_t *in = calloc(PIXELS, 1);
    uint8_t *out = malloc(EPD7_PACKED_BYTES);
    assert(in && out);

    /* Wrong pixel count. */
    memset(out, 0xEE, EPD7_PACKED_BYTES);
    assert(epd7_pack_4bpp(in, PIXELS - 1, out, EPD7_PACKED_BYTES) == EPD7_ERR_LENGTH);
    assert(epd7_pack_4bpp(in, PIXELS + 1, out, EPD7_PACKED_BYTES) == EPD7_ERR_LENGTH);
    /* Output buffer too small. */
    assert(epd7_pack_4bpp(in, PIXELS, out, EPD7_PACKED_BYTES - 1) == EPD7_ERR_LENGTH);
    /* Null pointers. */
    assert(epd7_pack_4bpp(NULL, PIXELS, out, EPD7_PACKED_BYTES) == EPD7_ERR_ARG);
    assert(epd7_pack_4bpp(in, PIXELS, NULL, EPD7_PACKED_BYTES) == EPD7_ERR_ARG);

    /* Colour codes outside the six valid ones, including the unused 4. */
    static const uint8_t bad[] = {4, 7, 15, 16, 255};
    for (size_t b = 0; b < sizeof(bad); b++) {
        in[PIXELS - 1] = bad[b];
        assert(epd7_pack_4bpp(in, PIXELS, out, EPD7_PACKED_BYTES) == EPD7_ERR_COLOR);
    }
    /* Nothing was written by any rejected call. */
    for (size_t i = 0; i < EPD7_PACKED_BYTES; i++) {
        assert(out[i] == 0xEE);
    }
    free(in);
    free(out);
}

static void test_pins_valid(void)
{
    /* Board values of the second hardware profile. */
    epd7_pins_t p = {.sck = 7, .mosi = 9, .cs = 44, .dc = 10, .rst = 38,
                     .busy = 4, .en = 43};
    assert(epd7_pins_valid(&p));
    p.en = -1; /* a board without a supply enable pin */
    assert(epd7_pins_valid(&p));
    assert(!epd7_pins_valid(NULL));

    /* Two signals on one pin, including the optional enable. */
    p.en = 43;
    p.dc = p.rst;
    assert(!epd7_pins_valid(&p));
    p.dc = 10;
    p.en = p.busy;
    assert(!epd7_pins_valid(&p));
    /* Out-of-range or unset required signals. */
    p.en = 43;
    p.cs = -1;
    assert(!epd7_pins_valid(&p));
    p.cs = 49;
    assert(!epd7_pins_valid(&p));
    p.cs = 44;
    p.en = 49;
    assert(!epd7_pins_valid(&p));
}

int main(void)
{
    test_pack_size_and_nibble_order();
    test_init_table_order();
    test_rejects_bad_input();
    test_pins_valid();
    printf("epd7in3e: all cases pass\n");
    return 0;
}
