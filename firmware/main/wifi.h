/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
/* Trimmed from flightportrait/frame's `main/wifi.h` (@ ce3335fc). Upstream
 * loads STA credentials from NVS because a BLE provisioning flow put them
 * there; this project loads them from NVS too, but from its own "secret"
 * partition, written by firmware/provision.sh rather than a BLE flow —
 * see enrol_secret.h's fp_device_creds_load(). Fast-connect hints
 * (remembered BSSID/channel) are dropped along with the NVS keys they
 * depended on — see firmware/main/nvs_schema.h. */
#pragma once

#include "esp_err.h"

/* Bring up the Wi-Fi/netif/event-loop platform. Idempotent — safe to
 * call more than once during one boot. */
esp_err_t fp_wifi_platform_init(void);

/* Loads the provisioned Wi-Fi SSID/password (and, if set, the static-IP
 * set) from the secret NVS partition, joins that network, and syncs the
 * clock over SNTP (a TLS prerequisite after any power loss, since the
 * device has no RTC battery). Blocks up to timeout_ms. Returns
 * FP_ERR_CONFIG (api_client.h) without any radio activity if the
 * provisioned credentials are missing or invalid. */
esp_err_t fp_wifi_connect(int timeout_ms);

/* 0 if unknown (not connected, or no AP info available). */
int fp_wifi_rssi(void);

/* Radio off before deep sleep — this is what makes the radio-off-
 * before-sleep guarantee true, and matters directly for battery life. */
void fp_wifi_stop(void);
