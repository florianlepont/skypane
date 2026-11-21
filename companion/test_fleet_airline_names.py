"""Airline names are fleet-wide: a name, override or default type set on one
frame is read by every other frame's editor, and the unidentified-row guard
refuses a prefix another frame already named."""
import os

import pytest

import fleet_console_support as fx
from companion import device_scope
from companion.pages import airlines_page
from companion_app_server import InProcessAppServer
from server import fleet_db, state_store
from server.plane import airline_default_types, manual_resolutions, name_overrides

UNRESOLVED = {"OCN": {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "OCN123"}}


class Fleet:
    def __init__(self, tmp_path):
        self.root = str(tmp_path / "state")
        self.server = InProcessAppServer(self.root)
        self.seed = fx.seed_fleet(self.root)
        conn = fleet_db.connect(self.root)
        try:
            self.second_id = fleet_db.add_device(
                conn, "aa:bb:cc:00:00:99", fx.SECRET_HASH, fx.hardware.LEGACY_KEY,
                self.seed.owner_id, name="Hall", state_path="auto")
        finally:
            conn.close()
        devices = {d.id: d for d in device_scope.load_devices(self.root)}
        self.frame_a = devices[self.seed.owned_id].state_dir
        self.frame_b = devices[self.second_id].state_dir
        for directory in (self.frame_a, self.frame_b):
            os.makedirs(directory, exist_ok=True)
            state_store.save_poll_state(directory, {"unresolved_prefixes": UNRESOLVED})
        self.cookie = fx.admin_cookie(self.root)

    def manage(self, device_id):
        return fx.get(self.server, self.cookie, "/devices/%s/airlines/manage" % device_id)

    def post(self, device_id, path, form):
        return fx.post(self.server, self.cookie, "/devices/%s%s" % (device_id, path), form)


@pytest.fixture
def fleet(tmp_path):
    rig = Fleet(tmp_path)
    yield rig
    rig.server.stop()


def test_a_name_given_on_one_frame_is_listed_as_named_on_another(fleet):
    _s, _h, before = fleet.manage(fleet.second_id)
    assert 'value="OCN"' in before
    status, headers, _b = fleet.post(
        fleet.seed.owned_id, "/airlines/resolve", {"prefix": "OCN", "airline_name": "Oceanic"})
    assert status == 303
    status, _h, after = fleet.manage(fleet.second_id)
    assert status == 200
    assert "Oceanic" in after
    assert 'value="OCN"' not in after
    assert not os.path.exists(os.path.join(fleet.frame_a, "manual_resolutions.json"))
    assert not os.path.exists(os.path.join(fleet.frame_b, "manual_resolutions.json"))


def test_an_override_and_a_default_type_set_on_one_frame_show_on_another(fleet):
    status, _h, _b = fleet.post(
        fleet.seed.owned_id, "/airlines/rename", {"airline": "Air France", "airline_name": "Skyline Air"})
    assert status == 303
    airline_default_types.set_default_type(fleet.frame_a, "skyline-air", "A320")
    _s, _h, body = fleet.manage(fleet.second_id)
    assert "Skyline Air" in body
    assert name_overrides.load_name_overrides(fleet.frame_b)["AFR"]["airline_name"] == "Skyline Air"
    assert airline_default_types.load_default_types(fleet.frame_b) == {"skyline-air": "A320"}


def test_a_stale_unidentified_row_cannot_overwrite_a_name_given_elsewhere(fleet):
    manual_resolutions.add_entry(fleet.frame_a, "OCN", "Oceanic", now="2026-01-01T00:00:00+00:00")
    before = open(manual_resolutions.manual_resolutions_path(fleet.frame_b)).read()
    status, headers, _b = fleet.post(
        fleet.second_id, "/airlines/resolve", {"prefix": "OCN", "airline_name": "Other Name"})
    assert status == 303
    assert "flash=%s" % airlines_page.FLASH_MANUAL_PREFIX_STALE in headers["Location"]
    assert open(manual_resolutions.manual_resolutions_path(fleet.frame_b)).read() == before
