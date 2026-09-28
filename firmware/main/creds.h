/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Pure validators for the device credentials firmware/provision.sh writes
 * into the "secret" NVS partition (Wi-Fi SSID/password, the API base and
 * the optional static-IP set) — kept apart from enrol_secret.c so each
 * rule is a pure function: no ESP-IDF, no I/O, compiled and asserted on a
 * host by firmware/tests/test_creds.c. enrol_secret.c calls these; it
 * does not re-derive the rules itself. The API base's scheme policy
 * (https-only in production, unless CONFIG_SKYPANE_ALLOW_HTTP) is
 * validated separately, by api_client.c's api_base_get() through
 * fp_url_valid() — not repeated here. */
#pragma once

#include <stdbool.h>

/* Every credential fp_device_creds_load (enrol_secret.h) reads from the
 * secret NVS partition. has_static is false whenever no static-IP set is
 * provisioned; ip/mask/gw/dns are then left empty. */
typedef struct {
    char ssid[33];  /* up to 32 bytes + NUL — fp_wifi_ssid_valid */
    char pass[65];  /* up to 64 bytes + NUL; "" is a valid open network */
    char api_base[128];
    bool has_static;
    char ip[16];
    char mask[16];
    char gw[16];
    char dns[16];
} fp_device_creds_t;

/* True iff s is 1 to 32 bytes with no control character (0x00-0x1F or
 * 0x7F, which includes '\n'). NULL or the empty string is false. */
bool fp_wifi_ssid_valid(const char *s);

/* True iff s is "" (an open network) or 8 to 63 bytes of printable ASCII
 * (0x20-0x7E). NULL is false. */
bool fp_wifi_pass_valid(const char *s);

/* True iff s is a dotted-quad IPv4 address: four decimal octets 0-255,
 * separated by exactly three dots, each with no leading zero (the
 * literal single digit "0" is fine; "01" is not). NULL, empty, too few
 * or too many segments, and an out-of-range octet are all false. */
bool fp_ipv4_valid(const char *s);

/* True iff ip/mask/gw/dns are all "" (no static IP provisioned) or all
 * four pass fp_ipv4_valid — never a mix of empty and set, since a
 * partially-provisioned static IP is not something the device can act
 * on safely. */
bool fp_static_ip_set_valid(const char *ip, const char *mask, const char *gw,
                            const char *dns);
