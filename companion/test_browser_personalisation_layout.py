"""Real-browser checks of the Personalisation tab's Layout view and pairing
picker, in English and French: picking layout C raises the save bar with the
one-section message, the Layout view being the section that carries the
change, Save persists it, and after a reload the C card is the
selected one; a frame on a giant layout shows the five pairing cards and a
picked pairing survives a save and a reload."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    _bar_text,
    _login,
    _save_via_bar,
    _wait_for_bar,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

LAYOUT_SECTION = {"en": "Layout", "fr": "Disposition"}
UNSAVED = {"en": "Unsaved changes", "fr": "Modifications non enregistrées"}
CHECKED_LAYOUT = "#personalisation-layout input[name=layout]:checked"
CHECKED_THEME = "#personalisation-look input[name=theme]:checked"


def _seed_classic(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="classic")


def _seed_giant(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="b", theme="grey")


def _open(new_context, base_url, route, lang):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_picking_layout_c_saves_and_is_selected_after_a_reload(new_context, make_app_server, lang):
    """clicking the C card raises the bar with the one-section message (the area names are listed
    only when several changed) from the Layout section's own wrapper, Save persists C, and the reloaded
    view has exactly the C radio checked and the frame's stored layout is c"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_LAYOUT_ROUTE, lang)
    try:
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "classic"
        page.locator('#personalisation-layout label:has(input[value="c"])').click()
        _wait_for_bar(page)
        assert _bar_text(page) == UNSAVED[lang]
        assert page.locator("#personalisation-layout").get_attribute(
            "data-dirty-section") == LAYOUT_SECTION[lang]
        _save_via_bar(page)
        page.reload()
        page.wait_for_selector(CHECKED_LAYOUT, state="attached")
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "c"
        assert page.locator("#personalisation-layout input[name=layout]:checked").count() == 1
        assert device_config.load_device_config(server.state_dir)["layout"] == "c"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_giant_layout_frame_picks_a_pairing_and_keeps_it_after_a_reload(
        new_context, make_app_server, lang):
    """on a frame whose layout is B the Departures view offers five pairing radios, the stored
    grey one is checked, picking light red then saving stores red_light and the reload checks it"""
    server = make_app_server(seed=_seed_giant)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_ROUTE, lang)
    try:
        radios = page.locator("#personalisation-look input[name=theme]")
        assert radios.count() == 5
        assert page.locator(CHECKED_THEME).get_attribute("value") == "grey"
        page.locator('#personalisation-look label:has(input[value="red_light"])').click()
        _wait_for_bar(page)
        _save_via_bar(page)
        page.reload()
        page.wait_for_selector(CHECKED_THEME, state="attached")
        assert page.locator(CHECKED_THEME).get_attribute("value") == "red_light"
        assert device_config.load_device_config(server.state_dir)["theme"] == "red_light"
    finally:
        context.close()
