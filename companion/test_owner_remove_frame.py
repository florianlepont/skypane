"""An owner removing their own frame over real HTTP: the owner alone may do
it, the live frame is refused and untouched, co-managers lose access, the
history is kept, and the Account dialog offers it to the owner only."""
import html

import pytest

import fleet_console_support as fx
from companion import prefs
from companion_app_server import http_request
from server import fleet_db

CO_EMAIL = "co@example.test"


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        seed.co_id = fleet_db.add_user(conn, CO_EMAIL, "user")
        fleet_db.add_co_manager(conn, seed.owned_id, seed.co_id, seed.owner_id)
    finally:
        conn.close()
    return server, seed


def _sql(state_dir, sql, args=()):
    conn = fleet_db.connect(state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _remove(server, cookie, device_id):
    return fx.post(server, cookie, "/devices/%s/frame/remove" % device_id, {})


def _owner(server):
    return fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL)


def _device_count(server, device_id):
    return _sql(server.state_dir, "SELECT COUNT(*) FROM devices WHERE id = ?",
                (device_id,))[0][0]


def test_the_owner_removes_their_frame_and_it_is_retired_with_its_history(rig):
    server, seed = rig
    status, headers, _ = _remove(server, _owner(server), seed.owned_id)
    assert (status, headers["Location"]) == (303, "/account?flash=frame_removed")
    assert _device_count(server, seed.owned_id) == 0
    retired = _sql(
        server.state_dir,
        "SELECT status, previous_owner_user_id, previous_name, "
        "previous_state_path = ? FROM pending_devices WHERE previous_device_id = ?",
        ("devices/" + seed.owned_id, seed.owned_id))
    assert retired == [("retired", seed.owner_id, "Kitchen", 1)]
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM device_co_managers") == [(0,)]
    rows = fx.audit_rows(server.state_dir, "device.retire")
    assert len(rows) == 1 and rows[0]["outcome"] == "ok"
    assert rows[0]["actor_user_id"] == seed.owner_id and '"via": "owner"' in rows[0]["detail"]
    assert len(fx.audit_rows(server.state_dir, "device.co_manager_remove")) == 1


def test_the_flash_after_a_removal_is_a_success_toast(rig):
    server, seed = rig
    cookie = _owner(server)
    assert _remove(server, cookie, seed.owned_id)[0] == 303
    body = html.unescape(fx.get(server, cookie, "/account?flash=frame_removed")[2])
    assert "Frame removed" in body and "Kitchen" not in body
    assert "dlg-remove-frame" not in body


def test_a_co_manager_loses_access_when_the_owner_removes_the_frame(rig):
    server, seed = rig
    co = fx.user_cookie(server.state_dir, email=CO_EMAIL)
    assert fx.get(server, co, "/devices/%s/" % seed.owned_id)[0] == 200
    assert _remove(server, _owner(server), seed.owned_id)[0] == 303
    assert fx.get(server, co, "/devices/%s/" % seed.owned_id)[0] == 404


def test_the_live_frame_is_refused_and_left_untouched(rig):
    server, seed = rig
    before = _sql(server.state_dir, "SELECT * FROM devices WHERE id = ?", (seed.live_id,))
    status, headers, _ = _remove(server, fx.admin_cookie(server.state_dir), seed.live_id)
    assert (status, headers["Location"]) == (303, "/account?flash=frame_remove_live")
    assert _sql(server.state_dir, "SELECT * FROM devices WHERE id = ?", (seed.live_id,)) == before
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM pending_devices WHERE "
                "previous_device_id = ?", (seed.live_id,)) == [(0,)]
    rows = fx.audit_rows(server.state_dir, "device.retire")
    assert [row["outcome"] for row in rows] == ["denied"]
    body = html.unescape(fx.get(
        server, fx.admin_cookie(server.state_dir), "/account?flash=frame_remove_live")[2])
    assert "cannot be removed" in body


@pytest.mark.parametrize("who", ["stranger", "co"])
def test_someone_who_is_not_the_owner_gets_the_unknown_path_answer(rig, who):
    server, seed = rig
    email = fx.USER_EMAIL if who == "stranger" else CO_EMAIL
    cookie = fx.user_cookie(server.state_dir, email=email)
    status, _headers, _ = _remove(server, cookie, seed.owned_id)
    assert status == 404
    assert _device_count(server, seed.owned_id) == 1
    assert fx.audit_rows(server.state_dir, "device.retire") == []


def test_an_administrator_who_is_not_the_owner_is_refused_in_the_handler(rig):
    server, seed = rig
    status, headers, _ = _remove(server, fx.admin_cookie(server.state_dir), seed.owned_id)
    assert (status, headers["Location"]) == (303, "/account?flash=frame_remove_refused")
    assert _device_count(server, seed.owned_id) == 1
    assert fx.audit_rows(server.state_dir, "device.retire") == []


def test_a_frame_reassigned_meanwhile_is_not_retired_by_its_old_owner(rig):
    server, seed = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute("DELETE FROM device_co_managers")
        conn.execute("UPDATE devices SET owner_user_id = ? WHERE id = ?",
                     (seed.user_id, seed.owned_id))
        conn.commit()
    finally:
        conn.close()
    status, headers, _ = _remove(server, _owner(server), seed.owned_id)
    assert status == 404
    assert _device_count(server, seed.owned_id) == 1


def test_a_missing_csrf_token_is_refused(rig):
    server, seed = rig
    cookie = _owner(server)
    status, _headers, _ = http_request(
        server.url("/devices/%s/frame/remove" % seed.owned_id), "POST", data=b"",
        cookie=cookie)
    assert status == 403
    assert _device_count(server, seed.owned_id) == 1


def test_the_account_dialog_offers_the_removal_to_the_owner_only(rig):
    server, seed = rig
    owner_page = fx.get(server, _owner(server), "/account")[2]
    slug = "dlg-remove-frame-%s" % seed.owned_id.lower().replace("_", "-")
    assert 'id="%s"' % slug in owner_page and 'href="#%s"' % slug in owner_page
    assert "/devices/%s/frame/remove" % seed.owned_id in owner_page
    co_page = fx.get(
        server, fx.user_cookie(server.state_dir, email=CO_EMAIL), "/account")[2]
    assert "dlg-remove-frame" not in co_page
    admin_page = fx.get(server, fx.admin_cookie(server.state_dir), "/account")[2]
    assert "dlg-remove-frame" not in admin_page
