"""Every aircraft the poll cycle detects leaves a record, even when the
display queue drops it before it is drawn, and the queue serves the aircraft
seen last.

Every assertion reads history.db or poll_state.json, never source text.
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.history_db as history_db  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.state_store as state_store  # noqa: E402

GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
CLOCK_BASE = 1_700_000_000.0


@pytest.fixture
def clock(monkeypatch):
    fake = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: fake["t"])
    return fake


def _snapshot(hex_code, callsign, baro_rate, alt=450):
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": 137.1, "baro_rate": baro_rate, "seen_pos": 1.0}]}


def _cycle(clock, state_dir, snapshot, advance_s=100):
    clock["t"] += advance_s
    poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)


def _rows(state_dir):
    with history_db.open_db(state_dir) as conn:
        return list(reversed(history_db.recent_runway_events(conn, limit=100)))


def _shown(state_dir):
    return (state_store.load_poll_state(state_dir).get("last_flight") or {}).get("hex")


def _queued(state_dir):
    return [e["flight"]["hex"] for e in state_store.load_poll_state(state_dir).get("pending_flights", [])]


def test_an_aircraft_dropped_unseen_leaves_a_row_with_what_was_known(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF87XA", 1800, alt=900), advance_s=10)
    assert _queued(state_dir) == ["bbbbbb"]
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    assert _queued(state_dir) == []
    assert _shown(state_dir) == "aaaaaa"
    dropped = [r for r in _rows(state_dir) if r["hex"] == "bbbbbb"]
    assert len(dropped) == 1
    (row,) = dropped
    assert (row["callsign"], row["confirmed_state"], row["gallery_name"]) == ("TVF87XA", "departing", "")
    assert row["route_source"] in ("airline_only", "manual", "miss")
    assert not row["origin"] and not row["destination"]
    assert row["tracked_runway"] == "3"


def test_a_drawn_aircraft_is_not_also_recorded_as_dropped(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF2BB", 1800, alt=900), advance_s=100)
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    assert [r["hex"] for r in _rows(state_dir)].count("aaaaaa") == 1
    assert [r["hex"] for r in _rows(state_dir)].count("bbbbbb") == 1


def test_the_same_pass_recorded_twice_within_the_window_is_stored_once(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        first = history_db.record_unshown_event(conn, "2026-11-15T10:00:00+00:00", hex="bbbbbb", callsign="TVF87XA")
        again = history_db.record_unshown_event(conn, "2026-11-15T10:20:00+00:00", hex="bbbbbb", callsign="TVF87XA")
        later = history_db.record_unshown_event(conn, "2026-11-15T10:31:00+00:00", hex="bbbbbb", callsign="TVF87XA")
        other = history_db.record_unshown_event(conn, "2026-11-15T10:01:00+00:00", hex="cccccc", callsign="TVF1CC")
        stored = [(r["hex"], r["ts"], r["gallery_name"]) for r in reversed(history_db.recent_runway_events(conn))]
    assert (first, again, later, other) == (1, 0, 1, 1)
    assert stored == [
        ("bbbbbb", "2026-11-15T10:00:00+00:00", ""),
        ("cccccc", "2026-11-15T10:01:00+00:00", ""),
        ("bbbbbb", "2026-11-15T10:31:00+00:00", ""),
    ]


def test_an_unshown_event_for_an_unreadable_time_is_still_stored(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        assert history_db.record_unshown_event(conn, "not a time", hex="bbbbbb") == 1


def test_a_drawn_aircraft_seen_again_after_a_drop_gets_its_own_row(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF87XA", 1800, alt=900), advance_s=10)
    _cycle(clock, state_dir, {"ac": []}, advance_s=200)
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF87XA", 1800, alt=900), advance_s=10)
    assert _shown(state_dir) == "bbbbbb"
    assert [r["hex"] for r in _rows(state_dir)].count("bbbbbb") == 2


def test_aircraft_evicted_by_the_depth_cap_are_recorded(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("a00000", "TVF0AA", -700))
    for index in range(1, 9):
        _cycle(clock, state_dir, _snapshot("b%05d" % index, "TVF%dBB" % index, 1800, alt=900), advance_s=10)
    assert len(_queued(state_dir)) == poll_cycle.MAX_PENDING_FLIGHTS
    recorded = {r["hex"] for r in _rows(state_dir)}
    assert {"b00001", "b00002", "b00003"} <= recorded
    assert not {"b00006", "b00007", "b00008"} & recorded


def test_the_aircraft_seen_last_is_drawn_when_the_display_can_advance(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF2BB", 1800, alt=900), advance_s=20)
    _cycle(clock, state_dir, _snapshot("cccccc", "TVF3CC", 1800, alt=900), advance_s=20)
    assert _queued(state_dir) == ["bbbbbb", "cccccc"]
    _cycle(clock, state_dir, {"ac": []}, advance_s=60)
    assert _shown(state_dir) == "cccccc"
    assert _queued(state_dir) == ["bbbbbb"]
    _cycle(clock, state_dir, {"ac": []}, advance_s=200)
    assert _queued(state_dir) == []
    assert [r["hex"] for r in _rows(state_dir)].count("bbbbbb") == 1


def test_recording_a_dropped_aircraft_never_fails_the_cycle(tmp_path, clock, monkeypatch):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF2BB", 1800, alt=900), advance_s=10)

    def broken(conn, **fields):
        raise OSError("disk full")

    monkeypatch.setattr(history_db, "record_unshown_event", broken)
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    assert _shown(state_dir) == "aaaaaa"
    assert [r["hex"] for r in _rows(state_dir)] == ["aaaaaa"]


def _route_payload(callsign, origin, dest):
    def airport(iata):
        return {"iata_code": iata, "icao_code": "X" + iata, "municipality": iata, "name": iata}
    return {"response": {"flightroute": {
        "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
        "airline": {"name": "easyJet Europe", "icao": callsign[:3], "iata": "XX", "country": "France"},
        "origin": airport(origin), "destination": airport(dest)}}}


@pytest.fixture
def routes(monkeypatch):
    table = {}

    def transport(callsign, timeout=None):
        payload = table.get(callsign)
        return (200, payload) if payload else (404, None)

    monkeypatch.setattr(enrich, "default_transport", transport)
    return table


def _drop_second_aircraft(clock, state_dir, callsign, hex_code="bbbbbb"):
    """A first aircraft on screen, a second one queued behind it with a level
    vertical rate (no direction of its own), then dropped unseen."""
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot(hex_code, callsign, 0, alt=450), advance_s=10)
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    (row,) = [r for r in _rows(state_dir) if r["hex"] == hex_code]
    return row


def test_a_dropped_aircraft_gets_its_route_and_the_direction_the_route_gives(
        tmp_path, clock, routes):
    """Recorded at Lyon: a departure queued behind another one and dropped
    unseen had no route and no direction. adsbdb gives ORY -> OPO: the watched
    airport is the origin, so it is a departure."""
    routes["EJU2OPO"] = _route_payload("EJU2OPO", "ORY", "OPO")
    row = _drop_second_aircraft(clock, str(tmp_path), "EJU2OPO")
    assert (row["origin"], row["destination"]) == ("ORY", "OPO")
    assert row["confirmed_state"] == "departing"
    assert row["route_source"] == "fresh_hit"
    assert row["gallery_name"] == ""


def test_a_dropped_arrival_gets_arriving_from_its_route(tmp_path, clock, routes):
    routes["EJU1LIN"] = _route_payload("EJU1LIN", "LIN", "ORY")
    row = _drop_second_aircraft(clock, str(tmp_path), "EJU1LIN")
    assert (row["origin"], row["destination"], row["confirmed_state"]) == ("LIN", "ORY", "arriving")


def test_a_dropped_aircraft_whose_route_excludes_the_watched_airport_keeps_no_route(
        tmp_path, clock, routes):
    routes["EZY9448"] = _route_payload("EZY9448", "BFS", "BRS")
    row = _drop_second_aircraft(clock, str(tmp_path), "EZY9448")
    assert not row["origin"] and not row["destination"]
    assert row["confirmed_state"] in (None, "")


def test_a_dropped_aircraft_with_its_own_direction_keeps_it_when_the_route_agrees(
        tmp_path, clock, routes):
    routes["TVF87XA"] = _route_payload("TVF87XA", "ORY", "OPO")
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "TVF1AA", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "TVF87XA", 1800, alt=900), advance_s=10)
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    (row,) = [r for r in _rows(state_dir) if r["hex"] == "bbbbbb"]
    assert (row["confirmed_state"], row["origin"], row["destination"]) == ("departing", "ORY", "OPO")
