"""Portrait compositor for layout C: the giant lettering compressed into the
top of the frame and the whole aircraft below it at the bottom. No band is
drawn; the field is the same plain pattern as the other layouts.
"""
from typing import Optional, Tuple

from PIL import Image

from server.pairings import Pairing
from server.plane.render.giant import lettering
from server.plane.render.giant.compose import (
    SHRINK_BLOCK_FRAC, _aircraft_path, _paint_small_text, _paint_status_marks,
    _paint_whole, lettering_split)
from server.plane.render.giant.field import field_pattern, ink_index

Size = Tuple[int, int]
Box = Tuple[int, int, int, int]

# Lettering box as fractions of (width, height, width, height); it ends above
# the aircraft's tail fin.
LETTERING_BOX_FRAC = (40 / 1200, 138 / 1600, 1160 / 1200, 888 / 1600)
# Whole aircraft: painted width and centre.
AIRCRAFT_WIDTH_FRAC = 1116 / 1200
AIRCRAFT_CENTER_X_FRAC = 0.5
AIRCRAFT_CENTER_Y_FRAC = 1072 / 1600


def lettering_box(size: Size, shrink: bool) -> Box:
    """Pixel box of the lettering block; `shrink` keeps the top and cuts the
    height to the squeezed-block share."""
    w, h = size
    x0, y0, x1, y1 = LETTERING_BOX_FRAC
    top, bottom = round(y0 * h), round(y1 * h)
    if shrink:
        bottom = top + round((bottom - top) * SHRINK_BLOCK_FRAC)
    return round(x0 * w), top, round(x1 * w), bottom


def compose_c(size: Size, flight: object, state: str, route: object, pairing: Pairing,
              state_dir: Optional[str] = None, source_fault: bool = False,
              battery_low: bool = False) -> Image.Image:
    """Layout C: lettering on top, the whole aircraft at the bottom."""
    canvas = field_pattern(pairing, size)
    result, is_airline = lettering_split(route, state)
    lettering.paint_lines(canvas, result.lines, lettering_box(size, result.shrink_block),
                          ink_index(pairing.lettering_ink))
    _paint_whole(canvas, _aircraft_path(flight, route, state_dir), AIRCRAFT_WIDTH_FRAC,
                 AIRCRAFT_CENTER_X_FRAC, AIRCRAFT_CENTER_Y_FRAC)
    _paint_small_text(canvas, pairing, state, route, is_airline, None)
    _paint_status_marks(canvas, pairing, source_fault, battery_low)
    return canvas
