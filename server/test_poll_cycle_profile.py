"""run_once with a hardware profile: native rendering and profile thresholds.

The profile=None path is the legacy live frame; the golden and end-to-end
tests pin its bytes. These tests cover the profile seam only.
"""
import dataclasses
import json
import os

import server.device_config as device_config
import server.hardware as hardware
import server.poll_cycle as poll_cycle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
LEGACY = hardware.get_profile(hardware.LEGACY_KEY)
LANDSCAPE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
LANDSCAPE_BYTES = 192000
PORTRAIT_BYTES = 960000


def _fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as fh:
        return json.load(fh)


def _panel(state_dir):
    with open(os.path.join(state_dir, "panel.bin"), "rb") as fh:
        return fh.read()


def _write_battery(state_dir, mv):
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": mv}, fh)


def _with_thresholds(**battery_fields):
    return dataclasses.replace(LEGACY, battery=dataclasses.replace(LEGACY.battery, **battery_fields))


def _run(state_dir, profile=None, snapshot=None):
    snapshot = _fixture("geofence_multi_aircraft.json") if snapshot is None else snapshot
    return poll_cycle.run_once(
        snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH, profile=profile)


def test_none_and_legacy_profile_write_identical_panels(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    res_a = _run(a)
    res_b = _run(b, LEGACY)
    assert _panel(a) == _panel(b)
    assert len(_panel(a)) == PORTRAIT_BYTES
    assert res_a == res_b


def test_landscape_profile_writes_native_panel(tmp_path):
    portrait, landscape = str(tmp_path / "p"), str(tmp_path / "l")
    res_p = _run(portrait)
    res_l = _run(landscape, LANDSCAPE)
    assert len(_panel(landscape)) == LANDSCAPE_BYTES
    assert res_l.keys() == res_p.keys()
    assert res_l["state"] == res_p["state"]


def test_landscape_empty_and_hold_states(tmp_path):
    empty_dir, hold_dir = str(tmp_path / "e"), str(tmp_path / "h")
    _run(empty_dir, LANDSCAPE, snapshot=_fixture("geofence_empty.json"))
    assert len(_panel(empty_dir)) == LANDSCAPE_BYTES
    os.makedirs(hold_dir)
    device_config.save_device_config(hold_dir, display_enabled=False)
    result = _run(hold_dir, LANDSCAPE)
    assert result["state"] == "display_off"
    assert len(_panel(hold_dir)) == LANDSCAPE_BYTES


def test_profile_low_threshold_decides_battery_low(tmp_path):
    legacy_dir, profile_dir = str(tmp_path / "l"), str(tmp_path / "p")
    for directory in (legacy_dir, profile_dir):
        os.makedirs(directory)
        _write_battery(directory, 3700)
    _run(legacy_dir)
    _run(profile_dir, _with_thresholds(low_mv=3800, low_clear_mv=3900))
    with open(os.path.join(legacy_dir, "poll_state.json")) as fh:
        assert json.load(fh)["battery_low_active"] is False
    with open(os.path.join(profile_dir, "poll_state.json")) as fh:
        assert json.load(fh)["battery_low_active"] is True


def test_profile_critical_threshold_latches_battery_empty(tmp_path):
    legacy_dir, profile_dir = str(tmp_path / "l"), str(tmp_path / "p")
    for directory in (legacy_dir, profile_dir):
        os.makedirs(directory)
        _write_battery(directory, 3700)
    legacy = _run(legacy_dir)
    profiled = _run(profile_dir, _with_thresholds(critical_mv=3750, critical_recover_mv=3800))
    assert legacy["state"] != "battery_empty"
    assert profiled["state"] == "battery_empty"
    with open(os.path.join(profile_dir, "poll_state.json")) as fh:
        assert json.load(fh)["battery_critical_active"] is True


def test_theme_fallback_does_not_rewrite_stored_theme(tmp_path):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    device_config.save_device_config(state_dir, theme="band_blue")
    narrow = dataclasses.replace(LANDSCAPE, inks=frozenset({hardware.panel_format.IDX_BLACK, hardware.panel_format.IDX_WHITE}))
    result = _run(state_dir, narrow)
    assert result["theme"] == "band_blue"
    assert device_config.load_device_config(state_dir)["theme"] == "band_blue"
