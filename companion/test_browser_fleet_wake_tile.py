# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the Settings tiles of a frame's page: the wake interval as one control in
minutes (field, step buttons, shortcuts, "Default" tag) over the posted seconds, and the wide
Diagnostic LED tile. Both fit at 360 px and on a desktop, in English and French."""
import os

import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from server import device_config
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login

pytestmark = pytest.mark.browser

_SETTLED = animation_settle.SETTLED
BAR = "[data-dirty-bar]"
SECONDS = "input[name='wake_interval_s']"
MINUTES = "#wake-interval-m"
TILE = ".fleet-tile:has(#wake-interval-m)"


def _open(new_context, server, viewport, lang, stored_s=600):
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=stored_s)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=settings&frame=" + seed.live_id)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(MINUTES).wait_for(state="visible")
    return context, page


def _shot(page, name):
    target = os.environ.get("SKYPANE_TILE_SHOTS")
    if target:
        page.locator("#fleet-section-settings").screenshot(path=os.path.join(target, name))


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_settings_tiles_fit_and_the_interval_tile_has_more_room(
        new_context, app_server_in_process, viewport, lang):
    context, page = _open(new_context, app_server_in_process, viewport, lang)
    try:
        assert page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0
        interval = page.locator(TILE).bounding_box()
        led = page.locator(".fleet-tile:has(#quick-switch-led-label)").bounding_box()
        state = page.locator("#fleet-section-state .fleet-tile").first.bounding_box()
        section = page.locator("#fleet-section-settings .fleet-tiles").bounding_box()
        for box in (interval, led):
            assert box["x"] >= section["x"] - 0.5
            assert box["x"] + box["width"] <= section["x"] + section["width"] + 0.5
        assert abs(interval["width"] - led["width"]) < 1
        # More padding than a state tile, and the controls inside the tile.
        pad = page.evaluate(
            "sel => parseFloat(getComputedStyle(document.querySelector(sel)).paddingTop)", TILE)
        state_pad = page.evaluate(
            "() => parseFloat(getComputedStyle("
            "document.querySelector('#fleet-section-state .fleet-tile')).paddingTop)")
        assert pad > state_pad, (pad, state_pad)
        for control in ("[data-minutes-step='-1']", "[data-minutes-step='1']", MINUTES,
                        "[data-minutes-preset='60']"):
            box = page.locator(control).bounding_box()
            assert box["height"] >= 44 - 0.5, (control, box)
            assert box["x"] >= interval["x"] and box["x"] + box["width"] <= (
                interval["x"] + interval["width"] + 0.5), (control, box, interval)
        assert state["height"] > 0
        _shot(page, "tiles-%d-%s.png" % (viewport["width"], lang))
    finally:
        context.close()


def test_the_step_buttons_and_shortcuts_move_the_minutes_and_the_seconds_follow(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        minutes, seconds = page.locator(MINUTES), page.locator(SECONDS)
        assert minutes.input_value() == "10" and seconds.input_value() == "600"
        page.locator("[data-minutes-step='1']").click()
        assert minutes.input_value() == "11" and seconds.input_value() == "660"
        assert "11 min" in page.locator(TILE + " .fleet-tile__value").inner_text()
        page.locator(BAR).wait_for(state="visible")
        page.locator("[data-minutes-step='-1']").click()
        page.locator("[data-minutes-step='-1']").click()
        assert minutes.input_value() == "9" and seconds.input_value() == "540"
        page.locator("[data-minutes-preset='30']").click()
        assert minutes.input_value() == "30" and seconds.input_value() == "1800"
        assert page.locator("[data-minutes-preset='30']").get_attribute("aria-pressed") == "true"
        assert page.locator("[data-minutes-preset='5']").get_attribute("aria-pressed") == "false"
        # The ends stop at 1 and 60 minutes.
        page.locator("[data-minutes-preset='60']").click()
        page.locator("[data-minutes-step='1']").click()
        assert minutes.input_value() == "60" and seconds.input_value() == "3600"
        minutes.fill("1")
        page.locator("[data-minutes-step='-1']").click()
        assert minutes.input_value() == "1" and seconds.input_value() == "60"
    finally:
        context.close()


def test_a_typed_number_of_minutes_saves_as_seconds(new_context, app_server_in_process):
    server = app_server_in_process
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, "en")
    try:
        page.locator(MINUTES).fill("7")
        page.locator(BAR).wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        with page.expect_navigation():
            page.locator(BAR + " .dirty-bar__save").click()
        page.locator(MINUTES).wait_for(state="visible")
        assert page.locator(MINUTES).input_value() == "7"
        assert device_config.load_device_config(server.state_dir)["wake_interval_s"] == 420
    finally:
        context.close()


def test_the_default_tag_follows_the_default_interval(
        new_context, app_server_in_process, monkeypatch):
    monkeypatch.setenv("SKYPANE_SLEEP_S", "900")
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        tag = page.locator(TILE + " [data-minutes-tag]")
        assert tag.is_hidden()
        page.locator("[data-minutes-preset='15']").click()
        assert tag.is_visible() and tag.inner_text() == "Default"
        page.locator("[data-minutes-step='1']").click()
        assert tag.is_hidden()
        assert "Default: 15 min." in page.locator(TILE).inner_text()
    finally:
        context.close()


def test_cancel_restores_the_minutes_and_the_seconds(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        page.locator("[data-minutes-preset='30']").click()
        page.locator(BAR).wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator(BAR + " .dirty-bar__cancel").click()
        page.locator(BAR).wait_for(state="hidden")
        page.wait_for_function(
            "() => document.querySelector('#wake-interval-m').value === '10'"
            " && document.querySelector('input[name=wake_interval_s]').value === '600'",
            timeout=10000)
        assert "10 min" in page.locator(TILE + " .fleet-tile__value").inner_text()
    finally:
        context.close()


def test_without_a_script_the_minutes_field_alone_saves(new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    context = new_context(viewport=VIEWPORT_DESKTOP, java_script_enabled=False)
    try:
        page = context.new_page()
        _login_no_script(page, server)
        page.goto(server.base_url() + "/fleet?tab=settings&frame=" + seed.live_id)
        assert page.locator("[data-minutes-step]").first.is_hidden()
        assert page.locator("[data-minutes-preset]").first.is_hidden()
        page.locator(MINUTES).fill("20")
        page.locator(".dirty-bar [data-static-save-fallback]").click()
        page.wait_for_load_state()
        assert device_config.load_device_config(server.state_dir)["wake_interval_s"] == 1200
    finally:
        context.close()


def _login_no_script(page, server):
    """Sign in with the scripts off: the session cookie comes from a scripted login."""
    scripted = page.context.browser.new_context()
    try:
        scripted_page = scripted.new_page()
        _login(scripted_page, server.base_url())
        page.context.add_cookies(scripted.cookies())
    finally:
        scripted.close()
