#!/usr/bin/env python3
"""Real-browser checks of the SkyPane brand lockup: at 390 and 1280 px in both themes the mark sits
beside the live "SkyPane" text in the sidebar (desktop) or the app bar (phone) without overflowing or
changing the title's height, it paints with the theme's ink and one accent stroke, the brand adds
no tab stop, and the login card shows the mark above its heading even with scripts blocked.
"""
import io

import pytest
from PIL import Image

from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_no_page_overflow, _in_both_themes,
    _login, _no_js_page,
)

pytestmark = pytest.mark.browser

# (viewport, the container that holds the lockup at that width)
SURFACES = [
    pytest.param(VIEWPORT_PHONE, ".site-header", id="390"),
    pytest.param(VIEWPORT_DESKTOP, ".dashboard-sidebar", id="1280"),
]


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


def _pixels(page, selector):
    """The RGB pixels of one element's screenshot."""
    shot = page.locator(selector).screenshot()
    image = Image.open(io.BytesIO(shot)).convert("RGB")
    raw = image.tobytes()
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]


def _near(pixel, colour, tolerance=40):
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, colour))


def _rgb(css_colour):
    inner = css_colour[css_colour.index("(") + 1:css_colour.index(")")]
    return tuple(int(float(part)) for part in inner.replace("/", ",").split(",")[:3])


@pytest.mark.parametrize("viewport,container", SURFACES)
def test_the_lockup_fits_and_the_mark_paints_in_the_theme_colours(
        new_context, server, viewport, container):
    """the mark has a real box beside the text, nothing overflows, the lockup is exactly its 44px link,
    and the mark is drawn in the theme's text colour plus the accent in light and in dark"""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_load_state("load")
        brand = container + " .brand"
        page.locator(brand).wait_for(state="visible")
        seen_ink = set()
        for theme in _in_both_themes(page):
            mark_box = page.locator(brand + " .logo-mark").bounding_box()
            title_box = page.locator(brand + " .site-title").bounding_box()
            brand_box = page.locator(brand).bounding_box()
            assert mark_box["width"] > 0 and mark_box["height"] > 0, mark_box
            assert mark_box["x"] + mark_box["width"] <= title_box["x"] + 0.5, "mark sits left of the text"
            # The lockup is the one link to Home: exactly its 44px tap target, never taller.
            assert abs(brand_box["height"] - max(title_box["height"], 44)) <= 1, (
                "the lockup must be exactly its 44px link", brand_box, title_box)
            assert brand_box["x"] >= 0 and brand_box["x"] + brand_box["width"] <= viewport["width"]
            assert _assert_no_page_overflow(page, "brand lockup (%s)" % theme["theme"]) == ""
            colours = page.locator(brand + " .logo-mark").evaluate(
                "e => ({ink: getComputedStyle(e).color,"
                " accent: getComputedStyle(document.documentElement).getPropertyValue('--color-accent')})")
            ink = _rgb(colours["ink"])
            seen_ink.add(ink)
            pixels = _pixels(page, brand + " .logo-mark")
            assert sum(_near(p, ink) for p in pixels) > 20, "the pane and the S follow currentColor"
            accent = colours["accent"].strip()
            accent_rgb = tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
            assert any(_near(p, accent_rgb, 30) for p in pixels), "the flick uses the accent token"
        assert len(seen_ink) == 2, "the ink changes with the theme: %r" % (seen_ink,)
    finally:
        context.close()


@pytest.mark.parametrize("viewport,container", SURFACES)
def test_the_brand_is_one_decorative_link_home_and_the_chrome_keeps_its_hit_targets(
        new_context, server, viewport, container):
    """on a personal page the lockup is plain text plus a decorative mark inside the one link to
    the frame's Home (the same for an administrator and a user): no button, an unchanged
    accessible name, and the phone app bar is a slim logo-only strip (no menu button)"""
    context = new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_load_state("load")
        brand = container + " .brand"
        page.locator(brand).wait_for(state="visible")
        assert page.locator(brand + " button").count() == 0
        assert page.locator(brand + " a").count() == 1
        assert page.locator(brand + " a.brand__link").count() == 1
        assert page.locator(brand + " svg").get_attribute("aria-hidden") == "true"
        assert page.locator(brand).inner_text().strip() == "SkyPane"
        if viewport is VIEWPORT_PHONE:
            header = page.locator("header.site-header")
            assert header.locator("button, form, input").count() == 0
            assert header.bounding_box()["height"] <= 56
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_login_card_shows_the_mark_above_the_heading_without_scripts(new_context, server, viewport):
    """scripts blocked, signed out: the inline mark has a box above the h1, centred in the card,
    and the card does not overflow the viewport"""
    with _no_js_page(new_context, server.base_url(), "/login", viewport=viewport, sign_in=False,
                     reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        mark = page.locator(".login-card .logo-mark").bounding_box()
        heading = page.locator(".login-card h1").bounding_box()
        card = page.locator(".login-card").bounding_box()
        assert mark["width"] > 0 and mark["height"] > 0
        assert mark["y"] + mark["height"] <= heading["y"]
        assert abs((mark["x"] + mark["width"] / 2) - (card["x"] + card["width"] / 2)) <= 1
        assert _assert_no_page_overflow(page, "login card") == ""


def test_the_tab_icon_links_resolve_in_a_real_browser(new_context, server):
    """the page's icon links are fetched before any session exists and answer 200 with their media type"""
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/login")
        page.wait_for_load_state("load")
        hrefs = page.eval_on_selector_all(
            "link[rel~='icon'], link[rel='apple-touch-icon']", "els => els.map(e => e.href)")
        assert len(hrefs) == 2, hrefs
        types = set()
        for href in hrefs:
            response = context.request.get(href)
            assert response.status == 200, href
            types.add(response.headers["content-type"])
        assert types == {"image/svg+xml", "image/png"}
    finally:
        context.close()


@pytest.mark.parametrize("scheme,tile,glyph", [
    ("light", (0x1F, 0x24, 0x30), (0xFF, 0xFF, 0xFF)),
    ("dark", (0xF2, 0xEF, 0xE9), (0x1F, 0x24, 0x30)),
])
@pytest.mark.parametrize("size", [16, 32])
def test_the_favicon_renders_in_both_colour_schemes(new_context, server, scheme, tile, glyph, size):
    """the served SVG paints as an image at tab-strip sizes: a tile of the scheme's colour
    carrying a glyph of the contrasting colour"""
    context = new_context(viewport={"width": 64, "height": 64}, color_scheme=scheme)
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/login")
        page.wait_for_load_state("load")
        page.set_content(
            "<body style='margin:0;background:#808080'><img id=f width=%d height=%d "
            "src='%s/static/favicon.svg'></body>" % (size, size, server.base_url()))
        page.wait_for_function(
            "() => { const i = document.getElementById('f'); return i.complete && i.naturalWidth > 0; }")
        shot = page.locator("#f").screenshot()
        image = Image.open(io.BytesIO(shot)).convert("RGB")
        colours = [colour for _, colour in image.getcolors(maxcolors=100000)]
        assert any(_near(c, tile, 6) for c in colours), (scheme, size, "tile")
        assert any(_near(c, glyph, 12) for c in colours), (scheme, size, "glyph")
    finally:
        context.close()
