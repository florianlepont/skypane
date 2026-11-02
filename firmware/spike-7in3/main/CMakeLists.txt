# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
idf_component_register(
    SRCS "epd7in3e_trial.c" "spike_main.c"
    INCLUDE_DIRS "."
    REQUIRES "driver" "esp_rom" "esp_timer" "freertos" "log" "heap"
)
