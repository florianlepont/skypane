"""The legacy-geofence kill switch, end to end through the fleet cycle.

The switch puts the legacy Orly ids back on the hand-tuned geofence file. It
never touches catalogue-runway or position devices, never rewrites stored
configuration, and turning it off leaves the live frame observably the same.
"""

import hashlib
import math
import os

import pytest

from server import airports, detection, device_config, fleet_cycle, fleet_zones, hardware, poll_cycle
from server.plane import detect, enrich
from server.zone_fetch import ZoneFetch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOFENCE = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
POSITION = (48.8566, 2.3522)
POSITION_SETTING = {"mode": "position", "radius_km": 9}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


class FakeLedger:
    def __init__(self):
        self.served = {}

    def zone_last_served(self):
        return dict(self.served)

    def mark_zone_served(self, key, when):
        self.served[key] = when


def _approach_record():
    """A low arrival on runway 3 that the legacy file itself admits."""
    legacy = detect.load_geofence(GEOFENCE)
    axis = detect.runway_axis(legacy, runway_id="3")
    track = math.degrees(math.atan2(axis["ux"], axis["uy"])) % 360.0
    for along in (-1500.0, -800.0, 0.0, 800.0, 1500.0, 2500.0):
        record = {
            "hex": "3c6001",
            "flight": "TST001 ",
            "t": "A320",
            "lat": axis["lat0"] + along * axis["uy"] / detect._M_PER_DEG_LAT,
            "lon": axis["lon0"] + along * axis["ux"] / axis["lon_scale"],
            "alt_baro": 600,
            "baro_rate": -700,
            "gs": 140,
            "track": track,
            "seen_pos": 0.4,
        }
        if detect.runway_candidates([record], legacy, "3"):
            return record
    raise AssertionError("no position admitted by the legacy file")


class Fleet:
    """A live Orly device, an LFPG device and a position device."""

    def __init__(self, monkeypatch, root):
        self.root = str(root)
        self.fetches = []
        self.record = _approach_record()
        self.devices = [fleet_cycle.FleetDevice("live", self.root, True, hardware.LEGACY_KEY, None)]
        self.devices.append(self._device(root, "lfpg", None, detection={
            "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}))
        self.devices.append(self._device(root, "pos", POSITION, detection=POSITION_SETTING))
        monkeypatch.setattr(fleet_cycle, "load_fleet", lambda root_, now=None: self.devices)
        monkeypatch.setattr(poll_cycle, "peek_hold", lambda state_dir, now=None: None)

    @staticmethod
    def _device(root, name, location, **config):
        directory = os.path.join(str(root), name)
        os.makedirs(directory, exist_ok=True)
        device_config.save_device_config(directory, **config)
        return fleet_cycle.FleetDevice(name, directory, False, hardware.LEGACY_KEY, 1e12, location)

    def device(self, name):
        return next(d for d in self.devices if d.id == name)

    def fetcher(self, ledger, lat, lon, radius_nm, **kwargs):
        self.fetches.append(fleet_zones.Zone(lat, lon, radius_nm).key)
        records = [dict(self.record)] if (lat, lon) == detection.LEGACY_ORLY_CENTER else []
        return ZoneFetch((("adsbfi", records), ("adsblol", [dict(r) for r in records])),
                         ("adsbfi", "adsblol"), ())

    def run(self):
        return fleet_cycle.run_fleet(
            self.root, GEOFENCE, None, ledger=FakeLedger(), fetcher=self.fetcher,
            route_transport=None, environ={hardware.SIM_ENV_VAR: "1"})

    def config_bytes(self):
        out = {}
        for device in self.devices:
            path = os.path.join(device.state_dir, "device_config.json")
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    out[device.id] = fh.read()
        return out

    def panel_hash(self, name="live"):
        with open(os.path.join(self.device(name).state_dir, "panel.bin"), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()


def _spec(fleet, name):
    cfg = device_config.load_device_config(fleet.device(name).state_dir)
    return detection.spec_for(cfg, fleet.device(name).location, legacy_geofence_path=GEOFENCE)


def _lfpg_key():
    airport = airports.find_airport("LFPG")
    return "%r|%r|%r" % (round(airport.lat, 4), round(airport.lon, 4), 5.0)


def _position_key():
    return fleet_zones.Zone(48.86, 2.35, detection.km_to_nm(9)).key


ORLY_KEY = "48.7233|2.3794|5.0"


def test_kill_switch_on_reverts_the_live_frame_to_the_legacy_file(monkeypatch, tmp_path):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    fleet = Fleet(monkeypatch, tmp_path)
    resolve = fleet_cycle.detection_resolver(GEOFENCE)
    zone, document = resolve(fleet.device("live"))
    assert zone.key == ORLY_KEY
    assert document == detect.load_geofence(GEOFENCE)
    result = fleet.run()
    assert result.count("ok") == 3
    assert sorted(fleet.fetches) == sorted([ORLY_KEY, _lfpg_key(), _position_key()])
    assert len(fleet.fetches) == len(set(fleet.fetches))


def test_kill_switch_on_keeps_catalogue_and_position_specs(monkeypatch, tmp_path):
    fleet = Fleet(monkeypatch, tmp_path)
    before = {name: _spec(fleet, name) for name in ("lfpg", "pos")}
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    resolve = fleet_cycle.detection_resolver(GEOFENCE)
    for name, key in (("lfpg", _lfpg_key()), ("pos", _position_key())):
        zone, document = resolve(fleet.device(name))
        assert zone.key == key
        assert document == before[name].geofence
        assert _spec(fleet, name).display_id == before[name].display_id
    assert _spec(fleet, "lfpg").display_id == "LFPG:08L/26R"


def test_kill_switch_off_serves_orly_with_identical_observable_output(monkeypatch, tmp_path):
    outcomes = {}
    for label, value in (("on", "1"), ("off", None)):
        if value is None:
            monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
        else:
            monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, value)
        fleet = Fleet(monkeypatch, tmp_path / label)
        zone, document = fleet_cycle.detection_resolver(GEOFENCE)(fleet.device("live"))
        assert fleet.run().count("ok") == 3
        with open(os.path.join(fleet.root, "poll_state.json"), "rb") as fh:
            state = fh.read()
        assert b"3c6001" in state
        outcomes[label] = (zone.key, document, fleet.panel_hash(), sorted(fleet.fetches), state)
    on, off = outcomes["on"], outcomes["off"]
    assert on[0] == off[0] == ORLY_KEY
    assert off[1] != on[1]
    assert off[1] == detection.spec_for({}).geofence
    assert on[2] == off[2]
    assert on[3] == off[3]
    assert detect.runway_candidates([_approach_record()], off[1], "3")


@pytest.mark.parametrize("value", ["0", "", "true", "yes", " 1", "1 ", "2"])
def test_kill_switch_value_rule(monkeypatch, value):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, value)
    document = detection.spec_for({}).geofence
    assert document != detect.load_geofence(GEOFENCE)
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    assert detection.spec_for({}, legacy_geofence_path=GEOFENCE).geofence == detect.load_geofence(
        GEOFENCE)


def test_config_bytes_unchanged_by_switch(monkeypatch, tmp_path):
    fleet = Fleet(monkeypatch, tmp_path)
    device_config.save_device_config(fleet.root, tracked_runway="06-24")
    snapshots = [fleet.config_bytes()]
    for value in ("1", None):
        if value is None:
            monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
        else:
            monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, value)
        assert fleet.run().count("ok") == 3
        snapshots.append(fleet.config_bytes())
    assert snapshots[0] == snapshots[1] == snapshots[2]
    assert "live" in snapshots[0]


def test_catalogue_device_ignores_switch(monkeypatch, tmp_path):
    fleet = Fleet(monkeypatch, tmp_path)
    plain = _spec(fleet, "lfpg")
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    switched = _spec(fleet, "lfpg")
    assert switched == plain
    assert switched.zone.key == _lfpg_key()
    # Orly reached through the catalogue's legacy-mapped runway is the one
    # catalogue choice the switch does govern, via its legacy id.
    orly = detection.spec_for({"detection": {"mode": "runway", "airport": "LFPO", "runway": "07/25"}},
                              legacy_geofence_path=GEOFENCE)
    assert orly.display_id == "3"
    assert orly.geofence == detect.load_geofence(GEOFENCE)
