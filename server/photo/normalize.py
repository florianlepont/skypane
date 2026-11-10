"""Strict normalisation of untrusted photo uploads.

Bytes go in, one reduced baseline sRGB JPEG comes out. The function takes no
filename and no content type, performs no file I/O, and the original bytes
are not reachable from the result. Rejections carry a stable machine reason
code as their only message, so nothing attacker-controlled (file names,
decoder text) can leak into responses or logs.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 50_000_000
MIN_SIDE = 200
STORE_MAX_SIDE = 2048
STORE_MAX_BYTES = 1_000_000
QUALITY_LADDER = (88, 82, 76, 70, 62)
SHRINK_FACTOR = 0.85

# Decoder allowlist handed to Image.open: every other plugin (GIF, TIFF, EPS,
# BMP, ...) stays out of reach. MPO phone photos open through the JPEG entry.
_OPEN_FORMATS = ["JPEG", "PNG", "WEBP"]
# What img.format may report after opening.
_ALLOWED_FORMATS = frozenset({"JPEG", "MPO", "PNG", "WEBP"})
_HEIF_BRANDS = frozenset(
    {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1", b"avif", b"avis"}
)


class PhotoRejected(ValueError):
    """An upload was refused; ``reason`` is a stable machine code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class StoredPhoto:
    """The single reduced copy kept for an upload."""

    jpeg: bytes
    width: int
    height: int


def _looks_like_heic(raw: bytes) -> bool:
    """True when the bytes start with an ISO-BMFF box of a HEIF/AVIF brand."""
    if len(raw) < 12 or raw[4:8] != b"ftyp":
        return False
    return raw[8:12] in _HEIF_BRANDS


def _open_checked(raw: bytes) -> Image.Image:
    """Open with the decoder allowlist and apply header-only checks.

    Nothing is decoded here: size limits are judged from the header so a
    tiny file declaring a huge canvas is refused before any allocation.
    """
    try:
        img = Image.open(io.BytesIO(raw), formats=_OPEN_FORMATS)
    except Image.DecompressionBombError:
        raise PhotoRejected("too_many_pixels") from None
    except Exception:  # decode boundary: no decoder text may escape
        raise PhotoRejected("not_an_image") from None
    if img.format not in _ALLOWED_FORMATS:
        raise PhotoRejected("unsupported_format")
    # MPO legitimately carries several frames, so only PNG and WebP count.
    if img.format in ("PNG", "WEBP") and getattr(img, "n_frames", 1) > 1:
        raise PhotoRejected("animated")
    width, height = img.size
    if width * height > MAX_PIXELS:
        raise PhotoRejected("too_many_pixels")
    if min(width, height) < MIN_SIDE:
        raise PhotoRejected("too_small")
    return img


def _decode(img: Image.Image) -> Image.Image:
    """Fully decode the first frame; truncated or broken data is refused."""
    try:
        img.load()
    except Exception:  # decode boundary: no decoder text may escape
        raise PhotoRejected("corrupt") from None
    return img


def normalize_upload(raw: bytes) -> StoredPhoto:
    """Validate ``raw`` and return the one reduced stored copy."""
    if not raw:
        raise PhotoRejected("empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoRejected("too_large")
    if _looks_like_heic(raw):
        raise PhotoRejected("heic_unsupported")
    _decode(_open_checked(raw))
    raise NotImplementedError
