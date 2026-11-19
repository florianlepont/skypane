"""Real-browser check that the personal frame button is drawn on personal pages only: an
administrator's Console pages (Health, Device, Update, per frame or global) have none, the
personal pages of the same frame keep it."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser

VIEWPORTS = {"phone": {"width": 390, "height": 844}, "desktop": {"width": 1440, "height": 900}}
_BUTTON = "details.frame-menu"


def _paths(seed):
    prefix = "/devices/%s" % seed.live_id
    return (
        ["/health", "/device", "/update", prefix + "/health", prefix + "/device"],
        [prefix + "/", prefix + "/flights"])


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", sorted(VIEWPORTS))
def test_the_frame_button_is_on_personal_pages_only(
        app_server_in_process, new_context, viewport, lang):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=VIEWPORTS[viewport])
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        console, personal = _paths(seed)
        for path in console:
            page.goto(server.base_url() + path)
            page.locator("main").wait_for(state="visible")
            assert page.locator(_BUTTON).count() == 0, path
        for path in personal:
            page.goto(server.base_url() + path)
            page.locator("main").wait_for(state="visible")
            assert page.locator(_BUTTON).count() == 1, path
    finally:
        context.close()
