"""companion/battery_card.py: the body of the Health page's Battery row.

A gauge with the level as its hero and the voltage beside it, one
status pill for the verdict, one "last reading" line, the trend chart
under a Percentage/Voltage switch, and the readings table shown open
below the chart. The chart itself is companion/battery_chart.py.

Page-independent: the Health page module passes in the verdict (state
and words) and the series, and nothing here imports a page module. The
level is printed once (the gauge); the voltage once (beside it); a
verdict is never carried by colour alone (an icon and words).
"""

import companion.battery as battery
import companion.battery_chart as battery_chart
import companion.draw as draw
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html

GAUGE_SIZE_PX = 112

BATTERY_READOUT_ID = "battery-readout"

LOW_VERDICT_TEXT = i18n.msg("health.battery_low", "Level is low")
_LEVEL_GROUP_LABEL = i18n.msg("health.battery_level_group", "Battery level and voltage")
_LAST_READING_TEXT = i18n.msg("health.battery_last_reading", "Last reading")
_TIME_COLUMN_TEXT = i18n.msg("health.battery_col_time", "Time")
_LEVEL_COLUMN_TEXT = i18n.msg("health.battery_col_level", "Level")
_LATEST_TEXT = i18n.msg("health.battery_latest", "Latest")
_EMPTY_TITLE_TEXT = i18n.msg(
    "health.battery_chart_empty", "Not enough readings for a curve yet")
_EMPTY_BODY_TEMPLATE = i18n.msg(
    "health.battery_chart_empty_body", "A curve appears from %d readings. %d so far.")
_READINGS_HEADING_TEMPLATE = i18n.msg("health.battery_readings_heading", "Readings (%d)")

_STATE_ICON = {"ok": "icon-check", "warn": "icon-warning", "error": "icon-toast-error"}


def _gauge_html(percent):
    """The 270-degree gauge with the percentage in its centre and a tick at
    the low-battery mark. Green above the mark, amber below it."""
    status = draw.DRAWING_STATUS_WARN_CLASS if percent < battery.LOW_BATTERY_DISPLAY_PERCENT \
        else draw.DRAWING_STATUS_OK_CLASS
    svg = draw.arc_gauge(
        percent / 100.0, GAUGE_SIZE_PX, status,
        tick_fraction=battery.LOW_BATTERY_DISPLAY_PERCENT / 100.0)
    return (
        '<div class="battery-gauge">%s<div class="battery-gauge__value tnum">'
        "<b>%d</b><span>%%</span></div></div>") % (svg, percent)


def _status_pill_html(state, verdict):
    state = state if state in _STATE_ICON else "warn"
    return '<span class="battery-status battery-status--%s">%s<span>%s</span></span>' % (
        state, layout.icon_html(_STATE_ICON[state], size=18), escape_html(verdict))


def _hero_html(millivolts, ts, now, state, verdict, curve):
    percent = battery.percent(millivolts, curve)
    last = '%s · %s · %s' % (
        escape_html(i18n.t(_LAST_READING_TEXT)),
        escape_html(battery_chart._full_local_timestamp_text(ts)),
        layout.relative_time_html(ts, now, fallback=""))
    facts = (
        '<div class="battery-facts">%s'
        '<span class="battery-volt tnum">%d <small>mV</small></span>'
        '<span class="battery-last time-value">%s</span></div>'
    ) % (_status_pill_html(state, verdict), millivolts, last)
    return '<div class="battery-hero" role="group" aria-label="%s">%s%s</div>' % (
        escape_html(i18n.t(_LEVEL_GROUP_LABEL)),
        _gauge_html(percent) if percent is not None else "", facts)


def _chart_title_html(caption):
    """The caption naming the series, `(title, detail)` on two lines (the
    detail may be empty), over the readout line the script
    writes a hovered or focused point's reading into (hidden until the
    script runs)."""
    return (
        '<div class="battery-chart__title"><span class="battery-chart__caption">%s%s</span>'
        '<p id="%s" class="battery-readout" role="status" hidden>'
        '<span class="battery-readout__value tnum"></span>'
        '<span class="battery-readout__detail time-value"></span></p></div>'
    ) % (
        escape_html(caption[0]),
        "<small>%s</small>" % escape_html(caption[1]) if caption[1] else "",
        BATTERY_READOUT_ID)


def _empty_chart_html(reading_count):
    body = i18n.t(_EMPTY_BODY_TEMPLATE) % (battery_chart.CHART_MIN_POINTS, reading_count)
    return (
        '<div class="battery-chart battery-chart--empty"><div class="battery-chart__empty">'
        "%s<b>%s</b><span>%s</span></div></div>"
    ) % (layout.icon_html("icon-info", size=24), escape_html(i18n.t(_EMPTY_TITLE_TEXT)),
         escape_html(body))


def _chart_block_html(plot_rows, daily, caption, reading_count, now, curve, latest_mv):
    """The chart under its title row, or the too-little-data note when the
    series cannot draw a curve. Returns `(html, has_chart)`."""
    chart = battery_chart.battery_unit_chart(
        plot_rows, now=now, daily=daily, curve=curve, title_html=_chart_title_html(caption),
        latest_mv=latest_mv)
    if chart:
        return '<div class="battery-chart-wrap">%s</div>' % chart, True
    return '<div class="battery-chart-wrap">%s</div>' % _empty_chart_html(reading_count), False


def _readings_html(trend_rows, now, curve):
    """The readings table (Time, Voltage, Level; the level is the shared
    estimate of the voltage), shown open under the chart. The newest row is
    emphasised and tagged."""
    body_rows = []
    for index, row in enumerate(trend_rows):
        millivolts = row.get("battery_mv")
        numeric = isinstance(millivolts, int) and not isinstance(millivolts, bool)
        percent = battery.percent(millivolts, curve) if numeric else None
        when = layout.concise_timestamp_html(row.get("ts"), now, fallback="")
        if index == 0:
            when += '<span class="battery-latest">%s</span>' % escape_html(i18n.t(_LATEST_TEXT))
        body_rows.append((
            when,
            "%d mV" % millivolts if numeric else "",
            "%d%%" % percent if percent is not None else ""))
    table = layout.data_table(
        [i18n.t(_TIME_COLUMN_TEXT), i18n.t(battery_chart.BATTERY_UNIT_MV_LABEL),
         i18n.t(_LEVEL_COLUMN_TEXT)],
        body_rows, mono_columns=(1, 2), raw_columns=(0,), modifier="readings")
    return (
        '<section class="battery-readings" aria-labelledby="battery-readings-title">'
        '<h3 class="battery-readings__title" id="battery-readings-title">%s</h3>%s</section>'
    ) % (escape_html(i18n.t(_READINGS_HEADING_TEMPLATE) % len(trend_rows)), table)


def body_html(trend_rows, plot_rows, daily, caption, reading_count, latest, now,
              state, verdict, curve=None):
    """The Battery row's body. `latest` is the newest numeric reading's
    `(millivolts, ts)`; `plot_rows`/`daily` the series the chart draws and
    `caption` its words; `state`/`verdict` the status pill's state word and
    text. Returns `(html, has_chart)`; the page adds battery-trend.js only
    when there is a chart."""
    millivolts, ts = latest
    chart_html, has_chart = _chart_block_html(
        plot_rows, daily, caption, reading_count, now, curve, millivolts)
    html = (
        _hero_html(millivolts, ts, now, state, verdict, curve) + chart_html
        + _readings_html(trend_rows, now, curve))
    return html, has_chart
