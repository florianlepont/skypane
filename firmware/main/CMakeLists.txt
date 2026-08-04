idf_component_register(
    SRCS "app_main.c" "backoff.c" "api_base.c" "epd13in3e.c" "panel.c" "panel_guard.c"
         "api_client.c" "wifi.c" "state_machine.c"
    INCLUDE_DIRS "."
    REQUIRES "nvs_flash" "esp_timer" "driver" "heap"
              "esp_wifi" "esp_netif" "esp_event" "esp_http_client" "esp-tls"
              "mbedtls" "json" "esp_app_format" "esp_hw_support"
)
