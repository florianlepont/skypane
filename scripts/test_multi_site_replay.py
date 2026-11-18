"""Tests for scripts/multi_site_replay.py: a recorded session (the raw provider
answers kept by multi_site_run.py) is replayed through the unchanged fleet
cycle on a fresh scratch root. Fake clock and a route table read from the
recorded adsbdb cache: no network, no sleeping, every directory a tmp_path.
"""
import os
import shutil
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import multi_site_replay as replay  # noqa: E402
from scripts import multi_site_run as runner_mod  # noqa: E402
from scripts import multi_site_setup as setup  # noqa: E402
from server import history_db  # noqa: E402

FIXTURES = os.path.join(REPO_ROOT, "scripts", "fixtures")
PAYLOADS = os.path.join(FIXTURES, "nantes_tvf63nb_payloads.jsonl")
ROUTES = os.path.join(FIXTURES, "nantes_tvf63nb_routes.json")
SPEC = "NTE=LFRS:03/21"


def _source(tmp_path):
    """A recorded session: the payloads of one real take-off at Nantes."""
    source = tmp_path / "source"
    (source / "payloads").mkdir(parents=True)
    shutil.copy(PAYLOADS, source / "payloads" / "zone.jsonl")
    shutil.copy(ROUTES, source / "adsbdb_shared_cache.json")
    return source


def _events(out_root):
    device = setup_devices(out_root)[0]
    with history_db.open_db(device) as conn:
        return list(reversed(history_db.recent_runway_events(conn, limit=100)))


def setup_devices(out_root):
    base = os.path.join(out_root, "devices")
    return [os.path.join(base, name) for name in sorted(os.listdir(base))]


def test_a_recorded_take_off_is_replayed_with_its_route(tmp_path):
    out = tmp_path / "replayed"
    done = replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    assert done == 7
    rows = [r for r in _events(str(out)) if r["hex"] == "39ceb3"]
    assert [(r["callsign"], r["confirmed_state"], r["origin"], r["destination"]) for r in rows] == [
        ("TVF63NB", "departing", "NTE", "DSS")]


def test_the_replayed_events_carry_the_recorded_times(tmp_path):
    out = tmp_path / "replayed"
    replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    (row,) = [r for r in _events(str(out)) if r["hex"] == "39ceb3"]
    assert row["ts"].startswith("2026-11-17T09:2")


def test_the_replay_never_reaches_the_network(tmp_path, monkeypatch):
    import server.plane.enrich as enrich

    def refuse(*args, **kwargs):
        raise AssertionError("the replay made a route request")

    monkeypatch.setattr(enrich, "default_transport", refuse)
    out = tmp_path / "replayed"
    replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    assert _events(str(out))


def test_a_route_missing_from_the_recorded_cache_is_a_miss_not_a_request(tmp_path):
    source = _source(tmp_path)
    (source / "adsbdb_shared_cache.json").write_text("{}")
    out = tmp_path / "replayed"
    replay.replay_session(str(source), str(out), [setup.parse_device(SPEC)])
    (row,) = [r for r in _events(str(out)) if r["hex"] == "39ceb3"]
    assert not row["origin"] and not row["destination"]


def test_the_cycles_follow_the_recorded_times(tmp_path):
    cycles = replay.read_cycles(str(_source(tmp_path)))
    stamps = [c["ts"] for c in cycles]
    assert stamps == sorted(stamps) and len(stamps) == 7


def test_refuses_an_existing_output_root_and_a_source_without_payloads(tmp_path):
    out = tmp_path / "replayed"
    out.mkdir()
    with pytest.raises(replay.ReplayError):
        replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(replay.ReplayError):
        replay.replay_session(str(empty), str(tmp_path / "fresh"), [setup.parse_device(SPEC)])
    assert replay.main(["--source", str(empty), "--out", str(tmp_path / "fresh2"),
                        "--device", SPEC]) == 2


def test_the_replay_has_the_scratch_marker_and_is_not_the_default_root(tmp_path):
    out = tmp_path / "replayed"
    replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    runner_mod.require_scratch_root(str(out))


def test_the_replay_never_asks_the_vrs_standing_data(tmp_path, monkeypatch):
    import server.plane.enrich as enrich

    asked = []

    def record(key, timeout=None):
        asked.append(key)
        return 404, None

    monkeypatch.setattr(enrich, "default_vrs_transport", record)
    out = tmp_path / "replayed"
    replay.replay_session(str(_source(tmp_path)), str(out), [setup.parse_device(SPEC)])
    assert asked == []
    (row,) = [r for r in _events(str(out)) if r["hex"] == "39ceb3"]
    assert (row["origin"], row["destination"]) == ("NTE", "DSS")
