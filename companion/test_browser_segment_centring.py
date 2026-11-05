#!/usr/bin/env python3
"""Browser check that the label of every segmented control and filter chip is centred in its
segment (Departures / Arrivals count tabs, the Personalisation tabs, the theme switch, the tab
bar, the space switch), at 360 px and 1280 px in both languages. A label that does not fit and
is clipped or overflows reads as off centre, so the measure is the text's own box against the
segment's box, the way a person sees it."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login

pytestmark = pytest.mark.browser

SEGMENTS = (
    ".filter-chip__box, .theme-option, .personalisation-nav__link, .space-switch__segment, "
    ".tab-bar__link")
PATHS = ("/flights", "/airlines", "/display", "/account")
MAX_OFFSET_X = 0.6
MAX_OFFSET_Y = 1.5

_OFF_CENTRE = (
    "(sel) => [...document.querySelectorAll(sel)]"
    ".filter((e) => e.getBoundingClientRect().width > 0).map((e) => {"
    " const r = document.createRange(); r.selectNodeContents(e);"
    " const t = r.getBoundingClientRect(); const b = e.getBoundingClientRect();"
    " return [e.className.toString(), (e.textContent || '').trim().slice(0, 24),"
    "   (t.left + t.right) / 2 - (b.left + b.right) / 2,"
    "   (t.top + t.bottom) / 2 - (b.top + b.bottom) / 2]; })")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_segment_and_chip_labels_are_centred(new_context, server, viewport, lang):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        for path in PATHS:
            page.goto(server.base_url() + path)
            page.wait_for_function(
                "() => document.readyState === 'complete' && document.getAnimations().every("
                "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations"
                " === Infinity)", timeout=10000)
            rows = page.evaluate(_OFF_CENTRE, SEGMENTS)
            off = [row for row in rows if abs(row[2]) > MAX_OFFSET_X or abs(row[3]) > MAX_OFFSET_Y]
            if off:
                raise AssertionError("%s at %dpx: labels off centre %r" % (
                    path, viewport["width"], off))
    finally:
        context.close()
