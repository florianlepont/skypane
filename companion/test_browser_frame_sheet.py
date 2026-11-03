"""Real-browser proof of the frame chip and card sheet: keyboard behaviour, the
page kept across frames, the no-script hash path, geometry at 360 and 1280 px
in both languages and themes, and the personal and Console lists of an
administrator."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

CHIP = "a.frame-chip"
SHEET = "dialog.frame-sheet"
CARDS = "dialog.frame-sheet a.frame-card"
CARD_FLOOR = 64
CLOSE_FLOOR = 44


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    # The fleet's owner is an administrator who owns every frame, so the
    # personal sheet lists all of them.
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, lang="en", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    page.locator(CHIP).wait_for(state="visible")
    return context, page


def _wait_open(page):
    page.wait_for_function("() => document.querySelector('dialog.frame-sheet').open")


def _wait_closed(page):
    page.wait_for_function("() => !document.querySelector('dialog.frame-sheet').open")


def _live_path(app, route):
    return "/devices/%s%s" % (app.fleet.live.id, route)


def test_tab_stays_inside_the_sheet_and_escape_returns_focus_to_the_chip(new_context, app):
    """the sheet opens with focus inside it, Tab never leaves it, Escape closes it and focus
    returns to the chip"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(CHIP).click()
        _wait_open(page)
        page.wait_for_function(
            "() => document.querySelector('dialog.frame-sheet').contains(document.activeElement)")
        for _ in range(12):
            page.keyboard.press("Tab")
            # The rest of the page is inert: focus is in the sheet, or on the
            # body while it wraps round, never on page content.
            page.wait_for_function(
                "() => { const a = document.activeElement;"
                " return a === document.body || a === document.documentElement"
                " || document.querySelector('dialog.frame-sheet').contains(a); }")
        page.keyboard.press("Escape")
        _wait_closed(page)
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('a.frame-chip')")
    finally:
        context.close()


@pytest.mark.parametrize("route", ["/display", "/flights", "/"])
def test_choosing_a_card_keeps_the_page_for_the_other_frame(new_context, app, route):
    """on Personalisation, Flight history and Home the other frame's card goes to the same
    page of that frame, and the current card carries aria-current"""
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, route), viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(CHIP).click()
        _wait_open(page)
        current = page.locator('%s[aria-current="true"]' % CARDS)
        assert current.count() == 1
        assert current.get_attribute("href") == _live_path(app, route)
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s%s"]' % (CARDS, other, route)).click()
        assert page.url.split("?")[0].endswith("/devices/%s%s" % (other, route))
        page.locator(CHIP).wait_for(state="visible")
    finally:
        context.close()


def test_no_script_hash_link_shows_the_sheet_and_a_card_navigates(new_context, app):
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, "/flights"), viewport=VIEWPORT_MIN_SUPPORTED,
        java_script_enabled=False)
    try:
        page.locator(CHIP).click()
        card = page.locator('%s[href="/devices/%s/flights"]' % (CARDS, other))
        card.wait_for(state="visible")
        with page.expect_navigation():
            card.click()
        assert page.url.endswith("/devices/%s/flights" % other)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_geometry_and_no_overflow(new_context, app, viewport, scheme, lang):
    """cards are at least 64px high, the close control at least 44x44, and neither the page
    nor the sheet overflows horizontally; below 700px the sheet is a bottom sheet"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), lang=lang, viewport=viewport,
        color_scheme=scheme)
    try:
        chip = page.locator(CHIP).bounding_box()
        assert chip["height"] >= 48
        if viewport["width"] >= 700:
            assert chip["width"] <= 24 * 16 + 1
        page.locator(CHIP).click()
        _wait_open(page)
        for index in range(page.locator(CARDS).count()):
            assert page.locator(CARDS).nth(index).bounding_box()["height"] >= CARD_FLOOR
        close = page.locator(SHEET + " a.modal__close").bounding_box()
        assert close["width"] >= CLOSE_FLOOR and close["height"] >= CLOSE_FLOOR
        box = page.locator(SHEET).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        if viewport["width"] < 700:
            assert box["y"] + box["height"] >= viewport["height"] - 1
        scroll = page.evaluate(
            "() => { const d = document.querySelector('dialog.frame-sheet');"
            " return d.scrollWidth - d.clientWidth; }")
        assert scroll <= 0
        assert not _assert_no_page_overflow(page, "sheet/%s/%s" % (scheme, lang), viewport["width"])
    finally:
        context.close()


def test_the_personal_sheet_of_an_administrator_has_no_fleet_entry(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(CHIP).click()
        _wait_open(page)
        assert page.locator(SHEET + ' a[href="/fleet"]').count() == 0
        assert page.locator(SHEET).get_by_text("All frames").count() == 0
        assert page.locator(SHEET + ' a[href="/account#account-frames"]').count() == 1
    finally:
        context.close()


def test_a_console_sheet_lists_every_frame_with_the_owner_email(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/health"), viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(CHIP).click()
        _wait_open(page)
        fleet = app.fleet
        for device in (fleet.live, fleet.dev_a, fleet.dev_b, fleet.landscape):
            assert page.locator(
                '%s[href="/devices/%s/health"]' % (CARDS, device.id)).count() == 1
        notes = page.locator(CARDS + " .frame-card__note").all_inner_texts()
        assert notes and all("@" in note for note in notes)
    finally:
        context.close()
