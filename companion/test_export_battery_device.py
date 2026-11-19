"""GET /api/export/battery-history?device=<id>: the same read-only export for
one registered frame's own history.db, through the same bearer token.

Every case talks to a real companion server over HTTP with a real fleet.db
and real per-device state directories.
"""
import os
import secrets
from datetime import timedelta

import pytest
from companion_app_server import http_request
from skypane_two_device_fleet import sim_hardware_env

from companion.test_export_battery_helpers import (
    KEYS, PATH, TOKEN_ENV, bearer, get, iso, lines, new_token, now, seed_rows,
    since_query, stamp)
from server import device_dirs, fleet_db, hardware

PRIMARY_MV = (4100, 4090, 4080)
SECOND_MV = (3900, 3890)
RETIRED_MV = (3700,)


def _rows(base, voltages, boot):
    return [(stamp(base + timedelta(minutes=15 * i)), mv, "9.9.9", boot, "-70")
            for i, mv in enumerate(voltages)]


def _add_frame(conn, state_dir, mac, owner):
    device_id = fleet_db.add_device(
        conn, mac, "f" * 64, hardware.SIM_CLONE_KEY, owner, state_path="auto")
    profile = hardware.get_profile(hardware.SIM_CLONE_KEY, os.environ)
    device_dirs.provision_device_dir(state_dir, device_id, profile.width, profile.height)
    return device_id


@pytest.fixture
def fleet(make_app_server):
    """(server, token, ids, base): a primary history, a registered second
    frame, a retired frame whose data is kept and a registered frame with no
    history.db."""
    token = new_token()
    base = now() - timedelta(days=2)
    ids = {}

    def seed(state_dir):
        seed_rows(state_dir, _rows(base, PRIMARY_MV, "primary"))
        conn = fleet_db.connect(state_dir)
        try:
            with sim_hardware_env(), fleet_db.transaction(conn):
                owner = fleet_db.add_user(conn, "owner@example.test", "admin")
                ids["second"] = _add_frame(conn, state_dir, "aa:bb:cc:00:00:01", owner)
                ids["retired"] = _add_frame(conn, state_dir, "aa:bb:cc:00:00:02", owner)
                ids["empty"] = _add_frame(conn, state_dir, "aa:bb:cc:00:00:03", owner)
            for name, voltages, boot in (
                    ("second", SECOND_MV, "second"), ("retired", RETIRED_MV, "retired")):
                seed_rows(os.path.join(state_dir, "devices", ids[name]),
                           _rows(base, voltages, boot))
            assert fleet_db.park_retired(conn, ids["retired"], 1) is not None
        finally:
            conn.close()

    server = make_app_server(seed=seed, env_overrides={TOKEN_ENV: token})
    return server, token, ids, base


def _device_query(base, device, hours=1):
    return since_query(base - timedelta(hours=hours)) + "&device=" + device


def test_without_device_the_primary_rows_are_served_unchanged(fleet):
    server, token, _ids, base = fleet
    status, _h, body = get(server, since_query(base - timedelta(hours=1)), bearer(token))
    assert status == 200
    assert [line["battery_mv"] for line in lines(body)] == list(PRIMARY_MV)


def test_device_returns_that_devices_rows_and_not_the_primary_ones(fleet):
    server, token, ids, base = fleet
    status, headers, body = get(server, _device_query(base, ids["second"]), bearer(token))
    assert status == 200
    assert headers["Content-Type"].startswith("application/x-ndjson")
    rows = lines(body)
    assert [line["battery_mv"] for line in rows] == list(SECOND_MV)
    assert all(list(line) == KEYS and line["boot_reason"] == "second" for line in rows)


def test_device_before_since_in_the_query_order_works_too(fleet):
    server, token, ids, base = fleet
    query = "?device=" + ids["second"] + "&since=" + iso(base - timedelta(hours=1))
    status, _h, body = get(server, query, bearer(token))
    assert status == 200 and len(lines(body)) == len(SECOND_MV)


def test_since_applies_to_the_device_rows(fleet):
    server, token, ids, base = fleet
    since = iso(base + timedelta(minutes=15))
    status, _h, body = get(
        server, "?since=" + since + "&device=" + ids["second"], bearer(token))
    assert status == 200
    assert [line["battery_mv"] for line in lines(body)] == [SECOND_MV[1]]


def test_a_retired_frame_with_kept_data_is_still_readable(fleet):
    server, token, ids, base = fleet
    status, _h, body = get(server, _device_query(base, ids["retired"]), bearer(token))
    assert status == 200
    assert [line["battery_mv"] for line in lines(body)] == list(RETIRED_MV)


def test_a_registered_frame_without_a_history_database_is_a_503_and_creates_none(fleet):
    server, token, ids, base = fleet
    status, _h, _body = get(server, _device_query(base, ids["empty"]), bearer(token))
    assert status == 503
    assert not os.path.exists(
        os.path.join(server.state_dir, "devices", ids["empty"], "history.db"))


def test_an_unregistered_well_formed_id_is_a_404_that_echoes_nothing(fleet):
    server, token, ids, base = fleet
    unknown = "d_" + secrets.token_hex(4)
    status, _h, body = get(server, _device_query(base, unknown), bearer(token))
    assert status == 404
    text = body.decode("utf-8")
    assert unknown not in text and not any(i in text for i in ids.values())


@pytest.mark.parametrize("device", [
    "", "d_", "D_12345678", "d_1234567", "d_123456789", "d_1234567g",
    "..", "../..", "d_12345678/..", "..%2f..%2fetc", "%2e%2e", "d_%2e%2e%2e%2e%2e%2e",
    "d_12345678%00", "d_12345678%0a", "devices/d_12345678", "%2fetc%2fpasswd",
    "a" * 5000, "d_" + "0" * 64, "p_12345678", ".",
])
def test_a_malformed_device_id_is_a_400(fleet, device):
    server, token, _ids, base = fleet
    status, _h, body = get(server, _device_query(base, device), bearer(token))
    assert status == 400
    assert b"battery_mv" not in body


def test_the_device_parameter_twice_is_refused(fleet):
    server, token, ids, base = fleet
    query = _device_query(base, ids["second"]) + "&device=" + ids["retired"]
    assert get(server, query, bearer(token))[0] == 400


@pytest.mark.parametrize("extra", ["&limit=1", "&x="])
def test_other_parameters_next_to_device_are_refused(fleet, extra):
    server, token, ids, base = fleet
    assert get(server, _device_query(base, ids["second"]) + extra, bearer(token))[0] == 400


def test_device_without_since_is_refused(fleet):
    server, token, ids, _base = fleet
    assert get(server, "?device=" + ids["second"], bearer(token))[0] == 400


def test_an_old_since_next_to_device_is_refused(fleet):
    server, token, ids, _base = fleet
    query = "?since=" + iso(now() - timedelta(days=500)) + "&device=" + ids["second"]
    assert get(server, query, bearer(token))[0] == 400


@pytest.mark.parametrize("route", ["flights", "poll-cycles", "status"])
def test_other_routes_still_refuse_device(fleet, route):
    server, token, ids, base = fleet
    query = _device_query(base, ids["second"])
    if route == "status":
        query = "?device=" + ids["second"]
    status, _h, body = get(
        server, query, bearer(token), path="/api/export/" + route)
    assert status == 400
    assert ids["second"].encode() not in body


def test_device_needs_the_bearer_token_and_a_cookie_is_no_substitute(fleet):
    server, _token, ids, base = fleet
    query = _device_query(base, ids["second"])
    assert get(server, query)[0] == 401
    assert get(server, query, {"Authorization": "Bearer " + "x" * 48})[0] == 401
    assert get(server, query, {"Cookie": "skypane_session=abc"})[0] == 401


def test_a_device_request_still_hits_the_failed_auth_throttle(fleet):
    server, _token, ids, base = fleet
    query = _device_query(base, ids["second"])
    wrong = {"Authorization": "Bearer " + "y" * 48}
    statuses = [get(server, query, wrong)[0] for _ in range(12)]
    assert statuses[0] == 401 and statuses[-1] == 429


def test_the_device_parameter_cannot_write(fleet):
    server, token, ids, base = fleet
    url = server.url(PATH + _device_query(base, ids["second"]))
    status, _h, _b = http_request(url, method="POST", extra_headers=bearer(token))
    assert status != 200
