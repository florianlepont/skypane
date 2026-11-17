#!/usr/bin/env python3
"""What a frame is told while the check-interval experiment runs.

A real stub-server/byos_server.py subprocess answers GET /device/v1/display
over loopback. The experiment file, the saved wake interval and the battery
reading are prepared in its state directory; assertions read the served
sleep_s, the response key set and, with poll cycles run in-process on the
same directory, the served image_hash over simulated time.
"""
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import server.check_interval as check_interval  # noqa: E402
import server.device_config as device_config  # noqa: E402
import server.device_policy as device_policy  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
from skypane_frame_server import DEFAULT_SLEEP_S, FrameServer  # noqa: E402

SERVER_PATH = os.path.join(HERE, "byos_server.py")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
WAKE_S = 900
CHECK_S = 60
MAC = "aa:bb:cc:dd:ee:42"
SECRET = "7" * 64

with open(os.path.join(HERE, "measured_fields_freeze.json"), encoding="utf-8") as _fh:
    FROZEN_DISPLAY_KEYS = sorted(json.load(_fh)["display_response_keys"]["keys"])


def load_byos_module():
    spec = importlib.util.spec_from_file_location("byos_server_check_interval", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Frame:
    """An enrolled frame talking to a byos subprocess."""

    def __init__(self, state_dir):
        self.state_dir = state_dir
        self.server = FrameServer(state_dir)
        self.token = None

    def start(self):
        load_byos_module().register_device(
            self.state_dir, MAC, hashlib.sha256(SECRET.encode("ascii")).hexdigest(),
            replace=True)
        self.server.start()
        status, body = self.server.setup(MAC, SECRET)
        assert status == 200
        self.token = body["device_token"]

    def display(self, battery_mv=None):
        headers = {"X-Battery-Mv": str(battery_mv)} if battery_mv is not None else None
        status, body = self.server.display(self.token, headers)
        assert status == 200
        return body

    def sleep_s(self, battery_mv=None):
        return self.display(battery_mv)["sleep_s"]


@pytest.fixture
def frame(tmp_path):
    instance = Frame(str(tmp_path))
    try:
        instance.start()
        device_config.save_device_config(instance.state_dir, wake_interval_s=WAKE_S)
        yield instance
    finally:
        instance.server.stop()


def start_experiment(frame, duration_s=24 * 3600, now=None):
    check_interval.write_experiment(
        frame.state_dir, CHECK_S, duration_s, time.time() if now is None else now)


def test_active_experiment_serves_check_interval(frame):
    start_experiment(frame)
    body = frame.display(battery_mv=3900)
    assert body["sleep_s"] == CHECK_S
    assert sorted(body) == FROZEN_DISPLAY_KEYS


def test_saved_battery_reading_is_used_when_header_is_absent(frame):
    start_experiment(frame)
    assert frame.sleep_s(battery_mv=3900) == CHECK_S
    assert frame.sleep_s() == CHECK_S


@pytest.mark.parametrize("battery_mv", [3700, 3650, 3000])
def test_battery_at_or_below_floor_keeps_normal_cadence(frame, battery_mv):
    start_experiment(frame)
    assert frame.sleep_s(battery_mv=battery_mv) == WAKE_S


def test_unknown_battery_keeps_normal_cadence(frame):
    start_experiment(frame)
    assert frame.sleep_s() == WAKE_S


def test_expired_experiment_keeps_normal_cadence(frame):
    start_experiment(frame, duration_s=60, now=time.time() - 3600)
    body = frame.display(battery_mv=3900)
    assert body["sleep_s"] == WAKE_S
    assert sorted(body) == FROZEN_DISPLAY_KEYS


def test_no_experiment_serves_the_saved_wake_interval(frame):
    body = frame.display(battery_mv=3900)
    assert body["sleep_s"] == WAKE_S
    assert sorted(body) == FROZEN_DISPLAY_KEYS


def test_experiment_ignored_without_a_saved_wake_interval(tmp_path):
    instance = Frame(str(tmp_path))
    try:
        instance.start()
        start_experiment(instance)
        assert instance.sleep_s(battery_mv=3900) == DEFAULT_SLEEP_S
    finally:
        instance.server.stop()


def test_display_off_still_wins(frame):
    start_experiment(frame)
    device_config.save_device_config(frame.state_dir, display_enabled=False)
    assert frame.sleep_s(battery_mv=3900) == device_policy.DISPLAY_OFF_SLEEP_S


def test_battery_critical_park_still_wins(frame):
    start_experiment(frame)
    with open(os.path.join(frame.state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3900}, fh)
    with open(os.path.join(frame.state_dir, "poll_state.json"), "w") as fh:
        json.dump({"battery_critical_active": True}, fh)
    # No header on this poll, so the saved 3900 mV keeps the experiment
    # eligible while the latch has not been shown to recover.
    assert frame.sleep_s() == device_policy.BATTERY_CRITICAL_SLEEP_S


def test_quiet_hours_still_extend_the_sleep(frame):
    start_experiment(frame)
    local = datetime.now(ZoneInfo("Europe/Paris"))
    device_config.save_device_config(
        frame.state_dir, quiet_hours_enabled=True,
        quiet_hours_start=(local - timedelta(minutes=30)).strftime("%H:%M"),
        quiet_hours_end=(local + timedelta(hours=3)).strftime("%H:%M"))
    assert frame.sleep_s(battery_mv=3900) >= 2 * 3600


def departing_snapshot(index):
    return {"ac": [{
        "hex": "%06x" % (0xB00000 + index), "flight": "AFR%03d" % (100 + index),
        "lat": 48.7233, "lon": 2.3794, "alt_baro": 450, "gs": 137.1,
        "baro_rate": 1500, "seen_pos": 1.0}]}


def stub_routes(monkeypatch):
    cities = ("Lisbon", "Madrid", "Rome", "Berlin", "Dublin", "Athens", "Vienna")

    def transport(callsign, timeout=None):
        index = int(callsign[3:]) - 100

        def airport(iata, city):
            return {"iata_code": iata, "icao_code": "X" + iata, "municipality": city, "name": city}
        return 200, {"response": {"flightroute": {
            "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
            "airline": {"name": "Air France", "icao": "AFR", "iata": "AF", "country": "France"},
            "origin": airport("ORY", "Paris"),
            "destination": airport("D%02d" % index, cities[index % len(cities)])}}}

    monkeypatch.setattr(enrich, "default_transport", transport)


def test_served_image_hash_changes_once_per_wake_interval(frame, monkeypatch):
    stub_routes(monkeypatch)
    clock = {"t": time.time()}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: clock["t"])
    start_experiment(frame, now=clock["t"])
    with open(os.path.join(frame.state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3900}, fh)

    def step(index):
        clock["t"] += 30
        poll_cycle.run_once(
            snapshot=departing_snapshot(index), state_dir=frame.state_dir, geofence=GEOFENCE_PATH)
        return frame.display(battery_mv=3900)["image_hash"]

    first = step(0)
    first_at = clock["t"]
    served = [step(1 + n // 3) for n in range(29)]
    assert clock["t"] - first_at < WAKE_S
    assert set(served) == {first}
    assert step(40) != first
    assert clock["t"] - first_at == WAKE_S
