"""Cancel in the save bar: the bar leaves and keyboard focus goes back to the
control that was changed, so the next Tab continues from where the person was
instead of from the top of the page."""
import pytest

from companion import layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _wait_for_bar, seed_state_dir)
from server import device_config

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
SAVED_LOOK = "band_red_field"
GREEN = '[data-look-sheet][data-look-inline] input[data-look-axis="colour"][value="green"]'
SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.playState !== 'running'"
    " || a.effect.getComputedTiming().iterations === Infinity)")


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme=SAVED_LOOK)


def _open(new_context, server, viewport):
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.DISPLAY_ROUTE)
    page.locator(GREEN).wait_for(state="attached")
    page.wait_for_function(SETTLED, timeout=15000)
    return context, page


def _cancel(page):
    _wait_for_bar(page)
    page.click(".dirty-bar [data-dirty-cancel]")
    page.wait_for_function("() => document.querySelector('.dirty-bar').hidden === true", timeout=5000)


@pytest.mark.parametrize("name,viewport", VIEWPORTS)
def test_cancel_returns_focus_to_the_control_that_was_changed(
        new_context, make_app_server, name, viewport):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport)
    try:
        page.locator(GREEN + " >> xpath=..").click()
        _cancel(page)
        page.wait_for_function(
            "() => { const a = document.activeElement;"
            " return !!a && a.matches('input[data-look-axis=\"colour\"]'); }", timeout=5000)
        assert device_config.load_device_config(server.state_dir).get("theme") == SAVED_LOOK
    finally:
        context.close()


def test_cancel_after_a_keyboard_change_keeps_focus_where_it_is(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.locator(GREEN).focus()
        page.keyboard.press("Space")
        _cancel(page)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches("
            "'input[data-look-axis=\"colour\"]')", timeout=5000)
    finally:
        context.close()
