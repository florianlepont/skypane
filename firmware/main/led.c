/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
#include "led.h"

#include <stdbool.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "sdkconfig.h"

static const char *TAG = "fp_led";

/* See Kconfig.projbuild's "Bring-up LED" menu for provenance. */
#define PIN_LED CONFIG_FP_PIN_LED

/* -1 = not yet configured this wake. Deep sleep clears RAM, so this
 * static gives lazy, once-per-wake pad configuration with no change to
 * app_main.c's boot sequence. */
static bool s_configured = false;

/* A bring-up aid must never be able to take the device down: a GPIO
 * configuration failure here warns and returns rather than aborting,
 * mirroring battery.c's error discipline (no fatal abort-on-error macro
 * anywhere in this file), unlike epd13in3e.c's fatal panel-pin setup. */
static bool led_configure(void)
{
    if (s_configured) {
        return true;
    }
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << PIN_LED,
        .mode = GPIO_MODE_OUTPUT,
    };
    esp_err_t err = gpio_config(&cfg);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "GPIO %d config failed: %d", PIN_LED, err);
        return false;
    }
    s_configured = true;
    return true;
}

/* Polarity is configuration-driven (CONFIG_FP_LED_ACTIVE_LOW), not a
 * hardcoded ternary: if the real polarity turns out inverted, the
 * correction is a reflash of this one Kconfig value, not a code edit.
 * The pad additionally reverts to high impedance in deep sleep by
 * default (no GPIO hold is enabled anywhere in this file), which for an
 * active-low LED tied to the rail also reads as off - so the explicit
 * fp_led_off() call below is belt-and-braces over a safe default, not
 * the only defence. */
void fp_led_on(void)
{
    if (!led_configure()) {
        return;
    }
#if CONFIG_FP_LED_ACTIVE_LOW
    gpio_set_level(PIN_LED, 0);
#else
    gpio_set_level(PIN_LED, 1);
#endif
}

void fp_led_off(void)
{
    /* Must be correct even if fp_led_on() never ran this wake - routing
     * through led_configure() here (rather than assuming it already ran)
     * is what keeps a future reordering of app_main.c from silently
     * writing to an unconfigured pad. */
    if (!led_configure()) {
        return;
    }
#if CONFIG_FP_LED_ACTIVE_LOW
    gpio_set_level(PIN_LED, 1);
#else
    gpio_set_level(PIN_LED, 0);
#endif
}
