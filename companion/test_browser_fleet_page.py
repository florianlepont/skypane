"""Real-browser checks of the admin Fleet page: no sideways scroll at the
smallest phone width, the table at desktop width and the cards below it, and
44px touch targets on the claim, register and confirm controls."""
import pytest

import fleet_console_support as fx
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44


def _open(new_context, server, viewport):
    fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet")
    page.locator("main").wait_for(state="visible")
    return context, page


def _height(page, selector):
    return page.locator(selector).first.bounding_box()["height"]


def test_phone_layout_stacks_cards_without_sideways_scroll(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED)
    try:
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert page.locator("ul.data-cards").is_visible()
        assert not page.locator("table.data-table--fleet").is_visible()
        summary = "ul.data-cards details.fleet-confirm > summary"
        assert _height(page, summary) >= MIN_TAP_PX
        page.locator(summary).first.click()
        confirm = "ul.data-cards details.fleet-confirm[open] button"
        assert _height(page, confirm) >= MIN_TAP_PX
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    finally:
        context.close()


def test_claim_and_register_controls_meet_the_touch_target(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_MIN_SUPPORTED)
    try:
        for selector in (
                "#pair-code", "#pair-owner", 'form[action="/fleet/pair"] button',
                "#register-mac", "#register-hash", "#register-hardware",
                'form[action="/fleet/register"] button'):
            assert _height(page, selector) >= MIN_TAP_PX, selector
    finally:
        context.close()


def test_desktop_layout_shows_the_table(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP)
    try:
        assert page.locator("table.data-table--fleet").is_visible()
        assert not page.locator("ul.data-cards").is_visible()
        assert page.locator("table.data-table--fleet tbody tr").count() == 4
    finally:
        context.close()
