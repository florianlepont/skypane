"""Strict normalisation of untrusted photo uploads.

Bytes go in, one reduced baseline sRGB JPEG comes out. The function takes no
filename and no content type, performs no file I/O, and the original bytes
are not reachable from the result. Rejections carry a stable machine reason
code as their only message, so nothing attacker-controlled (file names,
decoder text) can leak into responses or logs.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageCms, ImageOps

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


def _draft(img: Image.Image) -> None:
    """Ask the JPEG decoder for a reduced-size decode (before load).

    The target keeps the aspect ratio so the decoder may pick a 1/2, 1/4 or
    1/8 scale that still covers the stored size; it never upsamples.
    """
    if img.format not in ("JPEG", "MPO"):
        return
    width, height = img.size
    scale = STORE_MAX_SIDE / max(width, height)
    if scale >= 1:
        return
    img.draft("RGB", (math.ceil(width * scale), math.ceil(height * scale)))


def _decode(img: Image.Image) -> Image.Image:
    """Fully decode the first frame and apply EXIF orientation.

    Truncated or broken data (including unreadable EXIF) is refused.
    """
    try:
        img.load()
        return ImageOps.exif_transpose(img)
    except Exception:  # decode boundary: no decoder text may escape
        raise PhotoRejected("corrupt") from None


def _to_rgb(img: Image.Image) -> Image.Image:
    """Convert any accepted mode to RGB, flattening transparency onto white."""
    if img.mode in ("I;16", "I;16L", "I;16B", "I"):
        # convert() would clip 16-bit values; scale them down to 8 bits.
        img = img.point(lambda v: v / 256, "L")
    if "transparency" in img.info or img.mode in ("RGBA", "LA", "PA", "P"):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.getchannel("A"))
        return flat
    return img.convert("RGB")


def _to_srgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    """Convert from the embedded profile to sRGB; an unusable profile means sRGB."""
    if not icc:
        return img
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        converted = ImageCms.profileToProfile(
            img, source, ImageCms.createProfile("sRGB"), outputMode="RGB"
        )
    except (OSError, ImageCms.PyCMSError):
        return img
    return converted if converted is not None else img


def _reduce(img: Image.Image, max_side: int) -> Image.Image:
    """Shrink so the long edge is at most ``max_side``; never upscale."""
    longest = max(img.size)
    if longest <= max_side:
        return img
    scale = max_side / longest
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    return img.resize(size, Image.Resampling.LANCZOS)


def _encode_within(img: Image.Image) -> tuple[bytes, tuple[int, int]]:
    """Encode a baseline JPEG no larger than STORE_MAX_BYTES.

    Tries the quality ladder at the current size, then shrinks and repeats.
    No exif, icc_profile or comment is passed, so none is written.
    """
    while True:
        for quality in QUALITY_LADDER:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, optimize=True, progressive=False)
            if buf.tell() <= STORE_MAX_BYTES:
                return buf.getvalue(), img.size
        width, height = img.size
        img = img.resize(
            (max(1, round(width * SHRINK_FACTOR)), max(1, round(height * SHRINK_FACTOR))),
            Image.Resampling.LANCZOS,
        )


def normalize_upload(raw: bytes) -> StoredPhoto:
    """Validate ``raw`` and return the one reduced stored copy.

    Raises PhotoRejected with a stable reason code for anything that is not
    a decodable, reasonably sized JPEG, PNG or WebP still image.
    """
    if not raw:
        raise PhotoRejected("empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoRejected("too_large")
    if _looks_like_heic(raw):
        raise PhotoRejected("heic_unsupported")
    img = _open_checked(raw)
    icc = img.info.get("icc_profile")
    _draft(img)
    img = _decode(img)
    rgb = _to_srgb(_to_rgb(img), icc if isinstance(icc, bytes) else None)
    jpeg, (width, height) = _encode_within(_reduce(rgb, STORE_MAX_SIDE))
    return StoredPhoto(jpeg=jpeg, width=width, height=height)
