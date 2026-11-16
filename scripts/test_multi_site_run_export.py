"""Tests for scripts/multi_site_run.py and scripts/multi_site_export.py.

Fake fetchers, runners and clocks only: no network, no sleeping, and every
directory is a pytest tmp_path.
"""
import json
import os
import sys
from datetime import datetime, timezone

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import export_api  # noqa: E402
from scripts import multi_site_export as exporter  # noqa: E402
from scripts import multi_site_run as runner_mod  # noqa: E402
from scripts import multi_site_setup as setup  # noqa: E402
from scripts import runway_compare  # noqa: E402
from server import hardware, history_db, poll_cycle, state_store, zone_fetch  # noqa: E402

FIXTURES = os.path.join(REPO_ROOT, "server", "fixtures")
GEOFENCE = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
SPECS = ["orly-b=LFPO:06/24", "cdg=LFPG:08L/26R"]
START_WALL = datetime(2026, 11, 20, 8, 0, 0, tzinfo=timezone.utc).timestamp()


class FakeTime:
    """One clock for wall time, monotonic time and sleep."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def wall(self):
        return START_WALL + self.now

    def mono(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def _fleet(tmp_path):
    root = tmp_path / "scratch"
    setup.create_scratch_fleet(str(root), [setup.parse_device(s) for s in SPECS])
    return root


class Fetcher:
    def __init__(self, fake_time):
        self.time = fake_time
        self.calls = []

    def __call__(self, ledger, lat, lon, radius_nm, **kwargs):
        self.calls.append((self.time.now, round(lat, 3)))
        aircraft = [{"hex": "39dd00", "lat": lat, "lon": lon, "n": len(self.calls)}]
        return zone_fetch.ZoneFetch((("adsbfi", aircraft),), ("adsbfi", "adsblol"), ("adsblol",))


def _noop_runner(**kwargs):
    return None


def _session(root, fake, fetcher=None, runner=_noop_runner, **kwargs):
    return runner_mod.run_session(
        str(root), fetcher=fetcher if fetcher is not None else Fetcher(fake), runner=runner,
        clock=fake.wall, monotonic=fake.mono, sleep=fake.sleep, out=lambda line: None,
        **kwargs)


def test_cycles_record_payloads_per_zone_and_respect_the_interval(tmp_path):
    root, fake = _fleet(tmp_path), FakeTime()
    fetcher = Fetcher(fake)
    lines = []
    runner_mod.run_session(
        str(root), cycles=3, interval=30, fetcher=fetcher, runner=_noop_runner,
        clock=fake.wall, monotonic=fake.mono, sleep=fake.sleep, out=lines.append)
    payload_dir = root / "payloads"
    files = sorted(os.listdir(payload_dir))
    assert len(files) == 2 and all(name.endswith(".jsonl") for name in files)
    for name in files:
        records = [json.loads(line) for line in (payload_dir / name).read_text().splitlines()]
        assert len(records) == 3
        record = records[0]
        assert set(record) >= {"ts", "zone_key", "lat", "lon", "radius_nm", "results",
                               "queried", "failed"}
        assert record["results"]["adsbfi"][0]["hex"] == "39dd00"
        assert record["queried"] == ["adsbfi", "adsblol"] and record["failed"] == ["adsblol"]
        assert name[:-len(".jsonl")] == runner_mod.zone_file_stem(record["zone_key"])
    starts = sorted({t for t, _ in fetcher.calls})
    assert len(starts) == 3
    assert all(b - a >= 30 for a, b in zip(starts, starts[1:]))
    assert len(lines) == 3 and "payload" not in lines[0]


def test_recording_wrapper_returns_the_inner_result_unchanged(tmp_path):
    inner_result = zone_fetch.ZoneFetch((("adsbfi", [{"hex": "a"}]),), ("adsbfi",), ())
    wrapped = runner_mod.recording_fetcher(
        str(tmp_path), lambda *a, **k: inner_result, clock=lambda: START_WALL)
    assert wrapped(None, 48.7, 2.4, 10.0) is inner_result


def test_interval_floor_is_enforced(tmp_path):
    root, fake = _fleet(tmp_path), FakeTime()
    with pytest.raises(ValueError):
        _session(root, fake, cycles=1, interval=29.9)
    assert runner_mod.main(["--root", str(root), "--cycles", "1", "--interval", "10"]) == 2
    assert not (root / "payloads").exists()


def test_refuses_roots_without_the_marker_and_the_default_root(tmp_path, monkeypatch):
    fake = FakeTime()
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(setup.ScratchRootError):
        _session(plain, fake, cycles=1)
    assert os.listdir(plain) == []
    assert runner_mod.main(["--root", str(plain), "--cycles", "1"]) == 2
    marked = tmp_path / "marked"
    marked.mkdir()
    (marked / setup.MARKER_FILENAME).write_text("x")
    monkeypatch.setattr(state_store, "DEFAULT_STATE_DIR", str(marked))
    with pytest.raises(setup.ScratchRootError):
        _session(marked, fake, cycles=1)


def test_simulation_flag_is_set_only_while_running_and_restored(tmp_path, monkeypatch):
    root, fake = _fleet(tmp_path), FakeTime()
    seen = []

    def runner(**kwargs):
        seen.append(os.environ.get(hardware.SIM_ENV_VAR))

    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    _session(root, fake, runner=runner, cycles=1)
    assert "1" in seen
    assert hardware.SIM_ENV_VAR not in os.environ
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "0")
    _session(root, fake, runner=runner, cycles=1)
    assert os.environ[hardware.SIM_ENV_VAR] == "0"

    def failing(**kwargs):
        raise RuntimeError("boom")

    _session(root, fake, runner=failing, cycles=1)
    assert os.environ[hardware.SIM_ENV_VAR] == "0"


def test_stop_file_ends_the_session_after_the_current_cycle(tmp_path):
    root, fake = _fleet(tmp_path), FakeTime()
    stop = tmp_path / "stop"
    calls = []

    def runner(**kwargs):
        calls.append(kwargs["state_dir"])
        stop.write_text("")

    done = _session(root, fake, runner=runner, cycles=10, stop_file=str(stop))
    assert done == 1
    assert calls
    assert fake.sleeps == []


def test_until_bounds_the_session(tmp_path):
    root, fake = _fleet(tmp_path), FakeTime()
    until = datetime.fromtimestamp(START_WALL + 70, tz=timezone.utc)
    assert _session(root, fake, until=until, interval=30) == 3


def test_a_cycle_count_or_an_end_time_is_required(tmp_path):
    root, fake = _fleet(tmp_path), FakeTime()
    with pytest.raises(ValueError):
        _session(root, fake)


def _seeded_device(tmp_path):
    """A scratch device whose history.db was written by a real poll cycle."""
    root = _fleet(tmp_path)
    device = next(
        d for d in _devices(root) if d.name == "orly-b")
    with open(os.path.join(FIXTURES, "geofence_multi_aircraft.json")) as handle:
        snapshot = json.load(handle)
    poll_cycle.run_once(
        snapshot=snapshot, state_dir=device.state_dir, geofence=GEOFENCE,
        profile=hardware.get_profile(hardware.SIM_CLONE_KEY, {hardware.SIM_ENV_VAR: "1"}))
    conn = history_db.connect(device.state_dir)
    try:
        history_db.record_runway_event(
            conn, ts="2026-11-20T08:00:00+00:00", hex="39dd00", callsign="TVF87XA",
            aircraft_type="A20N", confirmed_state="arriving", corroborated="True",
            route_source="fresh_hit", airline="Transavia France", origin="NTE",
            destination="ORY", tracked_runway="06-24", gallery_name="x.png")
    finally:
        conn.close()
    return root, device


def _devices(root):
    return exporter.scratch_devices(str(root))


SINCE = "2000-01-01T00:00:00Z"


def test_export_is_byte_identical_to_the_companion_rendering(tmp_path):
    root, device = _seeded_device(tmp_path)
    out = tmp_path / "out"
    manifest = exporter.export_devices(str(root), device.id, SINCE, str(out))
    target = out / device.id
    for route, name in ((export_api.FLIGHTS_ROUTE, "runway_events.jsonl"),
                        (export_api.POLL_CYCLES_ROUTE, "poll_cycles.jsonl")):
        columns, reader = export_api._LINE_EXPORTS[route]
        rows = reader(device.state_dir, SINCE, export_api.MAX_ROWS)
        expected = export_api._render_lines(rows, columns)
        assert expected, name
        assert (target / name).read_bytes() == expected
        assert manifest[device.id]["files"][name]["rows"] == len(rows)
    saved = json.loads((target / "MANIFEST.json").read_text())
    assert saved["files"]["runway_events.jsonl"]["route"] == export_api.FLIGHTS_ROUTE
    assert len(saved["files"]["poll_cycles.jsonl"]["sha256"]) == 64


def test_export_never_creates_a_missing_database(tmp_path):
    root = _fleet(tmp_path)
    device = _devices(root)[0]
    with pytest.raises(exporter.ExportError):
        exporter.export_devices(str(root), device.id, SINCE, str(tmp_path / "out"))
    assert not os.path.exists(history_db.history_db_path(device.state_dir))
    assert exporter.main(
        ["--root", str(root), "--device", device.id, "--since", SINCE,
         "--out", str(tmp_path / "out2")]) == 2


def test_export_refuses_to_overwrite_and_bad_arguments(tmp_path):
    root, device = _seeded_device(tmp_path)
    out = tmp_path / "out"
    exporter.export_devices(str(root), device.id, SINCE, str(out))
    with pytest.raises(FileExistsError):
        exporter.export_devices(str(root), device.id, SINCE, str(out))
    with pytest.raises(exporter.ExportError):
        exporter.export_devices(str(root), "../../etc", SINCE, str(tmp_path / "o3"))
    with pytest.raises(exporter.ExportError):
        exporter.export_devices(str(root), "d_00000000", SINCE, str(tmp_path / "o4"))
    with pytest.raises(exporter.ExportError):
        exporter.export_devices(str(root), device.id, "yesterday", str(tmp_path / "o5"))


def test_all_exports_every_scratch_device_and_skips_missing_history(tmp_path):
    root, device = _seeded_device(tmp_path)
    out = tmp_path / "out"
    manifest = exporter.export_devices(str(root), "all", SINCE, str(out), skip_missing=True)
    assert list(manifest) == [device.id]


def test_run_compare_reads_a_device_export_unchanged(tmp_path):
    root, device = _seeded_device(tmp_path)
    out = tmp_path / "out"
    exporter.export_devices(str(root), device.id, SINCE, str(out))
    report = runway_compare.analyse(str(out / device.id), runway_compare.NO_ROUTE_MIN_DAYS)
    assert report["coverage"]["runway_events"]["rows"] == 1
