#!/usr/bin/env python3
"""Browser checks for Home's recent-flight tiles (the phone list below 960 px): no horizontal
overflow at 390 and 360 px in both themes and both languages, each tile two rows tall with its
content inside it, the airline ellipsised on one line, all five flights fitting in one 390x844
screen with the section heading at the top, the tiles working with scripts blocked, and the
desktop list unchanged at 1280 px. Also checks that Display, like the other pages, shows no
visible freshness line while keeping its hidden refresh marker.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

TILE = "li.recent-tile"
SECTION = 'section[aria-labelledby="home-flights"]'


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """A read-only server seeded with every tile variant and one repeated pass."""
    return module_app_server_factory(seed=vp.seed_home_tile_variety, fake_providers=True)


def _open_home(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/")
    page.locator(TILE).first.wait_for(state="visible")
    return context, page


_TILE_PROBE = (
    "() => [...document.querySelectorAll('li.recent-tile')].map(li => {"
    "  const c = li.getBoundingClientRect();"
    "  const inside = [...li.querySelectorAll('*')].every(el => {"
    "    const r = el.getBoundingClientRect();"
    "    return r.width === 0 || (r.left >= c.left - 0.5 && r.right <= c.right + 0.5"
    "      && r.top >= c.top - 0.5 && r.bottom <= c.bottom + 0.5);"
    "  });"
    "  const top = sel => li.querySelector(sel).getBoundingClientRect();"
    "  const id = top('.recent-tile__id'), art = top('.history-card__art'),"
    "        route = top('.history-card__route');"
    "  const airline = li.querySelector('.history-card__airline');"
    "  const codes = [...li.querySelectorAll('.history-card__code')]"
    "    .map(el => el.getBoundingClientRect().top);"
    "  return {callsign: li.querySelector('.history-card__callsign').textContent,"
    "          inside, height: c.height,"
    "          twoRows: id.bottom <= art.top + 0.5 && Math.abs(art.top - route.top) < 8,"
    "          airlineOneLine: airline.getBoundingClientRect().height < 24,"
    "          airlineClipped: airline.scrollWidth > airline.clientWidth,"
    "          codesOneRow: codes.every(t => Math.abs(t - codes[0]) < 1)};"
    "})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_tiles_fit_the_phone_in_both_themes(new_context, server, viewport, lang):
    """At 390 and 360 px, in English and French, light and dark: the page never scrolls
    sideways, every tile keeps its content inside its own box on two rows (identity, then the
    plate beside the route) no taller than 80 px, the route codes sit on one row, and the
    long operator name is cut with an ellipsis on one line rather than wrapping."""
    context, page = _open_home(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            where = "Home tiles (%s, %s)" % (lang, theme["theme"])
            failure = _assert_no_page_overflow(page, where, expected_width=viewport["width"])
            if failure:
                raise AssertionError(failure)
            tiles = page.evaluate(_TILE_PROBE)
            assert len(tiles) == 5, "%s: expected 5 tiles, got %d" % (where, len(tiles))
            for tile in tiles:
                ok = (tile["inside"] and tile["twoRows"] and tile["codesOneRow"]
                      and tile["airlineOneLine"] and tile["height"] <= 80)
                if not ok:
                    raise AssertionError("%s: tile %r is broken: %r" % (where, tile["callsign"], tile))
            long_name = [t for t in tiles if t["callsign"] == "XYZ9"][0]
            if not long_name["airlineClipped"]:
                raise AssertionError("%s: expected the long airline to be ellipsised" % where)
    finally:
        context.close()


def test_five_flights_fit_one_phone_screen(new_context, server):
    """With the Recent flights heading scrolled to the top of a 390x844 screen, all five tiles
    sit fully above the tab bar."""
    context, page = _open_home(new_context, server, VIEWPORT_PHONE)
    try:
        seen = page.evaluate(
            "() => {"
            "  const s = document.querySelector('%s');"
            "  const top = s.getBoundingClientRect().top;"
            "  const tab = [...document.querySelectorAll('.tab-bar')]"
            "    .find(t => getComputedStyle(t).display !== 'none');"
            "  const floor = tab ? tab.getBoundingClientRect().top : innerHeight;"
            "  const tiles = [...s.querySelectorAll('li.recent-tile')]"
            "    .map(li => li.getBoundingClientRect().bottom - top);"
            "  return {fit: tiles.filter(b => b <= floor).length, floor, tiles};"
            "}" % SECTION)
        if seen["fit"] < 5:
            raise AssertionError("expected 5 tiles in one 390x844 screen, got %r" % (seen,))
    finally:
        context.close()


def test_tiles_render_with_scripts_blocked(new_context, server):
    """The tiles are server-rendered: with scripts blocked a phone still gets five tiles with
    their times and no desktop list."""
    with _no_js_page(new_context, server.base_url(), "/", viewport=VIEWPORT_PHONE) as page:
        assert page.locator(TILE).count() == 5
        assert page.locator("%s .time-value--primary" % TILE).first.is_visible()
        assert not page.locator("li.recent-flight").first.is_visible()


def test_desktop_keeps_the_thumbnail_list(new_context, server):
    """At 1280 px the tiles are hidden and the desktop list renders as before: five
    thumbnail rows, each with its 40px square thumbnail, callsign, detail line and time."""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.locator("li.recent-flight").first.wait_for(state="visible")
        seen = page.evaluate(
            "() => ({"
            "  tiles: getComputedStyle(document.querySelector('ul.recent-flight-tiles')).display,"
            "  rows: [...document.querySelectorAll('li.recent-flight')].map(li => {"
            "    const thumb = li.querySelector('.recent-flight__thumb').getBoundingClientRect();"
            "    return {display: getComputedStyle(li).display,"
            "            thumb: [Math.round(thumb.width), Math.round(thumb.height)],"
            "            parts: ['.recent-flight__callsign', '.recent-flight__detail',"
            "                    '.recent-flight__time'].every(s => li.querySelector(s))};"
            "  })"
            "})")
        assert seen["tiles"] == "none", seen
        assert len(seen["rows"]) == 5, seen
        for row in seen["rows"]:
            assert row == {"display": "flex", "thumb": [40, 40], "parts": True}, row
    finally:
        context.close()


@pytest.mark.parametrize("lang,visible_word", [("en", "Updated"), ("fr", "Mis à jour")])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_display_shows_no_freshness_line_but_keeps_the_refresh_marker(
        new_context, server, viewport, lang, visible_word):
    """Display's header reads only its title: no "Updated" line and no live dot are painted,
    while the hidden refresh pill with its data-loaded-at instant is still in the header."""
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.locator(".page-header h1").wait_for(state="visible")
        header_text = page.locator(".page-header").inner_text()
        assert visible_word not in header_text, header_text
        assert page.locator("[data-refresh-live-dot], [data-refresh-clock]").count() == 0
        marker = page.locator(".page-header .page-header__freshness--silent [data-loaded-at]")
        assert marker.count() == 1
        assert marker.get_attribute("data-loaded-at")
        assert not marker.is_visible()
    finally:
        context.close()
