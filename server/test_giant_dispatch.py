"""build_canvas dispatch on the screen layout, and the poll cycle's layout pass."""
import json
import os

import pytest

import server.hardware as hardware
import server.plane.render as render
import server.plane.colour_rules as colour_rules
import server.poll_cycle as poll_cycle
from server import device_config, panel_format as pf, screen_layouts
from server.pairings import pairing_for_theme
from server.plane.render import layout
from server.plane.render.giant.field import ink_index
from server.plane.render.giant.palette_check import assert_giant_palette

HERE = os.path.dirname(os.path.abspath(__file__))
GEOFENCE_PATH = os.path.join(os.path.dirname(HERE), "adsb-test", "runway3.json")
FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
PREVIOUS = {"hex": "bbbbbb", "callsign": "TO1234", "aircraft_type": "A320"}
ROUTE = {
    "airline_name": "Air France", "origin_iata": "ORY", "origin_city": "Paris",
    "destination_iata": "JFK", "destination_city": "New York", "callsign_iata": "AF1380",
}
LANDSCAPE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
LEGACY = hardware.get_profile(hardware.LEGACY_KEY)


def _canvas(state="departing", **kwargs):
    return layout.build_canvas(FLIGHT, state, route=ROUTE, **kwargs)


def test_none_and_classic_equal_the_legacy_bytes():
    legacy = _canvas().tobytes()
    assert _canvas(layout=None).tobytes() == legacy
    assert _canvas(layout="classic").tobytes() == legacy


@pytest.mark.parametrize("layout_id", ["a", "b", "a_diagonal"])
def test_giant_layout_differs_and_has_portrait_size(layout_id):
    canvas = _canvas(layout=layout_id)
    assert canvas.size == (pf.WIDTH, pf.HEIGHT)
    assert canvas.tobytes() != _canvas().tobytes()


def test_unknown_layout_id_falls_back_to_the_default_layout():
    expected = _canvas(layout=screen_layouts.DEFAULT_LAYOUT_ID).tobytes()
    assert _canvas(layout="../../etc/passwd").tobytes() == expected
    assert _canvas(layout=42).tobytes() == expected


def test_previous_flight_does_not_change_a_giant_layout():
    plain = _canvas(layout="b")
    with_previous = _canvas(layout="b", previous_flight=PREVIOUS, previous_route=ROUTE,
                            previous_state="departing")
    assert plain.tobytes() == with_previous.tobytes()


@pytest.mark.parametrize("state", ["empty", "quiet_hours", "display_off", "battery_empty"])
def test_hold_screens_follow_the_layout_family(state):
    classic = layout.build_canvas(None, state, quiet_hours_until="07:00")
    assert layout.build_canvas(None, state, quiet_hours_until="07:00", layout="classic").tobytes() == classic.tobytes()
    giant = layout.build_canvas(None, state, quiet_hours_until="07:00", layout="b")
    assert giant.tobytes() != classic.tobytes()
    for layout_id in ("a", "c", "a_diagonal"):
        assert layout.build_canvas(None, state, quiet_hours_until="07:00", layout=layout_id).tobytes() == giant.tobytes()


def test_portrait_profile_matches_no_profile_for_a_giant_layout():
    assert _canvas(layout="b", profile=LEGACY).tobytes() == _canvas(layout="b").tobytes()


def test_giant_layout_on_a_landscape_profile_renders_natively():
    classic = _canvas(profile=LANDSCAPE)
    assert classic.size == (800, 480)
    giant = _canvas(profile=LANDSCAPE, layout="b")
    assert giant.size == (800, 480)
    assert giant.tobytes() != classic.tobytes()
    assert _canvas(profile=LANDSCAPE, layout="classic").tobytes() == classic.tobytes()


def _field_index(canvas):
    return max(canvas.getcolors(256))[1]


def test_arriving_colour_differs_from_the_departing_one(tmp_path):
    cfg = dict(device_config.load_device_config(str(tmp_path)), theme="blue_light", theme_arriving="red_light")
    departing = colour_rules.resolve_effective_theme_id("departing", FLIGHT, cfg)
    arriving = colour_rules.resolve_effective_theme_id("arriving", FLIGHT, cfg)
    assert (departing, arriving) == ("blue_light", "red_light")
    assert _field_index(_canvas(layout="b", theme_id=departing)) == pf.IDX_BLUE
    assert _field_index(_canvas("arriving", layout="b", theme_id=arriving)) == pf.IDX_RED


@pytest.mark.parametrize("theme_id", ["red_light", "yellow_light", "band_green_light", "band_blue", "white", "black"])
def test_stored_theme_resolves_to_its_pairing(theme_id):
    pairing = pairing_for_theme(theme_id)
    canvas = _canvas(layout="b", theme_id=theme_id)
    assert_giant_palette(canvas, ink_index(pairing.field_ink))
    assert canvas.tobytes() == _canvas(layout="b", theme_id=pairing.id).tobytes()


def test_a_per_airline_rule_theme_reaches_the_giant_canvas(tmp_path):
    rules = {kind: {} for kind in colour_rules.RULE_KINDS}
    rules[colour_rules.RULE_KIND_PREFIX] = {"AFR": {"theme_id": "red_light"}}
    flight = dict(FLIGHT, callsign="AFR1380")
    theme_id = colour_rules.resolve_effective_theme_id(
        "departing", flight, device_config.load_device_config(str(tmp_path)), rules=rules)
    assert theme_id == "red_light"
    assert _field_index(_canvas(layout="b", theme_id=theme_id)) == pf.IDX_RED


def test_a_calendar_theme_reaches_the_giant_canvas(tmp_path):
    theme_id = colour_rules.resolve_effective_theme_id(
        "departing", FLIGHT, device_config.load_device_config(str(tmp_path)),
        calendar_theme_id="band_blue")
    assert theme_id == "band_blue"
    canvas = _canvas(layout="b", theme_id=theme_id)
    assert_giant_palette(canvas, pf.IDX_BLUE)


def _fixture():
    with open(os.path.join(HERE, "fixtures", "geofence_multi_aircraft.json")) as fh:
        return json.load(fh)


@pytest.fixture
def spy(monkeypatch):
    calls = []
    original = render.build_canvas

    def _spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(poll_cycle.render, "build_canvas", _spy)
    return calls


def _run(state_dir, layout_id=None):
    if layout_id is not None:
        device_config.save_device_config(state_dir, layout=layout_id)
    return poll_cycle.run_once(snapshot=_fixture(), state_dir=state_dir, geofence=GEOFENCE_PATH)


@pytest.mark.parametrize("layout_id", ["classic", "a", "a_diagonal"])
def test_poll_cycle_passes_the_stored_layout(tmp_path, spy, layout_id):
    _run(str(tmp_path), layout_id)
    assert spy and all(call["layout"] == layout_id for call in spy)


def test_poll_cycle_without_a_stored_layout_passes_the_default(tmp_path, spy):
    _run(str(tmp_path))
    assert spy and all(call["layout"] == screen_layouts.DEFAULT_LAYOUT_ID for call in spy)


def test_every_poll_cycle_render_call_passes_a_layout(tmp_path, spy):
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, display_enabled=False)
    _run(state_dir)
    _run(str(tmp_path / "second"))
    assert spy and all("layout" in call for call in spy)
