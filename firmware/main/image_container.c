/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
#include "image_container.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define IMGC_HEADER_LEN 24u
#define IMGC_VERSION 1u
#define IMGC_PIXEL_FORMAT_NIBBLE 1u
#define IMGC_PALETTE_SPECTRA6 1u

static uint16_t rd16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
}

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

uint32_t imgc_crc32(const uint8_t *data, size_t len)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            /* Branch-free: the mask is all ones when the low bit is set. */
            crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

static imgc_status_t fail(imgc_view_t *out, imgc_status_t status)
{
    memset(out, 0, sizeof(*out));
    return status;
}

static bool has_magic(const uint8_t *body, size_t len)
{
    return len >= 4 && body[0] == 'S' && body[1] == 'P' && body[2] == 'I' &&
           body[3] == 'M';
}

static imgc_status_t parse_framed(const uint8_t *body, size_t len,
                                  uint32_t panel_w, uint32_t panel_h,
                                  uint64_t expected, imgc_view_t *out)
{
    if (len < IMGC_HEADER_LEN) {
        return fail(out, IMGC_ERR_TRUNCATED);
    }
    uint8_t version = body[4];
    uint64_t header_len = body[5];
    uint16_t flags = rd16(body + 6);
    uint16_t width = rd16(body + 8);
    uint16_t height = rd16(body + 10);
    uint8_t pixel_format = body[12];
    uint8_t palette_id = body[13];
    uint16_t reserved = rd16(body + 14);
    uint64_t payload_len = rd32(body + 16);
    uint32_t crc = rd32(body + 20);

    if (header_len < IMGC_HEADER_LEN || header_len > (uint64_t)len) {
        return fail(out, IMGC_ERR_HEADER_LEN);
    }
    if (version != IMGC_VERSION) {
        return fail(out, IMGC_ERR_VERSION);
    }
    if (flags != 0) {
        return fail(out, IMGC_ERR_FLAGS);
    }
    if (reserved != 0) {
        return fail(out, IMGC_ERR_RESERVED);
    }
    if (pixel_format != IMGC_PIXEL_FORMAT_NIBBLE) {
        return fail(out, IMGC_ERR_FORMAT);
    }
    if (palette_id != IMGC_PALETTE_SPECTRA6) {
        return fail(out, IMGC_ERR_PALETTE);
    }
    if (width != panel_w || height != panel_h) {
        return fail(out, IMGC_ERR_DIMENSIONS);
    }
    if (payload_len != expected) {
        return fail(out, IMGC_ERR_LENGTH);
    }
    /* header_len <= len here, so the subtraction cannot wrap. */
    if (payload_len != (uint64_t)len - header_len) {
        return fail(out, IMGC_ERR_LENGTH);
    }
    const uint8_t *payload = body + header_len;
    if (imgc_crc32(payload, (size_t)payload_len) != crc) {
        return fail(out, IMGC_ERR_CRC);
    }
    out->payload = payload;
    out->payload_len = (size_t)payload_len;
    out->palette_id = palette_id;
    out->legacy = false;
    return IMGC_OK;
}

imgc_status_t imgc_parse(const uint8_t *body, size_t len, uint32_t panel_w,
                         uint32_t panel_h, imgc_view_t *out)
{
    if (out == NULL) {
        return IMGC_ERR_ARG;
    }
    if (panel_w == 0 || panel_h == 0 || (body == NULL && len != 0)) {
        return fail(out, IMGC_ERR_ARG);
    }
    uint64_t expected = ((uint64_t)panel_w * (uint64_t)panel_h + 1u) / 2u;
    if (has_magic(body, len)) {
        return parse_framed(body, len, panel_w, panel_h, expected, out);
    }
    if ((uint64_t)len == expected) {
        out->payload = body;
        out->payload_len = len;
        out->palette_id = IMGC_PALETTE_SPECTRA6;
        out->legacy = true;
        return IMGC_LEGACY_OK;
    }
    if (len < 4) {
        return fail(out, IMGC_ERR_TRUNCATED);
    }
    return fail(out, IMGC_ERR_MAGIC);
}
