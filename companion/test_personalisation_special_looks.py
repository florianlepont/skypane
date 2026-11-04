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
        server.base_url() + "/display", cookie=session, extra_headers=headers)
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
    assert "calendar-disconnect-btn" in submit.attrs["class"]
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
    assert dialog.select_one("h2").text() == "Supprimer ce look spécial ?"
    assert dialog.select_one('button[type="submit"]').text() == "Supprimer le look spécial"
    assert dialog.select_one("a.modal__dismiss").text() == "Garder le look spécial"


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
    assert card.select_one(".personalisation-card__current").text() == "Current: 2 special looks"
    assert card.select_one("summary.special-add__summary").text() == "New special look"
    assert card.select(".empty-state") == []
    assert len(card.select("li.rule-row")) == 2


@pytest.mark.parametrize("lang,heading,hint", [
    ("en", "No special looks yet",
     "Create one when a particular airline or plane should look different."),
    ("fr", "Aucun look spécial pour l’instant",
     "Créez-en un quand une compagnie ou un avion précis doit avoir un autre look."),
])
def test_without_rules_the_card_shows_the_compact_empty_state_and_the_add_action(
        served, lang, heading, hint):
    server, session = served
    card = _card(_display(server, session, lang=lang))
    empty = card.select_one(".empty-state--compact")
    assert empty.select_one(".empty-state__heading").text() == heading
    assert empty.select_one(".empty-state__body").text() == hint
    assert card.select("li.rule-row") == []
    assert card.select_one("details.special-add form.rule-add-form") is not None


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
