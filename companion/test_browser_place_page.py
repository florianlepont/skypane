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
from companion.pages import place_page
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _no_js_page, _set_ui_theme)
from place_map_support import (
    HIT_PROBE as _HIT_PROBE, MIN_PX, SETTLED as _SETTLED, Hosts, open_details, seed as _seed,
    stored as _stored)
from server import airports

pytestmark = pytest.mark.browser

HOSTS = ("https://tile.openstreetmap.org/**", "https://nominatim.openstreetmap.org/**")
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_SHORT = {"width": 360, "height": 640}
VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_SHORT, VIEWPORT_PHONE, VIEWPORT_DESKTOP]
VIEWPORT_IDS = ["360", "360x640", "390", "1280"]
CDG = "LFPG"
CDG_RUNWAY = "08L/26R"
SAVE = "button.dirty-bar__save"

AREA_MODE = "label.place-mode:has(#place-mode-area)"
AIRPORT_MODE = "label.place-mode:has(#place-mode-runway)"
PARTS = (".place-stage", ".place-float", ".place-panel", "#place-map", ".place-sheet",
         ".place-modes", ".place-card")

_BOX_PROBE = (
    "sels => Object.fromEntries(sels.map((sel) => {"
    " const r = document.querySelector(sel).getBoundingClientRect();"
    " return [sel, {top: r.top + window.scrollY, bottom: r.bottom + window.scrollY,"
    " left: r.left, right: r.right, width: r.width, height: r.height}]; }))")


def _settle(page, scripts_on=True):
    """Wait until the animations have finished and the filter field owns its centre. A
    scripts-blocked page cannot run `wait_for_function`, so it is polled with `evaluate`."""
    page.locator("#place-search" if scripts_on else "#airport-filter").scroll_into_view_if_needed()
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
        page.goto(server.base_url() + "/detection?mode=runway")
        if not page.is_visible(".place-fallback"):
            raise AssertionError("the no-script explanation is not shown")
        if not page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the details card is closed")
        # Without a script the list opens on the first airports only; the
        # search field reaches the others.
        if page.locator("a.place-airport__link").count() != place_page.NOSCRIPT_AIRPORTS:
            raise AssertionError("the no-script list is not the short one")
        page.fill("#airport-filter", "roissy")
        with page.expect_navigation():
            page.click("#airport-filter-submit")
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


# The text of each segment and chip is centred in its box, within a pixel.
_CENTRING = (
    "() => [...document.querySelectorAll('.place-mode')].map((l) => {"
    " const t = l.querySelector('.place-mode__text'); const r = document.createRange();"
    " r.selectNodeContents(t); const a = r.getBoundingClientRect(); const b = l.getBoundingClientRect();"
    " return [Math.abs((a.left + a.right) / 2 - (b.left + b.right) / 2),"
    "        Math.abs((a.top + a.bottom) / 2 - (b.top + b.bottom) / 2)]; })")


def _assert_layout(page, width, scripts_on, height=None):
    failure = _assert_no_page_overflow(page, "/detection", width)
    if failure:
        raise AssertionError(failure)
    _choose_mode(page, AIRPORT_MODE, "place-mode-runway")
    selectors = ["label.place-mode", "label.runway-card"]
    if scripts_on:
        selectors += ["#place-search", "form.place-search button", "#place-info", "#place-locate"]
        if width >= 960:
            selectors += ["#place-map .leaflet-control-zoom-in"]
    else:
        selectors += ["#airport-filter", "#airport-filter-submit", "a.place-airport__link",
                      "#details > summary"]
    _probe(page, selectors, width)
    off = [o for o in page.evaluate(_CENTRING) if o[0] > 1 or o[1] > 1]
    if off:
        raise AssertionError("a mode label is off centre at %dpx: %r" % (width, off))
    sizes = page.evaluate(
        "() => [...document.querySelectorAll('label.place-mode, label.runway-card')]"
        ".map((e) => { const r = e.getBoundingClientRect(); return [r.width, r.height]; })")
    small = [s for s in sizes if s[0] < MIN_PX - SUBPIXEL or s[1] < MIN_PX - SUBPIXEL]
    if small:
        raise AssertionError("cards under 44 px at %dpx: %r" % (width, small[:3]))
    boxes = page.evaluate(_BOX_PROBE, list(PARTS))
    if not scripts_on:
        _assert_plain_column(boxes, width)
    elif width < 960:
        _assert_sheet(page, boxes, width, height)
    else:
        _assert_card(page, boxes)
    # My position mode: the radius and, with the coordinates card up, the place fields.
    _choose_mode(page, AREA_MODE, "place-mode-area")
    if scripts_on:
        open_details(page)
    _probe(page, ["#place-radius", "#place-lat", "#place-lon", "#place-label", "#place-timezone"]
           if scripts_on else ["#place-radius", "#place-lat", "#place-lon", "#place-label",
                               "#place-timezone"], width)


def _assert_plain_column(boxes, width):
    stage, panel = boxes[".place-stage"], boxes[".place-panel"]
    if panel["right"] > width + SUBPIXEL or panel["left"] < -SUBPIXEL:
        raise AssertionError("the plain form is not inside the viewport: %r" % boxes)
    if panel["top"] < stage["top"] - SUBPIXEL:
        raise AssertionError("the panel starts above the page: %r" % boxes)


def _assert_sheet(page, boxes, width, height):
    stage, float_box, panel, map_box = (boxes[sel] for sel in PARTS[:4])
    sheet, modes = boxes[".place-sheet"], boxes[".place-modes"]
    if abs(map_box["width"] - stage["width"]) > 2 or abs(map_box["height"] - stage["height"]) > 2:
        raise AssertionError("the map does not fill the stage: %r" % boxes)
    if abs(stage["width"] - width) > 1:
        raise AssertionError("the map is not edge to edge: %r" % boxes)
    if stage["top"] > SUBPIXEL:
        raise AssertionError("the map does not run under the status bar and app bar: %r" % boxes)
    header = page.evaluate(
        "() => document.querySelector('.site-header').getBoundingClientRect().bottom")
    if float_box["top"] < header - SUBPIXEL or float_box["bottom"] > modes["top"] + SUBPIXEL:
        raise AssertionError("the search field is not between the app bar and the chips: %r" % boxes)
    if modes["bottom"] > sheet["top"] + SUBPIXEL:
        raise AssertionError("the chips run into the sheet: %r" % boxes)
    gutter = 12
    if abs(sheet["width"] - (stage["width"] - 2 * gutter)) > 2:
        raise AssertionError("the sheet is not as wide as the map less its gutters: %r" % boxes)
    if sheet["height"] > height * 0.28 + 1:
        raise AssertionError("the sheet covers more than 28%% of the viewport: %r" % boxes)
    if panel["bottom"] > height + SUBPIXEL:
        raise AssertionError("the sheet is cut by the viewport foot: %r" % boxes)
    if page.evaluate("() => document.documentElement.scrollHeight") > height + 1:
        raise AssertionError("the page scrolls: the map does not fit between the bars")
    bar = page.evaluate(
        "() => { const t = document.querySelector('.tab-bar'); return t ? t.getBoundingClientRect().top : null; }")
    save_bar = page.evaluate(
        "() => { const b = document.querySelector('.place-panel > .dirty-bar');"
        " if (!b || b.hidden) return null; const r = b.getBoundingClientRect();"
        " return {top: r.top, bottom: r.bottom}; }")
    # The unsaved-changes actions are part of the card, so the card alone floats above the tab bar.
    if bar is not None and (sheet["bottom"] > bar + SUBPIXEL or bar - sheet["bottom"] > 24):
        raise AssertionError("the sheet does not float just above the bars: %r vs %r" % (sheet, bar))
    if save_bar and not (
            save_bar["top"] >= sheet["top"] - SUBPIXEL and save_bar["bottom"] <= sheet["bottom"] + SUBPIXEL):
        raise AssertionError("the save bar is not inside the sheet: %r vs %r" % (save_bar, sheet))
    if bar is not None and stage["bottom"] < height - SUBPIXEL:
        raise AssertionError("the map does not run under the tab bar: %r vs %r" % (stage, bar))
    tops = page.evaluate(
        "() => [...document.querySelectorAll('.place-sheet label.runway-card')].slice(0, 3)"
        ".map((c) => Math.round(c.getBoundingClientRect().top))")
    if len(tops) != 3 or max(tops) - min(tops) > 2:
        raise AssertionError("the runway cards are not three to a row: %r" % tops)
    tall = page.evaluate(
        "() => [...document.querySelectorAll('.place-sheet label.runway-card')]"
        ".map((c) => c.getBoundingClientRect().height).filter((h) => h > 72)")
    if tall:
        raise AssertionError("runway chips taller than 72 px: %r" % tall)
    covered = page.evaluate(
        "() => { const s = document.querySelector('.place-sheet'); const b = s.scrollHeight - s.clientHeight;"
        " return b; }")
    save = page.evaluate(
        "() => { const b = document.querySelector('.dirty-bar__save'); if (!b) return 'missing';"
        " const r = b.getBoundingClientRect(); return r.bottom <= window.innerHeight + 1; }")
    if covered > 0 and save is False:
        raise AssertionError("Save is cut off by the viewport")


def _assert_card(page, boxes):
    stage, float_box, panel, map_box = (boxes[sel] for sel in PARTS[:4])
    card, modes = boxes[".place-card"], boxes[".place-modes"]
    viewport = page.viewport_size
    if abs(map_box["height"] - stage["height"]) > 2 or map_box["left"] > 1 or (
            abs(map_box["width"] - viewport["width"]) > 1):
        raise AssertionError("the map is not the whole window: %r" % boxes)
    if stage["height"] < viewport["height"] - 2:
        raise AssertionError("the map is not the full height: %r" % boxes)
    if abs(card["width"] - 400) > 2 or abs(float_box["width"] - 400) > 2:
        raise AssertionError("card %.1f / search %.1f px wide, expected 400" % (
            card["width"], float_box["width"]))
    if round(card["left"]) != round(float_box["left"]):
        raise AssertionError("the search field is not above the card: %r" % boxes)
    if float_box["bottom"] > card["top"] - 4:
        raise AssertionError("the search field is not separate from the card: %r" % boxes)
    if not (card["left"] <= modes["left"] and modes["right"] <= card["right"]
            and card["top"] <= modes["top"]):
        raise AssertionError("the mode switch is not inside the card: %r" % boxes)
    if map_box["right"] - card["right"] < 300:
        raise AssertionError("the card leaves too little of the map: %r" % boxes)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_layout_and_hit_targets(new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        _assert_layout(page, viewport["width"], True, viewport["height"])
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_layout_without_scripts(new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    route = "/detection?airport=" + _largest_airport().icao
    with _no_js_page(new_context, server.base_url(), route, viewport=viewport) as page:
        _settle(page, scripts_on=False)
        _assert_layout(page, viewport["width"], False, viewport["height"])
        if page.is_visible("#place-map") or page.is_visible("form.place-search"):
            raise AssertionError("script-only controls show without scripts")


@pytest.mark.parametrize("viewport", [VIEWPORT_SHORT, VIEWPORT_PHONE], ids=["360x640", "390"])
def test_the_bottom_sheet_clears_the_floating_tab_bar(new_context, make_app_server, viewport):
    """On a phone the sheet ends above the floating tab bar, and the sheet's own scroll end
    shows its last control above the bar: the bar never covers the save action."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport)
    try:
        page.evaluate(
            "() => { const s = document.querySelector('.place-sheet'); s.scrollTop = s.scrollHeight; }")
        page.wait_for_function(
            "() => { const s = document.querySelector('.place-sheet');"
            " return s.scrollTop + s.clientHeight >= s.scrollHeight - 1; }")
        boxes = page.evaluate(
            "() => ({sheet: document.querySelector('.place-sheet').getBoundingClientRect().bottom,"
            " bar: document.querySelector('.tab-bar').getBoundingClientRect().top,"
            " last: [...document.querySelectorAll('.place-sheet *')]"
            "   .filter(e => e.getBoundingClientRect().height > 0)"
            "   .reduce((m, e) => Math.max(m, e.getBoundingClientRect().bottom), 0)})")
        assert boxes["sheet"] <= boxes["bar"] + 0.5, boxes
        assert boxes["last"] <= boxes["bar"] + 0.5, boxes
    finally:
        context.close()
