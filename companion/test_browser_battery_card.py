"""Real-browser checks of the Health page's Battery card: Percentage is the default unit, the
readings table keeps a Level column, the four states read in words and an icon (normal, low,
charging, too little data), the targets are 44px or more, the status pill and the charging pill
fit, and nothing overflows at 320, 390 and 1440 px in both languages and both themes."""
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, battery
from companion.test_browser_charging_pill import _seed_charging
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, _assert_no_page_overflow, _login, _set_ui_theme,
    seed_state_dir)
from server import history_db

pytestmark = pytest.mark.browser

ROUTE = "/fleet?frame=live&view=health"
VIEWPORTS = (
    ("320", {"width": 320, "height": 740}),
    ("390", {"width": 390, "height": 844}),
    ("1440", VIEWPORT_DESKTOP),
)
ROW = "#health-row-battery"


def _replace_readings(state_dir, readings):
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        conn.execute("DELETE FROM device_health")
        for age, millivolts in readings:
            history_db.record_device_health(
                conn, (now - age).isoformat(timespec="seconds"), battery_mv=millivolts,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")


def _seed_low(state_dir):
    seed_state_dir(state_dir)
    low = battery.low_display_mv()
    _replace_readings(state_dir, [
        (timedelta(days=day, minutes=2), low - 70 + day * 6) for day in range(40, -1, -1)])


def _seed_one_reading(state_dir):
    seed_state_dir(state_dir)
    _replace_readings(state_dir, [(timedelta(seconds=25), 3969)])


@pytest.fixture(scope="module")
def normal(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


@pytest.fixture(scope="module")
def low(module_app_server_factory):
    return module_app_server_factory(seed=_seed_low, fake_providers=True)


@pytest.fixture(scope="module")
def charging(module_app_server_factory):
    return module_app_server_factory(seed=_seed_charging, fake_providers=True)


@pytest.fixture(scope="module")
def one_reading(module_app_server_factory):
    return module_app_server_factory(seed=_seed_one_reading, fake_providers=True)


def _open(new_context, server, viewport, lang="en", theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + ROUTE)
    page.locator(ROW).wait_for(state="visible")
    _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", [v[1] for v in VIEWPORTS], ids=[v[0] for v in VIEWPORTS])
def test_the_card_overflows_nowhere_and_keeps_its_targets_at_44px(
        new_context, normal, viewport, lang, theme):
    context, page = _open(new_context, normal, viewport, lang, theme)
    try:
        where = "battery card %d/%s/%s" % (viewport["width"], lang, theme)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        card = page.locator(ROW).bounding_box()
        for selector in (".battery-hero", ".battery-chart-wrap", ".battery-readings > summary",
                         ".battery-status", ".sparkline__canvas:visible"):
            box = page.locator(ROW + " " + selector).first.bounding_box()
            assert box["x"] >= card["x"] - 0.5 and box["x"] + box["width"] <= card["x"] + card["width"] + 0.5, (
                where, selector, box, card)
        for unit in ("percent", "mv"):
            box = page.locator('.battery-unit__option[data-unit="%s"]' % unit).bounding_box()
            assert box["height"] >= 44 - 0.5 and box["width"] >= 44, (where, unit, box)
        summary = page.locator(ROW + " .battery-readings > summary").bounding_box()
        assert summary["height"] >= 52 - 0.5, (where, summary)
        assert abs(summary["width"] - card["width"]) <= 2, "the disclosure is a full-width row"
        assert page.locator(ROW + " .battery-readings > summary svg").is_visible(), "chevron and count"
        gauge = page.locator(ROW + " .battery-gauge").inner_text().replace("\n", "")
        assert gauge.replace("%", "").strip().isdigit(), "the gauge tick carries no label: %r" % gauge
    finally:
        context.close()


def test_percentage_is_the_default_unit_and_the_chart_follows_the_switch(new_context, normal):
    context, page = _open(new_context, normal, VIEWPORTS[1][1])
    try:
        page.wait_for_selector(".battery-unit:not([hidden])")
        checked = page.locator('.battery-unit__option[aria-checked="true"]')
        assert checked.count() == 1 and checked.get_attribute("data-unit") == "percent"
        assert page.locator(".battery-chart__view:not([hidden])").get_attribute("data-unit") == "percent"
        end = page.locator(".battery-chart__view:not([hidden]) .sparkline-text--strong", has_text="%")
        assert end.count() >= 1
        page.click('.battery-unit__option[data-unit="mv"]')
        assert page.locator(".battery-chart__view:not([hidden])").get_attribute("data-unit") == "mv"
        assert page.locator(
            ".battery-chart__view:not([hidden]) .sparkline-text--strong", has_text="mV").count() >= 1
    finally:
        context.close()


@pytest.mark.parametrize("lang,headers", (("en", ["Time", "Voltage", "Level"]),
                                          ("fr", ["Heure", "Tension", "Niveau"])))
def test_the_readings_table_has_time_voltage_and_level_columns(new_context, normal, lang, headers):
    context, page = _open(new_context, normal, VIEWPORTS[2][1], lang)
    try:
        assert page.locator(ROW + " .battery-readings table").is_hidden()
        page.click(ROW + " .battery-readings > summary")
        assert page.locator(ROW + " .battery-readings table").is_visible()
        assert [t.strip() for t in page.locator(ROW + " .battery-readings th").all_inner_texts()] == headers
        first = page.locator(ROW + " .battery-readings tbody tr").first.locator("td").all_inner_texts()
        assert first[1].replace("\xa0", " ").endswith("mV") and first[2].replace("\xa0", " ").endswith("%"), first
        assert not _assert_no_page_overflow(page, "readings open", VIEWPORTS[2][1]["width"])
    finally:
        context.close()


def test_a_normal_level_reads_as_a_pill_with_an_icon_and_no_charging_pill(new_context, normal):
    context, page = _open(new_context, normal, VIEWPORTS[1][1])
    try:
        pill = page.locator(ROW + " .battery-status")
        assert pill.inner_text().strip() == "Level looks normal" and pill.locator("svg").is_visible()
        assert page.locator(ROW + " .charging-pill").count() == 0
        assert page.locator(ROW).get_attribute("data-state") == "ok"
    finally:
        context.close()


@pytest.mark.parametrize("lang,words", (("en", "Level is low"), ("fr", "Le niveau est bas")))
def test_a_low_level_is_a_warning_in_words_and_an_icon(new_context, low, lang, words):
    context, page = _open(new_context, low, VIEWPORTS[0][1], lang)
    try:
        pill = page.locator(ROW + " .battery-status")
        assert pill.inner_text().strip() == words and pill.locator("svg").is_visible()
        assert page.locator(ROW).get_attribute("data-state") == "warn"
        assert not _assert_no_page_overflow(page, "low 320 " + lang, 320)
        assert page.locator(ROW + " .sparkline-threshold").count() >= 1, "the chart draws the mark"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [v[1] for v in VIEWPORTS], ids=[v[0] for v in VIEWPORTS])
def test_the_charging_pill_sits_in_the_card_header_only_when_charging(
        new_context, charging, normal, viewport):
    context, page = _open(new_context, charging, viewport, "fr")
    try:
        pill = page.locator(ROW + " > .health-row__summary .charging-pill")
        assert pill.is_visible()
        box, card = pill.bounding_box(), page.locator(ROW).bounding_box()
        assert box["x"] >= card["x"] and box["x"] + box["width"] <= card["x"] + card["width"] + 0.5
        assert not _assert_no_page_overflow(page, "charging", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang,title,note", (
    ("en", "Not enough readings for a curve yet", "A curve appears from 2 readings. 1 so far."),
    ("fr", "Pas encore assez de relevés pour une courbe",
     "La courbe apparaît à partir de 2 relevés. 1 pour l’instant.")))
@pytest.mark.parametrize("viewport", [v[1] for v in VIEWPORTS], ids=[v[0] for v in VIEWPORTS])
def test_too_little_data_says_so_and_keeps_every_other_datum(
        new_context, one_reading, viewport, lang, title, note):
    context, page = _open(new_context, one_reading, viewport, lang, "dark")
    try:
        empty = page.locator(ROW + " .battery-chart__empty")
        assert empty.is_visible() and title in empty.inner_text() and note in empty.inner_text()
        assert page.locator(ROW + " .battery-gauge").is_visible()
        assert page.locator(ROW + " .battery-volt").is_visible()
        assert page.locator(ROW + " .sparkline__canvas").count() == 0
        assert not _assert_no_page_overflow(page, "one reading", viewport["width"])
    finally:
        context.close()
