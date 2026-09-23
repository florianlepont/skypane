/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "tls_session.h"

#include <string.h>

#include "esp_attr.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "sdkconfig.h"

#include "api_base.h" /* FP_API_BASE_MAX */

/* See tls_session.h's header comment for why each of these three
 * conditions has to hold before this file's guarded implementation is
 * compiled in at all. */
#if CONFIG_SKYPANE_TLS_SESSION_PERSIST && CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS && \
    (ESP_IDF_VERSION == ESP_IDF_VERSION_VAL(5, 3, 1))
#define FP_TLS_SESSION_ACTIVE 1
#else
#define FP_TLS_SESSION_ACTIVE 0
#endif

#if FP_TLS_SESSION_ACTIVE

#include <stdlib.h>

#include "esp_tls.h"
#include "esp_transport_ssl.h"
#include "mbedtls/ssl.h"

static const char *TAG = "fp_tls";

/* Mirror of components/tcp_transport/transport_ssl.c's private
 * transport_esp_tls_t at ESP-IDF v5.3.1 - field order and types copied
 * exactly (re-confirmed against the container's own source at plan
 * time) so that casting esp_transport_get_context_data()'s result
 * through this type reaches the real session_ticket field, which
 * neither esp_transport nor esp_tls exposes a public accessor for. Must
 * be re-checked against the real struct on any ESP-IDF upgrade; the
 * FP_TLS_SESSION_ACTIVE guard above compiles this whole block out
 * outside the exact pinned version, so a mismatched mirror can never
 * silently misread memory on an untested IDF release. */
typedef enum {
    FP_MIRROR_TRANS_SSL_INIT = 0,
    FP_MIRROR_TRANS_SSL_CONNECTING,
} fp_mirror_ssl_conn_state_t;

typedef struct {
    esp_tls_t                 *tls;
    esp_tls_cfg_t              cfg;
    bool                       ssl_initialized;
    fp_mirror_ssl_conn_state_t conn_state;
    int                        sockfd;
    esp_tls_client_session_t  *session_ticket;
} fp_transport_esp_tls_mirror_t;

#define FP_TLS_SESSION_MAX 3072

/* Sized generously against a TLS 1.2 session ticket (typically hundreds
 * of bytes); the hardware session prints the real
 * mbedtls_ssl_session_save()-reported size on first connect to confirm
 * this reservation is enough for what Caddy actually issues. */
RTC_DATA_ATTR static uint8_t s_blob[FP_TLS_SESSION_MAX];
RTC_DATA_ATTR static uint16_t s_len;
RTC_DATA_ATTR static char s_origin[FP_API_BASE_MAX];

/* Per-wake diagnostic state, deliberately NOT in RTC memory - it
 * describes only what happened during this boot's wake, not anything
 * that should survive to the next one. */
static bool s_offered_this_wake;
static uint32_t s_saved_len_this_wake;

bool fp_tls_session_offer(esp_transport_handle_t ssl, const char *origin)
{
    s_offered_this_wake = false;
    if (!ssl || !origin || s_len == 0) {
        return false;
    }
    if (strncmp(s_origin, origin, sizeof(s_origin)) != 0) {
        return false; /* saved for a different server - never cross-offer */
    }

    esp_tls_client_session_t *session = calloc(1, sizeof(*session));
    if (!session) {
        return false;
    }
    mbedtls_ssl_session_init(&session->saved_session);
    int ret = mbedtls_ssl_session_load(&session->saved_session, s_blob, s_len);
    if (ret != 0) {
        ESP_LOGW(TAG, "saved TLS session did not load (mbedtls %d); discarding", ret);
        mbedtls_ssl_session_free(&session->saved_session);
        free(session);
        fp_tls_session_forget();
        return false;
    }

    fp_transport_esp_tls_mirror_t *mirror = esp_transport_get_context_data(ssl);
    if (!mirror) {
        mbedtls_ssl_session_free(&session->saved_session);
        free(session);
        return false;
    }
    esp_tls_free_client_session(mirror->session_ticket);
    mirror->session_ticket = session;
    esp_transport_ssl_session_ticket_operation(ssl, ESP_TRANSPORT_SESSION_TICKET_USE);

    s_offered_this_wake = true;
    ESP_LOGI(TAG, "offering a saved TLS session (%u bytes)", (unsigned)s_len);
    return true;
}

void fp_tls_session_save(esp_transport_handle_t ssl, const char *origin)
{
    if (!ssl || !origin) {
        return;
    }
    fp_transport_esp_tls_mirror_t *mirror = esp_transport_get_context_data(ssl);
    if (!mirror || !mirror->session_ticket) {
        return; /* nothing to save - e.g. the connect never completed */
    }

    size_t olen = 0;
    int ret = mbedtls_ssl_session_save(&mirror->session_ticket->saved_session,
                                       s_blob, sizeof(s_blob), &olen);
    if (ret != 0) {
        if (ret == MBEDTLS_ERR_SSL_BUFFER_TOO_SMALL) {
            ESP_LOGW(TAG, "TLS session needs %u bytes, have %u; not persisted",
                     (unsigned)olen, (unsigned)FP_TLS_SESSION_MAX);
        } else {
            ESP_LOGW(TAG, "TLS session save failed (mbedtls %d); not persisted", ret);
        }
        fp_tls_session_forget();
        return;
    }

    s_len = (uint16_t)olen;
    strlcpy(s_origin, origin, sizeof(s_origin));
    s_saved_len_this_wake = (uint32_t)olen;
    ESP_LOGI(TAG, "TLS session saved (%u bytes)", (unsigned)olen);
}

void fp_tls_session_forget(void)
{
    s_len = 0;
}

bool fp_tls_session_offered(void)
{
    return s_offered_this_wake;
}

uint32_t fp_tls_session_saved_len(void)
{
    return s_saved_len_this_wake;
}

#else /* !FP_TLS_SESSION_ACTIVE: no-op outside the pinned, opted-in config */

bool fp_tls_session_offer(esp_transport_handle_t ssl, const char *origin)
{
    (void)ssl;
    (void)origin;
    return false;
}

void fp_tls_session_save(esp_transport_handle_t ssl, const char *origin)
{
    (void)ssl;
    (void)origin;
}

void fp_tls_session_forget(void)
{
}

bool fp_tls_session_offered(void)
{
    return false;
}

uint32_t fp_tls_session_saved_len(void)
{
    return 0;
}

#endif /* FP_TLS_SESSION_ACTIVE */
