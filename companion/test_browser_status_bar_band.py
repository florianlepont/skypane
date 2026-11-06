"""Real-browser check that the page is one continuous sky under the phone status bar: with the
safe-area inset forced to 59px (a Dynamic Island), the first 200px of the page, the strip the
status bar sits over included, has no lighter band than the page gradient (read from a
screenshot with Pillow), and the browser-chrome colour is the gradient's very first colour, in
both themes."""
import io

import pytest
from companion_app_server import session_cookie_for_state_dir
from PIL import Image
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_PHONE
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

SAFE_TOP = 59
STRIP = 200
TOLERANCE = 2

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

_SKY = """() => {
  const root = getComputedStyle(document.documentElement);
  const hex = (name) => root.getPropertyValue(name).trim();
  return {top: hex('--sky-top'), mid: hex('--sky-mid'),
          height: document.documentElement.getBoundingClientRect().height,
          chrome: [...document.querySelectorAll('meta[name=theme-color]')]
              .map(m => [m.media, m.content]),
          floor: getComputedStyle(document.documentElement).backgroundColor,
          body: getComputedStyle(document.body).backgroundColor,
          header: getComputedStyle(document.querySelector('.site-header')).backgroundColor};
}"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _rgb(hex_colour):
    text = hex_colour.lstrip("#")
    return [int(text[i:i + 2], 16) for i in (0, 2, 4)]


def _expected(sky, y):
    """The gradient colour at row `y`: --sky-top at 0 easing to --sky-mid at 45% of the
    document height (the root gradient's second stop)."""
    fraction = min(1.0, y / (0.45 * sky["height"]))
    return [a + (b - a) * fraction for a, b in zip(_rgb(sky["top"]), _rgb(sky["mid"]))]


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_no_lighter_band_under_the_status_bar(new_context, app, scheme):
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme=scheme)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": base}])
    page = context.new_page()
    try:
        page.goto(base + "/devices/%s/" % app.fleet.live.id)
        page.locator(".tab-bar").wait_for(state="visible")
        page.wait_for_function(_SETTLED)
        page.evaluate(
            "(px) => document.documentElement.style.setProperty('--safe-top', px + 'px')",
            SAFE_TOP)
        page.wait_for_function(_SETTLED)
        sky = page.evaluate(_SKY)
        assert sky["header"] == "rgba(0, 0, 0, 0)" and sky["body"] == "rgba(0, 0, 0, 0)"
        # A browser that tints its top bar from the flat root colour, not the gradient image,
        # must read the gradient's first colour.
        assert sky["floor"] == "rgb(%d, %d, %d)" % tuple(_rgb(sky["top"])), sky
        chrome = dict(sky["chrome"])
        assert chrome["(prefers-color-scheme: %s)" % scheme].upper() == sky["top"].upper()
        shot = Image.open(io.BytesIO(page.screenshot(
            clip={"x": 0, "y": 0, "width": VIEWPORT_PHONE["width"], "height": STRIP})))
        shot = shot.convert("RGB")
        # Column 2 is left of every control (the page padding), so it shows only the sky.
        for y in (0, 1, SAFE_TOP - 1, SAFE_TOP, SAFE_TOP + 10, 130, STRIP - 1):
            seen = shot.getpixel((2, y))
            want = _expected(sky, y)
            assert all(abs(s - w) <= TOLERANCE for s, w in zip(seen, want)), (
                scheme, y, seen, want)
        top = shot.getpixel((2, 1))
        assert all(abs(t - w) <= TOLERANCE for t, w in zip(top, _rgb(chrome[
            "(prefers-color-scheme: %s)" % scheme]))), (scheme, top)
    finally:
        context.close()
