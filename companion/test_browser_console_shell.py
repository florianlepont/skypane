"""Real-browser checks of the admin console shell: the phone bar keeps its
tap-target size with the Admin tab, the section sub-nav wraps without sideways
scroll on a small phone and disappears at desktop width, and the sidebar
shows the Administration group."""
import pytest

from companion import console_routes, routes
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _login)

pytestmark = pytest.mark.browser

PAGES = (
    console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE,
    console_routes.LOCATIONS_ROUTE, console_routes.AUDIT_ROUTE)
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
def test_phone_bar_keeps_five_full_size_cells_with_the_admin_tab(
        new_context, server, viewport):
    """the Admin tab is at least 44px tall and wide, the bar still has five cells inside the
    viewport and the page does not scroll sideways"""
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
        admin = page.locator('.tab-bar a[href="/fleet"]')
        assert admin.count() == 1
        assert not _assert_no_page_overflow(page, "console/phone", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize(
    "viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_sub_nav_wraps_to_at_most_two_lines_without_sideways_scroll(
        new_context, server, viewport):
    """five chips, each at least 44px tall, on at most two lines, current page selected"""
    context, page = _open(new_context, server, viewport, console_routes.AUDIT_ROUTE)
    try:
        chips = page.evaluate(
            """() => [...document.querySelectorAll('.section-subnav .filter-chip')]
                .map(e => { const b = e.getBoundingClientRect();
                            return {top: Math.round(b.top), h: b.height,
                                    r: b.right}; })""")
        assert len(chips) == 5, chips
        assert len({chip["top"] for chip in chips}) <= 2, chips
        assert all(chip["h"] >= MIN_TAP_PX for chip in chips), chips
        assert all(chip["r"] <= viewport["width"] + 0.5 for chip in chips), chips
        assert page.locator('.section-subnav [aria-current="page"]').inner_text().strip(), chips
        assert not _assert_no_page_overflow(page, "console/subnav", viewport["width"])
    finally:
        context.close()


def test_desktop_hides_the_sub_nav_and_shows_the_administration_group(
        new_context, server):
    """at 1280px the sidebar lists the console pages and the redundant sub-nav is hidden"""
    context, page = _open(
        new_context, server, VIEWPORT_DESKTOP, console_routes.FLEET_ROUTE)
    try:
        assert not page.locator(".section-subnav").is_visible()
        group = page.locator(".sidebar-nav .nav-group:has-text('Administration')")
        assert group.locator(".nav-group__label").is_visible()
        for path in (*PAGES, "/update"):
            assert group.locator('a[href="%s"]' % path).is_visible(), path
        current = page.locator('.sidebar-nav a[aria-current="page"]')
        assert current.get_attribute("href") == "/fleet"
    finally:
        context.close()
