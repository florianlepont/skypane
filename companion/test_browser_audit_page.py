"""Real-browser checks of the Audit log page: no sideways scroll at the
smallest phone width, cards on a phone and the table on a desktop, chips and
pager links with a 44px touch target."""
import time

import pytest

import fleet_console_support as fx
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login)
from server import fleet_db

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44


def _open(new_context, server, viewport):
    fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            for index in range(60):
                fleet_db.audit_append(
                    conn, fx.ACTOR, "pairing.claim", "device", "d_00000001", "ok",
                    None, now=int(time.time()) + 1000 + index)
    finally:
        conn.close()
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/audit")
    page.locator("main").wait_for(state="visible")
    return context, page


def _no_sideways_scroll(page):
    return page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_phone_layout_stacks_cards_without_sideways_scroll(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED)
    try:
        assert _no_sideways_scroll(page)
        assert page.locator("ul.data-cards").is_visible()
        assert not page.locator("table.data-table--flights").is_visible()
        for selector in (".audit-chips .filter-chip__box", ".audit-pager .text-link"):
            assert page.locator(selector).first.bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()


def test_desktop_layout_shows_the_table_with_fifty_rows(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP)
    try:
        assert page.locator("table.data-table--flights").is_visible()
        assert not page.locator("ul.data-cards").is_visible()
        assert page.locator("table.data-table--flights tbody tr").count() == 50
        assert page.locator(".audit-chips").is_visible()
        assert _no_sideways_scroll(page)
    finally:
        context.close()
