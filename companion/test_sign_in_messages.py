"""The sign-in refusal and failure messages and the first-arrival welcome,
through a real in-process companion and the loopback fake Auth0. The
unverified-email page is chosen from the sign-in outcome's reason, after the
identity lookup, so which sign-ins are accepted is unchanged.
"""
import html
import re

import pytest

import companion_markup
from companion_app_server import http_request, http_request_full, login_via_auth0
from server import fleet_db, hardware

_REFRESH_RE = re.compile(r'http-equiv="refresh" content="0;url=([^"]*)"')
_SECRET = "d" * 64
_WELCOME = "Welcome to SkyPane"


def _target(body):
    found = _REFRESH_RE.search(body.decode("utf-8"))
    assert found, "no meta refresh in the page"
    return html.unescape(found.group(1))


def _toast(body):
    doc = companion_markup.parse_html(body.decode("utf-8"))
    return companion_markup.toast_title_detail(doc.select_one(".toast--docked"))


def _add_frame(state_dir, owner_id):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        return fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:01", _SECRET, hardware.LEGACY_KEY, owner_id,
            name="Alpha", state_path="auto")
    finally:
        conn.close()


def _page(rig, target, cookie):
    status, _, body = http_request(rig.server.url(target), cookie=cookie)
    assert status == 200
    return body.decode("utf-8")


# --- unverified email ----------------------------------------------------

def test_unlinked_unverified_identity_gets_the_confirm_page_and_no_session(auth0_rig):
    rig = auth0_rig
    rig.invite("pending@example.test", "user")
    result = login_via_auth0(
        rig.server, rig.fake, sub="auth0|new", email="pending@example.test",
        email_verified=False)
    assert result.status == 403
    assert result.session_cookie is None
    assert rig.session_count() == 0
    assert rig.rows("SELECT COUNT(*) FROM users WHERE sub IS NOT NULL")[0][0] == 0
    title, detail = _toast(result.body)
    assert title == "Confirm your email address"
    assert "confirmed its email address" in detail
    assert b"can't sign in" not in result.body
    assert b"pending@example.test" not in result.body


def test_the_confirm_page_is_the_same_for_invited_and_unknown_emails(auth0_rig):
    rig = auth0_rig
    rig.invite("pending@example.test", "user")
    invited = login_via_auth0(
        rig.server, rig.fake, sub="auth0|a", email="pending@example.test",
        email_verified=False)
    unknown = login_via_auth0(
        rig.server, rig.fake, sub="auth0|b", email="nobody@example.test",
        email_verified=False)
    assert invited.status == unknown.status == 403
    assert invited.body == unknown.body


def test_a_known_linked_identity_with_an_unverified_email_still_signs_in(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    first = login_via_auth0(rig.server, rig.fake, sub="auth0|known")
    assert first.status == 200
    again = login_via_auth0(
        rig.server, rig.fake, sub="auth0|known", email_verified=False)
    assert again.status == 200
    assert again.session_cookie is not None
    assert _target(again.body) == "/account"
    assert rig.user_count() == 1


def test_a_disabled_linked_identity_is_still_refused_whatever_its_verification(auth0_rig):
    rig = auth0_rig
    rig.invite("off@example.test", "user")
    login_via_auth0(rig.server, rig.fake, sub="auth0|off", email="off@example.test")
    conn = fleet_db.connect(rig.state_dir)
    try:
        conn.execute("UPDATE users SET disabled = 1 WHERE email = ?", ("off@example.test",))
        conn.commit()
    finally:
        conn.close()
    result = login_via_auth0(
        rig.server, rig.fake, sub="auth0|off", email="off@example.test",
        email_verified=False)
    assert result.status == 403
    assert result.session_cookie is None
    assert _toast(result.body)[0] == "This account can't sign in"


# --- not invited ---------------------------------------------------------

def test_not_invited_is_identical_for_unknown_disabled_and_linked_elsewhere(auth0_rig):
    rig = auth0_rig
    rig.invite("linked@example.test", "user", iss="https://other.example/", sub="auth0|other")
    rig.invite("off@example.test", "user", disabled=True)
    bodies = []
    for sub, email in (("auth0|1", "nobody@example.test"), ("auth0|2", "off@example.test"),
                       ("auth0|3", "linked@example.test")):
        result = login_via_auth0(rig.server, rig.fake, sub=sub, email=email)
        assert result.status == 403
        assert result.session_cookie is None
        bodies.append(result.body)
    assert len(set(bodies)) == 1
    assert _toast(bodies[0])[0] == "This account can't sign in"
    doc = companion_markup.parse_html(bodies[0].decode("utf-8"))
    assert doc.select_one("a.login-signin").attrs["href"] == "/login/auth0?prompt=login"


# --- provider text, cancellation, prompt -----------------------------------

def test_provider_error_text_is_never_echoed(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    hostile = "<script>alert(1)</script>"
    rig.fake.set_knob("redirect_error", hostile)
    result = login_via_auth0(rig.server, rig.fake)
    assert result.status == 303
    assert result.session_cookie is None
    assert "alert" not in result.headers["Location"]
    _status, _headers, page = http_request_full(rig.server.url(result.headers["Location"]))
    assert _toast(page) == (
        "Sign-in was cancelled", "Press Sign in whenever you are ready.")
    assert b"alert(1)" not in page
    assert b"user@example.test" not in page


def test_only_the_login_prompt_reaches_the_identity_provider(auth0_rig):
    rig = auth0_rig
    start = http_request_full(rig.server.url("/login/auth0?prompt=login"))
    assert start[0] == 303
    assert "prompt=login" in start[1].get("Location")
    for hostile in ("none", "consent", "login%0d%0aX:1", ""):
        reply = http_request_full(rig.server.url("/login/auth0?prompt=" + hostile))
        assert reply[0] == 303
        assert "prompt=" not in reply[1].get("Location")


# --- first arrival --------------------------------------------------------

def test_the_first_link_carries_one_welcome_and_the_next_sign_in_none(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    first = login_via_auth0(rig.server, rig.fake, sub="auth0|w")
    assert _target(first.body) == "/account?flash=welcome_account"
    page = _page(rig, "/account?flash=welcome_account", first.session_cookie)
    assert page.count(_WELCOME) == 1
    assert "Add your frame with the code shown on its screen." in page
    second = login_via_auth0(rig.server, rig.fake, sub="auth0|w")
    assert second.status == 200
    assert _target(second.body) == "/account"
    assert _WELCOME not in _page(rig, "/account", second.session_cookie)


def test_a_user_with_a_frame_is_welcomed_on_its_home(auth0_rig):
    rig = auth0_rig
    user_id = rig.invite("user@example.test", "user")
    frame = _add_frame(rig.state_dir, user_id)
    first = login_via_auth0(rig.server, rig.fake, sub="auth0|w")
    assert _target(first.body) == "/devices/%s/?flash=welcome" % frame
    page = _page(rig, "/devices/%s/?flash=welcome" % frame, first.session_cookie)
    assert page.count(_WELCOME) == 1
    assert "its dot tells you whether it is up to date" in page


def test_an_admin_is_welcomed_on_the_fleet_page_with_a_neutral_line(auth0_rig):
    rig = auth0_rig
    rig.invite("admin@example.test", "admin")
    first = login_via_auth0(
        rig.server, rig.fake, sub="auth0|adm", email="admin@example.test")
    assert _target(first.body) == "/fleet?flash=welcome_neutral"
    page = _page(rig, "/fleet?flash=welcome_neutral", first.session_cookie)
    assert page.count(_WELCOME) == 1
    assert "its dot tells you" not in page


def test_an_unknown_flash_token_renders_no_welcome(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    first = login_via_auth0(rig.server, rig.fake, sub="auth0|w")
    page = _page(rig, "/account?flash=%3Cb%3Ewelcome", first.session_cookie)
    assert _WELCOME not in page
    assert "<b>welcome" not in page


@pytest.mark.parametrize("route", ["/account", "/fleet"])
def test_a_welcome_token_without_a_session_shows_nothing(auth0_rig, route):
    status, _, body = http_request(
        auth0_rig.server.url(route + "?flash=welcome_neutral"))
    assert _WELCOME.encode() not in body
    assert status in (200, 303, 401, 403, 404)
