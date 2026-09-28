/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "creds.h"

/* RED-phase stub: every validator rejects everything, so
 * firmware/tests/test_creds.c fails until the real rules land. */

bool fp_wifi_ssid_valid(const char *s)
{
    (void)s;
    return false;
}

bool fp_wifi_pass_valid(const char *s)
{
    (void)s;
    return false;
}

bool fp_ipv4_valid(const char *s)
{
    (void)s;
    return false;
}

bool fp_static_ip_set_valid(const char *ip, const char *mask, const char *gw,
                            const char *dns)
{
    (void)ip;
    (void)mask;
    (void)gw;
    (void)dns;
    return false;
}
