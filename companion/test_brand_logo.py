"""The SkyPane logo as served: the favicon and apple-touch-icon links on every page type, the
public static routes behind them, the brand lockup in the sidebar and the phone app bar, and the
login card's own copy of the mark. Everything is asserted on served bytes (HTML, SVG, PNG), never
on source text.
"""
import re
import struct
import xml.etree.ElementTree as ET
from io import BytesIO

import pytest
from PIL import Image

from companion import auth
from companion_app_server import get, http_request, login
from companion_markup import parse_html

FAVICON = "/static/favicon.svg"
APPLE_TOUCH_ICON = "/static/apple-touch-icon.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def cookie(server):
    return login(server)


def _lang_cookie(session_cookie, lang):
    return "%s; %s=%s" % (session_cookie, auth.UI_LANG_COOKIE_NAME, lang)


def _icon_links(root):
    return {
        (link.attrs.get("rel"), link.attrs.get("href"), link.attrs.get("type"))
        for link in root.find_all("link") if "icon" in link.attrs.get("rel", "")}


EXPECTED_LINKS = {
    ("icon", FAVICON, "image/svg+xml"),
    ("apple-touch-icon", APPLE_TOUCH_ICON, None),
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("route", ["/", "/display", "/flights", "/airlines", "/fleet"])
def test_every_page_links_the_svg_favicon_and_the_apple_touch_icon(server, cookie, route, lang):
    status, _, body = get(server, route, cookie=_lang_cookie(cookie, lang))
    assert status == 200
    html = body.decode("utf-8")
    assert _icon_links(parse_html(html)) == EXPECTED_LINKS
    assert "data:image/svg+xml" not in html, "the old data: favicon is gone"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_login_page_links_the_icons(server, lang):
    status, _, body = get(server, "/login", cookie="%s=%s" % (auth.UI_LANG_COOKIE_NAME, lang))
    assert status == 200
    assert _icon_links(parse_html(body.decode("utf-8"))) == EXPECTED_LINKS


def test_the_error_pages_link_the_icons(server, cookie):
    status, _, body = get(server, "/no-such-page", cookie=cookie)
    assert status == 404
    assert _icon_links(parse_html(body.decode("utf-8"))) == EXPECTED_LINKS


def test_the_icons_load_without_a_session(server):
    """Browsers fetch the tab icon before any login, so neither route may redirect."""
    for route in (FAVICON, APPLE_TOUCH_ICON):
        status, _, body = get(server, route)
        assert status == 200, (route, status)
        assert body


def test_the_favicon_is_a_cacheable_svg_with_the_shared_static_policy(server):
    status, headers, body = get(server, FAVICON)
    assert status == 200
    assert headers["Content-Type"].startswith("image/svg+xml")
    assert "no-cache" in headers["Cache-Control"] and "public" in headers["Cache-Control"]
    assert headers["ETag"] and headers["Last-Modified"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    status, _, empty = http_request(
        server.base_url() + FAVICON, extra_headers={"If-None-Match": headers["ETag"]})
    assert status == 304 and empty == b""
    root = ET.fromstring(body)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == "0 0 32 32"


def test_the_favicon_is_self_contained_and_carries_nothing_sensitive(server):
    """No script, no external reference, no font dependency: the only embedded code is the one
    style block that switches the tile between its light and dark colours."""
    _, _, body = get(server, FAVICON)
    text = body.decode("utf-8")
    for forbidden in ("<script", "<text", "<image", "https://",
                      "href=", "password", "secret", "@import", "url("):
        assert forbidden not in text, forbidden
    assert text.count("<style>") == 1


def _favicon_rules(server):
    """The favicon's style rules as {scheme: {selector: {property: value}}}."""
    _, _, body = get(server, FAVICON)
    css = ET.fromstring(body).find("{http://www.w3.org/2000/svg}style").text
    media_at = css.index("@media")
    base, dark = css[:media_at], css[media_at:]
    dark = dark[dark.index("{") + 1:dark.rindex("}")]

    def parse(block):
        rules = {}
        for selector, declarations in re.findall(r"([.\w]+)\{([^}]*)\}", block):
            rules[selector] = dict(d.split(":") for d in declarations.split(";") if d)
        return rules
    assert "prefers-color-scheme:dark" in css.replace(" ", "")
    return {"light": parse(base), "dark": parse(dark)}


def test_the_favicon_tile_is_graphite_in_light_and_ivory_in_dark(server):
    rules = _favicon_rules(server)
    assert rules["light"][".tile"]["fill"] == "#1F2430"
    assert rules["light"][".glyph"]["stroke"] == "#FFFFFF"
    assert rules["dark"][".tile"]["fill"] == "#F2EFE9"
    assert rules["dark"][".glyph"]["stroke"] == "#1F2430"
    _, _, body = get(server, FAVICON)
    assert b"#B13F16" not in body, "the old orange tile is gone"
    root = ET.fromstring(body)
    classes = {el.attrib.get("class") for el in root.iter() if el.attrib.get("class")}
    assert classes == {"tile", "glyph"}, "colours come from the classes only"
    for el in root.iter():
        assert "fill" not in el.attrib and "stroke" not in el.attrib, el.tag


def _png_header(data):
    assert data[:8] == PNG_SIGNATURE
    width, height, depth, colour_type = struct.unpack(">IIBB", data[16:26])
    return width, height, depth, colour_type


def test_the_apple_touch_icon_is_a_180px_opaque_png(server):
    status, headers, body = get(server, APPLE_TOUCH_ICON)
    assert status == 200
    assert headers["Content-Type"] == "image/png"
    assert "no-cache" in headers["Cache-Control"]
    width, height, _, colour_type = _png_header(body)
    assert (width, height) == (180, 180)
    assert colour_type in (2, 6), "RGB or RGBA"
    assert len(body) > 500


def test_the_apple_touch_icon_is_the_graphite_tile_with_a_white_glyph(server):
    _, _, body = get(server, APPLE_TOUCH_ICON)
    image = Image.open(BytesIO(body)).convert("RGB")
    assert image.getpixel((4, 4)) == (0x1F, 0x24, 0x30), "full-bleed graphite corner"
    assert image.getpixel((90, 8)) == (0x1F, 0x24, 0x30), "graphite at a tile point"
    colours = {colour for _, colour in image.getcolors(maxcolors=100000)}
    assert any(min(c) > 240 for c in colours), "a white glyph is drawn"


def _brand(root, ancestor_selector):
    brand = root.select_one(ancestor_selector + " .brand")
    assert brand is not None, ancestor_selector
    return brand


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_sidebar_and_the_app_bar_carry_the_mark_beside_the_text(server, cookie, lang):
    _, _, body = get(server, "/", cookie=_lang_cookie(cookie, lang))
    root = parse_html(body.decode("utf-8"))
    for ancestor in (".dashboard-sidebar", ".site-header"):
        brand = _brand(root, ancestor)
        mark = brand.select_one("svg.logo-mark")
        assert mark is not None, ancestor
        assert mark.attrs["aria-hidden"] == "true"
        assert mark.select_one("use").attrs["href"] == "#icon-logo"
        title = brand.select_one(".site-title")
        assert title.text().strip() == "SkyPane", "the live wordmark stays the accessible name"
    assert re.search(r'<symbol id="icon-logo" viewBox="0 0 32 32">', body.decode("utf-8"))


def test_the_sprite_symbol_has_ink_and_exactly_one_accent_element(server, cookie):
    _, _, body = get(server, "/", cookie=cookie)
    root = parse_html(body.decode("utf-8"))
    symbol = [s for s in root.find_all("symbol") if s.attrs.get("id") == "icon-logo"][0]
    paths = symbol.find_all("path")
    accent = [p for p in paths if "logo-accent" in p.attrs.get("class", "").split()]
    assert len(paths) == 3 and len(accent) == 1
    markup = body.decode("utf-8")
    block = markup[markup.index('<symbol id="icon-logo"'):]
    block = block[:block.index("</symbol>")]
    assert 'stroke="currentColor"' in block
    assert "style=" not in block and "#" not in block.replace("#icon", "")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_login_card_carries_its_own_mark_above_the_heading(server, lang):
    _, _, body = get(server, "/login", cookie="%s=%s" % (auth.UI_LANG_COOKIE_NAME, lang))
    html = body.decode("utf-8")
    root = parse_html(html)
    card = root.select_one(".login-card")
    mark = card.select_one("svg.logo-mark")
    assert mark.attrs["aria-hidden"] == "true"
    assert mark.find_all("path") and 'class="logo-accent"' in html
    assert "<use" not in html, "the login shell carries no sprite"
    assert card.select_one("h1").text().strip() == "SkyPane"
    assert html.index('class="logo-mark"') < html.index("<h1")
    assert ' style="' not in html


def test_the_linked_icon_routes_are_the_static_allowlist_entries():
    from companion import layout, static_files
    assert layout.FAVICON_LINK_HTML.count('href="%s"' % static_files.FAVICON_ROUTE) == 1
    assert layout.FAVICON_LINK_HTML.count('href="%s"' % static_files.APPLE_TOUCH_ICON_ROUTE) == 1
    assert {static_files.FAVICON_ROUTE, static_files.APPLE_TOUCH_ICON_ROUTE} <= set(static_files.STATIC_ROUTES)
