"""Real-browser check that the page background reaches the very bottom of the screen on a short
page: the bottom-most pixel row matches the one 200 px above it (within the few levels the gradient itself spans), in both themes, at 390x844 and
360x640, also when the document is shorter than the visible window (a phone browser whose toolbars
have retracted shows more than the layout height)."""
import io

import animation_settle
import pytest
from PIL import Image

from companion import auth
from companion.test_browser_ux_helpers import UI_THEMES_EXPLICIT, _login, _set_ui_theme

pytestmark = pytest.mark.browser

VIEWPORTS = ({"width": 390, "height": 844}, {"width": 360, "height": 640})
# The bottom of the document, 150 px above the bottom of the window.
_SHORTER_THAN_WINDOW = """() => {
  const root = document.documentElement.style;
  root.minHeight = '0';
  root.height = (innerHeight - 150) + 'px';
}"""


def _rgb(page, x, y):
    png = page.screenshot(clip={"x": x, "y": y, "width": 1, "height": 1})
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((0, 0))


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=("390", "360"))
@pytest.mark.parametrize("window_taller", [False, True], ids=("fits", "window-taller"))
@pytest.mark.parametrize("path", ["/fleet", "/airlines"])
def test_the_background_colour_is_continuous_to_the_bottom_row(
        new_context, app_server_in_process, path, window_taller, viewport, theme):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "fr",
                          "url": app_server_in_process.base_url()}])
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + path)
        page.locator("main").wait_for(state="visible")
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 1"), "page must be short"
        if window_taller:
            page.evaluate(_SHORTER_THAN_WINDOW)
            page.wait_for_timeout(200)
        bottom = _rgb(page, 2, viewport["height"] - 1)
        above = _rgb(page, 2, viewport["height"] - 201)
        assert all(abs(a - b) <= 5 for a, b in zip(bottom, above)), (bottom, above)
    finally:
        context.close()
