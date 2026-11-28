"""The invitation behind POST /users/invite, against the loopback fake Auth0:
the local invite is committed first and stays the access gate, the link is
shown once in a never-cached response and held nowhere else, a second invite
of a person who has not signed in yet renews the link for a shorter time,
and every failure keeps the invite and says what to do."""
import logging
import os
import re
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import auth, prefs
from companion_app_server import http_request, with_csrf
from fake_auth0 import MGMT_TOKEN
from server import fleet_db

NEW_EMAIL = "new.person@example.test"
LINK_RE = re.compile(r"http://127\.0\.0\.1:\d+/lo/reset\?ticket=[A-Za-z0-9_-]+")


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process, invitation_auth0):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir), invitation_auth0


def _post(server, cookie, form, headers=None):
    return http_request(
        server.url("/users/invite"), "POST", data=with_csrf(cookie, form), cookie=cookie,
        extra_headers=headers)


def _invite(server, cookie, email=NEW_EMAIL, **form):
    status, headers, body = _post(server, cookie, dict(form, email=email))
    return status, headers, body.decode("utf-8")


def _link_of(body):
    found = LINK_RE.findall(body)
    assert len(found) >= 1, "no invitation link in the response"
    return found[0]


def _sql(state_dir, sql, args=()):
    conn = fleet_db.connect(state_dir)
    try:
        return [tuple(row) for row in conn.execute(sql, args)]
    finally:
        conn.close()


def _audit(state_dir, action):
    return fx.audit_rows(state_dir, action)


def _detail(row):
    return row["detail"] or ""


def _tickets(fake):
    return [body for path, body, _ in fake.mgmt.requests if path.endswith("password-change")]


def _signed_in(state_dir, email):
    _sql(state_dir, "UPDATE users SET iss = 'https://t.example.test/', sub = ? "
                    "WHERE email = ?", ("auth0|%s" % email, email))


# --- the first invitation -----------------------------------------------------


def test_a_new_invite_commits_locally_then_shows_the_link_once(rig):
    server, seed, cookie, fake = rig
    status, headers, body = _invite(server, cookie, role="admin")
    assert status == 200 and "Location" not in headers
    assert 'id="dlg-invitation-ready"' in body and "Invitation ready" in body
    assert "data-modal-once" in body
    link = _link_of(body)
    assert "rel=" not in body[body.index("dlg-invitation-ready"):].split("</dialog>")[0]
    row = _sql(server.state_dir, "SELECT id, role, disabled, iss, sub FROM users "
                                 "WHERE email = ?", (NEW_EMAIL,))[0]
    assert row[1:] == ("admin", 0, None, None)
    invite = _audit(server.state_dir, "user.invite")
    assert len(invite) == 1 and invite[0]["target_id"] == str(row[0])
    outcome = _audit(server.state_dir, "user.invitation")
    assert len(outcome) == 1 and outcome[0]["outcome"] == "ok"
    assert outcome[0]["target_id"] == str(row[0])
    assert '"renewed": false' in _detail(outcome[0]) and "432000" in _detail(outcome[0])
    # A second look at the page shows the invited row and no link.
    page = fx.get(server, cookie, "/users")[2]
    assert NEW_EMAIL in page and link not in page and "dlg-invitation-ready" not in page
    assert fake.calls_to("/oauth/token")


def test_the_link_response_is_never_cached_and_never_sends_a_referrer(rig):
    server, _seed, cookie, _fake = rig
    _status, headers, _body = _invite(server, cookie)
    assert headers["Cache-Control"] == "no-store"
    assert headers["Pragma"] == "no-cache"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "sp_flash" not in str(headers)
    # Every other page keeps the usual policy.
    other = http_request(server.url("/users"), cookie=cookie)[1]
    assert other["Referrer-Policy"] == "same-origin"
    assert other["Cache-Control"] == "no-store"


def test_the_link_is_held_nowhere_and_the_secret_is_in_no_output(rig, caplog):
    server, _seed, cookie, fake = rig
    caplog.set_level(logging.DEBUG)
    status, headers, body = _invite(server, cookie)
    assert status == 200
    link = _link_of(body)
    token = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["ticket"][0]
    # Not in the database (every table), nor in any file of the state directory.
    conn = fleet_db.connect(server.state_dir)
    try:
        dump = "\n".join(conn.iterdump())
    finally:
        conn.close()
    assert token not in dump and link not in dump
    for root, _dirs, files in os.walk(server.state_dir):
        for name in files:
            try:
                with open(os.path.join(root, name), "rb") as handle:
                    content = handle.read()
            except FileNotFoundError:
                # SQLite removes the write-ahead log when the last connection
                # closes, so a listed file can vanish before it is opened; a
                # vanished file cannot hold the secret.
                continue
            assert token.encode() not in content, name
    for row in _audit(server.state_dir, "user.invitation") + _audit(
            server.state_dir, "user.invite"):
        assert token not in _detail(row)
    # Not in the logs, any header, a cookie, the address, or a later page.
    assert token not in caplog.text
    assert token not in str(headers)
    assert token not in fx.get(server, cookie, "/users")[2]
    # The planted secrets never appear in the page, headers, database or logs.
    for secret in (fake.mgmt.client_secret, MGMT_TOKEN):
        assert secret not in body and secret not in str(headers)
        assert secret not in dump and secret not in caplog.text
    assert len(fake.mgmt.client_secret) > 10


def test_the_request_to_auth0_carries_a_lowercase_address_and_five_days(rig):
    server, _seed, cookie, fake = rig
    _invite(server, cookie, email="  New.Person@Example.TEST ")
    users = [b for p, b, _ in fake.mgmt.requests if p == "/api/v2/users"]
    assert len(users) == 1 and users[0]["email"] == NEW_EMAIL
    assert set(users[0]) == {"email", "connection", "email_verified", "verify_email", "password"}
    (ticket,) = _tickets(fake)
    assert ticket["ttl_sec"] == 5 * 24 * 3600 and "role" not in ticket
    assert ticket["result_url"] == server.base_url()
    assert set(ticket) == {"user_id", "result_url", "ttl_sec", "mark_email_as_verified"}


def test_the_dialog_and_the_copied_message_say_what_to_send_and_how_long_it_lasts(rig):
    server, _seed, cookie, _fake = rig
    _status, _headers, body = _invite(server, cookie)
    dialog = body[body.index('id="dlg-invitation-ready"'):].split("</dialog>")[0]
    text = re.sub(r"<[^>]+>", " ", dialog)
    assert "Send this link to" in text and NEW_EMAIL in text
    assert "it expires in 5 days" in text and "Treat it as a secret" in text
    assert "open %s and sign in" % server.base_url() in text
    assert "single-use" not in dialog.lower() and "one-time" not in dialog.lower()
    copy = re.search(r'data-copy-value="([^"]+)"', dialog).group(1)
    link = _link_of(dialog)
    assert link in copy and NEW_EMAIL in copy and "expires in 5 days" in copy
    assert server.base_url() in copy
    assert 'data-copied-text="Copied"' in dialog and ">Copy</span>" in dialog


def test_the_french_dialog_uses_the_catalogue(rig):
    server, _seed, cookie, _fake = rig
    status, _headers, body = http_request(
        server.url("/users/invite"), "POST",
        data=with_csrf(cookie, {"email": NEW_EMAIL}),
        cookie="%s; %s=fr" % (cookie, auth.UI_LANG_COOKIE_NAME))[:3]
    body = body.decode("utf-8")
    assert status == 200
    for wanted in ("Invitation prête", "Envoyez ce lien à", "il expire dans 5 jours",
                   "Traitez-le comme un secret", "Terminé", "Copier"):
        assert wanted in body, wanted
    assert "Invitation ready" not in body


# --- a second invitation --------------------------------------------------------


def test_a_second_invite_of_a_waiting_person_renews_the_link_for_a_day(rig):
    server, seed, cookie, fake = rig
    _status, _headers, first = _invite(server, cookie, role="admin")
    first_link = _link_of(first)
    status, _headers, again = _invite(server, cookie, role="user")
    assert status == 200 and "it expires in 24 hours" in again
    assert _link_of(again) != first_link
    # The role is what the first invite set; nothing else was created.
    assert _sql(server.state_dir, "SELECT role FROM users WHERE email = ?", (NEW_EMAIL,)) == [
        ("admin",)]
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM users WHERE email = ?",
                (NEW_EMAIL,)) == [(1,)]
    assert len(_audit(server.state_dir, "user.invite")) == 1
    outcomes = _audit(server.state_dir, "user.invitation")
    assert [row["outcome"] for row in outcomes] == ["ok", "ok"]
    assert '"renewed": true' in _detail(outcomes[-1]) and "86400" in _detail(outcomes[-1])
    first_ticket, second_ticket = _tickets(fake)
    assert first_ticket["ttl_sec"] == 432000 and second_ticket["ttl_sec"] == 86400
    assert second_ticket["email"] == NEW_EMAIL and "user_id" not in second_ticket


def test_the_row_menu_offers_a_new_invitation_only_to_a_person_who_has_not_signed_in(rig):
    server, seed, cookie, fake = rig
    _signed_in(server.state_dir, fx.OWNER_EMAIL)
    page = fx.get(server, cookie, "/users")[2]
    forms = re.findall(
        r'<form method="post" action="/users/invite"[^>]*>(.*?)</form>', page, re.S)
    assert len(forms) == 3  # the waiting user, the second administrator and the idle user
    waiting = [f for f in forms if 'value="%s"' % fx.USER_EMAIL in f]
    assert len(waiting) == 1 and "Send a new invitation" in waiting[0]
    assert 'name="csrf_token"' in waiting[0] and "<svg" in waiting[0]
    assert not [f for f in forms if 'value="%s"' % fx.OWNER_EMAIL in f]
    # Posting that form (address only) renews the link without touching the role.
    status, _headers, body = _invite(server, cookie, email=fx.USER_EMAIL)
    assert status == 200 and "it expires in 24 hours" in body and fx.USER_EMAIL in body
    assert _sql(server.state_dir, "SELECT role FROM users WHERE id = ?", (seed.user_id,)) == [
        ("user",)]


def test_a_signed_in_or_disabled_person_is_refused_not_renewed(rig):
    server, seed, cookie, fake = rig
    _signed_in(server.state_dir, fx.USER_EMAIL)
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.owner_id,))
    for email in (fx.USER_EMAIL, fx.OWNER_EMAIL):
        status, _headers, body = _invite(server, cookie, email=email)
        assert status == 400 and "That email is already invited." in body
    assert _audit(server.state_dir, "user.invitation") == []
    assert fake.calls == []


# --- failures keep the invite ---------------------------------------------------


def _failed_dialog(body):
    assert 'id="dlg-invitation-failed"' in body, "no failure dialog"
    return body[body.index('id="dlg-invitation-failed"'):].split("</dialog>")[0]


def test_a_failure_keeps_the_local_invite_and_offers_to_try_again(rig):
    server, _seed, cookie, fake = rig
    fake.set_knob("mgmt_ticket_status", 500)
    status, headers, body = _invite(server, cookie)
    assert status == 200 and not LINK_RE.search(body)
    dialog = _failed_dialog(body)
    assert "%s is invited, but no invitation link was created." % NEW_EMAIL in dialog
    assert "Try again" in dialog
    # The retry is the primary action, with the refresh glyph before its label.
    assert re.search(
        r"autofocus><svg[^>]*>.*?</svg><span>Try again</span>", dialog, re.S)
    retry = re.search(r'<form method="post" action="/users/invite">(.*?)</form>', dialog, re.S)
    assert retry and 'name="csrf_token"' in retry.group(1)
    assert 'name="email" value="%s"' % NEW_EMAIL in retry.group(1)
    assert _sql(server.state_dir, "SELECT iss, sub, disabled FROM users WHERE email = ?",
                (NEW_EMAIL,)) == [(None, None, 0)]
    assert len(_audit(server.state_dir, "user.invite")) == 1
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert outcome["outcome"] == "failed" and "ticket_failed" in _detail(outcome)
    # The provider's reason code is for the audit row only.
    assert "ticket_failed" not in body and "Cache-Control" in headers
    # Trying again, once the provider answers, renews the link for a day.
    fake.clear_knobs()
    status, _headers, again = _invite(server, cookie)
    assert status == 200 and _link_of(again) and "expires in 24 hours" in again


def test_a_busy_provider_says_to_try_again_in_a_moment(rig):
    server, _seed, cookie, fake = rig
    fake.set_knob("mgmt_users_status", 429)
    _status, _headers, body = _invite(server, cookie)
    dialog = _failed_dialog(body)
    assert "Try again in a moment." in dialog and "Try again</span></button>" in dialog
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert "rate_limited" in _detail(outcome) and "rate_limited" not in body


@pytest.mark.parametrize("knob, status, code, sentence", [
    ("mgmt_token_status", 401, "token_failed", "the Management API client id and secret"),
    ("mgmt_token_status", 403, "token_failed", "the Management API client id and secret"),
    ("mgmt_users_status", 400, "create_failed", "exact name of the database connection"),
    ("mgmt_users_status", 404, "create_failed", "exact name of the database connection"),
    ("mgmt_users_status", 403, "permission_denied", "create:users and create:user_tickets"),
    ("mgmt_ticket_status", 403, "permission_denied", "create:users and create:user_tickets"),
    ("mgmt_ticket_status", 400, "ticket_failed", "did not accept the request")])
def test_each_refusal_tells_the_administrator_what_to_check(
        rig, knob, status, code, sentence):
    server, _seed, cookie, fake = rig
    fake.set_knob(knob, status)
    _status, _headers, body = _invite(server, cookie)
    dialog = _failed_dialog(body)
    assert sentence in dialog and "Try again</span></button>" in dialog
    assert dialog.count('<p class="modal__note">') == 2
    assert code not in body and not re.search(r"\b%d\b" % status, dialog)
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert code in _detail(outcome)


def test_without_the_management_credential_the_invite_stays_local_and_says_so(
        app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    server.apply_env({name: None for name in (
        "SKYPANE_AUTH0_MGMT_CLIENT_ID", "SKYPANE_AUTH0_MGMT_CLIENT_SECRET",
        "SKYPANE_AUTH0_DB_CONNECTION", "SKYPANE_AUTH0_DB_CONNECTION_ID")})
    cookie = fx.admin_cookie(server.state_dir)
    status, _headers, body = _invite(server, cookie)
    assert status == 200
    dialog = _failed_dialog(body)
    assert "Automatic invitations are not set up on this server." in dialog
    assert "Try again</span></button>" not in dialog and "Done" in dialog
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM users WHERE email = ?",
                (NEW_EMAIL,)) == [(1,)]
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert "not_configured" in _detail(outcome)


@pytest.mark.parametrize("value, code", [
    (None, "user_exists_connection_id_missing"),
    ("con_short", "connection_id_invalid")])
def test_a_renewal_without_a_usable_connection_id_fails_closed_with_a_clear_message(
        rig, value, code):
    server, _seed, cookie, fake = rig
    server.apply_env({"SKYPANE_AUTH0_DB_CONNECTION_ID": value})
    assert _link_of(_invite(server, cookie)[2])  # a new person needs no connection id
    status, _headers, body = _invite(server, cookie)
    assert status == 200 and not LINK_RE.search(body)
    dialog = _failed_dialog(body)
    assert "SKYPANE_AUTH0_DB_CONNECTION_ID" in dialog and "deployment guide" in dialog
    assert "Try again</span></button>" not in dialog and code not in body
    rows = _audit(server.state_dir, "user.invitation")
    assert [row["outcome"] for row in rows] == ["ok", "failed"]
    assert code in _detail(rows[-1])
    assert len(_tickets(fake)) == 1  # nothing was asked of Auth0 for the renewal ticket


@pytest.mark.parametrize("ticket", [
    "https://evil.example.test/lo/reset?ticket=x", "http://127.0.0.1:1/lo/reset?ticket=x",
    "javascript:alert(1)", "//evil.example.test/x"])
def test_a_link_that_is_not_on_the_auth0_domain_is_never_shown(rig, ticket):
    server, _seed, cookie, fake = rig
    fake.set_knob("mgmt_ticket_status", 201)
    fake.set_knob("mgmt_ticket_body", '{"ticket": "%s"}' % ticket)
    _status, _headers, body = _invite(server, cookie)
    dialog = _failed_dialog(body)
    assert "evil.example" not in body and "javascript:" not in body
    assert ticket not in body and "Try again</span></button>" in dialog
    assert "SKYPANE_AUTH0_CUSTOM_DOMAIN" in dialog
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert "ticket_url_rejected" in _detail(outcome)


def test_an_unusable_return_address_says_to_check_the_host_header(rig):
    server, _seed, cookie, fake = rig
    status, _headers, body = _post(
        server, cookie, {"email": NEW_EMAIL}, {"Host": "a b"})[:3]
    dialog = _failed_dialog(body.decode("utf-8"))
    assert status == 200 and "Host header" in dialog and "bad_result_url" not in dialog
    (outcome,) = _audit(server.state_dir, "user.invitation")
    assert "bad_result_url" in _detail(outcome)


def test_the_failure_dialog_focuses_the_retry_and_keeps_done_secondary(rig):
    server, _seed, cookie, fake = rig
    fake.set_knob("mgmt_ticket_status", 500)
    dialog = _failed_dialog(_invite(server, cookie)[2])
    assert re.search(r'<button type="submit" class="btn btn--primary" autofocus>', dialog)
    done = re.search(r'<a class="([^"]*)" href="/users" data-modal-close([^>]*)>', dialog)
    assert "modal__dismiss--button" in done.group(1) and "autofocus" not in done.group(2)


def test_a_hostile_host_header_never_reaches_auth0_or_the_page(rig):
    server, _seed, cookie, fake = rig
    for host in ("evil.example.test/x@y", "evil.example.test:99999999", "a b"):
        status, _headers, body = _post(
            server, cookie, {"email": "host.%d@example.test" % len(host)}, {"Host": host})[:3]
        text = body.decode("utf-8")
        assert status == 200 and "evil.example.test" not in text
        assert not LINK_RE.search(text)
    assert _tickets(fake) == []
    assert all("evil" not in str(body) for _p, body, _b in fake.mgmt.requests)
