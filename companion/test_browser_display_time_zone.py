#!/usr/bin/env python3
"""Browser checks for the Time zone select in the Location and detection card on Display: it sits
in that card, a change raises the save bar naming "Time zone", Save persists it through the settings
form, and the form saves with scripts blocked.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _assert_hit_target, _assert_no_page_overflow, _bar_text, _login, _persist_without_js,
    _save_via_bar, _set_ui_theme, _wait_for_bar, seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

SELECT = "#quiet-hours-timezone"
CARD = "#location-detection"
ZONE = "America/Martinique"
ZONE_LABEL = {"en": "Time zone", "fr": "Fuseau horaire"}
VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP]
VIEWPORT_IDS = ["360", "1280"]


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _open(new_context, server, viewport, lang, theme=None):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/display")
    page.wait_for_selector(SELECT)
    if theme:
        _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_select_sits_in_the_merged_card_and_a_change_names_the_section(
        new_context, server, viewport, theme, lang):
    """The select is inside the Location and detection card, none is left in Quiet hours, a changed
    zone raises the bar naming "Time zone" and the select is a 44 px target without overflow."""
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        assert page.locator("select[name=timezone]").count() == 1
        assert page.locator(CARD + " " + SELECT).count() == 1
        quiet = page.locator('[data-dirty-section] #quiet-hours-group-heading').locator(
            "xpath=ancestor::*[@data-dirty-section][1]")
        assert quiet.locator("select[name=timezone]").count() == 0
        note = quiet.locator("a[href='#location-detection']")
        assert note.count() == 1
        page.wait_for_function(
            "() => { var s = document.querySelector('%s');"
            " return !!s.closest('[data-dirty-section]'); }" % SELECT)
        wrapper = page.locator(CARD + " [data-dirty-section]:has(%s)" % SELECT)
        assert wrapper.get_attribute("data-dirty-section") == ZONE_LABEL[lang]
        _assert_hit_target(page, SELECT, "time zone select")
        assert _assert_no_page_overflow(page, "Display", viewport["width"]) == ""

        page.select_option(SELECT, ZONE)
        _wait_for_bar(page)
        assert ZONE_LABEL[lang].lower() in _bar_text(page).lower()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_save_persists_the_time_zone_through_the_settings_form(
        new_context, make_app_server, viewport, lang):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang)
    try:
        page.select_option(SELECT, ZONE)
        _wait_for_bar(page)
        _save_via_bar(page)
        assert device_config.load_device_config(server.tmpdir)["timezone"] == ZONE
        page.wait_for_selector(SELECT)
        assert page.locator(SELECT).input_value() == ZONE
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_time_zone_saves_with_scripts_blocked(new_context, make_app_server, lang):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)

    def read_back():
        return device_config.load_device_config(server.tmpdir).get(
            "timezone", device_config.DEFAULT_TIMEZONE)

    result = _persist_without_js(
        new_context, server.base_url(), "/display", "timezone", ZONE, read_back,
        viewport=VIEWPORT_MIN_SUPPORTED,
        cookies=[{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    assert result["stored"] == ZONE
