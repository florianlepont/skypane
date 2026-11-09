"""Landscape compositors for the giant-lettering layouts. Same order as the
portrait ones (field, band, lettering, aircraft, small text), with the
destination on one stretched line; the geometry lives in `geometry_landscape`.
"""
from typing import Optional, Tuple

from types import SimpleNamespace

from PIL import Image, ImageDraw

from server.pairings import Pairing
from server.plane.render import landscape_card, landscape_common, style
from server.plane.render.giant import fonts, lettering, split
from server.plane.render.giant.compose import (
    MAX_FLIGHT_CHARS, _aircraft_path, _airline_name,
    _binary, _fit_font, _marker_ink, _paint_halves, _paint_whole, _route_field, band_mask,
    lettering_split, paint_text_mask)
from server.plane.render.giant.field import field_pattern, ink_index
from server.plane.render.giant.geometry_landscape import (
    DIRECTION_PX, DIRECTION_TOP, MARGIN, SPECS, LandscapeSpec)

Size = Tuple[int, int]
# Share of the width the flight number may take.
FLIGHT_MAX_WIDTH_FRAC = 0.45


# A left-hand footer starts right of the status marks when they are shown.
FOOTER_LEFT_LIMIT = 0.1
FOOTER_X_BATTERY = 0.17
FOOTER_X_FAULT = 0.5


def _footer_x(spec: LandscapeSpec, source_fault: bool, battery_low: bool) -> float:
    foot = spec.footer
    if foot.align_right or foot.x >= FOOTER_LEFT_LIMIT:
        return foot.x
    if source_fault:
        return FOOTER_X_FAULT
    return FOOTER_X_BATTERY if battery_low else foot.x


def _small_text_mask(size: Size, spec: LandscapeSpec, state: str, route: object,
                     hide_airline: bool, footer_x: float) -> Image.Image:
    """Binary mask of the direction word (top-left), the flight number and
    the airline name."""
    w, h = size
    foot = spec.footer
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.text((round(w * MARGIN), round(h * DIRECTION_TOP)),
              style.STATE_LABEL_TEXT.get(state, ""),
              font=fonts.inter_bold(round(h * DIRECTION_PX)), fill=255)
    x = round(w * footer_x)
    anchor = "ra" if foot.align_right else "la"
    room = (x if foot.align_right else w - x) - round(w * MARGIN)
    flight_no = (_route_field(route, "callsign_iata") or "")[:MAX_FLIGHT_CHARS]
    if flight_no:
        font = _fit_font(round(h * foot.flight_px), flight_no, min(room, w * FLIGHT_MAX_WIDTH_FRAC))
        draw.text((x, round(h * foot.flight_top)), flight_no, font=font, fill=255, anchor=anchor)
    airline = None if hide_airline else _airline_name(route)
    if airline:
        font = _fit_font(round(h * foot.airline_px), airline, room)
        draw.text((x, round(h * foot.airline_top)), airline, font=font, fill=255, anchor=anchor)
    return _binary(mask)


def _lettering_box(size: Size, spec: LandscapeSpec) -> Tuple[int, int, int, int]:
    w, h = size
    x0, y0, x1, y1 = spec.box
    return round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)


def _paint_aircraft(canvas: Image.Image, spec: LandscapeSpec, path: Optional[str]) -> None:
    if spec.halves is not None:
        g = spec.halves
        _paint_halves(canvas, path, g.nose_plane, g.rear_plane, g.nose_left, g.rear_right,
                      g.nose_center_y, g.rear_bottom_y)
    elif spec.whole is not None:
        _paint_whole(canvas, path, spec.whole.width, spec.whole.center_x, spec.whole.center_y)


def _paint_marks(canvas: Image.Image, pairing: Pairing, source_fault: bool,
                 battery_low: bool) -> None:
    """Battery-low glyph and source-fault badge in the bottom-left corner, in
    the landscape card's geometry."""
    ink = _marker_ink(pairing)
    size = canvas.size
    if battery_low:
        landscape_card.draw_battery_low(canvas, size, ink)
    if source_fault:
        margin = landscape_common.margin_for(size)
        geom = SimpleNamespace(margin=margin, overlay_right=round(size[0] * FOOTER_X_FAULT))
        landscape_card.draw_source_fault(canvas, size, geom, ink, "bold")


def compose_landscape(layout: str, size: Size, flight: object, state: str, route: object,
                      pairing: Pairing, state_dir: Optional[str] = None,
                      source_fault: bool = False, battery_low: bool = False) -> Image.Image:
    """Landscape canvas of layout `layout` ("a", "b", "c" or "a_diagonal")."""
    spec = SPECS[layout]
    canvas = field_pattern(pairing, size)
    band = band_mask(size) if spec.diagonal and pairing.band_allowed else None
    if band is not None:
        canvas.paste(ink_index(pairing.lettering_ink), (0, 0), band)
    result, is_airline = lettering_split(route, state, split.LANDSCAPE)
    lettering.paint_lines(
        canvas, result.lines, _lettering_box(size, spec), ink_index(pairing.lettering_ink),
        band, field_pattern(pairing, size) if band is not None else None)
    _paint_aircraft(canvas, spec, _aircraft_path(flight, route, state_dir))
    footer_x = _footer_x(spec, source_fault, battery_low)
    paint_text_mask(
        canvas, pairing, _small_text_mask(size, spec, state, route, is_airline, footer_x), band)
    _paint_marks(canvas, pairing, source_fault, battery_low)
    return canvas


def _for(layout: str):
    def compose(size: Size, flight: object, state: str, route: object, pairing: Pairing,
                state_dir: Optional[str] = None, source_fault: bool = False,
                battery_low: bool = False) -> Image.Image:
        return compose_landscape(layout, size, flight, state, route, pairing, state_dir,
                                 source_fault, battery_low)
    compose.__name__ = "compose_landscape_" + layout
    return compose


COMPOSERS = {layout: _for(layout) for layout in SPECS}
