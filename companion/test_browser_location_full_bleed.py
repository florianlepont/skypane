"""Real-browser check that on a phone the Location map fills the window from the very top edge
to the very bottom edge (under the status bar and the tab bar surroundings) while the header,
search field and chips stay below a forced safe-area inset, in both themes."""
import io

import pytest
from PIL import Image

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme)
from place_map_support import Hosts, SETTLED, seed
from server import airports

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
SAFE_TOP = 59
SAFE_BOTTOM = 34

_MEASURE = """() => {
  const box = (sel) => { const r = document.querySelector(sel).getBoundingClientRect();
    return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  return {map: box('#place-map'), header: box('.site-header .frame-switch, .site-header a, .site-header button'),
          search: box('.place-float'), tabs: box('.tab-bar'),
          height: window.innerHeight, width: window.innerWidth,
          page: document.documentElement.scrollHeight};
}"""


def _open(new_context, server, viewport, theme=None):
    context = new_context(viewport=viewport)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    icao = max(airports.load_catalogue().values(), key=lambda a: len(a.runways)).icao
    page.goto(server.base_url() + "/detection?airport=" + icao)
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    if theme is not None:
        _set_ui_theme(page, theme)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


def _force_insets(page):
    page.evaluate(
        "([t, b]) => { const s = document.documentElement.style;"
        " s.setProperty('--safe-top', t + 'px'); s.setProperty('--safe-bottom', b + 'px'); }",
        [SAFE_TOP, SAFE_BOTTOM])
    page.wait_for_function(
        "() => document.getAnimations().every((a) => a.playState !== 'running'"
        " || a.effect.getComputedTiming().iterations === Infinity)")


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_phone_map_fills_the_window_and_controls_clear_the_inset(
        new_context, make_app_server, viewport, theme):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, theme=theme)
    try:
        _force_insets(page)
        got = page.evaluate(_MEASURE)
        assert got["map"]["top"] <= 0 and got["map"]["bottom"] >= got["height"], got
        assert got["map"]["left"] <= 0 and got["map"]["right"] >= got["width"], got
        assert got["header"]["top"] >= SAFE_TOP - 1, got
        assert got["search"]["top"] >= SAFE_TOP, got
        assert got["tabs"]["bottom"] <= got["height"] - SAFE_BOTTOM + 1, got
        shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
        floor = page.evaluate("() => getComputedStyle(document.documentElement).backgroundColor")
        floor = tuple(int(v) for v in floor[4:-1].split(","))
        # Past the thin strips of the map's colour that tint Safari's bars (4px along each
        # edge), the rows are tiles, never the bare page.
        for y in (8, 10, shot.height - 11, shot.height - 9):
            row = [shot.getpixel((x, y)) for x in (3, shot.width // 2, shot.width - 4)]
            assert any(abs(p[0] - floor[0]) + abs(p[1] - floor[1]) + abs(p[2] - floor[2]) > 8
                       or p == (204, 204, 204) for p in row), (y, row, floor)
        for y in (shot.height - 3, shot.height - 1):
            assert shot.getpixel((shot.width // 2, y)) == floor, (y, floor)
    finally:
        context.close()


def test_the_desktop_map_box_is_the_whole_window(new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        got = page.evaluate(_MEASURE)
        assert got["map"]["top"] <= 0 and got["map"]["bottom"] >= got["height"], got
    finally:
        context.close()
