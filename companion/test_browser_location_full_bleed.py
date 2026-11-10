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
        for y in (0, 2, shot.height - 3, shot.height - 1):
            row = [shot.getpixel((x, y)) for x in (3, shot.width // 2, shot.width - 4)]
            assert any(abs(p[0] - floor[0]) + abs(p[1] - floor[1]) + abs(p[2] - floor[2]) > 8
                       or p == (204, 204, 204) for p in row), (y, row, floor)
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


_EDGE_SCAN = """() => {
  const h = window.innerHeight;
  // The first colour of a value, as [r, g, b, alpha] in 0-255 (rgb() or color(srgb ...)).
  const first = (v) => {
    const m = v.match(/(rgba?|color)\\(([^)]*)\\)/);
    if (!m) return null;
    const n = m[2].replace('srgb', '').split(/[\\s,\\/]+/).filter(Boolean).map(Number);
    const k = m[1] === 'color' ? 255 : 1;
    return [n[0] * k, n[1] * k, n[2] * k, n.length > 3 ? n[3] : 1];
  };
  const dark = (v) => { const c = first(v);
    return !!c && c[3] > 0.3 && (c[0] + c[1] + c[2]) / 3 < 120; };
  const found = [];
  for (const el of document.querySelectorAll('body *')) {
    for (const pseudo of [null, '::before', '::after']) {
      const s = getComputedStyle(el, pseudo);
      if (pseudo && s.content === 'none') continue;
      if (s.position !== 'fixed' && s.position !== 'absolute') continue;
      if (s.display === 'none' || s.visibility === 'hidden') continue;
      if (el.getClientRects().length === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.bottom <= 0 || r.top >= h) continue;
      let top = r.top, bottom = r.bottom;
      if (pseudo) {
        const t = parseFloat(s.top), b = parseFloat(s.bottom);
        top = r.top + (isNaN(t) ? 0 : t);
        bottom = r.bottom - (isNaN(b) ? 0 : b);
      }
      if (!(top <= 0.5 || bottom >= h - 0.5)) continue;
      if (dark(s.backgroundColor) || dark(s.backgroundImage)) {
        found.push((el.className || el.tagName) + (pseudo || '') + ' ' + s.backgroundColor);
      }
    }
  }
  return found;
}"""


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_map_container_shows_the_tile_ground_colour_and_no_dark_surface_touches_an_edge(
        new_context, make_app_server, viewport, theme):
    """on a phone the map box (document content spanning the full page height, edge to edge) is
    the light tile land colour in both themes (a browser tints its bars from such a box), and no
    other fixed or absolute element or
    pseudo-element touching the top or bottom edge paints a dark opaque or gradient surface"""
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, theme=theme)
    try:
        got = page.evaluate(
            "() => { const m = getComputedStyle(document.getElementById('place-map'));"
            " return {bg: m.backgroundColor, pos: m.position, top: m.top, bottom: m.bottom}; }")
        assert got == {"bg": "rgb(242, 239, 233)", "pos": "absolute", "top": "0px", "bottom": "0px"}, got
        found = page.evaluate(_EDGE_SCAN)
        assert found == [], found
    finally:
        context.close()
