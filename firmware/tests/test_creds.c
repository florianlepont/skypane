/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for every provisioned-credential validator
 * (firmware/main/creds.c): Wi-Fi SSID/password, dotted-quad IPv4, and the
 * all-or-nothing static-IP set.
 *
 *   cc -Wall -Wextra -std=c11 main/creds.c tests/test_creds.c \
 *      -o /tmp/tc && /tmp/tc
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../main/creds.h"

static void wifi_ssid_valid_cases(void)
{
    assert(fp_wifi_ssid_valid("home") == true);

    char max_ssid[33];
    memset(max_ssid, 'a', 32);
    max_ssid[32] = 0;
    assert(fp_wifi_ssid_valid(max_ssid) == true); /* 32 bytes, fits */

    char too_long[34];
    memset(too_long, 'a', 33);
    too_long[33] = 0;
    assert(fp_wifi_ssid_valid(too_long) == false); /* 33 bytes, one too many */

    assert(fp_wifi_ssid_valid("") == false);
    assert(fp_wifi_ssid_valid("bad\nname") == false); /* control char */
    assert(fp_wifi_ssid_valid(NULL) == false);
}

static void wifi_pass_valid_cases(void)
{
    assert(fp_wifi_pass_valid("") == true); /* open network */
    assert(fp_wifi_pass_valid("12345678") == true); /* 8 chars, the floor */

    char max_pass[64];
    memset(max_pass, 'a', 63);
    max_pass[63] = 0;
    assert(fp_wifi_pass_valid(max_pass) == true); /* 63 bytes, fits */

    assert(fp_wifi_pass_valid("1234567") == false); /* 7 chars, too short */

    char too_long[65];
    memset(too_long, 'a', 64);
    too_long[64] = 0;
    assert(fp_wifi_pass_valid(too_long) == false); /* 64 bytes, one too many */

    char high_byte[9] = "1234567";
    high_byte[7] = (char)0x7f;
    high_byte[8] = 0;
    assert(fp_wifi_pass_valid(high_byte) == false); /* byte >= 0x7f */

    assert(fp_wifi_pass_valid(NULL) == false);
}

static void ipv4_valid_cases(void)
{
    assert(fp_ipv4_valid("192.168.1.50") == true);
    assert(fp_ipv4_valid("0.0.0.0") == true);       /* the one legal leading zero */
    assert(fp_ipv4_valid("255.255.255.255") == true);

    assert(fp_ipv4_valid("256.1.1.1") == false);    /* octet out of range */
    assert(fp_ipv4_valid("1.2.3") == false);        /* too few segments */
    assert(fp_ipv4_valid("01.2.3.4") == false);      /* leading zero */
    assert(fp_ipv4_valid("1.2.3.4.5") == false);     /* too many segments */
    assert(fp_ipv4_valid("") == false);
    assert(fp_ipv4_valid(NULL) == false);
}

static void static_ip_set_valid_cases(void)
{
    assert(fp_static_ip_set_valid("", "", "", "") == true); /* no static IP */
    assert(fp_static_ip_set_valid("192.168.1.50", "255.255.255.0",
                                  "192.168.1.1", "192.168.1.1") == true);

    assert(fp_static_ip_set_valid("192.168.1.50", "", "", "") == false); /* mixed */
    assert(fp_static_ip_set_valid("192.168.1.50", "255.255.255.0",
                                  "192.168.1.1", "") == false); /* mixed */
    assert(fp_static_ip_set_valid("not-an-ip", "255.255.255.0",
                                  "192.168.1.1", "192.168.1.1") == false); /* invalid */
    assert(fp_static_ip_set_valid(NULL, "255.255.255.0", "192.168.1.1",
                                  "192.168.1.1") == false);
}

int main(void)
{
    wifi_ssid_valid_cases();
    wifi_pass_valid_cases();
    ipv4_valid_cases();
    static_ip_set_valid_cases();
    printf("creds: all cases pass\n");
    return 0;
}
