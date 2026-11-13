"""Real-browser checks of the Console and personal navigation: destination
cells that fill the bar without wrapped or clipped labels at 360px in English
and French, the space switch, the desktop sidebars, no administrator vocabulary for a user,
and the Locations form fitting its card at 360px. Light and dark themes."""
import pytest

from nav_spaces_support import (
    MIN_TAP_PX, admin_page as _admin_page, assert_bar as _assert_bar,
    own_frame_home as _own_frame_home, user_page as _user_page)
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)

pytestmark = pytest.mark.browser

USER_FORBIDDEN_WORDS = ("Admin", "Console", "Fleet", "Releases", "Device", "Update")

_FIELD_OVERFLOW = (
    "() => [...document.querySelectorAll('main input, main select')]"
    ".filter(e => e.offsetParent !== null).map(e => {"
    " const card = e.closest('section');"
    " const b = e.getBoundingClientRect(), c = card.getBoundingClientRect();"
    " return {id: e.id, sw: e.scrollWidth, cw: e.clientWidth,"
    " inside: b.right <= c.right + 0.5 && b.left >= c.left - 0.5}; })")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "path", ["/fleet", "/users", "/audit", "/update", "/health", "/device"])
def test_console_bar_fills_the_bar_with_five_cells_at_360(
        new_context, app_server_in_process, path, lang, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, path, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        _assert_bar(page, 5, "console%s/%s/%s" % (path, lang, scheme))
        assert page.locator(".section-subnav").count() == 0
        page.locator(".tab-bar__more > summary").click()
        sheet = page.locator(".tab-bar__more-panel a")
        assert sheet.count() == 2
        for index in range(sheet.count()):
            assert sheet.nth(index).bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_admin_personal_bar_has_six_cells_and_the_switch_in_more_at_360(
        new_context, app_server_in_process, lang, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, _own_frame_home, VIEWPORT_MIN_SUPPORTED,
        lang, scheme)
    try:
        _assert_bar(page, 6, "personal/%s/%s" % (lang, scheme))
        assert page.locator(".tab-bar__link--switch").count() == 0
        page.locator(".tab-bar__more > summary").click()
        sheet = page.locator(".tab-bar__more-panel a")
        assert sheet.count() == 2
        for index in range(sheet.count()):
            assert sheet.nth(index).bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_user_bar_has_six_cells_and_no_admin_words(
        new_context, app_server_in_process, lang, scheme):
    context, page = _user_page(
        new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED, lang, scheme)
    try:
        _assert_bar(page, 6, "user/%s/%s" % (lang, scheme))
        assert page.locator(".space-switch").count() == 0
        page.locator(".tab-bar__more > summary").click()
        assert page.locator(".tab-bar__more-panel a").count() == 1
        if lang == "en":
            text = page.locator("body").inner_text()
            for word in USER_FORBIDDEN_WORDS:
                assert word not in text, word
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_phone_more_switch_navigates_both_ways_under_a_slim_header_at_360(
        new_context, app_server_in_process, lang):
    context, page = _admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_MIN_SUPPORTED, lang)
    try:
        assert page.locator(".tab-bar > .tab-bar__link--switch").count() == 0
        assert page.locator(".space-strip").count() == 0
        assert page.locator("header.site-header").bounding_box()["height"] <= 56
        assert not _assert_no_page_overflow(page, "strip", 360)
        page.locator(".tab-bar__more > summary").click()
        switch = page.locator(".tab-bar__space-link")
        assert switch.count() == 1
        assert switch.bounding_box()["height"] >= MIN_TAP_PX
        switch.click()
        page.wait_for_function("() => !location.pathname.endsWith('/fleet')")
        page.wait_for_function(
            "() => { const r = document.querySelector('.tab-bar__more > summary');"
            " return !!r && !document.querySelector('.tab-bar__more').open; }")
        page.locator(".tab-bar__more > summary").click()
        page.wait_for_function(
            "() => document.querySelector('.tab-bar__space-link')"
            " && document.querySelector('.tab-bar__space-link').getAttribute('href') === '/fleet'")
        assert page.locator("header.site-header").bounding_box()["height"] <= 56
        page.locator(".tab-bar__space-link").click()
        page.wait_for_function("() => location.pathname.endsWith('/fleet')")
    finally:
        context.close()


_SIDEBAR_LINKS = (
    "() => [...document.querySelectorAll('.sidebar-nav a.sidebar-link')]"
    ".map(e => { const c = e.cloneNode(true);"
    " c.querySelectorAll('.visually-hidden').forEach(n => n.remove());"
    " return {text: c.textContent.trim(), h: e.getBoundingClientRect().height}; })")

CONSOLE_SIDEBAR_LABELS = [
    "Fleet", "Users", "Editor", "Audit log", "Account"]
PERSONAL_SIDEBAR_LABELS = [
    "Home", "Flight history", "Location and detection", "Style",
    "Airlines", "Account"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_desktop_sidebars_put_the_switch_first(
        new_context, app_server_in_process, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_DESKTOP, scheme=scheme)
    try:
        switch = page.locator(".dashboard-sidebar > .space-switch")
        assert switch.count() == 1
        assert page.locator(
            ".dashboard-sidebar > :not(.brand)").first.get_attribute("class") == "space-switch"
        assert switch.locator("a").first.inner_text().strip() == "Console"
        assert page.locator(".sidebar-nav .nav-group__label").first.inner_text(
            ).strip().lower() == "administration"
        links = page.evaluate(_SIDEBAR_LINKS)
        assert [link["text"] for link in links] == CONSOLE_SIDEBAR_LABELS
        assert all(link["h"] >= MIN_TAP_PX for link in links), links
        switch.locator("a", has_text="My frame").click()
        page.wait_for_function("() => !location.pathname.endsWith('/fleet')")
        page.wait_for_function(
            "() => { const a = document.querySelector('.dashboard-sidebar .space-switch"
            " [aria-current=page]'); return !!a && a.textContent.includes('My frame'); }")
        assert page.locator(".sidebar-nav").inner_text().count("Update") == 0
        assert page.locator(".section-subnav").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_desktop_personal_sidebar_lists_the_spec_links(
        new_context, app_server_in_process, scheme):
    context, page = _admin_page(
        new_context, app_server_in_process, _own_frame_home, VIEWPORT_DESKTOP,
        scheme=scheme)
    try:
        links = page.evaluate(_SIDEBAR_LINKS)
        assert [link["text"] for link in links] == PERSONAL_SIDEBAR_LABELS
        assert all(link["h"] >= MIN_TAP_PX for link in links), links
        assert page.locator(".sidebar-nav .nav-group__label").count() == 0
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
