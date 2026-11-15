"""Behaviour tests for two display bugs seen on the real frame:

  * a departing aircraft on its take-off roll (vertical rate inside the
    deadband) inherited "arriving" from the previous aircraft;
  * a stale adsbdb route (origin == the watched airport on an arrival)
    was shown as if it were true.

Every assertion reads the recorded history rows (what the owner sees in
the companion), never source text.
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


def _route_payload(callsign, origin, origin_city, dest, dest_city, airline="easyJet Europe"):
    def airport(iata, city):
        return {"iata_code": iata, "icao_code": "X" + iata, "municipality": city, "name": city}
    return {"response": {"flightroute": {
        "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
        "airline": {"name": airline, "icao": callsign[:3], "iata": "XX", "country": "France"},
        "origin": airport(origin, origin_city), "destination": airport(dest, dest_city)}}}


@pytest.fixture
def routes(monkeypatch):
    table = {}

    def transport(callsign, timeout=None):
        payload = table.get(callsign)
        return (200, payload) if payload else (404, None)

    monkeypatch.setattr(enrich, "default_transport", transport)
    return table


def _snapshot(hex_code, callsign, baro_rate, alt=450, gs=137.1):
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": gs, "baro_rate": baro_rate, "seen_pos": 1.0}]}


def _ground_snapshot(hex_code, callsign, gs=20.0):
    """A record on the runway pavement: the aggregator reports alt_baro as the
    string "ground" and a vertical rate of 0."""
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": "ground", "gs": gs, "baro_rate": 0, "seen_pos": 1.0}]}


def _shown(state_dir):
    """The flight and runway state the frame is currently drawing."""
    state = state_store.load_poll_state(state_dir)
    return (state.get("last_flight") or {}).get("hex"), state.get("last_confirmed_state")


def _rows(state_dir):
    with history_db.open_db(state_dir) as conn:
        return list(reversed(history_db.recent_runway_events(conn, limit=100)))


def _cycle(clock, state_dir, snapshot, advance_s=100):
    clock["t"] += advance_s
    poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)


def test_departure_on_take_off_roll_does_not_inherit_arriving(tmp_path, clock, routes):
    """An arrival, then an aircraft whose vertical rate is still ~0 (take-off
    roll) and then climbs: no event may say "arriving" for the second one."""
    state_dir = str(tmp_path)
    routes["EJU1LIN"] = _route_payload("EJU1LIN", "LIN", "Milan", "ORY", "Paris")
    routes["EJU2OPO"] = _route_payload("EJU2OPO", "ORY", "Paris", "OPO", "Porto")
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 0, alt=300, gs=90.0))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 0, alt=300, gs=90.0))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900, gs=160.0))
    second = [r for r in _rows(state_dir) if r["hex"] == "bbbbbb"]
    assert second, "the departing aircraft was never recorded"
    assert [r["confirmed_state"] for r in second] == ["departing"]


def test_arrival_with_the_watched_airport_as_origin_shows_no_route(tmp_path, clock, routes):
    """Stale rotating-callsign route ORY -> RVN on an arrival at Orly: the
    origin cannot be Orly, so no city is recorded."""
    state_dir = str(tmp_path)
    routes["TVF7950"] = _route_payload("TVF7950", "ORY", "Paris", "RVN", "Rovaniemi",
                                       airline="Transavia France")
    _cycle(clock, state_dir, _snapshot("cccccc", "TVF7950", -700))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "arriving"
    assert row["origin"] != "ORY"
    assert row["destination"] != "RVN"


def test_flight_without_route_is_recorded_cleanly(tmp_path, clock, routes):
    """A rotating-callsign flight with no adsbdb route keeps the plain
    fallback (guards the 21:59 Transavia case)."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("dddddd", "TVF1234", -700))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "arriving"
    assert not row["origin"] and not row["destination"]


def test_valid_routes_are_kept(tmp_path, clock, routes):
    """The consistency check only drops contradictions: a real arrival keeps
    its origin city and a real departure keeps its destination."""
    state_dir = str(tmp_path)
    routes["EJU1LIN"] = _route_payload("EJU1LIN", "LIN", "Milan", "ORY", "Paris")
    routes["EJU2OPO"] = _route_payload("EJU2OPO", "ORY", "Paris", "OPO", "Porto")
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800))
    arrival, departure = _rows(state_dir)
    assert (arrival["origin"], arrival["confirmed_state"]) == ("LIN", "arriving")
    assert (departure["destination"], departure["confirmed_state"]) == ("OPO", "departing")


def test_departure_with_the_watched_airport_as_destination_shows_no_route(tmp_path, clock, routes):
    state_dir = str(tmp_path)
    routes["TVF7951"] = _route_payload("TVF7951", "RVN", "Rovaniemi", "ORY", "Paris",
                                       airline="Transavia France")
    _cycle(clock, state_dir, _snapshot("eeeeee", "TVF7951", 1800))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "departing"
    assert row["destination"] != "ORY"


def test_aircraft_on_the_ground_without_a_state_does_not_blank_the_frame(tmp_path, clock, routes):
    """After an arrival, an aircraft on the pavement with no vertical rate has
    no direction to show: the arrival stays on screen instead of the frame
    falling back to the "Watching Runway" screen, and the aircraft is shown
    once it climbs."""
    state_dir = str(tmp_path)
    routes["EJU1LIN"] = _route_payload("EJU1LIN", "LIN", "Milan", "ORY", "Paris")
    routes["EJU2OPO"] = _route_payload("EJU2OPO", "ORY", "Paris", "OPO", "Porto")
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    assert _shown(state_dir) == ("aaaaaa", "arriving")

    _cycle(clock, state_dir, _ground_snapshot("bbbbbb", "EJU2OPO"))
    _cycle(clock, state_dir, _ground_snapshot("bbbbbb", "EJU2OPO", gs=90.0))
    assert _shown(state_dir) == ("aaaaaa", "arriving")

    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900, gs=160.0), advance_s=20)
    assert _shown(state_dir) == ("bbbbbb", "departing")
    assert [r["confirmed_state"] for r in _rows(state_dir) if r["hex"] == "bbbbbb"] == ["departing"]


def test_aircraft_on_the_ground_that_never_climbs_is_dropped_not_shown(tmp_path, clock, routes):
    """A landed aircraft rolling out on the pavement never produces a state:
    after the staleness limit it is discarded and the arrival stays up."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    for _ in range(3):
        _cycle(clock, state_dir, _ground_snapshot("bbbbbb", "EJU2OPO"))
    _cycle(clock, state_dir, {"ac": []}, advance_s=200)
    assert _shown(state_dir) == ("aaaaaa", "arriving")
    assert state_store.load_poll_state(state_dir).get("pending_flights") in ([], None)


def test_first_ever_aircraft_on_the_ground_waits_for_a_state(tmp_path, clock, routes):
    """With nothing on screen yet, a stateless ground aircraft is queued; the
    first aircraft that climbs is the first one drawn."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _ground_snapshot("bbbbbb", "EJU2OPO"))
    assert _shown(state_dir) == (None, None)
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900, gs=160.0))
    assert _shown(state_dir) == ("bbbbbb", "departing")
