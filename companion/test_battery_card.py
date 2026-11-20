"""The Health page's Battery card: the chart (a range fitted to the data, the
low-battery line only when the data is near it, an end value, three date ticks)
and the card around it (percentage default, the Level column, the verdict
states, the too-little-data note), read back from the served markup."""
import re
from datetime import timedelta

import pytest

import companion.test_status_pages_helpers as shp
import health_page_composition
from companion import battery, battery_chart, draw, prefs
from companion.pages import health_page
from companion_markup import parse_html

NOW = "2026-09-12T12:00:00+00:00"


def _rows(values, daily=False):
    """Newest-first rows, one per `values` entry (oldest first)."""
    rows = []
    count = len(values)
    for index, mv in enumerate(values):
        day = count - 1 - index
        ts = "2026-09-%02dT%s:00+00:00" % (12 - day, "00:00") if daily else (
            "2026-09-12T%02d:%02d:00+00:00" % (11 - day // 60, 59 - day % 60))
        rows.append({"ts": ts, "battery_mv": mv, "reading_count": 3})
    return list(reversed(rows))


def _chart(values, **kwargs):
    return parse_html(battery_chart.battery_sparkline_svg(_rows(values), now=NOW, **kwargs))


def _texts(doc):
    return [node.text() for node in doc.find_all("text")]


def _ys(doc, cls):
    return [float(node.attrs["y"].rstrip("%")) for node in doc.find_all("rect", cls=cls)]


def test_the_y_range_is_fitted_to_the_data_not_the_fixed_3000_4200_range():
    values = [3900 + i * 3 for i in range(30)]
    doc = _chart(values)
    # Grid labels sit just above their line (dy -6); the end value has its own offset.
    labels = [t.text() for t in doc.find_all("text") if t.attrs.get("dy") == "-6"]
    numbers = sorted(int(t.split()[0]) for t in labels)
    assert numbers and all(3800 <= n <= 4100 for n in numbers), labels
    assert 3000 not in numbers and 4200 not in numbers
    # One light hairline per grid label (the chart's axis class).
    assert len(_ys(doc, draw.DRAWING_CHART_AXIS_CLASS)) >= len(numbers)


def test_a_higher_reading_is_drawn_higher_on_the_chart():
    doc = _chart([3900, 3950, 4000, 4050])
    ys = [float(h.attrs["cy"].rstrip("%")) for h in doc.find_all("circle", cls=draw.DRAWING_CHART_HIT_CLASS)]
    assert ys == sorted(ys, reverse=True), "the chart is inverted: a larger value has a smaller y"
    assert all(11.5 <= y <= 84.5 for y in ys), ys


def test_the_percentage_axis_never_passes_100_and_the_end_value_is_labelled():
    doc = _chart([4000, 4050, 4100, 4150, 4190], unit=battery_chart.UNIT_PERCENT)
    percents = [int(t[:-1]) for t in _texts(doc) if re.fullmatch(r"\d+%", t)]
    assert percents and max(percents) <= 100
    end = battery.percent(4190)
    assert "%d%%" % end in _texts(doc), "the latest value sits beside its marker"
    mark = doc.find_all("circle", cls=draw.DRAWING_CHART_MARK_CLASS)
    assert len(mark) == 1 and mark[0].attrs["cx"] == "100.00%"


def test_three_date_ticks_in_daily_mode_and_clock_ticks_for_raw_readings():
    daily = [t for t in _texts(_chart([4000 - i for i in range(9)], daily=True)) if re.fullmatch(r"\d{1,2} [A-Z][a-z]{2}", t)]
    assert len(daily) == 3, daily
    clock = [t for t in _texts(_chart([4000 - i for i in range(9)])) if re.fullmatch(r"\d\d:\d\d", t)]
    assert len(clock) == 3, clock


def test_the_threshold_is_a_dashed_labelled_line_with_a_tinted_zone_when_the_data_is_near_it():
    low = battery.low_display_mv()
    doc = _chart([low + 150 - i * 6 for i in range(20)])
    assert len(doc.find_all("line", cls=draw.DRAWING_CHART_THRESHOLD_CLASS)) == 1
    assert len(doc.find_all("rect", cls=draw.DRAWING_CHART_ZONE_CLASS)) == 1
    label = "Low battery \u2014 %d mV (\u2248 %d%%)" % (low, battery.LOW_BATTERY_DISPLAY_PERCENT)
    assert label in _texts(doc), "the line is named in words, not by colour or dashes alone"
    assert not doc.find_all("div", cls=draw.DRAWING_CHART_LEGEND_ROW_CLASS)


def test_a_threshold_far_below_the_data_is_not_drawn_and_a_caption_says_where_it_is():
    doc = _chart([4150 - i for i in range(20)])
    assert not doc.find_all("line", cls=draw.DRAWING_CHART_THRESHOLD_CLASS)
    assert not doc.find_all("rect", cls=draw.DRAWING_CHART_ZONE_CLASS)
    legend = doc.find("div", cls=draw.DRAWING_CHART_LEGEND_ROW_CLASS)
    assert "below the range shown" in legend.text()
    assert "%d mV" % battery.low_display_mv() in legend.text()


def test_the_percentage_view_names_its_threshold_in_percent():
    doc = _chart([battery.low_display_mv() + 60 - i * 4 for i in range(20)], unit=battery_chart.UNIT_PERCENT)
    assert "Low battery \u2014 %d%%" % battery.LOW_BATTERY_DISPLAY_PERCENT in _texts(doc)


def test_axis_labels_do_not_sit_on_the_threshold_label():
    doc = _chart([battery.low_display_mv() + 10 - i for i in range(20)], unit=battery_chart.UNIT_PERCENT)
    grid = {t for t in _texts(doc) if re.fullmatch(r"\d+%", t)}
    assert "0%" not in grid or "20%" not in grid


def test_dense_series_shrink_their_hit_targets_and_every_point_stays_reachable():
    few = _chart([4000 - i for i in range(5)]).find_all("circle", cls=draw.DRAWING_CHART_HIT_CLASS)
    many = _chart([4000 - i for i in range(90)]).find_all("circle", cls=draw.DRAWING_CHART_HIT_CLASS)
    assert {h.attrs["r"] for h in few} == {"8"} and {h.attrs["r"] for h in many} == {"4"}
    assert len(many) == 90
    assert [h.attrs["tabindex"] for h in many].count("0") == 1


def test_the_area_sits_under_the_line_inside_its_own_viewbox():
    doc = _chart([3900, 3950, 4000])
    layer = doc.find("svg", cls=draw.DRAWING_CHART_AREA_LAYER_CLASS)
    assert layer.attrs["viewbox"] == "0 0 100 100" and layer.attrs["aria-hidden"] == "true"
    points = [tuple(float(v) for v in p.split(",")) for p in layer.find("polygon").attrs["points"].split()]
    assert points[-1][1] == points[-2][1] == 84.5, "closed along the bottom of the plot"
    assert all(0 <= x <= 100 and 11.5 <= y <= 84.5 for x, y in points)


def test_the_chart_has_no_external_reference_and_no_inline_style():
    svg = battery_chart.battery_sparkline_svg(_rows([3900, 3950, 4000]), now=NOW)
    for forbidden in ("url(", "<image", "<script", "style="):
        assert forbidden not in svg


def test_fewer_than_the_minimum_readings_draw_no_chart():
    assert battery_chart.CHART_MIN_POINTS == 2
    assert battery_chart.battery_sparkline_svg(_rows([4000]), now=NOW) == ""


# --- the card ---------------------------------------------------------------

def _render(tmp_path, readings, lang="en"):
    shp.seed_device_health(str(tmp_path), readings)
    base = shp.now()
    try:
        prefs.set_request_prefs(lang=lang)
        rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    finally:
        prefs.set_request_prefs(lang="en")
    return rendered, parse_html(rendered), shp.health_row(rendered, "battery")


def _readings(values, step_minutes=15):
    base = shp.now()
    count = len(values)
    return [(shp.iso(base - timedelta(minutes=step_minutes * (count - 1 - i), seconds=20)), mv)
            for i, mv in enumerate(values)]


def test_the_card_defaults_to_percentage_with_a_radio_switch(tmp_path):
    _rendered, doc, _row = _render(tmp_path, _readings([3990, 3985, 3980, 3975]))
    group = doc.find("div", cls="battery-unit")
    assert group.attrs["role"] == "radiogroup" and "hidden" in group.attrs
    checked = [b.attrs["data-unit"] for b in group.find_all("button") if b.attrs["aria-checked"] == "true"]
    assert checked == ["percent"]
    views = {v.attrs["data-unit"]: v for v in doc.find_all("div", cls="battery-chart__view")}
    assert "hidden" not in views["percent"].attrs and "hidden" in views["mv"].attrs


def test_the_level_is_stated_once_and_the_voltage_beside_it(tmp_path):
    mv = 3975
    _rendered, doc, row = _render(tmp_path, _readings([3990, 3985, 3980, mv]))
    assert doc.find("div", cls="battery-gauge__value").find("b").text() == str(battery.percent(mv))
    assert doc.find("span", cls="battery-volt").text().replace("\xa0", " ").strip() == "%d mV" % mv
    head = row.select_one(".health-row__summary").text()
    assert "mV" not in head and "%" not in head, "the header no longer repeats the level"
    last = doc.find("span", cls="battery-last")
    assert last.text().startswith("Last reading \u00b7 ") and last.find("time") is not None


def test_the_readings_table_has_time_voltage_and_level_columns(tmp_path):
    values = [3990, 3985, 3980, 3975]
    _rendered, doc, row = _render(tmp_path, _readings(values))
    table = row.select_one("details.battery-readings table")
    assert [th.text() for th in table.find_all("th")] == ["Time", "Voltage", "Level"]
    body = table.find_all("tr")[1:]
    assert len(body) == len(values)
    for tr, mv in zip(body, reversed(values)):
        cells = [td.text() for td in tr.find_all("td")]
        assert cells[1] == "%d mV" % mv and cells[2] == "%d%%" % battery.percent(mv), cells
    assert "Latest" in body[0].text() and "Latest" not in body[1].text()
    assert row.select_one("details.battery-readings summary").text().strip() == "View 4 readings"
    assert "open" not in row.select_one("details.battery-readings").attrs


def test_a_normal_level_says_so_with_an_icon_and_words(tmp_path):
    _rendered, _doc, row = _render(tmp_path, _readings([3990, 3985, 3980, 3975]))
    pill = row.select_one(".battery-status")
    assert pill.text().strip() == "Level looks normal" and pill.find("svg") is not None
    assert row.attrs["data-state"] == "ok"
    assert not row.find_all("span", cls="charging-pill")


def test_a_low_level_is_a_warning_with_its_own_icon_and_words(tmp_path):
    low = battery.low_display_mv()
    _rendered, doc, row = _render(tmp_path, _readings([low + 20, low + 10, low - 5, low - 10]))
    pill = row.select_one(".battery-status")
    assert pill.text().strip() == "Level is low" and "battery-status--warn" in pill.attrs["class"]
    assert row.attrs["data-state"] == "warn"
    assert doc.find("svg", cls="drawing--warn") is not None, "the gauge turns amber below the mark"


def test_a_low_level_reads_in_french(tmp_path):
    low = battery.low_display_mv()
    _rendered, _doc, row = _render(tmp_path, _readings([low + 20, low - 5, low - 10]), lang="fr")
    assert row.select_one(".battery-status").text().strip() == "Le niveau est bas"
    assert row.select_one(".battery-last").text().startswith("Dernier relevé")
    assert [th.text() for th in row.select_one("table").find_all("th")] == ["Heure", "Tension", "Niveau"]


def test_one_reading_says_a_curve_needs_more_and_keeps_every_other_datum(tmp_path):
    rendered, doc, row = _render(tmp_path, _readings([3975]))
    note = row.select_one(".battery-chart__empty")
    assert "Not enough readings for a curve yet" in note.text()
    assert "A curve appears from 2 readings. 1 so far." in note.text()
    assert row.select_one(".battery-gauge") is not None and row.select_one(".battery-volt") is not None
    assert row.select_one("details.battery-readings") is not None
    assert not doc.find_all("svg", cls="sparkline__canvas")
    assert "battery-trend.js" not in rendered, "no chart, no script"


def test_no_reading_still_shows_the_empty_state_and_no_card(tmp_path):
    rendered = health_page_composition.render(shp.ctx(str(tmp_path)))
    row = shp.health_row(rendered, "battery")
    assert not row.find_all("div", cls="battery-gauge") and "No battery readings yet." in rendered


@pytest.mark.parametrize("state_text", ["Level looks normal"])
def test_the_health_row_keeps_its_always_open_body_and_no_row_chevron(tmp_path, state_text):
    _rendered, _doc, row = _render(tmp_path, _readings([3990, 3985, 3980, 3975]))
    assert row.select_one(".health-row__body") is not None
    assert row.attrs["class"] == "health-row"
    assert len(row.select_one(".health-row__summary").find_all("svg")) == 1, "only the state icon: no chevron"
    assert state_text in row.text()
    assert health_page._battery_verdict("ok", (4000, "x"))[0] == "ok"
