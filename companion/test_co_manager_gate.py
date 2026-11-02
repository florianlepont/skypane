"""Co-manager access over HTTP: the ownership gate admits a membership row,
reads it on every request and fails closed when the table is unavailable.
"""
import pytest

from fleet_console_support import (
    OWNER_EMAIL, USER_EMAIL, get, seed_fleet, user_cookie)
from server import fleet_db


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seeded = seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.add_co_manager(conn, seeded.owned_id, seeded.user_id, seeded.owner_id)
    finally:
        conn.close()
    return server, seeded, user_cookie(server.state_dir, USER_EMAIL)


def _page(seeded, device_id):
    return "/devices/%s/" % device_id


def test_a_co_manager_reaches_their_frame_and_not_another_users(rig):
    server, seeded, cookie = rig
    unknown = get(server, cookie, "/no-such-page-anywhere")
    assert get(server, cookie, _page(seeded, seeded.owned_id))[0] == 200
    refused = get(server, cookie, _page(seeded, seeded.live_id))
    assert refused[0] == 404
    assert refused[2] == unknown[2]


def test_removal_takes_effect_on_the_next_request(rig):
    server, seeded, cookie = rig
    assert get(server, cookie, _page(seeded, seeded.owned_id))[0] == 200
    conn = fleet_db.connect(server.state_dir)
    try:
        assert fleet_db.remove_co_manager(conn, seeded.owned_id, seeded.user_id)
    finally:
        conn.close()
    assert get(server, cookie, _page(seeded, seeded.owned_id))[0] == 404


def test_a_missing_membership_table_fails_closed(rig):
    server, seeded, cookie = rig
    owner_cookie = user_cookie(server.state_dir, OWNER_EMAIL)
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute("DROP TRIGGER IF EXISTS devices_owner_not_co_manager")
        conn.execute("DROP TABLE device_co_managers")
    finally:
        conn.close()
    assert get(server, cookie, _page(seeded, seeded.owned_id))[0] == 404
    assert get(server, owner_cookie, _page(seeded, seeded.owned_id))[0] == 200
