#!/usr/bin/env python3
"""Behaviour checks for Home's recent-flights group, read from the page the companion app
serves: one row per flight (callsign, a detail line with the clock, airline, route and direction,
the live relative age) linking to the Flights page, then a "See all flights" row; the unresolved
airline, arrival, departure and no-route variants in English and French; no inline style
attribute; and a pass stored twice within a minute shown once.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion_app_server import get, login
from companion_markup import parse_html

_SECTION = 'section[aria-labelledby="home-flights"]'
_FLIGHTS = vp.FLIGHT_CARD_FLIGHTS


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_home_tile_variety)


def _home_section(server, lang="en"):
    cookie = login(server)
    if lang != "en":
        cookie += "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    status, _, body = get(server, "/", cookie=cookie)
    assert status == 200
    section = parse_html(body.decode("utf-8")).select_one(_SECTION)
    assert section is not None
    return section


def _rows(section):
    return {
        row.select_one(".row__label").text(): row
        for row in section.select("ul.group > li.recent-flight")}


def test_every_recent_flight_is_one_row_linking_to_flights(server):
    """each of the five newest distinct flights is one row of the group, newest first: a plane
    chip, the callsign in the identifier voice, a detail line and the relative age; the whole row
    is a link to the Flights page, and the "See all flights" row closes the group"""
    section = _home_section(server)
    rows = section.select("ul.group > li.recent-flight")
    assert [r.select_one(".row__label").text() for r in rows] == [f[0] for f in _FLIGHTS]
    for row in rows:
        assert row.attrs["class"].split() == ["row", "row--action", "recent-flight"]
        link = row.select_one("a.row__main")
        assert link is not None and link.attrs["href"] == "/flights"
        assert "mono" in row.select_one(".row__label .mono").attrs["class"].split()
        assert row.select_one(".row__chip") is not None
        assert row.select_one(".row__detail").text()
        assert row.select_one(".row__value time[data-relative]") is not None
    last = section.select("ul.group > li")[-1]
    assert "recent-flight-all" in last.attrs["class"].split()
    assert last.select_one("a.row__main").attrs["href"] == "/flights"
    assert last.select_one(".row__label").text() == "See all flights"
    assert section.select("[style]") == []


@pytest.mark.parametrize("lang,unknown,arriving,departing,no_route", [
    ("en", "Airline unknown", "Arriving", "Departing", "→"),
    ("fr", "Compagnie inconnue", "À l’arrivée", "Au départ", "→"),
])
def test_row_variants_in_both_languages(server, lang, unknown, arriving, departing, no_route):
    """the detail line joins the clock, the airline, the route and the direction word of the
    language; a flight with no route shows no route text; the long operator name stays whole"""
    rows = _rows(_home_section(server, lang))
    assert "Transavia France" in rows["TVF72YL"].select_one(".row__detail").text()
    assert departing in rows["TVF72YL"].select_one(".row__detail").text()
    assert arriving in rows["AFR6152"].select_one(".row__detail").text()
    assert "Some Very Long Charter Operator Name Limited" in (
        rows["XYZ9"].select_one(".row__detail").text())
    assert no_route not in rows["XYZ9"].select_one(".row__detail").text()
    assert no_route in rows["TVF72YL"].select_one(".row__detail").text()


def test_a_pass_stored_twice_within_a_minute_shows_once(server):
    """the seeded duplicate (same hex, callsign, route and direction, 30 s apart) is folded
    into one row, and the list still shows five distinct flights"""
    section = _home_section(server)
    callsigns = [r.text() for r in section.select("li.recent-flight .row__label")]
    assert callsigns.count("TVF72YL") == 1
    assert len(callsigns) == 5


def _pair_seed(second_ts, second_state="departing"):
    def seed(state_dir):
        vp.seed_runway_events(state_dir, [
            {"ts": "2026-09-03T20:55:00+00:00", "hex": "4b0001", "callsign": "TVF49NS",
             "airline": "Transavia France", "origin": "ORY", "destination": "BRI",
             "confirmed_state": "departing", "corroborated": True},
            {"ts": second_ts, "hex": "4b0001", "callsign": "TVF49NS",
             "airline": "Transavia France", "origin": "ORY", "destination": "BRI",
             "confirmed_state": second_state, "corroborated": None},
        ])
    return seed


@pytest.mark.parametrize("second_ts,second_state,expected", [
    ("2026-09-03T20:54:01+00:00", "departing", 1),
    ("2026-09-03T20:53:30+00:00", "departing", 2),
    ("2026-09-03T20:54:50+00:00", "arriving", 2),
])
def test_only_a_same_pass_repeat_inside_a_minute_is_folded(
        make_app_server, second_ts, second_state, expected):
    """a repeat 59 s later is folded; one 90 s apart, or one that changed direction, is a
    different reading and stays"""
    server = make_app_server(seed=_pair_seed(second_ts, second_state))
    section = _home_section(server)
    assert len(section.select("li.recent-flight")) == expected


def _overhead_seed(state_dir):
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-03T20:55:00+00:00", "hex": "4b0001", "callsign": "AFR1234",
         "airline": "Air France", "origin": None, "destination": None,
         "confirmed_state": "overhead"},
        {"ts": "2026-09-03T20:40:00+00:00", "hex": "4b0002", "callsign": "TVF49NS",
         "airline": "Transavia France", "origin": "ORY", "destination": "BRI",
         "confirmed_state": "departing"},
    ])


@pytest.mark.parametrize("lang,label", [("en", "Overhead"), ("fr", "Au-dessus")])
def test_an_overhead_row_is_labelled_on_home(make_app_server, lang, label):
    """a flight stored as overhead reads Overhead (Au-dessus) in its row"""
    server = make_app_server(seed=_overhead_seed)
    section = _home_section(server, lang)
    row = _rows(section)["AFR1234"]
    assert label in row.select_one(".row__detail").text()
    assert "None" not in row.text()


def test_an_overhead_row_is_in_all_but_in_no_direction_chip(tmp_path):
    """the Flights page names the overhead row and counts it under All only"""
    from companion.pages import history_page
    _overhead_seed(tmp_path)
    rendered = history_page.render(vp.history_ctx(tmp_path, now="2026-09-03T21:00:00+00:00"))
    doc = parse_html(rendered)
    assert "Overhead" in rendered
    assert doc.select('[data-filter-kind="overhead"]') == []
    kinds = {node.attrs["data-filter-kind"] for node in doc.select("[data-filter-kind]")}
    assert kinds == {"", "departing"}
