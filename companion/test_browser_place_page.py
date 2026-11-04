#!/usr/bin/env python3
"""Browser checks for the Location and detection page: the scripts-blocked save with both
external map hosts aborted, and the measured layout (card order, two columns from 960 px, no
sideways scroll, 44 px hit targets) at 360 and 1280 px in English and French, light and dark.

Boxes are measured only after the entrance animations have finished and the page owns its own
controls: right after a navigation a cross-document view transition is still running and
`elementFromPoint` answers the root element.
"""
import time

import pytest

from co_manager_browser_support import SUBPIXEL
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _no_js_page, _set_ui_theme)
from place_map_support import (
    HIT_PROBE as _HIT_PROBE, MIN_PX, SETTLED as _SETTLED, Hosts, seed as _seed, stored as _stored)
from server import airports

pytestmark = pytest.mark.browser

HOSTS = ("https://tile.openstreetmap.org/**", "https://nominatim.openstreetmap.org/**")
CDG = "LFPG"
CDG_RUNWAY = "08L/26R"
SAVE = "button.dirty-bar__save"

AREA_MODE = "label.place-mode:has(#place-mode-area)"
AIRPORT_MODE = "label.place-mode:has(#place-mode-runway)"
PARTS = (".place-stage", ".place-float", ".place-panel", "#place-map")

_BOX_PROBE = (
    "sels => Object.fromEntries(sels.map((sel) => {"
    " const r = document.querySelector(sel).getBoundingClientRect();"
    " return [sel, {top: r.top + window.scrollY, bottom: r.bottom + window.scrollY,"
    " left: r.left, right: r.right, width: r.width, height: r.height}]; }))")


def _settle(page, scripts_on=True):
    """Wait until the animations have finished and the filter field owns its centre. A
    scripts-blocked page cannot run `wait_for_function`, so it is polled with `evaluate`."""
    page.locator("#airport-filter").scroll_into_view_if_needed()
    if scripts_on:
        page.wait_for_function(_SETTLED, timeout=10000)
        return
    deadline = time.monotonic() + 10
    while not page.evaluate(_SETTLED):
        if time.monotonic() > deadline:
            raise AssertionError("the page did not settle")
        page.wait_for_timeout(50)


def _open(new_context, server, viewport, lang="en", theme=None):
    context = new_context(viewport=viewport)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection?airport=" + _largest_airport().icao)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    if theme is not None:
        _set_ui_theme(page, theme)
    _settle(page)
    return context, page


def _largest_airport():
    return max(airports.load_catalogue().values(), key=lambda a: len(a.runways))


def test_no_script_save_with_both_external_hosts_aborted(new_context, make_app_server):
    """Scripts blocked and the tile and search hosts aborted: the page loads, the fallback
    explanation and the open details card show, a list airport navigates with `?airport=`, and
    Save stores the choice and shows the saved toast. Nothing asks for either host."""
    server = make_app_server(seed=_seed, fake_providers=True)
    requested = []
    context = new_context(java_script_enabled=False, viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        for pattern in HOSTS:
            context.route(pattern, lambda route: (requested.append(route.request.url), route.abort()))
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        if not page.is_visible(".place-fallback"):
            raise AssertionError("the no-script explanation is not shown")
        if not page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the details card is closed")
        with page.expect_navigation():
            page.click("a.place-airport__link[data-icao=%s]" % CDG)
        if "airport=%s" % CDG not in page.url:
            raise AssertionError("the airport link landed on %s" % page.url)
        page.click("label.runway-card:has(input[value='%s'])" % CDG_RUNWAY)
        with page.expect_navigation() as info:
            page.click(SAVE)
        if info.value.status != 200:
            raise AssertionError("save ended on HTTP %d" % info.value.status)
        airport = airports.find_airport(CDG)
        if "Detection now follows %s" % airport.name not in page.inner_text("body"):
            raise AssertionError("the saved toast does not name the airport")
    finally:
        context.close()
    if requested:
        raise AssertionError("the page asked for an external host: %r" % requested)
    expected = {"mode": "runway", "airport": CDG, "runway": CDG_RUNWAY}
    if _stored(server) != expected:
        raise AssertionError("disk holds %r" % (_stored(server),))


def _choose_mode(page, label, control):
    page.click(label)
    if not page.is_checked("#" + control):
        raise AssertionError("%s was not chosen" % control)


def _probe(page, selectors, width):
    failures = page.evaluate(_HIT_PROBE, {"selectors": selectors, "min": MIN_PX - SUBPIXEL})
    if failures:
        raise AssertionError("controls too small or covered at %dpx: %r" % (width, failures))


def _assert_layout(page, width, scripts_on):
    failure = _assert_no_page_overflow(page, "/detection", width)
    if failure:
        raise AssertionError(failure)
    # Airport mode: the mode switch, the airport filter (the list shows while the filter has
    # focus), the runway cards, the credits and the coordinates summary.
    _choose_mode(page, AIRPORT_MODE, "place-mode-runway")
    if scripts_on:
        page.click(".place-more > summary")
        page.wait_for_function("() => document.querySelector('.place-more').open", timeout=5000)
    page.focus("#airport-filter")
    selectors = [
        "label.place-mode", "#airport-filter", "#airport-filter-submit", "a.place-airport__link",
        "label.runway-card", "#details > summary", ".place-about > summary"]
    if scripts_on:
        selectors += ["#place-search", "form.place-search button", "#place-locate"]
    _probe(page, selectors, width)
    sizes = page.evaluate(
        "() => [...document.querySelectorAll('label.place-mode, label.runway-card,"
        " a.place-airport__link')].map((e) => { const r = e.getBoundingClientRect();"
        " return [r.width, r.height]; })")
    small = [s for s in sizes if s[0] < MIN_PX - SUBPIXEL or s[1] < MIN_PX - SUBPIXEL]
    if small:
        raise AssertionError("cards under 44 px at %dpx: %r" % (width, small[:3]))
    # My position mode: the radius and, with the coordinates opened, the place fields.
    _choose_mode(page, AREA_MODE, "place-mode-area")
    if scripts_on:
        page.click("#details > summary")
        page.wait_for_function("() => document.getElementById('details').open", timeout=5000)
    _probe(page, ["#place-radius", "#place-lat", "#place-lon", "#place-label", "#place-timezone"],
           width)
    boxes = page.evaluate(_BOX_PROBE, list(PARTS))
    if not scripts_on:
        _assert_plain_column(boxes, width)
    elif width < 960:
        _assert_sheet(boxes, width)
    else:
        _assert_card(boxes)


def _assert_plain_column(boxes, width):
    float_box, panel = boxes[".place-float"], boxes[".place-panel"]
    if float_box["bottom"] > panel["top"] + SUBPIXEL:
        raise AssertionError("the panel is not below the mode switch: %r" % boxes)
    if round(float_box["left"]) != round(panel["left"]) or panel["right"] > width + SUBPIXEL:
        raise AssertionError("the plain form is not one column inside the viewport: %r" % boxes)


def _assert_sheet(boxes, width):
    stage, float_box, panel, map_box = (boxes[sel] for sel in PARTS)
    if abs(map_box["width"] - stage["width"]) > 2 or abs(map_box["height"] - stage["height"]) > 2:
        raise AssertionError("the map does not fill the stage: %r" % boxes)
    if float_box["top"] < stage["top"] - SUBPIXEL or float_box["bottom"] > panel["top"] + SUBPIXEL:
        raise AssertionError("the controls do not float above the sheet: %r" % boxes)
    if abs(panel["bottom"] - stage["bottom"]) > 2 or abs(panel["width"] - stage["width"]) > 2:
        raise AssertionError("the sheet is not docked at the foot of the map: %r" % boxes)
    if panel["height"] > stage["height"] * 0.5:
        raise AssertionError("the sheet covers more than half of the map: %r" % boxes)
    if stage["right"] > width + SUBPIXEL:
        raise AssertionError("the map leaves the viewport at %dpx" % width)


def _assert_card(boxes):
    stage, float_box, panel, map_box = (boxes[sel] for sel in PARTS)
    if abs(map_box["width"] - stage["width"]) > 2 or abs(map_box["height"] - stage["height"]) > 2:
        raise AssertionError("the map does not fill the stage: %r" % boxes)
    if abs(panel["width"] - 384) > 2 or abs(float_box["width"] - 384) > 2:
        raise AssertionError("the card is %.1f px wide, expected 24rem" % panel["width"])
    if round(panel["left"]) != round(float_box["left"]) or panel["left"] > stage["left"] + 32:
        raise AssertionError("the card is not at the left of the map: %r" % boxes)
    if float_box["bottom"] > panel["top"] + SUBPIXEL:
        raise AssertionError("the mode switch is not at the top of the card: %r" % boxes)
    if map_box["right"] - panel["right"] < 300:
        raise AssertionError("the card leaves too little of the map: %r" % boxes)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_layout_and_hit_targets(new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        _assert_layout(page, viewport["width"], True)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_layout_without_scripts(new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    route = "/detection?airport=" + _largest_airport().icao
    with _no_js_page(new_context, server.base_url(), route, viewport=viewport) as page:
        _settle(page, scripts_on=False)
        _assert_layout(page, viewport["width"], False)
        if page.is_visible("#place-map") or page.is_visible("form.place-search"):
            raise AssertionError("script-only controls show without scripts")
