"""Image container: the framed body the server sends to a frame.

Layout (little endian, 24 bytes, struct format "<4sBBHHHBBHII"):

    offset 0   magic        4s   b"SPIM"
    offset 4   version      B    1
    offset 5   header_len   B    >= 24; bytes past 24 are skipped
    offset 6   flags        H    no bit is defined in v1; any set bit is rejected
    offset 8   width        H
    offset 10  height       H
    offset 12  pixel_format B    1 = packed 4 bpp, high nibble first
    offset 13  palette_id   B    1 = Spectra 6 nibble codes (an id, not RGB)
    offset 14  reserved     H    must be 0
    offset 16  payload_len  I    ceil(width * height / 2)
    offset 20  crc32        I    zlib.crc32 of the payload only

A body without the magic whose length is exactly ceil(panel_w * panel_h / 2)
is the legacy raw form. A body starting with the magic is never legacy.

The C reader repeats every check below with 64-bit arithmetic so that
header_len + payload_len cannot wrap; Python integers need no such care.
The CRC detects corruption only, it does not authenticate the body.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

MAGIC = b"SPIM"
HEADER_FORMAT = "<4sBBHHHBBHII"
HEADER_LEN = struct.calcsize(HEADER_FORMAT)
VERSION_1 = 1
SUPPORTED_MAX = 1
PIXEL_FORMAT_NIBBLE = 1
PALETTE_SPECTRA6 = 1

_MAX_ANNOUNCE_CHARS = 3
_ASCII_DIGITS = frozenset("0123456789")


class ImageContainerError(ValueError):
    """Malformed container; ``reason`` names the failing field class."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True)
class ContainerView:
    """Decoded body: the pixel payload plus what the header declared."""

    payload: bytes
    palette_id: int
    legacy: bool
    width: int
    height: int


def payload_size(width: int, height: int) -> int:
    """Packed 4 bpp byte count; an odd pixel count pads one nibble."""
    return (width * height + 1) // 2


def encode_container(
    pixels: bytes,
    width: int,
    height: int,
    *,
    version: int = VERSION_1,
    palette_id: int = PALETTE_SPECTRA6,
) -> bytes:
    """Return the 24-byte header followed by the packed pixels."""
    if version != VERSION_1:
        raise ValueError(f"version: unsupported {version}")
    if not (0 < width <= 0xFFFF and 0 < height <= 0xFFFF):
        raise ValueError("dimensions: out of range")
    if len(pixels) != payload_size(width, height):
        raise ValueError("length: payload does not match dimensions")
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        version,
        HEADER_LEN,
        0,
        width,
        height,
        PIXEL_FORMAT_NIBBLE,
        palette_id,
        0,
        len(pixels),
        zlib.crc32(pixels),
    )
    return header + pixels


def decode_container(body: bytes, panel_w: int, panel_h: int) -> ContainerView:
    """Validate ``body`` for a panel of the given size.

    Raises ImageContainerError with ``reason`` one of: argument, truncated,
    magic, header_len, version, flags, reserved, pixel_format, palette,
    dimensions, length, crc.
    """
    if panel_w <= 0 or panel_h <= 0:
        raise ImageContainerError("argument", "panel size")
    expected = payload_size(panel_w, panel_h)
    if len(body) >= len(MAGIC) and body[: len(MAGIC)] == MAGIC:
        return _decode_framed(body, panel_w, panel_h, expected)
    if len(body) == expected:
        return ContainerView(
            payload=bytes(body),
            palette_id=PALETTE_SPECTRA6,
            legacy=True,
            width=panel_w,
            height=panel_h,
        )
    if len(body) < len(MAGIC):
        raise ImageContainerError("truncated", "shorter than magic")
    raise ImageContainerError("magic", "not a container and not legacy size")


def _decode_framed(
    body: bytes, panel_w: int, panel_h: int, expected: int
) -> ContainerView:
    if len(body) < HEADER_LEN:
        raise ImageContainerError("truncated", "shorter than header")
    (_magic, version, header_len, flags, width, height, pixel_format,
     palette_id, reserved, payload_len, crc) = struct.unpack_from(
        HEADER_FORMAT, body, 0)
    if header_len < HEADER_LEN or header_len > len(body):
        raise ImageContainerError("header_len", str(header_len))
    if version != VERSION_1:
        raise ImageContainerError("version", str(version))
    if flags != 0:
        raise ImageContainerError("flags", hex(flags))
    if reserved != 0:
        raise ImageContainerError("reserved", str(reserved))
    if pixel_format != PIXEL_FORMAT_NIBBLE:
        raise ImageContainerError("pixel_format", str(pixel_format))
    if palette_id != PALETTE_SPECTRA6:
        raise ImageContainerError("palette", str(palette_id))
    if width != panel_w or height != panel_h:
        raise ImageContainerError("dimensions", f"{width}x{height}")
    if payload_len != expected:
        raise ImageContainerError("length", f"payload_len {payload_len}")
    if len(body) != header_len + payload_len:
        raise ImageContainerError("length", f"total {len(body)}")
    payload = bytes(body[header_len:])
    if zlib.crc32(payload) != crc:
        raise ImageContainerError("crc", "payload checksum mismatch")
    return ContainerView(
        payload=payload,
        palette_id=palette_id,
        legacy=False,
        width=width,
        height=height,
    )


def negotiate_version(raw: object) -> int | None:
    """Parse a frame's container-version announcement; never raises.

    Only 1-3 ASCII digits with a non-zero value count. Anything else means
    the frame gets the legacy raw body (None). A version above what this
    server writes selects the server maximum.
    """
    if not isinstance(raw, str):
        return None
    if not 0 < len(raw) <= _MAX_ANNOUNCE_CHARS:
        return None
    if not all(ch in _ASCII_DIGITS for ch in raw):
        return None
    value = int(raw)
    if value == 0:
        return None
    return min(value, SUPPORTED_MAX)
