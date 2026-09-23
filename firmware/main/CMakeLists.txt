idf_component_register(
    SRC_DIRS "."
    INCLUDE_DIRS "."
    REQUIRES "nvs_flash" "esp_timer" "driver" "heap"
              "esp_wifi" "esp_netif" "esp_event" "esp_http_client" "esp-tls"
              "mbedtls" "json" "esp_app_format" "esp_hw_support" "esp_adc"
              "tcp_transport"
)
