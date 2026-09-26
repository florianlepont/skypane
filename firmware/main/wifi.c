/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
#include "wifi.h"

#include <string.h>
#include <time.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

#include "secrets.h"

static const char *TAG = "fp_wifi";
static EventGroupHandle_t s_events;
#define CONNECTED_BIT BIT0
#define FAILED_BIT    BIT1
static int s_retries;
static bool s_platform_ready;
static bool s_wifi_started;
static esp_netif_t *s_sta_netif;

#ifdef SKYPANE_STATIC_IP
#if !defined(SKYPANE_STATIC_NETMASK) || !defined(SKYPANE_STATIC_GW) || \
    !defined(SKYPANE_STATIC_DNS)
#error "SKYPANE_STATIC_IP requires SKYPANE_STATIC_NETMASK, SKYPANE_STATIC_GW and SKYPANE_STATIC_DNS to all be defined"
#endif

/* Optional fallback, off unless secrets.h defines all four macros:
 * stops the DHCP client on this netif and assigns a fixed address
 * instead, for measuring against CONFIG_LWIP_DHCP_RESTORE_LAST_IP on
 * hardware. With the DHCP client stopped, esp_netif's own
 * esp_netif_action_connected() posts IP_EVENT_STA_GOT_IP itself once
 * the station associates, so fp_wifi_connect()'s existing wait on that
 * event needs no change. */
static esp_err_t apply_static_ip(esp_netif_t *netif)
{
    esp_err_t err = esp_netif_dhcpc_stop(netif);
    if (err != ESP_OK && err != ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED) {
        ESP_LOGE(TAG, "static IP: dhcpc_stop failed: %s", esp_err_to_name(err));
        return err;
    }

    esp_netif_ip_info_t ip_info = {0};
    if (esp_netif_str_to_ip4(SKYPANE_STATIC_IP, &ip_info.ip) != ESP_OK ||
        esp_netif_str_to_ip4(SKYPANE_STATIC_NETMASK, &ip_info.netmask) != ESP_OK ||
        esp_netif_str_to_ip4(SKYPANE_STATIC_GW, &ip_info.gw) != ESP_OK) {
        ESP_LOGE(TAG, "static IP: malformed address literal");
        return ESP_ERR_INVALID_ARG;
    }
    err = esp_netif_set_ip_info(netif, &ip_info);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "static IP: set_ip_info failed: %s", esp_err_to_name(err));
        return err;
    }

    esp_netif_dns_info_t dns_info = {0};
    dns_info.ip.type = ESP_IPADDR_TYPE_V4;
    if (esp_netif_str_to_ip4(SKYPANE_STATIC_DNS, &dns_info.ip.u_addr.ip4) != ESP_OK) {
        ESP_LOGE(TAG, "static IP: malformed DNS literal");
        return ESP_ERR_INVALID_ARG;
    }
    err = esp_netif_set_dns_info(netif, ESP_NETIF_DNS_MAIN, &dns_info);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "static IP: set_dns_info failed: %s", esp_err_to_name(err));
        return err;
    }

    ESP_LOGI(TAG, "static IP %s", SKYPANE_STATIC_IP);
    return ESP_OK;
}
#endif /* SKYPANE_STATIC_IP */

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retries++ < 3) {
            esp_wifi_connect();
        } else {
            xEventGroupSetBits(s_events, FAILED_BIT);
        }
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        xEventGroupSetBits(s_events, CONNECTED_BIT);
    }
}

esp_err_t fp_wifi_platform_init(void)
{
    if (s_platform_ready) {
        return ESP_OK;
    }
    esp_err_t err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }
    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }
    s_sta_netif = esp_netif_create_default_wifi_sta();
    if (!s_sta_netif) {
        return ESP_FAIL;
    }
#ifdef SKYPANE_STATIC_IP
    err = apply_static_ip(s_sta_netif);
    if (err != ESP_OK) {
        return err;
    }
#endif
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    err = esp_wifi_init(&init);
    if (err != ESP_OK) {
        return err;
    }
    s_events = xEventGroupCreate();
    if (!s_events) {
        return ESP_ERR_NO_MEM;
    }
    err = esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                     on_event, NULL);
    if (err == ESP_OK) {
        err = esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                         on_event, NULL);
    }
    if (err != ESP_OK) {
        return err;
    }
    s_platform_ready = true;
    return ESP_OK;
}

/* No RTC battery: after any deep power loss the clock reads 1970 and TLS
 * certificate validation rejects everything. Sync before any HTTPS call.
 * RTC keeps time through deep sleep (not power loss), so this is cheap
 * on a normal wake — the sane-clock check below skips the wait. */
static esp_err_t sync_time(void)
{
    time_t now = 0;
    time(&now);
    if (now >= 1600000000) {
        return ESP_OK;
    }
    esp_sntp_config_t sntp = ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
    esp_netif_sntp_init(&sntp);
    esp_err_t err = esp_netif_sntp_sync_wait(pdMS_TO_TICKS(10000));
    esp_netif_sntp_deinit();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "SNTP sync failed; TLS unavailable");
        return err;
    }
    ESP_LOGI(TAG, "clock set via SNTP");
    return ESP_OK;
}

esp_err_t fp_wifi_connect(int timeout_ms)
{
    esp_err_t err = fp_wifi_platform_init();
    if (err != ESP_OK) {
        return err;
    }

    wifi_config_t cfg = {0};
    strlcpy((char *)cfg.sta.ssid, SKYPANE_WIFI_SSID, sizeof(cfg.sta.ssid));
    strlcpy((char *)cfg.sta.password, SKYPANE_WIFI_PASS, sizeof(cfg.sta.password));

    s_retries = 0;
    xEventGroupClearBits(s_events, CONNECTED_BIT | FAILED_BIT);
    err = esp_wifi_set_mode(WIFI_MODE_STA);
    if (err == ESP_OK) {
        err = esp_wifi_set_config(WIFI_IF_STA, &cfg);
    }
    memset(&cfg, 0, sizeof(cfg)); /* password lived on the stack */
    if (err == ESP_OK && !s_wifi_started) {
        err = esp_wifi_start();
        if (err == ESP_OK) {
            s_wifi_started = true;
        }
    }
    if (err == ESP_OK) {
        err = esp_wifi_connect();
    }
    if (err != ESP_OK) {
        return err;
    }

    EventBits_t bits = xEventGroupWaitBits(
        s_events, CONNECTED_BIT | FAILED_BIT, pdFALSE, pdFALSE,
        pdMS_TO_TICKS(timeout_ms));
    if (!(bits & CONNECTED_BIT)) {
        ESP_LOGW(TAG, "join failed/timeout");
        return ESP_FAIL;
    }

    if (sync_time() != ESP_OK) {
        return ESP_FAIL;
    }
    return ESP_OK;
}

int fp_wifi_rssi(void)
{
    wifi_ap_record_t ap;
    return esp_wifi_sta_get_ap_info(&ap) == ESP_OK ? ap.rssi : 0;
}

void fp_wifi_stop(void)
{
    if (s_platform_ready) {
        /* Stop unconditionally before deinit; NOT_STARTED is harmless and
         * avoids ESP_ERR_WIFI_NOT_STOPPED on an already-stopped radio. */
        esp_wifi_stop();
        s_wifi_started = false;
        esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                     on_event);
        esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                     on_event);
        esp_wifi_deinit();
        if (s_events) {
            vEventGroupDelete(s_events);
            s_events = NULL;
        }
        s_platform_ready = false;
    }
}
