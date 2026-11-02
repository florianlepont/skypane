/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Compile-only entry point for the 7.3" trial driver. This image exists to
 * prove the driver builds against ESP-IDF; it is never flashed. */
#include <stdlib.h>
#include <string.h>

#include "esp_heap_caps.h"
#include "esp_log.h"

#include "epd7in3e_trial.h"

static const char *TAG = "spike_main";

void app_main(void)
{
    uint8_t *pixels = heap_caps_malloc((size_t)EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT, MALLOC_CAP_8BIT);
    uint8_t *packed = heap_caps_malloc(EPD_TRIAL_PACKED_BYTES, MALLOC_CAP_8BIT);
    if (pixels == NULL || packed == NULL) {
        ESP_LOGE(TAG, "no memory for the frame");
        return;
    }
    memset(pixels, EPD_TRIAL_WHITE, (size_t)EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT);
    if (epd_trial_pack_4bpp(pixels, (size_t)EPD_TRIAL_WIDTH * EPD_TRIAL_HEIGHT,
                            packed, EPD_TRIAL_PACKED_BYTES) != EPD_TRIAL_OK) {
        return;
    }
    if (epd_trial_init(&EPD_TRIAL_PINS_EE04) == ESP_OK &&
        epd_trial_blit(packed) == ESP_OK) {
        epd_trial_sleep(0);
    }
    free(pixels);
    free(packed);
}
