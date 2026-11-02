/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Trial driver for the single-controller 7.3" Spectra 6 panel.
 *
 * Command order and data bytes of the init table were re-typed from
 * Seeed_GFX2, src/driver/epaper/Driver_ED2208.cpp, Driver_ED2208::init()
 * (https://github.com/Seeed-Studio/Seeed_GFX2, MIT licence, original work
 * by Seeed Studio, raw file read on branch main on 2026-11-01). The same
 * 800x480 panel is driven by the Waveshare reference EPD_7in3e.c
 * (https://github.com/waveshareteam/e-Paper, MIT-style permission notice in
 * the file header), which uses a shorter init with a few different values;
 * hardware/SECOND-HARDWARE-SPIKE.md lists both. Only constants and the
 * command order are taken; the code around them is written for ESP-IDF.
 *
 * Pin maps: XIAO_ePaper_Board_Configs.h (EE04) and the PhotoPainter
 * operating guide, as cited in hardware/SECOND-HARDWARE-SPIKE.md.
 */
#include "epd7in3e_trial.h"

#include <string.h>

const epd_trial_pins_t EPD_TRIAL_PINS_EE04 = {
    .sck = 7, .mosi = 9, .cs = 44, .dc = 10, .rst = 38, .busy = 4, .en = 43,
};

const epd_trial_pins_t EPD_TRIAL_PINS_PHOTOPAINTER = {
    .sck = 10, .mosi = 11, .cs = 9, .dc = 8, .rst = 12, .busy = 13, .en = -1,
};

static const epd_trial_cmd_t k_init_table[] = {
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
    {EPD_TRIAL_CMD_POWER_ON, 0, {0}},
};

static const epd_trial_cmd_t k_refresh = {EPD_TRIAL_CMD_REFRESH, 1, {0x00}};

const epd_trial_cmd_t *epd_trial_init_table(size_t *count)
{
    if (count != NULL) {
        *count = sizeof(k_init_table) / sizeof(k_init_table[0]);
    }
    return k_init_table;
}

const epd_trial_cmd_t *epd_trial_refresh_cmd(void)
{
    return &k_refresh;
}

static int color_valid(uint8_t c)
{
    return c <= EPD_TRIAL_RED || c == EPD_TRIAL_BLUE || c == EPD_TRIAL_GREEN;
}

epd_trial_status_t epd_trial_pack_4bpp(const uint8_t *pixels, size_t pixel_count,
                                       uint8_t *out, size_t out_len)
{
    if (pixels == NULL || out == NULL) {
        return EPD_TRIAL_ERR_ARG;
    }
    if (pixel_count != (size_t)EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT ||
        out_len < EPD_TRIAL_PACKED_BYTES) {
        return EPD_TRIAL_ERR_LENGTH;
    }
    /* Validate everything first so a rejected frame leaves out untouched. */
    for (size_t i = 0; i < pixel_count; i++) {
        if (!color_valid(pixels[i])) {
            return EPD_TRIAL_ERR_COLOR;
        }
    }
    for (size_t i = 0; i < EPD_TRIAL_PACKED_BYTES; i++) {
        out[i] = (uint8_t)((pixels[2 * i] << 4) | pixels[2 * i + 1]);
    }
    return EPD_TRIAL_OK;
}

#ifdef ESP_PLATFORM
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "epd7in3e_trial";

/* Roughly one packed row, so one chip-select assertion covers one row. */
#define ROW_BYTES (EPD_TRIAL_WIDTH / 2)
#define BUSY_TIMEOUT_MS 60000

static spi_device_handle_t s_spi;
static epd_trial_pins_t s_pins;

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

/* The controller drives BUSY high when idle. The first sample is taken
 * after a short pause because BUSY can still read high just after a command. */
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

esp_err_t epd_trial_init(const epd_trial_pins_t *pins)
{
    if (pins == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    s_pins = *pins;

    gpio_config_t out = {
        .pin_bit_mask = (1ULL << pins->dc) | (1ULL << pins->rst),
        .mode = GPIO_MODE_OUTPUT,
    };
    if (pins->en >= 0) {
        out.pin_bit_mask |= 1ULL << pins->en;
    }
    esp_err_t err = gpio_config(&out);
    if (err != ESP_OK) {
        return err;
    }
    gpio_config_t in = {
        .pin_bit_mask = 1ULL << pins->busy,
        .mode = GPIO_MODE_INPUT,
    };
    err = gpio_config(&in);
    if (err != ESP_OK) {
        return err;
    }
    if (pins->en >= 0) {
        gpio_set_level(pins->en, 1);
        delay_ms(20);
    }

    spi_bus_config_t bus = {
        .mosi_io_num = pins->mosi,
        .miso_io_num = -1,
        .sclk_io_num = pins->sck,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = ROW_BYTES,
    };
    err = spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    if (err != ESP_OK) {
        return err;
    }
    spi_device_interface_config_t dev = {
        .clock_speed_hz = 10 * 1000 * 1000,
        .mode = 0,
        .spics_io_num = pins->cs,
        .queue_size = 1,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    err = spi_bus_add_device(SPI2_HOST, &dev, &s_spi);
    if (err != ESP_OK) {
        return err;
    }

    /* Hardware reset: high 20 ms, low 10 ms, high 20 ms. */
    gpio_set_level(pins->rst, 1);
    delay_ms(20);
    gpio_set_level(pins->rst, 0);
    delay_ms(10);
    gpio_set_level(pins->rst, 1);
    delay_ms(20);

    size_t count = 0;
    const epd_trial_cmd_t *table = epd_trial_init_table(&count);
    for (size_t i = 0; i < count; i++) {
        err = send_cmd(table[i].cmd);
        if (err == ESP_OK && table[i].len > 0) {
            err = send_data(table[i].data, table[i].len);
        }
        if (err != ESP_OK) {
            return err;
        }
    }
    return wait_ready(); /* the table ends with power-on */
}

esp_err_t epd_trial_blit(const uint8_t *packed)
{
    if (packed == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = send_cmd(EPD_TRIAL_CMD_DATA_START);
    for (size_t row = 0; err == ESP_OK && row < EPD_TRIAL_HEIGHT; row++) {
        err = send_data(packed + row * ROW_BYTES, ROW_BYTES);
    }
    if (err != ESP_OK) {
        return err;
    }
    const epd_trial_cmd_t *r = epd_trial_refresh_cmd();
    err = send_cmd(r->cmd);
    if (err == ESP_OK) {
        err = send_data(r->data, r->len);
    }
    if (err == ESP_OK) {
        err = wait_ready();
    }
    return err;
}

esp_err_t epd_trial_sleep(int deep_sleep)
{
    static const uint8_t zero = 0x00;
    static const uint8_t check = 0xA5;
    esp_err_t err = send_cmd(EPD_TRIAL_CMD_POWER_OFF);
    if (err == ESP_OK) {
        err = send_data(&zero, 1);
    }
    if (err == ESP_OK) {
        err = wait_ready();
    }
    if (err == ESP_OK && deep_sleep) {
        err = send_cmd(EPD_TRIAL_CMD_DEEP_SLEEP);
        if (err == ESP_OK) {
            err = send_data(&check, 1);
        }
    }
    return err;
}
#endif /* ESP_PLATFORM */
