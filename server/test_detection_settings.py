#!/usr/bin/env python3
"""Selection validation, the legacy/catalogue storage split and the
read-back record the settings page shows."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.detection as detection  # noqa: E402
import server.device_config as device_config  # noqa: E402


def _bytes(state_dir):
    with open(device_config.device_config_path(str(state_dir)), "rb") as fh:
        return fh.read()


def _doc(state_dir):
    return json.loads(_bytes(state_dir))


def test_validate_runway_accepts_a_catalogue_pair():
    assert detection.validate_runway_selection("LFPG", "08L/26R") == ("LFPG", "08L/26R")


@pytest.mark.parametrize("icao, designator, code", [
    ("ZZZZ", "08L/26R", "airport"),
    ("lfpg", "08L/26R", "airport"),
    (None, "08L/26R", "airport"),
    ("LFPG", "99/17", "runway"),
    ("LFPG", "26R/08L", "runway"),
    ("LFPG", "07/25", "runway"),
    ("LFPG", None, "runway"),
])
def test_validate_runway_rejects_with_a_stable_code(icao, designator, code):
    with pytest.raises(ValueError) as exc:
        detection.validate_runway_selection(icao, designator)
    assert exc.value.args[0] == code


@pytest.mark.parametrize("value", [4, 17, 28])
def test_validate_radius_accepts_bounds(value):
    assert detection.validate_radius_km(value) == value


@pytest.mark.parametrize("value", [3, 29, True, 9.0, "9", None])
def test_validate_radius_rejects(value):
    with pytest.raises(ValueError) as exc:
        detection.validate_radius_km(value)
    assert exc.value.args[0] == "radius"


@pytest.mark.parametrize("designator, legacy", [("07/25", "3"), ("06/24", "06-24"), ("02/20", "02-20")])
def test_apply_legacy_orly_runways_store_the_legacy_id(tmp_path, designator, legacy):
    sd = str(tmp_path)
    detection.apply_runway_selection(sd, "LFPO", designator)
    assert _doc(sd)["tracked_runway"] == legacy
    assert "detection" not in _doc(sd)


def test_apply_legacy_keeps_bytes_identical_for_an_unchanged_setting(tmp_path):
    sd = str(tmp_path)
    device_config.save_device_config(sd, theme="black")
    before = _bytes(sd)
    detection.apply_runway_selection(sd, "LFPO", "07/25")
    assert _bytes(sd) == before


def test_apply_legacy_clears_a_previous_detection_object(tmp_path):
    sd = str(tmp_path)
    detection.apply_runway_selection(sd, "LFPG", "08L/26R")
    detection.apply_runway_selection(sd, "LFPO", "06/24")
    assert "detection" not in _doc(sd)
    assert _doc(sd)["tracked_runway"] == "06-24"


def test_apply_catalogue_stores_one_object_and_leaves_tracked_runway(tmp_path):
    sd = str(tmp_path)
    device_config.save_device_config(sd, tracked_runway="02-20")
    detection.apply_runway_selection(sd, "LFPG", "08L/26R")
    doc = _doc(sd)
    assert doc["detection"] == {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    assert doc["tracked_runway"] == "02-20"


def test_apply_position_stores_radius_only(tmp_path):
    sd = str(tmp_path)
    detection.apply_position_selection(sd, 9)
    assert _doc(sd)["detection"] == {"mode": "position", "radius_km": 9}


def test_current_selection_defaults_and_legacy_mapping():
    assert detection.current_selection({"tracked_runway": "06-24"}) == {
        "mode": "runway", "airport": "LFPO", "runway": "06/24"}
    assert detection.current_selection({}) == {"mode": "runway", "airport": "LFPO", "runway": "07/25"}


def test_current_selection_reports_catalogue_and_position(tmp_path):
    cfg = {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}}
    assert detection.current_selection(cfg) == cfg["detection"]
    assert detection.current_selection({"detection": {"mode": "position", "radius_km": 9}}) == {
        "mode": "position", "radius_km": 9}


@pytest.mark.parametrize("cfg", [
    None, 5, {"detection": 5}, {"detection": {"mode": "runway", "airport": "ZZZZ", "runway": "08L/26R"}},
    {"detection": {"mode": "position", "radius_km": 99}}, {"tracked_runway": "bogus"},
])
def test_current_selection_malformed_reads_as_the_legacy_default(cfg):
    assert detection.current_selection(cfg) == {"mode": "runway", "airport": "LFPO", "runway": "07/25"}


@pytest.mark.parametrize("call", [
    lambda sd: detection.apply_runway_selection(sd, "ZZZZ", "08L/26R"),
    lambda sd: detection.apply_runway_selection(sd, "LFPG", "26R/08L"),
    lambda sd: detection.apply_position_selection(sd, 3),
    lambda sd: detection.apply_position_selection(sd, True),
])
def test_all_or_nothing_on_invalid_input(tmp_path, call):
    sd = str(tmp_path)
    device_config.save_device_config(sd, theme="black", detection={"mode": "position", "radius_km": 5})
    before = _bytes(sd)
    with pytest.raises(ValueError):
        call(sd)
    assert _bytes(sd) == before


def test_all_or_nothing_creates_no_file_when_none_existed(tmp_path):
    sd = str(tmp_path / "fresh")
    with pytest.raises(ValueError):
        detection.apply_runway_selection(sd, "ZZZZ", "08L/26R")
    assert not os.path.exists(device_config.device_config_path(sd))


def test_stored_catalogue_selection_resolves_through_spec_for(tmp_path):
    sd = str(tmp_path)
    detection.apply_runway_selection(sd, "LFPG", "08L/26R")
    spec = detection.spec_for(device_config.load_device_config(sd))
    assert spec.display_id == detection.runway_display_id("LFPG", "08L/26R")
