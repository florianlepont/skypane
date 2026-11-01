"""The Co-managers card on the frame's Home page and the Account "Shared"
mark: the three card shapes as markup, the view builder's guards, and the
leave toast. Assertions read served HTML, never source."""
import html
import re

import pytest

from companion import device_scope, prefs
from companion.pages import co_managers_card as card
from companion_app_server import InProcessAppServer, http_request
from companion_markup import css_rules, declarations_for, parse_html

OWNER = "owner@example.test"
CO_EMAIL = "co-manager@example.test"
OTHER_CO = "Zed.Second@example.test"
STRANGER_EMAIL = "stranger@example.test"
INVITED_EMAIL = "invited-only@example.test"
TOKEN = "csrf-token-value"


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
        can_manage=True, viewer_user_id=1, viewer_is_member=False,
        is_admin_viewer=False)
    values.update(overrides)
    return card.CardView(**values)


def _tree(view):
    return parse_html(card.render(view))


def _add_forms(tree):
    return [f for f in tree.select("form") if f.attrs["action"] == card.ADD_ROUTE]


def _rows(tree):
    return tree.select("ul.data-cards > li.data-card")


# --- manage shape: owner ----------------------------------------------------


def test_the_owner_sees_the_owner_first_then_co_managers_by_email():
    view = _view(members=((8, OTHER_CO, False), (7, "alpha@example.test", False)))
    tree = _tree(view)
    emails = [row.select_one("span.co-manager__email").text() for row in _rows(tree)]
    # The view builder orders members; the card keeps the order it is given.
    assert emails == [OWNER, OTHER_CO, "alpha@example.test"]
    assert "Owner" in _rows(tree)[0].text()
    section = tree.select_one("section.page-section")
    assert section.attrs["aria-labelledby"] == "home-co-managers"
    assert tree.select_one("h2#home-co-managers").text() == "Co-managers"


def test_an_owner_gets_one_remove_form_per_co_manager_and_never_one_for_the_owner():
    tree = _tree(_view(members=((7, CO_EMAIL, False), (8, OTHER_CO, False))))
    rows = _rows(tree)
    assert not rows[0].select("button")
    for row, user_id, email in ((rows[1], "7", CO_EMAIL), (rows[2], "8", OTHER_CO)):
        form = row.select_one("form")
        assert form.attrs["method"] == "post"
        assert form.attrs["action"] == card.REMOVE_ROUTE
        button = row.select_one("button")
        assert button.text() == "Remove"
        assert button.attrs["aria-label"] == "Remove %s from this frame" % email
        hidden = {n.attrs["name"]: n.attrs["value"] for n in form.select("input")}
        assert hidden == {"csrf_token": TOKEN, "user_id": user_id}


def test_an_owner_types_an_email_in_a_required_bounded_field():
    tree = _tree(_view())
    field = tree.select_one("input#co-manager-email")
    assert field.attrs["type"] == "email"
    assert field.attrs["name"] == "email"
    assert "required" in field.attrs
    assert field.attrs["maxlength"] == "254"
    assert field.attrs["autocomplete"] == "off"
    assert tree.select_one('label[for="co-manager-email"]').text() == "E-mail address"
    assert "must already be invited" in tree.select_one("p#co-manager-email-help").text()
    form = field.parent.parent
    assert form.attrs["action"] == card.ADD_ROUTE
    assert form.select_one('button[type="submit"]').text() == "Add co-manager"
    assert not tree.select("select")
    assert not tree.select("details")


def test_an_owner_with_no_co_managers_sees_the_empty_state_after_the_owner_row():
    tree = _tree(_view(members=()))
    assert len(_rows(tree)) == 1
    text = tree.text()
    assert "No co-managers yet" in text
    assert "Add someone by e-mail address" in text
    assert "Choose an invited person" not in text


# --- manage shape: administrator -------------------------------------------


def test_an_admin_picks_from_the_eligible_people_with_the_email_as_the_value():
    view = _view(is_admin_viewer=True, candidates=("a@example.test", "b@example.test"))
    tree = _tree(view)
    select = tree.select_one("select")
    assert select.attrs["name"] == "email"
    assert "required" in select.attrs
    options = [(o.attrs["value"], o.text()) for o in select.select("option")]
    assert options == [
        ("", "Choose a person"), ("a@example.test", "a@example.test"),
        ("b@example.test", "b@example.test")]
    assert not tree.select('input[name="email"]')
    assert tree.select_one('label[for="co-manager-person"]').text() == "Invited person"
    (form,) = _add_forms(tree)
    assert form.select_one('button[type="submit"]').text() == "Add co-manager"


def test_an_admin_with_nobody_left_to_add_sees_a_line_and_no_control():
    tree = _tree(_view(is_admin_viewer=True, candidates=()))
    assert "Everyone who is invited is already on this frame." in tree.text()
    assert not tree.select("select")
    assert not _add_forms(tree)


def test_an_admin_with_no_co_managers_gets_the_admin_empty_body():
    tree = _tree(_view(members=(), is_admin_viewer=True, candidates=("a@example.test",)))
    assert "Choose an invited person" in tree.text()
    assert "Add someone by e-mail address" not in tree.text()


def test_the_disabled_pill_shows_to_a_manager_and_not_to_a_read_only_member():
    members = ((7, CO_EMAIL, True), (8, OTHER_CO, False))
    manage = _tree(_view(members=members))
    assert "Disabled" in _rows(manage)[1].text()
    assert "Disabled" not in _rows(manage)[2].text()
    read_only = _tree(_view(
        members=members, can_manage=False, viewer_is_member=True, viewer_user_id=8))
    assert "Disabled" not in read_only.text()


def test_an_admin_who_is_also_a_member_gets_manage_controls_and_no_leave():
    tree = _tree(_view(
        is_admin_viewer=True, candidates=("a@example.test",), viewer_user_id=7,
        viewer_is_member=True))
    assert not tree.select("details")
    assert tree.select("select")
    assert tree.select("button.calendar-disconnect-btn")
    assert "You" in _rows(tree)[1].text()


# --- read-only shape --------------------------------------------------------


def _read_only(**overrides):
    return _view(
        can_manage=False, viewer_user_id=7, viewer_is_member=True, **overrides)


def test_a_co_manager_sees_the_list_a_you_pill_and_no_manage_controls():
    tree = _tree(_read_only(members=((7, CO_EMAIL, False), (8, OTHER_CO, False))))
    rows = _rows(tree)
    assert "You" in rows[1].text() and "You" not in rows[2].text()
    assert not tree.select('input[name="email"]')
    assert not tree.select("select")
    assert not tree.select('input[name="user_id"]')
    assert "Only the owner or an administrator can change the list." in tree.text()
    assert "People who can change" not in tree.text()


def test_the_leave_block_is_a_closed_two_step_form_that_posts_no_id():
    tree = _tree(_read_only())
    details = tree.select_one("details.fleet-confirm")
    assert "open" not in details.attrs
    assert details.select_one("summary").text() == "Leave this frame"
    form = details.select_one("form")
    assert form.attrs["method"] == "post"
    assert form.attrs["action"] == card.LEAVE_ROUTE
    hidden = {n.attrs["name"]: n.attrs.get("value") for n in form.select("input")}
    assert hidden == {"csrf_token": TOKEN}
    assert "You will lose access to this frame" in form.text()
    assert form.select_one("button.calendar-disconnect-btn").text() == "Leave this frame"
    keep = form.select_one("a.text-link")
    assert keep.text() == "Stay on this frame"


# --- escaping, French, prefixed paths ---------------------------------------


def test_every_address_is_escaped():
    nasty = 'a<b>&"c@example.test'
    raw = card.render(_view(
        owner_email=nasty, members=((7, nasty, False),),
        is_admin_viewer=True, candidates=(nasty,)))
    assert nasty not in raw
    assert "<b>" not in raw
    assert html.escape(nasty, quote=True) in raw
    tree = parse_html(raw)
    assert tree.select_one("span.co-manager__email").text() == nasty


def test_the_french_card_uses_the_french_catalogue():
    prefs.set_request_prefs(lang="fr")
    tree = _tree(_view(is_admin_viewer=True, candidates=("a@example.test",)))
    text = tree.text()
    for expected in (
            "Co-gestionnaires", "Propriétaire", "Enlever", "Personne invitée",
            "Choisir une personne", "Ajouter un co-gestionnaire"):
        assert expected in text
    assert "Co-managers" not in text and "Remove" not in text
    leave = _tree(_read_only())
    assert "Quitter ce cadre" in leave.text()
    assert "Rester sur ce cadre" in leave.text()
    assert "Vous" in leave.text()


def test_form_actions_use_the_frame_prefix_on_a_prefixed_request(tmp_path):
    device = device_scope.Device(
        "d_0a1b2c3d", "Kitchen", "legacy", ".", str(tmp_path), False, 1)
    device_scope.set_request_scope(device, (device,))
    prefs.set_request_principal("user", "user")
    owner = _tree(_view())
    prefix = "/devices/d_0a1b2c3d"
    actions = {f.attrs["action"] for f in owner.select("form")}
    assert actions == {prefix + card.REMOVE_ROUTE, prefix + card.ADD_ROUTE}
    member = _tree(_read_only())
    assert member.select_one("form").attrs["action"] == prefix + card.LEAVE_ROUTE
    assert member.select_one("a.text-link").attrs["href"] == prefix + "/"
    prefs.set_request_principal(None)


# --- stylesheet ------------------------------------------------------------


def test_the_card_rules_use_existing_tokens_only(tmp_path):
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
