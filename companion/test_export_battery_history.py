"""GET /api/export/battery-history over real HTTP: a read-only, bearer-token
protected JSON Lines export of the `device_health` table.

Every case talks to a real companion server (subprocess unless a case
needs to change a module constant in-process). The token is generated per
test, never a literal that looks like a credential.
"""
import json
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest

from companion import export_api
from companion_app_server import http_request, login
from server import history_db

PATH = "/api/export/battery-history"
TOKEN_ENV = "SKYPANE_EXPORT_TOKEN"
KEYS = ["ts", "battery_mv", "fw_version", "boot_reason", "rssi"]
UNKNOWN_PATH = "/no-such-page-anywhere"


def _new_token(length=48):
    return secrets.token_urlsafe(length)[:length]


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _bearer(token):
    return {"Authorization": "Bearer " + token}


def _seed_rows(state_dir, rows):
    conn = history_db.connect(state_dir)
    try:
        for ts, battery_mv, fw, boot, rssi in rows:
            history_db.record_device_health(conn, ts, battery_mv, fw, boot, rssi)
        conn.execute(
            "INSERT INTO runway_events (ts, callsign) VALUES (?, ?)",
            ("2026-10-24T00:00:00+00:00", "SECRETCALLSIGN"))
        conn.commit()
    finally:
        conn.close()


def _stamp(moment):
    # The format the battery-log tailer stores.
    return moment.isoformat(timespec="seconds")


@pytest.fixture
def token():
    return _new_token()


@pytest.fixture
def seeded(make_app_server, token):
    """(server, rows): a server with the export enabled and four stored
    health rows, the second with a null battery.
    """
    base = _now() - timedelta(days=3)
    rows = [
        (_stamp(base + timedelta(minutes=15 * i)), mv, "1.2.3", "timer", "-61")
        for i, mv in enumerate((4050, None, 4040, 4030))]

    def seed(state_dir):
        _seed_rows(state_dir, rows)

    server = make_app_server(seed=seed, env_overrides={TOKEN_ENV: token})
    return server, rows, base


def _get(server, query="", headers=None, path=PATH):
    return http_request(
        server.url(path + query), extra_headers=headers or {})


def _since_query(moment):
    return "?since=" + _iso(moment)


def _lines(body):
    return [json.loads(line) for line in body.decode("utf-8").splitlines()]


# --- the feature is off unless a long enough token is configured -----------

def test_without_a_token_variable_the_route_is_an_unknown_path(make_app_server):
    server = make_app_server()
    _status, _h, unknown = _get(server, path=UNKNOWN_PATH)
    status, headers, body = _get(
        server, _since_query(_now() - timedelta(days=1)), _bearer(_new_token()))
    assert status == 404
    assert body == unknown
    assert "WWW-Authenticate" not in headers


def test_a_token_shorter_than_32_characters_leaves_the_feature_off(make_app_server):
    short = _new_token(31)
    server = make_app_server(env_overrides={TOKEN_ENV: short})
    _status, _h, unknown = _get(server, path=UNKNOWN_PATH)
    status, headers, body = _get(
        server, _since_query(_now() - timedelta(days=1)), _bearer(short))
    assert status == 404
    assert body == unknown
    assert "WWW-Authenticate" not in headers


def test_a_32_character_token_turns_the_feature_on(make_app_server):
    exact = _new_token(32)
    server = make_app_server(env_overrides={TOKEN_ENV: exact})
    status, _h, _body = _get(
        server, _since_query(_now() - timedelta(days=1)), _bearer(exact))
    assert status == 200


def test_an_admin_cookie_does_not_reveal_a_disabled_route(make_app_server):
    server = make_app_server()
    cookie = login(server)
    _status, _h, unknown = http_request(server.url(UNKNOWN_PATH), cookie=cookie)
    status, _h, body = http_request(
        server.url(PATH + _since_query(_now() - timedelta(days=1))), cookie=cookie)
    assert status == 404
    assert body == unknown


# --- what the export returns ---------------------------------------------------

def test_the_export_is_json_lines_of_the_device_health_columns(seeded, token):
    server, rows, base = seeded
    status, headers, body = _get(
        server, _since_query(base - timedelta(hours=1)), _bearer(token))
    assert status == 200
    assert headers["Content-Type"] == "application/x-ndjson; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in headers
    assert body.endswith(b"\n")
    parsed = _lines(body)
    assert [list(item) for item in parsed] == [KEYS] * len(rows)
    assert [(i["ts"], i["battery_mv"], i["fw_version"], i["boot_reason"], i["rssi"])
            for i in parsed] == rows
    assert parsed[1]["battery_mv"] is None


def test_since_keeps_only_rows_from_that_time_on(seeded, token):
    server, rows, base = seeded
    cut = base + timedelta(minutes=20)
    status, _h, body = _get(server, _since_query(cut), _bearer(token))
    assert status == 200
    assert [i["ts"] for i in _lines(body)] == [rows[2][0], rows[3][0]]


def test_an_empty_window_is_a_200_with_an_empty_body(seeded, token):
    server, _rows, _base = seeded
    status, _h, body = _get(
        server, _since_query(_now() + timedelta(hours=1)), _bearer(token))
    assert status == 200
    assert body == b""


def test_a_percent_encoded_since_is_accepted(seeded, token):
    server, rows, base = seeded
    encoded = urllib.parse.quote(_iso(base - timedelta(hours=1)), safe="")
    status, _h, body = _get(server, "?since=" + encoded, _bearer(token))
    assert status == 200
    assert len(_lines(body)) == len(rows)


def test_only_device_health_is_exported(seeded, token):
    server, _rows, base = seeded
    _status, _h, body = _get(
        server, _since_query(base - timedelta(hours=1)), _bearer(token))
    assert b"SECRETCALLSIGN" not in body
    assert b"callsign" not in body


def test_a_missing_history_database_is_a_503_and_is_not_created(make_app_server, token):
    server = make_app_server(env_overrides={TOKEN_ENV: token})
    status, _h, body = _get(
        server, _since_query(_now() - timedelta(days=1)), _bearer(token))
    assert status == 503
    assert token.encode() not in body
    assert not os.path.exists(history_db.history_db_path(server.state_dir))


# --- authentication --------------------------------------------------------------

def _refusal(server, headers, cookie=None):
    return http_request(
        server.url(PATH + _since_query(_now() - timedelta(days=1))),
        cookie=cookie, extra_headers=headers)


def test_a_missing_and_a_wrong_token_get_the_same_401(seeded, token):
    server, _rows, _base = seeded
    missing = _refusal(server, {})
    wrong = _refusal(server, _bearer(_new_token()))
    assert missing[0] == wrong[0] == 401
    assert missing[1]["WWW-Authenticate"] == "Bearer"
    assert wrong[1]["WWW-Authenticate"] == "Bearer"
    assert missing[2] == wrong[2]
    assert token.encode() not in missing[2]
    assert "Set-Cookie" not in missing[1] and "Set-Cookie" not in wrong[1]


@pytest.mark.parametrize("variant", [
    "prefix", "suffix", "scheme", "empty", "lowercase-scheme-wrong-token"])
def test_near_miss_credentials_are_refused(seeded, token, variant):
    server, _rows, _base = seeded
    header = {
        "prefix": "Bearer " + token[:-1],
        "suffix": "Bearer " + token + "x",
        "scheme": "Basic " + token,
        "empty": "Bearer ",
        "lowercase-scheme-wrong-token": "bearer " + _new_token(),
    }[variant]
    status, headers, _body = _refusal(server, {"Authorization": header})
    assert status == 401
    assert headers["WWW-Authenticate"] == "Bearer"


def test_the_scheme_name_is_case_insensitive(seeded, token):
    server, _rows, _base = seeded
    status, _h, _body = _refusal(server, {"Authorization": "bearer " + token})
    assert status == 200


def test_the_token_in_the_query_string_is_not_a_credential(seeded, token):
    server, _rows, _base = seeded
    status, _h, _body = http_request(server.url(
        PATH + _since_query(_now() - timedelta(days=1)) + "&token=" + token))
    assert status == 401


def test_a_signed_in_admin_cookie_never_grants_access(seeded):
    server, _rows, _base = seeded
    cookie = login(server)
    plain = _refusal(server, {}, cookie=cookie)
    wrong = _refusal(server, _bearer(_new_token()), cookie=cookie)
    assert plain[0] == wrong[0] == 401
    assert plain[2] == wrong[2]
    assert "Set-Cookie" not in plain[1] and "Set-Cookie" not in wrong[1]


def test_a_valid_token_response_sets_no_cookie_and_ignores_a_bad_one(seeded, token):
    server, _rows, _base = seeded
    status, headers, _body = _refusal(
        server, _bearer(token), cookie="sp_session=not-a-session")
    assert status == 200
    assert "Set-Cookie" not in headers


def test_the_token_never_reaches_the_server_log(seeded, token):
    server, _rows, _base = seeded
    _refusal(server, _bearer(token))
    _refusal(server, _bearer(token + "x"))
    _refusal(server, {})
    http_request(server.url(PATH + "?since=bad"), extra_headers=_bearer(token))
    assert token not in server.read_stdout()


# --- throttling ----------------------------------------------------------------

def test_repeated_failures_from_one_client_are_throttled(seeded, token):
    server, _rows, _base = seeded
    statuses = [_refusal(server, _bearer(_new_token()))[0] for _ in range(12)]
    assert statuses[:export_api.FAILURE_LIMIT] == [401] * export_api.FAILURE_LIMIT
    assert statuses[export_api.FAILURE_LIMIT:] == [429, 429]
    # A throttled client is refused even with the right token, so the
    # throttle cannot be used to test guesses faster.
    status, headers, body = _refusal(server, _bearer(token))
    assert status == 429
    assert "Retry-After" in headers
    assert token.encode() not in body


def test_throttling_is_per_client_address(seeded, token):
    server, _rows, _base = seeded
    for _ in range(export_api.FAILURE_LIMIT + 1):
        _refusal(server, {"X-Forwarded-For": "203.0.113.7"})
    blocked = _refusal(server, {**_bearer(token), "X-Forwarded-For": "203.0.113.7"})
    other = _refusal(server, {**_bearer(token), "X-Forwarded-For": "203.0.113.8"})
    assert blocked[0] == 429
    assert other[0] == 200


def test_successful_requests_do_not_use_up_the_failure_allowance(seeded, token):
    server, _rows, _base = seeded
    for _ in range(export_api.FAILURE_LIMIT + 5):
        assert _refusal(server, _bearer(token))[0] == 200


# --- input validation -----------------------------------------------------------

def _valid_since():
    return _iso(_now() - timedelta(days=1))


@pytest.mark.parametrize("query", [
    "",
    "?since=",
    "?since=yesterday",
    "?since=2026-10-23",
    "?since=2026-10-23T04:25:00",
    "?since=2026-10-23T04:25:00%2B00:00",
    "?since=2026-10-23t04:25:00z",
    "?since=2026-10-23T04:25:00Z%0A",
    "?since=2026-13-45T04:25:00Z",
    "?since=2026-10-23T25:25:00Z",
    "?since=%D9%A2%D9%A0%D9%A2%D9%A6-10-23T04:25:00Z",
    "?since=2026-10-23T04:25:00Z'%20OR%201=1--",
    "?since=2026-10-23T04:25:00Z';DROP%20TABLE%20device_health;--",
])
def test_a_malformed_since_is_a_short_400(seeded, token, query):
    server, _rows, _base = seeded
    status, headers, body = _get(server, query, _bearer(token))
    assert status == 400
    assert headers["Content-Type"].startswith("text/plain")
    assert len(body) < 200
    assert token.encode() not in body


def test_since_older_than_400_days_is_refused(seeded, token):
    server, _rows, _base = seeded
    old = _iso(_now() - timedelta(days=401))
    recent_enough = _iso(_now() - timedelta(days=399))
    assert _get(server, "?since=" + old, _bearer(token))[0] == 400
    assert _get(server, "?since=" + recent_enough, _bearer(token))[0] == 200


def test_since_more_than_a_day_in_the_future_is_refused(seeded, token):
    server, _rows, _base = seeded
    far = _iso(_now() + timedelta(days=1, hours=1))
    near = _iso(_now() + timedelta(hours=23))
    assert _get(server, "?since=" + far, _bearer(token))[0] == 400
    assert _get(server, "?since=" + near, _bearer(token))[0] == 200


@pytest.mark.parametrize("extra", ["&limit=1", "&x=", "&since=" + "2026-10-23T04:25:00Z"])
def test_any_other_or_repeated_parameter_is_refused(seeded, token, extra):
    server, _rows, _base = seeded
    status, _h, _body = _get(server, "?since=" + _valid_since() + extra, _bearer(token))
    assert status == 400


def test_validation_runs_only_after_authentication(seeded):
    server, _rows, _base = seeded
    status, _h, _body = _get(server, "?since=bad", _bearer(_new_token()))
    assert status == 401


def test_an_invalid_request_with_a_valid_token_does_not_count_as_a_failure(seeded, token):
    server, _rows, _base = seeded
    for _ in range(export_api.FAILURE_LIMIT + 3):
        assert _get(server, "?since=bad", _bearer(token))[0] == 400
    assert _get(server, "?since=" + _valid_since(), _bearer(token))[0] == 200


# --- methods ---------------------------------------------------------------------

@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "HEAD", "PATCH"])
def test_only_get_serves_the_export(seeded, token, method):
    server, _rows, _base = seeded
    status, _h, body = http_request(
        server.url(PATH + "?since=" + _valid_since()), method=method,
        extra_headers={**_bearer(token), "Origin": server.base_url()})
    assert status in (404, 405, 501)
    assert b"battery_mv" not in body


# --- the row cap -------------------------------------------------------------------

def test_more_rows_than_the_cap_is_a_413_never_a_truncation(
        app_server_in_process, monkeypatch, token):
    server = app_server_in_process
    server.apply_env({TOKEN_ENV: token})
    export_api.FAILURE_THROTTLE.reset()
    base = _now() - timedelta(days=1)
    _seed_rows(server.state_dir, [
        (_stamp(base + timedelta(minutes=i)), 4000 + i, "1", "t", "-1")
        for i in range(5)])
    monkeypatch.setattr(export_api, "MAX_ROWS", 4)
    status, _h, body = _get(
        server, _since_query(base - timedelta(hours=1)), _bearer(token))
    assert status == 413
    assert b"battery_mv" not in body
    monkeypatch.setattr(export_api, "MAX_ROWS", 5)
    status, _h, body = _get(
        server, _since_query(base - timedelta(hours=1)), _bearer(token))
    assert status == 200
    assert len(_lines(body)) == 5
