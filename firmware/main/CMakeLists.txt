idf_component_register(
    SRCS "app_main.c" "backoff.c" "api_base.c"
    INCLUDE_DIRS "."
    REQUIRES "nvs_flash" "esp_timer" "driver"
)
