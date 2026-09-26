/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Best-effort TLS session resumption across deep sleep — the session
 * esp_http_client resumes within one wake lives on the heap and is
 * gone once deep sleep tears it down; this module carries a copy
 * across that boundary in RTC memory. Neither esp_http_client nor
 * esp_tls exposes a public export API, so this reaches into a private
 * ESP-IDF struct via a same-layout mirror, pinned to exactly ESP-IDF
 * v5.3.1 (gated on ESP_IDF_VERSION, so an upgrade cannot silently
 * misread it); outside that pin, or on any failure, every function is
 * a safe no-op — a full handshake every wake, never an aborted one. */
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
