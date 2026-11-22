"""Real-browser checks of the two pages the State tiles open, Health and Versions: no list column,
one visible h1, a 44 px way back to the frame, nothing overflowing at 360, 390 and 1440 px in
English and French and both themes, the Health rows open, and a tile reaching its page in one tap."""
import datetime

import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _assert_health_rows_flat, _login, _set_ui_theme, seed_two_releases)
from server import device_config, history_db

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
VIEWPORTS = [VIEWPORT_MIN_SUPPORTED, PHONE, VIEWPORT_DESKTOP]
_SETTLED = animation_settle.SETTLED
TITLES = {"en": {"health": "Health", "versions": "Versions"},
          "fr": {"health": "Santé", "versions": "Versions"}}


def _seed(server):
    seed = fx.seed_fleet(server.state_dir)
    now = datetime.datetime.now(datetime.timezone.utc)
    with history_db.open_db(server.state_dir) as conn:
        for i in range(10):
            stamp = now - datetime.timedelta(hours=6 * (9 - i), seconds=20)
            history_db.record_device_health(
                conn, stamp.isoformat(timespec="seconds"), battery_mv=4050 - 9 * i,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    seed_two_releases(server.state_dir)
    return seed


def _open(new_context, server, viewport, lang, theme, path):
    seed = _seed(server)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path.replace("{live}", seed.live_id))
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("scheme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "390", "1440"])
@pytest.mark.parametrize("view", ["health", "versions"])
def test_a_detail_page_has_its_title_a_way_back_and_overflows_nowhere(
        new_context, app_server_in_process, view, viewport, lang, scheme):
    context, page = _open(
        new_context, app_server_in_process, viewport, lang, scheme,
        "/fleet?frame={live}&view=" + view)
    where = "fleet-%s/%d/%s/%s" % (view, viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        assert page.locator("main h1:visible").count() == 1, where
        assert page.locator("main h1:visible").inner_text() == TITLES[lang][view], where
        assert page.locator(".fleet-list").count() == 0, where
        assert page.locator(".fleet-switch").count() == 0 and page.locator("nav.fleet-anchors").count() == 0
        back = page.locator("a.fleet-back")
        box = back.bounding_box()
        assert box["height"] >= 44 - 0.5 and box["x"] >= 0, (where, box)
        assert ("Orly frame" if lang == "en" else "Cadre d’Orly") in back.inner_text(), where
        title = page.locator("main h1").bounding_box()
        assert box["x"] <= title["x"] + 1, (where, box, title)
        assert page.locator("details.frame-menu").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "390", "1440"])
def test_every_health_row_shows_its_evidence_without_a_tap(
        new_context, app_server_in_process, viewport):
    context, page = _open(
        new_context, app_server_in_process, viewport, "en", "light",
        "/fleet?frame={live}&view=health")
    try:
        rows = page.locator("div.health-row")
        assert rows.count() >= 5
        _assert_health_rows_flat(page)
        # One card per topic, none of them a collapsible row.
        assert page.locator("main ul.group:has(> li > .health-rows)").count() == rows.count()
        for row in range(rows.count()):
            assert rows.nth(row).locator(".health-row__body").is_visible()
        # The battery row's chart and readings table are on the page.
        assert page.locator("#health-row-battery .battery-readout").is_visible()
        assert page.locator("#health-row-battery svg").first.is_visible()
        # Unresolved airlines are handled in the Editor: no link to them on this page.
        assert page.locator("main a[href*='airlines/manage']").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [PHONE, VIEWPORT_DESKTOP], ids=["390", "1440"])
def test_a_tile_opens_its_page_in_one_tap_and_the_way_back_returns(
        new_context, app_server_in_process, viewport):
    context, page = _open(
        new_context, app_server_in_process, viewport, "en", "light", "/fleet?frame={live}")
    try:
        page.locator("a.fleet-tile", has_text="Battery").click()
        page.wait_for_url("**view=health")
        assert page.locator("main h1:visible").inner_text() == "Health"
        page.locator("a.fleet-back").click()
        page.wait_for_url("**/fleet?frame=*")
        assert page.locator("a.fleet-tile").count() == 4
        page.locator("a.fleet-tile", has_text="Firmware").click()
        page.wait_for_url("**view=versions")
        assert page.locator("main h1:visible").inner_text() == "Versions"
        assert page.locator(".update-cta form button[type=submit]").is_visible()
    finally:
        context.close()
