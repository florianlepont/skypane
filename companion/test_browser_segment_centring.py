#!/usr/bin/env python3
"""Browser check that the label of every segmented control and filter chip is centred in its
segment (Departures / Arrivals count tabs, the Personalisation tabs, the theme switch, the tab
bar, the space switch), at 360 px and 1280 px in both languages. A label that does not fit and
is clipped or overflows reads as off centre, so the measure is the text's own box against the
segment's box, the way a person sees it. Every segment is held within 1px on both axes at 360, 390
and 1440 px, including the Flights direction filter, the airline collection's show filter and
the Personalisation background and band controls; the Flights filter bar also shares one
44px height with its search button."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _login

pytestmark = pytest.mark.browser

SEGMENTS = (
    ".filter-chip__box, .theme-option, .personalisation-nav__link, .space-switch__segment, "
    ".tab-bar__link, .look-seg__option")
PATHS = ("/flights", "/airlines", "/display", "/account")
MAX_OFFSET = 1.0
VIEWPORT_PHONE_390 = {"width": 390, "height": 844}
VIEWPORT_WIDE = {"width": 1440, "height": 900}

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
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE_390, VIEWPORT_WIDE],
                         ids=["360", "390", "1440"])
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
            assert any("filter-chip__box" in row[0] for row in rows) or path in (
                "/display", "/account"), path
            off = [row for row in rows if abs(row[2]) > MAX_OFFSET or abs(row[3]) > MAX_OFFSET]
            if off:
                raise AssertionError("%s at %dpx: labels off centre %r" % (
                    path, viewport["width"], off))
    finally:
        context.close()


_BAR = (
    "() => { const box = (sel) => document.querySelector(sel).getBoundingClientRect();"
    " const track = box('.filter-bar__chips'); const search = box('.filter-bar__search');"
    " const title = box('.page-header');"
    " return {track: [track.height, (track.top + track.bottom) / 2],"
    "  search: [search.height, (search.top + search.bottom) / 2],"
    "  title: [title.height, (title.top + title.bottom) / 2],"
    "  chips: [...document.querySelectorAll('.filter-chip')].map((l) => l.getBoundingClientRect().height)}; }")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE_390],
                         ids=["360", "390"])
def test_the_flights_direction_track_and_title_row_search_are_both_44px(
        new_context, server, viewport, lang):
    """the segmented track and the collapsed search button in the title row are both 44px tall,
    the button sits on the title row's centre line, and every segment is a 44px target"""
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations().every("
            "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations"
            " === Infinity)", timeout=10000)
        bar = page.evaluate(_BAR)
        assert abs(bar["track"][0] - 44) <= 0.5 and abs(bar["search"][0] - 44) <= 0.5, bar
        assert abs(bar["title"][0] - 44) <= 0.5 or bar["title"][0] > 44, bar
        assert abs(bar["search"][1] - bar["title"][1]) <= 0.5, bar
        assert all(height >= 44 - 0.5 for height in bar["chips"]), bar
    finally:
        context.close()
