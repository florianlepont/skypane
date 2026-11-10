"""Behaviour tests for layout C: lettering on top, whole aircraft at the bottom."""
import pytest

from server import panel_format as pf
from server.pairings import PAIRINGS
from server.plane import illustrations
from server.plane.render import giant
from server.plane.render.giant import aircraft, compose, compose_c
from server.plane.render.giant.field import field_pattern, ink_index
from server.plane.render.giant.palette_check import assert_giant_palette

SIZE = (pf.WIDTH, pf.HEIGHT)
FLIGHT = {"hex": "3985a7", "callsign": "AF1006", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Air France", "origin_city": "Paris", "destination_city": "Marseille",
    "callsign_iata": "AF1006",
}


def _render(pairing="blue_light", route=ROUTE, state="departing"):
    return giant.build_canvas(SIZE, "c", FLIGHT, state, route=route, pairing=PAIRINGS[pairing])


@pytest.mark.parametrize("pairing", sorted(PAIRINGS))
def test_renders_legally_for_every_pairing(pairing):
    canvas = _render(pairing)
    assert canvas.size == SIZE and canvas.mode == "P"
    assert_giant_palette(canvas, ink_index(PAIRINGS[pairing].field_ink))


def test_c_differs_from_the_other_layouts():
    c = _render()
    for other in ("a", "b", "a_diagonal"):
        assert c.tobytes() != giant.build_canvas(
            SIZE, other, FLIGHT, "departing", route=ROUTE, pairing=PAIRINGS["blue_light"]).tobytes()


@pytest.mark.parametrize("shrink", [False, True])
def test_lettering_box_ends_above_the_aircraft(shrink):
    path = illustrations.select_illustration(ROUTE, "B738")
    content = aircraft.load_content(path, round(SIZE[0] * compose_c.AIRCRAFT_WIDTH_FRAC))
    top = round(SIZE[1] * compose_c.AIRCRAFT_CENTER_Y_FRAC) - content.size[1] // 2
    bottom = compose_c.lettering_box(SIZE, shrink)[3]
    assert bottom + aircraft.halo_radius(SIZE) < top
    assert top + content.size[1] < round(SIZE[1] * compose.FLIGHT_TOP_FRAC)


def test_lettering_ink_stays_in_the_upper_part():
    pairing = PAIRINGS["blue_light"]
    canvas = _render()
    box = compose_c.lettering_box(SIZE, False)
    ink = ink_index(pairing.lettering_ink)
    assert any(v == ink and n > 1000 for n, v in canvas.crop(box).getcolors(maxcolors=256))
    assert box[3] < SIZE[1] * 0.6
    gap = (0, box[1] - 20, SIZE[0], box[1] - 4)
    assert canvas.crop(gap).tobytes() == field_pattern(pairing, SIZE).crop(gap).tobytes()


def test_no_band_is_drawn():
    pairing = PAIRINGS["blue_light"]
    canvas = _render()
    strip = (0, 0, 30, SIZE[1])
    assert canvas.crop(strip).tobytes() == field_pattern(pairing, SIZE).crop(strip).tobytes()
    right = (SIZE[0] - 30, 0, SIZE[0], SIZE[1])
    assert canvas.crop(right).tobytes() == field_pattern(pairing, SIZE).crop(right).tobytes()


def test_airline_only_and_unknown_flight_texts():
    lines, is_airline = compose.lettering_split({"airline_name": "Air France"}, "departing")
    assert is_airline and "".join(lines.lines) == "AIRFRANCE"
    assert _render(route={"airline_name": "Air France"}).tobytes() != _render(route=None).tobytes()


def test_flight_number_and_direction_are_drawn():
    plain = _render()
    assert _render(route={**ROUTE, "callsign_iata": None}).tobytes() != plain.tobytes()
    assert _render(state="arriving").tobytes() != plain.tobytes()
