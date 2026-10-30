# Image container format

## Overview

The server can send a frame its image either as the legacy raw body or inside
a small versioned container. The container is a fixed 24-byte little-endian
header followed by the packed pixel payload. The pixel buffer stays the
canonical artifact; the container is only a framing added when a body is
served. Reference implementations: `server/image_container.py` (encoder and
decoder) and `firmware/main/image_container.[ch]` (pure C reader, no ESP-IDF
dependency).

## Announcement

A frame announces what it can read with a request header on the display poll:

    X-Img-Fmt: <n>

`n` is the highest container version the frame reads.

- The server never requires the header.
- A value of 1 to 3 ASCII digits with a non-zero value is an announcement.
- A version above the server's maximum selects the server's maximum. The
  server otherwise serves the highest version it supports that is not above
  the announced one.
- Absent, empty, malformed, zero, non-numeric or longer than 3 digits all mean
  legacy raw.
- The announcement is per request only. It is not stored in device state, the
  registry or the fleet database, so a legacy frame's recorded state cannot
  change.

## Header

Struct format `<4sBBHHHBBHII`, 24 bytes, every field naturally aligned.

| Offset | Size | Field        | Type  | Meaning |
|-------:|-----:|--------------|-------|---------|
| 0      | 4    | magic        | 4s    | ASCII `SPIM` |
| 4      | 1    | version      | u8    | container version, 1 |
| 5      | 1    | header_len   | u8    | at least 24 |
| 6      | 2    | flags        | u16   | must be 0 in v1 |
| 8      | 2    | width        | u16   | pixels |
| 10     | 2    | height       | u16   | pixels |
| 12     | 1    | pixel_format | u8    | 1 |
| 13     | 1    | palette_id   | u8    | 1 |
| 14     | 2    | reserved     | u16   | must be 0 |
| 16     | 4    | payload_len  | u32   | see Lengths |
| 20     | 4    | crc32        | u32   | see Lengths |

## v1 values and palette registry

- version 1.
- header_len 24. A reader skips `header_len - 24` extra bytes (a future minor
  extension) but never reads past the buffer.
- pixel_format 1 is packed 4 bits per pixel, high nibble first.
- palette_id 1 is the Spectra 6 controller nibble codes: 0 black, 1 white,
  2 yellow, 3 red, 5 blue, 6 green. The palette is an id into a registry held
  as constants in the server and the firmware, not RGB values inside each
  image.

## Flags

Bit 0 is reserved for future compression and must be 0 in v1. A reader
rejects any set flag bit. There is no compression in v1.

## Lengths and checksum

- `payload_len` must equal `ceil(width * height / 2)`. It equals
  `width * height / 2` for even pixel counts; an odd count pads one nibble.
  For 1200x1600 the payload is 960,000 bytes and the whole body 960,024 bytes.
- The whole body length must equal `header_len + payload_len`.
- `crc32` is the standard CRC-32 (`zlib.crc32`, polynomial reflected
  0xEDB88320) of the payload only.
- The CRC detects corruption. It is not authenticity. The SHA-256 of the whole
  served file stays the check the device already performs.

## Legacy raw format

A body with no `SPIM` magic whose length is exactly
`ceil(panel_w * panel_h / 2)` (960,000 bytes for 1200x1600) is the legacy raw
form: the payload alone, palette 1. A body that starts with `SPIM` is never
treated as legacy. This is unambiguous: the bytes `SPIM` are the nibbles
5, 3, 5, 0, 4, 9, 4, 13, and 4, 9 and 13 are not Spectra 6 codes, so no valid
legacy image starts with the magic.

## Reader validation order

The reader takes the received bytes and the panel width and height, returns a
validated view (payload pointer, length, palette id) or an error, and never
touches a display buffer. Checks run in this order; the first failure wins.
Error classes are shared by the Python decoder and the C reader
(`IMGC_ERR_*`):

1. argument: invalid panel size or arguments.
2. If the body starts with `SPIM`:
   1. truncated: shorter than the 24-byte header.
   2. header_len: below 24 or beyond the body length.
   3. version: not 1.
   4. flags: any bit set.
   5. reserved: not 0.
   6. pixel_format: not 1.
   7. palette: not 1.
   8. dimensions: width or height differs from the panel.
   9. length: `payload_len` is not the expected size, or the body length is not
      `header_len + payload_len`.
   10. crc: payload checksum mismatch.
3. Otherwise, a body of exactly the legacy size is accepted as legacy.
4. truncated: shorter than the magic.
5. magic: neither a container nor the legacy size.

The C reader performs the length arithmetic in 64 bits so that
`header_len + payload_len` cannot wrap.

## Hash and URL

The advertised `image_hash` and the content-addressed `/img/<sha256>.bin` path
keep their meaning: SHA-256 over the exact bytes served, header included. When
a frame switches format its hash changes, which costs that frame one extra
full refresh once. This is accepted. The canonical artifact the renderer
produces remains the pixel buffer; the container is applied at serve time.

## Golden fixtures

`firmware/tests/fixtures/image_container/` holds small binary bodies, one per
decoder outcome, and `manifest.txt` listing the expected result for each. The
generator `generate_fixtures.py` is deterministic and the bytes are committed.
The Python decoder tests and the C host tests read the same files. The
full-size 1200x1600 image is not committed; the manifest carries its payload
CRC-32 and the SHA-256 of the whole container for both sides to compare.

## Adoption notes for the firmware release that wires the reader

Nothing in this change is wired into the device firmware, built for release,
published or flashed. The pure C reader and its host test exist only. When a
firmware release adopts it:

- The download buffer and the length gate in `api_client.c` (currently exactly
  `FP_IMAGE_BYTES`) must grow by `header_len` (24 bytes for v1, more when a
  future extension is announced).
- The SHA-256 covers the whole body, header included, so the hash is computed
  over everything received, not just the payload.
- The frame sends `X-Img-Fmt` on the display poll only when it carries the
  reader, then validates with the reader before any display buffer access.
- A frame that switches format sees one extra full refresh.
