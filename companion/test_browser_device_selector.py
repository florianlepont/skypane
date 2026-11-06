"""Real-browser checks of the frame button for plain users: a user with two frames switches
frame from Display and stays on Display, a one-frame user sees the button with only the Add a
frame row, the popover fits at 360px and 1280px in both languages and colour schemes with 44px
targets and a check on the current row, and it works with scripts blocked."""
import os
from types import SimpleNamespace

import pytest
from companion_app_server import session_cookie_for_state_dir
from frame_menu_support import ADD, BUTTON, FRAMES, ROW, open_menu, wait_for_button
from skypane_two_device_fleet import sim_hardware_env

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)
from companion.test_device_helpers import start_fleet_app
from server import device_dirs, fleet_db, hardware

pytestmark = pytest.mark.browser

HIT_FLOOR = 44
ROW_FLOOR = 52
MULTI_EMAIL = "multi@example.test"
SINGLE_EMAIL = "single@example.test"


def _add_user_frames(state_dir, email, names):
    """A plain user owning one simulated frame per name; returns the ids."""
    ids = []
    conn = fleet_db.connect(state_dir)
    try:
        with sim_hardware_env(), fleet_db.transaction(conn):
            user_id = fleet_db.add_user(conn, email, "user")
            for index, name in enumerate(names):
                mac = "aa:bb:cc:ee:%02x:%02x" % (len(email), 0x20 + index)
                device_id = fleet_db.add_device(
                    conn, mac, "f" * 64, hardware.SIM_CLONE_KEY, user_id, name=name,
                    state_path="auto")
                profile = hardware.get_profile(hardware.SIM_CLONE_KEY, os.environ)
                device_dirs.provision_device_dir(
                    state_dir, device_id, profile.width, profile.height, fill=0)
                ids.append(device_id)
    finally:
        conn.close()
    return SimpleNamespace(ids=ids)


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    holder = {}

    def seed_extra(fleet):
        root = fleet.live.state_dir
        holder["multi"] = _add_user_frames(root, MULTI_EMAIL, ["Alpha", "Bravo"])
        holder["single"] = _add_user_frames(root, SINGLE_EMAIL, ["Solo"])

    app = start_fleet_app(module_app_server_factory, seed_extra=seed_extra)
    app.multi, app.single = holder["multi"], holder["single"]
    return app


def _open(new_context, app, email, route, lang="en", role="user", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    pair = session_cookie_for_state_dir(app.server.state_dir, email, role)
    name, value = pair.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + route)
    page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        wait_for_button(page)
    return context, page


def test_a_user_switches_frame_from_display_and_stays_on_display(new_context, fleet_app):
    """choosing the other frame's row on Display lands on that frame's Display, where the
    other frame's row is now the current one"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        assert page.locator(FRAMES).count() == 2
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s/display"]' % (FRAMES, second)).click()
        assert page.url.endswith("/devices/%s/display" % second)
        wait_for_button(page)
        open_menu(page)
        current = page.locator('%s[aria-current="true"]' % FRAMES)
        assert current.count() == 1
        assert current.get_attribute("href") == "/devices/%s/display" % second
    finally:
        context.close()


def test_a_single_frame_user_sees_the_button_with_only_the_add_row(new_context, fleet_app):
    """with one frame the button still shows (it carries Add a frame): one frame row, a check
    on it, and the Add row"""
    (solo,) = fleet_app.single.ids
    context, page = _open(
        new_context, fleet_app, SINGLE_EMAIL, "/devices/%s/display" % solo,
        viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator("ul.frame-tiles, details.frame-fold").count() == 0
        open_menu(page)
        assert page.locator(FRAMES).count() == 1
        assert page.locator(FRAMES + " .frame-row__check").count() == 1
        assert page.locator(ADD).count() == 1
        assert page.locator(ADD).get_attribute("href") == "/pair-frame"
    finally:
        context.close()


def test_a_user_has_an_add_a_frame_row_to_their_own_page(new_context, fleet_app):
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        add = page.locator(ADD)
        assert add.count() == 1 and add.get_attribute("href") == "/pair-frame"
        with page.expect_navigation():
            add.click()
        assert page.url.endswith("/pair-frame")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_popover_fits_with_big_targets_and_marks_the_current_row(
        new_context, fleet_app, viewport, scheme, lang):
    """no horizontal overflow, the button 44px high, every row 52px high or more, the current
    row carries the check and the others do not"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=viewport, color_scheme=scheme)
    try:
        assert page.locator(BUTTON).bounding_box()["height"] >= HIT_FLOOR
        open_menu(page)
        assert not _assert_no_page_overflow(page, "frame menu", viewport["width"])
        for index in range(page.locator(ROW).count()):
            assert page.locator(ROW).nth(index).bounding_box()["height"] >= ROW_FLOOR
        checks = page.locator(FRAMES + " .frame-row__check")
        assert checks.count() == 1
        assert page.locator(FRAMES + '[aria-current="true"] .frame-row__check').count() == 1
    finally:
        context.close()


@pytest.mark.parametrize("lang,word", [("en", "Not seen yet"), ("fr", "Pas encore vu")])
def test_rows_carry_the_dot_word_and_the_last_seen_word(
        new_context, fleet_app, lang, word):
    """every row has exactly one status dot with its word and the last-seen line, in the
    page language (a never-seen frame reads Not seen yet)"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=VIEWPORT_DESKTOP)
    try:
        open_menu(page)
        dots = page.locator(FRAMES + " .frame-row__dot [role='img']")
        assert dots.count() == 2
        assert [dots.nth(i).get_attribute("aria-label") for i in range(2)] == [word, word]
        assert page.locator(FRAMES + " .frame-row__seen").all_inner_texts() == [word, word]
    finally:
        context.close()


def test_scripts_blocked_a_row_still_navigates(new_context, fleet_app):
    """a row is a plain link: without script it goes to the same page of the other frame"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/flights" % first,
        viewport=VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        page.locator(BUTTON).click()
        row = page.locator('%s[href="/devices/%s/flights"]' % (FRAMES, second))
        row.wait_for(state="visible")
        with page.expect_navigation():
            row.click()
        assert page.url.endswith("/devices/%s/flights" % second)
    finally:
        context.close()
