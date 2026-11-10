"""Synthetic scenes for the photo render tests.

Everything is generated in memory; no binary fixture is committed and no
image shows a real person. The skin swatches are illustrative
approximations of a six-step skin-tone range, not a standard.
"""

from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageDraw

SKIN_TONES: dict[str, tuple[int, int, int]] = {
    "I": (255, 224, 196),
    "II": (241, 194, 155),
    "III": (224, 172, 124),
    "IV": (198, 134, 90),
    "V": (141, 85, 54),
    "VI": (80, 50, 36),
}

SCENE_SIZE = (480, 640)
# Box (left, top, right, bottom) of the face ellipse inside the scene.
_FACE_BOX = (120, 170, 360, 470)

RED = (220, 30, 30)
BLUE = (30, 30, 220)
GREEN = (30, 200, 30)
YELLOW = (230, 220, 30)


def skin_swatch(tone: str, size: tuple[int, int] = (64, 64)) -> Image.Image:
    """Flat swatch of one skin tone."""
    return Image.new("RGB", size, SKIN_TONES[tone])


def _backdrop(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        v = 70 + (y * 110) // max(1, h - 1)
        draw.line([(0, y), (w, y)], fill=(v, v + 10, v + 25))
    return img


def _shaded_face(tone: str, size: tuple[int, int]) -> Image.Image:
    """Skin colour scaled by a radial light falloff from the upper left."""
    base = SKIN_TONES[tone]
    left, top, right, bottom = _FACE_BOX
    fw, fh = right - left, bottom - top
    cx, cy = fw * 0.35, fh * 0.30
    face = Image.new("RGB", (fw, fh))
    px = face.load()
    assert px is not None
    reach = (fw * fw + fh * fh) ** 0.5
    for y in range(fh):
        for x in range(fw):
            d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / reach
            k = 1.12 - 0.62 * d
            px[x, y] = tuple(max(0, min(255, round(c * k))) for c in base)  # type: ignore[assignment]
    return face


def face_scene(
    tone: str, *, dull: bool = False, size: tuple[int, int] = SCENE_SIZE
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Shaded ellipse face on a graded backdrop with dark hair and a bright
    shirt band. Returns the image and the box of the skin region (an inner
    box of the face ellipse, well inside it). ``dull`` blends toward mid
    grey for a low-contrast variant."""
    img = _backdrop(size)
    left, top, right, bottom = _FACE_BOX
    draw = ImageDraw.Draw(img)
    draw.ellipse((left - 10, top - 50, right + 10, top + 150), fill=(25, 20, 18))
    mask = Image.new("L", (right - left, bottom - top), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, right - left - 1, bottom - top - 1), fill=255)
    img.paste(_shaded_face(tone, size), (left, top), mask)
    draw.rectangle((0, size[1] - 110, size[0], size[1] - 40), fill=(245, 245, 240))
    if dull:
        img = Image.blend(img, Image.new("RGB", size, (128, 128, 128)), 0.55)
    cx = (left + right) // 2
    cy = (top + bottom) // 2 + 20
    return img, (cx - 50, cy - 50, cx + 50, cy + 50)


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
