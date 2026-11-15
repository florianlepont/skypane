"""The overhead look (`theme_overhead`): stored only when set, follows the
departures look when unset, and colours the overhead state alone."""
import json

import pytest

from server import device_config as dc
from server.plane import colour_rules


def _read(state_dir):
    with open(dc.device_config_path(state_dir)) as fh:
        return fh.read()


def test_missing_key_loads_as_following_departures(tmp_path):
    assert dc.load_device_config(str(tmp_path))["theme_overhead"] is None


@pytest.mark.parametrize("stored", ["nope", 5, ["blue"], True, ""])
def test_unknown_stored_value_normalises_to_none(tmp_path, stored):
    with open(dc.device_config_path(str(tmp_path)), "w") as fh:
        json.dump({"theme_overhead": stored}, fh)
    assert dc.load_device_config(str(tmp_path))["theme_overhead"] is None


def test_a_frame_that_never_chose_an_overhead_look_keeps_its_file_bytes(tmp_path):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, theme=dc.DEFAULT_THEME_ID)
    before = _read(state_dir)
    assert "theme_overhead" not in before
    dc.save_device_config(state_dir, theme_overhead=dc.CLEAR_THEME_OVERHEAD)
    assert _read(state_dir) == before


def test_round_trip_carry_forward_and_clear(tmp_path):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, theme_overhead="blue")
    assert dc.load_device_config(state_dir)["theme_overhead"] == "blue"
    dc.save_device_config(state_dir, theme="red")
    assert dc.load_device_config(state_dir)["theme_overhead"] == "blue"
    dc.save_device_config(state_dir, theme_overhead=dc.CLEAR_THEME_OVERHEAD)
    assert dc.load_device_config(state_dir)["theme_overhead"] is None
    assert "theme_overhead" not in _read(state_dir)


@pytest.mark.parametrize("bad", ["nope", "", 3])
def test_invalid_value_is_refused_before_any_write(tmp_path, bad):
    state_dir = str(tmp_path)
    dc.save_device_config(state_dir, theme="red")
    before = _read(state_dir)
    with pytest.raises(ValueError):
        dc.save_device_config(state_dir, theme_overhead=bad)
    assert _read(state_dir) == before


def test_overhead_look_colours_only_the_overhead_state():
    cfg = {"theme": "white", "theme_arriving": "red", "theme_overhead": "blue"}
    resolve = colour_rules.resolve_effective_theme_id
    assert resolve("overhead", {}, cfg) == "blue"
    assert resolve("departing", {}, cfg) == "white"
    assert resolve("arriving", {}, cfg) == "red"


def test_unset_overhead_look_follows_departures_not_arrivals():
    cfg = {"theme": "green", "theme_arriving": "red", "theme_overhead": None}
    assert colour_rules.resolve_effective_theme_id("overhead", {}, cfg) == "green"


def test_a_rule_still_beats_the_overhead_look():
    rules = {"callsign": {"AFR1": {"theme_id": "yellow", "created_at": "2026-01-01T00:00:00Z"}},
             "hex": {}, "prefix": {}}
    cfg = {"theme": "white", "theme_overhead": "blue"}
    assert colour_rules.resolve_effective_theme_id(
        "overhead", {"callsign": "AFR1"}, cfg, rules=rules) == "yellow"
