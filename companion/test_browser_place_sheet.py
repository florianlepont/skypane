#!/usr/bin/env python3
"""Browser checks for the Location sheet: My position is the first tab and the default for a frame
with nothing saved; on a phone the nearest-airport offer is a one-line button and the sheet stays within
28% of the viewport; Save and Cancel are a bar that appears on a change (the top right of the compact card above the
tab bar on a phone, under the card on a wide screen) and that saves or cancels; the pin readout
follows the pin; and the map runs behind the glass sidebar and the glass tab bar.

Both external hosts are answered by `page.route`; waits are on the page's own state, never fixed
sleeps.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login
from place_map_support import (
    CLEAR_BOX, SETTLED, Hosts, saved_place, seed as _seed, stored as _stored)
from server import airports

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
MAP = "#place-map"
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
# Finite animations and transitions are over; a never-ending one is not waited for.
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
BAR = ".place-panel > .dirty-bar"
SAVE = BAR + " button.dirty-bar__save"
CANCEL = BAR + " button.dirty-bar__cancel"
BAR_SHOWN = (
    "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
    " return !!b && !b.hidden && getComputedStyle(b).display !== 'none'"
    " && b.getBoundingClientRect().height > 0; }")
BAR_HIDDEN = (
    "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
    " return !!b && (b.hidden || getComputedStyle(b).display === 'none'); }")


def _open(new_context, server, viewport, lang="en", route="/detection"):
    """The Location page with both external hosts answered by the test, settled and at rest."""
    context = new_context(viewport=viewport)
    hosts = Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    return context, page, hosts, errors


def _tap_map(page, fx, fy):
    """Chooses My position, then clicks at the given fractions of the part of the map nothing
    floats over."""
    if not page.is_checked("#place-mode-area"):
        page.click("label.place-mode:has(#place-mode-area)")
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    box = page.evaluate(CLEAR_BOX)
    page.mouse.click(box["x"] + box["width"] * fx, box["y"] + box["height"] * fy)


def _airport_point(icao, north_km):
    airport = airports.find_airport(icao)
    return airport, "%.4f" % (airport.lat + north_km / 111.0), "%.4f" % airport.lon


def _wait_bar(page, shown):
    page.wait_for_function(BAR_SHOWN if shown else BAR_HIDDEN, timeout=5000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)


def test_my_position_is_the_first_tab_and_the_default_for_a_new_frame(new_context, make_app_server):
    """the switch lists My position before Airport, and a frame with no saved detection opens on
    My position; the airport tab is one tap away and `?mode=runway` still opens on it"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        labels = page.locator("label.place-mode").all_inner_texts()
        assert [text.strip() for text in labels] == ["My position", "Airport"]
        assert page.is_checked("#place-mode-area")
        page.click("label.place-mode:has(#place-mode-runway)")
        assert page.is_checked("#place-mode-runway")
        page.goto(server.base_url() + "/detection?mode=runway")
        page.wait_for_function(READY, timeout=15000)
        assert page.is_checked("#place-mode-runway")
    finally:
        context.close()


def test_a_saved_airport_still_opens_on_the_airport_tab(new_context, make_app_server):
    """a frame that follows a runway is shown as it is saved: the tab order changed, not the
    stored setting"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_DESKTOP, route="/detection?airport=LFPG")
    try:
        page.click(SAVE)
        page.wait_for_load_state("load")
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(READY, timeout=15000)
        assert page.is_checked("#place-mode-runway")
        assert [text.strip() for text in page.locator("label.place-mode").all_inner_texts()] == [
            "My position", "Airport"]
    finally:
        context.close()


def _pin_near_an_airport(page):
    airport, lat, lon = _airport_point("LFPG", 1.5)
    page.evaluate("() => { window.location.hash = 'details'; }")
    page.wait_for_function(
        "() => { const d = document.getElementById('details');"
        " return d.open && getComputedStyle(d).display !== 'none'; }", timeout=5000)
    page.fill("#place-lat", lat)
    page.fill("#place-lon", lon)
    page.wait_for_function(
        "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
    return airport


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_on_a_phone_the_airport_offer_is_one_line_and_the_sheet_stays_compact(
        new_context, make_app_server, viewport):
    """with a pin next to an airport the offer is a single 44px button line in the sheet (the
    sentence is spoken, not shown); the sheet stays within 28% of the viewport height, keeps the
    readout and the radius reachable, and does not rise over the pin; tapping the button follows
    the airport's runway"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, viewport)
    try:
        airport = _pin_near_an_airport(page)
        page.evaluate("() => { window.location.hash = 'place-map'; }")
        page.wait_for_function(
            "() => !document.getElementById('place-nearest').hidden", timeout=5000)
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        offer = page.locator("#place-nearest")
        assert offer.is_visible()
        button = page.locator("#place-nearest button")
        assert 43.5 <= button.bounding_box()["height"] <= 56
        assert offer.bounding_box()["height"] <= 56
        assert button.inner_text() == "Follow %s" % airport.name
        assert page.locator("#place-nearest .place-nearest__text").bounding_box()["width"] <= 1
        sheet = page.locator(".place-sheet").bounding_box()
        assert sheet["height"] <= viewport["height"] * 0.28 + 1, sheet
        pin = page.evaluate(
            "() => document.querySelector('#place-map .place-pin').getBoundingClientRect().toJSON()")
        assert pin["bottom"] <= sheet["y"] + 1, (pin, sheet)
        assert page.locator("#place-coords").is_visible()
        assert page.locator("#place-radius").is_visible()
        assert page.locator("#place-radius-range").is_visible()
        assert page.locator(".place-radius__scale").is_hidden()
        # The offer does not sit over the pin: it can still be grabbed and moved.
        # Grab only once the pin has stopped moving (a pan or marker rebuild may still be
        # settling on a loaded machine).
        page.wait_for_function(
            "() => { const r = document.querySelector('#place-map .place-pin')"
            ".getBoundingClientRect(); const k = Math.round(r.left) + ':' + Math.round(r.top);"
            " const same = window.__pinKey === k; window.__pinKey = k;"
            " window.__pinSame = same ? (window.__pinSame || 0) + 1 : 0;"
            " return window.__pinSame >= 8; }", polling=50, timeout=10000)
        grab = page.evaluate(
            "() => { const r = document.querySelector('#place-map .place-pin')"
            ".getBoundingClientRect(); return {x: r.left + 22, y: r.top + 32}; }")
        before = page.input_value("#place-lat")
        hit = page.evaluate(
            "p => !!document.elementFromPoint(p.x, p.y).closest('#place-map')", grab)
        assert hit, grab
        page.mouse.move(grab["x"], grab["y"])
        page.mouse.down()
        page.mouse.move(grab["x"] + 40, grab["y"] - 40, steps=6)
        page.mouse.up()
        page.wait_for_function(
            "before => document.getElementById('place-lat').value !== before", arg=before,
            timeout=10000)
        button.click()
        page.wait_for_function(
            "() => location.search.indexOf('airport=%s') >= 0" % airport.icao, timeout=10000)
    finally:
        context.close()


def test_on_a_wide_screen_my_position_offers_the_nearby_airport(new_context, make_app_server):
    """the offer is a card with the airport's name, the distance and a 44px button"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        airport = _pin_near_an_airport(page)
        page.wait_for_function(
            "() => !document.getElementById('place-nearest').hidden", timeout=5000)
        assert page.locator("#place-nearest").is_visible()
        assert airport.name in page.inner_text("#place-nearest")
        assert page.locator("#place-nearest button").bounding_box()["height"] >= 43.5
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_floating_bar_appears_on_a_change_saves_and_cancels(
        new_context, make_app_server, viewport):
    """the bar is hidden until something changes; a changed radius shows it (in the card above the tab bar on
    a phone, at the foot of the main column on a wide screen); Cancel hides it and
    restores the value; Save stores the place and the radius"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, viewport)
    try:
        _wait_bar(page, False)
        _tap_map(page, 0.5, 0.4)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
        _wait_bar(page, True)
        bar = page.locator(BAR).bounding_box()
        assert 0 <= bar["x"] and bar["x"] + bar["width"] <= viewport["width"] + 0.5, bar
        assert bar["y"] + bar["height"] <= viewport["height"] + 0.5, bar
        if viewport["width"] < 960:
            tab = page.locator(".tab-bar").bounding_box()
            sheet = page.locator(".place-sheet").bounding_box()
            assert bar["y"] >= sheet["y"] - 0.5, (bar, sheet)
            assert bar["y"] + bar["height"] <= sheet["y"] + sheet["height"] + 0.5, (bar, sheet)
            assert bar["x"] + bar["width"] <= sheet["x"] + sheet["width"] + 0.5, (bar, sheet)
            assert sheet["y"] + sheet["height"] <= tab["y"] + 0.5, (sheet, tab)
            assert tab["y"] - (sheet["y"] + sheet["height"]) <= 24, (sheet, tab)
        else:
            sidebar = page.locator(".dashboard-sidebar").bounding_box()
            assert bar["x"] >= sidebar["x"] + sidebar["width"], (bar, sidebar)
            assert viewport["height"] - (bar["y"] + bar["height"]) <= 32, bar
        for selector in (SAVE, CANCEL):
            box = page.locator(selector).bounding_box()
            assert box["height"] >= 43.5 and box["width"] >= 43.5, (selector, box)
        page.fill("#place-radius", "12")
        page.click(CANCEL)
        _wait_bar(page, False)
        assert page.input_value("#place-radius") == "9"
        _tap_map(page, 0.5, 0.4)
        _wait_bar(page, True)
        page.fill("#place-radius", "12")
        with page.expect_navigation():
            page.click(SAVE)
        assert _stored(server) == {"mode": "position", "radius_km": 12}
        assert saved_place(server) is not None
    finally:
        context.close()


def test_the_pin_readout_follows_the_pin_in_both_languages(new_context, make_app_server):
    """the readout shows the pin's coordinates (decimal comma in French) and what a tap does"""
    server = make_app_server(seed=_seed, fake_providers=True)
    for lang, hint, comma in (("en", "Tap the map to move it", False),
                              ("fr", "Touchez la carte pour le déplacer", True)):
        context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP, lang=lang)
        try:
            assert page.locator("#place-coords").is_hidden()
            assert page.locator("#place-tap-hint").is_visible()
            _tap_map(page, 0.5, 0.4)
            page.wait_for_function(
                "() => !document.getElementById('place-coords').hidden", timeout=5000)
            text = page.inner_text("#place-coords")
            assert (" N · " in text) and (("," in text) == comma), text
            assert page.inner_text("#place-move-hint") == hint
            assert page.locator("#place-tap-hint").is_hidden()
        finally:
            context.close()


def test_the_map_runs_behind_the_glass_sidebar_on_a_wide_screen(new_context, make_app_server):
    """the map is the whole window, the sidebar sits above it as frosted glass, and a point inside
    the sidebar belongs to the sidebar, not to the map"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        box = page.locator(MAP).bounding_box()
        assert box["x"] == 0 and box["y"] == 0
        assert box["width"] == VIEWPORT_DESKTOP["width"] and box["height"] == VIEWPORT_DESKTOP["height"]
        side = page.locator(".dashboard-sidebar").bounding_box()
        assert side["x"] > 0 and side["width"] > 100
        probe = page.evaluate(
            "s => { const el = document.elementFromPoint(s.x + s.width / 2, s.y + s.height - 40);"
            " const side = document.querySelector('.dashboard-sidebar');"
            " const cs = getComputedStyle(side);"
            " return {owned: !!el && side.contains(el), filter: cs.backdropFilter,"
            "         alpha: cs.backgroundColor}; }", side)
        assert probe["owned"], probe
        assert "blur" in probe["filter"], probe
        assert probe["alpha"] != "rgb(255, 255, 255)" and probe["alpha"] != "rgba(255, 255, 255, 1)"
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        assert page.locator(".place-search").bounding_box()["x"] >= side["x"] + side["width"] - 1
    finally:
        context.close()


def test_the_map_runs_behind_the_opaque_tab_bar_on_a_phone(new_context, make_app_server):
    """the map reaches past the top and the bottom of the window, the tab bar floats over it as
    one opaque surface (a solid fill, no blur) and the sheet and the bar sit above the tab bar"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_PHONE)
    try:
        box = page.locator(MAP).bounding_box()
        assert box["y"] < 0 and box["y"] + box["height"] > VIEWPORT_PHONE["height"], box
        tab = page.locator(".tab-bar").bounding_box()
        assert box["y"] + box["height"] >= tab["y"] + tab["height"]
        fill = page.evaluate(
            "() => { const t = document.querySelector('.tab-bar');"
            " return {solid: getComputedStyle(t).backgroundColor,"
            "         glass: getComputedStyle(t, '::before').backdropFilter}; }")
        assert fill["solid"].startswith("rgb("), fill
        assert fill["glass"] in ("none", ""), fill
        sheet = page.locator(".place-sheet").bounding_box()
        assert sheet["y"] + sheet["height"] <= tab["y"] + 0.5, (sheet, tab)
        assert page.evaluate(
            "() => { const t = document.querySelector('.tab-bar').getBoundingClientRect();"
            " const el = document.elementFromPoint(t.left + t.width / 2, t.top + 4);"
            " return !!el && !!el.closest('.tab-bar'); }")
    finally:
        context.close()


def test_without_scripts_save_stays_a_plain_button_in_the_page(new_context, make_app_server):
    """scripts blocked: the bar is shown with a normal Save button that posts the form; nothing is
    hidden"""
    from companion.test_browser_ux_helpers import _no_js_page

    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/detection?airport=LFPG",
                     viewport=VIEWPORT_DESKTOP) as page:
        assert page.locator(BAR).is_visible()
        assert page.locator(SAVE).is_visible()
        assert page.locator(BAR).evaluate("e => getComputedStyle(e).position") == "fixed"
        with page.expect_navigation() as info:
            page.click(SAVE)
        assert info.value.status == 200
    assert _stored(server)["mode"] == "runway"
