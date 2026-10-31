"""The Account page and a plain user's whole experience over real HTTP: the
page itself, uniform 404s for everything else, a coherent error-page shell
and preference redirects that stay on /account.
"""
import hashlib
import json
import os
import re
import urllib.parse

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, routes
from companion.pages import account_page
from companion_app_server import http_request
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
        data=urllib.parse.urlencode(form or {}).encode(), extra_headers=extra)


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


def test_anonymous_account_redirects_to_bare_login(server):
    status, headers, _body = _get(server, "/account")
    assert status == 303
    assert headers["Location"] == "/login"


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


def test_every_admin_get_is_the_same_404_as_an_unknown_path(server, user_cookie):
    reference = _get(server, "/no-such-page-at-all", user_cookie)
    assert reference[0] == 404
    paths = _admin_get_paths()
    assert "/health" in paths and "/" in paths
    for path in paths:
        status, _headers, body = _get(server, path, user_cookie)
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
        target in ("/account", "/logout", "/ui-theme", "/ui-lang")
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


def _frames_card(body):
    return parse_html(body).select("section.page-section")[2]


def test_a_user_with_no_frames_sees_the_unchanged_empty_state(server, user_cookie):
    card = _frames_card(_get(server, "/account", user_cookie)[2])
    assert card.select_one("h2").text() == "Frames"
    assert card.select_one(".empty-state__heading").text() == "Your frames will appear here"


def test_a_user_sees_their_own_frames_ordered_by_name_with_an_open_link(fleet_server):
    server, seeded, second, cookies = fleet_server
    status, _headers, body = _get(server, "/account", cookies["owner"])
    assert status == 200
    card = _frames_card(body)
    assert card.select_one("h2").text() == "Your frames"
    rows = card.select("li.data-card")
    assert len(rows) == 2
    names = [row.select_one(".text-heading").text() for row in rows]
    assert names == sorted(names, key=str.casefold)
    hrefs = [row.select_one("a.text-link").attrs["href"] for row in rows]
    assert sorted(hrefs) == sorted([
        "/devices/%s/" % seeded.owner_device, "/devices/%s/" % second])
    attic = rows[names.index("Attic")]
    assert "Last contact" in attic.text()
    assert attic.select_one(".time-value") is not None
    assert "Battery" in attic.text() and "%" in attic.text()
    assert hardware.REGISTRY[hardware.LEGACY_KEY].label in attic.text()


def test_the_page_never_shows_another_users_frame_or_internals(fleet_server):
    server, seeded, second, cookies = fleet_server
    body = _get(server, "/account", cookies["owner"])[2]
    assert seeded.other_device not in body
    for secret in _SECRETS + ("aa:bb:cc:dd:ee", "firmware"):
        assert secret not in body
    stripped = body.replace("/devices/%s/" % seeded.owner_device, "").replace(
        "/devices/%s/" % second, "")
    assert seeded.owner_device not in stripped and second not in stripped
    other_body = _get(server, "/account", cookies["other"])[2]
    assert second not in other_body and seeded.owner_device not in other_body


def test_an_admin_sees_only_the_frames_they_own_on_the_account_page(fleet_server):
    server, seeded, second, cookies = fleet_server
    body = _get(server, "/account", cookies["admin"])[2]
    card = _frames_card(body)
    assert card.select_one(".empty-state__heading").text() == "Your frames will appear here"
    assert seeded.owner_device not in body and seeded.other_device not in body
    assert 'href="/devices/' not in body


def test_the_frames_card_is_translated_to_french():
    frame = account_page.FrameSummary("Salon", "XIAO", None, 80, "/devices/d_00000001/")
    from companion import prefs
    prefs.set_request_prefs(lang="fr")
    try:
        html = account_page.render(account_page.Identity("a@b.c", "user"), frames=[frame])
    finally:
        prefs.set_request_prefs(lang="en")
    for text in ("Vos cadres", "Dernier contact", "Aucun contact pour l’instant",
                 "Ouvrir", "Batterie"):
        assert text in html
