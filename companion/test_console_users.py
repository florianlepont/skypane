"""The Users page and its five actions over real HTTP: the page's guard
states, invite, role change, disable and enable, identity unlink, the
last-administrator and self-action guards (including two concurrent
requests), audit rows and the access gates."""
import html
import re
import threading
import urllib.parse

import pytest

import fleet_console_support as fx
from companion import console_routes, console_users, prefs
from companion_app_server import http_request, login_via_auth0, served_stylesheet
from companion_markup import declarations_for
from server import fleet_db, hardware

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


def _visible_status(row):
    """The status pills of a row that are shown (the Active switch flips two
    marks in place, so the other one is in the markup, hidden)."""
    return [
        name for name, rest in re.findall(r'users-pill--(\w+)"([^>]*)>', row)
        if "hidden" not in rest and not name == "you"]


def _row_html(body, user_id):
    """The table row holding this user's role form (its select id)."""
    for match in re.finditer(r'<tr class="users-row[^"]*"[^>]*>.*?</tr>', body, re.S):
        if 'for="role-%d"' % user_id in match.group(0) or (
                "/users/%d/" % user_id in match.group(0)):
            return match.group(0)
    raise AssertionError("no table row for user %d" % user_id)


def _row_forms(body, user_id):
    """action -> inner html of every form in the user's row."""
    return dict(re.findall(
        r'<form method="post" action="([^"]+)"[^>]*>(.*?)</form>',
        _row_html(body, user_id), re.S))


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


def test_the_page_lists_every_user_as_a_table_row_with_role_frames_and_pills(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.admin2_id, seed.owner_id)
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.owner_id,))
    status, _headers, body = fx.get(server, cookie, "/users")
    assert status == 200
    for email in (fx.ADMIN_EMAIL, fx.OWNER_EMAIL, fx.SECOND_ADMIN_EMAIL, fx.USER_EMAIL):
        assert email in body
    assert body.count('<tr class="users-row') == 4
    assert "entity-row" not in body and "dlg-user-" not in body and "Manage" not in body
    for heading in ("User", "Role", "Frames", "Last sign-in", "Active"):
        assert ">%s</th>" % heading in body
    assert "4 users" in body
    assert 'value="admin" selected' in _row_html(body, seed.admin2_id)
    assert "0 frames" in _row_html(body, seed.admin2_id)
    assert _visible_status(_row_html(body, seed.owner_id)) == ["disabled"]
    assert _visible_status(_row_html(body, seed.admin2_id)) == ["active"]
    assert _visible_status(_row_html(body, seed.user_id)) == ["invited"]
    assert "Never signed in" in _row_html(body, seed.user_id)
    own = _row_html(body, seed.admin_id)
    assert ">You<" in own and _visible_status(own) == ["active"]
    assert "Active: %s" % fx.USER_EMAIL in _row_html(body, seed.user_id)


def test_the_last_sign_in_is_a_relative_time_for_a_user_who_signed_in(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.owner_id)
    _sql(server.state_dir,
         "INSERT INTO sessions (id_hash, user_id, principal, created_at, last_seen_at, "
         "expires_at) VALUES ('h', ?, 'user', strftime('%s','now') - 9000, "
         "strftime('%s','now') - 7200, strftime('%s','now') + 9000)", (seed.owner_id,))
    body = fx.get(server, cookie, "/users")[2]
    owner = _row_html(body, seed.owner_id)
    assert "data-relative" in owner and "2h ago" in owner
    assert "Never signed in" not in owner


def test_a_signed_in_user_never_shows_invited_and_a_never_signed_in_one_does(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.owner_id)
    body = fx.get(server, cookie, "/users")[2]
    assert "Invited" not in _row_html(body, seed.owner_id)
    assert "Invited" in _row_html(body, seed.user_id)


def test_the_header_opens_an_invite_dialog_with_role_defaulting_to_user(rig):
    server, seed, cookie = rig
    body = fx.get(server, cookie, "/users")[2]
    assert re.search(
        r'<a href="#dlg-invite-user" class="page-header__action" data-modal-open>'
        r'\+ Invite a user</a>', body)
    dialog = re.search(r'<dialog class="modal" id="dlg-invite-user".*?</dialog>', body, re.S)
    assert dialog and " open" not in dialog.group(0).split(">", 1)[0]
    html = dialog.group(0)
    assert 'action="/users/invite"' in html and 'name="csrf_token"' in html
    assert 'type="email"' in html and "required" in html and 'maxlength="254"' in html
    assert re.search(r'<option value="user" selected>User</option>', html)
    assert "<option value=\"admin\" selected" not in html
    assert ">Invite user</button>" in html and "Send invitation" not in body
    assert "SkyPane does not send them a message, so tell them to sign in." in html
    assert ">Back to Users</a>" in html


def test_a_hostile_email_is_escaped_and_the_row_is_not_monospace(rig):
    server, seed, cookie = rig
    hostile = "<img src=x onerror=alert(1)>@e.test"
    _sql(server.state_dir, "UPDATE users SET email = ? WHERE id = ?", (hostile, seed.user_id))
    body = fx.get(server, cookie, "/users")[2]
    assert hostile not in body and "&lt;img src=x" in body
    css = served_stylesheet(server)
    declared = declarations_for(css, ".users-email")
    assert "monospace" not in str(declared)
    assert declared.get("overflow-wrap") == "anywhere" and "text-overflow" not in declared


def test_own_row_shows_the_guard_in_place_of_the_role_select_and_locks_the_switch(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.admin2_id)
    body = fx.get(server, cookie, "/users")[2]
    own = _row_html(body, seed.admin_id)
    assert "This is you." in own and "<select" not in own and "Save role" not in own
    assert 'role="switch" aria-checked="true"' in own and " disabled>" in own
    assert "The last active administrator cannot be changed." not in body
    other = _row_html(body, seed.admin2_id)
    assert "This is you." not in other
    assert "<select" in other and " disabled>" not in other
    assert "/users/%d/disable" % seed.admin2_id in _row_forms(body, seed.admin2_id)


def test_the_only_active_admin_row_shows_the_last_administrator_sentence(rig):
    server, seed, cookie = rig
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.admin2_id,))
    body = fx.get(server, cookie, "/users")[2]
    own = _row_html(body, seed.admin_id)
    assert "The last active administrator cannot be changed." in own
    assert "<select" not in own and " disabled>" in own
    off = _row_forms(body, seed.admin2_id)
    assert "/users/%d/enable" % seed.admin2_id in off
    assert 'aria-checked="false"' in _row_html(body, seed.admin2_id)


def test_row_controls_follow_the_user_state(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    _sql(server.state_dir, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.user_id,))
    body = fx.get(server, cookie, "/users")[2]
    linked = _row_forms(body, seed.owner_id)
    assert set(linked) == {"/users/%d/%s" % (seed.owner_id, a)
                           for a in ("role", "disable", "unlink")}
    row = _row_html(body, seed.owner_id)
    assert 'data-autosubmit' in row and "<noscript><button" in row
    assert row.count('class="row-menu"') == 1 and ">Reset sign-in<" in row
    never = _row_forms(body, seed.admin2_id)
    assert not any(action.endswith("/unlink") for action in never)
    assert ">Reset sign-in<" not in _row_html(body, seed.admin2_id)
    assert 'href="#dlg-delete-user-%d"' % seed.admin2_id in _row_html(body, seed.admin2_id)
    assert any(action.endswith("/disable") for action in never)
    disabled = _row_forms(body, seed.user_id)
    assert any(action.endswith("/enable") for action in disabled)
    assert not any(action.endswith("/disable") for action in disabled)


def test_every_action_form_has_csrf_and_the_right_path_and_no_script_confirm(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    body = fx.get(server, cookie, "/users")[2]
    forms = [
        form for form in re.findall(
            r'<form method="post" action="([^"]+)"[^>]*>(.*?)</form>', body, re.S)
        if form[0].startswith("/users")]
    assert len(forms) >= 9
    for action, inner in forms:
        assert 'name="csrf_token"' in inner, action
        assert re.match(r"^/users(/invite|/\d+/(role|disable|enable|unlink|delete))$", action)
    assert "/users/%d/role" % seed.owner_id in body
    table = body.split("<table")[1].split("</table>")[0]
    assert table.count("<details") == table.count('<tr class="users-row')
    assert "confirm(" not in body
    assert "/users/%d/delete" % seed.owner_id in body


def test_page_never_shows_identity_or_session_values(rig):
    server, seed, cookie = rig
    _link(server.state_dir, seed.admin_id, seed.owner_id)
    body = fx.get(server, cookie, "/users")[2]
    assert FAKE_ISS not in body and "auth0|fake-" not in body
    assert cookie.split("=", 1)[1] not in body


def test_a_refused_invite_rerenders_the_page_with_the_dialog_open(rig):
    server, seed, cookie = rig
    status, _headers, body = fx.post(
        server, cookie, "/users/invite", {"email": "not-an-email", "role": "admin"})
    assert status == 400
    head = re.search(r'<dialog class="modal" id="dlg-invite-user"[^>]*>', body).group(0)
    assert " open" in head
    assert 'value="not-an-email"' in body and "Enter a valid email address." in body
    assert 'aria-invalid="true"' in body and "dlg-invite-user-email-error" in body
    assert re.search(r'<option value="admin" selected>Administrator</option>', body)


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
    assert "Inviter" in body and "+ Inviter un utilisateur" in body
    assert "Retour aux utilisateurs" in body and "Gérer" not in body
    for heading in ("Utilisateur", "Rôle", "Cadres", "Dernière connexion", "Actif"):
        assert ">%s</th>" % heading in body
    assert "0 cadre" in body and "Vous" in body and "Jamais connecté" in body
    assert "Le rôle s’enregistre dès qu’on le change." not in body
    assert i18n_fr.BY_ID["admin_users.invite_user"] == "Inviter"


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
    assert "Invited" in page
    assert "Tell new.person@example.test to sign in with this address." in page


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


@pytest.mark.parametrize("lang,target,role,title,submit,keep", [
    ("en", "user", "admin", "Make this person an administrator?", "Make administrator",
     "Keep as user"),
    ("fr", "user", "admin", "Nommer cette personne administrateur\u00a0?",
     "Nommer administrateur", "Laisser utilisateur"),
    ("en", "admin2", "user", "Remove administrator rights?", "Remove rights",
     "Keep as administrator"),
    ("fr", "admin2", "user", "Retirer les droits d’administrateur\u00a0?",
     "Retirer les droits", "Laisser administrateur"),
])
def test_a_role_change_asks_first_and_changes_nothing_until_confirmed(
        rig, lang, target, role, title, submit, keep):
    server, seed, cookie = rig
    user_id = {"user": seed.user_id, "admin2": seed.admin2_id}[target]
    email = {"user": fx.USER_EMAIL, "admin2": fx.SECOND_ADMIN_EMAIL}[target]
    before = _user(server.state_dir, user_id)
    status, headers, _body = _act(server, cookie, user_id, "role", role=role)
    asking = "/users?role_change=%d&role=%s" % (user_id, role)
    assert (status, headers["Location"]) == (303, asking)
    status, _headers, body = http_request(
        server.url(asking), cookie=cookie, extra_headers={"Accept-Language": lang})
    page = body.decode("utf-8")
    assert status == 200
    assert _user(server.state_dir, user_id) == before
    assert _audit(server.state_dir, "user.role") == []
    dialog = re.search(
        r'<dialog class="modal" id="dlg-role-user-%d"[^>]* open.*?</dialog>' % user_id,
        page, re.S)
    assert dialog is not None, "no open confirmation dialog"
    text = html.unescape(re.sub(r"<[^>]+>", " ", dialog.group(0)))
    for wanted in (title, submit, keep, email):
        assert wanted in text, (wanted, text)
    form = dialog.group(0)
    assert 'action="/users/%d/role"' % user_id in form
    assert 'name="role" value="%s"' % role in form
    assert 'name="confirmed" value="1"' in form
    # Enter never confirms: the way out holds the focus.
    assert re.search(r'<a class="modal__dismiss" href="/users"[^>]* autofocus', form)
    # The row still shows the stored role.
    assert re.search(
        r'<option value="%s" selected' % before[0], _row_html(page, user_id))


@pytest.mark.parametrize("query", [
    "role_change=%(user)d&role=user",       # nothing would change
    "role_change=%(user)d&role=root",
    "role_change=99999&role=admin",
    "role_change=1x&role=admin",
    "role_change=%(user)d",
])
def test_an_address_that_asks_nothing_real_opens_no_confirmation(rig, query):
    server, seed, cookie = rig
    status, _headers, page = fx.get(server, cookie, "/users?" + query % {"user": seed.user_id})
    assert status == 200
    assert "dlg-role-user-" not in page
    assert _user(server.state_dir, seed.user_id)[0] == "user"


def test_a_confirmed_promotion_is_audited_with_old_and_new_role(rig):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.user_id, "role", role="admin", confirmed="1")
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
    assert _act(server, cookie, seed.admin2_id, "role", role="user", confirmed="1")[0] == 303
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


def test_disabling_an_owner_removes_co_managers_and_enabling_restores_nothing(rig):
    server, seed, cookie = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        frame = fleet_db.add_device(
            conn, "aa:bb:cc:dd:ee:21", "ab" * 32, hardware.LEGACY_KEY, seed.owner_id, token="t21",
            state_path="auto")
        fleet_db.add_co_manager(conn, frame, seed.user_id, seed.owner_id)
        fleet_db.add_co_manager(conn, frame, seed.admin2_id, seed.owner_id)
        conn.commit()
    finally:
        conn.close()
    assert _act(server, cookie, seed.owner_id, "disable")[0] == 303
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM device_co_managers") == [(0,)]
    rows = _audit(server.state_dir, "device.co_manager_remove")
    assert len(rows) == 2
    assert all('"owner_disabled"' in r["detail"] and r["target_id"] == frame for r in rows)
    assert len(_audit(server.state_dir, "user.disable")) == 1
    _act(server, cookie, seed.owner_id, "enable")
    assert _sql(server.state_dir, "SELECT COUNT(*) FROM device_co_managers") == [(0,)]
    assert len(_audit(server.state_dir, "device.co_manager_remove")) == 2


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


@pytest.mark.parametrize("action,form", [("role", {"role": "user", "confirmed": "1"}), ("disable", {})])
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


@pytest.mark.parametrize("action,form", [("role", {"role": "user", "confirmed": "1"}), ("disable", {})])
def test_nobody_acts_on_themselves(rig, action, form):
    server, seed, cookie = rig
    status, headers, _ = _act(server, cookie, seed.admin_id, action, **form)
    assert status == 303
    assert _user(server.state_dir, seed.admin_id)[:2] == ("admin", 0)
    page = _flash_text(server, cookie, headers)
    assert "Action refused" in page and "You cannot disable or demote yourself." in page
    assert [r["outcome"] for r in _audit(server.state_dir, "user." + action)] == ["denied"]


@pytest.mark.parametrize("action,form", [("role", {"role": "user", "confirmed": "1"}), ("disable", {})])
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
    for action in ("role", "disable", "enable", "unlink", "delete"):
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
    ("/users/%d/delete", {}),
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
