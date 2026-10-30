/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Reader for the image container the server sends to the frame, with no
 * ESP-IDF in it so it can be tested on a host.
 *
 * Wire layout (little endian, 24 bytes): "SPIM", version (1), header_len
 * (>= 24, extra bytes are skipped), flags (must be 0), width, height,
 * pixel_format (1 = packed 4 bpp), palette_id (1), reserved (0),
 * payload_len (= ceil(width * height / 2)), crc32 of the payload.
 *
 * A body without the magic whose length is exactly ceil(panel_w * panel_h / 2)
 * is the legacy raw form. A body that starts with the magic is never legacy.
 *
 * The reader is handed no display buffer: it only validates and returns a
 * view into the caller's body, so validation always precedes any pixel copy.
 * The CRC detects corruption only, it does not authenticate the body. */

typedef enum {
    IMGC_OK = 0,          /* valid container                              */
    IMGC_LEGACY_OK,       /* valid legacy raw body                        */
    IMGC_ERR_ARG,         /* NULL out, zero panel size, NULL body, len > 0 */
    IMGC_ERR_TRUNCATED,   /* shorter than the magic or the fixed header   */
    IMGC_ERR_MAGIC,       /* no magic and not the legacy size             */
    IMGC_ERR_HEADER_LEN,  /* header_len < 24 or past the end of the body  */
    IMGC_ERR_VERSION,
    IMGC_ERR_FLAGS,
    IMGC_ERR_RESERVED,
    IMGC_ERR_FORMAT,      /* pixel_format not supported                   */
    IMGC_ERR_PALETTE,
    IMGC_ERR_DIMENSIONS,  /* header size differs from the panel           */
    IMGC_ERR_LENGTH,      /* payload_len or total length inconsistent     */
    IMGC_ERR_CRC,
} imgc_status_t;

typedef struct {
    const uint8_t *payload; /* points into the body passed to imgc_parse */
    size_t payload_len;
    uint8_t palette_id;
    bool legacy;
} imgc_view_t;

/* Validates `body` for a panel of panel_w x panel_h pixels. `*out` is zeroed
 * on every non-success return (and on success of either kind it is filled).
 * A NULL body is treated as an empty one when len is 0. */
imgc_status_t imgc_parse(const uint8_t *body, size_t len, uint32_t panel_w,
                         uint32_t panel_h, imgc_view_t *out);

/* Reflected CRC-32 (polynomial 0xEDB88320, init and final xor 0xFFFFFFFF),
 * the same value zlib.crc32 produces. */
uint32_t imgc_crc32(const uint8_t *data, size_t len);
