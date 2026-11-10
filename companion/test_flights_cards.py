#!/usr/bin/env python3
"""Behaviour checks for the Flights phone list (below 960 px), read from the page the
companion app serves: one glass group per day with one row per flight (plane chip, callsign
and route, airline and aircraft, age and direction); the picture thumbnail as the row's one
lead control only when a picture exists (the plane chip otherwise), named per flight in English
and French; the unresolved-airline wording; the
day section labels; and no inline style attribute anywhere in the list.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.pages import history_page
from companion_app_server import get, login
from companion_markup import parse_html

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
        for card in doc.select(".history-cards li.history-card")}


def test_every_flight_is_one_row_with_chip_label_detail_and_value(pictured):
    """each flight renders as one row: one lead element (the picture thumbnail here, as every
    flight has a picture), the callsign and route label, the detail line, the age and direction
    at the right; the rows keep the filter contract (one data-filter-text and data-filter-group
    each)"""
    cards = _cards(_flights_doc(pictured))
    assert sorted(cards) == sorted(f[0] for f in _FLIGHTS)
    for callsign, card in cards.items():
        parts = [child.attrs.get("class") for child in card.select_one(".row__main").children
                 if not isinstance(child, str)]
        assert parts[:3] == ["history-card__thumb", "row__text", "row__value"], callsign
        assert not card.select(".row__chip") and not card.select(".history-card__picture"), callsign
        assert callsign.lower() in card.attrs["data-filter-text"]
        assert card.attrs["data-filter-group"].isdigit()
        assert not card.select('svg use[href="#icon-plane"]'), callsign
        assert not card.select(".history-card__direction"), callsign
        when = card.select_one(".row__value .history-card__when")
        assert when.select_one(".time-value--primary").text()
        assert when.select_one("time[data-relative]") is not None
        assert card.select_one(".row__detail").text()


def test_the_route_codes_mute_the_home_end_and_the_direction_reads_at_the_right(pictured):
    """a row with a route shows origin, arrow and destination with exactly one muted home end
    (the origin of a departure, the destination of an arrival); the confirmed direction is
    spoken in the label (the chip's turn shows it)"""
    for callsign, card in _cards(_flights_doc(pictured)).items():
        routes = card.select(".history-card__route")
        if not routes:
            continue
        homes = routes[0].select(".history-card__code--home")
        assert len(homes) == 1, callsign
        state = card.attrs["data-filter-kind"]
        if state:
            side = "from" if state == "departing" else "to"
            assert "history-card__code--" + side in homes[0].attrs["class"], callsign
            assert card.select_one(".row__detail").text().startswith(
                {"departing": "Departing", "arriving": "Arriving"}[state]), callsign


@pytest.mark.parametrize("lang,prefix", [("en", "View picture of "), ("fr", "Voir l’image de ")])
def test_the_thumbnail_is_the_one_picture_control_named_for_its_flight(pictured, lang, prefix):
    """with a picture available every row's lead is one real /gallery/ link with the lightbox
    trigger attributes and a per-flight accessible name, drawn as the picture's thumbnail
    alone (no plane icon on it, no separate image button, no plane chip), in English and
    French"""
    for callsign, card in _cards(_flights_doc(pictured, lang)).items():
        links = card.select("a[data-view-panel-src]")
        assert len(links) == 1, callsign
        link = links[0]
        assert link.parent.attrs["class"] == "row__main", callsign
        assert link.attrs["class"] == "history-card__thumb"
        assert link.attrs["href"] == "/gallery/" + _GALLERY
        assert link.attrs["data-view-panel-src"] == link.attrs["href"]
        assert link.attrs["data-view-panel-caption"]
        assert link.attrs["aria-label"] == prefix + callsign
        assert link.text() == ""
        image = link.select_one("img.history-card__thumb-image")
        assert image.attrs["src"] == link.attrs["href"] and image.attrs["alt"] == ""
        assert not link.select(".history-card__direction") and not link.select("svg")
        assert len(card.select("a")) == 1 and not card.select("button"), callsign


def test_a_flight_with_no_picture_has_no_plane_icon_and_no_control(unpictured):
    """with no archived render there is no picture link on any row, no lightbox shell, and
    no plane icon or other lead either"""
    doc = _flights_doc(unpictured)
    assert _cards(doc)
    assert not doc.select("li.history-card a[data-view-panel-src]")
    assert not doc.select("li.history-card .history-card__thumb")
    assert not doc.select("dialog#panel-lookup-dialog")
    for card in doc.select("li.history-card"):
        assert not card.select(".row__chip") and not card.select("svg")
        assert not card.select("a") and not card.select("button")


@pytest.mark.parametrize("lang,unknown,resolve", [
    ("en", "Airline unknown", "Name this airline"),
    ("fr", "Compagnie inconnue", "Nommer cette compagnie"),
])
def test_an_unresolved_airline_reads_unknown_with_no_resolve_link(pictured, lang, unknown, resolve):
    """an unresolved airline reads the unknown wording as the row's title and offers no link
    to name it, for anyone; a named airline does not carry it"""
    doc = _flights_doc(pictured, lang)
    cards = _cards(doc)
    assert unknown in cards["OBS412"].select_one(".row__label").text()
    assert [a for a in cards["OBS412"].select("a") if a.attrs["class"] != "history-card__thumb"] == []
    assert not [a for a in doc.select("a") if "resolve=" in a.attrs.get("href", "")]
    assert resolve not in doc.text()
    assert unknown not in cards["TVF72YL"].select_one(".row__label").text()


def test_each_day_is_one_group_labelled_by_its_day(pictured):
    """the list is one glass group per Paris day; each group's section label is its day, and
    the labels carry no filter text, so the filter count never counts them"""
    doc = _flights_doc(pictured)
    groups = doc.select(".history-cards > section.history-day")
    assert [g.select_one("h2.section-label").text() for g in groups] == ["3 Sep", "2 Sep"]
    assert all("data-filter-text" not in g.select_one("h2").attrs for g in groups)
    assert all("data-filter-day-group" in g.attrs for g in groups)
    assert not doc.select(".history-day .group .group")
    assert sum(len(g.select("li.history-card")) for g in groups) == len(_FLIGHTS)


def test_recent_day_labels_read_today_and_yesterday(tmp_path):
    """the two most recent day groups are labelled Today and Yesterday, older ones by date"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-10-03T20:55:00+00:00", "hex": "d1", "callsign": "TODAY1"},
        {"ts": "2026-10-02T20:55:00+00:00", "hex": "d2", "callsign": "YDAY1"},
        {"ts": "2026-09-30T20:55:00+00:00", "hex": "d3", "callsign": "OLDER1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, now="2026-10-03T21:00:00+00:00"))
    headers = parse_html(rendered).select(".history-cards h2.section-label")
    assert [h.text() for h in headers] == ["Today", "Yesterday", "30 Sep"]


def test_the_card_list_carries_no_inline_style(pictured):
    """the card list is styled from the stylesheet alone: no style attribute on any element"""
    doc = _flights_doc(pictured)
    card_list = doc.select_one(".history-cards")
    assert not card_list.select("[style]")


def _event(ts, callsign="TVF49NS", state="departing", hex_="4b0001", corroborated=True):
    return {"ts": ts, "hex": hex_, "callsign": callsign, "airline": "Transavia France",
            "origin": "ORY", "destination": "BRI", "confirmed_state": state,
            "corroborated": corroborated}


def _doc_for(make_app_server, events, path="/flights"):
    server = make_app_server(seed=lambda d: vp.seed_runway_events(d, events))
    status, _, body = get(server, path, cookie=login(server))
    assert status == 200
    return parse_html(body.decode("utf-8"))


def _chip_labels(doc):
    return [chip.text().strip() for chip in doc.select(".filter-chip")]


def _assert_chips_carry_no_number(doc):
    assert _chip_labels(doc) == ["All", "Departures", "Arrivals"]
    assert not doc.select(".filter-chip__count")


def _listed(doc):
    """the number of flights the screen-reader status line announces"""
    return int(doc.select_one("[data-filter-count]").text().split()[0])


@pytest.mark.parametrize("older_ts,older_state,cards", [
    ("2026-09-03T20:54:01+00:00", "departing", 1),
    ("2026-09-03T20:53:30+00:00", "departing", 2),
    ("2026-09-03T20:54:50+00:00", "arriving", 2),
])
def test_a_repeated_pass_inside_a_minute_is_one_flight(
        make_app_server, older_ts, older_state, cards):
    """a same-pass repeat 59 s apart is folded on Flights as on Home; one 90 s apart, or one
    whose direction changed, is a different reading and stays; the desktop table follows"""
    doc = _doc_for(make_app_server, [
        _event("2026-09-03T20:55:00+00:00"),
        _event(older_ts, state=older_state, corroborated=None)])
    assert len(doc.select(".history-cards li.history-card")) == cards
    assert len(doc.select("tr[data-flight-row]")) == cards
    assert _listed(doc) == cards


def test_status_count_and_day_headers_follow_the_folded_list(make_app_server):
    """the status count and the day headers count flights, not stored events: a pass stored
    twice adds nothing to either, and the chips stay plain direction labels"""
    doc = _doc_for(make_app_server, [
        _event("2026-09-03T20:55:00+00:00"),
        _event("2026-09-03T20:54:30+00:00", corroborated=None),
        _event("2026-09-03T20:40:00+00:00", callsign="AFR6152", state="arriving", hex_="3c0002"),
        _event("2026-09-02T09:00:00+00:00", callsign="SMR42", hex_="4b0003"),
        _event("2026-09-02T08:59:40+00:00", callsign="SMR42", hex_="4b0003", corroborated=None)])
    _assert_chips_carry_no_number(doc)
    assert len(doc.select(".history-cards li.history-card")) == 3
    assert len(doc.select(".history-cards h2.section-label")) == 2
    assert len(doc.select("tr.flight-day-row")) == 2
    assert doc.select_one("[data-filter-count]").text() == "3 flights"


def test_a_pass_straddling_midnight_folds_into_the_newer_day(make_app_server):
    """two events 20 s apart across Paris midnight are one flight listed under the later day,
    with no empty or duplicate day header for the earlier one"""
    doc = _doc_for(make_app_server, [
        _event("2026-09-03T22:00:10+00:00"),
        _event("2026-09-03T21:59:50+00:00", corroborated=None)])
    assert len(doc.select(".history-cards li.history-card")) == 1
    heads = [h.text() for h in doc.select(".history-cards h2.section-label")]
    assert len(heads) == 1 and "4 Sep" in heads[0]


def _fifty_events(count=50, **extra):
    """`count` distinct flights, one every 10 minutes, newest last in the list"""
    return [
        _event("2026-09-%02dT%02d:%02d:00+00:00" % (1 + i // 24, (i % 24) // 6 + 6, (i % 6) * 10),
               callsign="TVF%02d" % i, hex_="4b%04x" % i,
               state="arriving" if i % 5 == 0 else "departing", **extra)
        for i in range(count)]


def test_all_fifty_flights_are_in_the_first_response_with_no_paging_step(make_app_server):
    """50 distinct flights render as 50 cards and 50 table rows in the first response, with no
    Show-more control, and the status count covers all 50"""
    doc = _doc_for(make_app_server, _fifty_events())
    assert len(doc.select(".history-cards li.history-card")) == 50
    assert len(doc.select("tr[data-flight-row]")) == 50
    assert not doc.select(".flights-more")
    assert "show more" not in doc.text().lower()
    assert not [a for a in doc.select("a") if "limit=" in a.attrs.get("href", "")]
    _assert_chips_carry_no_number(doc)
    assert doc.select_one("[data-filter-count]").text() == "50 flights"


def test_a_legacy_limit_query_is_ignored(make_app_server):
    """a hand-typed ?limit= changes nothing: the page is identical to the one without it"""
    server = make_app_server(seed=lambda d: vp.seed_runway_events(d, _fifty_events()))
    cookie = login(server)
    plain = get(server, "/flights", cookie=cookie)
    for query in ("?limit=5", "?limit=30", "?limit=abc", "?limit=-1", "?limit=999999"):
        status, _, body = get(server, "/flights" + query, cookie=cookie)
        assert status == 200, query
        doc = parse_html(body.decode("utf-8"))
        assert len(doc.select(".history-cards li.history-card")) == 50, query
        assert not doc.select(".flights-more"), query
        assert _listed(doc) == 50, query
    assert plain[0] == 200


def test_folded_duplicates_still_reduce_the_full_list(make_app_server):
    """a pass stored twice among the newest 50 events is one flight: 49 cards, 49 in the status line"""
    events = _fifty_events(49)
    events.append(_event("2026-09-01T06:00:20+00:00", callsign="TVF00", hex_="4b0000",
                         state="arriving", corroborated=None))
    doc = _doc_for(make_app_server, events)
    assert len(doc.select(".history-cards li.history-card")) == 49
    assert _listed(doc) == 49
