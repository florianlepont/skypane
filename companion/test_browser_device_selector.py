"""Real-browser checks of the frame chip and card sheet: a user with two frames
switches frame from Display and stays on Display, a one-frame user sees no
chip, the sheet fits at 360px and 1280px in both languages and colour schemes
with 44px targets, and it works with scripts blocked."""
import os
from types import SimpleNamespace

import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import sim_hardware_env

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _hit_area)
from companion.test_device_helpers import start_fleet_app
from server import device_dirs, fleet_db, hardware

pytestmark = pytest.mark.browser

CHIP = "a.frame-chip"
SHEET = "dialog.frame-sheet"
ROWS = "dialog.frame-sheet a.frame-card"
HIT_FLOOR = 44
CHIP_HEIGHT = 48
CARD_HEIGHT = 64
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


def _open(new_context, app, email, route, lang="en", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    pair = session_cookie_for_state_dir(app.server.state_dir, email, "user")
    name, value = pair.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + route)
    page.locator("main").wait_for(state="visible")
    return context, page


def _wait_sheet_open(page):
    page.wait_for_function("() => document.querySelector('dialog.frame-sheet').open")
    # The sheet enters with a short animation; a box measured while it runs is
    # a fraction of a pixel short of its resting size.
    page.wait_for_function(
        "() => document.getAnimations().every((a) => a.playState !== 'running')")


def test_a_user_switches_frame_from_display_and_stays_on_display(new_context, fleet_app):
    """opening the sheet on Display and choosing the other frame's card lands on that frame's
    Display, where the other frame is now the current one"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        page.locator(CHIP).click()
        _wait_sheet_open(page)
        assert page.locator(ROWS).count() == 2
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s/display"]' % (ROWS, second)).click()
        assert page.url.endswith("/devices/%s/display" % second)
        page.locator(CHIP).click()
        _wait_sheet_open(page)
        current = page.locator('%s[aria-current="true"]' % ROWS)
        assert current.count() == 1
        assert current.get_attribute("href") == "/devices/%s/display" % second
    finally:
        context.close()


def test_a_single_frame_user_sees_no_chip(new_context, fleet_app):
    """with one frame the page carries no chip and no sheet at all"""
    (solo,) = fleet_app.single.ids
    context, page = _open(
        new_context, fleet_app, SINGLE_EMAIL, "/devices/%s/display" % solo,
        viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator(CHIP).count() == 0
        assert page.locator(SHEET).count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_open_sheet_fits_with_44px_targets(new_context, fleet_app, viewport, scheme, lang):
    """the closed and the open sheet have no horizontal overflow, the sheet stays inside the
    viewport, the chip is 48px high, every card is at least 64px high and the close control
    and the footer link are at least 44px"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=viewport, color_scheme=scheme)
    try:
        assert not _assert_no_page_overflow(page, "chip/closed", viewport["width"])
        assert _hit_area(page, CHIP)["visual"][1] >= CHIP_HEIGHT
        page.locator(CHIP).click()
        _wait_sheet_open(page)
        box = page.locator(SHEET).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        for index in range(page.locator(ROWS).count()):
            assert page.locator(ROWS).nth(index).bounding_box()["height"] >= CARD_HEIGHT
        close = page.locator(SHEET + " a.modal__close").bounding_box()
        assert close["width"] >= HIT_FLOOR and close["height"] >= HIT_FLOOR
        assert page.locator(SHEET + " .frame-sheet__footer a").bounding_box()[
            "height"] >= HIT_FLOOR
        assert not _assert_no_page_overflow(page, "chip/open", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang,word,aria", [
    ("en", "Not seen yet", "Switch frame, current: Alpha"),
    ("fr", "Pas encore vu", "Changer de cadre, actuel\u00a0: Alpha")])
def test_cards_carry_the_dot_word_and_the_chip_its_name(
        new_context, fleet_app, lang, word, aria):
    """the chip's accessible name names the current frame and every card has exactly one dot
    with its status word, in the page language (a never-seen frame reads Not seen yet)"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator(CHIP).get_attribute("aria-label") == aria
        page.locator(CHIP).click()
        _wait_sheet_open(page)
        dots = page.locator(ROWS + " [role='img']")
        assert dots.count() == 2
        labels = [dots.nth(i).get_attribute("aria-label") for i in range(2)]
        assert labels == [word, word]
    finally:
        context.close()


def test_scripts_blocked_the_sheet_still_navigates(new_context, fleet_app):
    """without script the hash link shows the sheet and a card goes to the same page of the
    other frame"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/flights" % first,
        viewport=VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        page.locator(CHIP).click()
        card = page.locator('%s[href="/devices/%s/flights"]' % (ROWS, second))
        card.wait_for(state="visible")
        with page.expect_navigation():
            card.click()
        assert page.url.endswith("/devices/%s/flights" % second)
    finally:
        context.close()
