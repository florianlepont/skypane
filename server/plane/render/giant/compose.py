"""Portrait compositors for the giant-lettering layouts.

Every layout is built in the same order: field, band (diagonal only), giant
lettering, aircraft with its white halo, then the small text. Geometry is
expressed as fractions of the canvas size so another size can reuse it.
Every mask is strictly binary, so the canvas only ever holds palette indices.
"""
from typing import Callable, Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from server import panel_format as pf
from server.pairings import Pairing
from server.plane import enrich, illustrations
from server.plane.render import glyphs, style, text
from server.plane.render.giant import aircraft, fonts, lettering, split
from server.plane.render.giant.field import field_pattern, ink_index, small_text_ink_pattern

Size = Tuple[int, int]
Box = Tuple[int, int, int, int]

# Lettering box as fractions of (width, height, width, height).
LETTERING_BOX_FRAC = (40 / 1200, 130 / 1600, 1160 / 1200, 1290 / 1600)
# Share of the box height kept when the splitter reports a squeezed block.
SHRINK_BLOCK_FRAC = 0.85
# Whole-aircraft layout: painted width and vertical centre.
WHOLE_WIDTH_FRAC = 1120 / 1200
WHOLE_CENTER_Y_FRAC = 710 / 1600
# Small text: margin and sizes as fractions of the canvas width, tops as
# fractions of its height.
MARGIN_FRAC = 64 / 1200
DIRECTION_PX_FRAC = 56 / 1200
DIRECTION_TOP_FRAC = 56 / 1600
FLIGHT_PX_FRAC = 124 / 1200
FLIGHT_TOP_FRAC = 1290 / 1600
AIRLINE_PX_FRAC = 48 / 1200
AIRLINE_TOP_FRAC = 1432 / 1600
# The flight number never takes more than this share of the width.
FLIGHT_MAX_WIDTH_FRAC = 0.5
MIN_TEXT_PX = 16
MAX_FLIGHT_CHARS = 12
UNKNOWN_FLIGHT_WORDS = "Unknown flight"
MASK_THRESHOLD = 127


def _binary(mask: Image.Image) -> Image.Image:
    return mask.point(lambda p: 255 if p > MASK_THRESHOLD else 0)


def band_mask(size: Size) -> Image.Image:
    """Binary "L" mask of the diagonal band, from the classic band geometry."""
    w, h = size
    poly = [
        (style.BAND_TOP_LEFT_FRAC * w, 0), (style.BAND_TOP_RIGHT_FRAC * w, 0),
        (style.BAND_BOT_RIGHT_FRAC * w, h), (style.BAND_BOT_LEFT_FRAC * w, h),
    ]
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    return mask


def _lettering_box(size: Size, shrink: bool) -> Box:
    w, h = size
    x0, y0, x1, y1 = LETTERING_BOX_FRAC
    top, bottom = round(y0 * h), round(y1 * h)
    if shrink:
        bottom = top + round((bottom - top) * SHRINK_BLOCK_FRAC)
    return round(x0 * w), top, round(x1 * w), bottom


def _clean(value: object) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _route_field(route: object, key: str) -> Optional[str]:
    if not isinstance(route, dict):
        return None
    try:
        return _clean(route.get(key))
    except Exception:
        return None


def _airline_name(route: object) -> Optional[str]:
    name = _route_field(route, "airline_name")
    return _clean(text.display_airline_name(name)) if name else None


def _city(route: object, state: str) -> Optional[str]:
    if not isinstance(route, dict):
        return None
    lookup_state = "departing" if state == "overhead" else state
    try:
        return _clean(enrich.city_for_state(route, lookup_state))
    except Exception:
        return None


def _drawable(name: Optional[str],
              orientation: str = split.PORTRAIT) -> Optional[split.Split]:
    """The split of `name` when Anton can letter it, trying an accent-free
    spelling when it cannot; None when the name is missing or not drawable."""
    if not name:
        return None
    for candidate in (name, fonts.ascii_fallback(name)):
        if not candidate:
            continue
        result = split.split_destination(candidate, orientation)
        if result.lines and lettering.supported_lines(result.lines):
            return result
    return None


def lettering_split(route: object, state: str,
                    orientation: str = split.PORTRAIT) -> Tuple[split.Split, bool]:
    """The lines to letter and whether they are the airline name.

    The destination city (the origin when arriving) comes first, then the
    airline name, then the unknown-flight wording. `orientation` is the
    splitter's: landscape keeps every text on one line.
    """
    by_city = _drawable(_city(route, state), orientation)
    if by_city is not None:
        return by_city, False
    by_airline = _drawable(_airline_name(route), orientation)
    if by_airline is not None:
        return by_airline, True
    fallback = split.split_destination(UNKNOWN_FLIGHT_WORDS, orientation)
    return fallback, False


def _fit_font(px: int, label: str, max_width: float) -> ImageFont.FreeTypeFont:
    while px > MIN_TEXT_PX:
        font = fonts.inter_bold(px)
        if font.getlength(label) <= max_width:
            return font
        px -= 2
    return fonts.inter_bold(MIN_TEXT_PX)


def _small_text_mask(size: Size, state: str, route: object, hide_airline: bool) -> Image.Image:
    """Binary mask of the direction word (top-left) and the flight number and
    airline name (bottom-right)."""
    w, h = size
    margin = round(w * MARGIN_FRAC)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    direction = style.STATE_LABEL_TEXT.get(state, "")
    draw.text((margin, round(h * DIRECTION_TOP_FRAC)), direction,
              font=fonts.inter_bold(round(w * DIRECTION_PX_FRAC)), fill=255)
    right = w - margin
    flight_no = (_route_field(route, "callsign_iata") or "")[:MAX_FLIGHT_CHARS]
    if flight_no:
        font = _fit_font(round(w * FLIGHT_PX_FRAC), flight_no, w * FLIGHT_MAX_WIDTH_FRAC)
        draw.text((right, round(h * FLIGHT_TOP_FRAC)), flight_no, font=font, fill=255, anchor="ra")
    airline = None if hide_airline else _airline_name(route)
    if airline:
        font = _fit_font(round(w * AIRLINE_PX_FRAC), airline, w - 2 * margin)
        draw.text((right, round(h * AIRLINE_TOP_FRAC)), airline, font=font, fill=255, anchor="ra")
    return _binary(mask)


def paint_text_mask(canvas: Image.Image, pairing: Pairing, mask: Image.Image,
                    band: Optional[Image.Image]) -> None:
    """Paint the small-text `mask` in the pairing's small-text ink; inside
    `band` (when given) it takes the field shade."""
    ink = small_text_ink_pattern(pairing, canvas.size)
    if band is not None:
        ink.paste(field_pattern(pairing, canvas.size), (0, 0), band)
    canvas.paste(ink, (0, 0), mask)


def _paint_small_text(canvas: Image.Image, pairing: Pairing, state: str, route: object,
                      hide_airline: bool, band: Optional[Image.Image]) -> None:
    paint_text_mask(canvas, pairing, _small_text_mask(canvas.size, state, route, hide_airline), band)


def _marker_ink(pairing: Pairing) -> int:
    """Ink for the status glyphs: black where the lettering ink is yellow."""
    if pairing.small_text_dither_toward_black:
        return pf.IDX_BLACK
    return ink_index(pairing.lettering_ink)


def _paint_status_marks(canvas: Image.Image, pairing: Pairing, source_fault: bool,
                        battery_low: bool) -> None:
    ink = _marker_ink(pairing)
    if source_fault:
        glyphs.draw_source_fault_badge(canvas, ink)
    if battery_low:
        glyphs.draw_battery_icon(canvas, ImageDraw.Draw(canvas), ink)


def _aircraft_path(flight: object, route: object, state_dir: Optional[str]) -> Optional[str]:
    aircraft_type = flight.get("aircraft_type") if isinstance(flight, dict) else None
    return illustrations.select_illustration(route, aircraft_type, state_dir=state_dir)


def _paint_whole(canvas: Image.Image, path: Optional[str],
                 width_frac: float = WHOLE_WIDTH_FRAC, center_x_frac: float = 0.5,
                 center_y_frac: float = WHOLE_CENTER_Y_FRAC) -> None:
    """Whole aircraft `width_frac` of the canvas width wide, centred on the
    given fractions of the canvas."""
    w, h = canvas.size
    content = aircraft.load_content(path, round(w * width_frac)) if path else None
    if content is None:
        return
    left = round(w * center_x_frac) - content.size[0] // 2
    top = round(h * center_y_frac) - content.size[1] // 2
    aircraft.paint_aircraft(canvas, content, left, top, aircraft.halo_radius(canvas.size))


def _paint_halves(canvas: Image.Image, path: Optional[str],
                  nose_plane_frac: float = aircraft.NOSE_PLANE_WIDTH_FRAC,
                  rear_plane_frac: float = aircraft.REAR_PLANE_WIDTH_FRAC,
                  nose_left_frac: float = aircraft.NOSE_LEFT_X_FRAC,
                  rear_right_frac: float = aircraft.REAR_RIGHT_X_FRAC,
                  nose_center_y_frac: float = aircraft.NOSE_CENTER_Y_FRAC,
                  rear_bottom_y_frac: float = aircraft.REAR_BOTTOM_Y_FRAC) -> None:
    """Nose half entering from the right edge and the smaller rear half
    entering from the left edge below it; both cut columns lie off-canvas.
    The plane fractions are the widths of the whole aircraft behind each half
    as shares of the canvas width; the anchors are where the cockpit tip and
    the tail end land, as shares of the canvas width; the vertical fractions
    are the nose half's centre and the rear half's bottom as shares of the
    canvas height."""
    if not path:
        return
    w, _h = canvas.size
    halo = aircraft.halo_radius(canvas.size)
    cut = aircraft.cut_fraction_for_path(path)
    large = aircraft.load_content(path, round(w * nose_plane_frac))
    small = aircraft.load_content(path, round(w * rear_plane_frac))
    if large is None or small is None:
        return
    nose, _ = aircraft.split_halves(
        large, aircraft.nose_cut(canvas.size, cut, nose_plane_frac, nose_left_frac))
    _, rear = aircraft.split_halves(
        small, aircraft.rear_cut(canvas.size, cut, rear_plane_frac, rear_right_frac))
    nose_box = aircraft.nose_half(canvas.size, nose.size, nose_center_y_frac, nose_left_frac)
    aircraft.paint_aircraft(canvas, nose, nose_box[0], nose_box[1], halo)
    rear_box = aircraft.rear_half(canvas.size, rear.size, rear_bottom_y_frac, rear_right_frac)
    aircraft.paint_aircraft(canvas, rear, rear_box[0], rear_box[1], halo)


def _compose(size: Size, flight: object, state: str, route: object, pairing: Pairing,
             state_dir: Optional[str], source_fault: bool, battery_low: bool,
             halves: bool, diagonal: bool) -> Image.Image:
    canvas = field_pattern(pairing, size)
    band = band_mask(size) if diagonal and pairing.band_allowed else None
    if band is not None:
        canvas.paste(ink_index(pairing.lettering_ink), (0, 0), band)
    result, is_airline = lettering_split(route, state)
    lettering.paint_lines(
        canvas, result.lines, _lettering_box(size, result.shrink_block),
        ink_index(pairing.lettering_ink), band,
        field_pattern(pairing, size) if band is not None else None)
    path = _aircraft_path(flight, route, state_dir)
    if halves:
        _paint_halves(canvas, path)
    else:
        _paint_whole(canvas, path)
    _paint_small_text(canvas, pairing, state, route, is_airline, band)
    _paint_status_marks(canvas, pairing, source_fault, battery_low)
    return canvas


def compose_b(size: Size, flight: object, state: str, route: object, pairing: Pairing,
              state_dir: Optional[str] = None, source_fault: bool = False,
              battery_low: bool = False) -> Image.Image:
    """Layout B: the whole aircraft centred in front of the lettering."""
    return _compose(size, flight, state, route, pairing, state_dir, source_fault,
                    battery_low, halves=False, diagonal=False)


def compose_a(size: Size, flight: object, state: str, route: object, pairing: Pairing,
              state_dir: Optional[str] = None, source_fault: bool = False,
              battery_low: bool = False) -> Image.Image:
    """Layout A: nose from the right edge, rear half from the left edge."""
    return _compose(size, flight, state, route, pairing, state_dir, source_fault,
                    battery_low, halves=True, diagonal=False)


def compose_a_diagonal(size: Size, flight: object, state: str, route: object,
                       pairing: Pairing, state_dir: Optional[str] = None,
                       source_fault: bool = False, battery_low: bool = False) -> Image.Image:
    """Layout A with the diagonal band; the white pairing draws no band."""
    return _compose(size, flight, state, route, pairing, state_dir, source_fault,
                    battery_low, halves=True, diagonal=True)


Composer = Callable[..., Image.Image]
COMPOSERS: Dict[str, Composer] = {
    "a": compose_a,
    "b": compose_b,
    "a_diagonal": compose_a_diagonal,
}

