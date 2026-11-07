"""Real-browser proof of the frame button and its popover for an administrator who owns every
frame: the page kept across frames, the Add a frame row and the pairing flow it opens, Escape,
outside tap, focus return and aria state, geometry at 360, 390 and 1440 px in both languages and
themes (rows of 52px or more, inside the viewport, no layout shift when opening), the button
aligned with the page title on a desktop, the Console list with owner emails, and reduced motion."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from frame_menu_support import (
    ADD, BUTTON, FRAMES, MENU, MENU_IS_CLOSED, MENU_IS_OPEN, PANEL, ROW, SYSTEM,
    close_menu_with_escape, open_menu, wait_for_button)
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

ROW_FLOOR = 52
BUTTON_FLOOR = 44
VIEWPORT_WIDE = {"width": 1440, "height": 900}
VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, VIEWPORT_WIDE]
VIEWPORT_IDS = ["360", "390", "1440"]


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    # The fleet's owner is an administrator who owns every frame, so the
    # personal list holds all of them.
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
    if context_args.get("java_script_enabled", True):
        wait_for_button(page)
    return context, page


def _live_path(app, route):
    return "/devices/%s%s" % (app.fleet.live.id, route)


@pytest.mark.parametrize("route", ["/display", "/flights", "/"])
def test_choosing_a_row_keeps_the_page_for_the_other_frame(new_context, app, route):
    """on Personalisation, Flight history and Home the other frame's row goes to the same page
    of that frame, and the current row carries aria-current and the check"""
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, route), viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        current = page.locator('%s[aria-current="true"]' % FRAMES)
        assert current.count() == 1
        assert current.get_attribute("href") == _live_path(app, route)
        assert current.locator(".frame-row__check").count() == 1
        assert page.locator(FRAMES + " .frame-row__check").count() == 1
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s%s"]' % (FRAMES, other, route)).click()
        assert page.url.split("?")[0].endswith("/devices/%s%s" % (other, route))
        wait_for_button(page)
        open_menu(page)
        assert page.locator('%s[aria-current="true"]' % FRAMES).get_attribute(
            "href") == "/devices/%s%s" % (other, route)
    finally:
        context.close()


def test_the_add_row_is_last_and_opens_the_pairing_flow(new_context, app):
    """a user's popover (and an administrator's on a personal page) ends with an Add a frame
    row to the Add a frame page; on a Console page an administrator's leads to the Fleet
    pairing dialog"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        last = page.locator(MENU + " ul.frame-menu__list > li").last.locator("a")
        assert last.get_attribute("class").split() == ["frame-row", "frame-row--add"]
        assert last.inner_text().strip().endswith("Add a frame")
        assert page.locator(ADD).get_attribute("href") == "/pair-frame"
        page.goto(app.server.base_url() + "/fleet")
        open_menu(page)
        page.locator(ADD).click()
        page.wait_for_function(
            "() => document.querySelector('dialog#dlg-add-frame').open")
    finally:
        context.close()


def test_escape_closes_the_popover_and_focus_returns_to_the_button(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        button = page.locator(BUTTON)
        assert button.get_attribute("aria-haspopup") == "true"
        page.wait_for_function(
            "() => document.querySelector('%s').getAttribute('aria-expanded') === 'false'"
            % BUTTON)
        open_menu(page)
        page.wait_for_function(
            "() => document.querySelector('%s').getAttribute('aria-expanded') === 'true'"
            % BUTTON)
        page.locator(FRAMES).last.focus()
        close_menu_with_escape(page)
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('%s')" % BUTTON)
        page.wait_for_function(
            "() => document.querySelector('%s').getAttribute('aria-expanded') === 'false'"
            % BUTTON)
    finally:
        context.close()


def test_a_tap_outside_closes_the_popover(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        page.mouse.click(300, 700)
        page.wait_for_function(MENU_IS_CLOSED)
        page.locator(BUTTON).click()
        page.wait_for_function(MENU_IS_OPEN)
    finally:
        context.close()


def test_the_rows_are_reached_and_activated_with_the_keyboard(new_context, app):
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(BUTTON).focus()
        page.keyboard.press("Enter")
        page.wait_for_function(MENU_IS_OPEN)
        page.locator('%s[href="/devices/%s/display"]' % (FRAMES, other)).focus()
        page.wait_for_function(
            "() => document.activeElement.matches('ul.frame-menu__list a.frame-row')")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        assert page.url.endswith("/devices/%s/display" % other)
    finally:
        context.close()


def test_scripts_blocked_the_button_opens_and_a_row_still_navigates(new_context, app):
    """the popover is a native disclosure: with no script it opens and each row is a plain
    link to the same page of the other frame"""
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, "/flights"), viewport=VIEWPORT_MIN_SUPPORTED,
        java_script_enabled=False)
    try:
        page.locator(BUTTON).click()
        row = page.locator('%s[href="/devices/%s/flights"]' % (FRAMES, other))
        row.wait_for(state="visible")
        with page.expect_navigation():
            row.click()
        assert page.url.endswith("/devices/%s/flights" % other)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_geometry_no_overflow_and_no_layout_shift(new_context, app, viewport, scheme, lang):
    """the button is 44px high or more and sits in the top bar; opening the popover moves
    nothing and keeps it inside the viewport; every row (the Add row included) is 52px high or
    more; the page does not overflow sideways"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), lang=lang, viewport=viewport,
        color_scheme=scheme)
    try:
        before = page.evaluate(
            """() => ({height: document.documentElement.scrollHeight,
                       title: document.querySelector('h1').getBoundingClientRect().toJSON(),
                       button: document.querySelector('%s').getBoundingClientRect().toJSON()})"""
            % BUTTON)
        assert before["button"]["height"] >= BUTTON_FLOOR
        assert before["button"]["right"] <= viewport["width"]
        assert before["button"]["x"] >= 0
        open_menu(page)
        after = page.evaluate(
            """() => ({height: document.documentElement.scrollHeight,
                       title: document.querySelector('h1').getBoundingClientRect().toJSON(),
                       button: document.querySelector('%s').getBoundingClientRect().toJSON(),
                       panel: document.querySelector('%s').getBoundingClientRect().toJSON()})"""
            % (BUTTON, PANEL))
        assert after["height"] == before["height"]
        assert after["title"] == before["title"] and after["button"] == before["button"]
        assert after["panel"]["x"] >= 0 and after["panel"]["right"] <= viewport["width"]
        assert after["panel"]["width"] <= 300.5
        assert after["panel"]["y"] >= after["button"]["bottom"]
        for index in range(page.locator(ROW).count()):
            box = page.locator(ROW).nth(index).bounding_box()
            assert box["height"] >= ROW_FLOOR, (index, box)
        label = "Ajouter un cadre" if lang == "fr" else "Add a frame"
        assert page.locator(ADD).inner_text().strip().endswith(label)
        pic = page.locator(FRAMES + " .frame-row__pic").first.bounding_box()
        assert pic["width"] > 0 and pic["height"] > pic["width"]
        assert not _assert_no_page_overflow(
            page, "frame-menu/%s/%s" % (scheme, lang), viewport["width"])
    finally:
        context.close()


def test_on_a_desktop_the_button_is_level_with_the_page_title_and_clear_of_it(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/flights"), viewport=VIEWPORT_WIDE)
    try:
        boxes = page.evaluate(
            """() => {
              const range = document.createRange();
              range.selectNodeContents(document.querySelector('h1'));
              return {title: range.getBoundingClientRect().toJSON(),
                      button: document.querySelector('%s').getBoundingClientRect().toJSON()};
            }""" % BUTTON)
        title, button = boxes["title"], boxes["button"]
        assert abs((button["y"] + button["height"] / 2) - (title["y"] + title["height"] / 2)) <= 24
        assert button["x"] >= title["right"] or button["y"] >= title["bottom"]
    finally:
        context.close()


def test_the_personal_list_has_no_fleet_entry_system_row_or_owner_line(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        assert page.locator(MENU + ' a[href="/fleet"]').count() == 0
        assert page.locator(SYSTEM).count() == 0
        assert page.locator(".frame-row__note").count() == 0
    finally:
        context.close()


def test_a_console_popover_lists_every_frame_with_the_owner_email(new_context, app):
    context, page = _open(
        new_context, app, "/fleet", viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        fleet = app.fleet
        for device in (fleet.live, fleet.dev_a, fleet.dev_b, fleet.landscape):
            assert page.locator(
                '%s[href="/fleet?frame=%s"]' % (FRAMES, device.id)).count() == 1
        notes = page.locator(FRAMES + " .frame-row__note").all_inner_texts()
        assert notes and all("@" in note for note in notes)
    finally:
        context.close()


def test_reduced_motion_zeroes_the_entrance(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP,
        reduced_motion="reduce")
    try:
        open_menu(page)
        duration = page.locator(PANEL).evaluate(
            "(el) => parseFloat(getComputedStyle(el).animationDuration)")
        assert duration < 0.001
    finally:
        context.close()
