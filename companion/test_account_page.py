"""The Account page and a plain user's whole experience over real HTTP: the
page itself, uniform 404s for everything else, a coherent error-page shell
and preference redirects that stay on /account.
"""
import hashlib
import json
import os
import re

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, routes
from companion.pages import account_page
from companion_app_server import http_request, with_csrf
from companion_markup import parse_html
from server import device_dirs, fleet_db, fleet_sessions, hardware

_THEME_RESPONSES = ("/ui-theme", "/ui-lang")
_HREF_RE = re.compile(r'href="([^"]*)"')
_ACTION_RE = re.compile(r'action="([^"]*)"')


def _seed_session(state_dir, role="user", token=None):
    token = token or "tok-%s" % role
    conn = fleet_db.connect(state_dir)
    try:
        user_id = fleet_db.add_user(conn, "%s@example.com" % role, role)
        fleet_sessions.create_session(
            conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
            principal="user", now=app._now())
    finally:
        conn.close()
    return "sp_session=%s" % token


@pytest.fixture
def server(app_server_in_process):
    return app_server_in_process


@pytest.fixture
def user_cookie(server):
    return _seed_session(server.state_dir, "user")


@pytest.fixture
def admin_cookie(server):
    return _seed_session(server.state_dir, "admin")


def _get(server, path, cookie=None):
    status, headers, body = http_request(server.url(path), cookie=cookie)
    return status, headers, body.decode("utf-8", "replace")


def _post(server, path, cookie, form=None, referer=None):
    extra = {"Origin": server.base_url()}
    if referer:
        extra["Referer"] = server.url(referer)
    return http_request(
        server.url(path), method="POST", cookie=cookie,
        data=with_csrf(cookie, form), extra_headers=extra)


def test_user_sees_the_account_page_with_email_and_role(server, user_cookie):
    status, _headers, body = _get(server, "/account", user_cookie)
    assert status == 200
    assert "user@example.com" in body
    assert ">User<" in body
    assert "Your frames will appear here" in body
    assert 'action="/logout"' in body


def test_admin_can_open_account(server, admin_cookie):
    status, _headers, body = _get(server, "/account", admin_cookie)
    assert status == 200
    assert ">Administrator<" in body
    assert "banner__pill" not in body


def test_anonymous_account_redirects_to_login_keeping_the_page(server):
    status, headers, _body = _get(server, "/account")
    assert status == 303
    assert headers["Location"] == "/login?next=%2Faccount"


def test_signed_in_user_visiting_login_goes_to_account(server, user_cookie):
    status, headers, _body = _get(server, "/login", user_cookie)
    assert (status, headers["Location"]) == (303, "/account")


def _refused_to_a_user(route):
    """An admin-only route, or a device route in its un-prefixed form (the
    live frame), which only an admin reaches."""
    return route.access == routes.ADMIN_ONLY or route.device_scoped


def _admin_get_paths():
    paths = []
    for route in routes.ROUTES:
        if route.method != "GET" or not _refused_to_a_user(route):
            continue
        matcher = route.matcher
        if isinstance(matcher, routes.Exact):
            paths.append(matcher.path)
        else:
            paths.append(matcher.prefix + "sample" + matcher.suffix)
    return paths


def _admin_post_paths():
    paths = []
    for route in routes.ROUTES:
        if route.method != "POST" or not _refused_to_a_user(route):
            continue
        matcher = route.matcher
        if isinstance(matcher, routes.Exact):
            paths.append(matcher.path)
        else:
            paths.append(matcher.prefix + "a/b" + matcher.suffix)
    return paths


FRAME_PAGES_FOR_FRAMELESS = (
    "/", "/display", "/flights", "/airlines", "/detection",
    "/settings", "/history", "/preview", "/display/screen", "/display/layout", "/health", "/device", "/update")


def test_every_admin_get_is_the_same_404_as_an_unknown_path(server, user_cookie):
    reference = _get(server, "/no-such-page-at-all", user_cookie)
    assert reference[0] == 404
    paths = _admin_get_paths()
    assert "/health" in paths and "/" in paths
    for path in paths:
        status, headers, body = _get(server, path, user_cookie)
        if path in FRAME_PAGES_FOR_FRAMELESS:
            # A user with no frame is sent to the page that offers to add one.
            assert (status, headers["Location"]) == (303, "/account"), path
            continue
        assert (status, body) == (reference[0], reference[2]), path


def test_admin_posts_are_404_for_a_user_and_change_nothing(server, user_cookie):
    reference = _get(server, "/no-such-page-at-all", user_cookie)
    for path in _admin_post_paths():
        status, _headers, body = _post(server, path, user_cookie, {"x": "1"})
        assert status == 404, path
        assert body.decode("utf-8", "replace") == reference[2], path


def test_user_404_has_the_user_shell(server, user_cookie):
    _status, _headers, body = _get(server, "/no-such-page-at-all", user_cookie)
    assert "Back to Account" in body
    assert "Back to Home" not in body
    assert "nav-notification" not in body
    assert "/health" not in body


def test_anonymous_404_links_back_to_sign_in(server):
    status, _headers, body = _get(server, "/no-such-page-at-all")
    assert status == 404
    assert "Back to sign in" in body
    assert 'href="/login"' in body
    assert "Back to Home" not in body


def test_admin_404_keeps_back_to_home(server, admin_cookie):
    body = _get(server, "/no-such-page-at-all", admin_cookie)[2]
    assert "Back to Home" in body


def test_user_forbidden_page_says_back_to_account(server, user_cookie):
    status, _headers, body = http_request(
        server.url("/ui-theme"), method="POST", cookie=user_cookie, data=b"",
        extra_headers={"Origin": "http://evil.example"})
    assert status == 403
    assert "Back to Account" in body.decode()


def test_french_back_to_account(server, user_cookie):
    cookie = user_cookie + "; sp_ui_lang=fr"
    assert "Retour au compte" in _get(server, "/no-such-page-at-all", cookie)[2]


@pytest.mark.parametrize("path", _THEME_RESPONSES)
@pytest.mark.parametrize("referer", ["/account", "/health", "/", None])
def test_user_preference_posts_return_to_account(server, user_cookie, path, referer):
    form = {"ui_theme": "dark"} if path == "/ui-theme" else {"ui_lang": "fr"}
    status, headers, _body = _post(server, path, user_cookie, form, referer=referer)
    assert (status, headers["Location"]) == (303, "/account")


def test_admin_preference_return_is_unchanged(server, admin_cookie):
    form = {"ui_theme": "dark"}
    assert _post(server, "/ui-theme", admin_cookie, form, referer="/health")[1]["Location"] == "/health"
    assert _post(server, "/ui-theme", admin_cookie, form, referer="/nowhere")[1]["Location"] == "/"
    assert _post(server, "/ui-theme", admin_cookie, form, referer="/account")[1]["Location"] == "/account"


def _hrefs(body):
    return _HREF_RE.findall(body) + _ACTION_RE.findall(body)


def _is_allowed_user_target(target):
    return (
        target in (
            "/account", "/locations", "/logout", "/pair-frame", "/ui-theme", "/ui-lang")
        or target.startswith("/static/")
        or target == "/favicon.ico"
        or target.startswith("#"))


@pytest.mark.parametrize("path", ["/account", "/no-such-page-at-all"])
def test_every_target_in_a_user_page_is_reachable_for_a_user(server, user_cookie, path):
    body = _get(server, path, user_cookie)[2]
    targets = _hrefs(body)
    assert "/account" in targets
    for target in targets:
        if _is_allowed_user_target(target):
            continue
        # Any other target must be a static asset route the table serves
        # publicly (data: favicon links and the like carry no path).
        assert not target.startswith("/"), target


def test_user_nav_links_are_routes_a_user_may_open(server, user_cookie):
    body = _get(server, "/account", user_cookie)[2]
    by_target = {}
    for route in routes.ROUTES:
        if route.method == "GET" and isinstance(route.matcher, routes.Exact):
            by_target[route.matcher.path] = route.access
    for target in _hrefs(body):
        if target.startswith("/") and target in by_target:
            assert by_target[target].min_role in (routes.ANONYMOUS, routes.USER), target


# --- the caller's own frames ------------------------------------------------

_SECRETS = ("d" * 64, "e" * 64, "f" * 64)


@pytest.fixture
def fleet_server(server):
    """The seeded owner/other/admin fleet with a session per account, a
    second owned frame and a battery reading."""
    seeded = seed_matrix_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        second = fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:03", _SECRETS[0], hardware.LEGACY_KEY,
            seeded.owner_id, name="Attic", state_path="auto")
        cookies = {}
        for name, user_id in (
                ("owner", seeded.owner_id), ("other", seeded.other_id),
                ("admin", seeded.admin_id)):
            token = "tok-fleet-" + name
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                principal="user", now=app._now())
            cookies[name] = "sp_session=" + token
    finally:
        conn.close()
    state_dir = device_dirs.resolve_state_dir(server.state_dir, "devices/" + second)
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3900, "received_at": app._now()}, fh)
    return server, seeded, second, cookies


def _sections(body):
    return parse_html(body).select("section.group-block")


def _frames_card(body):
    return _sections(body)[0]


def test_my_frames_is_the_first_card_and_an_empty_account_shows_the_empty_state(
        server, user_cookie):
    body = _get(server, "/account", user_cookie)[2]
    card = _frames_card(body)
    assert card.attrs["aria-labelledby"] == "account-frames"
    assert card.select_one("h2").text() == "My frames"
    assert card.select_one(".group--panel .empty-state__heading").text() == (
        "Your frames will appear here")
    assert "The pairing code is shown on your frame's screen." in card.text()
    assert [(a.text(), a.attrs["href"]) for a in card.select("a")] == [
        ("Add your frame", "/pair-frame")]
    sections = _sections(body)
    assert [s.select_one("h2").text() for s in sections if s.select("h2")] == [
        "My frames", "Identity", "Preferences"]
    assert sections[-1].select_one("form[action='/logout'] button").text() == "Sign out"


def test_a_user_sees_their_own_frames_ordered_by_name_with_a_dot_and_manage_access(
        fleet_server):
    server, seeded, second, cookies = fleet_server
    status, _headers, body = _get(server, "/account", cookies["owner"])
    assert status == 200
    card = _frames_card(body)
    assert card.select_one("h2").text() == "My frames"
    rows = card.select("li.account-frame")
    assert len(rows) == 2
    assert [a.attrs["href"] for a in card.select("li.account-add-frame a.row__main")] == [
        "/pair-frame"]
    names = [
        row.select_one(".row__label").text().replace(
            row.select_one(".account-frame__role").text(), "").strip() for row in rows]
    assert names == sorted(names, key=str.casefold)
    hrefs = [row.select_one("a.row__main").attrs["href"] for row in rows]
    assert sorted(hrefs) == sorted([
        "/devices/%s/" % seeded.owner_device, "/devices/%s/" % second])
    attic = rows[names.index("Attic")]
    assert attic.select_one('.row__detail .account-frame__status [role="img"]') is not None
    assert attic.select_one(".row__main .account-frame__pic i") is not None
    last_seen_word = attic.select_one(".account-frame__status").text().split("Online")[-1]
    assert last_seen_word.startswith("Seen ") or "Not seen yet" in last_seen_word
    # A person has no use for the hardware model: only an administrator sees it.
    assert not attic.select(".account-frame__line")
    assert hardware.REGISTRY[hardware.LEGACY_KEY].label not in attic.text()
    (action,) = attic.select("a[data-modal-open]")
    assert action.text() == "Manage access"
    for banned in ("Last contact", "Battery", "%"):
        assert banned not in card.text()


def test_the_page_never_shows_another_users_frame_or_internals(fleet_server):
    server, seeded, second, cookies = fleet_server
    body = _get(server, "/account", cookies["owner"])[2]
    assert seeded.other_device not in body
    for secret in _SECRETS + ("aa:bb:cc:dd:ee", "firmware"):
        assert secret not in body
    other_body = _get(server, "/account", cookies["other"])[2]
    assert second not in other_body and seeded.owner_device not in other_body
    assert "dlg-access-" + seeded.owner_device.replace("_", "-") not in other_body


def test_an_admin_sees_only_the_frames_they_own_on_the_account_page(fleet_server):
    server, seeded, second, cookies = fleet_server
    body = _get(server, "/account", cookies["admin"])[2]
    card = _frames_card(body)
    assert card.select_one(".empty-state__heading").text() == "Your frames will appear here"
    assert seeded.owner_device not in body and seeded.other_device not in body
    assert 'href="/devices/' not in body


def test_an_administrator_still_sees_the_hardware_line_of_their_frame():
    from companion.pages import account_page
    frame = account_page.FrameSummary(
        name="Attic", hardware="XIAO ePaper EE02", href="/devices/d_1/", device_id="d_1")
    body = account_page.render(
        account_page.Identity("a@example.com", account_page.ROLE_ADMIN), frames=(frame,))
    user_body = account_page.render(
        account_page.Identity("a@example.com", "user"), frames=(frame,))
    assert 'class="account-frame__line">XIAO ePaper EE02<' in body
    assert "XIAO ePaper EE02" not in user_body


def test_a_co_manager_gets_leave_frame_and_the_server_refuses_them_access_changes(
        fleet_server):
    server, seeded, second, cookies = fleet_server
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.add_co_manager(conn, second, seeded.other_id, None)
    finally:
        conn.close()
    tree = parse_html(_get(server, "/account", cookies["other"])[2])
    attic = [r for r in tree.select("li.account-frame") if "Attic" in r.text()][0]
    assert [a.text() for a in attic.select("a[data-modal-open]")] == ["Leave frame"]
    assert "Shared by owner@example.test" in attic.text()
    assert not tree.select("dialog#dlg-access-" + second.replace("_", "-"))
    form = with_csrf(cookies["other"], {"email": "admin@example.com", "return_to": "/account"})
    status, _headers, _body = http_request(
        server.url("/devices/%s/co-managers/add" % second), method="POST",
        cookie=cookies["other"], data=form, extra_headers={"Origin": server.base_url()})
    assert status in (403, 404)


def test_the_my_frames_card_is_translated_to_french():
    from companion import prefs
    frame = account_page.FrameSummary(
        "Salon", "XIAO", "/devices/d_00000001/", "d_00000001", shared=True,
        owner_email="o@e.fr")
    prefs.set_request_prefs(lang="fr")
    try:
        html = account_page.render(account_page.Identity("a@b.c", "user"), frames=[frame])
        empty = account_page.render(account_page.Identity("a@b.c", "user"))
    finally:
        prefs.set_request_prefs(lang="en")
    for text in ("Mes cadres", "Partagé par o@e.fr", "Quitter le cadre"):
        assert text in html
    assert "Vos cadres apparaîtront ici" in empty
