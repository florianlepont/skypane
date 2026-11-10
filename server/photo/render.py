"""Render a stored photo to a six-colour panel image.

Pure and deterministic: the same stored bytes, size, fit setting and
parameters always give identical pixels. The order is crop, boost, dither
in both fit modes. This module deliberately shares nothing with the plane
screen renderer beyond the palette, canvas, packing and dither helpers.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps

from server import panel_format as pf
from server.photo.crop import FitSetting
from server.photo.prep import DEFAULT_PREP, PrepParams, prepare
from server.plane.dither import dither_to_full_panel_palette

MAX_SIDE = 2400
# Colour of the unused area in bands mode.
BAND_INDEX = pf.IDX_WHITE


def _check_size(size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    if width <= 0 or height <= 0 or width % 2:
        raise ValueError("size must be positive with an even width")
    if width > MAX_SIDE or height > MAX_SIDE:
        raise ValueError(f"size must not exceed {MAX_SIDE} per side")
    return width, height


def _open_stored(stored: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(stored), formats=["JPEG"])
        return img.convert("RGB")
    except Exception:  # decode boundary: report a fixed message only
        raise ValueError("stored photo is not a decodable JPEG") from None


def _dither(rgb: Image.Image) -> Image.Image:
    out: Image.Image = dither_to_full_panel_palette(rgb)
    return out


def render_photo(
    stored: bytes,
    size: tuple[int, int],
    fit: FitSetting = FitSetting(),
    params: PrepParams = DEFAULT_PREP,
) -> Image.Image:
    """Return a "P" image of ``size`` using only the six panel indices."""
    size = _check_size(size)
    src = _open_stored(stored)
    if fit.mode == "fill":
        centering = (fit.pos_x, fit.pos_y)
        framed = ImageOps.fit(src, size, Image.Resampling.LANCZOS, centering=centering)
        return _dither(prepare(framed, params))
    inner = ImageOps.contain(src, size, Image.Resampling.LANCZOS)
    dithered = _dither(prepare(inner, params))
    canvas = pf.new_canvas(BAND_INDEX, size)
    canvas.paste(dithered, ((size[0] - inner.width) // 2, (size[1] - inner.height) // 2))
    return canvas


def render_photo_packed(
    stored: bytes,
    size: tuple[int, int],
    fit: FitSetting = FitSetting(),
    params: PrepParams = DEFAULT_PREP,
) -> bytes:
    """Render and pack to the panel wire format (width/2 * height bytes)."""
    return pf.pack_panel(render_photo(stored, size, fit, params))


def preview_png(image: Image.Image) -> bytes:
    """PNG bytes of a rendered "P" image."""
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()
