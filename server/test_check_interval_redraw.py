"""Poll-cycle behaviour of the check-interval experiment: the flight image
changes at most once per saved wake interval, hold screens are never
delayed, and with the experiment off nothing differs.

Everything is read from panel.bin and poll_state.json after real
poll_cycle.run_once() calls driven by a fake clock.
"""
import datetime
import hashlib
import json
import os
import sys
import zoneinfo

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.check_interval as check_interval  # noqa: E402
import server.device_config as device_config  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.state_store as state_store  # noqa: E402

GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
CLOCK_BASE = 1_700_000_000.0
STEP_S = 30
WAKE_S = 900
KEY = check_interval.LAST_FLIGHT_REDRAW_KEY


CITIES = ("Lisbon", "Madrid", "Rome", "Berlin", "Dublin", "Athens", "Vienna", "Oslo", "Prague", "Porto")


def route_payload(callsign):
    """An adsbdb-shaped route whose destination city depends on the callsign,
    so every aircraft draws differently on the panel.
    """
    index = int(callsign[3:]) - 100

    def airport(iata, city):
        return {"iata_code": iata, "icao_code": "X" + iata, "municipality": city, "name": city}
    return {"response": {"flightroute": {
        "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
        "airline": {"name": "Air France", "icao": "AFR", "iata": "AF", "country": "France"},
        "origin": airport("ORY", "Paris"),
        "destination": airport("D%02d" % (index % 100), CITIES[index % len(CITIES)])}}}


@pytest.fixture(autouse=True)
def route_lookups(monkeypatch):
    def transport(callsign, timeout=None):
        return 200, route_payload(callsign)

    monkeypatch.setattr(enrich, "default_transport", transport)


@pytest.fixture
def clock(monkeypatch):
    fake = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: fake["t"])
    return fake


def snapshot(index):
    """A departing aircraft; each index is a distinct, differently drawn one."""
    return {"ac": [{
        "hex": "%06x" % (0xA00000 + index), "flight": "AFR%03d" % (100 + index),
        "lat": 48.7233, "lon": 2.3794, "alt_baro": 450, "gs": 137.1,
        "baro_rate": 1500, "seen_pos": 1.0}]}


EMPTY_SNAPSHOT = {"ac": []}


def set_battery(state_dir, mv):
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": mv}, fh)


def prepare(state_dir, battery_mv=3900, wake_interval_s=WAKE_S, experiment=True):
    if wake_interval_s is not None:
        device_config.save_device_config(state_dir, wake_interval_s=wake_interval_s)
    if battery_mv is not None:
        set_battery(state_dir, battery_mv)
    if experiment:
        check_interval.write_experiment(state_dir, 60, 24 * 3600, CLOCK_BASE)


def cycle(clock, state_dir, snap, advance_s=STEP_S):
    """One poll cycle `advance_s` after the last; returns panel.bin's hash."""
    clock["t"] += advance_s
    poll_cycle.run_once(snapshot=snap, state_dir=state_dir, geofence=GEOFENCE_PATH)
    return panel_hash(state_dir)


def panel_hash(state_dir):
    path = os.path.join(state_dir, "panel.bin")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_flight_image_changes_once_per_wake_interval(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    first = cycle(clock, state_dir, snapshot(0))
    first_at = clock["t"]
    assert first is not None
    assert state_store.load_poll_state(state_dir)[KEY] == first_at
    for step in range(1, 30):
        assert cycle(clock, state_dir, snapshot(step // 3 + 1)) == first, step
        assert state_store.load_poll_state(state_dir)[KEY] == first_at
    assert clock["t"] - first_at < WAKE_S
    due = cycle(clock, state_dir, snapshot(50))
    assert clock["t"] - first_at == WAKE_S
    assert due != first
    assert state_store.load_poll_state(state_dir)[KEY] == clock["t"]


def test_same_aircraft_rerender_waits_for_spacing(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    first = cycle(clock, state_dir, snapshot(0))
    for _ in range(5):
        assert cycle(clock, state_dir, snapshot(0)) == first
    assert KEY in state_store.load_poll_state(state_dir)


def test_display_off_is_not_delayed_and_exit_repaints(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    flight_image = cycle(clock, state_dir, snapshot(0))
    cycle(clock, state_dir, snapshot(1))
    device_config.save_device_config(state_dir, display_enabled=False)
    off_image = cycle(clock, state_dir, snapshot(2))
    assert off_image != flight_image
    device_config.save_device_config(state_dir, display_enabled=True)
    back = cycle(clock, state_dir, EMPTY_SNAPSHOT)
    assert back not in (off_image, None)
    assert state_store.load_poll_state(state_dir)["last_flight"]["hex"] == "a00000"


def test_quiet_hours_entry_is_not_delayed(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    flight_image = cycle(clock, state_dir, snapshot(0))
    local = datetime.datetime.fromtimestamp(clock["t"], zoneinfo.ZoneInfo("Europe/Paris"))
    start = (local - datetime.timedelta(hours=1)).strftime("%H:%M")
    end = (local + datetime.timedelta(hours=2)).strftime("%H:%M")
    device_config.save_device_config(
        state_dir, quiet_hours_enabled=True, quiet_hours_start=start, quiet_hours_end=end)
    assert cycle(clock, state_dir, snapshot(1)) != flight_image


def test_battery_empty_is_not_delayed(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    flight_image = cycle(clock, state_dir, snapshot(0))
    set_battery(state_dir, 3000)
    assert cycle(clock, state_dir, snapshot(1)) != flight_image


def hash_sequence(clock, state_dir):
    """Panel hashes over 16 cycles; a new aircraft every three cycles."""
    clock["t"] = CLOCK_BASE
    return [cycle(clock, state_dir, snapshot(step // 3)) for step in range(16)]


def make_expired(state_dir):
    check_interval.write_experiment(state_dir, 60, 3600, CLOCK_BASE - 7200)


OFF_VARIANTS = {
    "no_file": dict(battery_mv=3900, wake_interval_s=WAKE_S, experiment=False),
    "expired": dict(battery_mv=3900, wake_interval_s=WAKE_S, experiment=False, after=make_expired),
    "battery_at_floor": dict(battery_mv=3700, wake_interval_s=WAKE_S, experiment=True),
    "battery_unknown": dict(battery_mv=None, wake_interval_s=WAKE_S, experiment=True),
    "wake_unset": dict(battery_mv=3900, wake_interval_s=None, experiment=True),
}


@pytest.mark.parametrize("name", sorted(OFF_VARIANTS))
def test_off_states_match_a_run_without_the_experiment(tmp_path, clock, name):
    variant = dict(OFF_VARIANTS[name])
    after = variant.pop("after", None)
    baseline_dir = str(tmp_path / "baseline")
    off_dir = str(tmp_path / "off")
    os.makedirs(baseline_dir)
    os.makedirs(off_dir)
    prepare(baseline_dir, **dict(variant, experiment=False))
    expected = hash_sequence(clock, baseline_dir)
    prepare(off_dir, **variant)
    if after is not None:
        after(off_dir)
    assert hash_sequence(clock, off_dir) == expected
    assert len(set(expected)) > 1  # pacing still advances aircraft
    assert KEY not in state_store.load_poll_state(off_dir)
    assert sorted(state_store.load_poll_state(off_dir)) == sorted(
        state_store.load_poll_state(baseline_dir))


def test_stale_redraw_stamp_is_removed_once_inactive(tmp_path, clock):
    state_dir = str(tmp_path)
    prepare(state_dir)
    cycle(clock, state_dir, snapshot(0))
    assert KEY in state_store.load_poll_state(state_dir)
    assert check_interval.clear_experiment(state_dir)
    cycle(clock, state_dir, snapshot(0))
    assert KEY not in state_store.load_poll_state(state_dir)
