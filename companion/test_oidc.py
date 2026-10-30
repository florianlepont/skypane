"""Unit tests for companion/oidc.py (no network)."""

import base64
import json
import threading
import urllib.parse

import pytest

from companion import oidc

NOW = 1_800_000_000
NONCE = "nonce-value"
BASE_ENV = {
    "SKYPANE_AUTH0_DOMAIN": "tenant.example.test",
    "SKYPANE_AUTH0_CLIENT_ID": "client-abc",
    "SKYPANE_AUTH0_CLIENT_SECRET": "secret-xyz",
    "SKYPANE_COMPANION_HOST": "frame.example.test",
}


def cfg(**overrides):
    env = dict(BASE_ENV)
    env.update(overrides)
    return oidc.Auth0Config.from_env(env)


def b64(doc):
    raw = json.dumps(doc).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def good_payload(config):
    return {"iss": config.issuer, "aud": config.client_id, "sub": "auth0|1",
            "email": "a@example.test", "email_verified": True, "nonce": NONCE,
            "iat": NOW - 5, "exp": NOW + 3600}


def make_token(payload, header=None):
    header = header or {"alg": "RS256", "typ": "JWT"}
    return "%s.%s.sig" % (b64(header), b64(payload))


def validate(token, config=None):
    config = config or cfg()
    return oidc.validate_id_token(token, config, NONCE, now=NOW)


# --- config ---

def test_config_absent_is_none():
    assert oidc.Auth0Config.from_env({}) is None


def test_config_derives_urls():
    config = cfg()
    assert config.issuer == "https://tenant.example.test/"
    assert config.base_url == "https://tenant.example.test"
    assert config.redirect_uri == "https://frame.example.test/callback"
    assert config.return_to == "https://frame.example.test/login"


def test_config_public_url_override():
    config = cfg(SKYPANE_COMPANION_PUBLIC_URL="https://other.example.test/")
    assert config.redirect_uri == "https://other.example.test/callback"


@pytest.mark.parametrize("drop", [
    ["SKYPANE_AUTH0_CLIENT_SECRET"],
    ["SKYPANE_AUTH0_CLIENT_ID", "SKYPANE_AUTH0_CLIENT_SECRET"],
    ["SKYPANE_AUTH0_DOMAIN"],
])
def test_partial_config_names_missing_variables_only(drop):
    env = {k: v for k, v in BASE_ENV.items() if k not in drop}
    with pytest.raises(oidc.Auth0ConfigError) as err:
        oidc.Auth0Config.from_env(env)
    message = str(err.value)
    for name in drop:
        assert name in message
    for value in BASE_ENV.values():
        assert value not in message


def test_missing_public_address_is_an_error():
    env = {k: v for k, v in BASE_ENV.items() if k != "SKYPANE_COMPANION_HOST"}
    with pytest.raises(oidc.Auth0ConfigError) as err:
        oidc.Auth0Config.from_env(env)
    assert "SKYPANE_COMPANION_HOST" in str(err.value)
    assert "SKYPANE_COMPANION_PUBLIC_URL" in str(err.value)


def test_http_public_url_refused_without_flag():
    with pytest.raises(oidc.Auth0ConfigError):
        cfg(SKYPANE_COMPANION_PUBLIC_URL="http://127.0.0.1:9000")


def test_http_domain_with_scheme_refused():
    with pytest.raises(oidc.Auth0ConfigError):
        cfg(SKYPANE_AUTH0_DOMAIN="http://tenant.example.test")


def test_loopback_flag_enables_http_only_for_loopback():
    config = cfg(SKYPANE_AUTH0_DOMAIN="127.0.0.1:5555",
                 SKYPANE_COMPANION_PUBLIC_URL="http://127.0.0.1:9000",
                 SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK="1")
    assert config.issuer == "http://127.0.0.1:5555/"
    assert config.redirect_uri == "http://127.0.0.1:9000/callback"
    remote = cfg(SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK="1")
    assert remote.scheme == "https"
    with pytest.raises(oidc.Auth0ConfigError):
        cfg(SKYPANE_COMPANION_PUBLIC_URL="http://frame.example.test",
            SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK="1")


def test_config_repr_hides_secret():
    assert "secret-xyz" not in repr(cfg())


# --- PKCE and URLs ---

def test_pkce_shape_and_uniqueness():
    verifier, challenge = oidc.new_pkce()
    assert len(verifier) == 43
    import hashlib
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected
    assert oidc.new_pkce()[0] != verifier


def test_authorize_url_parameters_exactly():
    url = oidc.authorize_url(cfg(), "st", "no", "ch")
    parts = urllib.parse.urlsplit(url)
    assert parts.path == "/authorize"
    query = dict(urllib.parse.parse_qsl(parts.query))
    assert query == {
        "response_type": "code", "client_id": "client-abc",
        "redirect_uri": "https://frame.example.test/callback",
        "scope": "openid email", "state": "st", "nonce": "no",
        "code_challenge": "ch", "code_challenge_method": "S256"}


def test_logout_url():
    parts = urllib.parse.urlsplit(oidc.logout_url(cfg()))
    assert parts.path == "/v2/logout"
    assert dict(urllib.parse.parse_qsl(parts.query)) == {
        "client_id": "client-abc",
        "returnTo": "https://frame.example.test/login"}


# --- claim validation ---

def test_good_token_accepted():
    config = cfg()
    claims = validate(make_token(good_payload(config)), config)
    assert claims == oidc.Claims("auth0|1", "a@example.test", True)


def mutate(**changes):
    payload = good_payload(cfg())
    for key, value in changes.items():
        if value is KeyError:
            payload.pop(key, None)
        else:
            payload[key] = value
    return make_token(payload)


@pytest.mark.parametrize("token", [
    mutate(iss="https://tenant.example.test"),
    mutate(iss="https://evil.example.test/"),
    mutate(aud="someone-else"),
    mutate(aud=["client-abc", "other"]),
    mutate(aud=["other"]),
    mutate(aud=7),
    mutate(azp="other"),
    mutate(aud=["client-abc", "other"], azp="other"),
    mutate(exp=NOW - 61),
    mutate(exp=True),
    mutate(exp="9999999999"),
    mutate(exp=KeyError),
    mutate(iat=NOW + 61),
    mutate(iat=True),
    mutate(nonce="different"),
    mutate(nonce=KeyError),
    mutate(sub=KeyError),
    mutate(sub=""),
    mutate(sub="x" * 256),
    mutate(sub=42),
])
def test_bad_claims_rejected(token):
    with pytest.raises(oidc.SignInError) as err:
        validate(token)
    assert err.value.kind in ("incomplete", "expired")
    assert token not in str(err.value)


@pytest.mark.parametrize("token", [
    "", "a.b", "a.b.c.d", "not a token", "a.b.c",
    "%s.%s.sig" % (b64({"alg": "none"}), b64(good_payload(cfg()))),
    "%s.%s.sig" % (b64({"typ": "JWT"}), b64(good_payload(cfg()))),
    "%s.%s.sig" % (b64([1]), b64(good_payload(cfg()))),
    "%s.%s.sig" % (b64({"alg": "RS256"}), b64([1])),
])
def test_malformed_tokens_rejected(token):
    with pytest.raises(oidc.SignInError):
        validate(token)


def test_non_string_token_rejected():
    with pytest.raises(oidc.SignInError):
        validate(None)


def test_expired_kind_and_leeway():
    with pytest.raises(oidc.SignInError) as err:
        validate(mutate(exp=NOW - 120))
    assert err.value.kind == "expired"
    assert validate(mutate(exp=NOW - 30)).sub == "auth0|1"


def test_aud_list_with_matching_azp_accepted():
    token = mutate(aud=["client-abc", "other"], azp="client-abc")
    assert validate(token).sub == "auth0|1"


def test_email_verified_must_be_boolean_true():
    assert validate(mutate(email_verified="true")).email_verified is False
    assert validate(mutate(email_verified=False)).email_verified is False
    assert validate(mutate(email_verified=KeyError)).email_verified is False
    assert validate(mutate()).email_verified is True


def test_missing_email_is_empty_string():
    assert validate(mutate(email=KeyError)).email == ""


# --- exchange_code ---

def reply(status=200, body=b""):
    return lambda url, data: oidc.HttpReply(status, body)


def test_exchange_success_ignores_access_token():
    body = json.dumps({"id_token": "tok", "access_token": "acc"}).encode()
    seen = {}

    def post(url, data):
        seen["url"], seen["data"] = url, data
        return oidc.HttpReply(200, body)

    assert oidc.exchange_code(cfg(), "the-code", "ver", post) == "tok"
    assert seen["url"] == "https://tenant.example.test/oauth/token"
    assert seen["data"]["code_verifier"] == "ver"
    assert seen["data"]["grant_type"] == "authorization_code"


@pytest.mark.parametrize("status,body", [
    (500, b'{"id_token": "tok"}'),
    (400, b"secret-body-text"),
    (200, b"not json"),
    (200, b"[1, 2]"),
    (200, b'{"access_token": "x"}'),
    (200, b'{"id_token": 5}'),
    (200, b'{"id_token": ""}'),
    (200, b"\xff\xfe"),
])
def test_exchange_failures_do_not_leak_body(status, body):
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(cfg(), "c", "v", reply(status, body))
    assert body.decode("latin-1") not in str(err.value) or body == b"[1, 2]"
    assert "secret-xyz" not in str(err.value)


# --- AttemptTable ---

class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_attempt_create_and_single_pop():
    table = oidc.AttemptTable(clock=Clock())
    attempt_id, attempt = table.create("/account")
    assert attempt.next_route == "/account"
    assert attempt.state != attempt.nonce
    assert table.pop(attempt_id) == attempt
    assert table.pop(attempt_id) is None


def test_attempt_unknown_id():
    assert oidc.AttemptTable().pop("nope") is None


def test_attempt_expires_after_ttl():
    clock = Clock()
    table = oidc.AttemptTable(clock=clock)
    attempt_id, _ = table.create("/")
    clock.now += 599
    fresh_id, _ = table.create("/")
    assert table.pop(fresh_id) is not None
    clock.now += 2
    assert table.pop(attempt_id) is None


def test_attempt_capacity_evicts_oldest():
    table = oidc.AttemptTable(clock=Clock(), capacity=3)
    ids = [table.create("/")[0] for _ in range(4)]
    assert table.pop(ids[0]) is None
    assert all(table.pop(i) is not None for i in ids[1:])


def test_attempt_default_capacity_is_4096():
    assert oidc.ATTEMPT_CAPACITY == 4096
    assert oidc.ATTEMPT_TTL_SECONDS == 600


def test_attempt_table_thread_safety():
    table = oidc.AttemptTable(capacity=50)
    failures = []

    def worker():
        try:
            for _ in range(200):
                attempt_id, _ = table.create("/")
                table.pop(attempt_id)
        except Exception as exc:  # noqa: BLE001 - surfaced by the assert below
            failures.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert failures == []


# --- requests_post against the loopback fake ---

@pytest.fixture
def live():
    from fake_auth0 import FakeAuth0

    redirect = "http://127.0.0.1:9/callback"
    fake = FakeAuth0("client-abc", "secret-xyz", redirect,
                     ["http://127.0.0.1:9/login"]).start()
    config = oidc.Auth0Config.from_env({
        "SKYPANE_AUTH0_DOMAIN": fake.domain,
        "SKYPANE_AUTH0_CLIENT_ID": "client-abc",
        "SKYPANE_AUTH0_CLIENT_SECRET": "secret-xyz",
        "SKYPANE_COMPANION_PUBLIC_URL": "http://127.0.0.1:9",
        "SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK": "1"})
    yield fake, config
    fake.stop()


def start_login(fake, config):
    import http.client
    verifier, challenge = oidc.new_pkce()
    url = urllib.parse.urlsplit(oidc.authorize_url(config, "st", NONCE, challenge))
    conn = http.client.HTTPConnection("127.0.0.1", fake.port, timeout=5)
    conn.request("GET", url.path + "?" + url.query)
    location = conn.getresponse().getheader("Location")
    conn.close()
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))
    return query["code"], verifier


def test_real_exchange_round_trip(live):
    fake, config = live
    code, verifier = start_login(fake, config)
    token = oidc.exchange_code(config, code, verifier, oidc.requests_post)
    assert oidc.validate_id_token(token, config, NONCE).sub == "auth0|fake-user"


def test_real_exchange_wrong_verifier_fails(live):
    fake, config = live
    code, _ = start_login(fake, config)
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(config, code, "wrong", oidc.requests_post)
    assert err.value.reason == "token_status_400"


def test_slow_token_endpoint_is_unavailable(live, monkeypatch):
    fake, config = live
    monkeypatch.setattr(oidc, "TOKEN_READ_TIMEOUT", 0.3)
    fake.set_knob("token_delay_s", 1.5)
    code, verifier = start_login(fake, config)
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(config, code, verifier, oidc.requests_post)
    assert err.value.kind == "unavailable"


def test_oversized_token_body_is_refused(live):
    fake, config = live
    fake.set_knob("token_body", "x" * (oidc.TOKEN_MAX_BYTES + 1))
    code, verifier = start_login(fake, config)
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(config, code, verifier, oidc.requests_post)
    assert err.value.kind == "unavailable"


def test_redirect_from_token_endpoint_is_not_followed(live):
    fake, config = live
    fake.set_knob("token_status", 302)
    code, verifier = start_login(fake, config)
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(config, code, verifier, oidc.requests_post)
    assert err.value.reason == "token_status_302"
    assert not fake.calls_to("/oauth/redirected")


def test_unreachable_endpoint_is_unavailable(live):
    fake, config = live
    fake.stop()
    with pytest.raises(oidc.SignInError) as err:
        oidc.exchange_code(config, "c", "v", oidc.requests_post)
    assert err.value.kind == "unavailable"
