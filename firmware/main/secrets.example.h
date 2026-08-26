/* SPDX-License-Identifier: Apache-2.0 */
/* SkyPane — Phase 1 credential template.
 *
 * Copy this file to `secrets.h` (gitignored — see firmware/.gitignore,
 * where the ignore rule was placed by plan 01-03 before this file ever
 * existed) and fill in the real values there. `secrets.h` must NEVER be
 * committed, and its contents must NEVER be pasted into a build log, an
 * issue, or a chat transcript.
 *
 * This whole credential-in-a-header arrangement belongs to Phase 1 only:
 * the device talks solely to the local stub server on the developer's
 * own laptop (stub-server/), which the developer fully controls, so
 * there is no BLE provisioning flow at runtime to receive these values
 * instead. A later phase reintroduces real provisioning (ESP-IDF's
 * `wifi_provisioning` component, BLE transport, Security 2) and this
 * file is retired in favour of it.
 */
#pragma once

/* The Wi-Fi network the device joins on every wake. */
#define SKYPANE_WIFI_SSID "your-wifi-ssid"
#define SKYPANE_WIFI_PASS "your-wifi-password"

/* The stub server's base URL: the http scheme, followed by the laptop's
 * LAN IPv4 address, followed by the stub server's port — for example
 * "http://192.168.1.42:8642". Print the real address with
 * `ipconfig getifaddr en0 || ipconfig getifaddr en1` on macOS (see
 * stub-server/README.md "Point the device at it" for the full command
 * and the transport decision behind why this is plain http, not https,
 * for Phase 1 only). */
#define SKYPANE_API_BASE "http://192.168.1.42:8642"

/* The setup secret sent as `provision_secret` in POST /device/v1/setup.
 * The local stub (stub-server/byos_server.py) accepts any value here
 * unless it was started with --secret. */
#define SKYPANE_SETUP_SECRET "dev-setup-secret"
