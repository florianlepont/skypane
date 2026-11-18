"""The Auth0 Management client against the loopback fake: invitation ticket
for a new and an existing user, the not-configured path, failure results,
and proof that no secret, token or ticket link leaks into logs, results or
reprs. No real network is used.
"""
import logging

import pytest

from companion import auth0_management as mgmt
from fake_auth0 import MGMT_TOKEN, FakeAuth0

MGMT_ID = "mgmt-client-id"
MGMT_SECRET = "mgmt-secret-placeholder-value"
CONNECTION = "test-db-connection"
CONNECTION_ID = "con_testplaceholder"
RESULT_URL = "https://companion.example.test/login"
EMAIL = "invitee@example.test"


@pytest.fixture
def fake():
    server = FakeAuth0("web-client", "web-secret", "http://127.0.0.1/callback")
    server.start()
    server.enable_management(MGMT_ID, MGMT_SECRET, CONNECTION, CONNECTION_ID)
    yield server
    server.stop()


def _invite(fake, environ=None, email=EMAIL, result_url=RESULT_URL, **kw):
    env = fake.mgmt_env() if environ is None else environ
    return mgmt.create_invitation(env, email, result_url, **kw)


def test_new_user_gets_a_ticket_link_and_no_password_is_returned(fake):
    result = _invite(fake)
    assert result.ok and result.reason == ""
    assert result.link.startswith("http://%s/lo/reset?ticket=" % fake.domain)
    created = [body for path, body, _ in fake.mgmt.requests
               if path == "/api/v2/users"][0]
    assert created["connection"] == CONNECTION
    assert created["email"] == EMAIL
    assert created["email_verified"] is False
    assert created["password"] and created["password"] not in repr(result)
    ticket = [body for path, body, _ in fake.mgmt.requests
              if path.endswith("password-change")][0]
    assert ticket["mark_email_as_verified"] is True
    assert ticket["result_url"] == RESULT_URL
    assert ticket["ttl_sec"] == 5 * 24 * 3600
    assert ticket["user_id"] == fake.mgmt.users[EMAIL]


def test_existing_user_gets_a_ticket_by_email_and_connection_id(fake):
    assert _invite(fake).ok
    again = _invite(fake)
    assert again.ok and again.link
    ticket = [body for path, body, _ in fake.mgmt.requests
              if path.endswith("password-change")][-1]
    assert ticket["email"] == EMAIL
    assert ticket["connection_id"] == CONNECTION_ID
    assert "user_id" not in ticket
    assert [p for p, _, _ in fake.mgmt.requests].count("/api/v2/users") == 2


def test_existing_user_without_connection_id_fails_closed(fake):
    env = fake.mgmt_env()
    del env["SKYPANE_AUTH0_DB_CONNECTION_ID"]
    assert _invite(fake, env).ok
    result = _invite(fake, env)
    assert not result.ok
    assert result.reason == mgmt.REASON_EXISTS_NO_CONNECTION_ID
    assert result.link == ""


@pytest.mark.parametrize("missing", [
    "SKYPANE_AUTH0_MGMT_CLIENT_ID", "SKYPANE_AUTH0_MGMT_CLIENT_SECRET",
    "SKYPANE_AUTH0_DB_CONNECTION", "SKYPANE_AUTH0_DOMAIN", "ALL"])
def test_not_configured_makes_no_network_call(fake, missing):
    env = fake.mgmt_env()
    for name in list(env):
        if missing == "ALL" and name.startswith("SKYPANE_AUTH0"):
            del env[name]
    env.pop(missing, None)
    calls = []

    def post(url, document, headers):
        calls.append(url)
        raise AssertionError("no network call expected")

    result = _invite(fake, env, post=post)
    assert not result.ok and result.reason == mgmt.REASON_NOT_CONFIGURED
    assert not mgmt.configured(env)
    assert calls == [] and fake.calls == []


def test_configured_reports_true_with_full_credential(fake):
    assert mgmt.configured(fake.mgmt_env())


def test_token_request_asks_only_for_the_audience_and_payload_has_no_role(fake):
    assert _invite(fake).ok
    (form,) = fake.mgmt.token_forms
    assert form["grant_type"] == "client_credentials"
    assert form["audience"] == "http://%s/api/v2/" % fake.domain
    assert "scope" not in form
    for path, body, bearer in fake.mgmt.requests:
        assert bearer == "Bearer " + MGMT_TOKEN
        assert MGMT_SECRET not in str(body)
        assert "app_metadata" not in body and "user_metadata" not in body
        assert "role" not in body and "roles" not in body


def test_secret_is_sent_only_in_the_token_request(fake):
    sent = []

    def spy(url, document, headers):
        sent.append((url, dict(document), dict(headers)))
        return mgmt.requests_post_json(url, document, headers)

    assert _invite(fake, post=spy).ok
    carrying = [url for url, doc, hdr in sent
                if MGMT_SECRET in str(doc) or MGMT_SECRET in str(hdr)]
    assert carrying == ["http://%s/oauth/token" % fake.domain]


@pytest.mark.parametrize("knob, value, reason", [
    ("mgmt_token_status", 401, mgmt.REASON_TOKEN),
    ("mgmt_users_status", 500, mgmt.REASON_CREATE),
    ("mgmt_users_status", 403, mgmt.REASON_CREATE),
    ("mgmt_ticket_status", 429, mgmt.REASON_TICKET),
])
def test_provider_errors_become_a_short_reason(fake, knob, value, reason):
    fake.set_knob(knob, value)
    result = _invite(fake)
    assert not result.ok and result.reason == reason and result.link == ""


@pytest.mark.parametrize("knob, body", [
    ("mgmt_users_body", "not json"),
    ("mgmt_users_body", "[]"),
    ("mgmt_users_body", "{}"),
    ("mgmt_ticket_body", "not json"),
    ("mgmt_ticket_body", '{"ticket": ""}'),
])
def test_malformed_responses_fail_closed(fake, knob, body):
    status_knob = knob.replace("body", "status")
    fake.set_knob(status_knob, 201)
    fake.set_knob(knob, body)
    result = _invite(fake)
    assert not result.ok and result.link == ""
    assert result.reason in (mgmt.REASON_BAD_RESPONSE, mgmt.REASON_CREATE)


def test_unreachable_provider_returns_a_result(fake):
    env = fake.mgmt_env()
    fake.stop()
    result = _invite(fake, env)
    assert not result.ok and result.reason == mgmt.REASON_UNREACHABLE


def test_slow_provider_hits_the_timeout(fake, monkeypatch):
    monkeypatch.setattr(mgmt, "READ_TIMEOUT", 0.3)
    fake.set_knob("mgmt_delay_s", 1.5)
    result = _invite(fake)
    assert not result.ok and result.reason == mgmt.REASON_UNREACHABLE


def test_oversized_response_is_refused(fake):
    fake.set_knob("mgmt_users_status", 201)
    fake.set_knob("mgmt_users_body", "x" * (mgmt.MAX_BYTES + 10))
    result = _invite(fake)
    assert not result.ok and result.reason == mgmt.REASON_UNREACHABLE


def test_a_raising_transport_never_escapes(fake):
    def post(url, document, headers):
        raise RuntimeError(MGMT_SECRET)

    result = _invite(fake, post=post)
    assert not result.ok and result.reason == mgmt.REASON_UNREACHABLE
    assert MGMT_SECRET not in repr(result)


@pytest.mark.parametrize("email", [
    "", "no-at-sign", "a@b", "two@@example.test", "sp ace@example.test",
    "line\nbreak@example.test", "x" * 250 + "@example.test"])
def test_bad_emails_are_refused_before_any_call(fake, email):
    result = _invite(fake, email=email)
    assert not result.ok and result.reason == mgmt.REASON_BAD_EMAIL
    assert fake.calls == []


@pytest.mark.parametrize("url", [
    "", "javascript:alert(1)", "http://companion.example.test/login",
    "https://user:pw@companion.example.test/", "//companion.example.test/"])
def test_bad_result_urls_are_refused(fake, url):
    env = fake.mgmt_env()
    del env["SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK"]
    result = _invite(fake, env, result_url=url)
    assert not result.ok and result.reason == mgmt.REASON_BAD_RESULT_URL


def test_secret_token_and_link_never_reach_logs_or_reprs(fake, caplog):
    caplog.set_level(logging.DEBUG)
    ok = _invite(fake)
    fake.set_knob("mgmt_ticket_status", 500)
    failed = _invite(fake)
    cfg = mgmt.from_env(fake.mgmt_env())
    secrets_seen = (MGMT_SECRET, MGMT_TOKEN, ok.link)
    text = "\n".join(
        [r.getMessage() for r in caplog.records]
        + [repr(ok), repr(failed), repr(cfg), str(ok), str(cfg)])
    for secret in secrets_seen:
        assert secret not in text


def test_insecure_scheme_needs_the_loopback_flag(fake):
    env = fake.mgmt_env()
    del env["SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK"]
    cfg = mgmt.from_env(env)
    assert cfg is not None and cfg.base_url.startswith("https://")


@pytest.mark.parametrize("domain", [
    "https://tenant.example.test", "tenant.example.test/path", "a@b.test",
    "tenant example.test"])
def test_malformed_domain_counts_as_not_configured(fake, domain):
    env = fake.mgmt_env()
    env["SKYPANE_AUTH0_DOMAIN"] = domain
    assert mgmt.from_env(env) is None
