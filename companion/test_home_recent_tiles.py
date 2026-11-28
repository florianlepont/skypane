#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Behaviour checks for Home's recent-flights strip, read from the page the companion app
serves: one tile per flight (picture box, callsign, direction and age) and a "See all flights"
link in the heading; the arrival, departure and overhead wording in English and French; no
inline style attribute; and a pass stored twice within a minute shown once. The strip's
section is also one of the regions the background refresh swaps, which is what keeps the ages
current.
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


def _tiles(section):
    return {
        tile.select_one("figcaption").text().split(" ")[0]: tile
        for tile in section.select("figure.home-strip__tile")}


def test_every_recent_flight_is_one_tile(server):
    """each of the five newest distinct flights is one portrait tile of the strip, newest first:
    its picture box, then the callsign with the direction and age under it; the strip's one
    link is the "See all flights" link of its heading"""
    section = _home_section(server)
    tiles = section.select("figure.home-strip__tile")
    assert [t.select_one("figcaption").text().split(" ")[0] for t in tiles] == [
        f[0] for f in _FLIGHTS]
    for tile in tiles:
        assert tile.select_one(".home-strip__frame") is not None
        assert tile.select("a") == [] and tile.select("button") == []
        assert tile.select_one("figcaption span").text()
    links = section.select("a")
    assert [a.attrs["href"] for a in links] == ["/flights"]
    assert links[0].text() == "See all flights"
    assert section.select("[style]") == []


@pytest.mark.parametrize("lang,arriving,departing", [
    ("en", "Arrival", "Departure"), ("fr", "Arrivée", "Décollage")])
def test_tile_captions_in_both_languages(server, lang, arriving, departing):
    """the caption's second line joins the direction word of the language and the age; a flight
    with no airline or route still reads as a tile with its callsign"""
    tiles = _tiles(_home_section(server, lang))
    assert tiles["TVF72YL"].select_one("figcaption span").text().startswith(departing + " ·")
    assert tiles["AFR6152"].select_one("figcaption span").text().startswith(arriving + " ·")
    assert "XYZ9" in tiles


def test_a_pass_stored_twice_within_a_minute_shows_once(server):
    """the seeded duplicate (same hex, callsign, route and direction, 30 s apart) is folded
    into one tile, and the strip still shows five distinct flights"""
    section = _home_section(server)
    callsigns = [t.select_one("figcaption").text().split(" ")[0]
                 for t in section.select("figure.home-strip__tile")]
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
    assert len(section.select("figure.home-strip__tile")) == expected


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
    tile = _tiles(section)["AFR1234"]
    assert label in tile.select_one("figcaption span").text()
    assert "None" not in tile.text()


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


# --- The preview-strip builder (companion/pages/home_recent_strip.py) ------

from companion import prefs  # noqa: E402
from companion.pages import history_page, home_recent_strip  # noqa: E402
from companion_markup import parse_html as _parse  # noqa: E402

_NOW = "2026-09-03T21:07:00+00:00"
_FLIGHT_TS = "2026-09-03T20:55:00+00:00"


def _strip(rows, state_dir, entries=(), lang="en"):
    prefs.set_request_prefs(lang=lang)
    try:
        return _parse(home_recent_strip.recent_strip_html(rows, _NOW, str(state_dir), entries))
    finally:
        prefs.set_request_prefs()


def _row(**fields):
    base = {"ts": _FLIGHT_TS, "callsign": "AFR1234", "airline": "Totally Unknown Air",
            "confirmed_state": "arriving", "gallery_name": None}
    base.update(fields)
    return base


def _name_at(offset_s):
    """The gallery file name stamped `offset_s` after the flight's timestamp."""
    from datetime import datetime, timedelta, timezone
    stamp = datetime.fromisoformat(_FLIGHT_TS).astimezone(timezone(timedelta(hours=2)))
    stamp += timedelta(seconds=offset_s)
    return stamp.strftime("%Y-%m-%dT%H-%M-%S+02-00.png")


def test_strip_tile_shows_the_render_inside_the_flights_match_window(tmp_path):
    """a flight with no stored render name shows the archived render stamped no more than the
    Flights window before and after it, and no other; the caption reads direction and age"""
    before = history_page.GALLERY_MATCH_BEFORE_S
    after = history_page.GALLERY_MATCH_AFTER_S
    for offset, shown in ((-before, True), (-before - 1, False), (after, True), (after + 1, False)):
        doc = _strip([_row()], tmp_path, [_name_at(offset)])
        assert bool(doc.select(".home-strip__frame--render img")) is shown, offset
    tile = _strip([_row()], tmp_path, [_name_at(-5)]).select_one("figure.home-strip__tile")
    assert tile.select_one("figcaption").text() == "AFR1234 Arrival · 12 min"
    assert tile.select_one("img").attrs["alt"] == ""


def test_strip_tile_with_a_stored_render_name_ignores_the_time_window(tmp_path):
    """a row that stores its render shows exactly that one while the gallery still holds it,
    and falls back once the gallery pruned it, whatever else is archived nearby"""
    stored = _name_at(-300)
    row = _row(gallery_name=stored)
    assert _strip([row], tmp_path, [stored, _name_at(-5)]).select_one(
        "img").attrs["src"] == "/gallery/" + stored
    assert _strip([row], tmp_path, [_name_at(-5)]).select(".home-strip__frame--render img") == []


def test_strip_tile_falls_back_to_the_airline_illustration_then_the_plane_chip(tmp_path):
    """no matching render: the airline's own illustration when it has one, else a plane chip;
    neither is an image of the flight and the chip is hidden from assistive technology"""
    with_art = _strip([_row(airline="Air France")], tmp_path).select_one("figure")
    assert with_art.select_one(".home-strip__frame--illustration img").attrs["src"].startswith(
        "/illustration/air-france.png")
    chip = _strip([_row()], tmp_path).select_one("figure")
    assert chip.select("img") == []
    frame = chip.select_one(".home-strip__frame--none")
    assert frame.attrs["aria-hidden"] == "true" and frame.select("use")


def test_strip_has_the_heading_the_link_and_no_inline_style(tmp_path):
    doc = _strip([_row()], tmp_path)
    heading = doc.select_one("section[aria-labelledby='home-flights'] h2#home-flights")
    assert heading.text() == "Recent flights"
    assert doc.select_one("a.home-strip__more").attrs["href"] == "/flights"
    assert doc.select("[style]") == []


def test_strip_without_a_flight_is_the_empty_state(tmp_path):
    doc = _strip([], tmp_path)
    assert doc.select("figure") == []
    assert "No flights yet." in doc.text()


def test_strip_in_french(tmp_path):
    doc = _strip([_row(confirmed_state="departing")], tmp_path, lang="fr")
    assert doc.select_one("h2").text() == "Derniers vols"
    assert doc.select_one("figcaption").text() == "AFR1234 Décollage · 12 min"
    assert "Voir tous les vols" in doc.select_one("a.home-strip__more").text()


def test_strip_escapes_every_dynamic_part(tmp_path):
    """a hostile callsign, airline and gallery name reach the markup only as text"""
    hostile = '"><script>alert(1)</script>'
    row = _row(callsign=hostile, airline=hostile, gallery_name=hostile)
    html = home_recent_strip.recent_strip_html([row], _NOW, str(tmp_path), [hostile])
    assert "<script>" not in html and hostile not in html
    assert _parse(html).select("script") == []


def test_the_strip_is_a_region_the_background_refresh_swaps(server):
    """the strip's section matches one of the Home swap selectors the page's refresh script
    replaces every 45 s, so a tile's age is repainted from the server's clock and never stays stale"""
    from companion import layout
    selectors = layout.REFRESH_SWAP_SELECTORS_BY_PAGE["home"]
    assert 'section[aria-labelledby="home-flights"]' in selectors
    assert _home_section(server) is not None
