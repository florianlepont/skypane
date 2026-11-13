#!/usr/bin/env python3
"""Browser checks for the Location page's first moments and its airport pick: the map really is
full-bleed on a phone (no pale band above or below it), a designed loading state shows from the
first paint with scripts on and never the plain form, the plain form stays complete with scripts
blocked, and choosing an airport moves the page in place without a navigation.

Both external map hosts are answered by `page.route`; waits are on the page's own state.
"""
import os

import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login, _no_js_page
from place_map_support import PAGE_OVERFLOW, SETTLED, Hosts, seed as _seed
from server import airports, device_config

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_MIN = {"width": 360, "height": 740}
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
SHOTS = os.environ.get("PLACE_BOOT_SHOTS", "")

# What shows of the plain form and of the loading state.
VISIBLE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect(); const s = getComputedStyle(el);"
    " return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; }")
PLAIN_FORM_VISIBLE = (
    "() => ['.place-fallback', '.place-airports', '#airport-filter', '#place-lat']"
    ".some((sel) => { const el = document.querySelector(sel);"
    " return !!el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().width > 0; })")
# The page's own position in history and a marker that a reload would erase.
MARK = "() => { window.__stays = 'same document'; }"


def _seed_position(state_dir):
    """The shared one-frame seed, with a stored My-position setting of 7 km."""
    _seed(state_dir)
    device_config.save_device_config(state_dir, detection={"mode": "position", "radius_km": 7})


def _context(new_context, server, viewport, lang="en", **options):
    context = new_context(viewport=viewport, **options)
    hosts = Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    return context, hosts


def _open_ready(new_context, server, viewport, route="/detection", lang="en", **options):
    context, hosts = _context(new_context, server, viewport, lang, **options)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page, hosts


def _hold_the_map_script(context):
    """Answers the page's own map script with nothing, so the page stays in its loading state."""
    context.route("**/static/place-map.js*", lambda route: route.fulfill(
        status=200, content_type="text/javascript", body="/* held */"))


def _shot(page, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, name + ".png"))


# Full-bleed on a phone.

@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN])
def test_the_map_covers_the_whole_phone_viewport_with_no_pale_band(
        new_context, make_app_server, viewport, theme):
    """the map runs from the top edge to the bottom edge and from side to side (under the status
    bar area, the tab bar and the bottom safe area); the page behind it is the theme's secondary surface,
    nothing but the map runs past the window and the document cannot be scrolled by hand, and the
    pixels at the bottom corners and the top row are map"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open_ready(
        new_context, server, viewport, color_scheme=theme)
    try:
        box = page.evaluate(
            "() => { const r = document.getElementById('place-map').getBoundingClientRect();"
            " return {top: r.top, left: r.left, right: r.right, bottom: r.bottom,"
            " w: innerWidth, h: innerHeight}; }")
        assert box["top"] <= 0 and box["left"] <= 0, box
        assert box["right"] >= box["w"] and box["bottom"] >= box["h"], box
        covers = page.evaluate(
            "() => [[2, 1], [innerWidth - 3, 1], [2, innerHeight - 2], [innerWidth - 3, innerHeight - 2],"
            " [innerWidth / 2, innerHeight - 1]].map(([x, y]) => document.elementsFromPoint(x, y)"
            ".some((el) => el.id === 'place-map' || !!el.closest('#place-map')))")
        assert all(covers), covers
        page_colours = page.evaluate(
            "() => { const map = getComputedStyle(document.getElementById('place-map'));"
            " const html = getComputedStyle(document.documentElement);"
            " return {map: map.backgroundColor, html: html.backgroundColor, image: html.backgroundImage,"
            " overflow: html.overflow}; }")
        # The page behind the map is the theme's secondary surface (a placeholder colour, never
        # the sky); the fixed map box itself shows the tile ground colour.
        assert page_colours["map"] == "rgb(242, 239, 233)", page_colours
        assert page_colours["html"] == page.evaluate(
            "() => { const p = document.createElement('i'); p.style.color = 'var(--color-secondary)';"
            " document.body.appendChild(p); const c = getComputedStyle(p).color; p.remove(); return c; }"
        ), page_colours
        assert page_colours["image"] == "none", page_colours
        assert page_colours["overflow"] == "hidden", page_colours
        assert page.evaluate(PAGE_OVERFLOW) <= 0
        # The picture itself: the bottom-corner pixels are the map's tile colour, like its middle.
        png = page.screenshot()
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(png)).convert("RGB")
        width, height = image.size
        # A page band would paint the page's sky colours; the corners are map (tiles and a tab bar's
        # shadow), never one of those.
        sky = page.evaluate(
            "() => ['--sky-top', '--sky-mid', '--sky-bottom'].map((name) => {"
            " const probe = document.createElement('i'); probe.style.color = 'var(' + name + ')';"
            " document.body.appendChild(probe); const c = getComputedStyle(probe).color;"
            " probe.remove(); return c.match(/\\d+/g).slice(0, 3).map(Number); })")
        for corner in ((2, height - 2), (width - 3, height - 2), (2, height - 6)):
            pixel = image.getpixel(corner)
            for colour in sky:
                assert max(abs(a - b) for a, b in zip(pixel, colour)) > 15, (corner, pixel, sky)
        _shot(page, "phone_full_bleed_%s_%d" % (theme, viewport["width"]))
    finally:
        context.close()


# The loading state.

@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP])
def test_a_designed_loading_state_shows_at_first_paint_instead_of_the_plain_form(
        new_context, make_app_server, viewport, theme):
    """with scripts on and the map not ready yet, the loading state (progress bar, shapes of the
    search field and the sheet, the loading note) shows and nothing of the plain form does"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, _hosts = _context(new_context, server, viewport, color_scheme=theme)
    _hold_the_map_script(context)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection", wait_until="domcontentloaded")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert page.evaluate(VISIBLE, ".place-boot")
        for part in (".place-boot__progress", ".place-boot__search", ".place-boot__sheet",
                     ".place-boot__note"):
            assert page.evaluate(VISIBLE, part), part
        assert "Loading the map" in page.inner_text(".place-boot__note")
        assert not page.evaluate(PLAIN_FORM_VISIBLE), "the plain form shows with scripts on"
        assert not page.evaluate("() => document.documentElement.classList.contains('map-ready')")
        finite = page.evaluate(
            "() => document.getAnimations().filter((a) => a.effect.getComputedTiming().iterations"
            " === Infinity).length")
        assert finite == 0
        _shot(page, "loading_%s_%d" % (theme, viewport["width"]))
    finally:
        context.close()


def test_the_loading_state_is_gone_once_the_map_is_ready(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open_ready(new_context, server, VIEWPORT_PHONE)
    try:
        assert not page.evaluate(VISIBLE, ".place-boot")
        assert page.evaluate(VISIBLE, "#place-search")
        assert not page.evaluate(PLAIN_FORM_VISIBLE)
        _shot(page, "loaded_phone")
    finally:
        context.close()


def test_the_loading_state_is_server_rendered_in_french(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, _hosts = _context(new_context, server, VIEWPORT_PHONE, lang="fr")
    _hold_the_map_script(context)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection", wait_until="domcontentloaded")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert "Chargement de la carte" in page.inner_text(".place-boot__note")
    finally:
        context.close()


def test_the_plain_form_is_complete_and_the_loading_state_absent_with_scripts_blocked(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/detection?mode=runway", viewport=VIEWPORT_PHONE) as page:
        assert not page.evaluate(VISIBLE, ".place-boot")
        assert page.evaluate(VISIBLE, ".place-fallback")
        assert page.evaluate(VISIBLE, "#airport-filter")
        assert page.evaluate(VISIBLE, "#place-lat")


def test_the_plain_form_returns_when_the_map_script_never_reports_ready(
        new_context, make_app_server):
    """the loading state is capped: with a script that never answers, the plain form shows
    after the cap instead of a loading state that never ends"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, _hosts = _context(new_context, server, VIEWPORT_PHONE)
    _hold_the_map_script(context)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(PLAIN_FORM_VISIBLE, timeout=15000)
        assert not page.evaluate(VISIBLE, ".place-boot")
    finally:
        context.close()


# Choosing an airport in place.

def _count_navigations(page):
    """Every document request of the page after this call: a navigation or a reload. A
    same-document address change (history.replaceState) is not one."""
    seen = []
    page.on("request", lambda request: seen.append(request.url)
            if request.resource_type == "document" else None)
    return seen


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP])
def test_picking_an_airport_from_the_suggestions_updates_the_page_in_place(
        new_context, make_app_server, viewport):
    """no navigation and no reload: the document survives, the loading state does not come back,
    the map moves to the airport, the runway cards, the pin fields, the mode and the address
    follow, and Save appears with the saved result unchanged until it is pressed"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open_ready(new_context, server, viewport, route="/detection?mode=runway")
    try:
        page.evaluate(MARK)
        navigations = _count_navigations(page)
        boots = page.evaluate(
            "() => { window.__boot = 0; new MutationObserver(() => {"
            " if (getComputedStyle(document.querySelector('.place-boot')).display !== 'none')"
            " window.__boot += 1; }).observe(document.documentElement, {attributes: true,"
            " subtree: true}); return 0; }")
        assert boots == 0
        page.fill("#place-search", "orly")
        page.wait_for_function("() => !document.getElementById('place-results').hidden", timeout=5000)
        page.locator("#place-results button, #place-results [role=option]").first.click()
        page.wait_for_function(
            "() => document.querySelector(\"input[name='airport'][form]\").value === 'LFPO'",
            timeout=10000)
        orly = airports.find_airport("LFPO")
        page.wait_for_function(
            "() => document.querySelectorAll('.place-sheet label.runway-card').length > 0",
            timeout=5000)
        assert page.evaluate("() => window.__stays") == "same document"
        assert navigations == []
        assert page.evaluate("() => window.__boot") == 0
        assert page.is_checked("#place-mode-runway")
        assert orly.name in page.inner_text(".place-chosen")
        cards = page.locator(".place-sheet label.runway-card").count()
        assert cards == len(orly.runways)
        assert page.is_checked("input[name=runway]:checked") or page.locator(
            "input[name=runway]:checked").count() == 1
        assert page.input_value("#place-label") == orly.name
        assert abs(float(page.input_value("#place-lat")) - orly.lat) < 0.001
        page.wait_for_function(
            "() => location.search.indexOf('airport=LFPO') >= 0 && location.search.indexOf('mode=runway') >= 0",
            timeout=5000)
        assert page.evaluate(VISIBLE, "#place-search")
        page.wait_for_function(
            "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
            " return !!b && !b.hidden; }", timeout=5000)
        page.wait_for_function(
            "(lat) => { const m = document.querySelector('#place-map .place-pin');"
            " return !!m; }", arg=orly.lat, timeout=5000)
        _shot(page, "picked_%d" % viewport["width"])
    finally:
        context.close()


def test_tapping_an_airport_pin_picks_it_in_place(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open_ready(
        new_context, server, VIEWPORT_DESKTOP, route="/detection?mode=runway")
    try:
        page.evaluate(MARK)
        navigations = _count_navigations(page)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length >= 1", timeout=10000)
        dot = page.evaluate(
            "() => { const lit = [...document.querySelectorAll('#place-map .place-dot')]"
            ".map((d) => [d, d.getBoundingClientRect()]).filter(([d, r]) => {"
            " const card = document.querySelector('.place-card').getBoundingClientRect();"
            " return r.left > card.right + 20 && r.top > 80 && r.bottom < innerHeight - 20"
            " && r.right < innerWidth - 20 && !d.classList.contains('place-dot--selected')"
            " && !!d.querySelector('.place-dot__mark'); });"
            " if (!lit.length) return null; const r = lit[0][1];"
            " return {x: r.left + r.width / 2, y: r.top + r.height / 2}; }")
        if dot is None:
            page.click(".place-france")
            page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
            # The pins are redrawn when the zoom ends: wait until they stop changing.
            page.wait_for_function(
                "() => { const key = [...document.querySelectorAll('#place-map .place-dot')]"
                ".map((d) => { const r = d.getBoundingClientRect(); return r.left + ',' + r.top; })"
                ".join(';'); const same = window.__dotKey === key;"
                " window.__dotKey = key; window.__dotSteady = same ? (window.__dotSteady || 0) + 1 : 0;"
                " return key !== '' && window.__dotSteady >= 6; }", polling=100, timeout=10000)
            dot = page.evaluate(
                "() => { const r = [...document.querySelectorAll('#place-map .place-dot')]"
                ".filter((d) => !d.classList.contains('place-dot--selected'))"
                ".map((d) => d.getBoundingClientRect()).find((r) => r.left > 450 && r.top > 80"
                " && r.bottom < innerHeight - 20 && r.right < innerWidth - 20);"
                " return r ? {x: r.left + r.width / 2, y: r.top + r.height / 2} : null; }")
        assert dot is not None
        before = page.input_value("input[name=airport][form]")
        page.mouse.click(dot["x"], dot["y"])
        page.wait_for_function(
            "(was) => document.querySelector(\"input[name='airport'][form]\").value !== was",
            arg=before, timeout=10000)
        assert page.evaluate("() => window.__stays") == "same document"
        assert navigations == []
        assert page.is_checked("#place-mode-runway")
        page.wait_for_function("() => location.search.indexOf('airport=') >= 0", timeout=5000)
    finally:
        context.close()


def test_a_failed_airport_fetch_falls_back_to_the_pages_own_navigation(
        new_context, make_app_server):
    """if the page cannot be updated in place the pick still lands: the old navigation runs"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open_ready(
        new_context, server, VIEWPORT_DESKTOP, route="/detection?mode=runway")
    try:
        context.route("**/detection?airport=LFPO*", lambda route: (
            route.fulfill(status=500, content_type="text/plain", body="no")
            if route.request.resource_type == "fetch" else route.continue_()))
        page.fill("#place-search", "orly")
        page.wait_for_function("() => !document.getElementById('place-results').hidden", timeout=5000)
        with page.expect_navigation():
            page.locator("#place-results button, #place-results [role=option]").first.click()
    finally:
        context.close()


def test_an_in_place_pick_keeps_the_typed_radius_and_cancel_puts_the_page_back(
        new_context, make_app_server):
    """the radius typed before the pick stays, the leave guard is armed (a real leave prompts),
    and Cancel restores the opened state in place: stored mode and radius, no airport cards, the
    opened address, still the same document"""
    server = make_app_server(seed=_seed_position, fake_providers=True)
    context, page, _hosts = _open_ready(new_context, server, VIEWPORT_DESKTOP)
    try:
        opened = page.url
        page.evaluate(MARK)
        navigations = _count_navigations(page)
        page.click("label.place-mode:has(#place-mode-area)")
        page.fill("#place-radius", "12")
        page.click("label.place-mode:has(#place-mode-runway)")
        page.fill("#place-search", "cdg")
        page.press("#place-search", "Enter")
        page.wait_for_function(
            "() => document.querySelectorAll('.place-sheet label.runway-card').length > 0",
            timeout=10000)
        assert page.input_value("#place-radius") == "12"
        page.wait_for_function("() => location.search.indexOf('radius_km=12') >= 0", timeout=5000)
        assert page.is_visible("button.dirty-bar__cancel")
        page.click("button.dirty-bar__cancel")
        page.wait_for_function(
            "() => document.querySelectorAll('.place-sheet label.runway-card').length === 0",
            timeout=10000)
        assert page.input_value("#place-radius") == "7"
        assert page.is_checked("#place-mode-area")
        page.wait_for_function("(url) => location.href === url", arg=opened, timeout=5000)
        assert page.evaluate("() => window.__stays") == "same document"
        assert navigations == []
    finally:
        context.close()
