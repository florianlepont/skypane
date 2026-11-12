#!/usr/bin/env python3
"""Browser checks that, on a phone, the Location map is document content rather than a fixed layer:
the page container is exactly the largest viewport tall, the map sits inside it from the top edge to
the bottom edge, nothing scrolls, and the header, search, chips, offer, sheet and tab bar stay where
they were. Pinch and pan (wheel and drag), the pin drag and the loading state keep working. In a
Safari tab on an iPhone the map also runs a lead above the page, which the page opens scrolled past,
and a tail below it, so that the status bar and the toolbar show map; a frosted layer runs from the
lead down past the app bar to the search field's top edge, never over the field, and a drag does not
scroll the page.

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
# The ground colour of the tiles, which the page shows behind and below the map.
GROUND = "rgb(242, 239, 233)"
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
    return context, page


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_phone_map_is_document_content_spanning_the_window(
        new_context, make_app_server, viewport, theme):
    """the map is not fixed: it lies inside the page container, which is as tall as the window; it
    runs from the top edge to the bottom edge, the document cannot scroll or be wider than the
    window, and the page body behind it is the tile ground colour in both themes"""
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
        assert state["mapTop"] <= 0 and state["mapBottom"] >= state["h"], state
        assert state["mapLeft"] <= 0 and state["mapRight"] >= state["w"], state
        assert state["hostTop"] == 0 and state["hostBottom"] == state["h"], state
        assert state["scrollY"] <= 0 and state["scrollX"] <= 0, state
        assert state["body"] == GROUND and state["mapColour"] == GROUND, state
        assert state["bodyBottom"] >= state["h"], state
        page.mouse.wheel(0, 400)
        page.wait_for_function("() => window.scrollY === 0")
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
    step zooms it, with the document still unscrolled afterwards"""
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
        assert page.evaluate("() => document.scrollingElement.scrollHeight - innerHeight") <= 0
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


# What sits at the top edge of the phone Location page when the page reaches under the status bar
# itself (a Home Screen web app; a Safari tab has the lead tested further down): one fixed box in
# the tile ground colour touching the edge, the body and the map in that colour, the page
# element's surface colour and the browser-chrome colours of the two theme-color tags.
TOP_EDGE_HTML = {"light": "rgb(233, 238, 245)", "dark": "rgb(28, 34, 45)"}
THEME_COLOURS = ["#E7EEF7", "#12151D"]
SAFE_TOP = 59
TOP_EDGE_CHAIN = (
    "() => { const map = document.getElementById('place-map'); const chain = [];"
    " for (let e = map; e; e = e.parentElement) { const s = getComputedStyle(e);"
    "  chain.push({tag: e.tagName, top: e.getBoundingClientRect().top, position: s.position,"
    "   overflow: s.overflow, transform: s.transform, filter: s.filter, contain: s.contain,"
    "   willChange: s.willChange, bg: s.backgroundColor}); }"
    " const top = document.elementFromPoint(innerWidth / 2, 1);"
    " return {chain: chain, root: document.documentElement.getBoundingClientRect().top,"
    "  chrome: [...document.querySelectorAll('meta[name=theme-color]')].map((m) => m.content),"
    "  width: innerWidth, topmost: top ? top.className : null,"
    "  fixedAtTop: [...document.querySelectorAll('*')].filter((e) => {"
    "   const s = getComputedStyle(e); const r = e.getBoundingClientRect();"
    "   return s.position === 'fixed' && r.top <= 1 && r.height > 0; }).map((e) => {"
    "   const s = getComputedStyle(e); const r = e.getBoundingClientRect();"
    "   return {name: e.className, top: r.top, left: r.left, right: r.right, height: r.height,"
    "    bg: s.backgroundColor, filter: s.backdropFilter || 'none', opacity: s.opacity}; })}; }")
# Everything of the app bar that could draw over the status bar zone: the bar and its pseudo
# elements, with their paint box, fill, picture and blur.
HEADER_PAINT = (
    "() => { const h = document.querySelector('.site-header'); const box = h.getBoundingClientRect();"
    " return [null, '::before', '::after'].map((pseudo) => { const s = getComputedStyle(h, pseudo);"
    "  if (pseudo && s.content === 'none') return null;"
    "  return {pseudo: pseudo, top: pseudo ? box.top + parseFloat(s.top) : box.top,"
    "   bg: s.backgroundColor, image: s.backgroundImage,"
    "   blur: s.backdropFilter || 'none'}; }).filter(Boolean); }")


def _force_safe_top(page):
    page.add_style_tag(content=":root { --safe-top: %dpx !important; }" % SAFE_TOP)
    page.wait_for_function(
        "(px) => getComputedStyle(document.documentElement).getPropertyValue('--safe-top')"
        ".trim() === px + 'px'", arg=SAFE_TOP, timeout=5000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)


def _status_zone(page):
    """The pixels of the status bar zone (the forced top inset), as rows of RGB tuples."""
    shot = page.screenshot(clip={"x": 0, "y": 0, "width": page.viewport_size["width"],
                                 "height": SAFE_TOP})
    picture = Image.open(io.BytesIO(shot)).convert("RGB")
    return [[picture.getpixel((x, y)) for x in range(picture.width)]
            for y in range(picture.height)]


def _assert_one_ground_strip_is_fixed_at_the_top(got):
    assert len(got["fixedAtTop"]) == 1, got
    edge = got["fixedAtTop"][0]
    assert edge["name"] == "place-edge" and got["topmost"] == "place-edge", got
    assert edge["top"] == 0 and edge["left"] == 0 and edge["right"] == got["width"], got
    assert 2 <= edge["height"] <= 4, got
    assert edge["bg"] == GROUND and edge["filter"] == "none" and edge["opacity"] == "1", got
    return edge


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_the_phone_top_edge_is_the_bare_map_under_the_status_bar_with_one_fixed_ground_strip(
        new_context, make_app_server, viewport, theme):
    """with a 59px top inset (a phone whose page reaches under the status bar): one fixed box
    touches the top edge, a strip of at most 4px in the tile ground colour across the window and
    on top of everything; below it the status bar zone shows exactly the pixels of the map, with
    no fill, gradient or blur of the app bar over it (the picture of the zone is the same with the
    app bar taken away); the map starts at the page's top edge, the page container clips, no
    ancestor of the map transforms, filters, contains or will-change, and the page element, the
    body and the map keep their colours"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_ready(new_context, server, viewport, color_scheme=theme)
    try:
        _force_safe_top(page)
        got = page.evaluate(TOP_EDGE_CHAIN)
        chain = {link["tag"]: link for link in reversed(got["chain"])}
        chain["MAP"] = got["chain"][0]
        edge = _assert_one_ground_strip_is_fixed_at_the_top(got)
        assert got["chrome"] == THEME_COLOURS, got
        assert chain["MAP"]["top"] == 0 and chain["MAP"]["position"] == "absolute", got
        assert chain["MAP"]["bg"] == GROUND and chain["BODY"]["bg"] == GROUND, got
        assert chain["HTML"]["bg"] == TOP_EDGE_HTML[theme], got
        assert chain["MAIN"]["overflow"] == "clip" and chain["MAIN"]["position"] == "relative", got
        for link in got["chain"]:
            assert link["top"] == 0, got
            assert link["transform"] == "none" and link["filter"] == "none", got
            assert link["contain"] == "none" and link["willChange"] == "auto", got
        for part in page.evaluate(HEADER_PAINT):
            assert part["blur"] == "none", part
            if part["pseudo"] is None:
                assert part["bg"] == "rgba(0, 0, 0, 0)" and part["image"] == "none", part
            else:
                assert part["top"] >= SAFE_TOP, part
        with_bar = _status_zone(page)
        page.add_style_tag(content=".site-header { visibility: hidden !important; }")
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.site-header')).visibility === 'hidden'",
            timeout=5000)
        bare = _status_zone(page)
        veil = max(abs(a - b) for row_a, row_b in zip(with_bar, bare)
                   for pixel_a, pixel_b in zip(row_a, row_b) for a, b in zip(pixel_a, pixel_b))
        # Two levels of 255: the soft shadow of the frame button below the zone, nothing more.
        assert veil <= 2, "the app bar paints over the status bar zone (%d levels)" % veil
        strip = int(edge["height"])
        ground = (242, 239, 233)
        assert all(pixel == ground for row in with_bar[:strip] for pixel in row), with_bar[0][:4]
        assert any(pixel != ground for row in with_bar[strip:] for pixel in row), (
            "the status bar zone shows a flat ground fill, not the map")
        state = page.evaluate(
            "() => { const m = document.getElementById('place-map').getBoundingClientRect();"
            " const r = document.scrollingElement;"
            " return {top: m.top, bottom: m.bottom, h: innerHeight,"
            " scrollY: r.scrollHeight - innerHeight, scrollX: r.scrollWidth - innerWidth}; }")
        assert state["top"] == 0 and state["bottom"] >= state["h"], state
        assert state["scrollY"] <= 0 and state["scrollX"] <= 0, state
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


# The page keys its status bar lead on navigator.standalone: false in a Safari tab on an iPhone,
# true in a Home Screen web app, undefined in every other browser (Chromium here).
SAFARI_TAB = (
    "Object.defineProperty(Navigator.prototype, 'standalone',"
    " {get: () => false, configurable: true});")
HOME_SCREEN_APP = SAFARI_TAB.replace("false", "true")
# The map above and below the page in a Safari tab, in CSS pixels.
LEAD = 80
TAIL = 80
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
# The free middle of the app bar, between the brand at the left and the frame button at the right
# (with room for the button's shadow), so a probe there sees only the bar's fade over the map.
HEADER_GAP = (
    "() => { const h = document.querySelector('.site-header'); const w = innerWidth; let l = 0, r = w;"
    " for (const e of h.querySelectorAll('*')) { const b = e.getBoundingClientRect();"
    "  if (!b.width || !b.height || b.top > h.getBoundingClientRect().bottom) continue;"
    "  if (b.right <= w / 2) l = Math.max(l, b.right); else if (b.left >= w / 2) r = Math.min(r, b.left); }"
    " return {x: l + 16, width: r - l - 32}; }")


def _open_tab(new_context, server, viewport, script=SAFARI_TAB, **options):
    context = new_context(viewport=viewport, **options)
    context.add_init_script(script)
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


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_in_a_safari_tab_the_page_starts_scrolled_past_a_lead_of_map_under_the_status_bar(
        new_context, make_app_server, viewport, theme):
    """in a Safari tab the status bar shows the document above the window and the toolbar the
    document below it, so the map runs a lead above the page and a tail below it, and the page
    opens scrolled past the lead: the map starts at the document's top and runs the tail past the
    window's bottom, lead and tail are map, the app bar, search, chips, sheet and tab bar sit
    exactly where they sit without them, no fixed box touches the top edge (the ground strip is
    gone), and a scroll that ends in the lead or in the tail settles back"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, viewport, color_scheme=theme)
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


def test_in_a_safari_tab_the_page_does_not_scroll_by_hand_over_the_sheet(
        new_context, make_app_server):
    """the page under the map does not scroll by hand: through a wheel over the sheet the page
    never leaves the lead, not even for a frame (a scroll there would bare the end of the tail
    under the toolbar and slide the app bar under the status bar until it settled back)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE)
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


# A test-only picture on the map in place of the flat test tiles: a dark line every 6px, so a
# blur over the map shows as lost contrast, row band by row band.
LINES = (
    "#place-map .leaflet-pane { visibility: hidden !important; }"
    " #place-map { background: repeating-linear-gradient("
    "to bottom, #000 0 1px, #fff 1px 6px) !important; }")
BAND = 6
# Where the app bar's backdrop layer starts and ends, in document pixels, its blur, and where the
# bar ends and the search field starts.
FROST = (
    "() => { const h = document.querySelector('.site-header'); const s = getComputedStyle(h, '::before');"
    " const top = h.getBoundingClientRect().top + window.scrollY + parseFloat(s.top);"
    " return {top: top, bottom: top + parseFloat(s.height), blur: s.backdropFilter,"
    "  barBottom: h.getBoundingClientRect().bottom + window.scrollY,"
    "  field: document.querySelector('.place-search__row').getBoundingClientRect().top"
    "   + window.scrollY}; }")


def _contrast_bands(page, clip):
    """The contrast (brightest less darkest, 0 to 1) of each BAND-row band of `clip`, averaged
    over its columns."""
    picture = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("L")
    bands = []
    for top in range(0, picture.height - BAND + 1, BAND):
        spans = []
        for x in range(picture.width):
            column = [picture.getpixel((x, y)) for y in range(top, top + BAND)]
            spans.append(max(column) - min(column))
        bands.append(sum(spans) / len(spans) / 255)
    return bands


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_a_frosted_layer_runs_from_the_status_bar_down_past_the_app_bar_in_a_safari_tab(
        new_context, make_app_server, theme):
    """Safari blurs only the top of the status bar zone and stops across its icons; the app bar's
    own frosted layer covers the whole lead (all that the status bar can show) and runs on past the
    bar down to the search field's top edge (it lies above the field, so no further). In the
    window, the map is blurred right under the status bar, then grows sharp row by row with no
    step, and is untouched below the layer"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE, color_scheme=theme)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        frost = page.evaluate(FROST)
        assert frost["top"] <= 0 and frost["blur"].startswith("blur("), frost
        assert frost["barBottom"] < frost["field"] - 1 <= frost["bottom"] <= frost["field"], frost
        page.add_style_tag(content=LINES)
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('#place-map .leaflet-pane'))"
            ".visibility === 'hidden'", timeout=5000)
        # The left gutter, clear of the brand, the search row and the chips all the way down.
        height = frost["bottom"] - LEAD + 2 * BAND
        clip = {"x": 2, "y": 0, "width": 8, "height": height}
        frosted = _contrast_bands(page, clip)
        page.add_style_tag(content=".site-header { visibility: hidden !important; }")
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.site-header')).visibility === 'hidden'",
            timeout=5000)
        bare = _contrast_bands(page, clip)
        assert min(bare) >= 0.9, bare
        seen = [f / b for f, b in zip(frosted, bare)]
        assert seen[0] <= 0.2, seen
        assert seen[-1] >= 0.95, seen
        steps = [b - a for a, b in zip(seen, seen[1:])]
        assert min(steps) >= -0.05 and max(steps) <= 0.3, seen
    finally:
        context.close()


# The search field's box in the window, its full height between its rounded ends (the map shows
# through the corners' edge pixels), and the app bar with no frosted layer.
FIELD_BOX = (
    "() => { const e = document.querySelector('.place-search__row'); const r = e.getBoundingClientRect();"
    " const end = Math.ceil(Math.min(parseFloat(getComputedStyle(e).borderTopLeftRadius), r.height / 2));"
    " return {x: r.left + end, y: r.top, width: r.width - 2 * end, height: r.height}; }")
NO_FROST = ".site-header::before { display: none !important; }"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN], ids=["390", "360"])
def test_in_a_safari_tab_the_frost_never_falls_on_the_search_field(
        new_context, make_app_server, viewport, theme):
    """the frosted layer lies above the search field, so it ends at the field's top edge: every
    pixel of the field, its top rows included, is drawn exactly as with no frost at all (a layer
    reaching into the field hazed its top, a pale veil over the dark theme's dark field)"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, viewport, color_scheme=theme)
    try:
        page.wait_for_function(AT_LEAD, arg=LEAD, timeout=5000)
        clip = page.evaluate(FIELD_BOX)
        frosted = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")
        page.add_style_tag(content=NO_FROST)
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.site-header'), '::before')"
            ".display === 'none'", timeout=5000)
        bare = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")
        high = max(band[1] for band in ImageChops.difference(frosted, bare).getextrema())
        assert high <= 2, (clip, high)
    finally:
        context.close()


# The map's own marks (the pin and the area circle) follow the theme; the band compared below is
# the app bar over the bare tiles.
NO_MARKS = (
    "#place-map .leaflet-overlay-pane, #place-map .leaflet-marker-pane,"
    " #place-map .leaflet-shadow-pane { visibility: hidden !important; }")
# The colour tokens the app bar's parts carry over the map (on the frame button, its frost's tint
# on the bar's backdrop layer), next to the page's own values.
BAR_TOKENS = (
    "() => { const names = ['--color-text', '--color-accent', '--color-border', '--color-status-ok',"
    " '--color-status-warn', '--color-status-error', '--glass-bg', '--glass-border',"
    " '--glass-highlight', '--glass-solid', '--shadow-glass'];"
    " const button = getComputedStyle(document.querySelector('.site-header .frame-menu__button'));"
    " const brand = getComputedStyle(document.querySelector('.site-header > .brand'));"
    " const frost = getComputedStyle(document.querySelector('.site-header'), '::before');"
    " const root = getComputedStyle(document.documentElement);"
    " const read = (s, list) => list.map((n) => n + ': ' + s.getPropertyValue(n).trim());"
    " return [read(button, names).concat(read(brand, ['--color-text', '--color-accent']),"
    "  read(frost, ['--color-canvas'])),"
    "  read(root, names).concat(read(root, ['--color-text', '--color-accent', '--color-canvas']))]; }")
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


def test_in_a_safari_tab_the_app_bar_over_the_map_is_drawn_the_same_in_both_themes(
        new_context, make_app_server):
    """the tiles are light in both themes, so the frosted app bar over them is too: in the dark
    theme the app bar (the frost, the logo, the wordmark and the frame button) is drawn exactly as
    in the light theme, with no turn to a dark tint behind it"""
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
    low, high = ImageChops.difference(bands["light"], bands["dark"]).convert("L").getextrema()
    assert high <= 2, (low, high)


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
def test_in_a_safari_tab_the_app_bar_reads_on_its_frost_in_both_themes(
        new_context, make_app_server, theme):
    """on the frosted band the wordmark and the frame button's name keep text contrast, and the
    logo the contrast of a graphic, against every pixel drawn behind them, in both themes (a light
    frost under the dark theme's light ink would not read)"""
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


def test_in_a_safari_tab_the_page_nudges_its_scroll_once_the_opening_splash_has_gone(
        new_context, make_app_server):
    """Safari's status bar keeps the look it took from the page at its last scroll, and the page
    scrolls past the lead while the opening splash still covers it (a dark splash in the dark
    theme left a grey veil under the clock): once the splash has gone, and not before, the page
    moves by one pixel for a moment and comes back to the lead"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, splash=True, color_scheme="dark")
    context.add_init_script(SAFARI_TAB)
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


def test_a_home_screen_app_and_a_wide_screen_have_no_lead(new_context, make_app_server):
    """a Home Screen web app draws under the status bar itself: no lead, nothing scrolled, the
    ground strip at the top edge as before; a wide screen in a Safari tab keeps its fixed map with
    no lead either"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_tab(new_context, server, VIEWPORT_PHONE, script=HOME_SCREEN_APP)
    try:
        state = page.evaluate(LEAD_STATE)
        assert not state["lead"] and state["scrollY"] == 0 and state["scrollMax"] <= 0, state
        assert state["mapTop"] == 0 and state["edge"] == "block", state
    finally:
        context.close()
    context, page = _open_tab(new_context, server, VIEWPORT_DESKTOP)
    try:
        state = page.evaluate(LEAD_STATE)
        assert state["position"] == "fixed" and state["scrollY"] == 0, state
        assert page.evaluate(
            "() => getComputedStyle(document.documentElement).getPropertyValue('--place-lead')"
        ).strip() == "", state
    finally:
        context.close()
