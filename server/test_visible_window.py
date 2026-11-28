# SPDX-License-Identifier: AGPL-3.0-only
"""A profile with a visible window draws inside it; nothing else changes."""
import dataclasses

import pytest
from PIL import Image

from server import hardware, pairing_image, visible_window
from server import panel_format as pf
from server.plane.render import layout

EE04 = hardware.get_profile(hardware.EVALUATION_KEY, {hardware.SECOND_ENV_VAR: "1"})
SIM_LANDSCAPE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
LEGACY = hardware.get_profile(hardware.LEGACY_KEY)
WINDOW = EE04.visible_window
FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
    "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": "AF1380",
}


def _canvas(profile, state="departing", **kwargs):
    flight = FLIGHT if state in ("departing", "arriving") else None
    route = ROUTE if flight else None
    return layout.build_canvas(flight, state, route=route, profile=profile, **kwargs)


def _window_profile():
    return dataclasses.replace(
        EE04, width=WINDOW.width, height=WINDOW.height, visible_window=None)


def _box(window):
    return (window.x, window.y, window.x + window.width, window.y + window.height)


def _unpack(data, width, height):
    nibble_to_index = {v: k for k, v in pf.INDEX_TO_NIBBLE.items()}
    out = bytearray()
    for byte in data:
        out.append(nibble_to_index[byte >> 4])
        out.append(nibble_to_index[byte & 15])
    return Image.frombytes("P", (width, height), bytes(out))


def _edges_repeat(image):
    left, top, right, bottom = _box(WINDOW)
    for y in range(top, bottom):
        edge = image.getpixel((left, y))
        if any(image.getpixel((x, y)) != edge for x in range(0, left)):
            return False
        edge = image.getpixel((right - 1, y))
        if any(image.getpixel((x, y)) != edge for x in range(right, image.width)):
            return False
    for x in range(image.width):
        edge = image.getpixel((x, top))
        if any(image.getpixel((x, y)) != edge for y in range(0, top)):
            return False
        edge = image.getpixel((x, bottom - 1))
        if any(image.getpixel((x, y)) != edge for y in range(bottom, image.height)):
            return False
    return True


def test_only_the_evaluation_profile_has_a_window():
    assert WINDOW is not None
    assert SIM_LANDSCAPE.visible_window is None
    assert LEGACY.visible_window is None
    assert hardware.registry_problems() == []


@pytest.mark.parametrize("window", [
    hardware.VisibleWindow(-1, 0, 700, 400),
    hardware.VisibleWindow(0, 0, 801, 400),
    hardware.VisibleWindow(0, 100, 700, 400),
    hardware.VisibleWindow(0, 0, 0, 400),
])
def test_a_window_outside_the_panel_is_a_registry_problem(window):
    bad = dataclasses.replace(EE04, visible_window=window)
    assert hardware._window_problems(bad)


def test_the_window_of_the_evaluation_profile_is_valid():
    assert hardware._window_problems(EE04) == []


@pytest.mark.parametrize("state", ["departing", "arriving", "empty", "quiet_hours",
                                   "display_off", "battery_empty"])
def test_screens_keep_the_panel_size_and_the_window_holds_the_whole_screen(state):
    framed = _canvas(EE04, state)
    assert framed.size == (EE04.width, EE04.height)
    assert framed.crop(_box(WINDOW)).tobytes() == _canvas(_window_profile(), state).tobytes()


def test_giant_layout_is_framed_too():
    framed = _canvas(EE04, layout="a")
    assert framed.crop(_box(WINDOW)).tobytes() == _canvas(_window_profile(), layout="a").tobytes()


def test_the_hidden_strips_repeat_the_edge_of_the_screen():
    assert _edges_repeat(_canvas(EE04))


def test_a_profile_without_a_window_draws_on_the_whole_panel():
    plain = dataclasses.replace(EE04, visible_window=None)
    assert _canvas(plain).tobytes() == _canvas(SIM_LANDSCAPE).tobytes()
    assert _canvas(plain).tobytes() != _canvas(EE04).tobytes()


def test_pairing_and_retired_screens_are_framed():
    for data in (pairing_image.render_pairing_image(EE04, "ABCD2345"),
                 pairing_image.render_retired_image(EE04)):
        assert len(data) == EE04.firmware.max_image_bytes
        assert _edges_repeat(_unpack(data, EE04.width, EE04.height))


def test_pairing_without_a_window_is_unchanged_and_with_one_differs():
    plain = dataclasses.replace(EE04, visible_window=None)
    assert (pairing_image.render_pairing_image(plain, "ABCD2345")
            == pairing_image.render_pairing_image(SIM_LANDSCAPE, "ABCD2345"))
    assert (pairing_image.render_pairing_image(plain, "ABCD2345")
            != pairing_image.render_pairing_image(EE04, "ABCD2345"))


def test_place_refuses_an_inner_image_of_the_wrong_size():
    with pytest.raises(ValueError):
        visible_window.place(Image.new("P", (10, 10)), (20, 20), hardware.VisibleWindow(2, 2, 8, 8))
