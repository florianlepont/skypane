/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* SkyPane — credential template.
 *
 * Copy this file to `secrets.h` (gitignored — see firmware/.gitignore)
 * and fill in the real values there. `secrets.h` must NEVER be
 * committed, and its contents must NEVER be pasted into a build log, an
 * issue, or a chat transcript.
 *
 * These are the only credentials a SkyPane image needs: Wi-Fi joins
 * with SKYPANE_WIFI_SSID/PASS, and the device talks to SKYPANE_API_BASE.
 * The per-device enrolment secret is NOT compiled in — it is written
 * directly into the device's own `secret` NVS partition by
 * firmware/provision.sh, so the firmware image is identical for every
 * device (see enrol_secret.h).
 */
#pragma once

/* The Wi-Fi network the device joins on every wake. */
#define SKYPANE_WIFI_SSID "your-wifi-ssid"
#define SKYPANE_WIFI_PASS "your-wifi-password"

/* The server's base URL. Production builds require https:// —
 * CONFIG_SKYPANE_ALLOW_HTTP is off by default and rejects anything
 * else. */
#define SKYPANE_API_BASE "https://your-server.example"

/* Optional. Read only when CONFIG_SKYPANE_ALLOW_HTTP is set (dev
 * builds — `SKYPANE_PROFILE=dev ./build.sh`), to reach the LAN stub
 * server (stub-server/) in place of the production base above. */
#define SKYPANE_API_BASE_DEV "http://192.168.1.42:8642"
