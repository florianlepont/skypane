#!/usr/bin/env python3
"""Behaviour checks for Home's recent-flight tiles (the phone list below 960 px), read from
the page the companion app serves: one slim tile per flight with its identity, artwork plate,
route line and time; the unresolved-airline, no-artwork, arrival and no-route variants in
English and French; no action of any kind inside a tile; the desktop list kept beside it; no
inline style attribute; and a pass stored twice within a minute shown once.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion_app_server import get, login
from companion_markup import parse_html
from server.plane import illustrations

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


def _tiles(section):
    return {
        tile.select_one(".history-card__callsign").text(): tile
        for tile in section.select("ul.recent-flight-tiles > li.recent-tile")}


def test_every_recent_flight_is_one_tile_with_identity_art_route_and_time(server):
    """each of the five newest distinct flights renders as one tile whose parts are identity,
    artwork plate, route line and time in that order, newest first; the time is the clock over
    a live relative age"""
    section = _home_section(server)
    tiles = section.select("ul.recent-flight-tiles > li.recent-tile")
    assert [t.select_one(".history-card__callsign").text() for t in tiles] == [
        f[0] for f in _FLIGHTS]
    for tile in tiles:
        parts = [child.attrs.get("class", "").split()[0]
                 for child in tile.children if not isinstance(child, str)]
        assert parts == ["recent-tile__id", "history-card__art", "history-card__route",
                         "history-card__when"], parts
        callsign = tile.select_one(".recent-tile__id .history-card__callsign")
        assert "mono" in callsign.attrs["class"].split()
        assert tile.select_one(".recent-tile__id .history-card__airline").text()
        when = tile.select_one(".history-card__when")
        assert when.select_one(".time-value--primary").text()
        assert when.select_one("time[data-relative]") is not None


def test_the_tiles_render_before_the_unchanged_desktop_list(server):
    """the phone tiles and the desktop list are siblings in that order inside the section,
    the desktop list keeps one row per tile, and the See all flights link stays last"""
    section = _home_section(server)
    lists = [child for child in section.children
             if not isinstance(child, str) and child.tag == "ul"]
    assert [ul.attrs["class"] for ul in lists] == ["recent-flight-tiles", "recent-flights"]
    assert len(lists[1].select("li.recent-flight")) == len(lists[0].select("li.recent-tile"))
    links = section.select("a")
    assert len(links) == 1 and links[0].attrs["href"] == "/flights"


def test_a_tile_carries_no_action_and_no_inline_style(server):
    """Home's rows have never been links, so a tile holds no link, button or focusable
    control; nothing in the section carries a style attribute (strict CSP)"""
    section = _home_section(server)
    for tile in section.select("li.recent-tile"):
        for selector in ("a", "button", "[tabindex]", "[onclick]"):
            assert tile.select(selector) == [], selector
    assert section.select("[style]") == []


@pytest.mark.parametrize("lang,unknown,empty,arriving,departing,no_route", [
    ("en", "Airline unknown", "No illustration", "Arriving", "Departing", "Route unavailable"),
    ("fr", "Compagnie inconnue", "Pas d’illustration", "À l’arrivée", "Au départ",
     "Trajet indisponible"),
])
def test_tile_variants_in_both_languages(server, lang, unknown, empty, arriving, departing,
                                         no_route):
    """an airline with artwork gets its plate named after the airline; one with no artwork file
    and an unresolved one get the dashed placeholder; the unresolved airline reads "Airline
    unknown" in italics with no resolve link; an arrival mutes its home destination and a
    departure its home origin, each with its direction label; a flight with no route shows the
    route fallback; the long operator name stays whole in the markup"""
    tiles = _tiles(_home_section(server, lang))

    art = tiles["TVF72YL"].select_one("img.history-card__art")
    key = illustrations.normalise_airline_key("Transavia France")
    assert art.attrs["src"] == "/illustration/%s.png" % key
    assert "Transavia France" in art.attrs["alt"]
    for callsign in ("SMR42", "OBS412", "XYZ9"):
        plate = tiles[callsign].select_one(".history-card__art")
        assert plate.tag == "span" and "history-card__art--empty" in plate.attrs["class"]
        assert plate.text() == empty

    airline = tiles["OBS412"].select_one(".history-card__airline")
    assert "history-card__airline--unknown" in airline.attrs["class"].split()
    assert airline.text() == unknown

    arrival = tiles["AFR6152"]
    assert "history-card__code--home" in arrival.select_one(".history-card__code--to").attrs["class"]
    assert "history-card__code--home" not in arrival.select_one(
        ".history-card__code--from").attrs["class"]
    assert arrival.select_one(".history-card__dir").text() == arriving
    departure = tiles["TVF72YL"]
    assert "history-card__code--home" in departure.select_one(
        ".history-card__code--from").attrs["class"]
    assert departure.select_one(".history-card__dir").text() == departing

    long_name = tiles["XYZ9"]
    assert long_name.select_one(".history-card__airline").text() == (
        "Some Very Long Charter Operator Name Limited")
    assert long_name.select_one(".history-card__code--none").text() == no_route


def test_a_pass_stored_twice_within_a_minute_shows_once(server):
    """the seeded duplicate (same hex, callsign, route and direction, 30 s apart) is folded
    into one tile and one desktop row, and the list still shows five distinct flights"""
    section = _home_section(server)
    tile_callsigns = [t.text() for t in section.select("li.recent-tile .history-card__callsign")]
    row_callsigns = [r.text() for r in section.select("li.recent-flight .recent-flight__callsign")]
    for callsigns in (tile_callsigns, row_callsigns):
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
    assert len(section.select("li.recent-tile")) == expected
    assert len(section.select("li.recent-flight")) == expected
