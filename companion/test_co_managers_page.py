"""The Manage access and Leave dialogs, the Fleet wiring and the Account
"Shared" mark: dialog markup, the view builder's guards, the return_to
whitelist, and the leave toast. Assertions read served HTML, never source."""
import html
import re

import pytest

import fleet_console_support as fx
from companion import device_scope, prefs
from companion.pages import co_managers_card as card
from companion_app_server import InProcessAppServer, http_request, with_csrf
from companion_markup import css_rules, declarations_for, parse_html
from server import fleet_db, hardware

OWNER = "owner@example.test"
CO_EMAIL = "co-manager@example.test"
OTHER_CO = "Zed.Second@example.test"
STRANGER_EMAIL = "stranger@example.test"
INVITED_EMAIL = "invited-only@example.test"
TOKEN = "csrf-token-value"
FRAME_ID = "d_0a1b2c3d"
PREFIX = "/devices/" + FRAME_ID


@pytest.fixture(autouse=True)
def _request_state():
    prefs.set_request_prefs(lang="en")
    prefs.set_request_csrf(TOKEN)
    device_scope.set_request_scope(None, ())
    yield
    prefs.set_request_prefs(lang="en")
    prefs.set_request_csrf("")
    device_scope.set_request_scope(None, ())


def _view(**overrides):
    values = dict(
        owner_email=OWNER, members=((7, CO_EMAIL, False),), candidates=(),
        viewer_user_id=1, is_admin_viewer=False)
    values.update(overrides)
    return card.CardView(**values)


def _tree(view, return_to=card.RETURN_FLEET, open_=False):
    return parse_html(card.manage_access_dialog_html(
        view, FRAME_ID, "Kitchen", return_to, open_=open_))


def _forms_to(tree, route):
    return [f for f in tree.select("form") if f.attrs["action"].endswith(route)]


def _rows(tree):
    return tree.select("ul.data-cards > li.data-card")


def _hidden(form):
    return {n.attrs["name"]: n.attrs.get("value") for n in form.select("input")}


# --- the dialog: owner ------------------------------------------------------


def test_the_dialog_carries_the_frame_name_the_title_and_the_done_dismissal():
    tree = _tree(_view())
    dialog = tree.select_one("dialog.modal")
    assert dialog.attrs["id"] == "dlg-access-d-0a1b2c3d"
    assert "open" not in dialog.attrs
    assert tree.select_one("h2.modal__title").text() == "Manage access"
    assert tree.select_one(".modal__subtitle").text() == "Kitchen"
    dismiss = tree.select_one("a.modal__dismiss")
    assert dismiss.text() == "Done"
    assert dismiss.attrs["href"] == "/fleet"
    assert tree.select_one("h3").text() == "Co-managers"


def test_a_reopened_dialog_renders_open():
    assert "open" in _tree(_view(), open_=True).select_one("dialog.modal").attrs


def test_the_owner_comes_first_then_the_co_managers_in_the_given_order():
    tree = _tree(_view(members=((8, OTHER_CO, False), (7, "alpha@example.test", False))))
    emails = [row.select_one("span.co-manager__email").text() for row in _rows(tree)]
    assert emails == [OWNER, OTHER_CO, "alpha@example.test"]
    assert "Owner" in _rows(tree)[0].text()


def test_every_co_manager_gets_a_destructive_remove_form_and_the_owner_none():
    tree = _tree(_view(members=((7, CO_EMAIL, False), (8, OTHER_CO, False))))
    rows = _rows(tree)
    assert not rows[0].select("button")
    for row, user_id, email in ((rows[1], "7", CO_EMAIL), (rows[2], "8", OTHER_CO)):
        form = row.select_one("form")
        assert form.attrs["method"] == "post"
        assert form.attrs["action"] == PREFIX + card.REMOVE_ROUTE
        button = row.select_one("button")
        assert button.text() == "Remove"
        assert "calendar-disconnect-btn" in button.attrs["class"]
        assert button.attrs["aria-label"] == "Remove %s from this frame" % email
        assert _hidden(form) == {
            "csrf_token": TOKEN, "return_to": "/fleet", "user_id": user_id}


def test_an_owner_types_an_email_in_a_required_bounded_field():
    tree = _tree(_view(), return_to=card.RETURN_ACCOUNT)
    field = tree.select_one('input[type="email"]')
    assert field.attrs["name"] == "email"
    assert "required" in field.attrs
    assert field.attrs["maxlength"] == "254"
    assert field.attrs["autocomplete"] == "off"
    assert tree.select_one('label[for="%s"]' % field.attrs["id"]).text() == "E-mail address"
    help_id = field.attrs["aria-describedby"]
    assert "must already be invited" in tree.select_one("p#%s" % help_id).text()
    (form,) = _forms_to(tree, card.ADD_ROUTE)
    assert form.attrs["action"] == PREFIX + card.ADD_ROUTE
    assert _hidden(form)["return_to"] == "/account"
    assert form.select_one('button[type="submit"]').text() == "Add co-manager"
    assert not tree.select("select")


def test_an_owner_with_no_co_managers_sees_the_empty_state_after_the_owner_row():
    tree = _tree(_view(members=()))
    assert len(_rows(tree)) == 1
    assert "No co-managers yet" in tree.text()
    assert "Add someone by e-mail address" in tree.text()
    assert "Choose an invited person" not in tree.text()


# --- the dialog: administrator ----------------------------------------------


def test_an_admin_picks_from_the_eligible_people_with_the_email_as_the_value():
    tree = _tree(_view(is_admin_viewer=True, candidates=("a@example.test", "b@example.test")))
    select = tree.select_one("select")
    assert select.attrs["name"] == "email"
    assert "required" in select.attrs
    options = [(o.attrs["value"], o.text()) for o in select.select("option")]
    assert options == [
        ("", "Choose a person"), ("a@example.test", "a@example.test"),
        ("b@example.test", "b@example.test")]
    assert not tree.select('input[type="email"]')
    assert tree.select_one('label[for="%s"]' % select.attrs["id"]).text() == "Invited person"
    (form,) = _forms_to(tree, card.ADD_ROUTE)
    assert form.select_one('button[type="submit"]').text() == "Add co-manager"


def test_an_admin_with_nobody_left_to_add_sees_a_line_and_no_control():
    tree = _tree(_view(is_admin_viewer=True, candidates=()))
    assert "Everyone who is invited is already on this frame." in tree.text()
    assert not tree.select("select")
    assert not _forms_to(tree, card.ADD_ROUTE)


def test_an_admin_with_no_co_managers_gets_the_admin_empty_body():
    tree = _tree(_view(members=(), is_admin_viewer=True, candidates=("a@example.test",)))
    assert "Choose an invited person" in tree.text()
    assert "Add someone by e-mail address" not in tree.text()


def test_the_disabled_pill_and_the_you_pill_show_on_the_right_rows():
    tree = _tree(_view(
        members=((7, CO_EMAIL, True), (8, OTHER_CO, False)), viewer_user_id=8))
    rows = _rows(tree)
    assert "Disabled" in rows[1].text() and "You" not in rows[1].text()
    assert "You" in rows[2].text() and "Disabled" not in rows[2].text()


def test_the_dialog_lands_its_first_focus_on_the_add_control():
    tree = _tree(_view())
    assert "autofocus" in tree.select_one('input[type="email"]').attrs


# --- leave dialog -----------------------------------------------------------


def test_the_leave_dialog_is_confirm_only_destructive_and_posts_no_id():
    tree = parse_html(card.leave_dialog_html(FRAME_ID, "Kitchen"))
    assert tree.select_one("h2.modal__title").text() == "Leave this frame?"
    assert tree.select_one(".modal__subtitle").text() == "Kitchen"
    form = tree.select_one("form")
    assert form.attrs["action"] == PREFIX + card.LEAVE_ROUTE
    assert _hidden(form) == {"csrf_token": TOKEN}
    assert "You will lose access to this frame" in form.text()
    assert "calendar-disconnect-btn" in form.select_one('button[type="submit"]').attrs["class"]
    assert form.select_one('button[type="submit"]').text() == "Leave this frame"
    keep = tree.select_one("a.modal__dismiss")
    assert keep.text() == "Stay on this frame"
    assert "autofocus" in keep.attrs
    assert keep.attrs["href"] == "/account"


# --- escaping, French --------------------------------------------------------


def test_every_address_is_escaped():
    nasty = 'a<b>&"c@example.test'
    raw = card.manage_access_dialog_html(
        _view(owner_email=nasty, members=((7, nasty, False),),
              is_admin_viewer=True, candidates=(nasty,)),
        FRAME_ID, nasty, card.RETURN_FLEET)
    assert nasty not in raw
    assert "<b>" not in raw
    assert html.escape(nasty, quote=True) in raw
    tree = parse_html(raw)
    assert tree.select_one("span.co-manager__email").text() == nasty


def test_the_french_dialogs_use_the_french_catalogue():
    prefs.set_request_prefs(lang="fr")
    text = _tree(_view(is_admin_viewer=True, candidates=("a@example.test",))).text()
    for expected in (
            "Gérer l’accès", "Co-gestionnaires", "Propriétaire", "Retirer",
            "Personne invitée", "Choisir une personne", "Ajouter un co-gestionnaire",
            "Terminé"):
        assert expected in text
    assert "Co-managers" not in text and "Remove" not in text and "Done" not in text
    leave = parse_html(card.leave_dialog_html(FRAME_ID, "Kitchen")).text()
    assert "Quitter ce cadre" in leave
    assert "Rester sur ce cadre" in leave


# --- the return_to whitelist -----------------------------------------------


@pytest.mark.parametrize("value", ["/fleet", "/account"])
def test_only_the_two_host_pages_are_accepted_as_return_targets(value):
    assert card.safe_return_to(value) == value


@pytest.mark.parametrize("value", [
    "https://evil.example/fleet", "//evil.example", "/users", "/fleet/", "/fleet?x=1",
    "/Fleet", " /fleet", "/fleet\r\nSet-Cookie: x=1", "", None, 5, ["/fleet"]])
def test_every_other_return_target_is_ignored(value):
    assert card.safe_return_to(value) is None


# --- stylesheet ------------------------------------------------------------


def test_the_dialog_rules_use_existing_tokens_only(tmp_path):
    server = InProcessAppServer(str(tmp_path / "state"))
    try:
        status, _headers, body = http_request(server.url("/static/style.css"))
    finally:
        server.stop()
    assert status == 200
    css = body.decode("utf-8")
    rules = [rule for rule in css_rules(css)
             if any(sel.startswith(".co-manager__") for sel in rule.selectors)]
    selectors = {sel for rule in rules for sel in rule.selectors}
    assert {".co-manager__email", ".co-manager__who", ".co-manager__row"} <= selectors
    assert declarations_for(css, ".co-manager__email") == {
        "overflow-wrap": "anywhere", "min-width": "0"}
    for rule in rules:
        for _name, value in rule.declarations:
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(", value)
            if "var(" in value:
                assert re.fullmatch(r"var\(--space-(xs|sm|md|lg)\)", value)


# --- over real HTTP ---------------------------------------------------------


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        self.path = "/devices/%s/" % seed.owned_id

    def get(self, who, path=None):
        status, headers, body = http_request(
            self.server.url(path or self.path), cookie=self.cookies[who])
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, route, form):
        cookie = self.cookies[who]
        status, headers, body = http_request(
            self.server.url("/devices/%s%s" % (self.seed.owned_id, route)),
            method="POST", cookie=cookie, data=with_csrf(cookie, form),
            extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def db(self, fn):
        conn = fleet_db.connect(self.server.state_dir)
        try:
            return fn(conn)
        finally:
            conn.close()

    def fleet(self, who="admin", query=""):
        status, _headers, body = self.get(who, "/fleet" + query)
        assert status == 200
        return parse_html(body), body

    def dialog(self, query=""):
        tree, _body = self.fleet(query=query)
        found = tree.select("dialog#dlg-access-%s" % self.seed.owned_id.replace("_", "-"))
        return found[0] if found else None


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "stranger": fx.user_cookie(state_dir, email=STRANGER_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    built = Rig(server, seed, cookies)

    def seed_people(conn):
        built.co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, built.co_id, None)
        fleet_db.add_user(conn, INVITED_EMAIL, "user")
    built.db(seed_people)
    yield built
    server.stop()


def test_fleet_offers_manage_access_in_the_row_menu_with_a_dialog_per_frame(rig):
    tree, _body = rig.fleet()
    dialog_id = "dlg-access-%s" % rig.seed.owned_id.replace("_", "-")
    items = [a for a in tree.select("details.row-menu a") if a.attrs["href"] == "#" + dialog_id]
    assert [a.text() for a in items] == ["Manage access"]
    dialog = tree.select_one("dialog#" + dialog_id)
    emails = [n.text() for n in dialog.select("span.co-manager__email")]
    assert emails == [fx.OWNER_EMAIL, CO_EMAIL]
    assert "open" not in dialog.attrs


def test_the_admin_dialog_offers_the_invited_people_and_remove_forms(rig):
    dialog = rig.dialog()
    options = [o.attrs["value"] for o in dialog.select("select option")]
    assert INVITED_EMAIL in options
    (remove,) = _forms_to(dialog, card.REMOVE_ROUTE)
    assert remove.attrs["action"] == "/devices/%s%s" % (rig.seed.owned_id, card.REMOVE_ROUTE)


def test_access_query_opens_only_the_named_frames_dialog(rig):
    dialog = rig.dialog("?access=" + rig.seed.owned_id)
    assert "open" in dialog.attrs
    tree, _body = rig.fleet(query="?access=" + rig.seed.owned_id)
    opened = [d for d in tree.select("dialog") if "open" in d.attrs]
    assert [d.attrs["id"] for d in opened] == [dialog.attrs["id"]]


def test_an_unknown_access_value_opens_nothing_and_is_not_echoed(rig):
    probe = "zz_<script>x"
    tree, body = rig.fleet(query="?access=" + probe.replace("<", "%3C").replace(">", "%3E"))
    assert not [d for d in tree.select("dialog") if "open" in d.attrs]
    assert probe not in body


def test_neither_an_owner_nor_a_co_manager_can_open_fleet(rig):
    for who in ("owner", "co", "stranger"):
        assert rig.get(who, "/fleet")[0] in (403, 404)


def test_the_invited_list_never_reaches_a_non_admin_through_the_frame_pages(rig):
    for who in ("owner", "co"):
        _status, _headers, body = rig.get(who)
        assert INVITED_EMAIL not in html.unescape(body)
        assert "co-manager__" not in body


def test_home_carries_no_co_managers_card_for_anyone(rig):
    for who in ("owner", "co", "admin"):
        status, _headers, body = rig.get(who)
        assert status == 200
        assert "home-co-managers" not in body
        assert "Co-managers" not in html.unescape(body)
    status, _headers, body = rig.get("stranger")
    assert status == 404
    assert CO_EMAIL not in body


def test_a_disabled_co_manager_keeps_the_row_with_a_pill(rig):
    other = rig.db(lambda c: fleet_db.add_user(c, OTHER_CO.lower(), "user"))
    rig.db(lambda c: fleet_db.add_co_manager(c, rig.seed.owned_id, other, None))
    rig.db(lambda c: fleet_db.set_user_disabled(c, OTHER_CO.lower(), True))
    disabled = [r for r in rig.dialog().select("li.data-card") if OTHER_CO.lower() in r.text()]
    assert "Disabled" in disabled[0].text()


def test_a_role_change_keeps_the_co_manager_row(rig):
    def co_rows():
        return [n.text() for n in rig.dialog().select("span.co-manager__email")]

    for role in ("admin", "user"):
        rig.db(lambda c, role=role: c.execute(
            "UPDATE users SET role = ? WHERE id = ?", (role, rig.co_id)))
        assert CO_EMAIL in co_rows()


def test_adding_with_a_fleet_return_goes_back_with_the_dialog_reopened(rig):
    status, headers, _body = rig.post(
        "admin", card.ADD_ROUTE, {"email": INVITED_EMAIL, "return_to": "/fleet"})
    assert status == 303
    assert headers["Location"] == "/fleet?access=" + rig.seed.owned_id
    assert "sp_flash=" in headers["Set-Cookie"]
    cookie = rig.cookies["admin"] + "; " + headers["Set-Cookie"].split(";")[0]
    status, _headers, body = http_request(
        rig.server.url(headers["Location"]), cookie=cookie)
    text = html.unescape(body.decode("utf-8"))
    assert status == 200
    assert "Co-manager added" in text
    dialog = parse_html(body.decode("utf-8")).select_one("dialog[open]")
    assert INVITED_EMAIL in [n.text() for n in dialog.select("span.co-manager__email")]


def test_a_refused_add_and_a_removal_return_to_fleet_too(rig):
    _s, headers, _b = rig.post(
        "admin", card.ADD_ROUTE, {"email": "nobody@example.test", "return_to": "/fleet"})
    assert headers["Location"] == "/fleet?access=" + rig.seed.owned_id
    assert "nobody@example.test" not in str(headers)
    _s, headers, _b = rig.post(
        "admin", card.REMOVE_ROUTE, {"user_id": str(rig.co_id), "return_to": "/fleet"})
    assert headers["Location"] == "/fleet?access=" + rig.seed.owned_id
    assert rig.dialog().select("span.co-manager__email")[-1].text() == fx.OWNER_EMAIL


def test_the_account_return_uses_the_flash_query(rig):
    status, headers, _body = rig.post(
        "owner", card.ADD_ROUTE, {"email": INVITED_EMAIL, "return_to": "/account"})
    assert status == 303
    assert headers["Location"] == "/account?access=%s&flash=%s" % (
        rig.seed.owned_id, card.FLASH_ADDED)


@pytest.mark.parametrize("target", [
    "https://evil.example/", "//evil.example/", "/users", "/fleet/x", "javascript:alert(1)"])
def test_an_unlisted_return_target_falls_back_to_the_frame_home(rig, target):
    status, headers, _body = rig.post(
        "admin", card.ADD_ROUTE, {"email": INVITED_EMAIL, "return_to": target})
    assert status == 303
    assert headers["Location"] == "%s?flash=%s" % (rig.path, card.FLASH_ADDED)
    assert "Set-Cookie" not in headers


def test_adding_without_a_return_target_keeps_the_home_toast(rig):
    status, headers, _body = rig.post("owner", card.ADD_ROUTE, {"email": INVITED_EMAIL})
    assert status == 303
    assert headers["Location"].endswith("?flash=" + card.FLASH_ADDED)
    status, _headers, body = rig.get("owner", headers["Location"])
    assert status == 200
    assert "Co-manager added" in html.unescape(body)


def test_a_co_manager_cannot_use_the_forms_whatever_the_return_target(rig):
    status, _headers, _body = rig.post(
        "co", card.ADD_ROUTE, {"email": INVITED_EMAIL, "return_to": "/fleet"})
    assert status in (403, 404)
    assert rig.db(lambda c: fleet_db.get_user_by_email(c, INVITED_EMAIL)) is not None
    assert [m for m in rig.dialog().select("span.co-manager__email")
            if m.text() == INVITED_EMAIL] == []


def test_a_french_request_renders_the_dialog_in_french(rig):
    status, _headers, body = http_request(
        rig.server.url("/fleet"), cookie=rig.cookies["admin"],
        extra_headers={"Accept-Language": "fr"})
    text = html.unescape(body.decode("utf-8"))
    assert status == 200
    assert "Gérer l’accès" in text
    assert "Co-gestionnaires" in text


def _check_in(rig, frame_id, age_hours):
    import datetime
    from server import history_db
    state_dir = device_scope.find_device(rig.server.state_dir, frame_id).state_dir
    stamp = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(hours=age_hours)).isoformat(timespec="seconds")
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, stamp, 3900)


def _fleet_word(rig, name):
    tree, _body = rig.fleet()
    row = [r for r in tree.select("li.entity-row") if name in r.text()][0]
    return row.select_one('[role="img"]').attrs["aria-label"]


def _home_word(rig, path):
    _status, _headers, home = rig.get("admin", path)
    return parse_html(home).select_one(".home-state__dot").attrs["aria-label"]


def test_a_late_served_frame_reads_overdue_on_both_home_and_fleet(rig):
    # Late means three wake intervals without a check-in; the served frame is
    # never "offline", so Overdue is the only word that tells it apart.
    from server import device_config
    device_config.save_device_config(rig.server.state_dir, wake_interval_s=1800)
    _check_in(rig, rig.seed.live_id, 3.5)
    assert _home_word(rig, "/") == "Overdue"
    assert _fleet_word(rig, "Orly frame") == "Overdue"


def test_a_silent_paired_frame_reads_the_same_word_on_home_and_fleet(rig):
    _check_in(rig, rig.seed.owned_id, 3.5)
    word = _home_word(rig, rig.path)
    assert word == "No contact"
    assert _fleet_word(rig, "Kitchen") == word


def test_a_battery_empty_frame_reads_the_same_word_on_home_and_fleet(rig):
    _check_in(rig, rig.seed.owned_id, 0.1)
    state_dir = device_scope.find_device(rig.server.state_dir, rig.seed.owned_id).state_dir
    from companion import wake
    from server import state_store
    state = state_store.load_poll_state(state_dir)
    state[wake.BATTERY_CRITICAL_STATE_KEY] = True
    state_store.save_poll_state(state_dir, state)
    word = _home_word(rig, rig.path)
    assert word == "Low battery"
    assert _fleet_word(rig, "Kitchen") == word


# --- the Account page ------------------------------------------------------


def _account(rig, who, query="", language=None):
    extra = {"Accept-Language": language} if language else None
    status, _headers, body = http_request(
        rig.server.url("/account" + query), cookie=rig.cookies[who], extra_headers=extra)
    assert status == 200
    return body.decode("utf-8")


def _frame_names(body):
    return [n.text() for n in parse_html(body).select("li.data-card span.text-heading")]


def test_a_co_managed_frame_is_marked_shared_with_the_owner_address(rig):
    tree = parse_html(_account(rig, "co"))
    (row,) = tree.select("li.data-card")
    assert "Shared" in [n.text() for n in row.select("span.banner__pill")]
    assert "Owner: %s" % fx.OWNER_EMAIL in row.text()
    assert row.select_one("a.text-link").attrs["href"] == rig.path


def test_an_owned_frame_carries_no_shared_mark(rig):
    tree = parse_html(_account(rig, "owner"))
    rows = [r for r in tree.select("li.data-card") if "Kitchen" in r.text()]
    assert rows
    assert "Shared" not in rows[0].text()
    assert "Owner:" not in rows[0].text()


def test_an_admin_lists_only_the_frames_they_own_or_co_manage(rig):
    before = _frame_names(_account(rig, "admin"))
    assert "Kitchen" not in before
    assert len(before) == 1
    admin_id = rig.db(lambda c: fleet_db.get_user_by_email(c, fx.ADMIN_EMAIL)["id"])
    rig.db(lambda c: fleet_db.add_co_manager(c, rig.seed.owned_id, admin_id, None))
    after = _frame_names(_account(rig, "admin"))
    assert sorted(after) == sorted(before + ["Kitchen"])
    tree = parse_html(_account(rig, "admin"))
    shared = [r for r in tree.select("li.data-card") if "Kitchen" in r.text()]
    assert "Shared" in shared[0].text()


def test_a_user_with_no_frames_sees_the_unchanged_empty_state(rig):
    body = html.unescape(_account(rig, "stranger"))
    assert "Your frames will appear here" in body
    assert "Shared" not in body


def test_frames_stay_ordered_by_name(rig):
    other = rig.db(lambda c: fleet_db.add_device(
        c, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY, rig.co_id,
        name="Attic window", state_path="auto"))
    assert other
    assert _frame_names(_account(rig, "co")) == ["Attic window", "Kitchen"]


def test_only_the_leave_flash_renders_a_toast_on_account(rig):
    body = html.unescape(_account(rig, "co", "?flash=" + card.FLASH_LEFT))
    toast = parse_html(body).select_one("div.toast-region--flash div.toast")
    assert toast.attrs["role"] == "status"
    assert "You left the frame" in toast.text()
    for key in (
            card.FLASH_ADDED, card.FLASH_REMOVED, card.FLASH_ADD_REFUSED,
            card.FLASH_FAILED, card.FLASH_LEAVE_NOOP, "unknown_key"):
        assert not parse_html(_account(rig, "co", "?flash=" + key)).select("div.toast-region--flash")


def test_the_leave_toast_is_french_for_a_french_request(rig):
    body = html.unescape(_account(rig, "co", "?flash=" + card.FLASH_LEFT, "fr"))
    assert "Vous avez quitté le cadre" in body
    assert "Partagé" in body


def test_leaving_lands_on_account_with_the_toast_and_the_frame_gone(rig):
    status, headers, _body = rig.post("co", card.LEAVE_ROUTE, {})
    assert status == 303
    assert headers["Location"] == "/account?flash=" + card.FLASH_LEFT
    status, _headers, body = http_request(
        rig.server.url(headers["Location"]), cookie=rig.cookies["co"])
    text = html.unescape(body.decode("utf-8"))
    assert status == 200
    assert "You left the frame" in text
    assert "Kitchen" not in _frame_names(text)
