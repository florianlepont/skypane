"""Tests for scripts/multi_site_setup.py: the scratch fleet and its guards.

Every directory is a pytest tmp_path; nothing reads or writes a real state root.
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import multi_site_setup as setup  # noqa: E402
from server import (  # noqa: E402
    detection,
    device_config,
    device_dirs,
    fleet_cycle,
    fleet_db,
    hardware,
    state_store,
)

GEOFENCE = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")


def _create(root, specs):
    return setup.create_scratch_fleet(str(root), [setup.parse_device(s) for s in specs])


def _devices(root):
    conn = fleet_db.connect_readonly(str(root))
    try:
        return fleet_db.list_devices(conn)
    finally:
        conn.close()


def test_creates_one_simulated_device_per_entry_with_its_selection(tmp_path):
    root = tmp_path / "scratch"
    made = _create(root, ["orly-b=LFPO:06/24", "orly-c=LFPO:02/20", "cdg=LFPG:08L/26R"])
    assert (root / setup.MARKER_FILENAME).is_file()
    rows = {row["id"]: row for row in _devices(root)}
    assert len(made) == 3
    for device in made:
        assert os.path.isdir(device.state_dir)
        assert device.state_dir == os.path.join(str(root), "devices", device.id)
        assert rows[device.id]["hardware_type"] == hardware.SIM_CLONE_KEY
        assert rows[device.id]["owner_email"] == setup.OWNER_EMAIL
    by_name = {device.name: device for device in made}
    legacy = device_config.load_device_config(by_name["orly-b"].state_dir)
    assert legacy["tracked_runway"] == "06-24"
    assert legacy.get("detection") is None
    cdg = device_config.load_device_config(by_name["cdg"].state_dir)
    assert cdg["detection"] == {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    assert detection.current_selection(cdg) == {
        "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    assert detection.current_selection(
        device_config.load_device_config(by_name["orly-c"].state_dir)
    ) == {"mode": "runway", "airport": "LFPO", "runway": "02/20"}


def test_refuses_real_looking_roots_and_bad_input(tmp_path, monkeypatch):
    default = tmp_path / "default-state"
    default.mkdir()
    monkeypatch.setattr(state_store, "DEFAULT_STATE_DIR", str(default))
    with pytest.raises(setup.ScratchRootError):
        _create(default, ["a=LFPO:06/24"])
    assert os.listdir(default) == []

    for name in (device_dirs.LIVE_MACS_FILENAME, "panel.bin", fleet_db.FLEET_DB_FILENAME):
        real = tmp_path / ("real-" + name)
        real.mkdir()
        (real / name).write_bytes(b"x")
        with pytest.raises(setup.ScratchRootError):
            _create(real, ["a=LFPO:06/24"])
        assert not (real / setup.MARKER_FILENAME).exists()

    other = tmp_path / "other"
    other.mkdir()
    (other / "something").write_text("x")
    with pytest.raises(setup.ScratchRootError):
        _create(other, ["a=LFPO:06/24"])

    fresh = tmp_path / "fresh"
    with pytest.raises(ValueError):
        _create(fresh, ["a=ZZZZ:06/24"])
    with pytest.raises(ValueError):
        _create(fresh, ["a=LFPO:99/99"])
    with pytest.raises(ValueError):
        setup.parse_device("no-separator")
    with pytest.raises(ValueError):
        setup.create_scratch_fleet(str(fresh), [])
    assert not fresh.exists()


def test_refuses_owner_less_and_non_simulated_hardware(tmp_path):
    specs = [setup.parse_device("a=LFPO:06/24")]
    with pytest.raises(ValueError):
        setup.create_scratch_fleet(str(tmp_path / "r1"), specs, owner_email="")
    with pytest.raises(ValueError):
        setup.create_scratch_fleet(
            str(tmp_path / "r2"), specs, hardware_type=hardware.LEGACY_KEY)
    with pytest.raises(ValueError):
        setup.create_scratch_fleet(
            str(tmp_path / "r3"), specs, hardware_type="not-a-type")
    assert not (tmp_path / "r1").exists()
    assert not (tmp_path / "r2").exists()
    assert not (tmp_path / "r3").exists()


def test_live_row_is_held_and_zones_follow_airports(tmp_path):
    root = tmp_path / "scratch"
    made = _create(root, [
        "orly-b=LFPO:06/24", "orly-c=LFPO:02/20", "cdg=LFPG:08L/26R", "be=LFBE:09/27"])
    devices = fleet_cycle.load_fleet(str(root))
    live = [d for d in devices if d.is_live]
    assert len(live) == 1 and live[0].state_dir == str(root)
    plan = fleet_cycle.plan_zones(devices, fleet_cycle.detection_resolver(GEOFENCE))
    assert live[0] in plan.held
    assert plan.unzoned == []
    zoned = {
        key: sorted(d.id for d in group.devices) for key, group in plan.zones.items()}
    assert len(zoned) == 3
    ids = {d.name: d.id for d in made}
    assert sorted([ids["orly-b"], ids["orly-c"]]) in zoned.values()
    assert [ids["cdg"]] in zoned.values()
    assert [ids["be"]] in zoned.values()


def test_nothing_outside_the_root_is_written(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    before = sorted(os.listdir(parent))
    _create(parent / "scratch", ["a=LFPO:06/24", "b=LFPG:08L/26R"])
    assert sorted(os.listdir(parent)) == before + ["scratch"]
    assert sorted(os.listdir(tmp_path)) == ["parent"]


def test_simulation_flag_is_not_left_in_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    _create(tmp_path / "scratch", ["a=LFPO:06/24"])
    assert hardware.SIM_ENV_VAR not in os.environ
