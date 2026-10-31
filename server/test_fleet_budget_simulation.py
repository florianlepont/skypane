"""Fleet-scale proofs of the ADS-B request budget with a fake clock.

A 100-device fleet is served by `run_fleet` with a fake clock shared by the
request ledger and the deadline, a recording device runner and a fake
provider call. Assertions are on recorded behaviour only: request start
times, which ZoneFetch each runner received and which devices ran.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import requests
import skypane_live_state as live_state
import skypane_two_device_fleet as two_fleet

from server import (
    device_config,
    device_dirs,
    fleet_cycle,
    fleet_db,
    fleet_migrate,
    fleet_zones,
    hardware,
    request_budget,
    zone_fetch,
)
from server.plane import detect

DEVICE_COUNT = 100
ZONE_RADIUS_NM = 25.0
PROVIDERS = ["adsbfi", "adsblol"]
# Longer than the 1.1 s spacing so float rounding cannot trip the check.
SPACING_FLOOR_S = 1.1 - 1e-6


def max_requests_in_window(times, window_s):
    """Most requests whose start times fall in any half-open window of window_s."""
    ordered = sorted(times)
    best = 0
    low = 0
    for high, moment in enumerate(ordered):
        while moment - ordered[low] >= window_s:
            low += 1
        best = max(best, high - low + 1)
    return best


class FakeClock:
    """One time source for the ledger, the deadline and the providers."""

    def __init__(self):
        self.now = time.time()

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def advance_to(self, moment):
        self.now = max(self.now, moment)


class FakeProviders:
    """Stands in for detect.query_provider; logs the fake start time of each call."""

    def __init__(self, clock):
        self.clock = clock
        self.log = []
        self.behaviour = {}

    def __call__(self, name, lat, lon, radius_nm, timeout=None):
        self.log.append((self.clock.now, name, lat))
        action = self.behaviour.get(lat)
        if action is not None:
            result = action(self.clock, name)
            if result is not None:
                return result
        return [{"hex": "%s-%s" % (name, lat)}]

    def times(self, lat=None):
        return [t for t, _, zone_lat in self.log if lat is None or zone_lat == lat]

    def clear(self):
        self.log.clear()


class Recorder:
    """Records each runner call and each fetcher result, keyed by zone latitude."""

    def __init__(self, zone_of, raise_for=()):
        self.zone_of = zone_of
        self.raise_for = set(raise_for)
        self.runs = []
        self.fetched = {}

    def runner(self, state_dir, zone_fetch=None, **kwargs):
        self.runs.append((os.path.basename(state_dir), state_dir, zone_fetch))
        if state_dir in self.raise_for:
            raise RuntimeError("renderer exploded")

    def fetcher(self, ledger, lat, lon, radius_nm, **kwargs):
        result = zone_fetch.fetch_zone(ledger, lat, lon, radius_nm, **kwargs)
        self.fetched.setdefault(lat, []).append(result)
        return result

    def reset(self):
        self.runs.clear()
        self.fetched.clear()

    def run_dirs(self):
        return [state_dir for _, state_dir, _ in self.runs]


def zone_lat(index):
    return 40.0 + index * 0.5


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def _build_fleet(root, clock, count):
    """Live frame plus count-1 simulated devices, all recently created."""
    live_state.seed_live_like_state(root)
    fleet_migrate.migrate(root, two_fleet.OWNER_EMAIL, dry_run=False)
    conn = fleet_db.connect(root)
    try:
        owner = int(conn.execute("SELECT owner_user_id FROM devices").fetchone()[0])
        with two_fleet.sim_hardware_env(), fleet_db.transaction(conn):
            for index in range(1, count):
                mac = "aa:bb:%02x:%02x:ee:%02x" % (index // 256, index % 256, 0x10)
                device_id = fleet_db.add_device(
                    conn, mac, "%064x" % index, hardware.SIM_CLONE_KEY, owner,
                    name="sim-%d" % index, token="tok-%04d-" % index + "e" * 36,
                    state_path="auto")
                device_dirs.provision_device_dir(root, device_id, 2, 2)
        conn.execute("UPDATE devices SET created_at = ? WHERE state_path != '.'",
                     (_iso(clock.now - 86400),))
    finally:
        conn.close()
    return fleet_cycle.load_fleet(root, clock.now)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def providers(monkeypatch, clock):
    fake = FakeProviders(clock)
    monkeypatch.setattr(detect, "query_provider", fake)
    return fake


@pytest.fixture
def fleet_root(tmp_path, clock):
    root = str(tmp_path)
    devices = _build_fleet(root, clock, DEVICE_COUNT)
    assert len(devices) == DEVICE_COUNT
    return SimpleNamespace(root=root, devices=devices)


def assign_zones(devices, zone_count, weights=None):
    """Device id -> zone index; the live frame is in zone 0 unless overridden."""
    mapping = {}
    for position, device in enumerate(devices):
        if weights is None:
            mapping[device.id] = position % zone_count
        else:
            mapping[device.id] = weights[position % len(weights)]
    return mapping


def make_resolver(mapping):
    def resolve(device):
        lat = zone_lat(mapping[device.id])
        zone = fleet_zones.Zone(lat, 2.0, ZONE_RADIUS_NM)
        return zone, {"center": {"lat": lat, "lon": 2.0}}
    return resolve


def run_cycle(fleet_root, clock, recorder, mapping, **kwargs):
    ledger = request_budget.RequestLedger(
        fleet_root.root, clock=clock.time, sleep=clock.sleep)
    return fleet_cycle.run_fleet(
        fleet_root.root, None, None,
        clock=clock.time, monotonic=clock.time, sleep=clock.sleep, ledger=ledger,
        runner=recorder.runner, fetcher=recorder.fetcher,
        resolver=make_resolver(mapping), route_transport=object(),
        environ={hardware.SIM_ENV_VAR: "1"}, **kwargs)


# Uneven spread: zone 0 holds half the fleet, the rest share the remainder.
UNEVEN = [0] * 10 + [1] * 5 + [2] * 3 + [3] * 2 + [4] + [5]


def test_hundred_devices_cost_two_requests_per_zone_per_cycle(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)
    by_dir = {d.state_dir: d for d in fleet_root.devices}
    for _ in range(20):
        recorder.reset()
        providers.clear()
        cycle_start = clock.now
        result = run_cycle(fleet_root, clock, recorder, mapping)

        assert len(providers.log) == 12
        for index in range(6):
            lat = zone_lat(index)
            assert [name for _, name, zone in providers.log if zone == lat] == PROVIDERS
        times = providers.times()
        gaps = [b - a for a, b in zip(times, times[1:])]
        assert all(gap >= SPACING_FLOOR_S for gap in gaps)
        assert max_requests_in_window(times, 1.0) == 1
        assert clock.now - cycle_start < detect_deadline()

        assert sorted(recorder.run_dirs()) == sorted(by_dir)
        assert len(recorder.runs) == DEVICE_COUNT
        assert result.count(fleet_cycle.STATUS_OK) == DEVICE_COUNT
        for _, state_dir, received in recorder.runs:
            lat = zone_lat(mapping[by_dir[state_dir].id])
            assert len(recorder.fetched[lat]) == 1
            assert received is recorder.fetched[lat][0]
        clock.advance_to(cycle_start + 30.0)


def detect_deadline():
    return fleet_cycle.FLEET_START_DEADLINE_S


def _first_request_order(providers):
    order = []
    for _, _, lat in providers.log:
        if lat not in order:
            order.append(lat)
    return order


def _expected_capacity(deadline_s):
    """Zones that start: zone k begins 2.2 * (k - 1) s in, checked 1.1 s earlier."""
    started = 0
    while 2.2 * started - 1.1 < deadline_s and started < 1000:
        started += 1
    return started if 2.2 * (started - 1) - 1.1 < deadline_s else started - 1


def _model_order(zone_count, live_index, served):
    def sort_key(index):
        seen = served.get(index)
        return (index != live_index, seen is not None, seen or 0, zone_lat(index))
    return sorted(range(zone_count), key=sort_key)


def _capacity_scenario(fleet_root, clock, providers, zone_count, live_index, cycles, **kwargs):
    mapping = assign_zones(fleet_root.devices, zone_count)
    live = next(d for d in fleet_root.devices if d.is_live)
    mapping[live.id] = live_index
    recorder = Recorder(mapping)
    served = {}
    seen_zones = set()
    for cycle in range(cycles):
        recorder.reset()
        providers.clear()
        cycle_start = clock.now
        run_cycle(fleet_root, clock, recorder, mapping, **kwargs)
        order = _first_request_order(providers)
        capacity = _expected_capacity(kwargs.get("start_deadline_s", detect_deadline()))
        expected = [zone_lat(i) for i in _model_order(zone_count, live_index, served)][:capacity]
        assert order == expected
        assert len(providers.log) == 2 * capacity
        assert max_requests_in_window(providers.times(), 1.0) == 1
        assert order[0] == zone_lat(live_index)
        fetched_zones = {round((lat - 40.0) / 0.5) for lat in order}
        served_now = {mapping[d.id] for d in fleet_root.devices
                      if d.state_dir in recorder.run_dirs()}
        # Devices run only for fetched zones; the zone fetched last can have its
        # devices deferred when its second request ends past the start deadline.
        assert served_now <= fetched_zones
        assert len(fetched_zones - served_now) <= 1
        for position, lat in enumerate(order):
            index = round((lat - 40.0) / 0.5)
            if index in served_now:
                served[index] = (cycle, position)
        seen_zones |= served_now
        clock.advance_to(cycle_start + 30.0)
    return seen_zones, len(providers.log) // 2


def test_capacity_exceeding_fleet_serves_twelve_zones_oldest_first(
        fleet_root, clock, providers):
    assert _expected_capacity(fleet_cycle.FLEET_START_DEADLINE_S) == 12
    seen, zones_fetched = _capacity_scenario(
        fleet_root, clock, providers, 30, live_index=17, cycles=3)
    assert zones_fetched == 12
    assert seen == set(range(30))


def test_small_deadline_serves_three_of_ten_zones_with_same_ordering(
        fleet_root, clock, providers):
    assert _expected_capacity(5.0) == 3
    seen, zones_fetched = _capacity_scenario(
        fleet_root, clock, providers, 10, live_index=4, cycles=10, start_deadline_s=5.0)
    assert zones_fetched == 3
    assert seen == set(range(10))


def test_unreached_zone_devices_are_not_run(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 30)
    recorder = Recorder(mapping)
    result = run_cycle(fleet_root, clock, recorder, mapping)
    fetched = {lat for _, _, lat in providers.log}
    by_dir = {d.state_dir: d for d in fleet_root.devices}
    assert 0 < len(recorder.runs) < DEVICE_COUNT
    assert result.count(fleet_cycle.STATUS_DEFERRED) == DEVICE_COUNT - len(recorder.runs)
    for state_dir in recorder.run_dirs():
        assert zone_lat(mapping[by_dir[state_dir].id]) in fetched


def _lat_of(device, mapping):
    return zone_lat(mapping[device.id])


def test_provider_failure_in_the_last_zone_leaves_others_healthy(
        fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)
    ledger = request_budget.RequestLedger(fleet_root.root, clock=clock.time, sleep=clock.sleep)
    # Zone 5 was served most recently, so it is fetched last.
    for index in range(5):
        ledger.mark_zone_served(
            fleet_zones.Zone(zone_lat(index), 2.0, ZONE_RADIUS_NM).key, clock.now - 1000 + index)
    ledger.mark_zone_served(
        fleet_zones.Zone(zone_lat(5), 2.0, ZONE_RADIUS_NM).key, clock.now - 10)

    def fail(_clock, _name):
        raise requests.HTTPError("503 upstream")
    providers.behaviour[zone_lat(5)] = fail

    result = run_cycle(fleet_root, clock, recorder, mapping)

    assert len(recorder.runs) == DEVICE_COUNT
    assert result.count(fleet_cycle.STATUS_OK) == DEVICE_COUNT
    by_dir = {d.state_dir: d for d in fleet_root.devices}
    for _, state_dir, received in recorder.runs:
        lat = _lat_of(by_dir[state_dir], mapping)
        if lat == zone_lat(5):
            assert received.results == ()
            assert received.failed == tuple(PROVIDERS)
        else:
            assert [name for name, _ in received.results] == PROVIDERS
            assert received.failed == ()


def test_provider_failure_pauses_the_provider_but_every_device_still_runs(
        fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)

    def fail(_clock, _name):
        raise requests.HTTPError("429 too many requests")
    providers.behaviour[zone_lat(0)] = fail

    result = run_cycle(fleet_root, clock, recorder, mapping)
    assert len(recorder.runs) == DEVICE_COUNT
    assert result.count(fleet_cycle.STATUS_OK) == DEVICE_COUNT
    # Both providers failed once for the live zone and are now paused: no
    # further request is made this cycle, nor 30 s later.
    assert len(providers.log) == 2
    providers.clear()
    clock.advance_to(clock.now + 30.0)
    recorder.reset()
    run_cycle(fleet_root, clock, recorder, mapping)
    assert providers.log == []
    assert len(recorder.runs) == DEVICE_COUNT


def test_slow_provider_does_not_block_later_zones(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)

    def slow(fake_clock, name):
        if name == "adsbfi":
            fake_clock.now += 8.0
    providers.behaviour[zone_lat(1)] = slow

    cycle_start = clock.now
    run_cycle(fleet_root, clock, recorder, mapping)
    assert len(providers.log) == 12
    assert len(recorder.runs) == DEVICE_COUNT
    assert max(providers.times()) - cycle_start < detect_deadline() + 1.2


def test_slow_zones_stop_new_zones_at_the_start_deadline(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)

    def slow(fake_clock, _name):
        fake_clock.now += 8.0
    for index in range(6):
        providers.behaviour[zone_lat(index)] = slow

    cycle_start = clock.now
    result = run_cycle(fleet_root, clock, recorder, mapping)
    zones_requested = {lat for _, _, lat in providers.log}
    assert 0 < len(zones_requested) < 6
    # No zone begins once the start deadline has passed.
    assert all(t < cycle_start + detect_deadline() for t in providers.times()[::2])
    assert 0 < len(recorder.runs) < DEVICE_COUNT
    assert result.count(fleet_cycle.STATUS_DEFERRED) == DEVICE_COUNT - len(recorder.runs)


def test_unexpected_provider_error_fails_that_zone_and_pauses_the_provider(
        fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)
    ledger = request_budget.RequestLedger(fleet_root.root, clock=clock.time, sleep=clock.sleep)
    for index in range(5):
        ledger.mark_zone_served(
            fleet_zones.Zone(zone_lat(index), 2.0, ZONE_RADIUS_NM).key, clock.now - 1000 + index)
    ledger.mark_zone_served(
        fleet_zones.Zone(zone_lat(5), 2.0, ZONE_RADIUS_NM).key, clock.now - 10)

    def boom(_clock, _name):
        raise RuntimeError("unexpected parser failure")
    providers.behaviour[zone_lat(5)] = boom

    run_cycle(fleet_root, clock, recorder, mapping)

    by_dir = {d.state_dir: d for d in fleet_root.devices}
    assert len(recorder.runs) == DEVICE_COUNT
    for _, state_dir, received in recorder.runs:
        lat = _lat_of(by_dir[state_dir], mapping)
        if lat == zone_lat(5):
            assert received.queried == received.failed == tuple(PROVIDERS)
            assert received.results == ()
        else:
            assert received.failed == ()
    providers.clear()
    clock.advance_to(clock.now + 30.0)
    recorder.reset()
    run_cycle(fleet_root, clock, recorder, mapping)
    assert providers.log == []
    clock.advance_to(clock.now + request_budget.PROVIDER_PAUSE_S)
    run_cycle(fleet_root, clock, recorder, mapping)
    assert providers.log


def test_raising_fetcher_gives_that_zone_a_failed_fetch_only(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    recorder = Recorder(mapping)
    bad_lat = zone_lat(3)
    real_fetcher = recorder.fetcher

    def fetcher(ledger, lat, lon, radius_nm, **kwargs):
        if lat == bad_lat:
            raise RuntimeError("fetcher bug")
        return real_fetcher(ledger, lat, lon, radius_nm, **kwargs)
    recorder.fetcher = fetcher

    run_cycle(fleet_root, clock, recorder, mapping)

    by_dir = {d.state_dir: d for d in fleet_root.devices}
    assert len(recorder.runs) == DEVICE_COUNT
    for _, state_dir, received in recorder.runs:
        if _lat_of(by_dir[state_dir], mapping) == bad_lat:
            assert received.queried == received.failed == tuple(PROVIDERS)
        else:
            assert received.failed == ()
    assert bad_lat not in {lat for _, _, lat in providers.log}


def test_runner_error_for_one_device_leaves_the_other_ninety_nine_run(
        fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    victim = fleet_root.devices[40]
    recorder = Recorder(mapping, raise_for=[victim.state_dir])
    result = run_cycle(fleet_root, clock, recorder, mapping)
    assert len(recorder.runs) == DEVICE_COUNT
    assert result.count(fleet_cycle.STATUS_FAILED) == 1
    assert result.count(fleet_cycle.STATUS_OK) == DEVICE_COUNT - 1


def test_held_devices_alone_in_a_zone_cost_no_request(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    held = [d for d in fleet_root.devices if not d.is_live][:4]
    for device in held:
        mapping[device.id] = 6
        device_config.save_device_config(device.state_dir, display_enabled=False)
    recorder = Recorder(mapping)
    result = run_cycle(fleet_root, clock, recorder, mapping)
    assert zone_lat(6) not in {lat for _, _, lat in providers.log}
    assert len({lat for _, _, lat in providers.log}) == 6
    assert result.count(fleet_cycle.STATUS_HELD) == len(held)
    for _, state_dir, received in recorder.runs:
        if state_dir in {d.state_dir for d in held}:
            assert received == zone_fetch.ZoneFetch.not_fetched()


def test_inactive_devices_are_never_run(fleet_root, clock, providers):
    mapping = assign_zones(fleet_root.devices, 6, weights=UNEVEN)
    stale = [d for d in fleet_root.devices if not d.is_live][:5]
    conn = fleet_db.connect(fleet_root.root)
    try:
        for device in stale:
            conn.execute("UPDATE devices SET created_at = ? WHERE id = ?",
                         (_iso(clock.now - 8 * 86400), device.id))
    finally:
        conn.close()
    recorder = Recorder(mapping)
    result = run_cycle(fleet_root, clock, recorder, mapping)
    ran = set(recorder.run_dirs())
    assert not ran & {d.state_dir for d in stale}
    live = next(d for d in fleet_root.devices if d.is_live)
    fresh = next(d for d in fleet_root.devices if d not in stale and not d.is_live)
    assert live.state_dir in ran and fresh.state_dir in ran
    assert result.count(fleet_cycle.STATUS_SKIPPED) == len(stale)
    assert len(recorder.runs) == DEVICE_COUNT - len(stale)
