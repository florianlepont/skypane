"""Where each audience lands: the role landing after sign-in, the default
frame of a user, the 303 from an un-prefixed frame page to the same page
under that frame, and /login while signed in. Every check goes through a
real in-process server (fake Auth0), so the served redirects are asserted.
"""
import html
import re
import time

import pytest

from companion import access, device_scope
from companion_app_server import http_request, login_via_auth0
from access_matrix_support import session_cookie_for
from matrix_rows_landing import FRAME_PAGE_REDIRECTS
from server import fleet_db, fleet_sessions, hardware

_REFRESH_RE = re.compile(r'http-equiv="refresh" content="0;url=([^"]*)"')
_SECRET = "c" * 64


def _refresh_target(body):
    """The meta-refresh target without the first-sign-in welcome token."""
    found = _REFRESH_RE.search(body.decode("utf-8"))
    assert found, "no meta refresh in the page"
    return re.sub(r"[?&]flash=welcome\w*$", "", html.unescape(found.group(1)))


def _fallback_label(body):
    found = re.search(r'<a class="text-link login-card__link"[^>]*>([^<]*)</a>',
                      body.decode("utf-8"))
    assert found
    return html.unescape(found.group(1))


def _add_frame(state_dir, owner_id, name, index):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        return fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:%02x" % index, _SECRET, hardware.LEGACY_KEY,
            owner_id, name=name, state_path="auto")
    finally:
        conn.close()


def _sign_in(rig, email, role="user", sub="auth0|landing", **kwargs):
    rig.invite(email, role)
    return login_via_auth0(rig.server, rig.fake, sub=sub, email=email, **kwargs)


# --- landing after sign-in -------------------------------------------------

def test_an_admin_lands_on_the_fleet_page(auth0_rig):
    result = _sign_in(auth0_rig, "admin@example.test", "admin")
    assert _refresh_target(result.body) == "/fleet"
    assert _fallback_label(result.body) == "Continue to Fleet"


def test_a_user_with_frames_lands_on_the_first_frame_by_name(auth0_rig):
    user_id = auth0_rig.invite("user@example.test", "user")
    _add_frame(auth0_rig.state_dir, user_id, "bravo", 1)
    first = _add_frame(auth0_rig.state_dir, user_id, "Alpha", 2)
    _add_frame(auth0_rig.state_dir, user_id, "charlie", 3)
    result = login_via_auth0(
        auth0_rig.server, auth0_rig.fake, sub="auth0|u", email="user@example.test")
    assert _refresh_target(result.body) == "/devices/%s/" % first
    assert _fallback_label(result.body) == "Continue to Home"


def test_equal_frame_names_break_the_tie_on_the_id(auth0_rig):
    user_id = auth0_rig.invite("user@example.test", "user")
    ids = sorted(_add_frame(auth0_rig.state_dir, user_id, "Same", i) for i in (1, 2))
    result = login_via_auth0(
        auth0_rig.server, auth0_rig.fake, sub="auth0|u", email="user@example.test")
    assert _refresh_target(result.body) == "/devices/%s/" % ids[0]


def test_a_user_without_a_frame_lands_on_the_account_page(auth0_rig):
    result = _sign_in(auth0_rig, "user@example.test")
    assert _refresh_target(result.body) == "/account"
    assert _fallback_label(result.body) == "Continue to Account"


def test_a_validated_next_wins_for_a_user_with_a_frame(auth0_rig):
    user_id = auth0_rig.invite("user@example.test", "user")
    _add_frame(auth0_rig.state_dir, user_id, "Alpha", 1)
    result = login_via_auth0(
        auth0_rig.server, auth0_rig.fake, next_route="/flights",
        sub="auth0|u", email="user@example.test")
    assert _refresh_target(result.body) == "/flights"


@pytest.mark.parametrize("hostile", [
    "//evil.example", "https://evil.example", "/\\evil.example", "javascript:alert(1)"])
def test_an_external_next_is_ignored(auth0_rig, hostile):
    user_id = auth0_rig.invite("user@example.test", "user")
    frame = _add_frame(auth0_rig.state_dir, user_id, "Alpha", 1)
    result = login_via_auth0(
        auth0_rig.server, auth0_rig.fake, next_route=hostile,
        sub="auth0|u", email="user@example.test")
    assert _refresh_target(result.body) == "/devices/%s/" % frame


# --- default frame ----------------------------------------------------------

def test_the_default_frame_is_none_without_a_fleet_or_a_principal(tmp_path):
    admin = access.Principal(access.KIND_USER, 1, "a@example.test", access.ADMIN)
    assert device_scope.default_frame_for(str(tmp_path), admin) is None
    assert device_scope.default_frame_for(str(tmp_path), None) is None


# --- un-prefixed frame pages and /login ---------------------------------------

@pytest.fixture
def landing_rig(auth0_rig):
    rig = auth0_rig
    owner = rig.invite("owner@example.test", "user")
    other = rig.invite("other@example.test", "user")
    rig.invite("none@example.test", "user")
    admin = rig.invite("admin@example.test", "admin")
    keeper = rig.invite("keeper@example.test", "admin")
    rig.keeper_frame = _add_frame(rig.state_dir, keeper, "Keeper frame", 3)
    rig.frame = _add_frame(rig.state_dir, owner, "Mine", 1)
    rig.foreign = _add_frame(rig.state_dir, other, "Theirs", 2)
    now = int(time.time())
    rig.cookies = {
        email: session_cookie_for(
            rig.state_dir, fleet_sessions.PRINCIPAL_USER, uid, now)
        for email, uid in (
            ("owner", owner), ("other", other), ("admin", admin), ("keeper", keeper),
            ("none", rig.rows("SELECT id FROM users WHERE email = ?",
                              ("none@example.test",))[0][0]))}
    return rig


@pytest.mark.parametrize("page", FRAME_PAGE_REDIRECTS)
def test_a_user_is_moved_from_an_unprefixed_page_to_their_frame(landing_rig, page):
    status, headers, _b = http_request(
        landing_rig.server.url(page), cookie=landing_rig.cookies["owner"])
    assert status == 303
    assert headers["Location"] == "/devices/%s%s" % (landing_rig.frame, page)
    follow, _h, _b = http_request(
        landing_rig.server.url(headers["Location"]),
        cookie=landing_rig.cookies["owner"])
    assert follow == 200


@pytest.mark.parametrize("page", FRAME_PAGE_REDIRECTS)
def test_a_user_without_a_frame_keeps_the_404(landing_rig, page):
    status, _h, _b = http_request(
        landing_rig.server.url(page), cookie=landing_rig.cookies["none"])
    assert status == 404


def test_another_users_frame_path_stays_404(landing_rig):
    for page in ("/", "/display", "/flights"):
        path = "/devices/%s%s" % (landing_rig.foreign, page)
        status, _h, _b = http_request(
            landing_rig.server.url(path), cookie=landing_rig.cookies["owner"])
        assert status == 404


@pytest.mark.parametrize("page", FRAME_PAGE_REDIRECTS)
def test_an_admin_without_a_frame_is_moved_to_the_account_page(landing_rig, page):
    status, headers, _b = http_request(
        landing_rig.server.url(page), cookie=landing_rig.cookies["admin"])
    assert (status, headers["Location"]) == (303, "/account")


@pytest.mark.parametrize("page", FRAME_PAGE_REDIRECTS)
def test_an_admin_is_moved_to_their_default_frame_like_a_user(landing_rig, page):
    status, headers, _b = http_request(
        landing_rig.server.url(page), cookie=landing_rig.cookies["keeper"])
    assert status == 303
    assert headers["Location"] == "/devices/%s%s" % (landing_rig.keeper_frame, page)
    follow, _h, _b = http_request(
        landing_rig.server.url(headers["Location"]),
        cookie=landing_rig.cookies["keeper"])
    assert follow == 200


def test_an_admin_redirect_keeps_the_query_re_encoded(landing_rig):
    status, headers, _b = http_request(
        landing_rig.server.url("/airlines?resolve=A%26B&x=1"),
        cookie=landing_rig.cookies["keeper"])
    assert status == 303
    assert headers["Location"] == "/devices/%s/airlines?resolve=A%%26B&x=1" % (
        landing_rig.keeper_frame)


def test_an_admin_can_still_open_any_frame_by_its_id(landing_rig):
    for frame in (landing_rig.frame, landing_rig.foreign, landing_rig.keeper_frame):
        status, _h, _b = http_request(
            landing_rig.server.url("/devices/%s/" % frame),
            cookie=landing_rig.cookies["admin"])
        assert status == 200


@pytest.mark.parametrize("who", ["owner", "keeper"])
@pytest.mark.parametrize("hostile", [
    "//evil.example", "https://evil.example/x", "a%0d%0aLocation:%20//evil.example",
    "%5Cevil.example", "/%2F%2Fevil.example"])
def test_the_redirect_never_follows_request_text(landing_rig, who, hostile):
    status, headers, _b = http_request(
        landing_rig.server.url("/display?next=%s&x=%s" % (hostile, hostile)),
        cookie=landing_rig.cookies[who])
    assert status == 303
    location = headers["Location"]
    frame = landing_rig.frame if who == "owner" else landing_rig.keeper_frame
    assert location.startswith("/devices/%s/display?" % frame)
    assert not location.startswith("//")
    assert "\r" not in location and "\n" not in location
    assert "evil.example" not in location.split("?", 1)[0]
    assert "://" not in location and "\\" not in location


def test_the_redirect_ignores_request_text(landing_rig):
    status, headers, _b = http_request(
        landing_rig.server.url("/display?device=%s&x=//evil.example" % landing_rig.foreign),
        cookie=landing_rig.cookies["owner"])
    assert status == 303
    assert headers["Location"] == (
        "/devices/%s/display?device=%s&x=%%2F%%2Fevil.example" % (
            landing_rig.frame, landing_rig.foreign))
    follow, _h, _b = http_request(
        landing_rig.server.url(headers["Location"]),
        cookie=landing_rig.cookies["owner"])
    assert follow == 404


@pytest.mark.parametrize("who,expected", [
    ("admin", "/fleet"), ("none", "/account")])
def test_login_while_signed_in_goes_to_the_role_landing(landing_rig, who, expected):
    status, headers, _b = http_request(
        landing_rig.server.url("/login"), cookie=landing_rig.cookies[who])
    assert status == 303 and headers["Location"] == expected


def test_login_while_signed_in_sends_a_user_to_their_frame(landing_rig):
    status, headers, _b = http_request(
        landing_rig.server.url("/login"), cookie=landing_rig.cookies["owner"])
    assert status == 303
    assert headers["Location"] == "/devices/%s/" % landing_rig.frame


def test_login_while_signed_out_is_unchanged(landing_rig):
    status, _h, body = http_request(landing_rig.server.url("/login"))
    assert status == 200 and b"login-signin" in body


# --- error pages ----------------------------------------------------------------

def test_the_404_back_link_goes_to_the_frame_home_for_a_user_with_a_frame(landing_rig):
    status, _h, body = http_request(
        landing_rig.server.url("/no-such-page"), cookie=landing_rig.cookies["owner"])
    assert status == 404
    assert ('<a href="/devices/%s/">Back to Home</a>' % landing_rig.frame) \
        in body.decode("utf-8")


def test_the_404_back_link_goes_to_the_account_for_a_user_without_a_frame(landing_rig):
    _s, _h, body = http_request(
        landing_rig.server.url("/no-such-page"), cookie=landing_rig.cookies["none"])
    assert '<a href="/account">Back to Account</a>' in body.decode("utf-8")
