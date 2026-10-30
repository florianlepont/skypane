"""Fleet enumeration, activity and hold gating, and zone grouping."""
import json
import os
import sqlite3

import pytest
import skypane_two_device_fleet as two_fleet

from server import device_dirs, fleet_cycle, fleet_db, fleet_zones, hardware

NOW = 2_000_000_000.0


@pytest.fixture
def fleet(tmp_path):
    state_dir = str(tmp_path)
    with two_fleet.sim_hardware_env():
        seeded = two_fleet.seed_two_device_fleet(state_dir)
        yield seeded


def _env():
    return {hardware.SIM_ENV_VAR: "1"}


def _set_row(state_dir, device_id, **columns):
    conn = fleet_db.connect(state_dir)
    try:
        for column, value in columns.items():
            conn.execute("UPDATE devices SET %s = ? WHERE id = ?" % column, (value, device_id))
    finally:
        conn.close()


def _write_battery(state_dir, received_at):
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"received_at": received_at, "battery_mv": 3900}, fh)


def test_no_fleet_db_is_the_live_frame_alone(tmp_path):
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert len(devices) == 1
    assert devices[0].is_live
    assert devices[0].state_dir == str(tmp_path)


def test_rows_map_to_resolved_directories_live_first(fleet, tmp_path):
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert [d.is_live for d in devices] == [True, False, False]
    assert devices[0].state_dir == str(tmp_path)
    assert {d.state_dir for d in devices[1:]} == {fleet.dev_a.state_dir, fleet.dev_b.state_dir}
    assert {d.id for d in devices[1:]} == {fleet.dev_a.id, fleet.dev_b.id}


def test_bad_state_path_rows_are_skipped_others_unaffected(fleet, tmp_path):
    _set_row(str(tmp_path), fleet.dev_a.id, state_path="devices/../x")
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert [d.id for d in devices if not d.is_live] == [fleet.dev_b.id]


def test_symlinked_device_directory_is_skipped(fleet, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.rename(fleet.dev_a.state_dir, str(tmp_path / "moved"))
    os.symlink(str(elsewhere), fleet.dev_a.state_dir)
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert [d.id for d in devices if not d.is_live] == [fleet.dev_b.id]


def test_missing_device_directory_is_skipped(fleet, tmp_path):
    os.rename(fleet.dev_b.state_dir, str(tmp_path / "gone"))
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert [d.id for d in devices if not d.is_live] == [fleet.dev_a.id]


def test_unreadable_fleet_db_falls_back_to_live(tmp_path):
    (tmp_path / "fleet.db").write_bytes(b"not a database")
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert [d.is_live for d in devices] == [True]


def test_unknown_or_unrenderable_hardware_is_skipped(fleet, tmp_path):
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    keep, skipped = fleet_cycle.runnable_devices(devices, NOW, {})
    assert [d.is_live for d in keep] == [True]
    assert {reason for _, reason in skipped} == {"unsupported_hardware"}


def test_landscape_hardware_is_skipped(tmp_path):
    with two_fleet.sim_hardware_env():
        seeded = two_fleet.seed_two_device_fleet(str(tmp_path), with_landscape=True)
        devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
        keep, skipped = fleet_cycle.runnable_devices(devices, NOW, _env())
    assert seeded.landscape.id in {device_id for device_id, _ in skipped}
    assert seeded.landscape.id not in {d.id for d in keep}


def test_fresh_device_without_check_in_is_kept(fleet, tmp_path):
    created = "2033-05-17T00:00:00+00:00"
    _set_row(str(tmp_path), fleet.dev_a.id, created_at=created)
    now = fleet_cycle._created_epoch(created) + 86400
    devices = fleet_cycle.load_fleet(str(tmp_path), now)
    keep, _ = fleet_cycle.runnable_devices(devices, now, _env())
    assert fleet.dev_a.id in {d.id for d in keep}


def test_old_device_without_check_in_is_inactive_but_live_stays(fleet, tmp_path):
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    later = max(d.created_epoch or 0 for d in devices) + 30 * 86400
    keep, skipped = fleet_cycle.runnable_devices(devices, later, _env())
    assert [d.is_live for d in keep] == [True]
    assert {reason for _, reason in skipped} == {"inactive"}


def test_recent_check_in_keeps_an_old_device(fleet, tmp_path):
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    later = max(d.created_epoch or 0 for d in devices) + 30 * 86400
    _write_battery(fleet.dev_a.state_dir, later - 3600)
    keep, skipped = fleet_cycle.runnable_devices(devices, later, _env())
    assert fleet.dev_a.id in {d.id for d in keep}
    assert fleet.dev_b.id in {device_id for device_id, _ in skipped}


def test_last_check_in_is_tolerant_of_garbage(tmp_path):
    (tmp_path / "battery_state.json").write_text("{not json")
    assert fleet_cycle.last_check_in_epoch(str(tmp_path)) is None
    (tmp_path / "battery_state.json").write_text(json.dumps({"received_at": True}))
    assert fleet_cycle.last_check_in_epoch(str(tmp_path)) is None


def _zone(lat):
    return fleet_zones.Zone(lat, 2.0, 25.0), {"center": {"lat": lat, "lon": 2.0}}


def _devices(count):
    return [fleet_cycle.FleetDevice("d%d" % i, "/x/%d" % i, i == 0, hardware.LEGACY_KEY, None)
            for i in range(count)]


def test_plan_zones_groups_by_exact_zone_and_separates_held():
    devices = _devices(4)
    zones = {"d0": 48.0, "d1": 48.0, "d2": 49.0, "d3": 48.0}
    holds = {"3": "display_off"}
    plan = fleet_cycle.plan_zones(
        devices, lambda d: _zone(zones[d.id]), hold_of=lambda path: holds.get(path.split("/")[-1]))
    assert sorted(len(g.devices) for g in plan.zones.values()) == [1, 2]
    assert [d.id for d in plan.held] == ["d3"]


def test_zone_of_only_held_devices_produces_no_group():
    devices = _devices(2)
    plan = fleet_cycle.plan_zones(
        devices, lambda d: _zone(48.0), hold_of=lambda path: "quiet_hours")
    assert plan.zones == {}
    assert len(plan.held) == 2


def test_resolver_failure_marks_the_device_unzoned():
    def resolver(device):
        if device.id == "d1":
            raise ValueError("bad")
        return _zone(48.0)

    plan = fleet_cycle.plan_zones(_devices(2), resolver, hold_of=lambda path: None)
    assert [d.id for d in plan.unzoned] == ["d1"]
    assert len(plan.zones) == 1


def test_default_resolver_gives_every_device_the_geofence_zone():
    geofence = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adsb-test", "runway3.json")
    resolver = fleet_cycle.geofence_resolver(geofence)
    devices = _devices(3)
    results = [resolver(d) for d in devices]
    assert len({zone.key for zone, _ in results}) == 1
    assert "center" in results[0][1]


def test_default_resolver_with_missing_geofence_raises_oserror(tmp_path):
    resolver = fleet_cycle.geofence_resolver(str(tmp_path / "nope.json"))
    with pytest.raises(OSError):
        resolver(_devices(1)[0])


def test_state_dirs_never_come_from_unvalidated_paths(fleet, tmp_path):
    conn = sqlite3.connect(str(tmp_path / "fleet.db"))
    conn.execute("UPDATE devices SET state_path = ? WHERE id = ?", ("/etc", fleet.dev_a.id))
    conn.commit()
    conn.close()
    devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
    assert fleet.dev_a.id not in {d.id for d in devices}
    assert device_dirs.valid_state_path("/etc") is False
