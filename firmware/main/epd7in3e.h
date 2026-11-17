/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Driver for a single-controller 7.3" E Ink Spectra 6 panel (800x480,
 * 4 bits per pixel, six colours), selected by CONFIG_FP_PANEL_7IN3E.
 *
 * The first half of this header is pure: constants, the init command table,
 * the pin validator and the pixel packer have no ESP-IDF dependency and are
 * covered by the host test. The second half is the thin SPI and GPIO layer,
 * declared only when the 7.3" panel is the configured one, so the default
 * 13.3" image does not reference any of it. Its register sequence is taken
 * from vendor sources and has not yet been seen to refresh a panel; see
 * firmware/VENDOR.md and hardware/SECOND-HARDWARE-SPIKE.md.
 */
#ifndef EPD7IN3E_H
#define EPD7IN3E_H

#include <stddef.h>
#include <stdint.h>

#define EPD7_WIDTH        800
#define EPD7_HEIGHT       480
/* Two pixels per byte, high nibble first. */
#define EPD7_PACKED_BYTES ((EPD7_WIDTH * EPD7_HEIGHT) / 2) /* 192,000 */

/* Colour codes the controller expects in each nibble. Code 4 is unused by
 * this panel; it is rejected rather than sent. */
#define EPD7_BLACK  0x0
#define EPD7_WHITE  0x1
#define EPD7_YELLOW 0x2
#define EPD7_RED    0x3
#define EPD7_BLUE   0x5
#define EPD7_GREEN  0x6

/* Controller commands used outside the init table. */
#define EPD7_CMD_POWER_OFF  0x02
#define EPD7_CMD_POWER_ON   0x04
#define EPD7_CMD_DEEP_SLEEP 0x07
#define EPD7_CMD_DATA_START 0x10
#define EPD7_CMD_REFRESH    0x12

typedef enum {
    EPD7_OK = 0,
    EPD7_ERR_ARG,    /* null pointer */
    EPD7_ERR_LENGTH, /* input is not exactly width*height pixels */
    EPD7_ERR_COLOR,  /* a pixel is not one of the six colour codes */
} epd7_status_t;

/* One command with up to six data bytes. */
typedef struct {
    uint8_t cmd;
    uint8_t len;
    uint8_t data[6];
} epd7_cmd_t;

/* Pin map of one carrier board. Values are GPIO numbers. */
typedef struct {
    int sck;
    int mosi;
    int cs;
    int dc;
    int rst;
    int busy;
    int en; /* panel supply enable, active high; -1 when the board has none */
} epd7_pins_t;

/* Init sequence, in the order it is sent; the last entry is power-on. */
const epd7_cmd_t *epd7_init_table(size_t *count);
/* Refresh command (register 0x12, one data byte). */
const epd7_cmd_t *epd7_refresh_cmd(void);

/* Returns 1 when every signal except en is a usable GPIO number (0..48)
 * and no two signals, en included when present, share a pin; 0 otherwise. */
int epd7_pins_valid(const epd7_pins_t *pins);

/* Packs one colour code per pixel (width*height bytes) into 4 bits per
 * pixel. out must hold EPD7_PACKED_BYTES. Nothing is written to out
 * unless the whole input validates. */
epd7_status_t epd7_pack_4bpp(const uint8_t *pixels, size_t pixel_count,
                             uint8_t *out, size_t out_len);

#if defined(ESP_PLATFORM) && defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#include "esp_err.h"

/* Configures SPI, GPIO and the panel supply from the CONFIG_FP_PIN_EPD_*
 * pins, resets the controller and sends the init table. */
esp_err_t epd7in3e_init(void);
/* Sends a packed frame (EPD7_PACKED_BYTES) and refreshes. */
esp_err_t epd7in3e_blit(const uint8_t *packed);
/* Powers the controller off, puts it in deep sleep, releases the SPI bus
 * and drops the panel supply. The next draw runs the full init again. */
void epd7in3e_sleep(void);
#endif

#endif /* EPD7IN3E_H */
