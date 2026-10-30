"""Cookie attributes, the authorize request and application output of the
Auth0 sign-in, read from the real response bytes of a companion
subprocess against the loopback fake.
"""
import urllib.parse

from companion_app_server import (
    begin_auth0, http_request_full, login_via_auth0, named_cookie,
    set_cookie_headers)


def _raw_cookie(headers, name):
    for raw in set_cookie_headers(headers):
        if raw.startswith(name + "="):
            return raw
    return None


def _attributes(raw):
    parts = [p.strip() for p in raw.split(";")[1:]]
    return {p.split("=", 1)[0].lower(): (p.split("=", 1)[1] if "=" in p else True)
            for p in parts}


def test_prelogin_cookie_attributes(auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    start = http_request_full(rig.server.url("/login/auth0"))
    assert start[0] == 303
    attrs = _attributes(_raw_cookie(start[1], "sp_oidc"))
    assert attrs["httponly"] is True
    assert attrs["secure"] is True
    assert attrs["samesite"] == "Lax"
    assert attrs["path"] == "/callback"
    assert attrs["max-age"] == "600"


def test_authorize_request_is_pinned_to_the_registered_client(auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    start = http_request_full(rig.server.url("/login/auth0"))
    location = urllib.parse.urlsplit(start[1]["Location"])
    assert location.netloc == rig.fake.domain
    assert location.path == "/authorize"
    params = dict(urllib.parse.parse_qsl(location.query))
    assert params["redirect_uri"] == rig.server.base_url() + "/callback"
    assert params["code_challenge_method"] == "S256"
    assert params["response_type"] == "code"
    assert params["client_id"] == rig.fake.client_id
    assert params["scope"] == "openid email"
    assert params["state"] and params["nonce"] and params["code_challenge"]
    assert "audience" not in params
    assert "client_secret" not in params


def test_session_cookie_attributes_and_prelogin_cookie_cleared(auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    rig.invite("user@example.test", "user")
    result = login_via_auth0(rig.server, rig.fake)
    assert result.status == 200
    session = _attributes(_raw_cookie(result.headers, "sp_session"))
    assert session["httponly"] is True
    assert session["secure"] is True
    assert session["samesite"] == "Strict"
    assert session["path"] == "/"
    cleared = _attributes(_raw_cookie(result.headers, "sp_oidc"))
    assert cleared["max-age"] == "0"
    assert cleared["path"] == "/callback"
    assert cleared["samesite"] == "Lax"


def test_failed_callback_clears_the_prelogin_cookie_and_sets_no_session(
        auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    rig.fake.set_knob("redirect_error", "access_denied")
    result = login_via_auth0(rig.server, rig.fake)
    assert result.status == 400
    assert named_cookie(result.headers, "sp_session") is None
    assert _attributes(_raw_cookie(result.headers, "sp_oidc"))["max-age"] == "0"


def test_callback_responses_are_not_cacheable_and_send_no_referrer(
        auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    rig.invite("user@example.test", "user")
    result = login_via_auth0(rig.server, rig.fake)
    assert result.headers["Cache-Control"] == "no-store"
    assert b'<meta name="referrer" content="no-referrer">' in result.body


def test_application_output_never_carries_secrets_or_identity(auth0_subprocess_rig):
    rig = auth0_subprocess_rig
    rig.invite("user@example.test", "user")
    ok = login_via_auth0(rig.server, rig.fake, sub="auth0|logged-sub")
    assert ok.status == 200
    _, _, cookie, path = begin_auth0(
        rig.server, rig.fake, sub="auth0|stranger", email="stranger@example.test")
    refused = http_request_full(rig.server.url(path), cookie=cookie)
    assert refused[0] == 403
    rig.fake.set_knob("token_status", 500)
    _, _, cookie_b, path_b = begin_auth0(rig.server, rig.fake)
    http_request_full(rig.server.url(path_b), cookie=cookie_b)
    codes = [
        urllib.parse.parse_qs(urllib.parse.urlsplit(p).query)["code"][0]
        for p in (path, path_b)]
    output = rig.server.read_stdout()
    assert "companion: signed in: user" in output
    forbidden = codes + [
        rig.fake.client_secret, "user@example.test", "stranger@example.test",
        "auth0|logged-sub", "auth0|stranger", "eyJ"]
    for needle in forbidden:
        assert needle not in output, "application output leaks %r" % needle
