#!/usr/bin/env python3
"""Behaviour checks for the Flights phone card (the boarding-pass layout below 960 px),
read from the page the companion app serves: one card per flight with its head, route line
and stub; the icon-only picture link only when a picture exists, named per flight in English
and French; the unresolved-airline variant; the no-artwork placeholder; the slim day headers;
and no inline style attribute anywhere in the card list.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.pages import history_page
from companion_app_server import get, login
from companion_markup import parse_html
from server.plane import illustrations

_GALLERY = vp.FLIGHT_CARD_GALLERY_NAME
_FLIGHTS = vp.FLIGHT_CARD_FLIGHTS


def _seed(state_dir, with_gallery):
    vp.seed_flight_card_variety(state_dir, with_gallery)


@pytest.fixture(scope="module")
def pictured(module_app_server_factory):
    return module_app_server_factory(seed=lambda d: _seed(d, True))


@pytest.fixture(scope="module")
def unpictured(module_app_server_factory):
    return module_app_server_factory(seed=lambda d: _seed(d, False))


def _flights_doc(server, lang="en"):
    cookie = login(server)
    if lang != "en":
        cookie += "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    status, _, body = get(server, "/flights", cookie=cookie)
    assert status == 200
    return parse_html(body.decode("utf-8"))


def _cards(doc):
    return {
        card.select_one(".history-card__callsign").text(): card
        for card in doc.select("ul.history-cards > li.history-card")}


def test_every_flight_is_one_card_with_head_route_and_stub(pictured):
    """each flight renders as one card whose bands are head, route and stub in that order, and
    the cards keep the filter contract (one data-filter-text and data-filter-group each)"""
    cards = _cards(_flights_doc(pictured))
    assert sorted(cards) == sorted(f[0] for f in _FLIGHTS)
    for callsign, card in cards.items():
        bands = [child.attrs.get("class") for child in card.children if not isinstance(child, str)]
        assert bands == ["history-card__head", "history-card__route", "history-card__stub"], callsign
        assert callsign.lower() in card.attrs["data-filter-text"]
        assert card.attrs["data-filter-group"].isdigit()
        when = card.select_one(".history-card__stub .history-card__when")
        assert when.select_one(".time-value--primary").text()
        assert when.select_one("time[data-relative]") is not None


@pytest.mark.parametrize("lang,prefix", [("en", "View picture of "), ("fr", "Voir l’image de ")])
def test_the_picture_action_is_an_icon_link_named_for_its_flight(pictured, lang, prefix):
    """with a picture available every card head carries one icon-only real /gallery/ link with
    the lightbox trigger attributes and a per-flight accessible name, in English and French"""
    for callsign, card in _cards(_flights_doc(pictured, lang)).items():
        links = card.select("a[data-view-panel-src]")
        assert len(links) == 1, callsign
        link = links[0]
        assert link.parent.attrs.get("class") == "history-card__head"
        assert link.attrs["href"] == "/gallery/" + _GALLERY
        assert link.attrs["data-view-panel-src"] == link.attrs["href"]
        assert link.attrs["data-view-panel-caption"]
        assert link.attrs["aria-label"] == prefix + callsign
        assert link.text() == ""
        assert link.select_one("svg").attrs["aria-hidden"] == "true"


def test_a_flight_with_no_picture_shows_no_action(unpictured):
    """with no archived render there is no picture link on any card, and no lightbox shell"""
    doc = _flights_doc(unpictured)
    assert _cards(doc)
    assert not doc.select("li.history-card a[data-view-panel-src]")
    assert not doc.select("li.history-card .history-card__picture")
    assert not doc.select("dialog#panel-lookup-dialog")


@pytest.mark.parametrize("lang,unknown,resolve", [
    ("en", "Airline unknown", "Name this airline"),
    ("fr", "Compagnie inconnue", "Nommer cette compagnie"),
])
def test_an_unresolved_airline_reads_unknown_with_its_resolve_link(pictured, lang, unknown, resolve):
    """an unresolved airline reads the italic unknown label with the one-hop resolve link under
    it in the card head; a named airline carries neither"""
    cards = _cards(_flights_doc(pictured, lang))
    identity = cards["OBS412"].select_one(".history-card__head .history-card__id")
    assert identity.select_one(".history-card__airline--unknown").text() == unknown
    link = identity.select_one(".history-card__resolve a")
    assert link.text() == resolve
    assert link.attrs["href"] == "/airlines?resolve=OBS"
    named = cards["TVF72YL"]
    assert not named.select(".history-card__airline--unknown")
    assert not named.select(".history-card__resolve")


@pytest.mark.parametrize("lang,placeholder", [("en", "No illustration"), ("fr", "Pas d’illustration")])
def test_artwork_shows_as_a_plate_or_a_quiet_placeholder(pictured, lang, placeholder):
    """an airline with an artwork file shows it as the stub's image plate; one without shows the
    dashed placeholder text and never an <img> that would 404"""
    cards = _cards(_flights_doc(pictured, lang))
    key = illustrations.normalise_airline_key("Transavia France")
    img = cards["TVF72YL"].select_one(".history-card__stub img.history-card__art")
    assert img.attrs["src"] == "/illustration/%s.png" % key
    for callsign in ("SMR42", "OBS412", "XYZ9"):
        stub = cards[callsign].select_one(".history-card__stub")
        assert not stub.select("img"), callsign
        assert stub.select_one(".history-card__art--empty").text() == placeholder


def test_day_headers_group_the_cards_without_joining_the_filter(pictured):
    """slim day headers split the list where the Paris day changes; they carry no filter text, so
    the filter count never counts them"""
    doc = _flights_doc(pictured)
    items = doc.select("ul.history-cards > li")
    headers = [item for item in items if item.attrs.get("class") == "history-cards__day"]
    assert [h.text() for h in headers] == ["3 Sep", "2 Sep"]
    assert all("data-filter-text" not in h.attrs for h in headers)
    order = [item.attrs.get("class") for item in items]
    assert order[0] == "history-cards__day"
    assert order.index("history-cards__day", 1) == 4


def test_recent_day_headers_read_today_and_yesterday_with_the_date(tmp_path):
    """the two most recent day headers name the day and add the short date after it"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-10-03T20:55:00+00:00", "hex": "d1", "callsign": "TODAY1"},
        {"ts": "2026-10-02T20:55:00+00:00", "hex": "d2", "callsign": "YDAY1"},
        {"ts": "2026-09-30T20:55:00+00:00", "hex": "d3", "callsign": "OLDER1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, now="2026-10-03T21:00:00+00:00"))
    headers = parse_html(rendered).select("ul.history-cards > li.history-cards__day")
    assert [h.text() for h in headers] == ["Today · 3 Oct", "Yesterday · 2 Oct", "30 Sep"]


def test_the_card_list_carries_no_inline_style(pictured):
    """the card list is styled from the stylesheet alone: no style attribute on any element"""
    doc = _flights_doc(pictured)
    card_list = doc.select_one("ul.history-cards")
    assert not card_list.select("[style]")
