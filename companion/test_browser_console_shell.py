"""Real-browser checks of the admin console shell: the phone bar keeps its
tap-target size, the page has no section chip row or sideways scroll on a small
phone, and the sidebar shows the Administration group."""
import pytest

from companion import console_routes, routes
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _login)

pytestmark = pytest.mark.browser

PAGES = (
    console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE, console_routes.AUDIT_ROUTE)
MIN_TAP_PX = 44


def _console_get(path):
    return routes.Route(
        "GET", routes.Exact(path),
        lambda h, m: h._console_page(path, None, "<p>console body</p>"),
        routes.ADMIN_ONLY)


@pytest.fixture
def server(app_server_in_process, monkeypatch):
    monkeypatch.setattr(
        routes, "ROUTES", routes.ROUTES + tuple(_console_get(p) for p in PAGES))
    return app_server_in_process


def _open(new_context, server, viewport, path):
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    return context, page


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_phone_bar_keeps_five_full_size_cells_in_the_console(
        new_context, server, viewport):
    """the Console bar has five cells, each at least 44px tall and wide and inside the
    viewport, and the page does not scroll sideways"""
    context, page = _open(new_context, server, viewport, console_routes.USERS_ROUTE)
    try:
        cells = page.evaluate(
            """() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details')]
                .map(e => { const b = e.getBoundingClientRect();
                            return {w: b.width, h: b.height, r: b.right}; })""")
        assert len(cells) == 5, cells
        for cell in cells:
            assert cell["h"] >= MIN_TAP_PX and cell["w"] >= MIN_TAP_PX, cells
            assert cell["r"] <= viewport["width"] + 0.5, cells
        fleet = page.locator('.tab-bar a[href="/fleet"]')
        assert fleet.count() == 1
        assert not _assert_no_page_overflow(page, "console/phone", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_no_section_chip_row_on_a_console_page_without_sideways_scroll(
        new_context, server, viewport):
    """the console page carries no section chip row and does not overflow"""
    context, page = _open(new_context, server, viewport, console_routes.AUDIT_ROUTE)
    try:
        assert page.locator(".section-subnav").count() == 0
        assert not _assert_no_page_overflow(page, "console/subnav", viewport["width"])
    finally:
        context.close()


def test_desktop_has_no_chip_row_and_shows_the_administration_group(
        new_context, server):
    """at 1280px the sidebar lists the console pages and there is no chip row"""
    context, page = _open(
        new_context, server, VIEWPORT_DESKTOP, console_routes.FLEET_ROUTE)
    try:
        assert page.locator(".section-subnav").count() == 0
        group = page.locator(".sidebar-nav .nav-group:has-text('Administration')")
        assert group.locator(".nav-group__label").is_visible()
        for path in (console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE):
            assert group.locator('a[href="%s"]' % path).is_visible(), path
        for path in PAGES:
            assert page.locator('.sidebar-nav a[href="%s"]' % path).is_visible(), path
        # Health, Device and Releases are folded into the Fleet view.
        for path in ("/health", "/device", "/update"):
            assert page.locator('.sidebar-nav a[href$="%s"]' % path).count() == 0, path
        current = page.locator('.sidebar-nav a[aria-current="page"]')
        assert current.get_attribute("href") == "/fleet"
    finally:
        context.close()
