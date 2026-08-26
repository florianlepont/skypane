/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Trimmed from flightportrait/frame's `main/wifi.h` (@ ce3335fc). Upstream
 * loads STA credentials from NVS because a BLE provisioning flow put them
 * there; this project has no provisioning this phase, so the credential
 * source is the SKYPANE_WIFI_SSID / SKYPANE_WIFI_PASS macros in the gitignored
 * secrets.h instead. Fast-connect hints (remembered BSSID/channel) are
 * dropped along with the NVS keys they depended on — see
 * firmware/main/nvs_schema.h. */
#pragma once

#include "esp_err.h"

/* Bring up the Wi-Fi/netif/event-loop platform. Idempotent — safe to
 * call more than once during one boot. */
esp_err_t fp_wifi_platform_init(void);

/* Join the network named by SKYPANE_WIFI_SSID/SKYPANE_WIFI_PASS and sync the
 * clock over SNTP (a TLS prerequisite after any power loss, since the
 * device has no RTC battery). Blocks up to timeout_ms. */
esp_err_t fp_wifi_connect(int timeout_ms);

/* 0 if unknown (not connected, or no AP info available). */
int fp_wifi_rssi(void);

/* Radio off before deep sleep — this is what makes the "radio off
 * before sleep" clause of DEVICE-03 true and matters directly for the
 * battery measurement in plan 01-08. */
void fp_wifi_stop(void);
