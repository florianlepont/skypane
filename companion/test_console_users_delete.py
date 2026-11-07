"""Delete user over real HTTP: the owned-frame, self and last-administrator
refusals, what a successful delete removes (sessions, co-manager rows, the
user record), and the audit trail that keeps the e-mail."""
import pytest

import fleet_console_support as fx
from companion import prefs
from server import fleet_db


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


def _sql(state_dir, sql, args=()):
    conn = fleet_db.connect(state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _flash_page(server, cookie, headers, path="/users"):
    values = [value.split(";")[0] for key, value in headers.items()
              if key.lower() == "set-cookie" and value.startswith("sp_flash=")]
    assert values, "no flash cookie"
    return fx.get(server, cookie + "; " + values[0], path)[2]


def _delete(server, cookie, user_id):
    return fx.post(server, cookie, "/users/%s/delete" % user_id, {})


def _user_count(state_dir, user_id):
    return _sql(state_dir, "SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))[0][0]


def test_a_person_who_owns_a_frame_is_refused_with_the_frame_name(rig):
    server, seed, cookie = rig
    status, headers, _ = _delete(server, cookie, seed.owner_id)
    assert status == 303
    page = _flash_page(server, cookie, headers)
    assert "Reassign or retire the frame first" in page and "Kitchen" in page
    assert _user_count(server.state_dir, seed.owner_id) == 1
    assert fx.audit_rows(server.state_dir, "user.delete")[0]["outcome"] == "denied"
    assert [row["outcome"] for row in fx.audit_rows(server.state_dir, "user.delete")] == [
        "denied"]


def test_the_signed_in_administrator_cannot_delete_themselves(rig):
    server, seed, cookie = rig
    status, headers, _ = _delete(server, cookie, seed.admin_id)
    assert status == 303
    assert "cannot disable, demote or delete yourself" in _flash_page(server, cookie, headers)
    assert _user_count(server.state_dir, seed.admin_id) == 1
    assert fx.audit_rows(server.state_dir, "user.delete")[0]["detail"] == '{"reason": "self"}'


def test_the_last_active_administrator_cannot_be_deleted(rig):
    server, seed, _cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.set_user_disabled(conn, fx.SECOND_ADMIN_EMAIL, True)
        with pytest.raises(fleet_db.LastAdminError):
            fleet_db.delete_user_guarded(conn, None, seed.admin_id)
    finally:
        conn.close()
    assert _user_count(server.state_dir, seed.admin_id) == 1


def test_a_delete_removes_sessions_co_manager_rows_and_the_record(rig):
    server, seed, cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.add_co_manager(conn, seed.owned_id, seed.user_id, seed.owner_id)
    finally:
        conn.close()
    fx.user_cookie(server.state_dir)
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                (seed.user_id,)) == [(1,)]
    status, headers, _ = _delete(server, cookie, seed.user_id)
    assert status == 303
    page = _flash_page(server, cookie, headers)
    assert "User deleted" in page and fx.USER_EMAIL in page
    assert _user_count(server.state_dir, seed.user_id) == 0
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                (seed.user_id,)) == [(0,)]
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM device_co_managers") == [(0,)]
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM devices WHERE id = ?",
                (seed.owned_id,)) == [(1,)]
    removal = fx.audit_rows(server.state_dir, "device.co_manager_remove")
    assert len(removal) == 1 and '"via": "user_deleted"' in removal[0]["detail"]


def test_the_audit_row_keeps_the_email_and_the_audit_page_shows_it(rig):
    server, seed, cookie = rig
    assert _delete(server, cookie, seed.user_id)[0] == 303
    rows = fx.audit_rows(server.state_dir, "user.delete")
    assert len(rows) == 1
    assert rows[0]["target_type"] == "user" and rows[0]["target_id"] == fx.USER_EMAIL
    assert rows[0]["outcome"] == "ok"
    body = fx.get(server, cookie, "/audit")[2]
    assert "User deleted" in body and fx.USER_EMAIL in body


def test_locations_the_person_created_survive_without_an_owner(rig):
    server, seed, cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        location_id = fleet_db.add_location(
            conn, "Home", 48.7, 2.4, "Europe/Paris", owner_user_id=seed.user_id)
    finally:
        conn.close()
    assert _delete(server, cookie, seed.user_id)[0] == 303
    assert _sql(server.state_dir, "SELECT owner_user_id FROM locations WHERE id = ?",
                (location_id,)) == [(None,)]


def test_an_unknown_user_changes_nothing(rig):
    server, _seed, cookie = rig
    status, headers, _ = _delete(server, cookie, 99999)
    assert status == 303 and "User not found" in _flash_page(server, cookie, headers)
    assert fx.audit_rows(server.state_dir, "user.delete") == []
