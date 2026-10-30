"""Tests for test-support/fake_auth0.py, driven over real loopback HTTP."""

import base64
import hashlib
import http.client
import json
import time
import urllib.parse

import pytest

from fake_auth0 import FakeAuth0

CLIENT_ID = "client-abc"
SECRET = "secret-xyz"
REDIRECT = "http://127.0.0.1:9/callback"
LOGIN = "http://127.0.0.1:9/login"


@pytest.fixture
def fake():
    server = FakeAuth0(CLIENT_ID, SECRET, REDIRECT, [LOGIN]).start()
    yield server
    server.stop()


def request(fake, method, path, form=None):
    conn = http.client.HTTPConnection("127.0.0.1", fake.port, timeout=5)
    body = urllib.parse.urlencode(form) if form is not None else None
    headers = {"Content-Type": "application/x-www-form-urlencoded"} if form else {}
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    data = resp.read().decode()
    result = (resp.status, resp.getheader("Location"), data)
    conn.close()
    return result


def challenge_for(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorize_params(**overrides):
    params = {"response_type": "code", "client_id": CLIENT_ID,
              "redirect_uri": REDIRECT, "scope": "openid email",
              "state": "st", "nonce": "no", "code_challenge": challenge_for("v"),
              "code_challenge_method": "S256"}
    params.update(overrides)
    return {k: v for k, v in params.items() if v is not None}


def authorize(fake, **overrides):
    query = urllib.parse.urlencode(authorize_params(**overrides))
    return request(fake, "GET", "/authorize?" + query)


def login(fake, **overrides):
    status, location, _ = authorize(fake, **overrides)
    assert status == 302
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))


def token_form(code, **overrides):
    form = {"grant_type": "authorization_code", "client_id": CLIENT_ID,
            "client_secret": SECRET, "code": code, "code_verifier": "v",
            "redirect_uri": REDIRECT}
    form.update(overrides)
    return form


def exchange(fake, code, **overrides):
    return request(fake, "POST", "/oauth/token", token_form(code, **overrides))


def decode_token(token):
    header, payload, _sig = token.split(".")

    def load(part):
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))

    return load(header), load(payload), _sig


def id_token(fake):
    query = login(fake)
    status, _, body = exchange(fake, query["code"])
    assert status == 200
    return json.loads(body)["id_token"]


# --- authorize ---

def test_authorize_redirects_with_code_and_state(fake):
    status, location, _ = authorize(fake)
    assert status == 302
    assert location.startswith(REDIRECT + "?")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))
    assert query["state"] == "st" and query["code"]


@pytest.mark.parametrize("override", [
    {"client_id": "other"},
    {"redirect_uri": "http://127.0.0.1:9/elsewhere"},
    {"code_challenge_method": "plain"},
    {"state": None},
    {"scope": "email"},
    {"response_type": "token"},
])
def test_authorize_refuses_bad_requests(fake, override):
    assert authorize(fake, **override)[0] == 400


# --- token ---

def test_token_success_shape(fake):
    query = login(fake)
    status, _, body = exchange(fake, query["code"])
    doc = json.loads(body)
    assert status == 200
    assert {"id_token", "access_token", "token_type", "expires_in"} <= set(doc)


def test_wrong_verifier_replay_secret_and_redirect(fake):
    code = login(fake)["code"]
    assert exchange(fake, code, code_verifier="wrong")[0] == 400
    code = login(fake)["code"]
    assert exchange(fake, code, client_secret="nope")[0] == 401
    code = login(fake)["code"]
    assert exchange(fake, code, redirect_uri="http://127.0.0.1:9/x")[0] == 400
    code = login(fake)["code"]
    assert exchange(fake, code)[0] == 200
    status, _, body = exchange(fake, code)
    assert status == 400 and "invalid_grant" in body


def test_id_token_header_and_claims(fake):
    fake.next_login(sub="auth0|abc", email="who@example.test",
                    email_verified=False)
    header, payload, sig = decode_token(id_token(fake))
    assert header == {"alg": "RS256", "typ": "JWT"}
    assert payload["iss"] == "http://%s/" % fake.domain
    assert payload["aud"] == CLIENT_ID
    assert payload["sub"] == "auth0|abc"
    assert payload["email"] == "who@example.test"
    assert payload["email_verified"] is False
    assert payload["nonce"] == "no"
    assert payload["exp"] > payload["iat"]
    assert sig == "junk-signature"


# --- logout and call log ---

def test_logout_allow_list(fake):
    query = urllib.parse.urlencode({"client_id": CLIENT_ID, "returnTo": LOGIN})
    status, location, _ = request(fake, "GET", "/v2/logout?" + query)
    assert (status, location) == (302, LOGIN)
    bad = urllib.parse.urlencode(
        {"client_id": CLIENT_ID, "returnTo": "http://evil.example.test/"})
    assert request(fake, "GET", "/v2/logout?" + bad)[0] == 400


def test_calls_are_ordered_and_elide_secrets(fake):
    code = login(fake)["code"]
    exchange(fake, code)
    assert [c[:2] for c in fake.calls] == [
        ("GET", "/authorize"), ("POST", "/oauth/token")]
    logged = repr(fake.calls)
    assert SECRET not in logged and code not in logged


# --- knobs ---

def minted_payload(fake, **claims):
    fake.set_knob("claims", claims)
    return decode_token(id_token(fake))[1]


def test_claim_overrides_and_removals(fake):
    payload = minted_payload(fake, iss="https://x/", aud="y", azp="z",
                             nonce="n", exp=1, iat=2, sub=None)
    assert payload["iss"] == "https://x/" and payload["aud"] == "y"
    assert payload["azp"] == "z" and payload["nonce"] == "n"
    assert payload["exp"] == 1 and payload["iat"] == 2
    assert "sub" not in payload


def test_alg_none_knob(fake):
    fake.set_knob("alg", "none")
    assert decode_token(id_token(fake))[0]["alg"] == "none"


def test_issuer_host_knob(fake):
    fake.set_knob("issuer_host", "localhost:1234")
    assert decode_token(id_token(fake))[1]["iss"] == "http://localhost:1234/"


def test_redirect_state_and_error_knobs(fake):
    fake.set_knob("redirect_state", "other")
    assert login(fake)["state"] == "other"
    fake.clear_knobs()
    fake.set_knob("redirect_error", "access_denied")
    query = login(fake)
    assert query["error"] == "access_denied" and "code" not in query


def test_token_status_body_and_omit_knobs(fake):
    fake.set_knob("token_status", 500)
    assert exchange(fake, login(fake)["code"])[0] == 500
    fake.clear_knobs()
    fake.set_knob("token_body", "not json")
    status, _, body = exchange(fake, login(fake)["code"])
    assert (status, body) == (200, "not json")
    fake.clear_knobs()
    fake.set_knob("omit_id_token", True)
    _, _, body = exchange(fake, login(fake)["code"])
    assert "id_token" not in json.loads(body)


def test_token_delay_knob(fake):
    fake.set_knob("token_delay_s", 0.3)
    code = login(fake)["code"]
    started = time.monotonic()
    exchange(fake, code)
    assert time.monotonic() - started >= 0.3


def test_reuse_code_knob(fake):
    fake.set_knob("reuse_code", True)
    code = login(fake)["code"]
    assert exchange(fake, code)[0] == 200
    assert exchange(fake, code)[0] == 200


def test_wrong_redirect_uri_knob(fake):
    fake.set_knob("wrong_redirect_uri", "http://127.0.0.1:9/other")
    assert exchange(fake, login(fake)["code"])[0] == 400


def test_unknown_knob_rejected(fake):
    with pytest.raises(KeyError):
        fake.set_knob("nonsense", 1)


def test_register_with_env(fake):
    env = fake.register_with_env({"KEEP": "1"})
    assert env["KEEP"] == "1"
    assert env["SKYPANE_AUTH0_DOMAIN"] == fake.domain
    assert env["SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK"] == "1"
    assert env["SKYPANE_AUTH0_CLIENT_ID"] == CLIENT_ID
