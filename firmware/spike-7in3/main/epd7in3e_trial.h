/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Trial driver for a single-controller 7.3" E Ink Spectra 6 panel
 * (800x480, 4 bits per pixel, six colours).
 *
 * The first half of this header is pure: constants, the init command table
 * and the pixel packer have no ESP-IDF dependency and are covered by the
 * host test. The second half (guarded by ESP_PLATFORM) is the thin SPI and
 * GPIO layer. It has only been compiled, never run against a panel.
 */
#ifndef EPD7IN3E_TRIAL_H
#define EPD7IN3E_TRIAL_H

#include <stddef.h>
#include <stdint.h>

#define EPD_TRIAL_WIDTH        800
#define EPD_TRIAL_HEIGHT       480
/* Two pixels per byte, high nibble first. */
#define EPD_TRIAL_PACKED_BYTES ((EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT) / 2)

/* Colour codes the controller expects in each nibble. Code 4 is unused by
 * this panel; it is rejected rather than sent. */
#define EPD_TRIAL_BLACK  0x0
#define EPD_TRIAL_WHITE  0x1
#define EPD_TRIAL_YELLOW 0x2
#define EPD_TRIAL_RED    0x3
#define EPD_TRIAL_BLUE   0x5
#define EPD_TRIAL_GREEN  0x6

/* Controller commands used outside the init table. */
#define EPD_TRIAL_CMD_POWER_OFF 0x02
#define EPD_TRIAL_CMD_POWER_ON  0x04
#define EPD_TRIAL_CMD_DEEP_SLEEP 0x07
#define EPD_TRIAL_CMD_DATA_START 0x10
#define EPD_TRIAL_CMD_REFRESH   0x12

typedef enum {
    EPD_TRIAL_OK = 0,
    EPD_TRIAL_ERR_ARG,    /* null pointer */
    EPD_TRIAL_ERR_LENGTH, /* input is not exactly width*height pixels */
    EPD_TRIAL_ERR_COLOR,  /* a pixel is not one of the six colour codes */
} epd_trial_status_t;

/* One command with up to six data bytes. */
typedef struct {
    uint8_t cmd;
    uint8_t len;
    uint8_t data[6];
} epd_trial_cmd_t;

/* Pin map of one carrier board. Values are GPIO numbers. */
typedef struct {
    int sck;
    int mosi;
    int cs;
    int dc;
    int rst;
    int busy;
    int en; /* panel supply enable, active high */
} epd_trial_pins_t;

/* XIAO ePaper EE04 carrier board (XIAO ESP32-S3 Plus). */
extern const epd_trial_pins_t EPD_TRIAL_PINS_EE04;
/* Waveshare ESP32-S3-PhotoPainter (no panel supply enable pin). */
extern const epd_trial_pins_t EPD_TRIAL_PINS_PHOTOPAINTER;

/* Init sequence, in the order it is sent; the last entry is power-on. */
const epd_trial_cmd_t *epd_trial_init_table(size_t *count);
/* Refresh command (register 0x12, one data byte). */
const epd_trial_cmd_t *epd_trial_refresh_cmd(void);

/* Packs one colour code per pixel (width*height bytes) into 4 bits per
 * pixel. out must hold EPD_TRIAL_PACKED_BYTES. Nothing is written to out
 * unless the whole input validates. */
epd_trial_status_t epd_trial_pack_4bpp(const uint8_t *pixels, size_t pixel_count,
                                       uint8_t *out, size_t out_len);

#ifdef ESP_PLATFORM
#include "esp_err.h"

/* Configures SPI, GPIO and the panel supply, resets the controller and
 * sends the init table. */
esp_err_t epd_trial_init(const epd_trial_pins_t *pins);
/* Sends a packed frame (EPD_TRIAL_PACKED_BYTES), refreshes, powers off. */
esp_err_t epd_trial_blit(const uint8_t *packed);
/* Powers the controller off; deep_sleep additionally sends the deep sleep
 * command, after which the controller needs a full reset and init. */
esp_err_t epd_trial_sleep(int deep_sleep);
#endif

#endif /* EPD7IN3E_TRIAL_H */
