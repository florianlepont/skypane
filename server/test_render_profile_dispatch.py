"""build_canvas dispatches on the hardware profile; None stays the legacy path."""
import dataclasses

import pytest

from server import hardware
from server import panel_format as pf
from server.plane.render import layout

LEGACY = hardware.get_profile(hardware.LEGACY_KEY)
SIM_ENV = {hardware.SIM_ENV_VAR: "1"}
LANDSCAPE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, SIM_ENV)

FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
    "callsign_iata": "AF1380",
}
BLACK_WHITE = frozenset({pf.IDX_BLACK, pf.IDX_WHITE})


def _bytes(profile, state="departing", **kwargs):
    flight = FLIGHT if state in ("departing", "arriving") else None
    route = ROUTE if flight else None
    canvas = layout.build_canvas(flight, state, route=route, profile=profile, **kwargs)
    return canvas.size, pf.pack_panel(canvas)


@pytest.mark.parametrize("state", ["departing", "arriving", "empty", "battery_empty"])
def test_portrait_profile_matches_legacy(state):
    assert _bytes(LEGACY, state) == _bytes(None, state)


def test_landscape_profile_renders_native_size():
    size, data = _bytes(LANDSCAPE)
    assert size == (800, 480)
    assert len(data) == LANDSCAPE.firmware.max_image_bytes == 192000


@pytest.mark.parametrize("state", ["empty", "quiet_hours", "display_off", "battery_empty"])
def test_landscape_hold_states(state):
    size, data = _bytes(LANDSCAPE, state)
    assert size == (800, 480)
    assert len(data) == 192000


def test_unavailable_theme_renders_as_default_without_mutation():
    reduced = dataclasses.replace(LEGACY, inks=BLACK_WHITE)
    theme = "band_red"
    assert _bytes(reduced, theme_id=theme) == _bytes(reduced, theme_id="white")
    assert _bytes(reduced, theme_id=theme) != _bytes(LEGACY, theme_id=theme)


def test_unavailable_theme_falls_back_on_landscape_too():
    reduced = dataclasses.replace(LANDSCAPE, inks=BLACK_WHITE)
    assert _bytes(reduced, theme_id="yellow") == _bytes(reduced, theme_id="white")


def test_mixed_order_matches_separate_renders():
    first = (_bytes(LANDSCAPE), _bytes(None))
    second = (_bytes(None), _bytes(LANDSCAPE))
    assert first == (second[1], second[0])
    assert _bytes(LANDSCAPE) == first[0]
    assert _bytes(None) == first[1]
