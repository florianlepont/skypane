"""Rename a frame, the Active switch of the Users page answering a fetch, the
Update confirmation without a made-up time, the pairing message naming a frame
without a name, and the retired Update address under a frame prefix. Every
assertion reads served pages, audit rows and the database."""
import re
from urllib.parse import quote

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


def _slug(device_id):
    return "dlg-rename-" + device_id.replace("_", "-")


def _dialog(body, device_id):
    """The Rename dialog of `device_id` in a served page."""
    text = body.decode("utf-8") if isinstance(body, bytes) else body
    return parse_html(text).select_one("dialog#" + _slug(device_id))


def _follow(server, cookie, headers, **kwargs):
    """The page a redirect answer points at (its fragment is the browser's)."""
    return fx.get(server, cookie, headers["Location"].partition("#")[0], **kwargs)[2]


def _rename(server, cookie, device_id, name, return_to=None):
    fields = {"name": name}
    if return_to is not None:
        fields["return_to"] = return_to
    return http_request(
        server.url("/devices/%s/frame/name" % device_id), method="POST", cookie=cookie,
        data=with_csrf(cookie, fields),
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
def test_an_invalid_name_reopens_the_dialog_with_the_field_error_and_nothing_stored(rig, bad):
    server, seed, cookies = rig
    status, headers, _body = _rename(server, cookies["owner"], seed.owned_id, bad)
    assert status == 303
    assert "#" not in headers["Location"] and "rename=%s" % seed.owned_id in headers["Location"]
    dialog = _dialog(_follow(server, cookies["owner"], headers), seed.owned_id)
    assert "open" in dialog.attrs
    assert dialog.select_one(".field-error").text() == "Enter a name of 1 to 40 characters."
    field = dialog.select_one('input[name="name"]')
    assert field.attrs["aria-invalid"] == "true" and field.attrs["maxlength"] == "40"
    assert field.attrs["value"] == " ".join(bad.split())[:40]
    assert _name_of(server, seed.owned_id) == "Kitchen"
    assert fx.audit_rows(server.state_dir, "device.rename") == []


def test_a_refused_name_comes_back_as_typed_and_a_page_without_the_query_has_no_error(rig):
    server, seed, cookies = rig
    _status, headers, _b = _rename(server, cookies["owner"], seed.owned_id, "y" * 60)
    dialog = _dialog(_follow(server, cookies["owner"], headers), seed.owned_id)
    assert dialog.select_one('input[name="name"]').attrs["value"] == "y" * 40
    calm = _dialog(fx.get(server, cookies["owner"], "/account")[2], seed.owned_id)
    assert "open" not in calm.attrs and calm.select(".field-error") == []
    assert calm.select_one('input[name="name"]').attrs["value"] == "Kitchen"


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


def test_the_rename_dialog_shows_the_name_equal_buttons_and_french_labels(rig):
    server, seed, cookies = rig
    dialog = _dialog(fx.get(server, cookies["owner"], "/account")[2], seed.owned_id)
    field = dialog.select_one('input[name="name"]')
    assert field.attrs["value"] == "Kitchen" and field.attrs["maxlength"] == "40"
    assert dialog.attrs["class"] == "modal modal--compact modal--top"
    assert dialog.select_one("h2").text() == "Rename frame"
    assert dialog.select_one('button[type="submit"]').text() == "Save"
    assert dialog.select_one("a.modal__dismiss--button").text() == "Cancel"
    assert dialog.select_one("a.modal__dismiss--button").attrs["href"] == "/account"
    assert dialog.select_one('input[name="return_to"]').attrs["value"] == "/account"
    french = fx.get(server, cookies["owner"], "/account", headers={"Accept-Language": "fr"})[2]
    shown = _dialog(french, seed.owned_id)
    assert shown.select_one("h2").text() == "Renommer le cadre"
    assert "Nom du cadre" in shown.text()
    assert shown.select_one("a.modal__dismiss--button").text() == "Annuler"


@pytest.mark.parametrize("lang,help_text,purpose", [
    ("en", "Up to 40 characters.", "It is not shown on the frame."),
    ("fr", "40 caractères au maximum.", "Il n’est pas affiché sur le cadre.")])
def test_the_rename_dialog_carries_no_standing_help_or_purpose_sentence(rig, lang, help_text, purpose):
    server, seed, cookies = rig
    page = fx.get(
        server, cookies["owner"], "/account", headers={"Accept-Language": lang})[2]
    text = page.decode("utf-8") if isinstance(page, bytes) else page
    assert help_text not in text and purpose not in text
    dialog = _dialog(text, seed.owned_id)
    assert dialog.select(".text-label") == [] and dialog.select(".modal__subtitle") == []
    assert dialog.select_one('input[name="name"]').attrs["maxlength"] == "40"


@pytest.mark.parametrize("lang,shown", [("en", "Orly frame"), ("fr", "Cadre d’Orly")])
def test_the_first_frames_default_name_reads_one_way_on_every_page(rig, lang, shown):
    """the first frame keeps its default name until someone renames it, and that name reads
    in the viewer's language everywhere it is shown: Home's title, the frame list of Account
    and the Rename field all say the same thing"""
    server, seed, cookies = rig
    headers = {"Accept-Language": lang}
    live = "/devices/%s" % seed.live_id
    home = parse_html(fx.get(server, cookies["admin"], live + "/", headers=headers)[2])
    assert home.select_one("h1").text().strip() == shown
    account = parse_html(fx.get(server, cookies["admin"], "/account", headers=headers)[2])
    rows = [link.text() for link in account.select('.account-frame a[href="%s/"]' % live)]
    assert rows and all(shown in row for row in rows), rows
    other = "Cadre d’Orly" if lang == "en" else "Orly frame"
    assert other not in account.text()
    field = _dialog(
        fx.get(server, cookies["admin"], "/account", headers=headers)[2], seed.live_id)
    assert field.select_one('input[name="name"]').attrs["value"] == shown


def test_a_name_someone_gave_is_never_translated(rig):
    """once renamed, even to the English default wording of another frame, a name is shown as
    typed in every language"""
    server, seed, cookies = rig
    assert _rename(server, cookies["owner"], seed.owned_id, "Orly frame")[0] == 303
    french = _dialog(fx.get(
        server, cookies["owner"], "/account",
        headers={"Accept-Language": "fr"})[2], seed.owned_id)
    assert french.select_one('input[name="name"]').attrs["value"] == "Orly frame"
    account = fx.get(server, cookies["owner"], "/account", headers={"Accept-Language": "fr"})[2]
    assert "Orly frame" in parse_html(account).text() and "Cadre d’Orly" not in account


def test_a_hostile_name_is_escaped_where_it_is_shown(rig):
    server, seed, cookies = rig
    _rename(server, cookies["owner"], seed.owned_id, "<b>x</b>")
    body = fx.get(server, cookies["owner"], "/devices/%s/" % seed.owned_id)[2]
    assert "<b>x</b>" not in body and "&lt;b&gt;x&lt;/b&gt;" in body


def test_the_account_row_pencil_and_the_fleet_header_open_the_rename_dialog(rig):
    server, seed, cookies = rig
    slug = _slug(seed.owned_id)
    account = parse_html(fx.get(server, cookies["owner"], "/account")[2])
    link = account.select_one("li.account-frame a.account-frame__action[href='#%s']" % slug)
    assert link.attrs["aria-label"].startswith("Rename: ") and "data-modal-open" in link.attrs
    assert account.select_one("dialog#" + slug) is not None
    assert not account.select("a.access-rename__link")
    assert "Rename this frame" not in account.text()
    fleet = parse_html(fx.get(server, cookies["admin"], "/fleet?frame=" + seed.owned_id)[2])
    button = fleet.select_one(".fleet-head a.fleet-icon-button[data-modal-open]")
    assert button.attrs["href"] == "#" + slug
    dialog = fleet.select_one("dialog#" + slug)
    assert dialog.select_one('input[name="return_to"]').attrs["value"] == (
        "/fleet?frame=%s" % seed.owned_id)


def test_the_users_active_switch_answers_a_fetch_with_its_toast_and_a_form_post_with_a_redirect(rig):
    server, seed, cookies = rig
    cookie = cookies["admin"]
    form = with_csrf(cookie, {"state": "off"})
    status, headers, body = http_request(
        server.url("/users/%d/disable" % seed.user_id), method="POST", cookie=cookie,
        data=form, extra_headers={
            "Origin": server.base_url(), "X-Requested-With": "quick-switch"})
    assert status == 200
    assert headers["X-Quick-Switch-Result"] == "toast"
    assert "no-store" in headers["Cache-Control"]
    text = body.decode("utf-8")
    assert "User disabled" in text and fx.USER_EMAIL in text and "<script" not in text
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
        server.url("/pair-frame"), method="POST", cookie=cookie,
        data=with_csrf(cookie, {"code": fx.FAKE_CODE, "owner_user_id": str(seed.owner_id)}),
        extra_headers={"Origin": server.base_url()})
    assert status == 303
    page = http_request(
        server.url(headers["Location"]),
        cookie=cookie + "; " + headers["Set-Cookie"].split(";")[0])[2].decode("utf-8")
    assert "Unnamed frame now belongs to" in page and "d_" not in re.sub(
        r'(href|id|action|data-[a-z-]+)="[^"]*"', "", page).split("now belongs to")[0][-80:]


def _home_of(seed):
    return "/devices/%s/" % seed.owned_id


def test_save_returns_to_the_page_the_person_came_from(rig):
    server, seed, cookies = rig
    home = _home_of(seed)
    for who in ("owner", "admin"):
        status, headers, _b = _rename(server, cookies[who], seed.owned_id, "Den", home)
        assert status == 303
        assert headers["Location"] == home + "?flash=frame_renamed"
        assert "Set-Cookie" not in headers
    status, headers, _b = _rename(
        server, cookies["admin"], seed.owned_id, "Den", "/fleet?frame=%s" % seed.owned_id)
    assert status == 303
    assert headers["Location"] == "/fleet?frame=%s" % seed.owned_id
    assert "Set-Cookie" in headers


@pytest.mark.parametrize("hostile", [
    "https://evil.example/", "//evil.example/", "/\\evil.example", "javascript:alert(1)",
    "/not-a-page", "/devices/d_00000000/frame/name", "/account#x", ""])
def test_a_hostile_or_unknown_return_to_is_ignored(rig, hostile):
    server, seed, cookies = rig
    status, headers, _b = _rename(server, cookies["owner"], seed.owned_id, "Den", hostile)
    assert status == 303 and headers["Location"] == "/account?flash=frame_renamed"
    page_url = "/devices/%s/frame/name?return_to=%s" % (seed.owned_id, quote(hostile, safe=""))
    status, headers, _b = http_request(server.url(page_url), cookie=cookies["owner"])
    assert status == 303 and headers["Location"] == "/account#" + _slug(seed.owned_id)


def test_the_rename_route_sends_a_get_to_the_page_that_holds_the_dialog(rig):
    server, seed, cookies = rig
    home = "/account"
    url = "/devices/%s/frame/name?return_to=%s" % (seed.owned_id, quote(home, safe=""))
    status, headers, _b = http_request(server.url(url), cookie=cookies["owner"])
    assert status == 303 and headers["Location"] == home + "#" + _slug(seed.owned_id)
    dialog = _dialog(fx.get(server, cookies["owner"], home)[2], seed.owned_id)
    assert dialog.select_one('input[name="return_to"]').attrs["value"] == home
    assert dialog.select_one("a.modal__dismiss--button").attrs["href"] == home


def test_a_refused_name_keeps_the_origin(rig):
    server, seed, cookies = rig
    home = "/account"
    status, headers, _b = _rename(server, cookies["owner"], seed.owned_id, "", home)
    assert status == 303 and headers["Location"].startswith(home + "?rename=" + seed.owned_id)
    dialog = _dialog(_follow(server, cookies["owner"], headers), seed.owned_id)
    assert "open" in dialog.attrs
    assert dialog.select_one('input[name="return_to"]').attrs["value"] == home
    assert dialog.select_one("a.modal__dismiss--button").attrs["href"] == home


def test_a_normal_user_is_never_sent_to_a_console_page(rig):
    server, seed, cookies = rig
    url = "/devices/%s/frame/name?return_to=%s" % (seed.owned_id, quote("/fleet", safe=""))
    status, headers, _b = http_request(server.url(url), cookie=cookies["owner"])
    assert headers["Location"] == "/account#" + _slug(seed.owned_id)
    status, headers, _b = _rename(server, cookies["owner"], seed.owned_id, "Den", "/fleet")
    assert status == 303 and headers["Location"] == "/account?flash=frame_renamed"
    status, headers, _b = http_request(server.url(url), cookie=cookies["admin"])
    assert headers["Location"] == "/fleet#" + _slug(seed.owned_id)


def test_a_return_target_the_viewer_cannot_open_is_replaced_by_the_default(rig):
    server, seed, cookies = rig
    cancel = "/devices/%s/frame/name" % seed.owned_id
    for who, hidden in (("owner", "/devices/%s/" % seed.live_id), ("owner", "/components"),
                        ("co", "/devices/%s/" % seed.live_id)):
        status, headers, _b = _rename(
            server, cookies[who], seed.owned_id, "Study", return_to=hidden)
        if who == "co":
            assert status == 404
            continue
        assert status == 303 and headers["Location"] == "/account?flash=frame_renamed"
        status, headers, _b = http_request(
            server.url(cancel + "?return_to=" + quote(hidden, safe="")), cookie=cookies[who])
        assert headers["Location"] == "/account#" + _slug(seed.owned_id)


def test_a_return_target_the_viewer_can_open_is_kept(rig):
    server, seed, cookies = rig
    own_home = "/devices/%s/" % seed.owned_id
    status, headers, _b = _rename(server, cookies["owner"], seed.owned_id, "Study", return_to=own_home)
    assert status == 303 and headers["Location"] == own_home + "?flash=frame_renamed"
    status, headers, _b = _rename(server, cookies["admin"], seed.owned_id, "Study", return_to="/components")
    assert status == 303 and headers["Location"].startswith("/components")
    other = "/devices/%s/" % seed.live_id
    status, headers, _b = _rename(server, cookies["admin"], seed.owned_id, "Study", return_to=other)
    assert status == 303 and headers["Location"].startswith(other)


def test_a_rename_post_without_the_token_is_forbidden_not_redirected(rig):
    server, seed, cookies = rig
    status, headers, body = http_request(
        server.url("/devices/%s/frame/name" % seed.owned_id), method="POST",
        cookie=cookies["owner"], data=b"name=Study",
        extra_headers={"Origin": server.base_url()})
    assert status == 403 and "Location" not in headers
    assert _name_of(server, seed.owned_id) == "Kitchen"
