/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Driver for the single-controller 7.3" Spectra 6 panel.
 *
 * Command order and data bytes of the init table were re-typed from
 * Seeed_GFX2, src/driver/epaper/Driver_ED2208.cpp, Driver_ED2208::init()
 * (https://github.com/Seeed-Studio/Seeed_GFX2, raw file read on branch main
 * on 2026-11-01, sha256 7350cf3dc95d7116...). Only constants and the command
 * order are taken; the code around them is written for ESP-IDF. Seeed_GFX2
 * is distributed under the MIT licence, reproduced here as required:
 *
 *   MIT License
 *
 *   Copyright (c) 2026 Seeed Studio
 *
 *   Permission is hereby granted, free of charge, to any person obtaining a
 *   copy of this software and associated documentation files (the
 *   "Software"), to deal in the Software without restriction, including
 *   without limitation the rights to use, copy, modify, merge, publish,
 *   distribute, sublicense, and/or sell copies of the Software, and to
 *   permit persons to whom the Software is furnished to do so, subject to
 *   the following conditions:
 *
 *   The above copyright notice and this permission notice shall be included
 *   in all copies or substantial portions of the Software.
 *
 *   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 *   OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 *   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 *   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 *   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 *   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 *   SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 * The same 800x480 panel is driven by the Waveshare reference EPD_7in3e.c
 * (https://github.com/waveshareteam/e-Paper), which uses a shorter init with
 * a few different values; hardware/SECOND-HARDWARE-SPIKE.md lists both.
 */
#include "epd7in3e.h"

#include <string.h>

static const epd7_cmd_t k_init_table[] = {
    {0xAA, 6, {0x49, 0x55, 0x20, 0x08, 0x09, 0x18}},
    {0x01, 6, {0x3F, 0x00, 0x32, 0x2A, 0x0E, 0x2A}},
    {0x00, 2, {0x5F, 0x69}},
    {0x03, 4, {0x00, 0x54, 0x00, 0x44}},
    {0x05, 4, {0x40, 0x1F, 0x1F, 0x2C}},
    {0x06, 4, {0x6F, 0x1F, 0x16, 0x25}},
    {0x08, 4, {0x6F, 0x1F, 0x1F, 0x22}},
    {0x13, 2, {0x00, 0x04}},
    {0x30, 1, {0x02}},
    {0x41, 1, {0x00}},
    {0x50, 1, {0x3F}},
    {0x60, 2, {0x02, 0x00}},
    /* Resolution: 800 = 0x0320, 480 = 0x01E0, big-endian. */
    {0x61, 4, {0x03, 0x20, 0x01, 0xE0}},
    {0x82, 1, {0x1E}},
    {0x84, 1, {0x01}},
    {0x86, 1, {0x00}},
    {0xE3, 1, {0x2F}},
    {0xE0, 1, {0x00}},
    {0xE6, 1, {0x00}},
    {EPD7_CMD_POWER_ON, 0, {0}},
};

static const epd7_cmd_t k_refresh = {EPD7_CMD_REFRESH, 1, {0x00}};

const epd7_cmd_t *epd7_init_table(size_t *count)
{
    if (count != NULL) {
        *count = sizeof(k_init_table) / sizeof(k_init_table[0]);
    }
    return k_init_table;
}

const epd7_cmd_t *epd7_refresh_cmd(void)
{
    return &k_refresh;
}

int epd7_pins_valid(const epd7_pins_t *pins)
{
    if (pins == NULL) {
        return 0;
    }
    const int sig[] = {pins->sck, pins->mosi, pins->cs, pins->dc, pins->rst,
                       pins->busy};
    const size_t n = sizeof(sig) / sizeof(sig[0]);
    for (size_t i = 0; i < n; i++) {
        if (sig[i] < 0 || sig[i] > 48) {
            return 0;
        }
        for (size_t j = i + 1; j < n; j++) {
            if (sig[i] == sig[j]) {
                return 0;
            }
        }
        if (pins->en == sig[i]) {
            return 0;
        }
    }
    return pins->en >= -1 && pins->en <= 48;
}

static int color_valid(uint8_t c)
{
    return c <= EPD7_RED || c == EPD7_BLUE || c == EPD7_GREEN;
}

epd7_status_t epd7_pack_4bpp(const uint8_t *pixels, size_t pixel_count,
                             uint8_t *out, size_t out_len)
{
    if (pixels == NULL || out == NULL) {
        return EPD7_ERR_ARG;
    }
    if (pixel_count != (size_t)EPD7_WIDTH * EPD7_HEIGHT ||
        out_len < EPD7_PACKED_BYTES) {
        return EPD7_ERR_LENGTH;
    }
    /* Validate everything first so a rejected frame leaves out untouched. */
    for (size_t i = 0; i < pixel_count; i++) {
        if (!color_valid(pixels[i])) {
            return EPD7_ERR_COLOR;
        }
    }
    for (size_t i = 0; i < EPD7_PACKED_BYTES; i++) {
        out[i] = (uint8_t)((pixels[2 * i] << 4) | pixels[2 * i + 1]);
    }
    return EPD7_OK;
}

#if defined(ESP_PLATFORM) && defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#include <stdbool.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

static const char *TAG = "epd7in3e";

/* One packed row, so one chip-select assertion covers one row. */
#define ROW_BYTES (EPD7_WIDTH / 2)
#define BUSY_TIMEOUT_MS 60000

_Static_assert(CONFIG_FP_PANEL_BUFFER_BYTES == EPD7_PACKED_BYTES,
               "sdkconfig buffer size must match the 800x480 packed frame");

static spi_device_handle_t s_spi;
static bool s_bus_up;
static epd7_pins_t s_pins;

static void delay_ms(uint32_t ms)
{
    if (ms < 10) {
        esp_rom_delay_us(ms * 1000);
    } else {
        vTaskDelay(pdMS_TO_TICKS(ms));
    }
}

static esp_err_t tx(const uint8_t *buf, size_t len)
{
    spi_transaction_t t;
    memset(&t, 0, sizeof(t));
    t.length = len * 8;
    t.tx_buffer = buf;
    return spi_device_polling_transmit(s_spi, &t);
}

static esp_err_t send_cmd(uint8_t cmd)
{
    gpio_set_level(s_pins.dc, 0);
    return tx(&cmd, 1);
}

static esp_err_t send_data(const uint8_t *data, size_t len)
{
    gpio_set_level(s_pins.dc, 1);
    return tx(data, len);
}

static esp_err_t send_cmd_data(const epd7_cmd_t *c)
{
    esp_err_t err = send_cmd(c->cmd);
    if (err == ESP_OK && c->len > 0) {
        err = send_data(c->data, c->len);
    }
    return err;
}

/* The controller drives BUSY high when idle. The first sample is taken
 * after a short pause because BUSY can still read high just after a command.
 * The task watchdog is fed by the yield in delay_ms. */
static esp_err_t wait_ready(void)
{
    delay_ms(10);
    int64_t start = esp_timer_get_time();
    while (!gpio_get_level(s_pins.busy)) {
        if ((esp_timer_get_time() - start) / 1000 > BUSY_TIMEOUT_MS) {
            ESP_LOGE(TAG, "BUSY timeout");
            return ESP_ERR_TIMEOUT;
        }
        delay_ms(1);
    }
    return ESP_OK;
}

static void release_bus(void)
{
    if (s_spi != NULL) {
        spi_bus_remove_device(s_spi);
        s_spi = NULL;
    }
    if (s_bus_up) {
        spi_bus_free(SPI2_HOST);
        s_bus_up = false;
    }
}

static esp_err_t setup_io(void)
{
    gpio_config_t out = {
        .pin_bit_mask = (1ULL << s_pins.dc) | (1ULL << s_pins.rst),
        .mode = GPIO_MODE_OUTPUT,
    };
    if (s_pins.en >= 0) {
        out.pin_bit_mask |= 1ULL << s_pins.en;
    }
    esp_err_t err = gpio_config(&out);
    if (err != ESP_OK) {
        return err;
    }
    gpio_config_t in = {
        .pin_bit_mask = 1ULL << s_pins.busy,
        .mode = GPIO_MODE_INPUT,
    };
    err = gpio_config(&in);
    if (err != ESP_OK) {
        return err;
    }
    if (s_pins.en >= 0) {
        gpio_set_level(s_pins.en, 1);
        delay_ms(20);
    }

    spi_bus_config_t bus = {
        .mosi_io_num = s_pins.mosi,
        .miso_io_num = -1,
        .sclk_io_num = s_pins.sck,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = ROW_BYTES,
    };
    err = spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    if (err != ESP_OK) {
        return err;
    }
    s_bus_up = true;
    spi_device_interface_config_t dev = {
        .clock_speed_hz = 10 * 1000 * 1000,
        .mode = 0,
        .spics_io_num = s_pins.cs,
        .queue_size = 1,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    return spi_bus_add_device(SPI2_HOST, &dev, &s_spi);
}

esp_err_t epd7in3e_init(void)
{
    s_pins = (epd7_pins_t){
        .sck = CONFIG_FP_PIN_EPD_SCK,
        .mosi = CONFIG_FP_PIN_EPD_MOSI,
        .cs = CONFIG_FP_PIN_EPD_CS_M,
        .dc = CONFIG_FP_PIN_EPD_DC,
        .rst = CONFIG_FP_PIN_EPD_RST,
        .busy = CONFIG_FP_PIN_EPD_BUSY,
        .en = CONFIG_FP_PIN_EPD_EN,
    };
    if (!epd7_pins_valid(&s_pins)) {
        ESP_LOGE(TAG, "invalid pin map");
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = setup_io();
    if (err != ESP_OK) {
        release_bus();
        return err;
    }

    /* Hardware reset: high 20 ms, low 10 ms, high 20 ms. */
    gpio_set_level(s_pins.rst, 1);
    delay_ms(20);
    gpio_set_level(s_pins.rst, 0);
    delay_ms(10);
    gpio_set_level(s_pins.rst, 1);
    delay_ms(20);

    size_t count = 0;
    const epd7_cmd_t *table = epd7_init_table(&count);
    for (size_t i = 0; err == ESP_OK && i < count; i++) {
        err = send_cmd_data(&table[i]);
    }
    if (err == ESP_OK) {
        err = wait_ready(); /* the table ends with power-on */
    }
    return err;
}

esp_err_t epd7in3e_blit(const uint8_t *packed)
{
    if (packed == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = send_cmd(EPD7_CMD_DATA_START);
    for (size_t row = 0; err == ESP_OK && row < EPD7_HEIGHT; row++) {
        err = send_data(packed + row * ROW_BYTES, ROW_BYTES);
    }
    if (err == ESP_OK) {
        err = send_cmd_data(epd7_refresh_cmd());
    }
    if (err == ESP_OK) {
        err = wait_ready();
    }
    return err;
}

void epd7in3e_sleep(void)
{
    static const uint8_t zero = 0x00;
    static const uint8_t check = 0xA5;
    if (s_spi != NULL) {
        /* Best effort: whatever fails here, the rails still go down below. */
        if (send_cmd(EPD7_CMD_POWER_OFF) == ESP_OK &&
            send_data(&zero, 1) == ESP_OK && wait_ready() == ESP_OK &&
            send_cmd(EPD7_CMD_DEEP_SLEEP) == ESP_OK) {
            send_data(&check, 1);
        }
    }
    release_bus();
    if (s_pins.en >= 0) {
        gpio_set_level(s_pins.en, 0);
    }
}
#endif /* ESP_PLATFORM && CONFIG_FP_PANEL_7IN3E */
