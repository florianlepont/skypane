"""Real-browser checks of the System page's tiles: four equal tiles at least 44 px tall, nothing
overflowing at 320, 390 and 1440 px in English and French and both themes, the warning tile's
state spelled out, and a tile bringing its block into view."""
import datetime

import pytest

import fleet_console_support as fx
from companion import auth, health_signals
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, _assert_no_page_overflow, _login, _set_ui_theme)
from companion.test_view_pages_helpers import seed_runway_events
from server import history_db

pytestmark = pytest.mark.browser

VIEWPORTS = [{"width": 320, "height": 700}, {"width": 390, "height": 844}, VIEWPORT_DESKTOP]


def _open(new_context, server, tmp_path, monkeypatch, viewport, lang, theme):
    fx.seed_fleet(server.state_dir)
    now = datetime.datetime.now(datetime.timezone.utc)
    seed_runway_events(server.state_dir, [dict(
        ts=(now - datetime.timedelta(minutes=10 + 20 * i)).isoformat(), hex="39%04x" % i,
        callsign="AFR%03d" % i, aircraft_type="A320", confirmed_state="confirmed",
        corroborated=i % 4 != 0, route_source="adsb", airline="Air France",
        origin="LFPO", destination="LFPG") for i in range(20)])
    with history_db.open_db(server.state_dir) as conn:
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, now.isoformat())
    stamp = (now - datetime.timedelta(hours=2)).strftime("%Y%m%dT%H%M%SZ")
    marker = tmp_path / "marker"
    marker.write_text("skypane-state-%s.tar.gz" % stamp)
    monkeypatch.setenv(health_signals.OFFBOX_MARKER_ENV_VAR, str(marker))
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?view=system")
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("scheme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["320", "390", "1440"])
def test_tiles_are_equal_reachable_and_fit(
        new_context, app_server_in_process, tmp_path, monkeypatch, viewport, lang, scheme):
    context, page = _open(
        new_context, app_server_in_process, tmp_path, monkeypatch, viewport, lang, scheme)
    where = "system/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        tiles = page.locator("main .fleet-tiles--system a.fleet-tile")
        assert tiles.count() == 4, where
        boxes = [tiles.nth(i).bounding_box() for i in range(4)]
        assert all(b["height"] >= 44 for b in boxes), where
        assert len({round(b["width"]) for b in boxes}) == 1, where
        assert len({round(b["height"]) for b in boxes}) == 1, where
        for i in range(4):
            assert boxes[i]["x"] >= 0 and boxes[i]["x"] + boxes[i]["width"] <= viewport["width"], where
        warn = page.locator("main .fleet-tile[data-state='warn']")
        assert warn.count() == 1 and warn.locator(".visually-hidden").inner_text().strip(), where
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS[1:], ids=["390", "1440"])
def test_a_tile_brings_its_block_into_view(
        new_context, app_server_in_process, tmp_path, monkeypatch, viewport):
    context, page = _open(
        new_context, app_server_in_process, tmp_path, monkeypatch, viewport, "en", "light")
    try:
        page.locator("main .fleet-tile[href='#system-topic-backup']").click()
        page.wait_for_timeout(600)
        box = page.locator("#system-topic-backup").bounding_box()
        assert 0 <= box["y"] < viewport["height"]
    finally:
        context.close()
