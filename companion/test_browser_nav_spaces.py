"""Real-browser checks of the two administrator spaces and the user bar: equal
bar cells without wrapped or clipped labels at 360px in English and French,
the space switch, the desktop sidebars, no administrator vocabulary for a user,
and the Locations form fitting its card at 360px. Light and dark themes."""
import pytest

import fleet_console_support as fx
from locations_page_support import open_locations_page
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login,
    _set_ui_theme)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44
USER_FORBIDDEN_WORDS = ("Admin", "Console", "Fleet", "Releases", "Device", "Update")

_CELLS = (
    "() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')]"
    ".map(e => { const b = e.getBoundingClientRect();"
    " return {w: b.width, h: b.height, r: b.right}; })")
_LABELS = (
    "() => [...document.querySelectorAll('.tab-bar__label')]"
    ".map(e => ({text: e.textContent, sw: e.scrollWidth, cw: e.clientWidth,"
    " lines: new Set([...(() => { const r = document.createRange();"
    " r.selectNodeContents(e); return [...r.getClientRects()]; })()]"
    ".map(x => Math.round(x.top))).size}))")
_FIELD_OVERFLOW = (
    "() => [...document.querySelectorAll('main input, main select')]"
    ".filter(e => e.offsetParent !== null).map(e => {"
    " const card = e.closest('section');"
    " const b = e.getBoundingClientRect(), c = card.getBoundingClientRect();"
    " return {id: e.id, sw: e.scrollWidth, cw: e.clientWidth,"
    " inside: b.right <= c.right + 0.5 && b.left >= c.left - 0.5}; })")


def _context(new_context, server, viewport, lang="en", scheme="light"):
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    return context


def _admin_page(new_context, server, path, viewport, lang="en", scheme="light"):
    fx.seed_fleet(server.state_dir)
    context = _context(new_context, server, viewport, lang, scheme)
    page = context.new_page()
    _login(page, server.base_url())
    if path == "/locations":
        open_locations_page(page, server.base_url())
    else:
        page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page


def _user_page(new_context, server, viewport, lang="en", scheme="light"):
    seed = fx.seed_fleet(server.state_dir)
    name, value = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL).split("=", 1)
    context = _context(new_context, server, viewport, lang, scheme)
    context.add_cookies([{
        "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
        "sameSite": "Strict"}])
    page = context.new_page()
    page.goto("%s/devices/%s/" % (server.base_url(), seed.owned_id))
    page.locator("main").wait_for(state="visible")
    return context, page


def _assert_bar(page, expected_cells, where):
    cells = page.evaluate(_CELLS)
    assert len(cells) == expected_cells, (where, cells)
    widths = [cell["w"] for cell in cells]
    assert max(widths) - min(widths) <= 1, (where, widths)
    for cell in cells:
        assert cell["h"] >= MIN_TAP_PX and cell["w"] >= MIN_TAP_PX, (where, cells)
        assert cell["r"] <= page.viewport_size["width"] + 0.5, (where, cells)
    for label in page.evaluate(_LABELS):
        assert label["sw"] <= label["cw"], (where, label)
        assert label["lines"] <= 1, (where, label)
    assert not _assert_no_page_overflow(page, where, page.viewport_size["width"])


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("path", ["/fleet", "/users", "/audit", "/update"])
def test_console_bar_has_four_equal_cells_at_360(
        new_context, app_server_in_process, path, lang, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, path, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        _assert_bar(page, 4, "console%s/%s/%s" % (path, lang, scheme))
        assert page.locator(".section-subnav").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_my_views_bar_has_five_equal_cells_at_360(
        new_context, app_server_in_process, lang, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, "/", VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        _assert_bar(page, 5, "my-views/%s/%s" % (lang, scheme))
        page.locator(".tab-bar__more > summary").click()
        sheet = page.locator(".tab-bar__more-panel a")
        assert sheet.count() == 4
        for index in range(sheet.count()):
            assert sheet.nth(index).bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_user_bar_has_four_equal_cells_and_no_admin_words(
        new_context, app_server_in_process, lang):
    context, page = _user_page(
        new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        _assert_bar(page, 4, "user/" + lang)
        assert page.locator(".space-switch").count() == 0
        if lang == "en":
            text = page.locator("body").inner_text()
            for word in USER_FORBIDDEN_WORDS:
                assert word not in text, word
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_header_switch_fits_and_navigates_both_ways_at_360(
        new_context, app_server_in_process, lang):
    context, page = _admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_MIN_SUPPORTED, lang)
    try:
        link = page.locator("header .space-switch")
        box = link.bounding_box()
        assert box["height"] >= MIN_TAP_PX
        header = page.locator("header.site-header").bounding_box()
        assert header["height"] < 120
        assert not _assert_no_page_overflow(page, "header", 360)
        link.click()
        page.wait_for_url(lambda url: not url.endswith("/fleet"))
        back = page.locator("header .space-switch")
        assert back.get_attribute("href") == "/fleet"
        assert page.locator("header.site-header").bounding_box()["height"] < 120
        back.click()
        page.wait_for_url(lambda url: url.endswith("/fleet"))
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_desktop_sidebars_put_the_switch_first(
        new_context, app_server_in_process, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_DESKTOP, scheme=scheme)
    try:
        first = page.locator(".sidebar-nav > *").first
        assert "space-switch" in first.get_attribute("class")
        assert first.inner_text().strip() == "My views"
        assert page.locator(".sidebar-nav .nav-group__label").first.inner_text(
            ).strip().lower() == "administration"
        first.click()
        page.wait_for_url(lambda url: not url.endswith("/fleet"))
        first = page.locator(".sidebar-nav > *").first
        assert first.inner_text().strip() == "Console"
        assert page.locator(".sidebar-nav").inner_text().count("Update") == 0
        assert page.locator(".section-subnav").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_locations_fields_fit_their_card_at_360(
        new_context, app_server_in_process, lang, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, "/locations", VIEWPORT_MIN_SUPPORTED,
        lang, scheme)
    try:
        fields = page.evaluate(_FIELD_OVERFLOW)
        assert fields
        for field in fields:
            assert field["inside"], field
            assert field["sw"] <= field["cw"] + 1, field
        assert not _assert_no_page_overflow(page, "locations", 360)
    finally:
        context.close()
