# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the route directory cards on the System view: both directories and the
answered-by bar are visible without a tap, the bar has width, and nothing overflows at 360 and 1280 px in
English and French and both themes."""
import datetime

import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _set_ui_theme)
from server import history_db

pytestmark = pytest.mark.browser

VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP]
_SETTLED = animation_settle.SETTLED
VERDICTS = {
    "en": ("Reachable", "Not reachable"),
    "fr": ("Joignable", "Injoignable"),
}


def _ago(**delta):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**delta)).isoformat(
        timespec="seconds")


def _seed(server, with_counters):
    fx.seed_fleet(server.state_dir)
    with history_db.open_db(server.state_dir) as conn:
        history_db.record_device_health(conn, _ago(minutes=2), battery_mv=4000)
        if with_counters:
            history_db.record_route_lookups(
                conn, _ago(hours=3), [("vrs", "found")] * 60 + [("vrs", "none")] * 2 + [("vrs", "failed")])
            history_db.record_route_lookups(conn, _ago(minutes=4), [("vrs", "found")])
            history_db.record_route_lookups(
                conn, _ago(hours=5), [("adsbdb", "found")] * 5 + [("adsbdb", "none")] * 2)
            history_db.record_route_lookups(conn, _ago(hours=3), [("adsbdb", "failed")] * 4)
            for directory in ["vrs"] * 118 + ["adsbdb"] * 30:
                history_db.record_runway_event(conn, ts=_ago(hours=1), route_directory=directory)


def _open(new_context, server, viewport, lang, theme, with_counters=True):
    _seed(server, with_counters)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?view=system")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("scheme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "1280"])
def test_the_route_cards_show_both_directories_and_overflow_nowhere(
        new_context, app_server_in_process, viewport, lang, scheme):
    context, page = _open(new_context, app_server_in_process, viewport, lang, scheme)
    where = "route-sources/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        reachable, down = VERDICTS[lang]
        vrs = page.locator("#system-card-route-directory-vrs")
        adsbdb = page.locator("#system-card-route-directory-adsbdb")
        assert vrs.locator(".sys-card__value").inner_text() == reachable, where
        assert adsbdb.locator(".sys-card__value").inner_text() == down, where
        for card in (vrs, adsbdb):
            assert card.locator(".sys-card__facts").is_visible(), where
            assert card.locator(".sys-card__facts > div").count() == 4, where
        bar = page.locator("#system-card-route-answers .route-bar")
        box = bar.bounding_box()
        assert box["width"] > 100 and box["height"] >= 8, (where, box)
        segments = bar.locator(".route-bar__seg")
        first, second = segments.nth(0).bounding_box(), segments.nth(1).bounding_box()
        assert first["width"] > 2 * second["width"] > 0, (where, first, second)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "1280"])
def test_a_frame_with_no_counters_yet_says_so_without_overflow(
        new_context, app_server_in_process, viewport):
    context, page = _open(
        new_context, app_server_in_process, viewport, "en", "light", with_counters=False)
    try:
        assert not _assert_no_page_overflow(page, "route-sources-empty", viewport["width"])
        for directory in ("vrs", "adsbdb"):
            card = page.locator("#system-card-route-directory-" + directory)
            assert card.locator(".sys-card__value").inner_text() == "No request yet"
        assert page.locator("#system-card-route-answers .route-bar").count() == 0
    finally:
        context.close()
