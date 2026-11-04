"""Real-browser checks of the estimated "Probably charging" pill: in Health's Battery row it
is visible and the personal Home never shows it; it stays on one line inside its container and the page at
360, 390 and 1280 px in both languages and both themes, and takes nothing from the controls
around it; with a discharging battery it is absent; and a new on-battery reading removes it on
the next load."""
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    _open_health_rows,
    _set_ui_theme,
    seed_state_dir,
)
from server import device_config, history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (
    ("1280", VIEWPORT_DESKTOP),
    ("390", VIEWPORT_PHONE),
    ("360", VIEWPORT_MIN_SUPPORTED),
)
WORDS = {"en": "Probably charging", "fr": "Probablement en charge"}
HEALTH_PILL = "#health-row-battery > summary .charging-pill"
# An hourly cadence keeps the readings fresh for two hours, so the shared,
# read-only server below never outlives its fixture however slow the run.
INTERVAL_S = 3600


def _seed_readings(state_dir, mvs):
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for i, mv in enumerate(mvs):
            ts = now - timedelta(seconds=10 + INTERVAL_S * (len(mvs) - 1 - i))
            history_db.record_device_health(
                conn, ts.isoformat(timespec="seconds"), battery_mv=mv,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(
        state_dir, wake_interval_s=INTERVAL_S, display_enabled=True, quiet_hours_enabled=False)


def _seed_charging(state_dir):
    seed_state_dir(state_dir)
    _seed_readings(state_dir, [3700 + 12 * i for i in range(12)])


def _seed_discharging(state_dir):
    seed_state_dir(state_dir)
    _seed_readings(state_dir, [4000 - 3 * i for i in range(12)])


@pytest.fixture(scope="module")
def charging_server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_charging, fake_providers=True)


@pytest.fixture(scope="module")
def discharging_server(module_app_server_factory):
    return module_app_server_factory(seed=_seed_discharging, fake_providers=True)


def _open(new_context, server, route, lang, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.locator("main").wait_for(state="visible")
    return context, page


_FIT_PROBE = """([pillSel, boxSel]) => {
  const pill = document.querySelector(pillSel);
  const box = document.querySelector(boxSel);
  const text = pill.querySelector('.charging-pill__text');
  const p = pill.getBoundingClientRect(), b = box.getBoundingClientRect();
  const t = text.getBoundingClientRect();
  const lineHeight = parseFloat(getComputedStyle(text).lineHeight);
  return {
    pill: p, box: b, textHeight: t.height, lineHeight: lineHeight,
    whiteSpace: getComputedStyle(pill).whiteSpace,
    clipped: pill.scrollWidth > pill.clientWidth + 1,
    iconBeforeText: pill.querySelector('svg').getBoundingClientRect().right <= t.left + 1,
    visible: p.width > 0 && p.height > 0 && getComputedStyle(pill).visibility === 'visible',
  };
}"""


def _assert_pill_fits(page, pill_selector, box_selector, where):
    seen = page.evaluate(_FIT_PROBE, [pill_selector, box_selector])
    assert seen["visible"], where
    assert seen["whiteSpace"] == "nowrap", where
    assert seen["textHeight"] <= seen["lineHeight"] + 1, "%s: the pill text wrapped" % where
    assert not seen["clipped"], "%s: the pill clips its own content" % where
    assert seen["iconBeforeText"], where
    pill, box = seen["pill"], seen["box"]
    assert box["left"] - 1 <= pill["left"] and pill["right"] <= box["right"] + 1, (
        "%s: the pill sticks out of its container" % where)
    assert pill["height"] <= 28, "%s: the pill grew to %spx tall" % (where, pill["height"])


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_home_shows_no_pill_and_no_battery_block_in_both_themes(
        new_context, charging_server, lang, viewport_name, viewport):
    """the personal Home never shows the charging pill nor a battery block, even while the
    battery is charging (the pill lives on Console Health), and does not overflow, in light
    and dark"""
    context, page = _open(new_context, charging_server, layout.HOME_ROUTE, lang, viewport)
    try:
        page.locator(".home-state").wait_for(state="visible")
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            where = "Home %s %s %s" % (lang, viewport_name, theme)
            assert page.locator(".charging-pill").count() == 0, where
            assert page.locator(".home-battery").count() == 0, where
            assert WORDS[lang] not in page.locator("body").inner_text(), where
            assert _assert_no_page_overflow(page, where) == ""
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_health_pill_is_visible_and_fits_in_both_themes(
        new_context, charging_server, lang, viewport_name, viewport):
    """in Health's Battery row the pill is visible in the closed row's summary, whole inside it,
    on one line, with no page overflow, in light and dark"""
    context, page = _open(new_context, charging_server, layout.HEALTH_ROUTE, lang, viewport)
    try:
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            where = "Health %s %s %s" % (lang, viewport_name, theme)
            page.locator(HEALTH_PILL).wait_for(state="visible")
            assert page.locator(HEALTH_PILL).inner_text().strip() == WORDS[lang], where
            _assert_pill_fits(page, HEALTH_PILL, "#health-row-battery > summary", where)
            assert _assert_no_page_overflow(page, where) == ""
    finally:
        context.close()


def test_the_pill_costs_the_controls_around_it_nothing(new_context, charging_server):
    """Home's two switches keep their 44px targets (with no pill on Home) and the Battery row's
    summary stays one tappable disclosure, with the pill present, at the narrowest supported
    width"""
    context, page = _open(
        new_context, charging_server, layout.HOME_ROUTE, "fr", VIEWPORT_MIN_SUPPORTED)
    try:
        page.locator(".home-state").wait_for(state="visible")
        assert page.locator(".charging-pill").count() == 0
        for selector in ('form[action="/quick/display"] button[role="switch"]',
                         'form[action="/quick/quiet-hours"] button[role="switch"]'):
            box = page.locator(selector).bounding_box()
            assert box["height"] >= 44 and box["width"] >= 44, (selector, box)
        page.goto(charging_server.base_url() + layout.HEALTH_ROUTE)
        summary = page.locator("#health-row-battery > summary")
        summary.wait_for(state="visible")
        assert summary.bounding_box()["height"] >= 44
        assert summary.bounding_box()["width"] <= VIEWPORT_MIN_SUPPORTED["width"]
        _open_health_rows(page)
        assert page.locator("#health-row-battery").get_attribute("open") is not None
        page.locator(HEALTH_PILL).wait_for(state="visible")
    finally:
        context.close()


def test_a_discharging_battery_shows_no_pill(new_context, discharging_server):
    """with a falling battery neither page shows the pill"""
    for route in (layout.HOME_ROUTE, layout.HEALTH_ROUTE):
        context, page = _open(new_context, discharging_server, route, "en", VIEWPORT_PHONE)
        try:
            assert page.locator(".charging-pill").count() == 0, route
            assert "Probably charging" not in page.locator("body").inner_text()
        finally:
            context.close()


def test_the_pill_is_inside_a_region_the_freshness_loop_swaps(new_context, charging_server):
    """on Health the pill sits inside one of the regions the page's refresh loop replaces in
    place, so it appears and disappears with its data and needs no reload"""
    swap_selectors = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_HEALTH]
    context, page = _open(new_context, charging_server, layout.HEALTH_ROUTE, "en", VIEWPORT_PHONE)
    try:
        page.locator(HEALTH_PILL).first.wait_for(state="visible")
        inside = page.evaluate(
            """([pillSel, regionSels]) => {
                const pill = document.querySelector(pillSel);
                return regionSels.some(sel => pill.closest(sel) !== null);
            }""", [HEALTH_PILL, list(swap_selectors)])
        assert inside
    finally:
        context.close()


def test_a_new_reading_removes_the_pill_on_the_next_load(new_context, make_app_server):
    """with Health open, an on-battery reading (an 84 mV step down, the real unplug) arrives and
    the next load of the page no longer shows the pill (Health has no live refresh marker, so
    the personal Home that used to swap it in place is the only loop that ever did)"""
    server = make_app_server(seed=_seed_charging, fake_providers=True)
    context, page = _open(new_context, server, layout.HEALTH_ROUTE, "en", VIEWPORT_PHONE)
    try:
        page.locator(HEALTH_PILL).wait_for(state="visible")
        with history_db.open_db(server.state_dir) as conn:
            history_db.record_device_health(
                conn, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                battery_mv=3700 + 12 * 11 - 84, fw_version="1.0.0", boot_reason="wake",
                rssi="-60")
        page.reload()
        page.locator('details.health-row[id$="battery"]').wait_for(state="visible")
        assert page.locator(".charging-pill").count() == 0
    finally:
        context.close()
