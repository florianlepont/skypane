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
from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from server import airports, device_config, device_dirs, fleet_db, hardware

pytestmark = pytest.mark.browser

HOSTS = ("https://tile.openstreetmap.org/**", "https://nominatim.openstreetmap.org/**")
CDG = "LFPG"
CDG_RUNWAY = "08L/26R"
SAVE = "button.dirty-bar__save"
MIN_PX = 44

CARDS = (
    ".place-card--status", ".place-card--map", ".place-card--airports",
    ".place-card--follow", "#details")

# Whether the page is at rest and a known control owns its own centre.
_SETTLED = (
    "() => {"
    " if (document.getAnimations().some((a) => a.playState === 'running')) return false;"
    " const e = document.querySelector('#airport-filter');"
    " e.scrollIntoView({block: 'center'});"
    " const r = e.getBoundingClientRect();"
    " return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === e; }")

# For each selector, the first matching element is scrolled to the middle and measured; a control
# fails when it is smaller than the floor or something else owns its centre.
_HIT_PROBE = (
    "args => args.selectors.map((sel) => {"
    " const el = document.querySelector(sel);"
    " if (!el) return [sel, 'missing'];"
    " el.scrollIntoView({block: 'center'});"
    " const r = el.getBoundingClientRect();"
    " if (r.width < args.min || r.height < args.min) {"
    "   return [sel, 'size ' + r.width.toFixed(1) + 'x' + r.height.toFixed(1)]; }"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " if (!hit || !(el === hit || el.contains(hit) || hit.contains(el))) {"
    "   return [sel, 'covered by ' + (hit ? hit.tagName + '.' + hit.className : 'nothing')]; }"
    " return null; }).filter(Boolean)")

_BOX_PROBE = (
    "sels => Object.fromEntries(sels.map((sel) => {"
    " const r = document.querySelector(sel).getBoundingClientRect();"
    " return [sel, {top: r.top + window.scrollY, bottom: r.bottom + window.scrollY,"
    " left: r.left, right: r.right, width: r.width}]; }))")


def _seed(state_dir):
    session_cookie_for_state_dir(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        owner = fleet_db.get_user_by_email(conn, TEST_ADMIN_EMAIL)["id"]
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:04", "d" * 64, hardware.LEGACY_KEY, owner,
            name="Live frame", state_path=device_dirs.LIVE_STATE_PATH)
    finally:
        conn.close()


def _stored(server):
    return device_config.load_device_config(server.state_dir).get("detection")


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
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection?airport=" + _largest_airport().icao)
    page.locator("main").wait_for(state="visible")
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


def _hit_selectors(scripts_on):
    selectors = [
        "#airport-filter", "#airport-filter-submit", "a.place-airport__link",
        "label.runway-card", "#place-radius", "#place-lat", "#place-lon", "#place-label",
        "#place-timezone", "#details > summary", ".place-about > summary"]
    if scripts_on:
        selectors += ["#place-search", "form.place-search button", "#place-locate"]
    return selectors


def _assert_layout(page, width, scripts_on):
    failure = _assert_no_page_overflow(page, "/detection", width)
    if failure:
        raise AssertionError(failure)
    failures = page.evaluate(
        _HIT_PROBE, {"selectors": _hit_selectors(scripts_on), "min": MIN_PX - SUBPIXEL})
    if failures:
        raise AssertionError("controls too small or covered at %dpx: %r" % (width, failures))
    # Every runway and mode card, not only the first.
    sizes = page.evaluate(
        "() => [...document.querySelectorAll('label.runway-card, a.place-airport__link')]"
        ".map((e) => { const r = e.getBoundingClientRect(); return [r.width, r.height]; })")
    small = [s for s in sizes if s[0] < MIN_PX - SUBPIXEL or s[1] < MIN_PX - SUBPIXEL]
    if small:
        raise AssertionError("cards under 44 px at %dpx: %r" % (width, small[:3]))
    boxes = page.evaluate(_BOX_PROBE, list(CARDS))
    if width < 960:
        _assert_single_column(boxes, width)
    else:
        _assert_two_columns(boxes)


def _assert_single_column(boxes, width):
    tops = [boxes[sel]["top"] for sel in CARDS]
    if tops != sorted(tops):
        raise AssertionError("cards are out of order on a phone: %r" % tops)
    lefts = {round(boxes[sel]["left"]) for sel in CARDS}
    if len(lefts) != 1:
        raise AssertionError("the phone is not one column: lefts %r" % lefts)
    if max(boxes[sel]["right"] for sel in CARDS) > width + SUBPIXEL:
        raise AssertionError("a card leaves the viewport at %dpx" % width)


def _assert_two_columns(boxes):
    status, place = boxes[CARDS[0]], boxes[CARDS[1]]
    left_column = [boxes[sel] for sel in (CARDS[0], CARDS[2], CARDS[3], CARDS[4])]
    if len({round(b["left"]) for b in left_column}) != 1:
        raise AssertionError("the left column cards do not share a left edge")
    if abs(status["width"] - 384) > 2:
        raise AssertionError("the left column is %.1f px wide, expected 24rem" % status["width"])
    if place["left"] < status["right"] - SUBPIXEL:
        raise AssertionError("the place card is not in the right column")
    if abs(place["top"] - status["top"]) > 2:
        raise AssertionError("the place card does not start level with the status card")
    tops = [b["top"] for b in left_column]
    if tops != sorted(tops):
        raise AssertionError("the left column is out of order: %r" % tops)


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
