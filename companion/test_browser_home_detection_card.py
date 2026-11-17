"""Real-browser checks of Home's Detection card: the whole row is a tap
target of at least 44 px in both themes, nothing overflows at 360 px, and a
tap leads to the Location page of the same frame."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _in_both_themes)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

ROW = 'section[aria-labelledby="home-detection"] a.row__main'


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, lang, viewport):
    context = new_context(viewport=viewport)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto("%s/devices/%s/" % (base, app.fleet.live.id))
    page.locator(ROW).wait_for(state="visible")
    return page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_the_row_is_a_44px_target_that_never_overflows(new_context, fleet_app, lang, viewport):
    page = _open(new_context, fleet_app, lang, viewport)
    for theme in _in_both_themes(page):
        box = page.locator(ROW).bounding_box()
        assert box["height"] >= 44, (theme, box)
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], (theme, box)
        assert not _assert_no_page_overflow(page, "Home/%s" % theme, viewport["width"])


def test_a_tap_opens_the_location_page_of_the_same_frame(new_context, fleet_app):
    page = _open(new_context, fleet_app, "en", VIEWPORT_MIN_SUPPORTED)
    page.locator(ROW).click()
    page.wait_for_url("**/devices/%s/detection" % fleet_app.fleet.live.id)
