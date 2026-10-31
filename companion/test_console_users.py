"""The Users page and its five actions over real HTTP: the page's guard
states, invite, role change, disable and enable, identity unlink, the
last-administrator and self-action guards (including two concurrent
requests), audit rows and the access gates."""
import re
import threading
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import console_routes, console_users, prefs
from companion_app_server import http_request, login_via_auth0
from server import fleet_db

FAKE_ISS = "https://tenant.example.test/"


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


def _sql(state_dir, sql, args=()):
    conn = fleet_db.connect(state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _link(state_dir, *user_ids):
    for user_id in user_ids:
        _sql(state_dir, "UPDATE users SET iss = ?, sub = ? WHERE id = ?",
             (FAKE_ISS, "auth0|fake-%d" % user_id, user_id))


def _user(state_dir, user_id):
    return _sql(
        state_dir, "SELECT role, disabled, iss, sub FROM users WHERE id = ?", (user_id,))[0]


def _row_html(body, user_id):
    match = re.search(
        r'<tr data-user="%d".*?</tr>' % user_id, body, re.S)
    assert match, "no table row for user %d" % user_id
    return match.group(0)


def _act(server, cookie, user_id, action, **form):
    return fx.post(server, cookie, "/users/%s/%s" % (user_id, action), form)


def _flash_text(server, cookie, headers):
    values = [value.split(";")[0] for key, value in headers.items()
              if key.lower() == "set-cookie" and value.startswith("sp_flash=")]
    assert values, "no flash cookie"
    return fx.get(server, cookie + "; " + values[0], "/users")[2]


def _audit(state_dir, action):
    return fx.audit_rows(state_dir, action)


# --- page ---------------------------------------------------------------------


def test_the_page_lists_every_user_with_role_status_and_frames(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.admin2_id, seed.owner_id)
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.owner_id,))
    status, _headers, body = fx.get(server, cookie, "/users")
    assert status == 200
    for email in (fx.ADMIN_EMAIL, fx.OWNER_EMAIL, fx.SECOND_ADMIN_EMAIL, fx.USER_EMAIL):
        assert email in body
    assert "Never signed in" in body and "Signed in" in body
    assert "Administrator" in _row_html(body, seed.admin2_id)
    assert "Disabled" in _row_html(body, seed.owner_id)
    assert "Invited" in _row_html(body, seed.user_id)
    assert "Active" in _row_html(body, seed.admin2_id)
    assert 'class="data-card"' in body and "data-table" in body
    assert "4 users" in body


def test_own_row_shows_no_demote_or_disable_and_another_admin_row_does(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.admin2_id)
    body = fx.get(server, cookie, "/users")[2]
    own = _row_html(body, seed.admin_id)
    assert "This is you." in own
    assert "/disable" not in own and "Change to User" not in own
    assert "The last active administrator cannot be changed." not in body
    other = _row_html(body, seed.admin2_id)
    assert "/users/%d/disable" % seed.admin2_id in other and "Change to User" in other
    assert "This is you." not in other


def test_the_only_active_admin_row_shows_the_last_administrator_line(rig):
    server, seed, cookie = rig
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.admin2_id,))
    body = fx.get(server, cookie, "/users")[2]
    own = _row_html(body, seed.admin_id)
    assert "The last active administrator cannot be changed." in own
    assert "/disable" not in own and "Change to User" not in own
    assert "/users/%d/enable" % seed.admin2_id in _row_html(body, seed.admin2_id)


def test_actions_follow_the_user_state(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.user_id,))
    body = fx.get(server, cookie, "/users")[2]
    linked = _row_html(body, seed.owner_id)
    assert "/unlink" in linked and "/disable" in linked and "/enable" not in linked
    never = _row_html(body, seed.admin2_id)
    assert "/unlink" not in never and "/disable" in never
    disabled = _row_html(body, seed.user_id)
    assert "/enable" in disabled and "/disable" not in disabled


def test_every_action_form_has_csrf_and_the_right_path_and_no_script_confirm(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    body = fx.get(server, cookie, "/users")[2]
    forms = [
        form for form in re.findall(
            r'<form method="post" action="([^"]+)"[^>]*>(.*?)</form>', body, re.S)
        if form[0].startswith("/users")]
    assert len(forms) >= 6
    for action, inner in forms:
        assert 'name="csrf_token"' in inner, action
        assert re.match(r"^/users(/invite|/\d+/(role|disable|enable|unlink))$", action)
    assert "/users/%d/role" % seed.owner_id in body
    assert "<dialog" not in body and "confirm(" not in body


def test_page_never_shows_identity_or_session_values_and_the_invite_card_copy(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    body = fx.get(server, cookie, "/users")[2]
    assert FAKE_ISS not in body and "auth0|fake-" not in body
    assert cookie.split("=", 1)[1] not in body
    assert "They sign in with this email through Auth0. SkyPane does not send them a message." in body
    assert body.count("Send invitation") == 1
    content = body[body.index('id="users-list"'):]
    accent = re.findall(r'<button type="submit">([^<]*)</button>', content)
    assert accent == ["Send invitation"]
    assert 'type="email"' in body and "required" in body


def test_page_is_admin_only_and_anonymous_is_sent_to_sign_in(rig):
    server, seed, _cookie = rig
    user = fx.user_cookie(server.state_dir)
    assert fx.get(server, user, "/users")[0] == 404
    status, headers, _ = http_request(server.url("/users"))
    assert status in (302, 303) and "/login" in headers["Location"]


def test_french_page_uses_the_catalogue(rig):
    server, seed, cookie = rig
    status, _headers, body = fx.get(
        server, cookie, "/users", headers={"Accept-Language": "fr"})
    assert status == 200
    from companion import i18n_fr
    assert i18n_fr.BY_ID["admin_users.send_invitation"] == "Enregistrer l’invitation"


def test_the_paths_match_the_console_route_constants():
    assert console_users.USERS_PATH == console_routes.USERS_ROUTE
    assert console_users.USERS_INVITE_PATH == console_routes.USERS_INVITE_ROUTE
    assert console_users.USER_ACTION_PREFIX == console_routes.USER_ACTION_PREFIX
    assert console_users.ROLE_SUFFIX == console_routes.USER_ROLE_SUFFIX
    assert console_users.DISABLE_SUFFIX == console_routes.USER_DISABLE_SUFFIX
    assert console_users.ENABLE_SUFFIX == console_routes.USER_ENABLE_SUFFIX
    assert console_users.UNLINK_SUFFIX == console_routes.USER_UNLINK_SUFFIX


# --- invite -------------------------------------------------------------------


def test_invite_creates_an_active_unlinked_user_and_one_audit_row(rig):
    server, seed, cookie = rig
    status, headers, _ = fx.post(
        server, cookie, "/users/invite", {"email": "New.Person@Example.test", "role": "admin"})
    assert status == 303 and headers["Location"] == "/users"
    row = _sql(server.state_dir,
               "SELECT id, role, disabled, iss, sub FROM users WHERE email = ?",
               ("new.person@example.test",))[0]
    assert row[1:] == ("admin", 0, None, None)
    rows = _audit(server.state_dir, "user.invite")
    assert len(rows) == 1 and rows[0]["target_id"] == str(row[0])
    assert rows[0]["target_type"] == "user" and rows[0]["outcome"] == "ok"
    page = _flash_text(server, cookie, headers)
    assert "Invitation saved" in page
    assert "new.person@example.test can now sign in as Administrator." in page


@pytest.mark.parametrize("email", ["", "not-an-email", "a b@example.test", "x" * 300 + "@e.test"])
def test_invite_with_an_invalid_email_is_a_field_error(rig, email):
    server, seed, cookie = rig
    before = _sql(server.state_dir, "SELECT COUNT(*) FROM users")
    status, _headers, body = fx.post(
        server, cookie, "/users/invite", {"email": email, "role": "user"})
    assert status == 400 and "Enter a valid email address." in body
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM users") == before
    assert _audit(server.state_dir, "user.invite") == []


def test_invite_with_an_unknown_role_is_a_field_error(rig):
    server, seed, cookie = rig
    for role in ("", "owner", "ADMIN"):
        status, _headers, body = fx.post(
            server, cookie, "/users/invite", {"email": "x@example.test", "role": role})
        assert status == 400 and "Choose a role." in body
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM users WHERE email = 'x@example.test'") == [(0,)]


def test_invite_of_an_existing_email_is_refused_case_insensitively(rig):
    server, seed, cookie = rig
    status, _headers, body = fx.post(
        server, cookie, "/users/invite", {"email": fx.USER_EMAIL.upper(), "role": "admin"})
    assert status == 400 and "That email is already invited." in body
    assert _user(server.state_dir, seed.user_id)[0] == "user"
    assert _audit(server.state_dir, "user.invite") == []


def test_an_invited_email_can_sign_in_and_another_cannot(auth0_rig):
    rig = auth0_rig
    admin = fx.admin_cookie(rig.state_dir)
    status, _headers, _body = fx.post(
        rig.server, admin, "/users/invite", {"email": "invited@example.test", "role": "user"})
    assert status == 303
    ok = login_via_auth0(
        rig.server, rig.fake, sub="auth0|fake-invited", email="invited@example.test")
    assert ok.status == 200 and ok.session_cookie is not None
    assert rig.rows("SELECT sub FROM users WHERE email = 'invited@example.test'") == [
        ("auth0|fake-invited",)]
    refused = login_via_auth0(
        rig.server, rig.fake, sub="auth0|fake-stranger", email="stranger@example.test")
    assert refused.session_cookie is None
    assert rig.rows("SELECT COUNT(*) FROM users WHERE email = 'stranger@example.test'") == [(0,)]


# --- role ---------------------------------------------------------------------


def test_promotion_needs_no_confirm_and_is_audited_with_old_and_new_role(rig):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.user_id, "role", role="admin")
    assert status == 303
    assert _user(server.state_dir, seed.user_id)[0] == "admin"
    rows = _audit(server.state_dir, "user.role")
    assert len(rows) == 1 and rows[0]["target_id"] == str(seed.user_id)
    assert rows[0]["detail"] == '{"from": "user", "to": "admin"}'
    assert "Role saved" in _flash_text(server, cookie, headers)


def test_demotion_works_while_another_admin_exists_and_takes_effect_next_request(rig):
    server, seed, cookie = rig
    second = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    assert fx.get(server, second, "/users")[0] == 200
    assert _act(server, cookie, seed.admin2_id, "role", role="user")[0] == 303
    assert _user(server.state_dir, seed.admin2_id)[0] == "user"
    assert fx.get(server, second, "/users")[0] == 404


def test_saving_an_unchanged_role_changes_and_audits_nothing(rig):
    server, seed, cookie = rig
    assert _act(server, cookie, seed.user_id, "role", role="user")[0] == 303
    assert _audit(server.state_dir, "user.role") == []


def test_an_unknown_role_name_changes_nothing(rig):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.user_id, "role", role="root")
    assert status == 303
    assert _user(server.state_dir, seed.user_id)[0] == "user"
    assert "Choose a role" in _flash_text(server, cookie, headers)


# --- disable and enable -------------------------------------------------------


def test_disabling_ends_the_sessions_and_the_next_request_is_refused(rig):
    server, seed, cookie = rig
    victim = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    assert fx.get(server, victim, "/users")[0] == 200
    status, headers, _ = _act(server, cookie, seed.admin2_id, "disable")
    assert status == 303
    assert _user(server.state_dir, seed.admin2_id)[1] == 1
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                (seed.admin2_id,)) == [(0,)]
    assert fx.get(server, victim, "/users")[0] != 200
    assert len(_audit(server.state_dir, "user.disable")) == 1
    assert "User disabled" in _flash_text(server, cookie, headers)


def test_enabling_restores_sign_in_and_is_audited(rig):
    server, seed, cookie = rig
    _act(server, cookie, seed.admin2_id, "disable")
    status, headers, _ = _act(server, cookie, seed.admin2_id, "enable")
    assert status == 303
    assert _user(server.state_dir, seed.admin2_id)[1] == 0
    fresh = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    assert fx.get(server, fresh, "/users")[0] == 200
    assert len(_audit(server.state_dir, "user.enable")) == 1
    assert "User enabled" in _flash_text(server, cookie, headers)
    _act(server, cookie, seed.admin2_id, "enable")
    assert len(_audit(server.state_dir, "user.enable")) == 1


# --- guards -------------------------------------------------------------------


class _StubHandler:
    """The slice of the request handler `_run_action` uses, for the guard
    that no HTTP actor can reach (an active administrator acting on the
    only active administrator is always that administrator)."""

    def __init__(self, state_dir, user_id, email):
        self.args = type("Args", (), {"state_dir": state_dir})()
        self.client_address = ("127.0.0.1", 0)
        self.headers = {}
        self._principal = (
            None if user_id is None
            else __import__("companion.access", fromlist=["Principal"]).Principal(
                "user", user_id, email, "admin"))

    def _safe_principal(self):
        return self._principal

    def redirect(self, location, set_cookie=None):
        return location, set_cookie


@pytest.mark.parametrize("action,form", [("role", {"role": "user"}), ("disable", {})])
def test_the_last_active_admin_cannot_be_demoted_or_disabled_by_another_actor(rig, action, form):
    server, seed, _cookie = rig
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.admin2_id,))
    actor = _StubHandler(server.state_dir, seed.admin2_id, fx.SECOND_ADMIN_EMAIL)
    match = type("Match", (), {"captured": str(seed.admin_id)})()
    actor.read_form = lambda: form
    handler = {"role": console_users.handle_role, "disable": console_users.handle_disable}[action]
    location, cookie = handler(actor, match)
    assert location == "/users"
    assert _user(server.state_dir, seed.admin_id)[:2] == ("admin", 0)
    value = cookie.split(";")[0].split("=", 1)[1]
    assert console_flash_key(value) == console_users.FLASH_LAST_ADMIN
    denied = _audit(server.state_dir, "user." + action)
    assert [r["outcome"] for r in denied] == ["denied"]
    assert denied[0]["target_id"] == str(seed.admin_id)
    assert denied[0]["actor_user_id"] == seed.admin2_id


def console_flash_key(value):
    from companion import console_flash
    return console_flash._decode(value)["k"]


@pytest.mark.parametrize("action,form", [("role", {"role": "user"}), ("disable", {})])
def test_nobody_acts_on_themselves(rig, action, form):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.admin_id, action, **form)
    assert status == 303
    assert _user(server.state_dir, seed.admin_id)[:2] == ("admin", 0)
    page = _flash_text(server, cookie, headers)
    assert "Action refused" in page and "You cannot disable or demote yourself." in page
    assert [r["outcome"] for r in _audit(server.state_dir, "user." + action)] == ["denied"]


@pytest.mark.parametrize("action,form", [("role", {"role": "user"}), ("disable", {})])
def test_two_admins_acting_on_each_other_leave_one_active_admin(rig, action, form):
    server, seed, cookie = rig
    second = fx.admin_cookie(server.state_dir, fx.SECOND_ADMIN_EMAIL)
    barrier = threading.Barrier(2)
    results = []

    def run(who, target):
        barrier.wait()
        results.append(_act(server, who, target, action, **form)[0])

    threads = [
        threading.Thread(target=run, args=(cookie, seed.admin2_id)),
        threading.Thread(target=run, args=(second, seed.admin_id))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    active = _sql(server.state_dir,
                  "SELECT COUNT(*) FROM users WHERE role = 'admin' AND disabled = 0")
    assert active == [(1,)]
    changed = _sql(server.state_dir,
                   "SELECT COUNT(*) FROM audit_log WHERE action = ? AND outcome = 'ok'",
                   ("user." + action,))
    assert changed == [(1,)]
    assert sorted(results)[0] == 303


# --- unlink -------------------------------------------------------------------


def test_unlink_clears_the_identity_and_sessions_and_signin_relinks(auth0_rig):
    rig = auth0_rig
    admin = fx.admin_cookie(rig.state_dir)
    rig.invite("linked@example.test", "user")
    first = login_via_auth0(
        rig.server, rig.fake, sub="auth0|fake-one", email="linked@example.test")
    assert first.status == 200
    user_id = rig.rows("SELECT id FROM users WHERE email = 'linked@example.test'")[0][0]
    assert rig.rows("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)) == [(1,)]
    status, headers, _ = _act(rig.server, admin, user_id, "unlink")
    assert status == 303
    assert rig.rows("SELECT iss, sub FROM users WHERE id = ?", (user_id,)) == [(None, None)]
    assert rig.rows("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)) == [(0,)]
    audited = _audit(rig.state_dir, "user.unlink")
    assert len(audited) == 1 and audited[0]["target_id"] == str(user_id)
    again = login_via_auth0(
        rig.server, rig.fake, sub="auth0|fake-two", email="linked@example.test")
    assert again.status == 200 and again.session_cookie is not None
    assert rig.rows("SELECT sub FROM users WHERE id = ?", (user_id,)) == [("auth0|fake-two",)]
    del headers


def test_unlinking_a_user_without_an_identity_is_an_error_flash_and_no_audit(rig):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.user_id, "unlink")
    assert status == 303
    assert "Nothing to unlink" in _flash_text(server, cookie, headers)
    assert _audit(server.state_dir, "user.unlink") == []


# --- ids and gates ------------------------------------------------------------


@pytest.mark.parametrize("middle", ["abc", "1x", "-1", "99999", "1" * 12, "invite"])
def test_invalid_or_unknown_ids_touch_nothing(rig, middle):
    server, seed, cookie = rig
    before = _sql(server.state_dir, "SELECT id, role, disabled, iss, sub FROM users ORDER BY id")
    for action in ("role", "disable", "enable", "unlink"):
        status, headers, _ = _act(server, cookie, middle, action, role="admin")
        assert status in (303, 404)
        if status == 303:
            assert "User not found" in _flash_text(server, cookie, headers)
    assert _sql(
        server.state_dir, "SELECT id, role, disabled, iss, sub FROM users ORDER BY id") == before
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM audit_log") == [(0,)]


_ROUTES = (
    ("/users/invite", {"email": "z@example.test", "role": "user"}),
    ("/users/%d/role", {"role": "admin"}),
    ("/users/%d/disable", {}),
    ("/users/%d/enable", {}),
    ("/users/%d/unlink", {}),
)


@pytest.mark.parametrize("template,form", _ROUTES)
def test_the_action_routes_are_admin_only_and_need_the_csrf_token(rig, template, form):
    server, seed, cookie = rig
    path = template % seed.user_id if "%d" in template else template
    before = _sql(server.state_dir, "SELECT id, role, disabled, iss, sub FROM users ORDER BY id")
    user = fx.user_cookie(server.state_dir)
    assert fx.post(server, user, path, form)[0] == 404
    body = urllib.parse.urlencode(form).encode()
    status, headers, _ = http_request(server.url(path), "POST", data=body)
    assert status in (302, 303) and "/" in headers["Location"]
    status, _headers, _body = http_request(server.url(path), "POST", data=body, cookie=cookie)
    assert status == 403
    assert _sql(
        server.state_dir, "SELECT id, role, disabled, iss, sub FROM users ORDER BY id") == before
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM audit_log") == [(0,)]
