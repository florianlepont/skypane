/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0
 *
 * Modified from FlightPortrait (github.com/flightportrait/frame) for
 * SkyPane; the changes are listed in firmware/VENDOR.md. */
/* SkyPane NVS schema — trimmed from upstream's nvs_schema.h down to
 * everything a device remembers: four keys in the `skypane` namespace
 * on the default `nvs` partition, plus eight more in that namespace on
 * its own dedicated `secret` partition (see firmware/VENDOR.md for what
 * was removed and why). A later phase reintroducing provisioning must
 * migrate this namespace in place, never rename it — a factory reset
 * wipes the default partition's namespace wholesale, silently orphaning
 * a renamed key. */
#pragma once

#define FP_NVS_NAMESPACE "skypane"

/* Bearer token returned by POST /device/v1/setup; sent thereafter as
 * `Authorization: Bearer <token>` on every /display and /log call. */
#define FP_NVS_DEVICE_TOKEN "dev_token"

/* Last successfully blitted image hash, "sha256:<hex>" — compared
 * against the server's next `image_hash` to decide the hash-skip. May
 * also hold FP_FAULT_SCREEN_HASH after the on-device fault screen was
 * drawn — deliberately never shaped like a real server hash, so the
 * first healthy poll after recovery always redraws the real picture. */
#define FP_NVS_IMAGE_HASH "image_hash"

/* Consecutive-failure counter driving fp_backoff_seconds(n). Lives in
 * NVS, not RTC memory, because RTC memory does not survive power loss
 * or a brownout. */
#define FP_NVS_BACKOFF_N "backoff_n"

/* Boot counter — diagnostic only, emitted in the "wake reason=... boot_count=..."
 * log line. */
#define FP_NVS_BOOT_COUNT "boot_count"

/* The enrolment secret's own NVS partition (firmware/partitions.csv),
 * kept apart from the default `nvs` partition above so re-provisioning a
 * device (firmware/provision.sh) can never touch the token, image hash
 * or backoff keys, and so an application factory-reset of the default
 * partition can never erase the one copy of this device's credential.
 * The application only ever reads these keys — it never writes or
 * erases the `secret` partition (enrol_secret.c). */
#define FP_NVS_SECRET_PARTITION "secret"
#define FP_NVS_ENROL_SECRET "enrol_secret"

/* Device credentials, written into the same `secret` partition by
 * firmware/provision.sh alongside the enrolment secret above, so the
 * compiled image carries no credential of its own (enrol_secret.c reads
 * all seven of these keys via fp_device_creds_load). The static-IP keys
 * are optional: either all four are present, or none are — see
 * fp_static_ip_set_valid (creds.h). */
#define FP_NVS_WIFI_SSID "wifi_ssid"
#define FP_NVS_WIFI_PASS "wifi_pass"
#define FP_NVS_API_BASE "api_base"
#define FP_NVS_STATIC_IP "static_ip"
#define FP_NVS_STATIC_MASK "static_mask"
#define FP_NVS_STATIC_GW "static_gw"
#define FP_NVS_STATIC_DNS "static_dns"
