"""Behaviour tests for the landscape (800x480) giant layouts."""
import pytest

import server.hardware as hardware
from server import panel_format as pf
from server.pairings import PAIRINGS
from server.plane.render import giant, layout
from server.plane.render.giant import compose, compose_landscape, split
from server.plane.render.giant.field import field_pattern, ink_index
from server.plane.render.giant.palette_check import assert_giant_palette

SIZE = (800, 480)
PROFILE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
LAYOUTS = ("a", "b", "c", "a_diagonal")
FLIGHT = {"hex": "3985a7", "callsign": "AF1006", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Air France", "origin_city": "Paris", "destination_city": "Marseille",
    "callsign_iata": "AF1006",
}
LONG = {**ROUTE, "destination_city": "Clermont-Ferrand"}
SHORT = {**ROUTE, "destination_city": "Pau"}
AIRLINE_ONLY = {"airline_name": "Air France"}


def _render(layout_id, pairing="blue_light", route=ROUTE, state="departing"):
    return giant.build_canvas(SIZE, layout_id, FLIGHT, state, route=route, pairing=PAIRINGS[pairing])


def _ink_bands(canvas, layout_id, pairing="blue_light"):
    """Number of separate horizontal runs of lettering-ink rows in the box."""
    spec = compose_landscape.SPECS[layout_id]
    x0, y0, x1, y1 = compose_landscape._lettering_box(SIZE, spec)
    ink = ink_index(PAIRINGS[pairing].lettering_ink)
    # Columns away from the aircraft and the small text: the left strip.
    strip = canvas.crop((x0, y0, x0 + 40, y1))
    rows = [any(strip.getpixel((x, y)) == ink for x in range(0, 40, 2))
            and sum(strip.getpixel((x, y)) == ink for x in range(40)) > 20
            for y in range(strip.height)]
    return sum(1 for i, on in enumerate(rows) if on and (i == 0 or not rows[i - 1]))


@pytest.mark.parametrize("layout_id", LAYOUTS)
@pytest.mark.parametrize("pairing", sorted(PAIRINGS))
def test_renders_legally_at_the_profile_size(layout_id, pairing):
    canvas = _render(layout_id, pairing)
    assert canvas.size == SIZE and canvas.mode == "P"
    assert_giant_palette(canvas, ink_index(PAIRINGS[pairing].field_ink))


@pytest.mark.parametrize("layout_id", LAYOUTS)
def test_profile_dispatch_packs_192000_bytes(layout_id):
    canvas = layout.build_canvas(
        FLIGHT, "departing", route=ROUTE, theme_id="blue_light", profile=PROFILE, layout=layout_id)
    assert canvas.size == SIZE
    assert len(pf.pack_panel(canvas)) == 192000


@pytest.mark.parametrize("layout_id", LAYOUTS)
def test_layouts_differ_from_each_other(layout_id):
    others = {o: _render(o).tobytes() for o in LAYOUTS if o != layout_id}
    assert _render(layout_id).tobytes() not in others.values()


@pytest.mark.parametrize("route", [ROUTE, LONG, SHORT, AIRLINE_ONLY, None])
def test_destination_is_a_single_line(route):
    lines, _ = compose.lettering_split(route, "departing", split.LANDSCAPE)
    assert len(lines.lines) == 1
    canvas = _render("b", route=route)
    assert _ink_bands(canvas, "b") == 1


def test_long_name_is_one_stretched_line_not_stacked():
    lines, _ = compose.lettering_split(LONG, "departing", split.LANDSCAPE)
    assert lines.lines == ("CLERMONT FERRAND",)
    portrait, _ = compose.lettering_split(LONG, "departing")
    assert len(portrait.lines) > 1


def test_airline_only_route_letters_the_airline():
    lines, is_airline = compose.lettering_split(AIRLINE_ONLY, "departing", split.LANDSCAPE)
    assert is_airline and lines.lines == ("AIR FRANCE",)
    for layout_id in LAYOUTS:
        assert _render(layout_id, route=AIRLINE_ONLY).tobytes() != _render(layout_id, route=None).tobytes()


def test_unknown_flight_wording_when_nothing_is_known():
    lines, is_airline = compose.lettering_split({}, "departing", split.LANDSCAPE)
    assert not is_airline and lines.lines == ("UNKNOWN FLIGHT",)
    portrait, _ = compose.lettering_split({}, "departing")
    assert "".join(lines.lines).replace(" ", "") == "".join(portrait.lines)


@pytest.mark.parametrize("layout_id", LAYOUTS)
def test_name_of_three_letters_is_one_line(layout_id):
    lines, _ = compose.lettering_split(SHORT, "departing", split.LANDSCAPE)
    assert lines.lines == ("PAU",)
    assert_giant_palette(_render(layout_id, route=SHORT), pf.IDX_BLUE)
    assert _render(layout_id, route=SHORT).tobytes() != _render(layout_id).tobytes()


def _band_ink_share(canvas, ink):
    mask = compose.band_mask(SIZE).crop((400, 344, 800, 356))
    pixels = canvas.crop((400, 344, 800, 356))
    inside = [v for v, m in zip(pixels.tobytes(), mask.tobytes()) if m]
    assert inside
    return sum(1 for v in inside if v == ink) / len(inside)


def test_diagonal_band_is_solid_ink_except_for_the_white_pairing():
    assert _band_ink_share(_render("a_diagonal"), pf.IDX_BLUE) > 0.95
    assert _band_ink_share(_render("a_diagonal", "white"), pf.IDX_BLACK) < 0.5
    assert _render("a_diagonal").tobytes() != _render("a").tobytes()


def test_layout_c_has_no_band_and_the_aircraft_sits_low():
    pairing = PAIRINGS["blue_light"]
    canvas = _render("c")
    top = canvas.crop((0, 0, 14, SIZE[1]))
    assert top.tobytes() == field_pattern(pairing, SIZE).crop((0, 0, 14, SIZE[1])).tobytes()
    plane = canvas.crop((300, 340, 800, 470))
    assert any(v == pf.IDX_WHITE and n > 500 for n, v in plane.getcolors(maxcolors=256))


def test_layout_a_aircraft_enters_from_both_side_edges():
    canvas = _render("a")
    blank = field_pattern(PAIRINGS["blue_light"], SIZE)
    right = (SIZE[0] - 3, 40, SIZE[0], 200)
    left = (0, 300, 3, 460)
    assert canvas.crop(right).tobytes() != blank.crop(right).tobytes()
    assert canvas.crop(left).tobytes() != blank.crop(left).tobytes()


def test_flight_number_changes_the_picture():
    for layout_id in LAYOUTS:
        assert _render(layout_id, route={**ROUTE, "callsign_iata": None}).tobytes() != _render(layout_id).tobytes()


@pytest.mark.parametrize("layout_id", LAYOUTS)
def test_status_marks_change_the_picture(layout_id):
    plain = _render(layout_id)
    for kwargs in ({"battery_low": True}, {"source_fault": True}):
        marked = giant.build_canvas(SIZE, layout_id, FLIGHT, "departing", route=ROUTE,
                                    pairing=PAIRINGS["blue_light"], **kwargs)
        assert marked.tobytes() != plain.tobytes()
        assert_giant_palette(marked, pf.IDX_BLUE)


def test_classic_landscape_profile_is_unchanged():
    classic = layout.build_canvas(FLIGHT, "departing", route=ROUTE, profile=PROFILE)
    assert classic.tobytes() == layout.build_canvas(
        FLIGHT, "departing", route=ROUTE, profile=PROFILE, layout="classic").tobytes()
    assert classic.size == SIZE
