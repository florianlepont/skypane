#!/usr/bin/env python3
"""Browser check that an airport's code label never pokes out from under, or over, the details
card, the sheet or a control floating on the Location map, on a wide screen and a phone, and that
a label returns once it clears them."""
import pytest

from companion.test_browser_place_pins import IDLE, READY, TILES, _open
from place_map_support import seed as _seed

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}

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


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["1280", "390"])
def test_no_label_pokes_out_from_under_the_card_or_the_floating_controls(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, viewport=viewport, route="/detection?mode=runway")
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
            page.wait_for_function(IDLE, timeout=10000)
            page.wait_for_timeout(150)
            read = page.evaluate(PAINTED_OVERLAPS)
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
