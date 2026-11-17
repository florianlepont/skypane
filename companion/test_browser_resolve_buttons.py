"""The airline editor's resolve step: its Upload and Delete my name buttons are
the shared buttons, 44px tall at 360 and 1280px in English and French, in the
page's own panel (scripts blocked) and in the dialog the deep link opens."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _no_js_page, seed_state_dir)
from server.plane import manual_resolutions

pytestmark = pytest.mark.browser

PREFIX = "NEW"
ROUTE = "/airlines/manage?resolve=" + PREFIX
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
_MEASURE = (
    "root => [...document.querySelectorAll(root + ' button[type=submit]')]"
    ".filter(b => b.getBoundingClientRect().height > 0).map(b => ({"
    " text: b.textContent.trim(), cls: b.className, h: b.getBoundingClientRect().height,"
    " w: b.getBoundingClientRect().width}))")


def _seed(state_dir):
    seed_state_dir(state_dir)
    if manual_resolutions.add_entry(
            state_dir, PREFIX, "Totally Novel Airline") != manual_resolutions.ADD_OK:
        raise AssertionError("could not seed the manual entry")


def _assert_shared_buttons(found, expected_count):
    assert len(found) >= expected_count, found
    for button in found:
        assert "btn" in button["cls"].split(), button
        assert button["h"] >= 43.5 and button["w"] >= 43.5, button


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS)
def test_the_resolve_panel_buttons_are_shared_buttons_without_scripts(
        new_context, make_app_server, name, viewport, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    cookies = [{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}]
    with _no_js_page(
            new_context, server.base_url(), ROUTE, viewport=viewport, cookies=cookies) as page:
        _assert_shared_buttons(page.evaluate(_MEASURE, "[data-resolve-fallback]"), 2)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS)
def test_the_resolve_dialog_buttons_are_shared_buttons(
        new_context, make_app_server, name, viewport, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + ROUTE)
        page.locator("#panel-lookup-dialog[open]").wait_for(state="visible")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations()"
            ".every(a => a.playState !== 'running')", timeout=15000)
        _assert_shared_buttons(page.evaluate(_MEASURE, "#panel-lookup-dialog"), 2)
    finally:
        context.close()
