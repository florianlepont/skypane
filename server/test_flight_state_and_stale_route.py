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


def _rows(state_dir):
    with history_db.open_db(state_dir) as conn:
        return list(reversed(history_db.recent_runway_events(conn, limit=100)))


def _cycle(clock, state_dir, snapshot, advance_s=100):
    clock["t"] += advance_s
    poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)


@pytest.mark.xfail(strict=True, reason="a new aircraft inherits the previous aircraft's state")
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


@pytest.mark.xfail(strict=True, reason="a route contradicting the arrival is displayed")
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
