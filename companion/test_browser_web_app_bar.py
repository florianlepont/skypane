#!/usr/bin/env python3
"""Browser checks that the phone app bar starts lower in an iPhone Home Screen web app, and only
there. iOS 27 draws a frost over the top of a Home Screen web app's window, over the page, fading
out about 36px below the status bar; there the bar starts 24px lower, so the logo, the wordmark and
the frame button's name are clear of it, on every page, the Location page included (its floating
parts and its loading state move down with the bar). navigator.standalone tells the clients apart:
true in a Home Screen web app, false in a Safari tab, undefined in every other browser (Chromium as
it is). A Safari tab, every other browser and a wide screen keep the bar where it was.

Both external map hosts are answered by `page.route`; waits are on the page's own state.
"""
import io

import pytest
from PIL import Image, ImageChops

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login
from place_map_support import SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_MIN = {"width": 360, "height": 740}

# What navigator.standalone says in each client.
CLIENTS = {
    "home-screen-app": (
        "Object.defineProperty(Navigator.prototype, 'standalone',"
        " {get: () => true, configurable: true});"),
    "safari-tab": (
        "Object.defineProperty(Navigator.prototype, 'standalone',"
        " {get: () => false, configurable: true});"),
    "other-browser": "",
}
# How much lower the phone app bar starts in each client, in CSS pixels.
DROP = {"home-screen-app": 24, "safari-tab": 0, "other-browser": 0}
# How far below the window's top edge iOS 27's frost reaches in a Home Screen web app, in CSS
# pixels (measured in the iOS 27.0 simulator: a fine stripe pattern loses contrast from the top
# edge down to here).
FROST = 36
# Accueil, Vols, Lieu and Style: the tab bar's pages.
ROUTES = ("/", "/flights", "/detection", "/display")

# The page at rest: loaded, nothing moving, and the Location page's map ready and scrolled past its
# lead (none outside an iPhone).
AT_REST = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"
    " && (!document.querySelector('.place-stage') || (document.documentElement.classList"
    ".contains('map-ready') && Math.abs(window.scrollY - (parseFloat(getComputedStyle("
    "document.documentElement).getPropertyValue('--place-lead')) || 0)) < 1))")
ALL_TILES = (
    "() => { const tiles = document.querySelectorAll('#place-map .leaflet-tile');"
    " return [...tiles].every((t) => t.classList.contains('leaflet-tile-loaded')"
    "  && getComputedStyle(t).opacity === '1'); }")
# The app bar, what it carries and the Location page's floating parts, in the window: left, top,
# right, bottom (null where the page has none).
BOXES = (
    "() => { const box = (sel) => { const e = document.querySelector(sel);"
    " if (!e) return null; const r = e.getBoundingClientRect();"
    " return [r.left, r.top, r.right, r.bottom].map((v) => Math.round(v * 10) / 10); };"
    " return {webApp: document.documentElement.classList.contains('web-app'),"
    "  header: box('.site-header'), logo: box('.site-header .logo-mark'),"
    "  button: box('.site-header .frame-menu__button'),"
    "  search: box('.place-search__row'), modes: box('.place-modes'),"
    "  bootSearch: box('.place-boot__search')}; }")
# The glyphs of the app bar: the logo, the wordmark and the frame button's name.
GLYPHS_HIDDEN = (
    ".site-header .site-title, .site-header .frame-menu__name, .site-header .logo-mark"
    " { visibility: hidden !important; }")
GLYPHS_GONE = (
    "() => getComputedStyle(document.querySelector('.site-header .site-title'))"
    ".visibility === 'hidden'")


def _open(new_context, server, viewport, client):
    context = new_context(viewport=viewport)
    if CLIENTS[client]:
        context.add_init_script(CLIENTS[client])
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    return context, page


def _boxes_on(page, server, route):
    page.goto(server.base_url() + route)
    page.wait_for_function(AT_REST, timeout=15000)
    if route == "/detection":
        page.wait_for_function(SETTLED, timeout=10000)
        page.wait_for_function(ALL_TILES, timeout=10000)
    return page.evaluate(BOXES)


def _first_glyph_row(page, width):
    """The first row of the window where the app bar's glyphs are painted: the bar shot with its
    glyphs against the same bar without them."""
    clip = {"x": 0, "y": 0, "width": width, "height": 120}
    shown = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("L")
    tag = page.add_style_tag(content=GLYPHS_HIDDEN)
    page.wait_for_function(GLYPHS_GONE, timeout=5000)
    bare = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("L")
    tag.evaluate("(t) => t.remove()")
    ink = ImageChops.difference(shown, bare).point(lambda v: 255 if v > 8 else 0).getbbox()
    assert ink, "no glyph painted in the app bar"
    return ink[1]


@pytest.mark.parametrize("client", list(CLIENTS))
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_phone_app_bar_starts_below_the_frost_only_in_a_home_screen_web_app(
        new_context, make_app_server, viewport, client):
    """on Accueil, Vols, Lieu and Style, a Home Screen web app (and only it) is marked before the
    first paint and starts the app bar 24px lower: the bar is 24px taller, its logo and frame
    button sit 24px lower, and the first painted row of its glyphs is clear of the frost; on the
    Location page the search field and the chips follow the bar by the same 24px, the same gap
    below it as anywhere else; a Safari tab and every other browser keep everything where it
    was"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, client)
    width, drop = viewport["width"], DROP[client]
    try:
        for route in ROUTES:
            got = _boxes_on(page, server, route)
            assert got["webApp"] is (client == "home-screen-app"), (route, got)
            assert got["header"] == [0, 0, width, 52 + drop], (route, got)
            # The 28px logo and the 44px frame button, centred under the bar's 4px top padding.
            assert got["logo"][1] == 12 + drop and got["button"][1] == 4 + drop, (route, got)
            if client == "home-screen-app":
                first = _first_glyph_row(page, width)
                assert first >= FROST, (route, first)
            if route == "/detection":
                assert got["search"] == [12, 64 + drop, width - 12, 118 + drop], got
                assert got["search"][1] - got["header"][3] == 12, got
                assert got["modes"][1] == 126 + drop, got
    finally:
        context.close()


def _hold_the_map_script(context):
    """Answers the page's own map script with nothing, so the page stays in its loading state."""
    context.route("**/static/place-map.js*", lambda route: route.fulfill(
        status=200, content_type="text/javascript", body="/* held */"))


@pytest.mark.parametrize("client", list(CLIENTS))
def test_the_location_loading_state_follows_the_app_bar(new_context, make_app_server, client):
    """before the map is ready, the Location page's placeholder search field sits where the real
    one will, below the app bar: 24px lower in a Home Screen web app, where it always was
    elsewhere, so nothing jumps when the map takes over"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_PHONE, client)
    _hold_the_map_script(context)
    drop = DROP[client]
    try:
        page.goto(server.base_url() + "/detection")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.locator(".place-boot__search").wait_for(state="visible")
        got = page.evaluate(BOXES)
        assert got["header"] == [0, 0, VIEWPORT_PHONE["width"], 52 + drop], got
        assert got["bootSearch"][1] == 64 + drop, got
    finally:
        context.close()


@pytest.mark.parametrize("client", list(CLIENTS))
def test_a_wide_screen_keeps_the_frame_button_where_it_was(
        new_context, make_app_server, client):
    """the wide layout has no app bar row (the sidebar carries the brand): its frame button and
    the Location page's search field sit at the same place in every client, a Home Screen web app
    on a wide screen included"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, client)
    try:
        for route in ROUTES:
            got = _boxes_on(page, server, route)
            assert got["webApp"] is (client == "home-screen-app"), (route, got)
            assert got["header"][1] == 0 and got["header"][3] == 0, (route, got)
            assert got["button"][1] == 48 and got["button"][3] == 92, (route, got)
            if route == "/detection":
                assert got["search"][1] == 16, got
    finally:
        context.close()
