"""The Account page and a plain user's whole experience over real HTTP: the
page itself, uniform 404s for everything else, a coherent error-page shell
and preference redirects that stay on /account.
"""
import hashlib
import re
import urllib.parse

import pytest

from companion import app, routes
from companion_app_server import http_request
from server import fleet_db, fleet_sessions

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
