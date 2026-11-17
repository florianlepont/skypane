"""The read-only debugging exports next to /api/export/battery-history:
flights and poll-cycles (JSON Lines) and status (one JSON object).

Every case talks to a real companion server. The token is generated per
test, never a literal that looks like a credential.
"""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest

from companion_app_server import http_request, login
from server import history_db

TOKEN_ENV = "SKYPANE_EXPORT_TOKEN"
FLIGHTS = "/api/export/flights"
POLL_CYCLES = "/api/export/poll-cycles"
STATUS = "/api/export/status"
LINE_ROUTES = (FLIGHTS, POLL_CYCLES)
ALL_ROUTES = LINE_ROUTES + (STATUS,)

FLIGHT_KEYS = [
    "ts", "hex", "callsign", "aircraft_type", "confirmed_state", "corroborated",
    "route_source", "airline", "origin", "destination", "tracked_runway", "gallery_name"]
CYCLE_KEYS = ["ts"] + list(history_db.POLL_CYCLE_COLUMNS)


def _token():
    return secrets.token_urlsafe(48)[:48]


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(moment):
    return moment.isoformat(timespec="seconds")


def _get(server, path, token=None, query=""):
    headers = {"Authorization": "Bearer " + token} if token else {}
    return http_request(server.url(path + query), extra_headers=headers)


def _lines(body):
    return [json.loads(line) for line in body.decode("utf-8").splitlines()]


def _seed(state_dir):
    base = _now() - timedelta(hours=2)
    conn = history_db.connect(state_dir)
    try:
        history_db.record_runway_event(
            conn, ts=_stamp(base - timedelta(days=3)), hex="old000", callsign="OLD1")
        history_db.record_runway_event(
            conn, ts=_stamp(base), hex="39dd00", callsign="TVF87XA", aircraft_type="A20N",
            confirmed_state="arriving", corroborated="True", route_source="fresh_hit",
            airline="Transavia France", origin="NTE", destination="ORY", tracked_runway="3",
            gallery_name="x.png")
        history_db.record_poll_cycle(conn, _stamp(base), {
            "branch": "promoted", "detected_hex": "39dd00", "detected_callsign": "TVF87XA",
            "detected_altitude_ft": 575.0, "detected_rate_fpm": -700.0,
            "detected_on_ground": False, "shown_hex": "39dd00", "confirmed_state": "arriving",
            "render_state": "arriving", "state_source": "inferred", "pending": 0,
            "dropped": "44017c", "redraw_blocked": False, "panel_changed": True,
            "source_fault": False, "tracked_runway": "3"})
    finally:
        conn.close()
    with open(os.path.join(state_dir, "poll_state.json"), "w") as fh:
        json.dump({
            "last_flight": {"hex": "39dd00", "callsign": "TVF87XA", "altitude_ft": 575.0,
                            "lat": 48.7, "lon": 2.4, "route_note": "private"},
            "last_confirmed_state": "arriving",
            "pending_flights": [
                {"flight": {"hex": "44017c", "callsign": "EJU198X", "altitude_ft": 0.0},
                 "first_seen": _now().timestamp() - 30}],
            "last_advance_at": 123.0,
            "hold_state": None,
        }, fh)
    with open(os.path.join(state_dir, "device_config.json"), "w") as fh:
        json.dump({"wake_interval_s": 300, "tracked_runway": "3",
                    "detection": {"mode": "position", "center": [48.1, 2.2], "radius_km": 9}}, fh)
    return base


@pytest.fixture
def token():
    return _token()


@pytest.fixture
def server(make_app_server, token):
    return make_app_server(seed=_seed, env_overrides={TOKEN_ENV: token})


# --- access: the same bearer token, off unless configured ------------------

@pytest.mark.parametrize("path", ALL_ROUTES)
def test_without_a_token_variable_each_route_is_an_unknown_path(make_app_server, path):
    server = make_app_server()
    _status, _h, unknown = http_request(server.url("/no-such-page-anywhere"))
    status, headers, body = _get(
        server, path, _token(), "" if path == STATUS else "?since=" + _iso(_now() - timedelta(days=1)))
    assert status == 404
    assert body == unknown
    assert "WWW-Authenticate" not in headers


@pytest.mark.parametrize("path", ALL_ROUTES)
def test_a_missing_or_wrong_token_is_refused(server, path):
    query = "" if path == STATUS else "?since=" + _iso(_now() - timedelta(days=1))
    assert _get(server, path, None, query)[0] == 401
    assert _get(server, path, _token(), query)[0] == 401


@pytest.mark.parametrize("path", ALL_ROUTES)
def test_a_signed_in_session_grants_nothing(server, path):
    cookie = login(server)
    query = "" if path == STATUS else "?since=" + _iso(_now() - timedelta(days=1))
    status, _h, _b = http_request(server.url(path + query), cookie=cookie)
    assert status == 401


@pytest.mark.parametrize("path", LINE_ROUTES)
def test_a_line_route_needs_exactly_the_since_parameter(server, token, path):
    assert _get(server, path, token)[0] == 400
    assert _get(server, path, token, "?since=yesterday")[0] == 400
    assert _get(server, path, token, "?since=%s&x=1" % _iso(_now()))[0] == 400


# --- the line routes ---------------------------------------------------------

def test_flights_returns_the_runway_events_since_the_given_time(server, token):
    status, headers, body = _get(server, FLIGHTS, token, "?since=" + _iso(_now() - timedelta(days=1)))
    assert status == 200
    assert headers["Content-Type"] == "application/x-ndjson; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    (row,) = _lines(body)
    assert list(row) == FLIGHT_KEYS
    assert (row["hex"], row["callsign"], row["confirmed_state"], row["origin"]) == (
        "39dd00", "TVF87XA", "arriving", "NTE")


def test_flights_since_reaches_back_to_older_rows(server, token):
    _status, _h, body = _get(server, FLIGHTS, token, "?since=" + _iso(_now() - timedelta(days=10)))
    assert [r["hex"] for r in _lines(body)] == ["old000", "39dd00"]


def test_poll_cycles_returns_the_trace_with_booleans_as_numbers(server, token):
    status, _h, body = _get(server, POLL_CYCLES, token, "?since=" + _iso(_now() - timedelta(days=1)))
    assert status == 200
    (row,) = _lines(body)
    assert list(row) == CYCLE_KEYS
    assert (row["detected_hex"], row["detected_altitude_ft"], row["dropped"]) == ("39dd00", 575.0, "44017c")
    assert (row["panel_changed"], row["redraw_blocked"], row["detected_on_ground"]) == (1, 0, 0)


def test_a_future_since_returns_no_lines(server, token):
    for path in LINE_ROUTES:
        status, _h, body = _get(server, path, token, "?since=" + _iso(_now() + timedelta(hours=12)))
        assert (status, body) == (200, b"")


# --- status -------------------------------------------------------------------

def test_status_is_one_json_object_with_the_frame_state(server, token):
    status, headers, body = _get(server, STATUS, token)
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    snapshot = json.loads(body)
    assert snapshot["shown"]["hex"] == "39dd00"
    assert snapshot["shown_state"] == "arriving"
    assert snapshot["last_advance_at"] == 123.0
    (waiting,) = snapshot["pending"]
    assert (waiting["hex"], waiting["callsign"]) == ("44017c", "EJU198X")
    assert 25 <= waiting["age_s"] <= 120
    assert snapshot["device"]["wake_interval_s"] == 300
    assert snapshot["device"]["tracked_runway"] == "3"
    assert snapshot["check_interval_experiment"] is None
    assert "now" in snapshot and "meta" in snapshot


def test_status_never_shows_a_position_or_unlisted_field(server, token):
    _status, _h, body = _get(server, STATUS, token)
    text = body.decode("utf-8")
    for leaked in ("48.7", "2.4", "route_note", "private", "center", "radius", "detection", "lat", "lon"):
        assert leaked not in text, leaked


def test_status_takes_no_parameter(server, token):
    assert _get(server, STATUS, token, "?since=" + _iso(_now()))[0] == 400
    assert _get(server, STATUS, token, "?x=1")[0] == 400


def test_other_methods_are_not_allowed_on_any_route(server, token):
    for path in ALL_ROUTES:
        status, _h, _b = http_request(
            server.url(path), method="POST", data=b"",
            extra_headers={"Authorization": "Bearer " + token})
        assert status in (404, 405)
