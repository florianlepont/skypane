"""Behaviour tests for the portrait giant-lettering compositors."""
import time

import pytest
from PIL import Image

from server import panel_format as pf
from server.pairings import PAIRINGS
from server.plane import illustrations
from server.plane.render.giant import aircraft, compose
from server.plane.render.giant import build_canvas as giant_canvas
from server.plane.render.giant.field import field_pattern, ink_index
from server.plane.render.giant.palette_check import assert_giant_palette

SIZE = (pf.WIDTH, pf.HEIGHT)
LAYOUTS = ("a", "b", "a_diagonal")
FLIGHT = {"hex": "3985a7", "callsign": "AF1006", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Air France", "origin_city": "Paris", "destination_city": "Marseille",
    "callsign_iata": "AF1006",
}
AIRLINE_ONLY = {"airline_name": "Air France"}
RENDER_BUDGET_S = 10.0


def _render(layout, pairing="blue_light", route=ROUTE, state="departing", **kwargs):
    return giant_canvas(SIZE, layout, FLIGHT, state, route=route, pairing=PAIRINGS[pairing], **kwargs)


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("pairing", sorted(PAIRINGS))
def test_layout_renders_legally_with_lettering(layout, pairing):
    canvas = _render(layout, pairing)
    assert canvas.size == SIZE and canvas.mode == "P"
    assert_giant_palette(canvas, ink_index(PAIRINGS[pairing].field_ink))
    box = compose._lettering_box(SIZE, False)
    ink = ink_index(PAIRINGS[pairing].lettering_ink)
    region = canvas.crop(box).getcolors(maxcolors=256)
    assert any(value == ink and count > 1000 for count, value in region)


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("state", ["departing", "arriving", "overhead"])
def test_each_state_renders(layout, state):
    assert_giant_palette(_render(layout, state=state), pf.IDX_BLUE)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_unknown_route_renders(layout):
    canvas = _render(layout, route=None)
    assert_giant_palette(canvas, pf.IDX_BLUE)
    assert canvas.tobytes() != _render(layout).tobytes()


def test_airline_only_route_letters_the_airline_name():
    lines, is_airline = compose.lettering_split(AIRLINE_ONLY, "departing")
    assert is_airline and "".join(lines.lines).replace(" ", "") == "AIRFRANCE"
    unknown = _render("b", route={"airline_name": None})
    airline = _render("b", route=AIRLINE_ONLY)
    assert airline.tobytes() != unknown.tobytes()
    lines, is_airline = compose.lettering_split({}, "departing")
    assert not is_airline and lines.lines == ("UNKNOWN", "FLIGHT")


def test_arriving_uses_the_origin_city():
    lines, _ = compose.lettering_split(ROUTE, "arriving")
    assert "".join(lines.lines) == "PARIS"
    lines, _ = compose.lettering_split(ROUTE, "departing")
    assert "".join(lines.lines) == "MARSEILLE"


def test_diagonal_draws_a_band_except_for_the_white_pairing():
    plain = _render("a", "blue_light")
    banded = _render("a_diagonal", "blue_light")
    assert plain.tobytes() != banded.tobytes()
    assert _render("a", "white").tobytes() == _render("a_diagonal", "white").tobytes()


def test_diagonal_lettering_inside_the_band_takes_the_field_shade():
    banded = _render("a_diagonal", "blue_light")
    mask = compose.band_mask(SIZE)
    inside = Image.composite(banded, Image.new("P", SIZE, 0), mask)
    solid = ink_index("blue")
    assert inside.getcolors(maxcolors=256)
    assert sum(c for c, v in inside.getcolors(maxcolors=256) if v == solid) > 100000


def test_flight_number_is_drawn_bottom_right():
    with_number = _render("b")
    without = _render("b", route={**ROUTE, "callsign_iata": None})
    diff = Image.eval(
        Image.frombytes("L", SIZE, bytes(a != b for a, b in zip(with_number.tobytes(), without.tobytes()))),
        lambda p: 255 if p else 0)
    left, top, right, bottom = diff.getbbox()
    assert left > SIZE[0] // 3 and top > SIZE[1] * 0.75 and right <= SIZE[0]


def test_halves_cut_columns_lie_outside_the_frame():
    path = illustrations.select_illustration(ROUTE, "B738")
    w, h = SIZE
    cut = aircraft.cut_fraction_for_path(path)
    large = aircraft.load_content(path, round(w * aircraft.NOSE_PLANE_WIDTH_FRAC))
    small = aircraft.load_content(path, round(w * aircraft.REAR_PLANE_WIDTH_FRAC))
    nose, _ = aircraft.split_halves(large, aircraft.nose_cut(SIZE, cut))
    _, rear = aircraft.split_halves(small, aircraft.rear_cut(SIZE, cut))
    assert aircraft.nose_half(SIZE, nose.size)[2] > w
    assert aircraft.rear_half(SIZE, rear.size)[0] < 0


def test_layout_a_aircraft_touches_both_side_edges():
    base = _render("a")
    blank = field_pattern(PAIRINGS["blue_light"], SIZE)
    left = base.crop((0, 700, 3, 1300)).tobytes() != blank.crop((0, 700, 3, 1300)).tobytes()
    right = base.crop((w := SIZE[0] - 3, 250, SIZE[0], 700)).tobytes() != blank.crop((w, 250, SIZE[0], 700)).tobytes()
    assert left and right


def test_status_marks_change_the_picture():
    plain = _render("b")
    assert _render("b", battery_low=True).tobytes() != plain.tobytes()
    assert _render("b", source_fault=True).tobytes() != plain.tobytes()


def test_unknown_layout_without_compositor_renders_the_default():
    assert giant_canvas(SIZE, "no-such-layout", FLIGHT, "departing", route=ROUTE, pairing=PAIRINGS["grey"]).tobytes() == \
        giant_canvas(SIZE, "b", FLIGHT, "departing", route=ROUTE, pairing=PAIRINGS["grey"]).tobytes()


def test_render_time_is_far_below_the_poll_period():
    start = time.monotonic()
    for layout in LAYOUTS:
        _render(layout, "red_light")
    assert time.monotonic() - start < RENDER_BUDGET_S
