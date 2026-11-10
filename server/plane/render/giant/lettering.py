"""Stretched, strictly binary Anton lettering lines.

Every line is drawn large, scaled so its capital height fills the slot and
its width fills the box, then hard-thresholded. A soft mask would blend
palette index integers on a "P" canvas into illegal colours, so no mask in
this module is ever anything but 0 or 255.
"""
from typing import Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from server.plane.render.giant import fonts
from server.plane.render.giant.split import LINE_GAP_PX, MAX_LINES

# Mask value strictly above this is painted.
MASK_THRESHOLD = 127
# Longest line drawn; bounds the size of the supersampled layer.
MAX_LINE_CHARS = 80
# Spare columns (at supersample size) right of the drawn text.
_PAD_PX = 8

Box = Tuple[int, int, int, int]


def _binary(mask: Image.Image) -> Image.Image:
    return mask.point(lambda p: 255 if p > MASK_THRESHOLD else 0)


def _render_big(text: str) -> Tuple[Image.Image, int]:
    """The line at supersample size, cropped horizontally to its ink.

    Returns (layer, baseline_row). The layer holds the rows from the top of
    the tallest glyph (accents included) down to the baseline.
    """
    if not text or len(text) > MAX_LINE_CHARS:
        raise ValueError("lettering line must be 1..%d characters" % MAX_LINE_CHARS)
    font = fonts.anton(fonts.SUPERSAMPLE_PX)
    left, top, right, _bottom = font.getbbox(text, anchor="ls")
    cap = fonts.cap_height(fonts.SUPERSAMPLE_PX)
    above = max(-top, cap)
    wide = Image.new("L", (right + _PAD_PX, above), 0)
    ImageDraw.Draw(wide).text((0, above), text, font=font, fill=255, anchor="ls")
    ink = wide.getbbox()
    if ink is None:
        raise ValueError("lettering line has no visible glyphs")
    layer = wide.crop((ink[0], 0, ink[2], above))
    return layer, above


def _stretch(layer: Image.Image, above: int, box_w: int, slot_h: int,
             factor: int) -> Image.Image:
    """`layer` resized so the capital band is `slot_h` tall and the width is
    `box_w`; accents keep their proportion above it. `factor` oversizes the
    result for the optional downsample-then-threshold pass.
    """
    cap = fonts.cap_height(fonts.SUPERSAMPLE_PX)
    scale_y = slot_h * factor / cap
    out_h = max(1, round(above * scale_y))
    resized = layer.resize((box_w * factor, out_h), Image.Resampling.LANCZOS)
    return _binary(resized)


def line_layer(text: str, box_w: int, slot_h: int,
               downsample_2x: bool = False) -> Tuple[Image.Image, int]:
    """Binary "L" layer for one line and its overhang in pixels.

    The layer is `box_w` wide and `slot_h + overhang` tall; the capital band
    occupies its bottom `slot_h` rows, accents the rows above.
    `downsample_2x` draws at twice the size, thresholds, halves with a box
    filter and thresholds again, which softens thin joins the way glass does.
    """
    layer, above = _render_big(text)
    factor = 2 if downsample_2x else 1
    stretched = _stretch(layer, above, box_w, slot_h, factor)
    if downsample_2x:
        stretched = _binary(stretched.resize(
            (box_w, stretched.height // 2), Image.Resampling.BOX))
    return stretched, max(0, stretched.height - slot_h)


def line_mask(text: str, box_w: int, slot_h: int) -> Image.Image:
    """Binary "L" mask of exactly (box_w, slot_h): the capital band of the
    line. Accents that rise above the slot are cut here; `paint_lines` keeps
    them.
    """
    layer, overhang = line_layer(text, box_w, slot_h)
    return layer.crop((0, overhang, box_w, overhang + slot_h))


def supported_lines(lines: Sequence[str]) -> bool:
    """Whether Anton can draw every line, so a caller can fall back to the
    airline name when it cannot."""
    return bool(lines) and all(fonts.supports(line) for line in lines)


def _slot_geometry(box: Box, count: int) -> Tuple[float, int]:
    x0, y0, x1, y1 = box
    slot = (y1 - y0) / count
    return slot, max(1, round(slot - LINE_GAP_PX))


def _paint_layer(canvas: Image.Image, mask: Image.Image, pos: Tuple[int, int],
                 ink_idx: int, band_mask: Optional[Image.Image],
                 band_field_pattern: Optional[Image.Image]) -> None:
    if band_mask is None or band_field_pattern is None:
        canvas.paste(ink_idx, pos, mask)
        return
    region = (pos[0], pos[1], pos[0] + mask.width, pos[1] + mask.height)
    band = _binary(band_mask.crop(region))
    on_band = ImageChops.multiply(mask, band)
    off_band = ImageChops.subtract(mask, band)
    canvas.paste(ink_idx, pos, off_band)
    canvas.paste(band_field_pattern.crop(region), pos, on_band)


def paint_lines(canvas: Image.Image, lines: Sequence[str], box: Box, ink_idx: int,
                band_mask: Optional[Image.Image] = None,
                band_field_pattern: Optional[Image.Image] = None) -> None:
    """Stack `lines` in `box` (x0, y0, x1, y1), each stretched to the box width.

    Off-band pixels take palette index `ink_idx`. When `band_mask` (a
    canvas-sized "L" polygon) and `band_field_pattern` (a canvas-sized "P"
    field shade) are both given, lettering inside the band takes the field
    pattern instead, so it stays readable on the solid band.
    """
    if not 1 <= len(lines) <= MAX_LINES:
        raise ValueError("expected 1..%d lettering lines" % MAX_LINES)
    x0, y0, x1, _y1 = box
    slot, slot_h = _slot_geometry(box, len(lines))
    for i, text in enumerate(lines):
        layer, overhang = line_layer(text, x1 - x0, slot_h)
        pos = (x0, round(y0 + slot * i) - overhang)
        _paint_layer(canvas, layer, pos, ink_idx, band_mask, band_field_pattern)
