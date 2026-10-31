"""Pipeline-level proof that selection, zone and frame text follow one
per-device detection spec, and that the live Orly frame behaves the same
whether its geometry comes from the generated document or the legacy file."""

import hashlib
import json
import math
import os
import sqlite3

import pytest

import server.device_config as device_config
import server.plane.enrich as enrich
import server.poll_cycle as poll_cycle
from server import detection
from server.plane import detect

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_FILE = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
LEGACY_IDS = ("3", "06-24", "02-20")
POSITION_ORIGIN = (48.86, 2.35)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


def _doc(display_id):
    return detection.spec_for({"tracked_runway": display_id}).geofence


def _on_final(doc, display_id, hex_code, along_m=-1500.0, alt_ft=600, track_offset=0.0):
    """An arriving record on the extended centreline of `display_id`."""
    axis = detect.runway_axis(doc, runway_id=display_id)
    x = along_m * axis["ux"]
    y = along_m * axis["uy"]
    track = math.degrees(math.atan2(axis["ux"], axis["uy"])) % 360.0
    return {
        "hex": hex_code,
        "flight": "TST%s " % hex_code[-3:],
        "t": "A320",
        "lat": axis["lat0"] + y / detect._M_PER_DEG_LAT,
        "lon": axis["lon0"] + x / axis["lon_scale"],
        "alt_baro": alt_ft,
        "baro_rate": -700,
        "gs": 140,
        "track": track + track_offset,
        "seen_pos": 0.4,
    }


def _write_config(state_dir, **kwargs):
    os.makedirs(state_dir, exist_ok=True)
    device_config.save_device_config(str(state_dir), **kwargs)


def _run(state_dir, snapshot, **kwargs):
    kwargs.setdefault("geofence", LEGACY_FILE)
    return poll_cycle.run_once(snapshot=snapshot, state_dir=str(state_dir), **kwargs)


def _panel_hash(state_dir):
    with open(os.path.join(str(state_dir), "panel.bin"), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _poll_state_keys(state_dir):
    with open(os.path.join(str(state_dir), "poll_state.json")) as fh:
        return sorted(json.load(fh))


def _strip(flight):
    return None if flight is None else {k: v for k, v in flight.items() if k != "seen_pos"}


def _legacy_snapshot(display_id):
    """A low aircraft the legacy Orly document admits for `display_id`.

    The hand-tuned bounding box clips the corridor, so the along-track
    position is searched until the legacy file itself accepts the record.
    """
    legacy = detect.load_geofence(LEGACY_FILE)
    for along in (-1500.0, -800.0, 0.0, 800.0, 1500.0, 2500.0):
        record = _on_final(_doc(display_id), display_id, "3c6001", along_m=along)
        if detect.runway_candidates([record], legacy, display_id):
            return {"ac": [record]}
    raise AssertionError("no admitted position for " + display_id)


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_pipeline_generic_equals_legacy(tmp_path, monkeypatch, runway_id):
    snapshot = _legacy_snapshot(runway_id)
    outcomes = {}
    for label, kill_switch in (("generic", None), ("legacy", "1")):
        state_dir = tmp_path / label
        _write_config(state_dir, tracked_runway=runway_id)
        if kill_switch:
            monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, kill_switch)
        else:
            monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
        result = _run(state_dir, snapshot)
        outcomes[label] = (result, _panel_hash(state_dir), _poll_state_keys(state_dir))
    generic, legacy = outcomes["generic"], outcomes["legacy"]
    assert generic[0]["flight"] is not None
    assert _strip(generic[0]["flight"]) == _strip(legacy[0]["flight"])
    assert {k: v for k, v in generic[0].items() if k != "flight"} == (
        {k: v for k, v in legacy[0].items() if k != "flight"})
    assert generic[0]["tracked_runway"] == runway_id
    assert generic[1] == legacy[1]
    assert generic[2] == legacy[2]


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_pipeline_generic_equals_legacy_when_nothing_is_there(tmp_path, monkeypatch, runway_id):
    hashes = []
    for label, kill_switch in (("generic", None), ("legacy", "1")):
        state_dir = tmp_path / label
        _write_config(state_dir, tracked_runway=runway_id)
        if kill_switch:
            monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, kill_switch)
        else:
            monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)
        result = _run(state_dir, {"ac": []})
        assert result["flight"] is None
        hashes.append((_panel_hash(state_dir), _poll_state_keys(state_dir), result["tracked_runway"]))
    assert hashes[0] == hashes[1]


def _cdg_snapshot():
    doc = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}}).geofence
    return {"ac": [_on_final(doc, "LFPG:08L/26R", "3c6cd1", along_m=-1800.0, alt_ft=900)]}


def test_pipeline_cdg_runway_isolation(tmp_path):
    snapshot = _cdg_snapshot()
    on = tmp_path / "on"
    off = tmp_path / "off"
    _write_config(on, detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    _write_config(off, detection={"mode": "runway", "airport": "LFPG", "runway": "08R/26L"})
    selected = _run(on, snapshot)
    other = _run(off, snapshot)
    assert selected["flight"] is not None
    assert selected["flight"]["hex"] == "3c6cd1"
    assert selected["tracked_runway"] == "LFPG:08L/26R"
    assert other["flight"] is None
    assert other["tracked_runway"] == "LFPG:08R/26L"


def test_pipeline_cdg_device_never_selects_an_orly_runway_aircraft(tmp_path):
    orly = _legacy_snapshot("3")
    state_dir = tmp_path / "cdg"
    _write_config(state_dir, detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    assert _run(state_dir, orly)["flight"] is None


def _position_aircraft(hex_code, dlat, alt_ft, rate=-600):
    return {
        "hex": hex_code, "flight": "POS%s " % hex_code[-3:], "t": "A320",
        "lat": POSITION_ORIGIN[0] + dlat, "lon": POSITION_ORIGIN[1],
        "alt_baro": alt_ft, "baro_rate": rate, "gs": 150, "track": 90, "seen_pos": 0.4,
    }


def test_pipeline_position_selects_lowest(tmp_path):
    state_dir = tmp_path / "pos"
    _write_config(state_dir, detection={"mode": "position", "radius_km": 9})
    snapshot = {"ac": [
        _position_aircraft("aaa111", 0.02, 4500),
        _position_aircraft("bbb222", 0.03, 2200),
        _position_aircraft("ccc333", 0.30, 800),
        _position_aircraft("ddd444", 0.01, 12000),
    ]}
    result = _run(state_dir, snapshot, location=POSITION_ORIGIN)
    assert result["flight"]["hex"] == "bbb222"
    assert result["tracked_runway"] == "position:9"


def test_pipeline_position_adds_no_new_poll_state(tmp_path):
    runway_dir = tmp_path / "runway"
    pos_dir = tmp_path / "pos"
    _write_config(runway_dir, tracked_runway="3")
    _write_config(pos_dir, detection={"mode": "position", "radius_km": 9})
    level_dir = tmp_path / "level"
    _write_config(level_dir, detection={"mode": "position", "radius_km": 9})
    _run(runway_dir, _legacy_snapshot("3"))
    descending = _position_aircraft("eee555", 0.02, 2500)
    _run(pos_dir, {"ac": [descending]}, location=POSITION_ORIGIN)
    assert _poll_state_keys(pos_dir) == _poll_state_keys(runway_dir)
    cruiser = _position_aircraft("fff666", 0.02, 3000, rate=0)
    _run(level_dir, {"ac": [cruiser]}, location=POSITION_ORIGIN)
    assert set(_poll_state_keys(level_dir)) <= set(_poll_state_keys(runway_dir))


def test_pipeline_position_without_location_shows_set_location_and_never_fetches(
        monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("an ADS-B fetch was attempted")

    monkeypatch.setattr(poll_cycle.zone_fetch, "fetch_zone", forbidden)
    state_dir = tmp_path / "pos"
    _write_config(state_dir, detection={"mode": "position", "radius_km": 9})
    reference = tmp_path / "ref"
    reference.mkdir()
    poll_cycle.run_once(snapshot={"ac": []}, state_dir=str(reference), geofence=LEGACY_FILE)
    for location in (None, (40.7128, -74.006)):
        result = poll_cycle.run_once(state_dir=str(state_dir), geofence=LEGACY_FILE, location=location)
        assert result["tracked_runway"] == detection.NO_LOCATION_DISPLAY_ID
        assert result["flight"] is None
        assert result["state"] == "empty"
        assert _panel_hash(state_dir) != _panel_hash(reference)


def test_pipeline_no_location_screen_text_and_history(tmp_path):
    state_dir = tmp_path / "pos"
    _write_config(state_dir, detection={"mode": "position", "radius_km": 9})
    poll_cycle.run_once(state_dir=str(state_dir), geofence=LEGACY_FILE, location=None)
    spec = detection.spec_for(device_config.load_device_config(str(state_dir)), None)
    assert spec.empty_heading == "Set a location"
    assert spec.tag_text == "SET A LOCATION"
    render = poll_cycle.render
    assert render.style.empty_body_lines(spec.display_id) == render.style.NO_LOCATION_BODY_LINES
    assert render.style.empty_body_lines("3") == render.EMPTY_BODY_LINES
    assert render.empty_heading_text(spec.display_id) == "Set a location"
    conn = sqlite3.connect(os.path.join(str(state_dir), "history.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM runway_events WHERE tracked_runway = '3'").fetchone()[0] == 0
    finally:
        conn.close()


def test_pipeline_leaving_no_location_repaints_the_live_board(tmp_path):
    state_dir = tmp_path / "pos"
    _write_config(state_dir, detection={"mode": "position", "radius_km": 9})
    poll_cycle.run_once(state_dir=str(state_dir), geofence=LEGACY_FILE, location=None)
    shown = _panel_hash(state_dir)
    poll_cycle.run_once(
        snapshot={"ac": []}, state_dir=str(state_dir), geofence=LEGACY_FILE,
        location=(48.86, 2.35))
    assert _panel_hash(state_dir) != shown
    assert "no_location_active" not in json.load(open(os.path.join(str(state_dir), "poll_state.json")))


def test_pipeline_runs_without_the_legacy_geofence_file(tmp_path):
    state_dir = tmp_path / "live"
    _write_config(state_dir, tracked_runway="3")
    result = _run(state_dir, _legacy_snapshot("3"), geofence=str(tmp_path / "missing.json"))
    assert result["flight"] is not None
