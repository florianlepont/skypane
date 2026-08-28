/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#include "battery.h"

#include "driver/gpio.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

#include "battery_math.h"

static const char *TAG = "fp_batt";

/* EE02 driver board sense pins (Phase 5 / DEVICE-04) - see
 * Kconfig.projbuild's "Battery sense" menu for provenance and caveats. */
#define PIN_BATT_ADC CONFIG_FP_PIN_BATTERY_ADC
#define PIN_BATT_EN  CONFIG_FP_PIN_BATTERY_ADC_EN

/* The divider needs a moment to settle after its enable line goes high
 * before the sample is meaningful. */
#define FP_BATTERY_SETTLE_MS 10

/* -1 = not yet read this wake. Deep sleep clears RAM, so this static gives
 * exactly one ADC read per wake with no change to app_main.c. */
static int s_cached_mv = -1;

uint32_t fp_battery_mv(void)
{
    if (s_cached_mv >= 0) {
        return (uint32_t)s_cached_mv;
    }

    /* A battery-telemetry failure must degrade to the unknown sentinel,
     * never take the device down - so no ESP_ERROR_CHECK() here, unlike
     * epd13in3e.c's own panel-pin setup. */
    gpio_config_t en_cfg = {
        .pin_bit_mask = 1ULL << PIN_BATT_EN,
        .mode = GPIO_MODE_OUTPUT,
    };
    esp_err_t err = gpio_config(&en_cfg);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "battery enable-line config failed: %d", err);
        s_cached_mv = 0;
        return 0;
    }
    gpio_set_level(PIN_BATT_EN, 1);
    vTaskDelay(pdMS_TO_TICKS(FP_BATTERY_SETTLE_MS));

    /* Resolve the configured sense GPIO to a unit/channel rather than
     * hardcoding a channel number, so the Kconfig GPIO stays the single
     * source of truth and cannot drift from a separately configured
     * channel. */
    adc_unit_t unit;
    adc_channel_t channel;
    err = adc_oneshot_io_to_channel(PIN_BATT_ADC, &unit, &channel);
    if (err != ESP_OK || unit != ADC_UNIT_1) {
        ESP_LOGW(TAG, "battery ADC GPIO %d does not resolve to ADC unit 1",
                 PIN_BATT_ADC);
        gpio_set_level(PIN_BATT_EN, 0);
        s_cached_mv = 0;
        return 0;
    }

    adc_oneshot_unit_handle_t adc1 = NULL;
    adc_oneshot_unit_init_cfg_t init_cfg = { .unit_id = ADC_UNIT_1 };
    err = adc_oneshot_new_unit(&init_cfg, &adc1);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "adc_oneshot_new_unit failed: %d", err);
        gpio_set_level(PIN_BATT_EN, 0);
        s_cached_mv = 0;
        return 0;
    }

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    err = adc_oneshot_config_channel(adc1, channel, &chan_cfg);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "adc_oneshot_config_channel failed: %d", err);
        adc_oneshot_del_unit(adc1);
        gpio_set_level(PIN_BATT_EN, 0);
        s_cached_mv = 0;
        return 0;
    }

    adc_cali_handle_t cali = NULL;
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    err = adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "adc_cali_create_scheme_curve_fitting failed: %d", err);
        adc_oneshot_del_unit(adc1);
        gpio_set_level(PIN_BATT_EN, 0);
        s_cached_mv = 0;
        return 0;
    }

    int pin_mv = 0;
    err = adc_oneshot_get_calibrated_result(adc1, cali, channel, &pin_mv);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "adc_oneshot_get_calibrated_result failed: %d", err);
        adc_cali_delete_scheme_curve_fitting(cali);
        adc_oneshot_del_unit(adc1);
        gpio_set_level(PIN_BATT_EN, 0);
        s_cached_mv = 0;
        return 0;
    }

    uint32_t pack_mv = battery_math_apply_divider((uint32_t)pin_mv);
    adc_cali_delete_scheme_curve_fitting(cali);
    adc_oneshot_del_unit(adc1);
    gpio_set_level(PIN_BATT_EN, 0);

    s_cached_mv = (int)pack_mv;
    /* Both numbers matter: Task 3's whole confirmation is "does the sense
     * pin read roughly half a plausible pack voltage", and a line
     * carrying only the converted value cannot distinguish a working
     * circuit from a coincidence. This line sits outside VENDOR.md's
     * frozen five-line Log Line Contract. */
    ESP_LOGI(TAG, "battery mv=%u pin_mv=%d", (unsigned)pack_mv, pin_mv);
    return pack_mv;
}
