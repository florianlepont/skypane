#!/usr/bin/env python3
"""Browser checks that, on a phone, the Location map is document content rather than a fixed layer:
the map sits inside the page container from above the window's top edge to below its bottom edge,
and the header, search, chips, offer, sheet and tab bar stay where they were. Pinch and pan (wheel
and drag), the pin drag and the loading state keep working. The map runs a lead above the page,
which the page opens scrolled past, and a tail below it, so that an iPhone's status bar and a
Safari tab's toolbar show map; a Safari tab, a Home Screen web app and every other browser get the
same layout. The app bar draws nothing of its own over the map, and a drag does not scroll the
page.

Both external hosts are answered by `page.route`; waits are on the page's own state.
"""
import io

import pytest
from PIL import Image, ImageChops

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login
from place_map_support import CLEAR_BOX, SETTLED, Hosts, seed as _seed
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, WCAG_AA_UI_COMPONENT, contrast_ratio

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_MIN = {"width": 360, "height": 740}
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
# The page at rest: on a phone scrolled exactly past the map's lead, on a wide screen at the top.
AT_REST = (
    "() => Math.abs(window.scrollY - (parseFloat(getComputedStyle(document.documentElement)"
    ".getPropertyValue('--place-lead')) || 0)) < 1")
# The ground colour of the tiles, which the page shows behind and below the map.
GROUND = "rgb(242, 239, 233)"
# The map above and below the page on a phone, in CSS pixels.
LEAD = 80
TAIL = 80
PIN_BOX = (
    "() => { const r = document.querySelector('#place-map .place-pin').getBoundingClientRect();"
    " return {x: r.left + 22, y: r.top + 42}; }")

BOXES = (
    "() => Object.fromEntries(['.site-header', '.place-search__row', '.place-modes', '.place-sheet',"
    " '.tab-bar', '#place-map'].map((sel) => { const el = document.querySelector(sel);"
    " if (!el) return [sel, null]; const r = el.getBoundingClientRect();"
    " return [sel, [r.left, r.top, r.right, r.bottom].map((v) => Math.round(v * 10) / 10)]; }))")

# The positions of the floating parts at a 390x844 and a 360x740 phone with the compact sheet in
# My position mode, nothing unsaved: left, top, right, bottom of each.
FLOATING = {
    390: {
        ".site-header": [0, 0, 390, 52],
        ".place-search__row": [12, 64, 378, 118],
        ".place-modes": [12, 126, None, 170],
        ".place-sheet": [12, None, 378, 762],
        ".tab-bar": [8, 770, 382, 838],
    },
    360: {
        ".site-header": [0, 0, 360, 52],
        ".place-search__row": [12, 64, 348, 118],
        ".place-modes": [12, 126, None, 170],
        ".place-sheet": [12, None, 348, 658],
        ".tab-bar": [8, 666, 352, 734],
    },
}


def _open_ready(new_context, server, viewport, **options):
    context = new_context(viewport=viewport, **options)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    page.wait_for_function(AT_REST, timeout=5000)
    return context, page


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_phone_map_is_document_content_spanning_the_window(
        new_context, make_app_server, viewport, theme):
    """the map is not fixed: it lies inside the page container, which is exactly as tall as the
    map; it runs from above the top edge to below the bottom edge, the document is no wider than
    the window, and the page body behind it is the tile ground colour in both themes"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, viewport, color_scheme=theme)
    try:
        state = page.evaluate(
            "() => { const map = document.getElementById('place-map');"
            " const host = document.querySelector('.page-content');"
            " const m = map.getBoundingClientRect(); const h = host.getBoundingClientRect();"
            " const root = document.scrollingElement;"
            " return {position: getComputedStyle(map).position, inside: host.contains(map),"
            " mapTop: m.top, mapBottom: m.bottom, mapLeft: m.left, mapRight: m.right,"
            " hostTop: h.top, hostBottom: h.bottom, w: innerWidth, h: innerHeight,"
            " scrollY: root.scrollHeight - innerHeight, scrollX: root.scrollWidth - innerWidth,"
            " body: getComputedStyle(document.body).backgroundColor,"
            " bodyBottom: document.body.getBoundingClientRect().bottom,"
            " mapColour: getComputedStyle(map).backgroundColor}; }")
        assert state["position"] == "absolute", state
        assert state["inside"], state
        assert state["mapTop"] < 0 and state["mapBottom"] > state["h"], state
        assert state["mapLeft"] <= 0 and state["mapRight"] >= state["w"], state
        assert state["hostTop"] == state["mapTop"], state
        assert state["hostBottom"] == state["mapBottom"], state
        assert state["scrollX"] <= 0, state
        assert state["body"] == GROUND and state["mapColour"] == GROUND, state
        assert state["bodyBottom"] >= state["h"], state
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_floating_parts_keep_their_places_over_the_document_map(
        new_context, make_app_server, viewport, theme):
    """the app bar, the search row and the tab bar sit where they sat when the map was a fixed
    layer, and so do the mode chips and the sheet"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, viewport, color_scheme=theme)
    try:
        boxes = page.evaluate(BOXES)
        for selector, expected in FLOATING[viewport["width"]].items():
            got = boxes[selector]
            # A None edge is content dependent (text width of the chips, height of the sheet with
            # its runway list) and differs between machines; the other edges are layout fixed.
            assert got and all(
                b is None or abs(a - b) <= 1.5 for a, b in zip(got, expected)), (selector, boxes)
    finally:
        context.close()


def test_the_map_still_pans_zooms_and_moves_the_pin_on_a_phone(new_context, make_app_server):
    """a tap drops the pin and dragging the pin moves it, a drag on the map pans it and a wheel
    step zooms it, with the document at rest past the lead afterwards"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, VIEWPORT_PHONE)
    try:
        page.click("label.place-mode:has(#place-mode-area)")
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length === 0", timeout=5000)
        box = page.evaluate(CLEAR_BOX)
        page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.55)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=10000)
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        page.wait_for_function(SETTLED, timeout=10000)
        lat = page.input_value("#place-lat")
        pin = page.evaluate(PIN_BOX)
        page.mouse.move(pin["x"], pin["y"] - 10)
        page.mouse.down()
        page.mouse.move(pin["x"] + 50, pin["y"] - 10 + 30, steps=6)
        page.mouse.up()
        page.wait_for_function(
            "before => document.getElementById('place-lat').value !== before", arg=lat, timeout=10000)
        centre = "() => { const p = document.querySelector('#place-map .leaflet-map-pane');" \
            " const r = p.getBoundingClientRect(); return [r.left, r.top]; }"
        before = page.evaluate(centre)
        page.mouse.move(60, 300)
        page.mouse.down()
        page.mouse.move(120, 340, steps=6)
        page.mouse.up()
        page.wait_for_function(
            "b => { const r = document.querySelector('#place-map .leaflet-map-pane')"
            ".getBoundingClientRect(); return Math.abs(r.left - b[0]) > 20; }", arg=before)
        tiles_before = page.evaluate(
            "() => document.querySelector('#place-map .leaflet-tile-pane').innerHTML.length")
        page.mouse.move(195, 300)
        page.mouse.wheel(0, -300)
        page.wait_for_function(
            "n => document.querySelector('#place-map .leaflet-tile-pane').innerHTML.length !== n",
            arg=tiles_before, timeout=10000)
        page.wait_for_function(AT_REST, timeout=5000)
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_phone_loading_state_is_document_content_in_the_ground_colour(
        new_context, make_app_server, viewport, theme):
    """while the map script has not run, the loading placeholder is not a fixed layer: it fills
    the window in the tile ground colour (never the dark theme surface) and the page does not
    scroll"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=theme)
    Hosts(context)
    context.route("**/static/place-map.js*", lambda route: route.fulfill(
        status=200, content_type="text/javascript", body="/* held */"))
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection", wait_until="domcontentloaded")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.wait_for_function("() => document.documentElement.classList.contains('js-early')")
        state = page.evaluate(
            "() => { const b = document.querySelector('.place-boot'); const r = b.getBoundingClientRect();"
            " const s = getComputedStyle(b); const root = document.scrollingElement;"
            " return {position: s.position, bg: s.backgroundColor, top: r.top, bottom: r.bottom,"
            " left: r.left, right: r.right, w: innerWidth, h: innerHeight,"
            " body: getComputedStyle(document.body).backgroundColor,"
            " scroll: root.scrollHeight - innerHeight}; }")
        assert state["position"] == "absolute" and state["bg"] == GROUND, state
        assert state["body"] == GROUND, state
        assert state["top"] <= 0 and state["bottom"] >= state["h"], state
        assert state["left"] <= 0 and state["right"] >= state["w"], state
        assert state["scroll"] <= 0, state
    finally:
        context.close()


def test_the_wide_screen_map_stays_a_fixed_layer(new_context, make_app_server):
    """from 960px the map is unchanged: still a fixed layer behind the sidebar"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, VIEWPORT_DESKTOP)
    try:
        assert page.evaluate(
            "() => getComputedStyle(document.getElementById('place-map')).position") == "fixed"
    finally:
        context.close()


# The fixed boxes touching the top edge of the window, as when the loading placeholder shows: the
# one ground-coloured strip there.
TOP_EDGE_CHAIN = (
    "() => { const top = document.elementFromPoint(innerWidth / 2, 1);"
    " return {width: innerWidth, topmost: top ? top.className : null,"
    "  fixedAtTop: [...document.querySelectorAll('*')].filter((e) => {"
    "   const s = getComputedStyle(e); const r = e.getBoundingClientRect();"
    "   return s.position === 'fixed' && r.top <= 1 && r.height > 0; }).map((e) => {"
    "   const s = getComputedStyle(e); const r = e.getBoundingClientRect();"
    "   return {name: e.className, top: r.top, left: r.left, right: r.right, height: r.height,"
    "    bg: s.backgroundColor, filter: s.backdropFilter || 'none', opacity: s.opacity}; })}; }")
# Everything of the app bar that could draw over the map behind it: the bar and its pseudo
# elements, with their fill, picture, blur and mask.
HEADER_PAINT = (
    "() => { const h = document.querySelector('.site-header');"
    " return [null, '::before', '::after'].map((pseudo) => { const s = getComputedStyle(h, pseudo);"
    "  if (pseudo && s.content === 'none') return null;"
    "  return {pseudo: pseudo, bg: s.backgroundColor, image: s.backgroundImage,"
    "   blur: s.backdropFilter || 'none', mask: s.maskImage || 'none'}; }).filter(Boolean); }")
# The window from its top edge down to the search field's top edge, over the full width.
ABOVE_FIELD = (
    "() => ({x: 0, y: 0, width: innerWidth,"
    " height: document.querySelector('.place-search__row').getBoundingClientRect().top})")


def _assert_one_ground_strip_is_fixed_at_the_top(got):
    assert len(got["fixedAtTop"]) == 1, got
    edge = got["fixedAtTop"][0]
    assert edge["name"] == "place-edge" and got["topmost"] == "place-edge", got
    assert edge["top"] == 0 and edge["left"] == 0 and edge["right"] == got["width"], got
    assert 2 <= edge["height"] <= 4, got
    assert edge["bg"] == GROUND and edge["filter"] == "none" and edge["opacity"] == "1", got
    return edge


def _shot(page, clip, css):
    """A screenshot of `clip` with `css` added to the page (each call adds its own style tag)."""
    page.add_style_tag(content=css)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    return Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_app_bar_draws_nothing_of_its_own_over_the_map(
        new_context, make_app_server, viewport, theme):
    """over the map the app bar is only its parts (the logo with the wordmark, and the frame
    button on its own surface): the bar and its pseudo elements carry no fill, gradient, blur or
    mask, and from the window's top edge down to the search field the picture with the parts
    hidden is exactly the bare map, the picture with the whole bar hidden (under an iPhone's status
    bar only the browser's own blur shows)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, viewport, color_scheme=theme)
    try:
        page.wait_for_function(ALL_TILES, timeout=10000)
        paint = page.evaluate(HEADER_PAINT)
        assert [part["pseudo"] for part in paint] == [None], paint
        assert paint[0]["bg"] == "rgba(0, 0, 0, 0)" and paint[0]["image"] == "none", paint
        assert paint[0]["blur"] == "none" and paint[0]["mask"] == "none", paint
        clip = page.evaluate(ABOVE_FIELD)
        assert clip["height"] > 52, clip
        bar = _shot(page, clip, NO_MARKS + " .site-header * { visibility: hidden !important; }")
        bare = _shot(page, clip, ".site-header { visibility: hidden !important; }")
        high = max(band[1] for band in ImageChops.difference(bar, bare).getextrema())
        assert high <= 2, "the app bar draws over the map (%d levels)" % high
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_ground_strip_is_fixed_at_the_top_while_the_map_loads_and_absent_on_a_wide_screen(
        new_context, make_app_server, theme):
    """the fixed strip is there from the first paint on a phone (the loading placeholder is
    document content too), and a wide screen, whose map is itself the fixed layer, has none"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN, color_scheme=theme)
    Hosts(context)
    context.route("**/static/place-map.js*", lambda route: route.fulfill(
        status=200, content_type="text/javascript", body="/* held */"))
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection", wait_until="domcontentloaded")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.wait_for_function("() => document.documentElement.classList.contains('js-early')")
        page.locator(".place-boot").wait_for(state="visible")
        _assert_one_ground_strip_is_fixed_at_the_top(page.evaluate(TOP_EDGE_CHAIN))
    finally:
        context.close()
    context, page = _open_ready(new_context, server, VIEWPORT_DESKTOP, color_scheme=theme)
    try:
        assert page.evaluate(
            "() => getComputedStyle(document.querySelector('.place-edge')).display") == "none"
    finally:
        context.close()


# What navigator.standalone says in each browser the page meets: false in a Safari tab on an
# iPhone, true in a Home Screen web app, undefined in every other browser (Chromium as it is). The
# page lays itself out the same in all three.
BROWSERS = {
    "safari-tab": (
        "Object.defineProperty(Navigator.prototype, 'standalone',"
        " {get: () => false, configurable: true});"),
    "home-screen-app": (
        "Object.defineProperty(Navigator.prototype, 'standalone',"
        " {get: () => true, configurable: true});"),
    "other-browser": "",
}
LEAD_STATE = (
    "() => { const m = document.getElementById('place-map').getBoundingClientRect();"
    " const edge = document.querySelector('.place-edge');"
    " return {lead: document.documentElement.classList.contains('place-lead'),"
    "  scrollY: window.scrollY, mapTop: m.top + window.scrollY, mapBottom: m.bottom,"
    "  h: innerHeight, scrollMax: document.scrollingElement.scrollHeight - innerHeight,"
    "  position: getComputedStyle(document.getElementById('place-map')).position,"
    "  edge: edge ? getComputedStyle(edge).display : null}; }")
# With the page scrolled to its very top, what lies in the lead: the map, at its top, middle and
# bottom rows (nothing scrolls between the scroll and the probes).
LEAD_IS_MAP = (
    "(lead) => { window.scrollTo(0, 0); const map = document.getElementById('place-map');"
    " return [window.scrollY].concat([2, lead / 2, lead - 2].map((y) => {"
    "  const hit = document.elementFromPoint(innerWidth / 2, y);"
    "  return !!hit && map.contains(hit); })); }")
# The same with the page scrolled to its very end: the last rows of the window are the tail (at
# the left edge, clear of the floating tab bar).
TAIL_IS_MAP = (
    "(tail) => { const root = document.scrollingElement;"
    " window.scrollTo(0, root.scrollHeight - innerHeight); const map = document.getElementById('place-map');"
    " return [window.scrollY].concat([innerHeight - 2, innerHeight - tail / 2, innerHeight - tail + 2]"
    "  .map((y) => { const hit = document.elementFromPoint(2, y);"
    "  return !!hit && map.contains(hit); })); }")
AT_LEAD = "(lead) => Math.abs(window.scrollY - lead) < 1"


def _open_tab(new_context, server, viewport, client="safari-tab", **options):
    context = new_context(viewport=viewport, **options)
    if BROWSERS[client]:
        context.add_init_script(BROWSERS[client])
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


@pytest.mark.parametrize("client", list(BROWSERS))
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_page_starts_scrolled_past_a_lead_of_map_under_the_status_bar(
        new_context, make_app_server, viewport, theme, client):
    """on an iPhone the status bar shows the document above the window, in a Safari tab and in a
    Home Screen web app alike, and a tab's toolbar the document below it, so the map runs a lead
    above the page and a tail below it, and the page opens scrolled past the lead, whatever the
    browser: the map starts at the document's top and runs the tail past the window's bottom, lead
    and tail are map, the app bar, search, chips, sheet and tab bar sit exactly where they sit
    without them, no fixed box touches the top edge (the loading state's ground strip is gone), and
    a scroll that ends in the lead or in the tail settles back"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, viewport, client, color_scheme=theme)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        state = page.evaluate(LEAD_STATE)
        assert state["lead"] and state["position"] == "absolute", state
        assert state["mapTop"] == 0 and state["mapBottom"] == state["h"] + TAIL, state
        assert state["scrollMax"] == LEAD + TAIL, state
        assert state["edge"] == "none" and page.evaluate(TOP_EDGE_CHAIN)["fixedAtTop"] == [], state
        boxes = page.evaluate(BOXES)
        for selector, expected in FLOATING[viewport["width"]].items():
            got = boxes[selector]
            assert got and all(
                b is None or abs(a - b) <= 1.5 for a, b in zip(got, expected)), (selector, boxes)
        top, *hits = page.evaluate(LEAD_IS_MAP, LEAD)
        assert top == 0 and all(hits), hits
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        end, *hits = page.evaluate(TAIL_IS_MAP, TAIL)
        assert end == LEAD + TAIL and all(hits), (end, hits)
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
    finally:
        context.close()


@pytest.mark.parametrize("client", list(BROWSERS))
def test_the_page_does_not_scroll_by_hand_over_the_sheet(new_context, make_app_server, client):
    """the page under the map does not scroll by hand, whatever the browser: through a wheel over
    the sheet the page never leaves the lead, not even for a frame (a scroll there would bare the
    end of the tail under the toolbar and slide the app bar under the status bar until it settled
    back)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE, client)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        # Every frame's scroll position from here on.
        page.evaluate(
            "() => { window.__seen = []; const look = () => {"
            " window.__seen.push(window.scrollY); requestAnimationFrame(look); }; look(); }")
        sheet = page.evaluate(
            "() => { const r = document.querySelector('.place-sheet').getBoundingClientRect();"
            " return {x: r.left + 24, y: r.top + 12}; }")
        page.mouse.move(sheet["x"], sheet["y"])
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(400)
        seen = page.evaluate("() => window.__seen")
        assert len(seen) > 10 and set(seen) == {LEAD}, sorted(set(seen))
    finally:
        context.close()


# The map's own marks (the pin and the area circle) follow the theme; the band compared below is
# the app bar over the bare tiles.
NO_MARKS = (
    "#place-map .leaflet-overlay-pane, #place-map .leaflet-marker-pane,"
    " #place-map .leaflet-shadow-pane { visibility: hidden !important; }")
# The colour tokens the app bar's parts carry over the map (on the frame button and the brand),
# next to the page's own values.
BAR_TOKENS = (
    "() => { const names = ['--color-text', '--color-accent', '--color-border', '--color-status-ok',"
    " '--color-status-warn', '--color-status-error', '--glass-bg', '--glass-border',"
    " '--glass-highlight', '--glass-solid', '--shadow-glass'];"
    " const button = getComputedStyle(document.querySelector('.site-header .frame-menu__button'));"
    " const brand = getComputedStyle(document.querySelector('.site-header > .brand'));"
    " const root = getComputedStyle(document.documentElement);"
    " const read = (s, list) => list.map((n) => n + ': ' + s.getPropertyValue(n).trim());"
    " return [read(button, names).concat(read(brand, ['--color-text', '--color-accent'])),"
    "  read(root, names).concat(read(root, ['--color-text', '--color-accent']))]; }")
ALL_TILES = (
    "() => { const tiles = document.querySelectorAll('#place-map .leaflet-tile');"
    " return tiles.length > 0 && [...tiles].every((t) => t.classList.contains('leaflet-tile-loaded')"
    "  && getComputedStyle(t).opacity === '1'); }")


def _bar_band(page):
    """The window from its top edge to the app bar's bottom edge (below it the search row's own
    shadow, which follows the theme, reaches up)."""
    page.add_style_tag(content=NO_MARKS)
    page.wait_for_function(ALL_TILES, timeout=10000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    bottom = page.evaluate(
        "() => document.querySelector('.site-header').getBoundingClientRect().bottom")
    clip = {"x": 0, "y": 0, "width": VIEWPORT_PHONE["width"], "height": bottom}
    return Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")


def test_the_app_bar_over_the_map_is_drawn_the_same_in_both_themes(
        new_context, make_app_server):
    """the tiles are light in both themes, and so is an iPhone's status bar over them, so the app
    bar is too: in the dark theme its parts (the logo, the wordmark and the frame button) are drawn
    over the map exactly as in the light theme"""
    server = make_app_server(seed=_seed, fake_providers=True)
    bands = {}
    for theme in ("light", "dark"):
        context, page = _open_tab(new_context, server, VIEWPORT_PHONE, color_scheme=theme)
        try:
            page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
            if theme == "light":
                # The bar's colours are the light theme's own, not a copy that has drifted.
                bar, own = page.evaluate(BAR_TOKENS)
                assert bar == own, (bar, own)
            bands[theme] = _bar_band(page)
        finally:
            context.close()
    # The logo's edges are smoothed a little differently from one theme to the other (about 15
    # pixels of the band, by up to 15 levels); a tint behind the bar would change most of it.
    diff = ImageChops.difference(bands["light"], bands["dark"]).convert("L")
    changed = sum(diff.histogram()[3:])
    assert changed <= diff.width * diff.height // 200, (changed, diff.getbbox(), diff.getextrema())


# What sits on the app bar: each part's box in the window and its own colour (the text colour of
# the wordmark and of the frame button's name, the stroke colour of the logo).
BAR_PARTS = (
    "() => Object.fromEntries([['wordmark', '.site-header .site-title'],"
    " ['frame', '.site-header .frame-menu__name'], ['logo', '.site-header .logo-mark']]"
    " .map(([name, sel]) => { const e = document.querySelector(sel); const r = e.getBoundingClientRect();"
    "  return [name, {box: [r.left, r.top, r.right, r.bottom], colour: getComputedStyle(e).color}]; }))")
BARE_PARTS = (
    ".site-header .site-title, .site-header .frame-menu__name, .site-header .logo-mark"
    " { visibility: hidden !important; }")


def _hex(css_colour):
    channels = css_colour[css_colour.index("(") + 1:css_colour.index(")")].split(",")[:3]
    return "#%02X%02X%02X" % tuple(round(float(c)) for c in channels)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_app_bar_reads_on_the_map_in_both_themes(new_context, make_app_server, theme):
    """over the bare map the wordmark and the frame button's name keep text contrast, and the logo
    the contrast of a graphic, against every pixel drawn behind them, in both themes (the light
    tiles under the dark theme's light ink would not read)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE, color_scheme=theme)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        parts = page.evaluate(BAR_PARTS)
        page.add_style_tag(content=BARE_PARTS)
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.site-header .site-title'))"
            ".visibility === 'hidden'", timeout=5000)
        band = _bar_band(page)
        worst = {}
        for name, part in parts.items():
            left, top, right, bottom = (round(v) for v in part["box"])
            ink = _hex(part["colour"])
            worst[name] = min(
                contrast_ratio(ink, "#%02X%02X%02X" % band.getpixel((x, y)))
                for x in range(left, right) for y in range(top, bottom))
        assert worst["wordmark"] >= WCAG_AA_NORMAL_TEXT, worst
        assert worst["frame"] >= WCAG_AA_NORMAL_TEXT, worst
        assert worst["logo"] >= WCAG_AA_UI_COMPONENT, worst
    finally:
        context.close()


# Every frame from the document's start: the time, the scroll position and whether the opening
# splash covers the page.
FRAMES = (
    "window.__frames = []; (function look() { const root = document.documentElement;"
    " window.__frames.push([performance.now(), window.scrollY,"
    "  !!root && root.classList.contains('splash-on')]);"
    " requestAnimationFrame(look); })();")
NO_SPLASH = "() => !document.documentElement.classList.contains('splash-on')"
# How long the screen has had to settle after the splash before the nudge, at least, in ms (in the
# iOS Simulator a nudge 100ms after it still left part of the splash's veil, 300ms none).
SPLASH_GONE_MS = 300


@pytest.mark.parametrize("client", list(BROWSERS))
def test_the_page_nudges_its_scroll_once_the_opening_splash_has_gone(
        new_context, make_app_server, client):
    """an iPhone's status bar keeps the look it took from the page at its last scroll, and the page
    scrolls past the lead while the opening splash still covers it (a dark splash in the dark
    theme left a grey veil under the clock): once the splash has gone, and not before, the page
    moves by one pixel for a moment and comes back to the lead, whatever the browser"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, splash=True, color_scheme="dark")
    if BROWSERS[client]:
        context.add_init_script(BROWSERS[client])
    context.add_init_script(FRAMES)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(READY, timeout=15000)
        page.wait_for_function(NO_SPLASH, timeout=15000)
        page.wait_for_timeout(1500)
        frames = page.evaluate("() => window.__frames")
        under = [y for _, y, splash in frames if splash]
        last_splash = max(i for i, (_, _, splash) in enumerate(frames) if splash)
        after = [y for _, y, _ in frames[last_splash + 1:]]
        assert under and set(under) <= {0, LEAD} and under[-1] == LEAD, sorted(set(under))
        assert set(after) == {LEAD, LEAD - 1} and after[-1] == LEAD, after
        assert 1 <= after.count(LEAD - 1) <= 4, after
        # Not in the splash's last frames: Safari takes the look of the screen as it settles, and
        # a nudge right as the splash goes still caught part of it.
        nudged = next(t for t, y, _ in frames[last_splash + 1:] if y == LEAD - 1)
        assert SPLASH_GONE_MS <= nudged - frames[last_splash][0] <= 1500, nudged - frames[last_splash][0]
    finally:
        context.close()


def test_the_lead_does_not_pull_the_page_back_while_a_field_is_typed_in(
        new_context, make_app_server):
    """a scroll into the lead while the search field has focus (the keyboard is up on a phone)
    stays where it is; once the field lets go the page settles back past the lead"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        page.focus("#place-search")
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        assert page.evaluate("() => window.scrollY") == 0
        page.evaluate("() => document.activeElement.blur()")
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
    finally:
        context.close()


def test_a_wide_screen_has_no_lead(new_context, make_app_server):
    """a wide screen, even in a Safari tab, keeps its fixed map with no lead and nothing
    scrolled"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_DESKTOP)
    try:
        state = page.evaluate(LEAD_STATE)
        assert state["position"] == "fixed" and state["scrollY"] == 0, state
        assert page.evaluate(
            "() => getComputedStyle(document.documentElement).getPropertyValue('--place-lead')"
        ).strip() == "", state
    finally:
        context.close()
