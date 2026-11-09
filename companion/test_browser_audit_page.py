"""Real-browser checks of the Audit log page: no sideways scroll at the
smallest phone width, cards on a phone and the table on a desktop, chips and
pager links with a 44px touch target."""
import time

import pytest

import fleet_console_support as fx
from companion.test_browser_ux_helpers import (
    _login)
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


def _wait_ready(page):
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_function(
        "() => { const s = document.querySelector('.audit-event__row');"
        " if (!s) return false; const r = s.getBoundingClientRect();"
        " return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) !== document.documentElement; }")


@pytest.mark.parametrize("viewport", [
    {"width": 360, "height": 740}, {"width": 390, "height": 844},
    {"width": 1280, "height": 900}, {"width": 1440, "height": 900}])
def test_rows_are_compact_expand_and_never_overflow(
        new_context, app_server_in_process, viewport):
    context, page = _open(new_context, app_server_in_process, viewport)
    try:
        _wait_ready(page)
        assert _no_sideways_scroll(page)
        assert page.locator(".audit-event").count() == 50
        first = page.locator(".audit-event").first
        assert first.locator(".audit-event__detail").is_hidden()
        assert first.locator("summary").bounding_box()["height"] >= MIN_TAP_PX
        first.locator("summary").click()
        page.wait_for_function(
            "() => document.querySelector('.audit-event details').open")
        detail = first.locator(".audit-event__detail")
        assert detail.is_visible()
        for label in ("Target", "From", "Exact date", "Author"):
            assert first.locator("dt", has_text=label).is_visible()
        box = detail.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        assert _no_sideways_scroll(page)
        head_visible = page.locator(".audit-head").is_visible()
        assert head_visible == (viewport["width"] >= 1000)
        for selector in (".filter-bar__chips--links .filter-chip__box", ".audit-pager .text-link"):
            assert page.locator(selector).first.bounding_box()["height"] >= MIN_TAP_PX
    finally:
        context.close()
