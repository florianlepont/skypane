"""The direction word (DEPARTING / ARRIVING / OVERHEAD) on every giant layout,
portrait and landscape: it is drawn as ink in the top-left corner and never
touches the lettering or the aircraft. Names are lettered without hyphens."""
import pytest
from PIL import Image, ImageChops

from server import panel_format as pf
from server.pairings import PAIRINGS
from server.plane.render import giant, style
from server.plane.render.giant import (
    compose, compose_c, compose_landscape, fonts, geometry_landscape as geo, lettering, split)
from server.plane.render.giant.field import field_pattern

PORTRAIT = (pf.WIDTH, pf.HEIGHT)
LANDSCAPE = (800, 480)
LAYOUTS = ("a", "b", "c", "a_diagonal")
STATES = ("departing", "arriving", "overhead")
FLIGHT = {"hex": "3985a7", "callsign": "AF1006", "aircraft_type": "B738"}
BASE = {"airline_name": "Air France", "origin_city": "Paris", "callsign_iata": "AF1006"}
NAMES = ("Clermont-Ferrand", "Pau")
BLANK = 1
LETTER_INK = 2


def _route(name):
    return {**BASE, "destination_city": name, "origin_city": name}


def _zone(size, state):
    """Pixel box of the direction word."""
    w, h = size
    if size == LANDSCAPE:
        pos = (round(w * geo.MARGIN), round(h * geo.DIRECTION_TOP))
        font = fonts.inter_bold(round(h * geo.DIRECTION_PX))
    else:
        pos = (round(w * compose.MARGIN_FRAC), round(h * compose.DIRECTION_TOP_FRAC))
        font = fonts.inter_bold(round(w * compose.DIRECTION_PX_FRAC))
    left, top, right, bottom = font.getbbox(style.STATE_LABEL_TEXT[state])
    return pos[0] + left, pos[1] + top, pos[0] + right, pos[1] + bottom


def _lettering_canvas(size, layout, state, route):
    canvas = Image.new("P", size, BLANK)
    if size == LANDSCAPE:
        result, _ = compose.lettering_split(route, state, split.LANDSCAPE)
        box = compose_landscape._lettering_box(size, compose_landscape.SPECS[layout])
    else:
        result, _ = compose.lettering_split(route, state)
        if layout == "c":
            box = compose_c.lettering_box(size, result.shrink_block)
        else:
            box = compose._lettering_box(size, result.shrink_block)
    lettering.paint_lines(canvas, result.lines, box, LETTER_INK)
    return canvas


def _aircraft_canvas(size, layout, route):
    canvas = Image.new("P", size, BLANK)
    path = compose._aircraft_path(FLIGHT, route, None)
    if size == LANDSCAPE:
        compose_landscape._paint_aircraft(canvas, compose_landscape.SPECS[layout], path)
    elif layout == "b":
        compose._paint_whole(canvas, path)
    elif layout == "c":
        compose._paint_whole(canvas, path, compose_c.AIRCRAFT_WIDTH_FRAC,
                             compose_c.AIRCRAFT_CENTER_X_FRAC, compose_c.AIRCRAFT_CENTER_Y_FRAC)
    else:
        compose._paint_halves(canvas, path)
    return canvas


def _touched(canvas, zone):
    return ImageChops.difference(
        canvas, Image.new("P", canvas.size, BLANK)).crop(zone).getbbox() is not None


def _render(size, layout, state, route, pairing="blue_light"):
    return giant.build_canvas(size, layout, FLIGHT, state, route=route, pairing=PAIRINGS[pairing])


def _ink_pixels(size, canvas, zone, pairing="blue_light"):
    diff = ImageChops.difference(canvas, field_pattern(PAIRINGS[pairing], size)).crop(zone)
    return diff.width * diff.height - diff.histogram()[0]


@pytest.mark.parametrize("size", (PORTRAIT, LANDSCAPE), ids=("portrait", "landscape"))
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("name", NAMES)
def test_direction_word_is_ink_and_clear_of_lettering_and_aircraft(size, layout, state, name):
    route = _route(name)
    zone = _zone(size, state)
    assert _ink_pixels(size, _render(size, layout, state, route), zone) > 40
    assert not _touched(_lettering_canvas(size, layout, state, route), zone)
    assert not _touched(_aircraft_canvas(size, layout, route), zone)


@pytest.mark.parametrize("size", (PORTRAIT, LANDSCAPE), ids=("portrait", "landscape"))
@pytest.mark.parametrize("layout", LAYOUTS)
def test_each_state_draws_its_own_word(size, layout):
    zone = _zone(size, "overhead")
    crops = {s: _render(size, layout, s, _route("Pau")).crop(zone).tobytes() for s in STATES}
    assert len(set(crops.values())) == 3


@pytest.mark.parametrize("state, word", (("departing", "DEPARTING"), ("arriving", "ARRIVING"),
                                         ("overhead", "OVERHEAD")))
def test_state_wording(state, word):
    assert style.STATE_LABEL_TEXT[state] == word


@pytest.mark.parametrize("orientation", (split.PORTRAIT, split.LANDSCAPE))
def test_hyphenated_name_is_lettered_without_a_hyphen(orientation):
    result, _ = compose.lettering_split(_route("Clermont-Ferrand"), "departing", orientation)
    assert result.lines
    assert not any("-" in line for line in result.lines)
