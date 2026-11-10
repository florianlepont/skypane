"""Status glyphs drawn larger than their native size without stair-stepping.

The production `glyphs.draw_*_icon` functions are reused unchanged: they draw
onto a coordinate-scaling proxy at a supersampled resolution, and the result is
reduced and thresholded to a binary mask. The mask is pure ink / no ink, so it
can be pasted with a palette index and never introduces an illegal colour.
"""
from typing import Callable, Dict, Tuple

from PIL import Image, ImageDraw

from server.plane.render import glyphs

# Drawing resolution relative to the output; a fixed small factor keeps the
# cost bounded (the work area stays a few hundred pixels square).
SUPERSAMPLE = 4
_THRESHOLD = 128
# Room around the glyph in native units, so strokes never touch the work edge.
_PAD = 12
_NATIVE_BOX = 120

# kind -> (production drawer, native glyph height in pixels)
ICONS: Dict[str, Tuple[Callable, int]] = {
    "watching": (glyphs.draw_runway_icon, glyphs.RUNWAY_ICON_HEIGHT_PX),
    "quiet_hours": (glyphs.draw_moon_icon, glyphs.MOON_ICON_DIAMETER_PX),
    "display_off": (glyphs.draw_power_icon,
                    glyphs.POWER_ICON_BAR_RISE_PX + glyphs.POWER_ICON_DIAMETER_PX),
    "battery_empty": (glyphs.draw_empty_battery_icon, glyphs.EMPTY_BATTERY_ICON_HEIGHT_PX),
    "no_connection": (glyphs.draw_alert_icon, glyphs.ALERT_ICON_HEIGHT_PX),
    "updating": (glyphs.draw_updating_icon, glyphs.UPDATING_ICON_DIAMETER_PX),
    "retired": (glyphs.draw_power_icon,
                glyphs.POWER_ICON_BAR_RISE_PX + glyphs.POWER_ICON_DIAMETER_PX),
}


class _ScaledDraw:
    """The `ImageDraw` calls the glyph drawers use, with every coordinate and
    stroke width multiplied by `factor`. Box corners are inclusive pixel
    indices (the glyph code's convention), points are pixel centres."""

    def __init__(self, draw: ImageDraw.ImageDraw, factor: float) -> None:
        self._draw = draw
        self._f = factor

    def _point(self, p):
        f = self._f
        return (p[0] * f + (f - 1) / 2, p[1] * f + (f - 1) / 2)

    def _points(self, xy):
        if isinstance(xy[0], (tuple, list)):
            return [self._point(p) for p in xy]
        return [self._point(xy[i:i + 2]) for i in range(0, len(xy), 2)]

    def _box(self, xy):
        f = self._f
        pts = self._points(xy)
        (x0, y0), (x1, y1) = pts[0], pts[1]
        # Back from pixel centres to edges, with the far corner inclusive.
        return (x0 - (f - 1) / 2, y0 - (f - 1) / 2, x1 + (f - 1) / 2, y1 + (f - 1) / 2)

    def _width(self, width):
        return max(1, round(width * self._f))

    def arc(self, xy, start, end, fill=None, width=1):
        self._draw.arc(self._box(xy), start, end, fill=fill, width=self._width(width))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self._draw.rectangle(self._box(xy), fill=fill, outline=outline, width=self._width(width))

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        self._draw.rounded_rectangle(
            self._box(xy), radius=radius * self._f, fill=fill, outline=outline,
            width=self._width(width))

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self._draw.ellipse(self._box(xy), fill=fill, outline=outline, width=self._width(width))

    def polygon(self, xy, fill=None, outline=None, width=1):
        self._draw.polygon(self._points(xy), fill=fill, outline=outline, width=self._width(width))

    def line(self, xy, fill=None, width=1):
        self._draw.line(self._points(xy), fill=fill, width=self._width(width))


def icon_mask(kind: str, height: int) -> Image.Image:
    """Binary "L" mask (255 = ink) of the glyph for `kind`, cropped to its ink
    and `height` pixels tall. The glyph is the production one drawn at
    `SUPERSAMPLE` times the target size, reduced and thresholded."""
    drawer, native_h = ICONS[kind]
    factor = height / native_h * SUPERSAMPLE
    side = round((_NATIVE_BOX + 2 * _PAD) * factor)
    work = Image.new("L", (side, side), 0)
    drawer(_ScaledDraw(ImageDraw.Draw(work), factor), (_NATIVE_BOX + 2 * _PAD) // 2, _PAD, 255)
    box = work.getbbox()
    if box is None:
        raise ValueError("glyph drew nothing: " + kind)
    work = work.crop(box)
    out_w = max(1, round(work.width / SUPERSAMPLE))
    out_h = max(1, round(work.height / SUPERSAMPLE))
    small = work.resize((out_w, out_h), Image.Resampling.BOX)
    return small.point(lambda v: 255 if v >= _THRESHOLD else 0)
