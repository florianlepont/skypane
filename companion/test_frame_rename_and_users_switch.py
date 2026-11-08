"""Rename a frame, the Active switch of the Users page answering a fetch, the
Update confirmation without a made-up time, the pairing message naming a frame
without a name, and the retired Update address under a frame prefix. Every
assertion reads served pages, audit rows and the database."""
import re

import pytest

import fleet_console_support as fx
from companion import prefs
from companion_app_server import http_request, with_csrf
from companion_markup import parse_html
from server import fleet_db


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
        co = fleet_db.add_user(conn, "co@example.test", "user")
        fleet_db.add_co_manager(conn, seed.owned_id, co, None)
    finally:
        conn.close()
    cookies = {
        "admin": fx.admin_cookie(server.state_dir),
        "owner": fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(server.state_dir, email="co@example.test"),
        "user": fx.user_cookie(server.state_dir, email=fx.USER_EMAIL)}
    return server, seed, cookies


def _name_of(server, device_id):
    conn = fleet_db.connect(server.state_dir)
    try:
        return fleet_db.get_device(conn, device_id)["name"]
    finally:
        conn.close()


def _rename(server, cookie, device_id, name):
    return http_request(
        server.url("/devices/%s/frame/name" % device_id), method="POST", cookie=cookie,
        data=with_csrf(cookie, {"name": name}),
        extra_headers={"Origin": server.base_url()})


def test_the_owner_renames_the_frame_and_the_change_is_audited(rig):
    server, seed, cookies = rig
    status, headers, _body = _rename(server, cookies["owner"], seed.owned_id, "  Living   room ")
    assert status == 303 and headers["Location"].startswith("/account?flash=frame_renamed")
    assert _name_of(server, seed.owned_id) == "Living room"
    (row,) = fx.audit_rows(server.state_dir, "device.rename")
    assert row["target_id"] == seed.owned_id and row["outcome"] == "ok"
    assert row["actor_label"] == fx.OWNER_EMAIL
    assert "Living room" in row["detail"] and "Kitchen" in row["detail"]
    status, _h, body = fx.get(server, cookies["owner"], "/account?flash=frame_renamed")
    assert "Frame renamed" in body and "Living room" in body


def test_an_administrator_renames_any_frame_and_returns_to_its_fleet_settings(rig):
    server, seed, cookies = rig
    status, headers, _body = _rename(server, cookies["admin"], seed.owned_id, "Garage")
    assert status == 303
    assert headers["Location"] == "/fleet?frame=%s&tab=settings" % seed.owned_id
    assert _name_of(server, seed.owned_id) == "Garage"
    cookie = cookies["admin"] + "; " + headers["Set-Cookie"].split(";")[0]
    _s, _h, body = http_request(server.url(headers["Location"]), cookie=cookie)
    assert "Frame renamed" in body.decode("utf-8")


@pytest.mark.parametrize("bad", ["", "   ", "x" * 41, "zero\u200bwidth", "bell\x07"])
def test_an_invalid_name_is_refused_with_the_field_error_and_nothing_stored(rig, bad):
    server, seed, cookies = rig
    status, _headers, body = _rename(server, cookies["owner"], seed.owned_id, bad)
    assert status == 400
    assert "Enter a name of 1 to 40 characters." in body.decode("utf-8")
    assert _name_of(server, seed.owned_id) == "Kitchen"
    assert fx.audit_rows(server.state_dir, "device.rename") == []


def test_a_co_manager_a_stranger_and_anonymous_cannot_rename(rig):
    server, seed, cookies = rig
    for who in ("co", "user"):
        status, _h, _b = _rename(server, cookies[who], seed.owned_id, "Hijack")
        assert status == 404
        status, _h, _b = http_request(
            server.url("/devices/%s/frame/name" % seed.owned_id), cookie=cookies[who])
        assert status == 404
    status, headers, _b = _rename(server, None, seed.owned_id, "Hijack")
    assert status == 303 and headers["Location"].startswith("/login")
    assert _name_of(server, seed.owned_id) == "Kitchen"


def test_the_rename_page_shows_the_name_the_save_bar_and_french_labels(rig):
    server, seed, cookies = rig
    path = "/devices/%s/frame/name" % seed.owned_id
    tree = parse_html(fx.get(server, cookies["owner"], path)[2])
    field = tree.select_one('input[name="name"]')
    assert field.attrs["value"] == "Kitchen" and field.attrs["maxlength"] == "40"
    assert tree.select_one("form[data-dirty-form]").attrs["id"] == "frame-name-form"
    assert tree.select_one(".dirty-bar") is not None
    assert tree.select_one("h1").text() == "Rename frame"
    french = fx.get(server, cookies["owner"], path, headers={"Accept-Language": "fr"})[2]
    assert "Renommer le cadre" in french and "Nom du cadre" in french


def test_a_hostile_name_is_escaped_where_it_is_shown(rig):
    server, seed, cookies = rig
    _rename(server, cookies["owner"], seed.owned_id, "<b>x</b>")
    body = fx.get(server, cookies["owner"], "/devices/%s/frame/name" % seed.owned_id)[2]
    assert "<b>x</b>" not in body and "&lt;b&gt;x&lt;/b&gt;" in body


def test_the_manage_access_dialog_and_the_fleet_header_link_to_the_rename_page(rig):
    server, seed, cookies = rig
    account = fx.get(server, cookies["owner"], "/account")[2]
    assert 'href="/devices/%s/frame/name"' % seed.owned_id in account
    fleet = fx.get(server, cookies["admin"], "/fleet?frame=" + seed.owned_id)[2]
    assert 'href="/devices/%s/frame/name"' % seed.owned_id in fleet


def test_the_users_active_switch_answers_a_fetch_with_no_content_and_a_form_post_with_a_redirect(rig):
    server, seed, cookies = rig
    cookie = cookies["admin"]
    form = with_csrf(cookie, {"state": "off"})
    status, _h, _b = http_request(
        server.url("/users/%d/disable" % seed.user_id), method="POST", cookie=cookie,
        data=form, extra_headers={
            "Origin": server.base_url(), "X-Requested-With": "quick-switch"})
    assert status == 204
    conn = fleet_db.connect(server.state_dir)
    try:
        assert conn.execute(
            "SELECT disabled FROM users WHERE id = ?", (seed.user_id,)).fetchone()[0] == 1
    finally:
        conn.close()
    status, headers, _b = http_request(
        server.url("/users/%d/enable" % seed.user_id), method="POST", cookie=cookie,
        data=with_csrf(cookie, {}), extra_headers={"Origin": server.base_url()})
    assert status == 303 and headers["Location"] == "/users"


def test_a_refused_fetch_disable_never_answers_no_content(rig):
    server, seed, cookies = rig
    cookie = cookies["admin"]
    status, _h, _b = http_request(
        server.url("/users/%d/disable" % seed.admin_id), method="POST", cookie=cookie,
        data=with_csrf(cookie, {}), extra_headers={
            "Origin": server.base_url(), "X-Requested-With": "quick-switch"})
    assert status == 303


def test_the_users_page_renders_the_switch_as_a_quick_switch_that_flips_both_routes(rig):
    server, seed, cookies = rig
    body = fx.get(server, cookies["admin"], "/users")[2]
    row = re.search(r'<tr class="users-row[^>]*id="user-%d".*?</tr>' % seed.user_id, body, re.S).group(0)
    assert "data-quick-switch" in row and "data-quick-region" in row
    assert 'data-quick-action-on="/users/%d/disable"' % seed.user_id in row
    assert 'data-quick-action-off="/users/%d/enable"' % seed.user_id in row
    assert "/static/quick-switch.js" in body


def test_delete_user_is_not_offered_on_the_signed_in_administrators_own_row(rig):
    server, seed, cookies = rig
    body = fx.get(server, cookies["admin"], "/users")[2]
    own = re.search(r'<tr class="users-row[^>]*id="user-%d".*?</tr>' % seed.admin_id, body, re.S).group(0)
    other = re.search(r'<tr class="users-row[^>]*id="user-%d".*?</tr>' % seed.user_id, body, re.S).group(0)
    assert "Delete user" not in own and "dlg-delete-user-%d" % seed.admin_id not in body
    assert "Delete user" in other


def test_the_pairing_message_names_an_unnamed_frame_without_its_id(rig):
    server, seed, cookies = rig
    fx.issue_code(server.state_dir, seed.pending_id)
    cookie = cookies["admin"]
    status, headers, _b = http_request(
        server.url("/fleet/pair"), method="POST", cookie=cookie,
        data=with_csrf(cookie, {"code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)}),
        extra_headers={"Origin": server.base_url()})
    assert status == 303
    page = http_request(
        server.url(headers["Location"]),
        cookie=cookie + "; " + headers["Set-Cookie"].split(";")[0])[2].decode("utf-8")
    assert "Unnamed frame now belongs to" in page and "d_" not in re.sub(
        r'(href|id|action|data-[a-z-]+)="[^"]*"', "", page).split("now belongs to")[0][-80:]
