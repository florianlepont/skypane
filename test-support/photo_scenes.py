"""Synthetic scenes for the photo render tests.

Everything is generated in memory; no binary fixture is committed and no
image shows a real person. The skin swatches are illustrative
approximations of a six-step skin-tone range, not a standard.
"""

from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageDraw

from server.photo.trial import (  # noqa: F401  (re-exported for the tests)
    SCENE_SIZE,
    SKIN_TONES,
    face_scene,
    skin_swatch,
)

RED = (220, 30, 30)
BLUE = (30, 30, 220)
GREEN = (30, 200, 30)
YELLOW = (230, 220, 30)


def left_right(size: tuple[int, int] = (400, 400)) -> Image.Image:
    """Left half red, right half blue."""
    img = Image.new("RGB", size, BLUE)
    ImageDraw.Draw(img).rectangle((0, 0, size[0] // 2 - 1, size[1]), fill=RED)
    return img


def top_bottom(size: tuple[int, int] = (400, 400)) -> Image.Image:
    """Top half green, bottom half yellow."""
    img = Image.new("RGB", size, YELLOW)
    ImageDraw.Draw(img).rectangle((0, 0, size[0], size[1] // 2 - 1), fill=GREEN)
    return img


def corner_markers(size: tuple[int, int] = (600, 400), marker: int = 40) -> Image.Image:
    """Mid-grey image with a distinct solid square in each corner:
    top-left red, top-right green, bottom-left blue, bottom-right yellow."""
    img = Image.new("RGB", size, (128, 128, 128))
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.rectangle((0, 0, marker - 1, marker - 1), fill=RED)
    draw.rectangle((w - marker, 0, w - 1, marker - 1), fill=GREEN)
    draw.rectangle((0, h - marker, marker - 1, h - 1), fill=BLUE)
    draw.rectangle((w - marker, h - marker, w - 1, h - 1), fill=YELLOW)
    return img


def to_stored_jpeg(img: Image.Image) -> bytes:
    """Encode like the stored copy: baseline JPEG, no metadata."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


def images_equal(a: Image.Image, b: Image.Image) -> bool:
    """Pixel equality for two images of the same mode and size."""
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None
