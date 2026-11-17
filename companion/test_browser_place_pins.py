#!/usr/bin/env python3
"""Browser checks for the airport pins, the tap-to-place hint and the typed suggestions of the
Location and detection page, with both external hosts answered by `page.route`
(test-support/place_map_support.py): a fresh page draws a tappable pin for every airport of
the catalogue and tapping one selects it; My position mode draws none and a tap places the
pin; typing lists airports from the page's own catalogue without any request, a submitted
address is looked up once and listed, and the list is a keyboard-operable listbox."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login)
from place_map_support import (
    CLEAR_BOX, SETTLED as _SETTLED, Hosts, saved_place, seed as _seed, stored)
from server import airports

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
IDLE = (
    "() => document.getAnimations().every((a) => a.playState !== 'running'"
    " || a.effect.getComputedTiming().iterations === Infinity)")
SEARCH = "#place-search"
OPTIONS = "#place-results button[role='option']"
AREA = "label.place-mode:has(#place-mode-area)"
# A pin whose own hit box owns its centre and lies in the part of the map nothing floats over.
CLEAR_PIN = (
    "() => { const c = (" + CLEAR_BOX + ")(); "
    "const own = document.querySelector('input[name=airport][form]').value;"
    "for (const d of document.querySelectorAll('#place-map .place-dot')) {"
    " const r = d.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;"
    " const mark = d.querySelector('.place-dot__mark');"
    " if (mark.dataset.icao !== own && x > c.x + 30 && x < c.x + c.width - 30 && y > c.y + 30"
    " && y < c.y + c.height - 30 && d.contains(document.elementFromPoint(x, y)))"
    "  return {icao: mark.dataset.icao, x: x, y: y, w: r.width, h: r.height}; }"
    " return null; }")


def _open(new_context, server, viewport=PHONE, lang="en", route="/detection", **host_kwargs):
    context = new_context(viewport=viewport)
    hosts = Hosts(context, **host_kwargs)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES, timeout=15000)
    page.wait_for_function(IDLE, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)
    return context, page, hosts


def test_a_fresh_page_draws_tappable_pins_and_tapping_one_selects_it(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server, route="/detection?mode=runway")
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length >= 1", timeout=10000)
        sizes = page.evaluate(
            "() => [...document.querySelectorAll('#place-map .place-dot')]"
            ".map((d) => { const m = d.querySelector('.place-dot__mark').getBoundingClientRect();"
            " const h = d.getBoundingClientRect(); return [m.width, m.height, h.width, h.height]; })")
        assert all(s[0] >= 10 and s[1] >= 10 for s in sizes), "a pin mark is not drawn round"
        assert all(s[2] >= 44 and s[3] >= 44 for s in sizes), "a pin hit box is under 44 px"
        # The map opens on the frame's own airport; zoomed out, isolated airports stay pins.
        page.click(".place-france")
        page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_function(CLEAR_PIN, timeout=10000)
        pin = page.evaluate(CLEAR_PIN)
        with page.expect_navigation():
            page.mouse.click(pin["x"], pin["y"])
        page.wait_for_function(READY, timeout=15000)
        assert "airport=%s" % pin["icao"] in page.url, page.url
        chosen = airports.find_airport(pin["icao"])
        assert page.is_checked("#place-mode-runway")
        assert page.input_value("input[name=airport][form]") == chosen.icao
        assert chosen.name in page.inner_text(".place-chosen")
        assert page.locator(".place-sheet label.runway-card").count() == len(chosen.runways)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-dot--selected')", timeout=5000)
        assert not hosts.search_requests
    finally:
        context.close()


@pytest.mark.parametrize("lang,hint", [("en", "Tap the map to place"),
                                       ("fr", "Touchez la carte pour placer le point")])
def test_my_position_draws_no_pins_shows_a_hint_and_a_tap_places_the_pin(
        new_context, make_app_server, lang, hint):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        page.click(AREA)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length === 0", timeout=5000)
        page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_function(
            "h => document.getElementById('place-tap-hint').getBoundingClientRect().height > 0"
            " && document.getElementById('place-tap-hint').textContent === h", arg=hint, timeout=5000)
        assert not _assert_no_page_overflow(page, "/detection", 360)
        box = page.evaluate(CLEAR_BOX)
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')"
            " && !!document.querySelector('#place-map .place-circle')", timeout=5000)
        assert page.input_value("#place-lat") and page.input_value("#place-lon")
        page.wait_for_function("() => document.getElementById('place-tap-hint').hidden", timeout=5000)
    finally:
        context.close()


def test_typing_lists_airports_without_any_request_and_the_keyboard_picks_one(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.click(SEARCH)
        page.keyboard.type("ory")
        page.wait_for_function(
            "() => document.querySelectorAll(\"#place-results button[role='option']\").length >= 1",
            timeout=5000)
        first = page.locator(OPTIONS).first
        assert "Paris-Orly" in first.inner_text()
        assert first.bounding_box()["height"] >= 52 - 1
        assert page.locator(OPTIONS).count() <= 6
        assert page.get_attribute(SEARCH, "role") == "combobox"
        assert page.get_attribute(SEARCH, "aria-expanded") == "true"
        assert page.get_attribute("#place-results ul", "role") == "listbox"
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            "() => document.getElementById('place-search').getAttribute('aria-activedescendant')"
            " === document.querySelector(\"#place-results [aria-selected='true']\").id", timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_function("() => document.getElementById('place-results').hidden", timeout=5000)
        assert page.get_attribute(SEARCH, "aria-expanded") == "false"
        page.keyboard.press("ArrowDown")
        page.wait_for_function("() => !document.getElementById('place-results').hidden", timeout=5000)
        page.keyboard.press("ArrowDown")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        page.wait_for_function(READY, timeout=15000)
        assert "airport=LFPO" in page.url, page.url
        # The airport list itself never asks the geocoder; only the place suggestions that follow
        # a typing pause do (a slow machine can reach it), and then only for what was typed.
        assert all("q=ory" in url for url, _headers in hosts.search_requests), hosts.search_requests
    finally:
        context.close()


def test_a_submitted_address_is_looked_up_once_listed_and_chosen_as_the_position(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server, PHONE, "fr")
    try:
        page.fill(SEARCH, "Lyon")
        page.wait_for_function(
            "() => document.querySelectorAll(\"#place-results button[role='option']\").length >= 1",
            timeout=5000)
        assert not hosts.search_requests, "a request left while typing"
        page.press(SEARCH, "Enter")
        page.wait_for_function(
            "() => [...document.querySelectorAll('#place-results .place-result__name')]"
            ".some((e) => e.textContent === 'Rue de Rivoli')", timeout=10000)
        assert len(hosts.search_requests) == 1
        assert page.locator(OPTIONS).count() == 2
        page.locator(OPTIONS).nth(1).click()
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')"
            " && document.getElementById('place-mode-area').checked", timeout=10000)
        assert abs(float(page.input_value("#place-lat")) - 45.7578) < 0.001
        assert page.evaluate("() => document.getElementById('place-results').hidden")
    finally:
        context.close()


def test_the_map_runs_under_an_app_bar_with_no_backdrop_of_its_own(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, PHONE)
    try:
        top = page.evaluate("() => document.getElementById('place-map').getBoundingClientRect().top")
        bar = page.evaluate("() => document.querySelector('.site-header').getBoundingClientRect()")
        assert top <= 0.5 and bar["height"] > 40, (top, bar)
        backdrop = page.evaluate(
            "() => { const s = getComputedStyle(document.querySelector('.site-header'), '::before');"
            " return [s.content, s.backgroundImage]; }")
        assert backdrop == ["none", "none"], backdrop
    finally:
        context.close()


# --- My position after an airport pick ----------------------------------------------

SAVE = "button.dirty-bar__save"
STATUS_IS = "text => document.getElementById('place-status').textContent === text"
STATUS_LACKS = "text => !document.getElementById('place-status').textContent.includes(text)"


@pytest.mark.parametrize("lang,follows", [
    ("en", "Detection now follows the area within"),
    ("fr", "La détection suit désormais la zone dans un rayon de")])
def test_my_position_after_an_airport_pick_stops_naming_the_airport(
        new_context, make_app_server, lang, follows):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, lang=lang, route="/detection?mode=runway")
    try:
        page.click(".place-france")
        page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_function(CLEAR_PIN, timeout=10000)
        dot = page.evaluate(CLEAR_PIN)
        chosen = airports.find_airport(dot["icao"])
        page.mouse.click(dot["x"], dot["y"])
        page.wait_for_function(STATUS_IS, arg=chosen.name, timeout=10000)
        page.wait_for_function(
            "name => document.getElementById('place-label').value === name", arg=chosen.name,
            timeout=5000)
        page.click(AREA)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length === 0", timeout=5000)
        page.wait_for_function(STATUS_LACKS, arg=chosen.name, timeout=5000)
        page.wait_for_function(IDLE, timeout=10000)
        before = page.input_value("#place-lat")
        box = page.evaluate(CLEAR_BOX)
        page.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
        page.wait_for_function(
            "v => document.getElementById('place-lat').value !== v", arg=before, timeout=5000)
        page.wait_for_function(STATUS_LACKS, arg=chosen.name, timeout=5000)
        page.locator(SAVE).wait_for(state="visible", timeout=5000)
        with page.expect_navigation():
            page.click(SAVE)
        page.wait_for_function(READY, timeout=15000)
        page.wait_for_function(
            "text => [...document.querySelectorAll('.toast')]"
            ".some((t) => t.textContent.includes(text))", arg=follows, timeout=5000)
        toast = " ".join(page.locator(".toast").all_text_contents())
        assert follows in toast, toast
        assert chosen.name not in toast, toast
    finally:
        context.close()
    assert stored(server)["mode"] == "position"
    assert saved_place(server)["name"] != chosen.name
