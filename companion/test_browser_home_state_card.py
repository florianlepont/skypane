"""Real-browser checks of Home's merged frame-state card: 44px targets and no
horizontal overflow at 1280/390/360 px, keyboard operation with a visible
focus indicator, the persisted effect plus confirmation flash after each
button, and the same flow with scripts blocked."""
from urllib.parse import urlsplit

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    _no_js_page,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

VIEWPORTS = (
    ("1280", VIEWPORT_DESKTOP),
    ("390", VIEWPORT_PHONE),
    ("360", VIEWPORT_MIN_SUPPORTED),
)
SCREEN_BUTTON = 'form[action="/quick/display"] button'
QUIET_BUTTON = 'form[action="/quick/quiet-hours"] button'
FLASH = '.banner--flash[role="status"]'


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=False)


def _open_home(new_context, base_url, lang, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.HOME_ROUTE)
    page.locator("main").wait_for(state="visible")
    return context, page


def _has_visible_focus_indicator(page, selector):
    return page.evaluate(
        """sel => {
            const el = document.querySelector(sel);
            if (document.activeElement !== el) return false;
            const style = getComputedStyle(el);
            const outline = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0;
            return outline || style.boxShadow !== 'none';
        }""", selector)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_state_card_layout_targets_and_keyboard(
        new_context, make_app_server, lang, viewport_name, viewport):
    """both buttons are at least 44px tall, fully inside the viewport with no page overflow, show
    a focus indicator under keyboard navigation, and a Space press on the screen button persists
    display_enabled=false and lands back on Home with the confirmation flash"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_home(new_context, server.base_url(), lang, viewport)
    try:
        card = page.locator('section[aria-labelledby="home-frame-state"]')
        card.wait_for(state="visible")
        for selector in (SCREEN_BUTTON, QUIET_BUTTON):
            box = page.locator(selector).bounding_box()
            assert box is not None
            assert box["height"] >= 44, "%s: %s is %spx tall" % (viewport_name, selector, box["height"])
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], (
                "%s: %s leaves the viewport" % (viewport_name, selector))
        overflow = _assert_no_page_overflow(page, "home/%s/%s" % (lang, viewport_name), viewport["width"])
        assert not overflow, overflow

        page.locator(SCREEN_BUTTON).focus()
        page.keyboard.press("Tab")
        assert _has_visible_focus_indicator(page, QUIET_BUTTON), "no focus ring on the quiet button"
        page.keyboard.press("Shift+Tab")
        assert _has_visible_focus_indicator(page, SCREEN_BUTTON), "no focus ring on the screen button"
        with page.expect_navigation():
            page.keyboard.press("Space")
        # flash-cleanup.js drops the query string once the banner is shown.
        assert urlsplit(page.url).path == layout.HOME_ROUTE
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is False
        headline = page.locator(".home-state__headline").inner_text()
        assert headline.strip() == ("Screen off — the frame stays blank" if lang == "en"
                                    else "Écran éteint — le cadre reste vide")
    finally:
        context.close()


def test_quiet_hours_button_with_scripts_blocked(new_context, make_app_server):
    """with JavaScript disabled the quiet-hours form still posts, persists, redirects to Home and
    shows the flash plus the opposite button"""
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(new_context, server.base_url(), layout.HOME_ROUTE) as page:
        with page.expect_navigation():
            page.locator(QUIET_BUTTON).click()
        assert page.url == server.base_url() + "/?flash=quiet_on"
        assert page.locator(FLASH).count() == 1
        assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is True
        assert "Turn quiet hours off" in page.locator(QUIET_BUTTON).inner_text()
