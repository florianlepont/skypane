#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Browser checks for Home's recent-flights strip: no horizontal overflow at 390 and 360 px in
both themes and both languages, a 44 px heading row with a 44 px "See all flights" link, portrait
tiles of 112 px with a 3:4 picture box that shows the whole picture (contain), captions that stay
inside their tile and keep their direction word whole on one line, the tiles working with
scripts blocked, the same tiles at 1280 px, and the strip's section being one of the regions the
background refresh swaps (which keeps the ages current). Also checks that Display, like the other
pages, shows no visible freshness line while keeping its hidden refresh marker.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

TILE = "figure.home-strip__tile"
SECTION = 'section[aria-labelledby="home-flights"]'


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """A read-only server seeded with every flight variant and one repeated pass."""
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
    "() => [...document.querySelectorAll('figure.home-strip__tile')].map(t => {"
    "  const f = t.querySelector('.home-strip__frame').getBoundingClientRect();"
    "  const c = t.querySelector('figcaption').getBoundingClientRect();"
    "  const span = t.querySelector('figcaption span');"
    "  const img = t.querySelector('.home-strip__frame img');"
    "  const range = document.createRange(); range.selectNodeContents(span);"
    "  const lines = new Set([...range.getClientRects()].map(r => Math.round(r.top))).size;"
    "  return {frame: [Math.round(f.width), Math.round(f.height)],"
    "          captionInside: c.width <= f.width + 0.5, lines,"
    "          fit: img ? getComputedStyle(img).objectFit : 'none'};"
    "})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_tiles_fit_the_phone_in_both_themes(new_context, server, viewport, lang):
    """At 390 and 360 px, in English and French, light and dark: the page never scrolls sideways,
    five tiles show, each 112 px wide with a 3:4 picture box, a caption inside its tile whose
    direction and age stay on one line, and the picture shown whole (contain)"""
    context, page = _open_home(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            where = "Home strip (%s, %s)" % (lang, theme["theme"])
            failure = _assert_no_page_overflow(page, where, expected_width=viewport["width"])
            if failure:
                raise AssertionError(failure)
            tiles = page.evaluate(_TILE_PROBE)
            assert len(tiles) == 5, "%s: expected 5 tiles, got %d" % (where, len(tiles))
            for tile in tiles:
                assert tile["frame"] == [112, 149], (where, tile)
                assert tile["captionInside"] and tile["lines"] == 1, (where, tile)
                assert tile["fit"] in ("contain", "none"), (where, tile)
    finally:
        context.close()


def test_the_heading_row_and_its_link_are_44px(new_context, server):
    """the heading row is 44 px high with the label at the left and the "See all flights" link, a
    44 px target, at the right; the link leads to Flights"""
    context, page = _open_home(new_context, server, VIEWPORT_PHONE)
    try:
        seen = page.evaluate(
            "() => { const h = document.querySelector('.home-strip__head').getBoundingClientRect();"
            "  const l = document.querySelector('.home-strip__more').getBoundingClientRect();"
            "  const t = document.querySelector('.home-strip__label').getBoundingClientRect();"
            "  return {row: h.height, link: [l.width, l.height], labelRight: t.right, linkLeft: l.left}; }")
        assert seen["row"] >= 44 and seen["link"][1] >= 44 and seen["link"][0] >= 44, seen
        assert seen["labelRight"] <= seen["linkLeft"], seen
        assert page.locator(".home-strip__more").get_attribute("href") == "/flights"
    finally:
        context.close()


def test_tiles_render_with_scripts_blocked(new_context, server):
    """The tiles are server-rendered: with scripts blocked a phone still gets five tiles with
    their captions; only the heading's link goes to Flights."""
    with _no_js_page(new_context, server.base_url(), "/", viewport=VIEWPORT_PHONE) as page:
        assert page.locator(TILE).count() == 5
        assert page.locator("%s figcaption span" % TILE).first.is_visible()
        assert page.locator("%s a" % SECTION).count() == 1


def test_desktop_shows_the_same_tiles(new_context, server):
    """At 1280 px the strip renders the same five tiles in one row with the heading link above"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.locator(TILE).first.wait_for(state="visible")
        seen = page.evaluate(
            "() => ({tiles: [...document.querySelectorAll('figure.home-strip__tile')].map("
            "  t => Math.round(t.getBoundingClientRect().top)),"
            "  head: document.querySelector('.home-strip__head').getBoundingClientRect().bottom,"
            "  first: document.querySelector('figure.home-strip__tile').getBoundingClientRect().top})")
        assert len(seen["tiles"]) == 5 and len(set(seen["tiles"])) == 1, seen
        assert seen["head"] <= seen["first"] + 1, seen
    finally:
        context.close()


_CARD_WIDTHS = (
    "() => { const box = (s) => document.querySelector(s).getBoundingClientRect();"
    " const card = box('.home-flight'), pic = box('.home-flight__picture'),"
    " meta = box('.home-flight__meta'), column = box('.home-state');"
    " return {card: card.width, column: column.width, left: card.left, columnLeft: column.left,"
    " picRight: pic.right, metaLeft: meta.left, metaRight: meta.right, cardRight: card.right}; }")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [1280, 1440, 1920])
def test_the_flight_card_hugs_its_content_on_a_wide_screen(new_context, server, width, lang):
    """on a desktop the flight card is a capped block (the picture and its flight side by side)
    at the column's left edge, not a band spanning the whole column"""
    context, page = _open_home(new_context, server, {"width": width, "height": 900}, lang)
    try:
        seen = page.evaluate(_CARD_WIDTHS)
        assert seen["card"] <= 36 * 16 + 1, seen
        assert seen["card"] < seen["column"] - 100, seen
        assert abs(seen["left"] - seen["columnLeft"]) < 1.5, seen
        assert seen["picRight"] <= seen["metaLeft"] and seen["metaRight"] <= seen["cardRight"], seen
    finally:
        context.close()


@pytest.mark.parametrize("width", [360, 390])
def test_the_flight_card_still_spans_the_column_on_a_phone(new_context, server, width):
    context, page = _open_home(new_context, server, {"width": width, "height": 780})
    try:
        seen = page.evaluate(_CARD_WIDTHS)
        assert abs(seen["card"] - seen["column"]) < 1.5, seen
    finally:
        context.close()


def test_the_strip_section_is_a_region_the_refresh_swaps(new_context, server):
    """the strip's section matches a selector in the page's refresh registry, so its ages are
    repainted from the server's clock about every 45 s instead of staying as first rendered"""
    context, page = _open_home(new_context, server, VIEWPORT_PHONE)
    try:
        from companion import layout
        matched = [
            selector for selector in layout.REFRESH_SWAP_SELECTORS_BY_PAGE["home"]
            if page.locator(selector).count() == 1 and page.locator(SECTION).evaluate(
                "(el, sel) => el.matches(sel)", selector)]
        assert matched == [SECTION], matched
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


