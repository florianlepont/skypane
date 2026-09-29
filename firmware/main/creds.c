/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "creds.h"

#include <string.h>

/* Parses s[0..len) as one dotted-quad octet: 1-3 decimal digits, no
 * leading zero unless the whole segment is the single digit "0", value
 * in 0..255. Never reads past len. */
static bool parse_octet(const char *s, size_t len, int *out)
{
    if (len == 0 || len > 3) {
        return false;
    }
    if (len > 1 && s[0] == '0') {
        return false; /* e.g. "01" */
    }
    int val = 0;
    for (size_t i = 0; i < len; i++) {
        if (s[i] < '0' || s[i] > '9') {
            return false;
        }
        val = val * 10 + (s[i] - '0');
    }
    if (val > 255) {
        return false;
    }
    *out = val;
    return true;
}

bool fp_wifi_ssid_valid(const char *s)
{
    if (!s) {
        return false;
    }
    size_t len = strlen(s);
    if (len < 1 || len > 32) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c < 0x20 || c == 0x7f) {
            return false; /* control character, including '\n' */
        }
    }
    return true;
}

bool fp_wifi_pass_valid(const char *s)
{
    if (!s) {
        return false;
    }
    size_t len = strlen(s);
    if (len == 0) {
        return true; /* open network */
    }
    if (len < 8 || len > 63) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c < 0x20 || c >= 0x7f) {
            return false; /* printable ASCII only */
        }
    }
    return true;
}

bool fp_ipv4_valid(const char *s)
{
    if (!s) {
        return false;
    }
    size_t len = strlen(s);
    if (len == 0 || len > 15) {
        return false; /* "255.255.255.255" is 15 chars, the longest legal form */
    }
    int octets = 0;
    size_t seg_start = 0;
    for (size_t i = 0; i <= len; i++) {
        if (i == len || s[i] == '.') {
            int val;
            if (!parse_octet(s + seg_start, i - seg_start, &val)) {
                return false;
            }
            octets++;
            if (octets > 4) {
                return false;
            }
            seg_start = i + 1;
        }
    }
    return octets == 4;
}

bool fp_static_ip_set_valid(const char *ip, const char *mask, const char *gw,
                            const char *dns)
{
    if (!ip || !mask || !gw || !dns) {
        return false;
    }
    bool all_empty = ip[0] == 0 && mask[0] == 0 && gw[0] == 0 && dns[0] == 0;
    if (all_empty) {
        return true;
    }
    return fp_ipv4_valid(ip) && fp_ipv4_valid(mask) && fp_ipv4_valid(gw) &&
           fp_ipv4_valid(dns);
}
