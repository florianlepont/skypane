#!/usr/bin/env python3
"""Browser checks for the map of the Location and detection page: tiles, the draggable pin and
its fields, the attribution, the failure modes (tile host down, library blocked) and the Referer
the tile host receives.

Both external hosts are answered by `page.route` (test-support/place_map_support.py): nothing
reaches the network. Waits are on the page's own state (`map-ready`, loaded tiles, settled
animations, a control owning its centre), never fixed sleeps; boxes are measured only after the
finite animations ended and the cross-document view transition is over.
"""
import pytest

from co_manager_browser_support import SUBPIXEL
from companion import auth, page_policy
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _set_ui_theme)
from place_map_support import (
    HIT_PROBE as _HIT_PROBE, MIN_PX, SETTLED as _SETTLED, Hosts, saved_place, seed as _seed,
    stored as _stored)

pytestmark = pytest.mark.browser

SAVE = "button.dirty-bar__save"
MAP = "#place-map"
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
# Finite animations and transitions are over; a never-ending one is not waited for.
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
NOTICE_SHOWN = "() => !document.getElementById('place-notice').hidden"
STATUS_HAS = "text => document.getElementById('place-status').textContent.includes(text)"
PIN_BOX = (
    "() => { const p = document.querySelector('#place-map .place-pin');"
    " if (!p) return null; const r = p.getBoundingClientRect();"
    " return {x: r.left + 22, y: r.top + 42, left: r.left, top: r.top}; }")


def _raised(errors):
    """The page's script errors, minus the browser's own note that a cross-document view
    transition was skipped (it comes from the stylesheet's opt-in, not from any script)."""
    return [e for e in errors if "ViewTransition" not in e]


def _wait_settled(page):
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)
    page.locator(MAP).scroll_into_view_if_needed()
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)


def _open(new_context, server, viewport, lang="en", theme=None, route="/detection",
          wait_tiles=True, **host_kwargs):
    context = new_context(viewport=viewport)
    hosts = Hosts(context, **host_kwargs)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    if wait_tiles:
        page.wait_for_function(TILES_LOADED, timeout=15000)
    if theme is not None:
        _set_ui_theme(page, theme)
    _wait_settled(page)
    return context, page, hosts, errors


def _map_box(page):
    return page.locator(MAP).bounding_box()


def _tap_map(page, fx, fy):
    box = _map_box(page)
    x, y = box["x"] + box["width"] * fx, box["y"] + box["height"] * fy
    page.mouse.click(x, y)
    return x, y


def _field(page, field_id):
    return page.locator("#" + field_id).input_value()


def _wait_pin(page, x, y):
    """The pin's tip sits at (x, y) once the marker is placed."""
    page.wait_for_function(
        "args => { const p = document.querySelector('#place-map .place-pin');"
        " if (!p) return false; const r = p.getBoundingClientRect();"
        " return Math.abs(r.left + 22 - args.x) < 3 && Math.abs(r.top + 42 - args.y) < 3; }",
        arg={"x": x, "y": y}, timeout=10000)


def _open_details(page):
    if not page.eval_on_selector("#details", "el => el.open"):
        page.click("#details > summary")
        page.wait_for_function("() => document.getElementById('details').open", timeout=5000)


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_tap_drops_the_pin_and_fills_the_fields_then_dragging_adjusts_them(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, errors = _open(new_context, server, viewport)
    try:
        if page.locator(MAP + " .place-pin").count():
            raise AssertionError("a pin shows before anything is chosen")
        x, y = _tap_map(page, 0.5, 0.55)
        _wait_pin(page, x, y)
        first = (_field(page, "place-lat"), _field(page, "place-lon"))
        if not first[0] or not first[1]:
            raise AssertionError("the fields stayed empty after a tap: %r" % (first,))
        if len(first[0].split(".")[1]) != 4:
            raise AssertionError("latitude is not rounded to 4 decimals: %r" % first[0])
        page.wait_for_function(STATUS_HAS, arg="Pin placed at %s, %s" % first, timeout=5000)
        pin = page.evaluate(PIN_BOX)
        page.mouse.move(pin["x"], pin["y"] - 10)
        page.mouse.down()
        page.mouse.move(pin["x"] + 50, pin["y"] - 10 + 30, steps=6)
        page.mouse.up()
        page.wait_for_function(
            "before => document.getElementById('place-lat').value !== before",
            arg=first[0], timeout=10000)
        _wait_pin(page, pin["x"] + 50, pin["y"] + 30)
        moved = (_field(page, "place-lat"), _field(page, "place-lon"))
        if moved == first:
            raise AssertionError("dragging did not change the fields")
        if hosts.image_requests:
            raise AssertionError("library images were requested: %r" % hosts.image_requests)
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


def test_typing_coordinates_moves_the_pin(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_details(page)
        page.fill("#place-lat", "45.7578")
        page.fill("#place-lon", "4.8320")
        page.wait_for_function(
            "() => { const p = document.querySelector('#place-map .place-pin');"
            " if (!p) return false;"
            " const m = document.getElementById('place-map').getBoundingClientRect();"
            " const r = p.getBoundingClientRect();"
            " return r.left > m.left && r.right < m.right && r.top > m.top && r.bottom < m.bottom; }",
            timeout=10000)
        if (_field(page, "place-lat"), _field(page, "place-lon")) != ("45.7578", "4.8320"):
            raise AssertionError("the typed fields were rewritten")
    finally:
        context.close()


def test_the_fields_start_tucked_away_and_a_saved_place_opens_pinned(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, route="/detection?airport=LFPG")
    try:
        if page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the coordinates card is open while the map runs")
        if not page.locator(MAP + " .place-pin").count():
            raise AssertionError("an airport page opens without its pin")
        if page.is_visible(".place-fallback"):
            raise AssertionError("the fallback explanation shows while the map runs")
        if abs(float(_field(page, "place-lat")) - 49.0097) > 0.01:
            raise AssertionError("the pin fields do not hold the airport")
    finally:
        context.close()


def test_the_attribution_is_visible_inside_the_map_and_links_to_the_copyright_page(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        link = page.locator(MAP + " .leaflet-control-attribution a")
        if not link.is_visible():
            raise AssertionError("the attribution is not visible")
        if link.inner_text().strip() != "© OpenStreetMap contributors":
            raise AssertionError("attribution reads %r" % link.inner_text())
        if link.get_attribute("href") != "https://www.openstreetmap.org/copyright":
            raise AssertionError("attribution links to %r" % link.get_attribute("href"))
        box, map_box = link.bounding_box(), _map_box(page)
        if not (box["x"] >= map_box["x"] and box["x"] + box["width"] <= map_box["x"] + map_box["width"]
                and box["y"] + box["height"] <= map_box["y"] + map_box["height"] + SUBPIXEL):
            raise AssertionError("the attribution leaves the map: %r in %r" % (box, map_box))
    finally:
        context.close()


def test_every_tile_request_carries_the_page_origin_as_referer(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        if not hosts.tile_requests:
            raise AssertionError("no tile was requested")
        expected = server.base_url().rstrip("/") + "/"
        bad = [(u, h.get("referer")) for u, h in hosts.tile_requests if h.get("referer") != expected]
        if bad:
            raise AssertionError("tile requests with a wrong Referer (want %r): %r" % (expected, bad[:3]))
        wrong_host = [u for u, _h in hosts.tile_requests
                      if not u.startswith("https://tile.openstreetmap.org/")]
        if wrong_host:
            raise AssertionError("a tile came from another host: %r" % wrong_host)
    finally:
        context.close()


def _assert_controls(page, width):
    failure = _assert_no_page_overflow(page, "/detection", width)
    if failure:
        raise AssertionError(failure)
    selectors = [
        MAP + " .leaflet-control-zoom-in", MAP + " .leaflet-control-zoom-out",
        "label.place-mode", ".place-about > summary", "#details > summary"]
    failures = page.evaluate(_HIT_PROBE, {"selectors": selectors, "min": MIN_PX - SUBPIXEL})
    if failures:
        raise AssertionError("controls too small or covered at %dpx: %r" % (width, failures))
    box = _map_box(page)
    if box["x"] < -SUBPIXEL or box["x"] + box["width"] > width + SUBPIXEL:
        raise AssertionError("the map leaves the viewport: %r" % box)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_map_page_layout_and_controls(new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, viewport, lang, theme)
    try:
        _assert_controls(page, viewport["width"])
        if lang == "fr" and page.locator(MAP + " .leaflet-control-attribution a").inner_text() != (
                "© contributeurs d’OpenStreetMap"):
            raise AssertionError("the attribution is not French")
    finally:
        context.close()


def _save_area_place(server, page):
    """Saving by the pin and the fields works after the map failed."""
    page.click("label.place-mode:has(#place-mode-area)")
    _open_details(page)
    page.fill("#place-label", "Test spot")
    with page.expect_navigation() as info:
        page.click(SAVE)
    if info.value.status != 200:
        raise AssertionError("save ended on HTTP %d" % info.value.status)
    return saved_place(server)


def test_with_the_tile_host_down_the_notice_shows_and_the_pin_still_saves(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, wait_tiles=False, tiles="abort")
    try:
        page.wait_for_function(NOTICE_SHOWN, timeout=15000)
        text = page.inner_text("#place-notice")
        if text != "The map pictures could not load. The pin and the coordinates still work.":
            raise AssertionError("the notice reads %r" % text)
        if not page.locator("#place-notice").evaluate("el => el.closest('.place-card') !== null"):
            raise AssertionError("the notice is outside the card")
        x, y = _tap_map(page, 0.45, 0.5)
        _wait_pin(page, x, y)
        place = _save_area_place(server, page)
        if place is None or place["name"] != "Test spot":
            raise AssertionError("the pin was not saved: %r" % (place,))
        if _stored(server)["mode"] != "position":
            raise AssertionError("mode not stored: %r" % (_stored(server),))
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


def test_with_the_library_blocked_the_plain_form_shows_and_saves(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    hosts = Hosts(context)
    context.route("**/static/vendor/leaflet/leaflet.js", lambda route: route.abort())
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    console = []
    page.on("console", lambda message: console.append(message) if message.type == "error" else None)
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.getElementById('place-map').hidden", timeout=10000)
        page.wait_for_function(_SETTLED, timeout=10000)
        if page.evaluate(READY):
            raise AssertionError("map-ready is set without the library")
        if not page.is_visible(".place-fallback"):
            raise AssertionError("the fallback explanation is hidden")
        if not page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the details card is closed")
        for hidden in ("form.place-search", "#place-locate", MAP):
            if page.is_visible(hidden):
                raise AssertionError("%s shows without the library" % hidden)
        page.fill("#place-lat", "48.8566")
        page.fill("#place-lon", "2.3522")
        page.fill("#place-label", "Plain form")
        page.click("label.place-mode:has(#place-mode-area)")
        with page.expect_navigation() as info:
            page.click(SAVE)
        if info.value.status != 200:
            raise AssertionError("save ended on HTTP %d" % info.value.status)
        place = saved_place(server)
        if place is None or place["name"] != "Plain form":
            raise AssertionError("the plain form did not save: %r" % (place,))
        own = [m.text for m in console if "leaflet.js" not in m.text and "ERR_" not in m.text
               and "Failed to load resource" not in m.text]
        if _raised(errors) or own:
            raise AssertionError("the page's own scripts raised %r %r" % (errors, own))
        if hosts.image_requests:
            raise AssertionError("library images were requested")
    finally:
        context.close()


def test_the_map_page_keeps_the_policy_headers_of_the_map_policy(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    Hosts(context)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        response = page.goto(server.base_url() + "/detection")
        headers = response.headers
        if headers.get("content-security-policy") != page_policy.MAP_CONTENT_SECURITY_POLICY:
            raise AssertionError("CSP is %r" % headers.get("content-security-policy"))
        if headers.get("permissions-policy") != page_policy.MAP_PERMISSIONS_POLICY:
            raise AssertionError("Permissions-Policy is %r" % headers.get("permissions-policy"))
    finally:
        context.close()

