"""companion/device_scope.py: device lookup, per-device poll locks, request
scope helpers, poll capability and offline status. Real fleet.db and state
directories seeded through the shared two-device fixture.
"""
import json
import os
import threading

import pytest

from skypane_two_device_fleet import seed_two_device_fleet, sim_hardware_env

from companion import device_scope, routes
from server import device_dirs, fleet_db, hardware, history_db


@pytest.fixture
def fleet(tmp_path):
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)
    with sim_hardware_env():
        seeded = seed_two_device_fleet(state_dir, with_landscape=True)
    return state_dir, seeded


@pytest.fixture(autouse=True)
def _reset_scope():
    device_scope.set_request_scope(None, ())
    yield
    device_scope.set_request_scope(None, ())


def _set_state_path(state_dir, device_id, state_path):
    conn = fleet_db.connect(state_dir)
    try:
        conn.execute("UPDATE devices SET state_path = ? WHERE id = ?", (state_path, device_id))
    finally:
        conn.close()


class TestLookup:
    def test_find_known_device(self, fleet):
        state_dir, seeded = fleet
        device = device_scope.find_device(state_dir, seeded.dev_a.id)
        assert device is not None
        assert device.id == seeded.dev_a.id
        assert device.state_path == "devices/" + seeded.dev_a.id
        assert device.state_dir == seeded.dev_a.state_dir
        assert not device.is_live

    def test_unknown_and_malformed_ids_return_none(self, fleet):
        state_dir, _ = fleet
        assert device_scope.find_device(state_dir, "d_00000000") is None
        for bad in ("", "d_1a2b3c4", "D_1A2B3C4D", "../etc", "d_1a2b3c4d\n", None):
            assert device_scope.find_device(state_dir, bad) is None

    def test_tampered_state_path_returns_none(self, fleet):
        state_dir, seeded = fleet
        _set_state_path(state_dir, seeded.dev_a.id, "../../etc")
        assert device_scope.find_device(state_dir, seeded.dev_a.id) is None
        assert seeded.dev_a.id not in [d.id for d in device_scope.load_devices(state_dir)]

    def test_live_row_is_returned_as_live(self, fleet):
        state_dir, seeded = fleet
        device = device_scope.find_device(state_dir, seeded.live.id)
        assert device is not None and device.is_live
        assert device.state_dir == state_dir

    def test_device_has_no_secret_fields(self):
        for field in device_scope.Device._fields:
            assert field not in ("mac", "token", "secret")

    def test_load_devices_orders_live_first_then_name_then_id(self, fleet):
        state_dir, seeded = fleet
        devices = device_scope.load_devices(state_dir)
        assert devices[0].is_live
        assert devices[0].id == seeded.live.id
        rest = devices[1:]
        assert [d.name for d in rest] == sorted(d.name for d in rest)
        assert {d.id for d in rest} == {seeded.dev_a.id, seeded.dev_b.id, seeded.landscape.id}

    def test_nameless_live_row_gets_the_default_name(self, fleet):
        state_dir, seeded = fleet
        conn = fleet_db.connect(state_dir)
        try:
            conn.execute("UPDATE devices SET name = NULL WHERE id = ?", (seeded.live.id,))
        finally:
            conn.close()
        assert device_scope.live_device(state_dir).name == "Orly frame"

    def test_nameless_non_live_device_is_named_by_its_id(self, fleet):
        state_dir, seeded = fleet
        conn = fleet_db.connect(state_dir)
        try:
            conn.execute("UPDATE devices SET name = NULL WHERE id = ?", (seeded.dev_a.id,))
        finally:
            conn.close()
        assert device_scope.find_device(state_dir, seeded.dev_a.id).name == seeded.dev_a.id

    def test_absent_fleet_db_yields_only_the_live_device(self, tmp_path):
        state_dir = str(tmp_path)
        devices = device_scope.load_devices(state_dir)
        assert len(devices) == 1 and devices[0].is_live
        assert devices[0].state_dir == state_dir

    def test_unreadable_fleet_db_yields_only_the_live_device(self, tmp_path):
        with open(os.path.join(str(tmp_path), "fleet.db"), "wb") as fh:
            fh.write(b"not a sqlite database" * 20)
        devices = device_scope.load_devices(str(tmp_path))
        assert len(devices) == 1 and devices[0].is_live


class TestPollLocks:
    def test_same_dir_same_lock_other_dir_other_lock(self, tmp_path):
        a, b = str(tmp_path / "a"), str(tmp_path / "b")
        assert device_scope.poll_lock_for(a) is device_scope.poll_lock_for(a)
        assert device_scope.poll_lock_for(a) is not device_scope.poll_lock_for(b)

    def test_key_is_realpathed(self, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        link = tmp_path / "link"
        os.symlink(str(real), str(link))
        assert device_scope.poll_lock_for(str(real)) is device_scope.poll_lock_for(str(link))

    def test_holding_one_does_not_block_another(self, tmp_path):
        lock_a = device_scope.poll_lock_for(str(tmp_path / "a"))
        lock_b = device_scope.poll_lock_for(str(tmp_path / "b"))
        assert lock_a.acquire(blocking=False)
        try:
            result = []
            thread = threading.Thread(
                target=lambda: result.append(
                    (lock_a.acquire(blocking=False), lock_b.acquire(blocking=False))))
            thread.start()
            thread.join(5)
            assert result == [(False, True)]
        finally:
            lock_a.release()
            lock_b.release()


class TestPathHelpers:
    def test_strip_prefix(self):
        assert device_scope.strip_prefix("/devices/d_1a2b3c4d/health") == "/health"
        assert device_scope.strip_prefix("/devices/d_1a2b3c4d") == "/"
        assert device_scope.strip_prefix("/devices/x/health") == "/devices/x/health"
        assert device_scope.strip_prefix("/health") == "/health"

    def test_target_path(self, fleet):
        state_dir, seeded = fleet
        other = device_scope.find_device(state_dir, seeded.dev_b.id)
        live = device_scope.live_device(state_dir)
        assert device_scope.target_path("/health", other) == "/devices/%s/health" % other.id
        assert device_scope.target_path(
            "/devices/d_1a2b3c4d/health", other) == "/devices/%s/health" % other.id
        assert device_scope.target_path("/devices/d_1a2b3c4d/health", live) == "/health"

    def test_scoped_without_scope_is_identity(self):
        assert device_scope.scoped("/health") == "/health"
        assert device_scope.current_prefix() == ""

    def test_scoped_for_live_frame_is_identity(self, fleet):
        state_dir, _ = fleet
        live = device_scope.live_device(state_dir)
        device_scope.set_request_scope(live, [live])
        assert device_scope.scoped("/health") == "/health"

    def test_scoped_with_a_device(self, fleet):
        state_dir, seeded = fleet
        dev = device_scope.find_device(state_dir, seeded.dev_a.id)
        device_scope.set_request_scope(dev, device_scope.load_devices(state_dir))
        prefix = "/devices/" + dev.id
        assert device_scope.current_prefix() == prefix
        assert device_scope.current_device() == dev
        assert len(device_scope.current_devices()) == 4
        assert device_scope.scoped("/health") == prefix + "/health"
        assert device_scope.scoped("/health?x=1#top") == prefix + "/health?x=1#top"
        assert device_scope.scoped("/quick/led", method="POST") == prefix + "/quick/led"
        assert device_scope.scoped("/quick/led") == "/quick/led"
        for global_path in ("/update", "/login", "/static/style.css", "/ui-lang"):
            assert device_scope.scoped(global_path) == global_path
        assert routes.match("GET", device_scope.scoped("/health"), "") is not None


class TestDeviceStatus:
    NOW = 1_800_000_000.0

    def _device(self, fleet):
        state_dir, seeded = fleet
        return device_scope.find_device(state_dir, seeded.dev_a.id)

    def _write_battery(self, device, received_at):
        with open(os.path.join(device.state_dir, "battery_state.json"), "w") as fh:
            json.dump({"battery_mv": 3900, "received_at": received_at}, fh)

    def test_live_frame_has_no_status(self, fleet):
        state_dir, _ = fleet
        assert device_scope.device_status(device_scope.live_device(state_dir), self.NOW) is None

    def test_never_seen(self, fleet):
        assert device_scope.device_status(self._device(fleet), self.NOW) == "never_seen"

    def test_online_and_offline_from_battery_state(self, fleet):
        device = self._device(fleet)
        self._write_battery(device, self.NOW - 100)
        assert device_scope.device_status(device, self.NOW) == "online"
        # Default wake interval is 3600 s, so offline starts past 7200 s.
        self._write_battery(device, self.NOW - 7300)
        assert device_scope.device_status(device, self.NOW) == "offline"

    def test_threshold_follows_the_devices_own_wake_interval(self, fleet):
        device = self._device(fleet)
        with open(os.path.join(device.state_dir, "device_config.json"), "w") as fh:
            json.dump({"wake_interval_s": 60}, fh)
        self._write_battery(device, self.NOW - 300)
        assert device_scope.device_status(device, self.NOW) == "offline"
        self._write_battery(device, self.NOW - 100)
        assert device_scope.device_status(device, self.NOW) == "online"

    def test_history_db_check_in_is_preferred(self, fleet):
        device = self._device(fleet)
        self._write_battery(device, self.NOW - 100000)
        with history_db.open_db(device.state_dir) as conn:
            history_db.record_device_health(
                conn, "2027-01-15T08:00:00+00:00", battery_mv=3900)
        from datetime import datetime, timezone
        newest = datetime(2027, 1, 15, 8, 0, tzinfo=timezone.utc).timestamp()
        assert device_scope.device_status(device, newest + 60) == "online"
        assert device_scope.device_status(device, newest + 8000) == "offline"

    def test_unreadable_history_db_falls_back(self, fleet):
        device = self._device(fleet)
        with open(os.path.join(device.state_dir, "history.db"), "wb") as fh:
            fh.write(b"garbage" * 100)
        assert device_scope.device_status(device, self.NOW) == "never_seen"


def test_resolve_state_dir_is_the_only_directory_source(fleet):
    state_dir, seeded = fleet
    device = device_scope.find_device(state_dir, seeded.dev_b.id)
    assert device.state_dir == device_dirs.resolve_state_dir(state_dir, device.state_path)


def test_profile_for_reads_the_row_hardware_type_and_falls_back(fleet):
    state_dir, _seeded = fleet
    with sim_hardware_env():
        devices = device_scope.load_devices(state_dir)
        for device in devices:
            assert device_scope.profile_for(device).key == device.hardware_type
    # Gated off (simulation disabled): non-legacy rows read as legacy.
    for device in devices:
        assert device_scope.profile_for(device).key in (
            device.hardware_type, hardware.LEGACY_KEY)
    assert device_scope.profile_for(None).key == hardware.LEGACY_KEY
