/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Best-effort TLS session resumption across deep sleep (FW-10's optional
 * half - the mandatory half is api_client.c's own in-wake connection
 * reuse). esp_http_client already resumes a session ticket *within* one
 * wake, via CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS + save_client_session:
 * every connect on the same handle after the first tries to reuse the
 * ticket its own previous connect saved. That in-process state lives on
 * the heap, so it is gone the instant deep sleep tears the heap down;
 * this module is the missing piece that carries a copy of it across that
 * boundary in RTC memory, which does survive deep sleep.
 *
 * Why this file reaches into a private ESP-IDF struct: neither
 * esp_http_client nor esp_tls exposes a public "export this session as
 * bytes" API - the ticket lives behind tcp_transport's private
 * transport_esp_tls_t, reachable only via esp_transport_get_context_data
 * and a same-layout struct mirror. mbedtls itself does expose exactly
 * the serialization primitive this needs
 * (mbedtls_ssl_session_save()/_load()), so this file mirrors just enough
 * of that private struct to reach the one field (session_ticket) it
 * needs, then calls the public mbedtls functions to flatten/restore it.
 *
 * Why this is pinned to exactly ESP-IDF v5.3.1: the mirrored struct's
 * field order is not a contract ESP-IDF guarantees stable across
 * releases, even patch releases - CONFIG_SKYPANE_TLS_SESSION_PERSIST is
 * therefore additionally gated on ESP_IDF_VERSION, so the mirror can
 * never silently misread a struct that a future IDF upgrade has
 * reordered. Outside that exact pin (or with the Kconfig option off, or
 * without session tickets enabled), every function below is a no-op:
 * the device simply pays a full TLS handshake every wake, exactly as it
 * did before this file existed. Any load/save failure inside the pinned
 * path degrades the same way - it forgets the saved session and falls
 * back to a full handshake - never aborts a wake.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_transport.h"

/* Offers a session saved by a previous wake to ssl (a not-yet-connected
 * SSL transport), if one was saved for the same origin. Call once, right
 * after creating the transport, before the wake's first
 * esp_http_client_open(). Returns true if a session was offered - used
 * only for the fp_api diagnostic line; callers never branch on it. */
bool fp_tls_session_offer(esp_transport_handle_t ssl, const char *origin);

/* Serializes ssl's current session (already populated by
 * esp_http_client's own save_client_session machinery right after
 * connecting) into RTC memory for the next wake to offer. Call once,
 * after the first request on ssl has returned any HTTP status this
 * wake. A session that does not fit, or fails to serialize, is logged
 * and dropped - never fatal to the wake. */
void fp_tls_session_save(esp_transport_handle_t ssl, const char *origin);

/* Drops any session saved by a previous wake, so a stale or unusable one
 * is never offered again. Call when a connect that was offered a saved
 * session fails - a session that led to a broken connect is worse than
 * no session at all. */
void fp_tls_session_forget(void);

/* True if fp_tls_session_offer() offered a session this wake. */
bool fp_tls_session_offered(void);

/* Byte length of the session saved this wake by fp_tls_session_save(),
 * or 0 if none was saved this wake. */
uint32_t fp_tls_session_saved_len(void);
