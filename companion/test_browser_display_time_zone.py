"""Browser checks for Display after the time zone and the place moved to the Location and
detection page: Display has no location card, no location picker and no time zone select, the
Quiet hours note links to the details card of the Location page, the page does not overflow and
every control is a 44 px target. Measured at 360 and 1280 px, in English and French, in both
themes. Boxes are read only once the page has finished loading, its finite animations have ended
and its controls own their centres (a cross-document view transition otherwise answers the root).
"""
import pytest
from place_map_support import Hosts

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _assert_hit_target, _assert_no_page_overflow, _login, _set_ui_theme,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

NOTE_LINK = ".quiet-timezone-note a"
QUIET_FIELDS = ("input[name=quiet_hours_start]", "input[name=quiet_hours_end]")
VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP]
VIEWPORT_IDS = ["360", "1280"]
LINK_TEXT = {"en": "Location and detection", "fr": "Lieu et détection"}

# Finite animations only: the live pulse never ends and must not hold the test.
_ANIMATIONS_DONE = (
    "document.getAnimations().every((a) => a.effect && "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _wait_at_rest(page, selector):
    """Wait for the finished load, the finite animations and `selector` owning its centre."""
    page.wait_for_function(
        """sel => {
          if (document.readyState !== 'complete' || !(%s)) return false;
          const e = document.querySelector(sel);
          if (!e) return false;
          const r = e.getBoundingClientRect();
          const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
          return !!hit && (hit === e || e.contains(hit));
        }""" % _ANIMATIONS_DONE, arg=selector, timeout=10000)


def _open(new_context, server, viewport, lang, theme=None):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/display")
    page.wait_for_selector(NOTE_LINK)
    if theme:
        _set_ui_theme(page, theme)
    page.locator(NOTE_LINK).scroll_into_view_if_needed()
    _wait_at_rest(page, NOTE_LINK)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_display_has_none_of_the_moved_controls_and_the_note_is_a_44px_link(
        new_context, server, viewport, theme, lang):
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        assert page.locator("section.detection-card").count() == 0
        assert page.locator("select[name=location_id]").count() == 0
        assert page.locator("select[name=timezone]").count() == 0
        assert page.locator("#location-detection-heading").count() == 0
        assert page.locator(NOTE_LINK).count() == 1
        assert page.locator(NOTE_LINK).inner_text() == LINK_TEXT[lang]
        assert page.locator(NOTE_LINK).get_attribute("href").endswith("/detection#details")
        for selector in (NOTE_LINK,) + QUIET_FIELDS:
            _assert_hit_target(page, selector, "Display")
        assert _assert_no_page_overflow(page, "Display", viewport["width"]) == ""
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
def test_the_note_leads_to_the_open_details_card_of_the_location_page(
        new_context, server, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        page.click(NOTE_LINK)
        page.wait_for_function(
            "() => location.pathname === '/detection' && location.hash === '#details'"
            " && document.readyState === 'complete'"
            " && document.documentElement.classList.contains('map-ready')",
            timeout=15000)
        page.wait_for_function(
            "() => { const d = document.getElementById('details');"
            " const s = document.querySelector('#details select[name=timezone]');"
            " return !!d && d.open && !!s && s.getBoundingClientRect().height > 0; }",
            timeout=10000)
    finally:
        context.close()
