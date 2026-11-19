#!/usr/bin/env python3
"""Real-browser check that the text of every chip, pill and button sits in the middle of its box,
on both axes, whatever the system font's metrics are.

A line box centres the font's content area (ascent plus descent). Fonts such as Segoe UI have a
tall ascent, so a label sat 1 to 2px off the middle of its pill. The page is therefore also
measured with a face of deliberately lopsided metrics standing in for the system font: the capitals must still land on the box's middle. The
ink of the label (its painted pixels) is measured, not the layout boxes, because the layout
boxes are exactly what the lopsided metrics skew.

The shared text-centring rules (`.btn`, the filter chips, the pills of the Airlines editor) are
measured on the Airlines editor, Flights and Fleet pages at a phone and a desktop width.
"""
import io

import pytest

from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_PHONE, _login

pytestmark = pytest.mark.browser

PIL_Image = pytest.importorskip("PIL.Image")

ROUTES = ("/airlines/manage", "/flights", "/fleet")
VIEWPORTS = (("390", VIEWPORT_PHONE), ("1280", VIEWPORT_DESKTOP))

# The boxes whose text is centred: the filter chips, the buttons, the Airlines editor's pills.
SELECTOR = ", ".join((
    ".filter-chip__box", ".btn", ".airlines-pill", ".airlines-gap__prefix",
    ".airlines-act", ".airline-card__chip"))

# One pixel of slack on top of the measured 0.5px that pixel snapping alone gives.
TOLERANCE = 1.25

# A lopsided stand-in for a system font: a tall ascent and a short descent. The stack starts with
# the names Blink treats as the system UI font, so the face is installed through the font tokens.
_LOPSIDED_FONT = (
    '@font-face{font-family:"Lopsided Test";'
    'src:local("Inter"),local("Inter Regular"),local("DejaVu Sans"),local("Arial");'
    "ascent-override:120%;descent-override:20%;line-gap-override:0%}"
    ':root{--font-ui:"Lopsided Test",sans-serif;--font-display:"Lopsided Test",sans-serif}')

_BOXES = """(sel) => {
  const out = [];
  document.querySelectorAll(sel).forEach((el, index) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (rect.width < 20 || rect.height < 14 || style.visibility === 'hidden') return;
    if (el.closest('[hidden], dialog:not([open])') || el.querySelector('svg, img, input')) return;
    if (!el.textContent.trim() || rect.bottom < 0 || rect.top > innerHeight) return;
    el.setAttribute('data-centring-index', String(index));
    // Capitals only: the ink of a label with descenders (g, y, parentheses) or tall
    // ascenders is lopsided by design, which would hide a real offset of the box.
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.textContent.trim()) node.textContent = 'H'.repeat(Math.min(node.textContent.trim().length, 6));
    }
    out.push(index);
  });
  return out;
}"""


def _ink_offsets(png):
    """`(dx, dy)` of the painted text's bounding box from the middle of the box, in pixels."""
    image = PIL_Image.open(io.BytesIO(png)).convert("RGB")
    width, height = image.size
    pixels = image.load()
    background = pixels[width // 2, 3]
    xs, ys = [], []
    for y in range(4, height - 4):
        for x in range(8, width - 8):
            pixel = pixels[x, y]
            if sum(abs(pixel[k] - background[k]) for k in range(3)) > 150:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return ((min(xs) + max(xs) + 1) / 2 - width / 2, (min(ys) + max(ys) + 1) / 2 - height / 2)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_airline_editor, fake_providers=True)


@pytest.mark.parametrize("lopsided", (False, True), ids=("system-font", "lopsided-font"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[name for name, _ in VIEWPORTS])
@pytest.mark.parametrize("route", ROUTES)
def test_the_text_of_every_chip_pill_and_button_is_centred_in_its_box(
        new_context, server, route, name, viewport, lopsided):
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    if lopsided:
        page.add_style_tag(content=_LOPSIDED_FONT)
        page.evaluate("() => document.fonts.load('15px \"Lopsided Test\"')")
    page.wait_for_function(
        "() => document.getAnimations().every(a => a.playState !== 'running' "
        "|| a.effect.getTiming().iterations === Infinity)", timeout=10000)
    indices = page.evaluate(_BOXES, SELECTOR)
    measured = 0
    for index in indices:
        box = page.locator('[data-centring-index="%d"]' % index)
        text = box.get_attribute("class")
        offsets = _ink_offsets(box.screenshot())
        if offsets is None:
            continue
        measured += 1
        dx, dy = offsets
        assert abs(dx) <= TOLERANCE and abs(dy) <= TOLERANCE, (
            "%r on %s at %s px is off the middle of its box by dx=%.2f dy=%.2f px (%s font)" % (
                text, route, name, dx, dy, "lopsided" if lopsided else "system"))
    if route == "/airlines/manage":
        assert measured >= 4, "expected the editor's chips, pill and buttons to be measured"
