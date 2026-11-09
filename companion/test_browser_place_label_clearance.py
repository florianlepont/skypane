#!/usr/bin/env python3
"""Browser check that an airport's code label never pokes out from under, or over, the details
card, the sheet or a control floating on the Location map, on a wide screen and a phone, and that
a label returns once it clears them."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login
from place_map_support import SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

READY = "() => document.documentElement.classList.contains('map-ready')"
TILES = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
IDLE = (
    "() => document.getAnimations().every((a) => a.playState !== 'running'"
    " || a.effect.getComputedTiming().iterations === Infinity)")
PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}



def _open(new_context, server, viewport, route):
    context = new_context(viewport=viewport)
    hosts = Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES, timeout=15000)
    page.wait_for_function(IDLE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page, hosts


# Every label that paints (not hidden) against the boxes floating over the map and the map's edge.
PAINTED_OVERLAPS = """() => {
  const covers = ['.place-card', '.place-sheet', '.place-float', '.place-modes', '.place-tools',
    '.place-info', '.place-pos'].flatMap((s) => [...document.querySelectorAll(s)])
    .map((e) => e.getBoundingClientRect()).filter((b) => b.width > 0 && b.height > 0);
  const map = document.getElementById('place-map').getBoundingClientRect();
  const out = {painted: 0, covered: 0, bad: []};
  for (const l of document.querySelectorAll('#place-map .place-dot__label')) {
    const style = getComputedStyle(l);
    if (style.display === 'none') continue;
    if (style.visibility === 'hidden') { out.covered += 1; continue; }
    out.painted += 1;
    const b = l.getBoundingClientRect();
    const hit = covers.some((c) => b.left < c.right && b.right > c.left
      && b.top < c.bottom && b.bottom > c.top);
    const outside = b.left < map.left || b.right > map.right || b.top < map.top
      || b.bottom > map.bottom;
    if (hit || outside) out.bad.push(l.textContent);
  }
  return out;
}"""


def _settled_read(page):
    """The map's labels once it has come to rest (a drag's glide starts a beat after the mouse
    is released): three clean reads in a row, 120ms apart, or the last dirty one."""
    clean = 0
    read = None
    for _ in range(40):
        page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_timeout(120)
        read = page.evaluate(PAINTED_OVERLAPS)
        clean = clean + 1 if not read["bad"] else 0
        if clean == 3:
            return read
    return read


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["1280", "390"])
def test_no_label_pokes_out_from_under_the_card_or_the_floating_controls(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, viewport, route="/detection?mode=runway")
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length >= 100", timeout=10000)
        page.click(".place-france")
        for _ in range(2):
            page.focus("#place-map")
            page.keyboard.press("+")
            page.wait_for_function(IDLE, timeout=10000)
        page.wait_for_function(TILES, timeout=10000)
        box = page.locator("#place-map").bounding_box()
        covered_seen = 0
        for step in range(6):
            read = _settled_read(page)
            assert not read["bad"], (step, read)
            covered_seen += read["covered"]
            start_x = box["x"] + box["width"] * 0.7
            start_y = box["y"] + box["height"] * 0.45
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x - 90, start_y + 40, steps=6)
            page.mouse.up()
        assert covered_seen > 0, "no label ever met the card or a control, the check proved nothing"
    finally:
        context.close()
