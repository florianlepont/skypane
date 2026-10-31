"""The Auth0 authorization-code sign-in against the loopback fake: the happy
paths, every way the callback can be hostile or broken, invite-only
refusals, the `next` whitelist and sign-out.

Runs against `auth0_rig` (an in-process companion plus FakeAuth0) so the
token-read timeout can be shortened and the Auth0 settings changed under
the live server. Assertions are on HTTP status, headers, fleet.db rows and
the served HTML.
"""
import hashlib
import html
import re
import threading
import time
import sqlite3
import urllib.parse

import pytest

from server import fleet_sessions

from companion import oidc, sign_in
from companion_app_server import (
    begin_auth0, http_request, http_request_full, login_via_auth0, named_cookie, set_cookie_headers)

REFRESH_RE = re.compile(r'http-equiv="refresh" content="0;url=([^"]*)"')
GENERIC_FAILURE_STATUSES = (400, 503)


def _refresh_target(body):
    match = REFRESH_RE.search(body.decode("utf-8"))
    assert match, "no meta refresh in the page"
    return html.unescape(match.group(1))


def _assert_refused(rig, result, statuses=GENERIC_FAILURE_STATUSES, user_sub=None):
    """No session cookie, no sessions row, no durable change to users."""
    assert result.status in statuses
    assert result.session_cookie is None
    assert rig.session_count() == 0
    assert rig.rows("SELECT COUNT(*) FROM users WHERE sub IS NOT NULL")[0][0] == 0
    cleared = named_cookie(result.headers, "sp_oidc")
    assert cleared == "sp_oidc="


# --- happy paths -----------------------------------------------------------

def test_invited_admin_signs_in_and_lands_on_home(auth0_rig):
    rig = auth0_rig
    rig.invite("admin@example.test", "admin")
    result = login_via_auth0(
        rig.server, rig.fake, sub="auth0|admin", email="admin@example.test")
    assert result.status == 200
    assert _refresh_target(result.body) == "/"
    token = result.session_cookie.split("=", 1)[1]
    assert rig.rows("SELECT id_hash, principal FROM sessions") == [
        (hashlib.sha256(token.encode()).hexdigest(), "user")]
    assert rig.rows("SELECT sub FROM users") == [("auth0|admin",)]


def test_invited_user_lands_on_account(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    result = login_via_auth0(rig.server, rig.fake)
    assert result.status == 200
    assert _refresh_target(result.body) == "/account"
    assert result.session_cookie is not None


def test_second_login_matches_on_sub_not_email(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    first = login_via_auth0(rig.server, rig.fake, sub="auth0|u1")
    assert first.status == 200
    second = login_via_auth0(
        rig.server, rig.fake, sub="auth0|u1", email="renamed@example.test",
        email_verified=False)
    assert second.status == 200
    assert rig.user_count() == 1


def test_login_rotates_the_previous_session(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    first = login_via_auth0(rig.server, rig.fake)
    second = login_via_auth0(rig.server, rig.fake, cookie=first.session_cookie)
    assert second.status == 200
    assert rig.session_count() == 1
    assert second.session_cookie != first.session_cookie


# --- hostile or broken callbacks ---------------------------------------------

def _now():
    return int(time.time())


FAILURE_KNOBS = {
    "wrong_iss": ("claims", {"iss": "http://evil.example/"}),
    "wrong_aud": ("claims", {"aud": "someone-else"}),
    "wrong_azp": ("claims", {"aud": ["test-client-id", "other"], "azp": "other"}),
    "wrong_nonce": ("claims", {"nonce": "not-the-nonce"}),
    "expired": ("claims", {"exp": _now() - 3600}),
    "future_iat": ("claims", {"iat": _now() + 3600}),
    "missing_sub": ("claims", {"sub": None}),
    "alg_none": ("alg", "none"),
    "token_500": ("token_status", 500),
    "token_not_json": ("token_body", "this is not json"),
    "no_id_token": ("omit_id_token", True),
    "wrong_redirect_uri": ("wrong_redirect_uri", "http://elsewhere.example/callback"),
    "provider_error": ("redirect_error", "access_denied"),
}


@pytest.mark.parametrize("case", sorted(FAILURE_KNOBS))
def test_broken_sign_in_creates_nothing(auth0_rig, case):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    knob, value = FAILURE_KNOBS[case]
    rig.fake.set_knob(knob, value)
    result = login_via_auth0(rig.server, rig.fake)
    _assert_refused(rig, result)
    assert b"user@example.test" not in result.body


def test_state_mismatch_never_reaches_the_token_endpoint(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    rig.fake.set_knob("redirect_state", "forged-state")
    result = login_via_auth0(rig.server, rig.fake)
    _assert_refused(rig, result)
    assert rig.fake.calls_to("/oauth/token") == []


def test_callback_without_the_prelogin_cookie_is_refused(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    _, _, _, callback_path = begin_auth0(rig.server, rig.fake)
    reply = http_request_full(rig.server.url(callback_path))
    assert reply[0] == 400
    assert named_cookie(reply[1], "sp_session") is None
    assert rig.session_count() == 0
    assert rig.fake.calls_to("/oauth/token") == []


def test_expired_attempt_is_refused(auth0_rig, monkeypatch):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    monkeypatch.setattr(sign_in, "ATTEMPTS", oidc.AttemptTable(ttl=0))
    result = login_via_auth0(rig.server, rig.fake)
    _assert_refused(rig, result)
    assert rig.fake.calls_to("/oauth/token") == []


def test_a_callback_works_once(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    _, _, attempt_cookie, callback_path = begin_auth0(rig.server, rig.fake)
    first = http_request_full(rig.server.url(callback_path), cookie=attempt_cookie)
    assert first[0] == 200
    replay = http_request_full(rig.server.url(callback_path), cookie=attempt_cookie)
    assert replay[0] == 400
    assert named_cookie(replay[1], "sp_session") is None
    assert rig.session_count() == 1
    assert len(rig.fake.calls_to("/oauth/token")) == 1


def test_a_replayed_code_on_a_fresh_attempt_is_refused(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    _, _, cookie_a, path_a = begin_auth0(rig.server, rig.fake)
    assert http_request_full(rig.server.url(path_a), cookie=cookie_a)[0] == 200
    old_code = urllib.parse.parse_qs(urllib.parse.urlsplit(path_a).query)["code"][0]
    _, _, cookie_b, path_b = begin_auth0(rig.server, rig.fake)
    state_b = urllib.parse.parse_qs(urllib.parse.urlsplit(path_b).query)["state"][0]
    forged = "/callback?" + urllib.parse.urlencode({"code": old_code, "state": state_b})
    reply = http_request_full(rig.server.url(forged), cookie=cookie_b)
    assert reply[0] == 400
    assert named_cookie(reply[1], "sp_session") is None
    assert rig.session_count() == 1


def test_a_wrong_code_verifier_is_refused(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    start = http_request_full(rig.server.url("/login/auth0"))
    cookie = named_cookie(start[1], "sp_oidc")
    location = urllib.parse.urlsplit(start[1]["Location"])
    params = dict(urllib.parse.parse_qsl(location.query))
    params["code_challenge"] = "A" * 43
    hop = http_request_full(
        "%s://%s%s?%s" % (location.scheme, location.netloc, location.path,
                          urllib.parse.urlencode(params)))
    back = urllib.parse.urlsplit(hop[1]["Location"])
    reply = http_request_full(
        rig.server.url(back.path + "?" + back.query), cookie=cookie)
    assert reply[0] == 400
    assert named_cookie(reply[1], "sp_session") is None
    assert rig.session_count() == 0


def test_a_slow_token_endpoint_answers_unavailable(auth0_rig, monkeypatch):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    monkeypatch.setattr(oidc, "TOKEN_READ_TIMEOUT", 0.3)
    rig.fake.set_knob("token_delay_s", 1.5)
    result = login_via_auth0(rig.server, rig.fake)
    _assert_refused(rig, result, statuses=(503,))


# --- invite-only -------------------------------------------------------------

def _refusal_body(rig, **identity):
    result = login_via_auth0(rig.server, rig.fake, **identity)
    assert result.status == 403
    assert result.session_cookie is None
    assert rig.session_count() == 0
    return result.body


def test_every_uninvited_identity_gets_the_same_403(auth0_rig):
    rig = auth0_rig
    rig.invite("linked@example.test", "user", iss="https://other.example/", sub="auth0|other")
    rig.invite("off@example.test", "user", disabled=True)
    rig.invite("pending@example.test", "user")
    users_before = rig.user_count()
    bodies = [
        _refusal_body(rig, sub="auth0|nobody", email="nobody@example.test"),
        _refusal_body(rig, sub="auth0|x", email="pending@example.test",
                      email_verified=False),
        _refusal_body(rig, sub="auth0|y", email="linked@example.test"),
        _refusal_body(rig, sub="auth0|z", email="off@example.test"),
    ]
    assert len(set(bodies)) == 1
    assert rig.user_count() == users_before
    for email in (b"nobody@example.test", b"pending@example.test",
                  b"linked@example.test", b"off@example.test"):
        assert email not in bodies[0]
    assert rig.rows("SELECT sub FROM users WHERE sub IS NOT NULL") == [("auth0|other",)]


def test_two_subs_racing_for_one_invitation_yield_one_session(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    attempts = []
    for sub in ("auth0|first", "auth0|second"):
        _, _, cookie, path = begin_auth0(
            rig.server, rig.fake, sub=sub, email="user@example.test")
        attempts.append((cookie, path))
    replies = []

    def fire(cookie, path):
        replies.append(http_request_full(rig.server.url(path), cookie=cookie))

    threads = [threading.Thread(target=fire, args=a) for a in attempts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r[0] for r in replies) == [200, 403]
    assert rig.session_count() == 1
    assert len(rig.rows("SELECT sub FROM users WHERE sub IS NOT NULL")) == 1


# --- next ----------------------------------------------------------------------

def test_an_admin_lands_on_a_whitelisted_next(auth0_rig):
    rig = auth0_rig
    rig.invite("admin@example.test", "admin")
    result = login_via_auth0(
        rig.server, rig.fake, next_route="/health", sub="auth0|a",
        email="admin@example.test")
    assert _refresh_target(result.body) == "/health"


@pytest.mark.parametrize("hostile", [
    "//evil.example", "https://evil.example", "/\\evil.example",
    "javascript:alert(1)", "%2F%2Fevil.example", "/health/../x", "/healthx",
    "/health?x=1", "",
])
def test_hostile_next_falls_back_to_the_default_landing(auth0_rig, hostile):
    rig = auth0_rig
    rig.invite("admin@example.test", "admin")
    result = login_via_auth0(
        rig.server, rig.fake, next_route=hostile, sub="auth0|a",
        email="admin@example.test")
    assert result.status == 200
    assert _refresh_target(result.body) == "/"


def test_a_user_ignores_an_admin_only_next(auth0_rig):
    rig = auth0_rig
    rig.invite("user@example.test", "user")
    result = login_via_auth0(rig.server, rig.fake, next_route="/health")
    assert _refresh_target(result.body) == "/account"


# --- unconfigured or malformed settings ------------------------------------------

def test_start_is_the_shared_404_when_auth0_is_unconfigured(auth0_rig):
    rig = auth0_rig
    rig.server.apply_env({
        "SKYPANE_AUTH0_DOMAIN": None, "SKYPANE_AUTH0_CLIENT_ID": None,
        "SKYPANE_AUTH0_CLIENT_SECRET": None})
    status, _, body = http_request(rig.server.url("/login/auth0"))
    _, _, unknown = http_request(rig.server.url("/no-such-page"))
    assert status == 404
    assert body == unknown


def test_partial_configuration_answers_unavailable_without_values(auth0_rig):
    rig = auth0_rig
    rig.server.apply_env({"SKYPANE_AUTH0_CLIENT_SECRET": None})
    status, _, body = http_request(rig.server.url("/login/auth0"))
    assert status == 503
    for leaked in (rig.fake.domain, rig.fake.client_id, rig.fake.client_secret):
        assert leaked.encode() not in body


# --- sign-out ---------------------------------------------------------------------

def _signed_in_user(rig):
    rig.invite("user@example.test", "user")
    return login_via_auth0(rig.server, rig.fake).session_cookie


def test_user_logout_ends_the_session_then_hops_to_auth0(auth0_rig):
    rig = auth0_rig
    cookie = _signed_in_user(rig)
    assert http_request(rig.server.url("/"), cookie=cookie)[0] == 404
    status, headers, body = http_request_full(
        rig.server.url("/logout"), method="POST", data=b"", cookie=cookie)
    assert status == 200
    assert any("sp_session=;" in c and "Max-Age=0" in c
               for c in set_cookie_headers(headers))
    target = urllib.parse.urlsplit(_refresh_target(body))
    assert target.netloc == rig.fake.domain
    assert target.path == "/v2/logout"
    query = dict(urllib.parse.parse_qsl(target.query))
    assert query == {"client_id": rig.fake.client_id,
                     "returnTo": rig.server.base_url() + "/login"}
    assert rig.session_count() == 0
    replay = http_request(rig.server.url("/"), cookie=cookie)
    assert replay[0] == 303
    assert replay[1]["Location"].startswith("/login")


def test_a_refused_auth0_hop_does_not_resurrect_the_session(auth0_rig):
    rig = auth0_rig
    cookie = _signed_in_user(rig)
    _, _, body = http_request_full(
        rig.server.url("/logout"), method="POST", data=b"", cookie=cookie)
    rig.fake.allowed_logout_urls = []
    assert http_request(_refresh_target(body))[0] == 400
    assert http_request(rig.server.url("/"), cookie=cookie)[0] == 303


def test_logout_without_auth0_redirects_to_login(auth0_rig):
    rig = auth0_rig
    cookie = _signed_in_user(rig)
    rig.server.apply_env({
        "SKYPANE_AUTH0_DOMAIN": None, "SKYPANE_AUTH0_CLIENT_ID": None,
        "SKYPANE_AUTH0_CLIENT_SECRET": None})
    status, headers, _ = http_request(
        rig.server.url("/logout"), method="POST", data=b"", cookie=cookie)
    assert status == 303
    assert headers["Location"] == "/login"
    assert rig.session_count() == 0


def test_login_page_offers_the_auth0_start_link(auth0_rig):
    status, _, body = http_request(auth0_rig.server.url("/login"))
    assert status == 200
    assert b'href="/login/auth0"' in body


# --- start throttle ---------------------------------------------------------------

def test_one_client_cannot_start_unlimited_sign_ins(auth0_rig, monkeypatch):
    rig = auth0_rig
    monkeypatch.setattr(sign_in, "START_THROTTLE", oidc.StartThrottle(limit=3))
    pending = begin_auth0(rig.server, rig.fake)
    for _ in range(2):
        assert http_request(rig.server.url("/login/auth0"))[0] == 303
    status, headers, body = http_request(rig.server.url("/login/auth0"))
    assert status == 429
    assert "Set-Cookie" not in headers
    assert b"Sign-in is not available right now" in body
    # The attempt begun before the flood still completes.
    _start, _authorize, attempt_cookie, callback_path = pending
    callback = http_request_full(rig.server.url(callback_path), cookie=attempt_cookie)
    assert callback[0] != 429


def test_start_throttle_window_slides_and_is_per_client():
    now = [1000.0]
    throttle = oidc.StartThrottle(clock=lambda: now[0], limit=2, window=60)
    assert throttle.allow("a") and throttle.allow("a")
    assert not throttle.allow("a")
    assert throttle.allow("b")
    now[0] += 61
    assert throttle.allow("a")


def test_start_throttle_table_stays_bounded():
    throttle = oidc.StartThrottle(limit=2, max_keys=8)
    for index in range(100):
        assert throttle.allow("client-%d" % index)
    assert len(throttle._starts) <= 8


def test_a_failure_storing_the_session_leaves_no_identity_link(auth0_rig, monkeypatch):
    rig = auth0_rig
    rig.invite("admin@example.test", "admin")

    def refuse(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(fleet_sessions, "_insert_session", refuse)
    result = login_via_auth0(
        rig.server, rig.fake, sub="auth0|admin", email="admin@example.test")
    assert result.status == 503
    assert result.session_cookie is None
    assert rig.rows("SELECT iss, sub FROM users") == [(None, None)]
    assert rig.rows("SELECT COUNT(*) FROM sessions") == [(0,)]
