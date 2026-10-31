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


def test_landscape_hardware_is_skipped_while_simulation_is_off(tmp_path):
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


# --- run_fleet ----------------------------------------------------------------

import shutil
import threading

from server import poll_cycle, request_budget, state_store, zone_fetch
from server.plane import detect

GEOFENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "adsb-test", "runway3.json")
ZONE_A = fleet_zones.Zone(48.7, 2.4, 20.0)
ZONE_B = fleet_zones.Zone(49.0, 2.5, 20.0)
ANSWERED = zone_fetch.ZoneFetch((("adsbfi", []), ("adsblol", [])), ("adsbfi", "adsblol"), ())
ALL_FAILED = zone_fetch.ZoneFetch((), ("adsbfi", "adsblol"), ("adsbfi", "adsblol"))


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.lock = threading.Lock()

    def time(self):
        return self.now

    def sleep(self, seconds):
        with self.lock:
            self.now += seconds


class FakeLedger:
    def __init__(self, last_served=None):
        self.last_served = dict(last_served or {})
        self.marked = []

    def zone_last_served(self):
        return dict(self.last_served)

    def mark_zone_served(self, key, when):
        self.marked.append(key)
        self.last_served[key] = when


class Recorder:
    """Fake runner and fetcher sharing one call log."""

    def __init__(self, zone_results=None, raises=(), clock=None, step=0.0):
        self.zone_results = zone_results or {}
        self.raises = set(raises)
        self.clock = clock
        self.step = step
        self.fetches = []
        self.runs = []

    def fetcher(self, ledger, lat, lon, radius_nm, **kwargs):
        self.fetches.append(((lat, lon, radius_nm), kwargs))
        outcome = self.zone_results.get((lat, lon, radius_nm), ANSWERED)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def runner(self, **kwargs):
        name = os.path.basename(kwargs["state_dir"])
        self.runs.append((name, kwargs))
        if self.clock is not None:
            self.clock.now += self.step
        if name in self.raises:
            raise RuntimeError("boom " + name)
        path = os.path.join(kwargs["state_dir"], state_store.POLL_STATE_FILENAME)
        with open(path, "w") as fh:
            fh.write("{}")
        os.utime(path, (len(self.runs), len(self.runs)))
        return {}

    def names(self):
        return [name for name, _ in self.runs]


def _fleet(monkeypatch, tmp_path, names):
    """Patch load_fleet to the live root plus one device directory per name."""
    root = str(tmp_path)
    devices = [fleet_cycle.FleetDevice("live", root, True, hardware.LEGACY_KEY, None)]
    for name in names:
        directory = tmp_path / name
        directory.mkdir(exist_ok=True)
        devices.append(fleet_cycle.FleetDevice(name, str(directory), False, hardware.LEGACY_KEY, 1e12))
    monkeypatch.setattr(fleet_cycle, "load_fleet", lambda root_, now=None: devices)
    monkeypatch.setattr(poll_cycle, "peek_hold", lambda state_dir, now=None: None)
    return root


def _resolver(mapping):
    def resolve(device):
        zone = mapping.get(device.id, ZONE_A)
        return zone, {"center": {"lat": zone.lat, "lon": zone.lon}}
    return resolve


def _run(root, rec, ledger=None, **kwargs):
    kwargs.setdefault("resolver", _resolver({}))
    return fleet_cycle.run_fleet(
        root, GEOFENCE, "caddy.log", ledger=ledger or FakeLedger(),
        runner=rec.runner, fetcher=rec.fetcher, route_transport="transport",
        environ={}, **kwargs)


def test_one_zone_is_fetched_once_and_shared(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    rec = Recorder()
    result = _run(root, rec)
    assert len(rec.fetches) == 1
    assert len(rec.runs) == 3
    assert result.zone_fetches == 1
    assert len({id(kw["zone_fetch"]) for _, kw in rec.runs}) == 1
    assert all(kw["ledger_root"] == root for _, kw in rec.runs)


def test_two_zones_two_fetches(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    rec = Recorder()
    _run(root, rec, resolver=_resolver({"b": ZONE_B}))
    assert len(rec.fetches) == 2


def test_held_device_gets_not_fetched_and_costs_no_request(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    monkeypatch.setattr(
        poll_cycle, "peek_hold",
        lambda state_dir, now=None: "display_off" if state_dir.endswith("b") else None)
    rec = Recorder()
    result = _run(root, rec, resolver=_resolver({"b": ZONE_B}))
    assert len(rec.fetches) == 1
    held_kwargs = dict(rec.runs)["b"]
    assert held_kwargs["zone_fetch"] == zone_fetch.ZoneFetch.not_fetched()
    assert result.count("held") == 1


def test_live_zone_first_then_oldest_served(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b", "c"])
    rec = Recorder()
    zone_c = fleet_zones.Zone(50.0, 2.0, 20.0)
    ledger = FakeLedger({ZONE_B.key: 500.0, zone_c.key: 100.0})
    _run(root, rec, ledger=ledger,
         resolver=_resolver({"live": ZONE_A, "a": ZONE_B, "b": zone_c, "c": ZONE_A}))
    assert rec.names()[0] == os.path.basename(root)
    assert [centre for centre, _ in rec.fetches] == [
        (ZONE_A.lat, ZONE_A.lon, ZONE_A.radius_nm),
        (zone_c.lat, zone_c.lon, zone_c.radius_nm),
        (ZONE_B.lat, ZONE_B.lon, ZONE_B.radius_nm)]
    assert sorted(ledger.marked) == sorted([ZONE_A.key, ZONE_B.key, zone_c.key])


def test_unanswered_zone_is_not_marked_served(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a"])
    rec = Recorder({(ZONE_B.lat, ZONE_B.lon, ZONE_B.radius_nm): ALL_FAILED})
    ledger = FakeLedger()
    _run(root, rec, ledger=ledger, resolver=_resolver({"a": ZONE_B}))
    assert ledger.marked == [ZONE_A.key]
    received = dict(rec.runs)["a"]["zone_fetch"]
    assert received is ALL_FAILED


def test_deadline_defers_unreached_devices(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    clock = FakeClock()
    rec = Recorder(clock=clock, step=30.0)
    ledger = FakeLedger()
    result = _run(root, rec, ledger=ledger, monotonic=clock.time,
                  resolver=_resolver({"a": ZONE_B, "b": ZONE_B}))
    assert rec.names() == [os.path.basename(root)]
    assert len(rec.fetches) == 1
    assert result.count("deferred") == 2
    for name in ("a", "b"):
        assert not os.path.exists(tmp_path / name / state_store.POLL_STATE_FILENAME)
    deadline_at = rec.fetches[0][1]["deadline_at"]
    assert deadline_at <= 1000.0 + fleet_cycle.FLEET_START_DEADLINE_S


def test_fetch_deadline_follows_the_injected_start_deadline(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, [])
    clock = FakeClock()
    rec = Recorder()
    _run(root, rec, monotonic=clock.time, start_deadline_s=7.0)
    assert rec.fetches[0][1]["deadline_at"] == pytest.approx(1007.0)


def test_mid_zone_deadline_and_next_cycle_order(monkeypatch, tmp_path):
    names = ["a", "b", "c"]
    root = _fleet(monkeypatch, tmp_path, names)
    clock = FakeClock()
    rec = Recorder(clock=clock, step=10.0)
    ledger = FakeLedger()
    first = _run(root, rec, ledger=ledger, monotonic=clock.time)
    ran_first = rec.names()
    assert len(ran_first) == 3
    assert first.count("deferred") == 1
    deferred = [o.device_id for o in first.outcomes if o.status == "deferred"]
    assert ledger.marked == [ZONE_A.key]
    rec.runs.clear()
    _run(root, rec, ledger=ledger, monotonic=clock.time)
    assert rec.names()[0] == os.path.basename(root)
    assert rec.names()[1] == deferred[0]


def test_zone_whose_devices_were_all_deferred_is_not_marked(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a"])
    clock = FakeClock()

    def slow_fetcher(ledger, lat, lon, radius_nm, **kwargs):
        if lat == ZONE_B.lat:
            clock.now += 100.0
        return ANSWERED

    rec = Recorder()
    ledger = FakeLedger()
    fleet_result = fleet_cycle.run_fleet(
        root, GEOFENCE, None, ledger=ledger, runner=rec.runner, fetcher=slow_fetcher,
        route_transport="t", monotonic=clock.time, environ={},
        resolver=_resolver({"a": ZONE_B}))
    assert fleet_result.count("deferred") == 1
    assert ledger.marked == [ZONE_A.key]


def test_runner_failure_does_not_stop_other_devices(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b", "c"])
    rec = Recorder(raises=["b"])
    result = _run(root, rec, resolver=_resolver({"c": ZONE_B}))
    assert sorted(rec.names()) == sorted([os.path.basename(root), "a", "b", "c"])
    assert result.count("failed") == 1
    assert result.count("ok") == 3


def test_busy_device_is_counted_and_skipped(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    rec = Recorder()
    inner = rec.runner

    def runner(**kwargs):
        if kwargs["state_dir"].endswith("a"):
            raise poll_cycle.PollBusy("lock-a", 1.0)
        return inner(**kwargs)

    result = fleet_cycle.run_fleet(
        root, GEOFENCE, None, ledger=FakeLedger(), runner=runner, fetcher=rec.fetcher,
        route_transport="t", environ={}, resolver=_resolver({}))
    assert result.count("busy") == 1
    assert result.count("ok") == 2


def test_failed_zone_does_not_touch_other_zones(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a", "b"])
    rec = Recorder({(ZONE_B.lat, ZONE_B.lon, ZONE_B.radius_nm): ALL_FAILED})
    _run(root, rec, resolver=_resolver({"a": ZONE_B, "b": ZONE_B}))
    received = {name: kw["zone_fetch"] for name, kw in rec.runs}
    assert received["a"] is ALL_FAILED and received["b"] is ALL_FAILED
    assert received[os.path.basename(root)] is ANSWERED


def test_live_runs_with_reconcile_and_caddy_log_only(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a"])
    rec = Recorder()
    _run(root, rec)
    by_name = dict(rec.runs)
    live = by_name[os.path.basename(root)]
    assert live["reconcile_firmware"] is True and live["caddy_log"] == "caddy.log"
    assert by_name["a"]["reconcile_firmware"] is False and by_name["a"]["caddy_log"] is None
    assert {kw["route_transport"] for _, kw in rec.runs} == {"transport"}


def test_live_frame_with_unresolvable_zone_runs_standalone(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a"])
    rec = Recorder()

    def resolver(device):
        raise OSError("no geofence")

    result = _run(root, rec, resolver=resolver)
    assert dict(rec.runs)[os.path.basename(root)]["zone_fetch"] is None
    assert rec.fetches == []
    assert result.count("skipped") == 1


def test_fetcher_crash_becomes_a_failed_fetch(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, ["a"])
    rec = Recorder({(ZONE_B.lat, ZONE_B.lon, ZONE_B.radius_nm): RuntimeError("x")})
    _run(root, rec, resolver=_resolver({"a": ZONE_B}))
    received = dict(rec.runs)["a"]["zone_fetch"]
    assert received != zone_fetch.ZoneFetch.not_fetched()
    assert received.queried == received.failed == detect.DEFAULT_PROVIDER_ORDER
    assert dict(rec.runs)[os.path.basename(root)]["zone_fetch"] is ANSWERED


def test_real_cycle_reports_source_fault_only_for_the_failed_zone(fleet, tmp_path):
    outcomes = {}

    def runner(**kwargs):
        outcomes[kwargs["state_dir"]] = poll_cycle.run_once(**kwargs)
        return outcomes[kwargs["state_dir"]]

    def fetcher(ledger, lat, lon, radius_nm, **kwargs):
        if lat == ZONE_B.lat:
            raise RuntimeError("down")
        return ANSWERED

    result = fleet_cycle.run_fleet(
        str(tmp_path), GEOFENCE, None, ledger=FakeLedger(), runner=runner, fetcher=fetcher,
        route_transport=None, environ=_env(),
        resolver=_resolver({fleet.dev_a.id: ZONE_B}))
    assert result.count("ok") == 3
    assert outcomes[fleet.dev_a.state_dir]["source_fault"] is True
    assert outcomes[fleet.dev_b.state_dir]["source_fault"] is False
    assert outcomes[str(tmp_path)]["source_fault"] is False


def test_real_cycles_update_every_device_and_match_a_direct_live_run(fleet, tmp_path):
    root = str(tmp_path)
    copy = str(tmp_path.parent / (tmp_path.name + "-copy"))
    shutil.copytree(root, copy)
    before = {fleet.dev_a.id: _panel(fleet.dev_a.state_dir), fleet.dev_b.id: _panel(fleet.dev_b.state_dir)}
    result = fleet_cycle.run_fleet(
        root, GEOFENCE, None, ledger=FakeLedger(), fetcher=lambda *a, **k: ANSWERED,
        route_transport=None, environ=_env())
    assert result.count("ok") == 3
    assert _panel(fleet.dev_a.state_dir) != before[fleet.dev_a.id]
    assert _panel(fleet.dev_b.state_dir) != before[fleet.dev_b.id]
    assert os.path.exists(os.path.join(fleet.dev_a.state_dir, state_store.POLL_STATE_FILENAME))
    poll_cycle.run_once(state_dir=copy, geofence=GEOFENCE, zone_fetch=ANSWERED, ledger_root=copy,
                        reconcile_firmware=True)
    assert _panel(root) == _panel(copy)


def _panel(state_dir):
    with open(os.path.join(state_dir, "panel.bin"), "rb") as fh:
        return fh.read()


def test_overlapping_runs_never_space_requests_closer_than_the_budget(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, [])
    clock = FakeClock()
    stamps = []

    def query(name, lat, lon, radius_nm, timeout):
        with clock.lock:
            stamps.append(clock.now)
        return []

    monkeypatch.setattr(detect, "query_provider", query)
    rec = Recorder()

    def one_run():
        fleet_cycle.run_fleet(
            root, GEOFENCE, None, clock=clock.time, sleep=clock.sleep, runner=rec.runner,
            route_transport="t", environ={}, resolver=_resolver({}))

    threads = [threading.Thread(target=one_run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    stamps.sort()
    assert len(stamps) == 4
    assert all(b - a >= request_budget.MIN_SPACING_S - 1e-6 for a, b in zip(stamps, stamps[1:]))


def test_landscape_hardware_is_kept_when_simulation_is_on(tmp_path):
    with two_fleet.sim_hardware_env():
        seeded = two_fleet.seed_two_device_fleet(str(tmp_path), with_landscape=True)
        devices = fleet_cycle.load_fleet(str(tmp_path), NOW)
        keep, skipped = fleet_cycle.runnable_devices(
            devices, NOW, {"SKYPANE_SIM_HARDWARE": "1"})
    assert (seeded.landscape.id, "unsupported_hardware") not in skipped


def test_only_non_live_devices_cycle_through_their_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")
    root = _fleet(monkeypatch, tmp_path, ["a"])
    devices = fleet_cycle.load_fleet(root)
    devices[1] = fleet_cycle.FleetDevice(
        "a", devices[1].state_dir, False, hardware.SIM_LANDSCAPE_KEY, 1e12)
    monkeypatch.setattr(fleet_cycle, "load_fleet", lambda root_, now=None: devices)
    rec = Recorder()
    fleet_cycle.run_fleet(
        root, GEOFENCE, "caddy.log", ledger=FakeLedger(), runner=rec.runner,
        fetcher=rec.fetcher, route_transport="transport",
        environ={"SKYPANE_SIM_HARDWARE": "1"}, resolver=_resolver({}))
    live = [kw for _, kw in rec.runs if kw["state_dir"] == root]
    other = [kw for _, kw in rec.runs if kw["state_dir"] != root]
    assert len(live) == 1 and "profile" not in live[0]
    assert [kw["profile"].key for kw in other] == [hardware.SIM_LANDSCAPE_KEY]


# --- per-device detection resolver --------------------------------------------

from server import detection, device_config  # noqa: E402


def _save_detection(state_dir, **kwargs):
    os.makedirs(state_dir, exist_ok=True)
    device_config.save_device_config(state_dir, **kwargs)


def _runway_setting(icao, designator):
    return {"mode": "runway", "airport": icao, "runway": designator}


def _plan(tmp_path, devices):
    resolver = fleet_cycle.detection_resolver(GEOFENCE)
    return fleet_cycle.plan_zones(devices, resolver, hold_of=lambda path: None)


def _device(tmp_path, name, location=None, live=False, **config):
    directory = str(tmp_path / name)
    os.makedirs(directory, exist_ok=True)
    if config:
        device_config.save_device_config(directory, **config)
    return fleet_cycle.FleetDevice(
        name, directory, live, hardware.LEGACY_KEY, 1e12, location)


def test_devices_of_one_airport_share_a_zone_across_runways(tmp_path):
    live = _device(tmp_path, "live", live=True)
    a = _device(tmp_path, "a", detection=_runway_setting("LFPG", "08L/26R"))
    b = _device(tmp_path, "b", detection=_runway_setting("LFPG", "08R/26L"))
    plan = _plan(tmp_path, [live, a, b])
    assert len(plan.zones) == 2
    sizes = sorted(len(g.devices) for g in plan.zones.values())
    assert sizes == [1, 2]
    assert plan.unzoned == []


def test_shared_airport_zone_is_fetched_once_and_each_device_keeps_its_runway(
        monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, [])
    devices = [
        fleet_cycle.FleetDevice("live", root, True, hardware.LEGACY_KEY, None),
        _device(tmp_path, "a", detection=_runway_setting("LFPG", "08L/26R")),
        _device(tmp_path, "b", detection=_runway_setting("LFPG", "08R/26L")),
    ]
    monkeypatch.setattr(fleet_cycle, "load_fleet", lambda root_, now=None: devices)
    rec = Recorder()
    seen = {}
    base_runner = rec.runner

    def runner(**kwargs):
        cfg = device_config.load_device_config(kwargs["state_dir"])
        spec = detection.spec_for(cfg, kwargs.get("location"), legacy_geofence_path=GEOFENCE)
        seen[os.path.basename(kwargs["state_dir"])] = spec.display_id
        return base_runner(**kwargs)

    fleet_cycle.run_fleet(
        root, GEOFENCE, None, ledger=FakeLedger(), runner=runner,
        fetcher=rec.fetcher, route_transport="transport", environ={})
    assert len(rec.fetches) == 2
    assert seen["a"] == "LFPG:08L/26R"
    assert seen["b"] == "LFPG:08R/26L"
    assert seen[os.path.basename(root)] == "3"


def test_neighbouring_position_devices_share_one_zone(tmp_path):
    setting = {"mode": "position", "radius_km": 9}
    a = _device(tmp_path, "a", location=(48.8566, 2.3522), detection=setting)
    b = _device(tmp_path, "b", location=(48.8601, 2.3500), detection=setting)
    plan = _plan(tmp_path, [a, b])
    assert len(plan.zones) == 1
    group = next(iter(plan.zones.values()))
    assert [d.id for d in group.devices] == ["a", "b"]
    assert (group.zone.lat, group.zone.lon) == (48.86, 2.35)


def test_position_devices_with_different_radius_are_different_zones(tmp_path):
    a = _device(tmp_path, "a", location=(48.86, 2.35), detection={"mode": "position", "radius_km": 9})
    b = _device(tmp_path, "b", location=(48.86, 2.35), detection={"mode": "position", "radius_km": 12})
    assert len(_plan(tmp_path, [a, b]).zones) == 2


def test_position_device_without_usable_location_polls_the_orly_zone(tmp_path):
    setting = {"mode": "position", "radius_km": 9}
    live = _device(tmp_path, "live", live=True)
    nowhere = _device(tmp_path, "nowhere", detection=setting)
    abroad = _device(tmp_path, "abroad", location=(40.7128, -74.006), detection=setting)
    plan = _plan(tmp_path, [live, nowhere, abroad])
    assert len(plan.zones) == 1
    assert len(next(iter(plan.zones.values())).devices) == 3
    assert plan.unzoned == []


def test_corrupt_device_config_falls_back_to_the_legacy_zone(tmp_path):
    live = _device(tmp_path, "live", live=True)
    broken = _device(tmp_path, "broken")
    with open(os.path.join(broken.state_dir, "device_config.json"), "w") as fh:
        fh.write("{not json")
    plan = _plan(tmp_path, [live, broken])
    assert len(plan.zones) == 1
    assert plan.unzoned == []


def test_missing_legacy_file_with_kill_switch_leaves_the_device_unzoned(monkeypatch, tmp_path):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    resolver = fleet_cycle.detection_resolver(str(tmp_path / "nope.json"))
    plan = fleet_cycle.plan_zones(
        [_device(tmp_path, "live", live=True)], resolver, hold_of=lambda path: None)
    assert [d.id for d in plan.unzoned] == ["live"]


def test_generic_and_kill_switch_resolvers_give_the_live_frame_one_zone(monkeypatch, tmp_path):
    live = _device(tmp_path, "live", live=True)
    generic_zone, _ = fleet_cycle.detection_resolver(GEOFENCE)(live)
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    legacy_zone, _ = fleet_cycle.detection_resolver(GEOFENCE)(live)
    assert generic_zone == legacy_zone
    assert generic_zone.key == legacy_zone.key


def test_runner_receives_location_only_for_devices_that_have_one(monkeypatch, tmp_path):
    root = _fleet(monkeypatch, tmp_path, [])
    devices = [
        fleet_cycle.FleetDevice("live", root, True, hardware.LEGACY_KEY, None),
        _device(tmp_path, "p", location=(48.86, 2.35),
                detection={"mode": "position", "radius_km": 9}),
    ]
    monkeypatch.setattr(fleet_cycle, "load_fleet", lambda root_, now=None: devices)
    rec = Recorder()
    _run(root, rec, resolver=_resolver({}))
    by_name = dict(rec.runs)
    assert "location" not in by_name[os.path.basename(root)]
    assert by_name["p"]["location"] == (48.86, 2.35)


def test_load_fleet_reads_each_devices_own_location(fleet, tmp_path):
    conn = fleet_db.connect(str(tmp_path))
    try:
        with fleet_db.transaction(conn):
            loc = fleet_db.add_location(conn, "Paris", 48.8566, 2.3522, "Europe/Paris")
            assert fleet_db.set_device_location(conn, fleet.dev_a.mac, loc)
    finally:
        conn.close()
    by_id = {d.id: d for d in fleet_cycle.load_fleet(str(tmp_path), NOW)}
    assert by_id[fleet.dev_a.id].location == (48.8566, 2.3522)
    assert by_id[fleet.dev_b.id].location is None
    assert by_id[fleet.live.id].location != by_id[fleet.dev_a.id].location
