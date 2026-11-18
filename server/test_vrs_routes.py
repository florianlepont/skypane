"""Routes from the VRS standing data, asked before adsbdb.

Measured on 2026-11-17 against Flightradar24 (155 flights at four airports):
adsbdb alone gave the right route for 80 %, VRS first then adsbdb for 94 %,
and 24 of the 26 flights that had no route had one in VRS. Every assertion
reads the recorded history rows, never source text.
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

CITIES = {
    "ORY": "Paris", "TLV": "Tel Aviv", "FCO": "Rome", "MAD": "Madrid", "CDG": "Paris",
    "TLS": "Toulouse", "NTE": "Nantes", "SNR": "Saint-Nazaire", "LIS": "Lisbon", "LIN": "Milan",
    "SZG": "Salzburg", "BHX": "Birmingham",
}


def _vrs_body(codes):
    """A VRS standing-data answer for the IATA airports `codes`, in the
    shape of the real files (`_airport_codes_iata`, `_airports`)."""
    return {
        "callsign": "X", "airline_code": "XXX",
        "_airport_codes_iata": "-".join(codes),
        "_airports": [
            {"name": CITIES[c] + " Airport", "iata": c, "icao": "X" + c, "location": CITIES[c]}
            for c in dict.fromkeys(codes)],
    }


def _adsbdb_body(callsign, origin, dest):
    def airport(iata):
        return {"iata_code": iata, "icao_code": "X" + iata, "municipality": CITIES[iata], "name": CITIES[iata]}
    return {"response": {"flightroute": {
        "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
        "airline": {"name": "easyJet Europe", "icao": callsign[:3], "iata": "XX", "country": "France"},
        "origin": airport(origin), "destination": airport(dest)}}}


@pytest.fixture
def clock(monkeypatch):
    fake = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: fake["t"])
    return fake


@pytest.fixture
def adsbdb(monkeypatch):
    table, calls = {}, []

    def transport(callsign, timeout=None):
        calls.append(callsign)
        body = table.get(callsign)
        return (200, body) if body else (404, None)

    monkeypatch.setattr(enrich, "default_transport", transport)
    table["calls"] = calls
    return table


@pytest.fixture
def vrs(monkeypatch):
    state = {"table": {}, "calls": [], "fail": False}

    def transport(key, timeout=None):
        state["calls"].append(key)
        if state["fail"]:
            raise OSError("vrs unreachable")
        body = state["table"].get(key)
        return (200, body) if body else (404, None)

    monkeypatch.setattr(enrich, "default_vrs_transport", transport)
    return state


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


def test_a_callsign_adsbdb_does_not_know_gets_its_route_from_vrs(tmp_path, clock, adsbdb, vrs):
    """Recorded at Orly: TVF17ST (TO3453 from Tel Aviv) had no route in adsbdb."""
    vrs["table"]["TVF17ST"] = _vrs_body(["TLV", "ORY"])
    _cycle(clock, str(tmp_path), _snapshot("39de59", "TVF17ST", -700))
    (row,) = _rows(str(tmp_path))
    assert (row["confirmed_state"], row["origin"], row["destination"]) == ("arriving", "TLV", "ORY")
    assert row["airline"] == "Transavia France"


def test_vrs_is_asked_first_and_wins_when_adsbdb_is_wrong(tmp_path, clock, adsbdb, vrs):
    """Recorded at Orly: EJU82RM (EC4941 to Rome) was SZG to BHX in adsbdb."""
    adsbdb["EJU82RM"] = _adsbdb_body("EJU82RM", "SZG", "BHX")
    vrs["table"]["EJU82RM"] = _vrs_body(["ORY", "FCO"])
    _cycle(clock, str(tmp_path), _snapshot("440352", "EJU82RM", 1800, alt=900))
    (row,) = _rows(str(tmp_path))
    assert (row["confirmed_state"], row["origin"], row["destination"]) == ("departing", "ORY", "FCO")
    assert adsbdb["calls"] == []


def test_a_vrs_route_without_the_watched_airport_falls_back_to_adsbdb(tmp_path, clock, adsbdb, vrs):
    vrs["table"]["EJU1LIN"] = _vrs_body(["MAD", "LIS"])
    adsbdb["EJU1LIN"] = _adsbdb_body("EJU1LIN", "LIN", "ORY")
    _cycle(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    (row,) = _rows(str(tmp_path))
    assert (row["origin"], row["destination"]) == ("LIN", "ORY")


def test_a_callsign_vrs_does_not_know_falls_back_to_adsbdb(tmp_path, clock, adsbdb, vrs):
    adsbdb["EJU1LIN"] = _adsbdb_body("EJU1LIN", "LIN", "ORY")
    _cycle(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    (row,) = _rows(str(tmp_path))
    assert (row["origin"], row["destination"]) == ("LIN", "ORY")
    assert vrs["calls"] == ["EJU1LIN"]


def test_the_leading_zero_is_removed_for_vrs_only(tmp_path, clock, adsbdb, vrs):
    """IBE05RR is IBE5RR in the VRS files."""
    vrs["table"]["IBE5RR"] = _vrs_body(["ORY", "MAD"])
    _cycle(clock, str(tmp_path), _snapshot("346458", "IBE05RR", 1800, alt=900))
    (row,) = _rows(str(tmp_path))
    assert (row["origin"], row["destination"]) == ("ORY", "MAD")
    assert vrs["calls"] == ["IBE5RR"]


def test_a_vrs_answer_is_cached_for_the_next_aircraft_with_that_callsign(tmp_path, clock, adsbdb, vrs):
    vrs["table"]["TVF17ST"] = _vrs_body(["TLV", "ORY"])
    _cycle(clock, str(tmp_path), _snapshot("39de59", "TVF17ST", -700))
    _cycle(clock, str(tmp_path), _snapshot("39de60", "TVF17ST", -700), advance_s=400)
    assert vrs["calls"] == ["TVF17ST"]
    assert [r["origin"] for r in _rows(str(tmp_path))] == ["TLV", "TLV"]


def test_an_unreachable_vrs_falls_back_to_adsbdb_and_is_not_cached(tmp_path, clock, adsbdb, vrs):
    vrs["fail"] = True
    adsbdb["EJU1LIN"] = _adsbdb_body("EJU1LIN", "LIN", "ORY")
    _cycle(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    _cycle(clock, str(tmp_path), _snapshot("bbbbbb", "EJU1LIN", -700), advance_s=400)
    assert vrs["calls"] == ["EJU1LIN", "EJU1LIN"]
    assert [r["origin"] for r in _rows(str(tmp_path))] == ["LIN", "LIN"]


def test_vrs_route_for_an_airline_without_a_name_is_kept_without_the_airline(tmp_path, clock, adsbdb, vrs):
    """Recorded at Lyon: ITI2915 (Strasbourg), a prefix no table names."""
    vrs["table"]["ITI25KZ"] = _vrs_body(["LIN", "ORY"])
    _cycle(clock, str(tmp_path), _snapshot("394d49", "ITI25KZ", -700))
    (row,) = _rows(str(tmp_path))
    assert (row["origin"], row["destination"]) == ("LIN", "ORY")
    assert not row["airline"]


def test_the_leg_at_the_watched_airport_is_chosen_in_a_multi_leg_route():
    """Recorded at Nantes: CCM321L flies TLS, NTE, SNR, TLS."""
    airports = [{"iata": c, "city": CITIES[c]} for c in ("TLS", "NTE", "SNR", "TLS")]
    watched = frozenset({"NTE"})
    arrival = enrich.route_leg(airports, "arriving", watched)
    departure = enrich.route_leg(airports, "departing", watched)
    assert [a["iata"] for a in arrival] == ["TLS", "NTE"]
    assert [a["iata"] for a in departure] == ["NTE", "SNR"]
    assert enrich.route_leg(airports, None, watched) is None
    assert enrich.route_leg(airports, "arriving", frozenset({"CDG"})) is None


def test_without_a_direction_a_two_airport_route_still_gives_its_leg():
    airports = [{"iata": c, "city": CITIES[c]} for c in ("TLV", "ORY")]
    leg = enrich.route_leg(airports, None, frozenset({"ORY"}))
    assert [a["iata"] for a in leg] == ["TLV", "ORY"]


def test_a_lookup_without_a_leg_context_never_asks_vrs(vrs, adsbdb):
    adsbdb["EJU1LIN"] = _adsbdb_body("EJU1LIN", "LIN", "ORY")
    route = enrich.lookup_route("EJU1LIN", {}, now=CLOCK_BASE)
    assert route["origin_iata"] == "LIN"
    assert vrs["calls"] == []
