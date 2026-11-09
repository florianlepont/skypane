"""The calm status screens: watching, quiet hours, display off, battery empty,
no connection, updating and retired.

One composition for all of them, in portrait and landscape: the production
glyph top-left, a small label under it, two giant Anton lines flush left (whole
words, each line sized to the width), and small body text bottom-left. The
watching screen is white with black ink; the others are the dithered dark field
with white ink. Colour themes never apply here. Geometry is derived from the
canvas size, so any size of either orientation renders.

Must not import `layout.py`: `layout.build_canvas` dispatches into this module.
"""
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from server import device_config
from server import panel_format as pf
from server.plane import dither
from server.plane.render import glyphs, landscape_card, landscape_common, style
from server.plane.render.giant import fonts, icons

Size = Tuple[int, int]

KINDS = ("watching", "quiet_hours", "display_off", "battery_empty",
         "no_connection", "updating", "retired")

RETIRED_BODY_LINES = (
    "This frame was removed from SkyPane.",
    "Ask an administrator to set it up again.",
)

_LABELS = {
    "watching": "WATCHING",
    "quiet_hours": "SLEEPING",
    "display_off": "SWITCHED OFF",
    "battery_empty": "CHARGE ME",
    "no_connection": "OFFLINE",
    "updating": "INSTALLING",
    "retired": "SKYPANE",
}
_LINES = {
    "quiet_hours": ("QUIET", "HOURS"),
    "display_off": ("DISPLAY", "OFF"),
    "battery_empty": ("BATTERY", "EMPTY"),
    "no_connection": ("NO", "CONNECTION"),
    "updating": ("FIRMWARE", "UPDATE"),
    "retired": ("FRAME", "RETIRED"),
}
_BODIES = {
    "display_off": style.DISPLAY_OFF_BODY_LINES,
    "battery_empty": style.BATTERY_EMPTY_BODY_LINES,
    "no_connection": style.NO_CONNECTION_BODY_LINES,
    "updating": style.UPDATING_BODY_LINES,
    "retired": RETIRED_BODY_LINES,
}
# Kinds that show the battery-low glyph and source-fault badge, as before.
_MARKED = ("watching", "quiet_hours", "display_off")

# Share of a giant line's slot its font may fill, leaving a gap between lines.
_LINE_FILL = 0.8
_GIANT_MAX_FRACTION = 330 / 1200  # of the canvas width, portrait
_LABEL_ICON_GAP_LANDSCAPE = 12


@dataclass(frozen=True)
class _Geometry:
    margin: int
    icon_top: int
    icon_h: int
    label_y: int
    label_px: int
    giant_top: int
    giant_bottom: int
    giant_max_px: int
    body_y: int
    body_px: int
    body_step: int


def _geometry(size: Size) -> _Geometry:
    """Portrait scales the 1200-wide design by width; landscape is designed
    from the short side: 6.9% margin, 12.5% icon."""
    w, h = size
    if w < h:
        k = w / 1200
        return _Geometry(
            margin=round(110 * k), icon_top=round(120 * k), icon_h=round(120 * k),
            label_y=round(262 * k), label_px=round(52 * k),
            giant_top=round(380 * k), giant_bottom=round(1180 * k),
            giant_max_px=round(w * _GIANT_MAX_FRACTION),
            body_y=round(1290 * k), body_px=round(40 * k), body_step=round(58 * k))
    margin = round(h * 0.069)
    icon_h = round(h * 0.125)
    label_y = margin + icon_h + round(h * _LABEL_ICON_GAP_LANDSCAPE / 480)
    body_px = round(h * 20 / 480)
    step = round(h * 28 / 480)
    body_y = h - margin - step - body_px
    return _Geometry(
        margin=margin, icon_top=margin, icon_h=icon_h, label_y=label_y,
        label_px=round(h * 22 / 480), giant_top=round(h * 150 / 480),
        giant_bottom=body_y - round(h * 20 / 480), giant_max_px=round(h * 0.25),
        body_y=body_y, body_px=body_px, body_step=step)


def _ink_box(font: ImageFont.FreeTypeFont, line: str) -> Tuple[int, int, int, int]:
    """Ink bounding box of `line` relative to its draw origin; unlike
    `font.getbbox` it includes the left side bearing."""
    mask, (off_x, off_y) = font.getmask2(line)
    left, top, right, bottom = mask.getbbox() or (0, 0, 0, 0)
    return off_x + left, off_y + top, off_x + right, off_y + bottom


def _ink_width(font: ImageFont.FreeTypeFont, line: str) -> int:
    box = _ink_box(font, line)
    return box[2] - box[0]


def _fit_anton(line: str, max_px: int, width: int) -> ImageFont.FreeTypeFont:
    """Anton at the largest size up to `max_px` whose `line` fits `width`."""
    px = max(1, max_px)
    font = fonts.anton(px)
    measured = _ink_width(font, line)
    if measured > width:
        px = max(1, int(px * width / measured))
        font = fonts.anton(px)
        while px > 1 and _ink_width(font, line) > width:
            px -= 1
            font = fonts.anton(px)
    return font


def _headline(kind: str, runway_id: str) -> Tuple[Tuple[str, ...], str]:
    """Giant lines and label of the watching screen: the empty heading minus
    its leading word ("Watching Runway 3" -> RUNWAY / 3). A heading without
    that word is split before its last word."""
    words = style.empty_heading_text(runway_id).upper().split()
    if words[0] == "WATCHING" and len(words) > 1:
        words = words[1:]
        cut = 1
    else:
        cut = max(1, len(words) - 1)
    first, rest = " ".join(words[:cut]), " ".join(words[cut:])
    return ((first, rest) if rest else (first,)), _LABELS[kind]


def _body_lines(kind: str, runway_id: str, quiet_hours_until: Optional[str]) -> Tuple[str, ...]:
    if kind == "watching":
        return tuple(style.empty_body_lines(runway_id))
    if kind == "quiet_hours":
        if isinstance(quiet_hours_until, str) and quiet_hours_until:
            return (style.QUIET_HOURS_BODY_TEMPLATE % quiet_hours_until,)
        return ()
    return tuple(_BODIES[kind])


def _paint_text(canvas: Image.Image, geom: _Geometry, size: Size, lines: Tuple[str, ...],
                label: str, body: Tuple[str, ...], ink: int) -> None:
    """Giant lines, label and body, each flush left at the margin."""
    draw = ImageDraw.Draw(canvas)
    width = size[0] - 2 * geom.margin
    slot = (geom.giant_bottom - geom.giant_top) / 2
    max_px = min(geom.giant_max_px, round(slot * _LINE_FILL))
    for i, line in enumerate(lines):
        font = _fit_anton(line, max_px, width)
        left, top, _right, _bottom = _ink_box(font, line)
        draw.text((geom.margin - left, round(geom.giant_top + slot * i) - top),
                  line, font=font, fill=ink)
    label_font = fonts.inter_bold(geom.label_px)
    draw.text((geom.margin - _ink_box(label_font, label)[0], geom.label_y),
              label, font=label_font, fill=ink)
    body_font = fonts.inter_bold(geom.body_px)
    for i, line in enumerate(body):
        draw.text((geom.margin, geom.body_y + i * geom.body_step), line, font=body_font, fill=ink)


def _paint_marks(canvas: Image.Image, size: Size, ink: int, source_fault: bool,
                 battery_low: bool) -> None:
    """Battery-low glyph and source-fault badge, drawn in the screen's ink."""
    if size[0] < size[1]:
        draw = ImageDraw.Draw(canvas)
        if source_fault:
            glyphs.draw_source_fault_badge(canvas, ink, weight="bold")
        if battery_low:
            glyphs.draw_battery_icon(canvas, draw, ink)
        return
    if battery_low:
        landscape_card.draw_battery_low(canvas, size, ink)
    if source_fault:
        geom = SimpleNamespace(margin=landscape_common.margin_for(size),
                               overlay_right=round(size[0] * 0.5))
        landscape_card.draw_source_fault(canvas, size, geom, ink, "bold")


def build_status(kind: str, size: Size, *, quiet_hours_until: Optional[str] = None,
                 source_fault: bool = False, battery_low: bool = False,
                 runway_id: str = device_config.DEFAULT_RUNWAY_ID,
                 flat: bool = False) -> Image.Image:
    """"P"-mode calm status canvas of `size` for `kind` (one of `KINDS`).

    `flat` gives a two-colour canvas (black field, white ink, no dither) so
    the firmware ink masks can be extracted exactly. `battery_empty` ignores
    every other argument: its bytes depend on `size` and `flat` alone.
    """
    if kind not in KINDS:
        raise ValueError("unknown status kind: %r" % (kind,))
    size = (int(size[0]), int(size[1]))
    if kind == "battery_empty":
        source_fault = battery_low = False
        quiet_hours_until = None
        runway_id = device_config.DEFAULT_RUNWAY_ID
    watching = kind == "watching"
    ink = style.EMPTY_INK if watching else style.DIMMED_INK
    if watching:
        canvas = pf.new_canvas(pf.IDX_WHITE, size)
    elif flat:
        canvas = pf.new_canvas(style.DIMMED_FIELD_IDX, size)
    else:
        canvas = dither.dithered_state_background(style.DIMMED_FIELD_IDX, size=size)
    geom = _geometry(size)
    if watching:
        lines, label = _headline(kind, runway_id)
    else:
        lines, label = _LINES[kind], _LABELS[kind]
    mask = icons.icon_mask(kind, geom.icon_h)
    canvas.paste(ink, (geom.margin, geom.icon_top), mask)
    _paint_text(canvas, geom, size, lines, label, _body_lines(kind, runway_id, quiet_hours_until), ink)
    if kind in _MARKED:
        _paint_marks(canvas, size, ink, source_fault, battery_low)
    return canvas
