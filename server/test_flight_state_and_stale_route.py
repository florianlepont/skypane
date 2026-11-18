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
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 0, alt=300, gs=90.0), advance_s=40)
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 0, alt=300, gs=90.0), advance_s=40)
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900, gs=160.0), advance_s=40)
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


def _approach(hex_code, callsign, alt):
    """An aircraft on final approach whose vertical rate is not reported."""
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": 140.0, "seen_pos": 1.0}]}


def _departure_roll(hex_code, callsign, alt):
    """An aircraft climbing out whose vertical rate reads level."""
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": 150.0, "baro_rate": 0, "seen_pos": 1.0}]}


def test_arrival_without_a_vertical_rate_takes_its_direction_from_the_altitude(tmp_path, clock, routes):
    """The frame is never blanked for a detected aircraft: with no vertical
    rate, its falling altitude says it is arriving once it has been seen twice."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _approach("aaaaaa", "EJU1LIN", 1200))
    assert _shown(state_dir) == (None, None)
    _cycle(clock, state_dir, _approach("aaaaaa", "EJU1LIN", 1000), advance_s=30)
    assert _shown(state_dir) == ("aaaaaa", "arriving")
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "arriving"


def test_departure_with_a_level_vertical_rate_takes_its_direction_from_the_altitude(tmp_path, clock, routes):
    """Right after an arrival, a climbing aircraft whose vertical rate reads 0
    is shown as departing, never as the previous arrival's direction."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    _cycle(clock, state_dir, _departure_roll("bbbbbb", "EJU2OPO", 400))
    assert _shown(state_dir) == ("aaaaaa", "arriving")
    _cycle(clock, state_dir, _departure_roll("bbbbbb", "EJU2OPO", 650), advance_s=40)
    assert _shown(state_dir) == ("bbbbbb", "departing")
    assert [r["confirmed_state"] for r in _rows(state_dir) if r["hex"] == "bbbbbb"] == ["departing"]


def test_aircraft_whose_altitude_does_not_move_keeps_the_current_flight(tmp_path, clock, routes):
    """No rate and a flat altitude give no direction: the arrival stays on
    screen and the aircraft is dropped once stale."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    for _ in range(3):
        _cycle(clock, state_dir, _approach("bbbbbb", "EJU2OPO", 600), advance_s=60)
    assert _shown(state_dir) == ("aaaaaa", "arriving")
    _cycle(clock, state_dir, {"ac": []}, advance_s=200)
    assert _shown(state_dir) == ("aaaaaa", "arriving")
    assert state_store.load_poll_state(state_dir).get("pending_flights") in ([], None)


def test_altitude_reference_survives_a_restart_between_cycles(tmp_path, clock, routes):
    """Every cycle is a fresh process: the first altitude must come back from
    poll_state.json, and the refreshed record of the shown aircraft keeps it."""
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _approach("aaaaaa", "EJU1LIN", 1200))
    reference = [e["flight"]["altitude_ref_ft"] for e in state_store.load_poll_state(state_dir)["pending_flights"]]
    assert reference == [1200.0]
    _cycle(clock, state_dir, _approach("aaaaaa", "EJU1LIN", 1000), advance_s=30)
    assert state_store.load_poll_state(state_dir)["last_flight"]["altitude_ref_ft"] == 1200.0
    _cycle(clock, state_dir, _approach("aaaaaa", "EJU1LIN", 800), advance_s=30)
    assert state_store.load_poll_state(state_dir)["last_flight"]["altitude_ref_ft"] == 1200.0


def test_arrival_whose_route_does_not_end_at_the_watched_airport_shows_no_route(
        tmp_path, clock, routes):
    """Recorded at Nantes: easyJet callsign EZS1345 resolved to GVA -> LRH
    for an arrival. The route has neither end at the watched airport, so it
    belongs to another leg of that callsign and no city is recorded."""
    state_dir = str(tmp_path)
    routes["EZS1345"] = _route_payload("EZS1345", "GVA", "Geneva", "LRH", "La Rochelle")
    _cycle(clock, state_dir, _snapshot("ffffff", "EZS1345", -700))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "arriving"
    assert not row["origin"] and not row["destination"]


def test_departure_whose_route_does_not_start_at_the_watched_airport_shows_no_route(
        tmp_path, clock, routes):
    """Recorded at Nantes: EZY9448 resolved to BFS -> BRS for a departure."""
    state_dir = str(tmp_path)
    routes["EZY9448"] = _route_payload("EZY9448", "BFS", "Belfast", "BRS", "Bristol")
    _cycle(clock, state_dir, _snapshot("999999", "EZY9448", 1800))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "departing"
    assert not row["origin"] and not row["destination"]


def test_route_with_a_missing_end_is_kept_when_the_other_end_is_the_watched_airport(
        tmp_path, clock, routes):
    """Only a route that excludes the watched airport is dropped: one whose
    other end is unknown stays as long as it is consistent."""
    state_dir = str(tmp_path)
    routes["EJU3XXX"] = _route_payload("EJU3XXX", "LIN", "Milan", "ORY", "Paris")
    _cycle(clock, state_dir, _snapshot("abcabc", "EJU3XXX", -700))
    (row,) = _rows(state_dir)
    assert row["origin"] == "LIN"


def _ground_roll_snapshot(hex_code, callsign, baro_rate):
    """A record on the runway pavement reporting a small positive vertical
    rate while rolling out after touchdown."""
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": "ground", "gs": 60.0, "baro_rate": baro_rate, "seen_pos": 1.0}]}


def test_landing_roll_out_with_a_positive_vertical_rate_stays_an_arrival(
        tmp_path, clock, routes):
    """Recorded at Roissy: KAL901 (B777) descends, lands, and one minute later
    the pavement record reports +320 ft/min. The aircraft is still the one that
    just landed: no 'departing' event may follow its arrival."""
    state_dir = str(tmp_path)
    routes["KAL901"] = _route_payload("KAL901", "ICN", "Seoul", "ORY", "Paris", airline="Korean Air")
    _cycle(clock, state_dir, _snapshot("71c009", "KAL901", -640, alt=1400))
    _cycle(clock, state_dir, _snapshot("71c009", "KAL901", -896, alt=1150), advance_s=30)
    _cycle(clock, state_dir, _ground_roll_snapshot("71c009", "KAL901", 320), advance_s=30)
    _cycle(clock, state_dir, _ground_roll_snapshot("71c009", "KAL901", 320), advance_s=30)
    states = [r["confirmed_state"] for r in _rows(state_dir) if r["hex"] == "71c009"]
    assert states and set(states) == {"arriving"}


def test_take_off_with_a_positive_vertical_rate_still_departs_after_a_landing(
        tmp_path, clock, routes):
    """The landing roll-out rule never blocks a real take-off: once the
    aircraft is airborne and climbing, it is a departure."""
    state_dir = str(tmp_path)
    routes["EJU2OPO"] = _route_payload("EJU2OPO", "ORY", "Paris", "OPO", "Porto")
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900))
    (row,) = _rows(state_dir)
    assert row["confirmed_state"] == "departing"


def test_a_wrong_vertical_rate_sign_in_the_air_does_not_make_a_landing_a_departure(
        tmp_path, clock, routes):
    """Recorded at Roissy: UAE7V (A380) descends 1450, 1325, then reports
    +608 ft/min at 1000 ft (its altitude fell 325 ft in 30 s), then is on the
    pavement. No 'departing' event may follow its arrival."""
    state_dir = str(tmp_path)
    routes["UAE7V"] = _route_payload("UAE7V", "DXB", "Dubai", "ORY", "Paris", airline="Emirates")
    _cycle(clock, state_dir, _snapshot("896189", "UAE7V", -640, alt=1450))
    _cycle(clock, state_dir, _snapshot("896189", "UAE7V", -704, alt=1325), advance_s=30)
    _cycle(clock, state_dir, _snapshot("896189", "UAE7V", 608, alt=1000), advance_s=30)
    _cycle(clock, state_dir, _ground_roll_snapshot("896189", "UAE7V", 608), advance_s=30)
    states = [r["confirmed_state"] for r in _rows(state_dir) if r["hex"] == "896189"]
    assert states and set(states) == {"arriving"}
