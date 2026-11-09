"""The Special looks card of Personalisation over a real in-process server: the rules list, the
Remove confirm dialog (named dismiss that takes the initial focus, csrf, escaped values), the
compact empty state and the unchanged delete route, in English and French.
"""
import re

import pytest

from companion.settings import rules as rules_settings
from companion_app_server import http_request, login, with_csrf
from companion_markup import parse_html
from server.plane import colour_rules

DELETE_PATH = "/settings/rules/%s/%s/delete"


def _display(server, session, lang=None):
    headers = {"Accept-Language": lang} if lang else None
    status, _headers, body = http_request(
        server.base_url() + "/display/special-looks", cookie=session, extra_headers=headers)
    assert status == 200
    return body.decode("utf-8")


def _card(page):
    return parse_html(page).select_one("section#personalisation-special-looks")


@pytest.fixture
def served(make_app_server):
    server = make_app_server(fake_providers=True)
    return server, login(server)


def test_a_rule_row_offers_a_remove_dialog_whose_dismiss_is_named_and_focused(served):
    """Remove opens a per-rule dialog: destructive submit posting to the delete route with the
    page's token, and "Keep special look" as the dismiss control carrying the initial focus"""
    server, session = served
    colour_rules.add_rule(server.state_dir, "prefix", "TVF", "white")
    card = _card(_display(server, session))
    row = card.select_one("li.rule-row")
    trigger = row.select_one("a[data-modal-open]")
    dialog = row.select_one("dialog.modal")
    assert trigger.attrs["href"] == "#" + dialog.attrs["id"]
    assert dialog.select_one("h2").text() == "Remove this special look?"
    form = dialog.select_one("form")
    assert form.attrs["method"] == "post"
    assert form.attrs["action"] == DELETE_PATH % ("prefix", "TVF")
    assert form.select_one('input[name="csrf_token"]') is not None
    submit = form.select_one('button[type="submit"]')
    assert submit.text() == "Remove special look"
    assert "btn--danger" in submit.attrs["class"]
    dismiss = form.select_one("a.modal__dismiss")
    assert dismiss.text() == "Keep special look"
    assert "autofocus" in dismiss.attrs
    assert "autofocus" not in submit.attrs
    assert dismiss.attrs["href"].endswith("#personalisation-special-looks")


def test_the_dialog_is_french_in_french(served):
    server, session = served
    colour_rules.add_rule(server.state_dir, "callsign", "AFR1234", "white")
    row = _card(_display(server, session, lang="fr")).select_one("li.rule-row")
    dialog = row.select_one("dialog.modal")
    assert dialog.select_one("h2").text() == "Supprimer cette allure spéciale ?"
    assert dialog.select_one('button[type="submit"]').text() == "Supprimer l’allure spéciale"
    assert dialog.select_one("a.modal__dismiss").text() == "Garder l’allure spéciale"


def test_every_rule_gets_its_own_dialog_with_a_slug_id(served):
    server, session = served
    for kind, value in (("prefix", "TVF"), ("callsign", "AFR1234"), ("hex", "3944F2")):
        colour_rules.add_rule(server.state_dir, kind, value, "white")
    card = _card(_display(server, session))
    ids = [d.attrs["id"] for d in card.select("dialog.modal")]
    assert len(ids) == 3 and len(set(ids)) == 3
    assert all(re.fullmatch(r"remove-look-[a-z]+-[0-9a-f]{10}", i) for i in ids)
    actions = {d.select_one("form").attrs["action"] for d in card.select("dialog.modal")}
    assert actions == {DELETE_PATH % pair for pair in (
        ("prefix", "TVF"), ("callsign", "AFR1234"), ("hex", "3944F2"))}


def test_posting_the_dialog_removes_the_rule_and_a_post_without_a_token_does_not(served):
    server, session = served
    colour_rules.add_rule(server.state_dir, "prefix", "TVF", "white")
    url = server.base_url() + DELETE_PATH % ("prefix", "TVF")
    status, _headers, _body = http_request(url, method="POST", data={}, cookie=session)
    assert status in (400, 403)
    assert "TVF" in colour_rules.load_colour_rules(server.state_dir)["prefix"]
    status, headers, _body = http_request(
        url, method="POST", data=with_csrf(session), cookie=session)
    assert status == 303 and "flash=rule_deleted" in headers.get("Location", "")
    assert "TVF" not in colour_rules.load_colour_rules(server.state_dir)["prefix"]
    status, headers, _body = http_request(
        url, method="POST", data=with_csrf(session), cookie=session)
    assert status == 303 and "flash=" not in headers.get("Location", "")


def test_the_card_counts_the_rules_and_leads_with_the_new_special_look_action(served):
    server, session = served
    colour_rules.add_rule(server.state_dir, "prefix", "TVF", "white")
    colour_rules.add_rule(server.state_dir, "hex", "3944F2", "white")
    card = _card(_display(server, session))
    assert card.select(".personalisation-card__current") == []
    add = card.select_one("a.special-add__summary")
    assert add.text() == "New special look"
    assert add.attrs["href"].endswith("/display/special-looks/new")
    assert card.select_one(".special-looks > .section-caption").text() == (
        "A different look for one airline, flight or plane.")
    assert card.select(".empty-state") == []
    assert len(card.select("li.rule-row")) == 2


@pytest.mark.parametrize("lang,heading", [
    ("en", "No special looks yet."),
    ("fr", "Aucune allure spéciale."),
])
def test_without_rules_the_card_shows_the_compact_empty_state_and_the_add_action(
        served, lang, heading):
    server, session = served
    card = _card(_display(server, session, lang=lang))
    empty = card.select_one(".empty-state--compact")
    assert empty.select_one(".empty-state__heading").text() == heading
    assert empty.select(".empty-state__body") == []
    assert card.select("li.rule-row") == []
    assert card.select_one("a.special-add__summary") is not None
    assert card.select("form") == [] and card.select("details.special-add") == []


def test_a_hostile_stored_rule_is_not_rendered_but_a_normalised_one_is_escaped():
    """a stored kind or value the normaliser would not accept never reaches an id, a form action
    or the text; an accepted one appears only in its normalised form"""
    rows = [
        ("prefix", '<img src=x onerror=alert(1)>', "white", "2026-01-01T00:00:00+00:00"),
        ("prefix", "tvf", "white", "2026-01-01T00:00:00+00:00"),
        ("bogus", "TVF", "white", "2026-01-01T00:00:00+00:00"),
        ("prefix", "TVF", "white", "2026-01-01T00:00:00+00:00"),
    ]
    markup = rules_settings._rule_list_html(rows)
    assert "onerror" not in markup and "<img src=x" not in markup
    assert "bogus" not in markup
    assert markup.count("<li ") == 1
    assert 'action="/settings/rules/prefix/TVF/delete"' in markup


def _page(server, session, path, lang=None):
    headers = {"Accept-Language": lang} if lang else None
    status, _headers, body = http_request(
        server.base_url() + path, cookie=session, extra_headers=headers)
    assert status == 200
    return parse_html(body.decode("utf-8"))


def test_the_new_special_look_is_a_page_with_the_unchanged_fields_and_a_docked_bar(served):
    """the new look page posts the same fields to the same route, shows the picture and the
    options, and carries Cancel (a link back to the list) and Save in the docked bar"""
    server, session = served
    page = _page(server, session, "/display/special-looks/new")
    form = page.select_one("form#special-look-form")
    assert form.attrs["action"] == "/settings/rules/add" and form.attrs["method"] == "post"
    assert [r.attrs["value"] for r in form.select('input[name="rule_kind"]')] == [
        "callsign", "hex", "prefix"]
    assert form.select_one('input[name="rule_key"]') is not None
    assert form.select('input[name="rule_theme_id"]')
    assert form.select_one(".look-frame__image") is not None
    assert page.select("dialog[open]") == [] and page.select("details.special-add") == []
    bar = page.select_one(".dirty-bar")
    assert bar.select_one("a.dirty-bar__cancel").attrs["href"] == "/display/special-looks"
    assert bar.select_one("a.dirty-bar__cancel").text() == "Cancel"
    submit = bar.select_one('button[type="submit"]')
    assert submit.attrs["form"] == "special-look-form" and submit.text() == "Save"
    assert page.select_one("a.form-back").attrs["href"] == "/display/special-looks"
    current = page.select_one('nav.personalisation-nav a[aria-current="page"]')
    assert current.attrs["data-pers-view"] == "special-looks"


def test_editing_a_special_look_keeps_its_key_and_preselects_its_look(served):
    """the edit page names the rule's key as fixed fields, checks the rule's own look, and
    saves through the same add route (which replaces); an unknown rule shows the new look page"""
    server, session = served
    colour_rules.add_rule(server.state_dir, "prefix", "TVF", "green_light")
    list_page = _page(server, session, "/display/special-looks")
    edit = list_page.select_one("li.rule-row a.special-row__edit")
    assert edit.attrs["href"].endswith(
        "/display/special-looks/edit?rule_kind=prefix&rule_key=TVF")
    page = _page(server, session, "/display/special-looks/edit?rule_kind=prefix&rule_key=TVF")
    form = page.select_one("form#special-look-form")
    assert form.attrs["action"] == "/settings/rules/add"
    assert form.select_one('input[name="rule_kind"]').attrs["value"] == "prefix"
    assert form.select_one('input[name="rule_kind"]').attrs["type"] == "hidden"
    assert form.select_one('input[name="rule_key"]').attrs["value"] == "TVF"
    checked = [r for r in form.select('input[name="rule_theme_id"]') if "checked" in r.attrs]
    assert [r.attrs["value"] for r in checked] == ["green_light"]
    assert page.select_one(".form-page__name").text() == "Edit special look"
    assert page.select_one('.dirty-bar button[type="submit"]').text() == "Save"
    unknown = _page(server, session, "/display/special-looks/edit?rule_kind=prefix&rule_key=ZZZ")
    assert unknown.select_one(".form-page__name").text() == "New special look"
    hostile = _page(
        server, session, "/display/special-looks/edit?rule_kind=%3Cb%3E&rule_key=%3Cscript%3E")
    assert hostile.select_one(".form-page__name").text() == "New special look"


def test_the_edit_and_new_pages_are_french_in_french(served):
    server, session = served
    colour_rules.add_rule(server.state_dir, "prefix", "TVF", "green_light")
    new = _page(server, session, "/display/special-looks/new", lang="fr")
    assert new.select_one(".form-page__name").text() == "Nouvelle allure spéciale"
    assert new.select_one('.dirty-bar button[type="submit"]').text() == "Enregistrer"
    edit = _page(
        server, session, "/display/special-looks/edit?rule_kind=prefix&rule_key=TVF", lang="fr")
    assert edit.select_one(".form-page__name").text() == "Modifier l’allure spéciale"
