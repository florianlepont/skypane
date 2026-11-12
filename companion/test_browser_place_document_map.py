#!/usr/bin/env python3
"""Browser checks that, on a phone, the Location map is document content rather than a fixed layer:
the page container is exactly the largest viewport tall, the map sits inside it from the top edge to
the bottom edge, nothing scrolls, and the header, search, chips, offer, sheet and tab bar stay where
they were. Pinch and pan (wheel and drag), the pin drag and the loading state keep working.

Both external hosts are answered by `page.route`; waits are on the page's own state.
"""
import io

import pytest
from PIL import Image

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login
from place_map_support import CLEAR_BOX, SETTLED, Hosts, seed as _seed

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


# What sits at the top edge of the phone Location page, as in the build whose iPhone status bar
# showed the map with no band and no veil: one fixed box in the tile ground colour touching the
# edge, the body and the map in that colour, the page element's surface colour and the
# browser-chrome colours of the two theme-color tags.
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
