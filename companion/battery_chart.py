"""companion/battery_chart.py: the battery-trend sparkline, built entirely
on companion/draw.py's shared scale and shape primitives.

Never imports a page module: this is presentation logic for one drawing,
consumed by the Health page module (which re-exports every name a test
or another module reads as its own attribute, so nothing outside this
file needs to know the chart moved here).

The chart's own class strings ("sparkline-hit", ...) are unchanged from
before this migration and re-declared in companion/draw.py's
DRAWING_CLASSES registry (as the DRAWING_CHART_* constants this module
aliases below), so `companion/static/battery-trend.js`'s `.sparkline-hit`
selectors and `style.css`'s `.sparkline*` rules keep working untouched,
and the class-resolves-in-CSS / no-colour-literal / escaping / no-script
drawing contract tests cover this chart the same way they cover every
other drawing.
"""
import math
from zoneinfo import ZoneInfo

import companion.battery as battery
import companion.draw as draw
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
from server import history_db

# --- the chart's own class vocabulary, aliased from draw.py's registry ---
# String values UNCHANGED from before this migration: battery-trend.js's
# selectors and style.css's `.sparkline*` rules are static assets and
# cannot be renamed alongside this Python refactor.
SPARKLINE_HIT_CLASS = draw.DRAWING_CHART_HIT_CLASS
SPARKLINE_LINE_CLASS = draw.DRAWING_CHART_LINE_CLASS
SPARKLINE_AXIS_CLASS = draw.DRAWING_CHART_AXIS_CLASS
# Two classes for two elements: a nested <svg> layer owning the
# coordinate system, and the filled <polygon> inside it.
SPARKLINE_AREA_LAYER_CLASS = draw.DRAWING_CHART_AREA_LAYER_CLASS
SPARKLINE_AREA_CLASS = draw.DRAWING_CHART_AREA_CLASS
SPARKLINE_MARK_CLASS = draw.DRAWING_CHART_MARK_CLASS
SPARKLINE_THRESHOLD_CLASS = draw.DRAWING_CHART_THRESHOLD_CLASS
SPARKLINE_LEGEND_ROW_CLASS = draw.DRAWING_CHART_LEGEND_ROW_CLASS
SPARKLINE_LEGEND_CLASS = draw.DRAWING_CHART_LEGEND_CLASS
SPARKLINE_LEGEND_SWATCH_CLASS = draw.DRAWING_CHART_LEGEND_SWATCH_CLASS
SPARKLINE_ZONE_CLASS = draw.DRAWING_CHART_ZONE_CLASS
SPARKLINE_TEXT_CLASS = draw.DRAWING_CHART_TEXT_CLASS
SPARKLINE_TEXT_STRONG_CLASS = draw.DRAWING_CHART_TEXT_STRONG_CLASS

# The section heading names the subject only: the plotted window is
# not part of it, so the chart's own accessible name reuses this text.
BATTERY_SECTION_HEADING = i18n.msg("health.battery", "Battery")

BATTERY_TREND_WINDOW_DAYS = 90  # The chart's primary window, 3 months.
# A display window only: nothing is deleted.



# --- geometry -----------------------------------------------------------
# The canvas is a fixed height (declared once more in style.css's
# `.battery-trend-section svg:not(.icon)` rule): every y coordinate below is
# a percentage of it. The plot sits between the top and bottom margins; the
# bottom margin holds the date labels, the top one the highest axis label.
CANVAS_HEIGHT_PX = 192
_PLOT_TOP_PERCENT = 11.5
_PLOT_BOTTOM_PERCENT = 84.5

# A chart needs two points to be a line; below that the card says so.
CHART_MIN_POINTS = 2

UNIT_MV = "mv"
UNIT_PERCENT = "percent"

_HIT_RADIUS_PX = 8
_MARK_RADIUS_PX = 6

# The point count at which hit targets of evenly spread points overlap on
# the narrowest chart (about 226 px): their radius then shrinks, and every
# point stays reachable from the keyboard.
_NARROWEST_CANVAS_PX = 226
_HIT_DIAMETER_FLOOR_PX = 6
_DENSE_POINT_THRESHOLD = int(_NARROWEST_CANVAS_PX / _HIT_DIAMETER_FLOOR_PX + 1) + 1
_DENSE_HIT_RADIUS_PX = 4

# Axis steps and the distance (in steps) at which the threshold joins the
# range: farther away the axis stays on the data and a caption says where
# the threshold is.
_STEP_MV = 100
_STEP_PERCENT = 20
_THRESHOLD_NEAR_STEPS = 1.5
# Axis labels this close to the threshold line, or to its label (which sits
# `_THRESHOLD_LABEL_DROP_PX` below it), are left out.
_LABEL_CLEARANCE_PX = 16
_THRESHOLD_LABEL_DROP_PX = 18


def _plot_value(unit, mv, curve=None):
    """The number a reading of `mv` plots at in `unit`: the millivolt
    reading itself, or the shared percentage estimate for it (0 when the
    estimate cannot resolve, so the point pins to the floor rather than
    vanishing).
    """
    if unit == UNIT_PERCENT:
        pct = battery.percent(mv, curve)
        return pct if pct is not None else 0
    return mv


def _fit_axis(values, threshold, step, ceiling=None):
    """`(axis_min, axis_max, threshold_in_range)` for a chart of `values`:
    a range fitted to the data (padded, on `step` boundaries, at least two
    steps tall) so a small real slope is visible. The threshold joins the
    range only when the data comes within `_THRESHOLD_NEAR_STEPS` of it.
    """
    low, high = min(values), max(values)
    span = max(high - low, step * 0.6)
    axis_min = math.floor((low - 0.15 * span) / step) * step
    axis_max = math.ceil((high + 0.15 * span) / step) * step
    if ceiling is not None:
        axis_max = min(axis_max, ceiling)
    if axis_max - axis_min < 2 * step:
        # Grow away from a ceiling the scale cannot pass.
        if ceiling is not None:
            axis_min = axis_max - 2 * step
        else:
            axis_max = axis_min + 2 * step
    near = low - threshold <= _THRESHOLD_NEAR_STEPS * step
    if near:
        axis_min = min(axis_min, math.floor((threshold - 0.3 * step) / step) * step)
    if ceiling is not None:
        axis_min = max(axis_min, 0)
    return axis_min, axis_max, near


def _y_percent(value, axis_min, axis_max):
    """The y position of `value` on the fitted axis, as a percentage of
    the canvas height (inverted: larger value, smaller y)."""
    fraction = (value - axis_min) / float(axis_max - axis_min)
    fraction = max(0.0, min(1.0, fraction))
    return _PLOT_TOP_PERCENT + (_PLOT_BOTTOM_PERCENT - _PLOT_TOP_PERCENT) * (1 - fraction)


def _px(percent):
    return percent * CANVAS_HEIGHT_PX / 100.0


# The hover/tap readout's text, as constants so the French catalogue
# (companion/i18n_fr/health.py) carries them.
BATTERY_AVERAGE_WHEN_ONE_TEMPLATE = i18n.msg(
    "health.daily_average_reading", "%s — daily average (%d reading)")
BATTERY_AVERAGE_WHEN_MANY_TEMPLATE = i18n.msg(
    "health.daily_average_readings", "%s — daily average (%d readings)")
BATTERY_AVERAGE_WHEN_BARE_TEMPLATE = i18n.msg(
    "health.daily_average", "%s — daily average")

# The drawn low-battery threshold's label names what the line means, not
# just what it is worth. Prints the percentage beside the level because
# the level is the millivolt reading at which battery.py's estimate
# returns that percentage, tying the line to the same figure the readout
# and ring print above the chart.
BATTERY_THRESHOLD_LABEL_TEMPLATE = i18n.msg(
    "health.low_battery_mv", "Low battery — %d mV (≈ %d%%)")
BATTERY_THRESHOLD_PERCENT_LABEL_TEMPLATE = i18n.msg(
    "health.low_battery_pct", "Low battery — %d%%")

# The caption under a chart whose range does not reach the threshold: the
# line is then not drawn, and this says where it is instead of stretching
# the axis down to it.
BATTERY_THRESHOLD_OFF_RANGE_TEMPLATE = i18n.msg(
    "health.low_battery_off_range",
    "Low battery: %d mV (\u2248 %d%%), below the range shown")
BATTERY_THRESHOLD_OFF_RANGE_PERCENT_TEMPLATE = i18n.msg(
    "health.low_battery_off_range_pct", "Low battery: %d%%, below the range shown")

BATTERY_UNIT_GROUP_LABEL = i18n.msg("health.battery_unit_group", "Battery chart unit")
BATTERY_UNIT_PERCENT_LABEL = i18n.msg("health.battery_unit_percent", "Percentage")
BATTERY_UNIT_MV_LABEL = i18n.msg("health.battery_unit_voltage", "Voltage")

# The sentinel and helper live in companion/layout.py, since the
# freshness line this page shares with Home and the Display scope needs
# the same full local timestamp, and a page module cannot import another.
_FULL_TIMESTAMP_SENTINEL_NOW = layout.FULL_TIMESTAMP_SENTINEL_NOW


def _full_local_timestamp_text(ts):
    """"D Mon HH:MM" in Europe/Paris — see
    `layout.full_local_timestamp_text()`, of which this is the delegate.
    """
    return layout.full_local_timestamp_text(ts)


def _as_paris(parsed):
    """A naive datetime is taken as UTC (matching
    `history_db.utc_now_iso()`'s output), then converted to
    Europe/Paris. Shared by every helper below that renders a battery
    timestamp, so there is exactly one place a stored `ts` crosses into
    local wall-clock time.
    """
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(layout.LOCAL_TZ)


def _axis_clock_label(ts):
    """"HH:MM" Europe/Paris clock text for a battery-chart X-axis label.
    Built through `layout.local_clock_text()` with no `now_parsed`,
    which keeps this a bare clock rather than the day-qualified form.
    Falls back to the raw `ts` string, never raising, when it fails to
    parse.
    """
    parsed = layout.parse_iso(ts)
    return layout.local_clock_text(parsed) if parsed is not None else (ts or "")


def _axis_day_label(ts):
    """"D Mon" X-axis label for the chart's daily mode, for a `ts` that
    names a whole Europe/Paris calendar day: `_axis_clock_label()` would
    parse it fine but print "00:00" for every day, hence this sibling.
    Uses `layout.month_abbr()`, not `strftime`'s locale-dependent
    directive. Falls back to the raw `ts` string when it fails to parse.
    """
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return ts or ""
    local = _as_paris(parsed)
    return "%d %s" % (local.day, layout.month_abbr(local.month))


def _battery_reading_parts(mv, ts, now, curve=None):
    """The plain-text `(value, when)` pair every rendering of one
    battery reading shares, computed once so they can't drift apart.
    `value` is "≈ NN% · {mv} mV" when the estimate resolves, else bare
    "{mv} mV" (the frame's own warning uses the exact mV threshold, not
    this estimate). Returns unescaped text, not markup: `battery-trend.js`
    rewrites the readout via `textContent`, which would destroy markup.
    """
    pct = battery.percent(mv, curve)
    value = ("≈ %d%% · %s mV" % (pct, mv)) if pct is not None else ("%s mV" % mv)
    age = layout.age_seconds(ts, now)
    if age is None:
        return value, (ts or "")
    when = "%s (%s)" % (_full_local_timestamp_text(ts), layout.relative_age_text(age))
    return value, when


def _daily_reading_parts(mv, ts, reading_count):
    """`_battery_reading_parts()`'s sibling for a daily-average chart
    point: names that the value is an average, not a raw reading, so a
    hovered point can't be mistaken for the resting readout. Degrades to
    a bare "daily average" phrase when `reading_count` is missing or not
    a positive int, since naming zero or an unknown count would mislead.
    """
    value = "%d mV" % mv
    day_label = _axis_day_label(ts)
    if isinstance(reading_count, int) and not isinstance(reading_count, bool) and reading_count > 0:
        template = (BATTERY_AVERAGE_WHEN_ONE_TEMPLATE if reading_count == 1
                    else BATTERY_AVERAGE_WHEN_MANY_TEMPLATE)
        when = i18n.t(template) % (day_label, reading_count)
    else:
        when = i18n.t(BATTERY_AVERAGE_WHEN_BARE_TEMPLATE) % day_label
    return value, when



def _threshold_for(unit, curve):
    """`(threshold_value, label_text, off_range_text)` for `unit`."""
    low_mv = battery.low_display_mv(curve)
    if unit == UNIT_PERCENT:
        pct = battery.LOW_BATTERY_DISPLAY_PERCENT
        return (
            pct,
            i18n.t(BATTERY_THRESHOLD_PERCENT_LABEL_TEMPLATE) % pct,
            i18n.t(BATTERY_THRESHOLD_OFF_RANGE_PERCENT_TEMPLATE) % pct)
    return (
        low_mv,
        i18n.t(BATTERY_THRESHOLD_LABEL_TEMPLATE) % (low_mv, battery.LOW_BATTERY_DISPLAY_PERCENT),
        i18n.t(BATTERY_THRESHOLD_OFF_RANGE_TEMPLATE) % (low_mv, battery.LOW_BATTERY_DISPLAY_PERCENT))


def _hit_attrs(value, ts, reading_count, is_latest, now, daily, unit, plotted_value, curve):
    """The attributes of one point's hit target: its reading and time, a
    tooltip, and the roving tabindex (only the latest point is a Tab stop;
    battery-trend.js moves between the others with the arrow keys)."""
    if daily:
        _value_text, when_text = _daily_reading_parts(value, ts, reading_count)
    else:
        _value_text, when_text = _battery_reading_parts(value, ts, now, curve)
    # `ts` is coerced to "" for a non-string value; every value is escaped
    # once, by draw._attrs().
    attrs = {
        "tabindex": "0" if is_latest else "-1",
        "role": "button",
        "data-mv": value,
        "data-ts": ts if isinstance(ts, str) else "",
        "data-when": when_text,
        "aria-label": when_text,
        "title": when_text,
    }
    if unit == UNIT_PERCENT:
        # The readout text of this view, so the script never converts a unit.
        attrs["data-reading"] = "\u2248 %d%%" % plotted_value
    return attrs


def _points_and_marks(pairs, axis, now, daily, unit, curve, end_value=None):
    """`(points, markup)`: `points` is the `[(x, y), ...]` percentage list
    the area plots against; `markup` is every line segment, the end mark
    and every hit target, in paint order. The end mark sits at the last
    point's x, at `end_value` (the latest reading) when that differs from
    the plotted value (a daily average), else on the point."""
    point_count = len(pairs)
    end_y = None if end_value is None else _y_percent(end_value, *axis)
    hit_radius = _DENSE_HIT_RADIUS_PX if point_count >= _DENSE_POINT_THRESHOLD else _HIT_RADIUS_PX
    points, segments, circles = [], [], []
    for index, (value, ts, reading_count) in enumerate(pairs):
        plotted_value = _plot_value(unit, value, curve)
        x, y = draw.percent_x(index, point_count), _y_percent(plotted_value, *axis)
        if points:
            prev_x, prev_y = points[-1]
            segments.append(draw.line(
                SPARKLINE_LINE_CLASS, draw.percent_attr(prev_x), draw.percent_attr(prev_y),
                draw.percent_attr(x), draw.percent_attr(y)))
        points.append((x, y))
        is_latest = index == point_count - 1
        cx, cy = draw.percent_attr(x), draw.percent_attr(y)
        if is_latest:
            circles.append(draw.circle(
                SPARKLINE_MARK_CLASS, cx, cy if end_y is None else draw.percent_attr(end_y),
                _MARK_RADIUS_PX, attrs={"aria-hidden": "true"}))
        circles.append(draw.circle(SPARKLINE_HIT_CLASS, cx, cy, hit_radius, attrs=_hit_attrs(
            value, ts, reading_count, is_latest, now, daily, unit, plotted_value, curve)))
    return points, "".join(segments) + "".join(circles)


def _area_layer(points):
    """The faded area under the line: a nested private-viewBox <svg>
    (percentages are not allowed in a <polygon>), closed at the plot's
    bottom edge. The fade is the stylesheet's (a mask), never a gradient
    reference."""
    coords = " ".join("%.2f,%.2f" % point for point in points)
    coords += " %.2f,%.2f %.2f,%.2f" % (
        points[-1][0], _PLOT_BOTTOM_PERCENT, points[0][0], _PLOT_BOTTOM_PERCENT)
    return draw.area_canvas(
        SPARKLINE_AREA_LAYER_CLASS, 100, 100, draw.polygon(SPARKLINE_AREA_CLASS, coords))


def _clashes_with_threshold(baseline_px, threshold_px):
    """True when an axis label whose baseline is `baseline_px` would touch
    the threshold line or the threshold label drawn just below it."""
    return threshold_px - _LABEL_CLEARANCE_PX < baseline_px < threshold_px + _THRESHOLD_LABEL_DROP_PX + 6


def _grid(axis, unit, threshold_y):
    """The light horizontal grid lines and their labels, the labels sitting
    just above their line. A label near the threshold's own is left out."""
    axis_min, axis_max, step = axis[0], axis[1], _STEP_PERCENT if unit == UNIT_PERCENT else _STEP_MV
    suffix = "%" if unit == UNIT_PERCENT else " mV"
    lines, labels = [], []
    for value in range(int(axis_min), int(axis_max) + 1, step):
        y = _y_percent(value, axis_min, axis_max)
        lines.append(draw.rect(
            SPARKLINE_AXIS_CLASS, 0, draw.percent_attr(y), "100%", 1,
            attrs={"aria-hidden": "true"}))
        if threshold_y is not None and _clashes_with_threshold(_px(y) - 6, _px(threshold_y)):
            continue
        labels.append(draw.text(
            SPARKLINE_TEXT_CLASS, 0, draw.percent_attr(y), "%d%s" % (value, suffix),
            attrs={"dy": "-6", "aria-hidden": "true"}))
    return "".join(lines), "".join(labels)


def _threshold_layers(threshold_y, label_text):
    """`(zone, rule, label)` of the low-battery threshold: the tinted zone
    below the line, the dashed line and its label (dashed and worded,
    never colour alone)."""
    zone = draw.rect(
        SPARKLINE_ZONE_CLASS, 0, draw.percent_attr(threshold_y), "100%",
        draw.percent_attr(_PLOT_BOTTOM_PERCENT - threshold_y), attrs={"aria-hidden": "true"})
    rule = draw.line(
        SPARKLINE_THRESHOLD_CLASS, 0, draw.percent_attr(threshold_y), "100%",
        draw.percent_attr(threshold_y), attrs={"aria-hidden": "true"})
    label = draw.text(
        SPARKLINE_TEXT_STRONG_CLASS, 0, draw.percent_attr(threshold_y), label_text,
        attrs={"dy": str(_THRESHOLD_LABEL_DROP_PX)})
    return zone, rule, label


def _end_and_date_labels(pairs, end_y, end_text, daily):
    """The latest value beside its marker, and the three date ticks."""
    # Above the marker, or below it when there is no room above.
    end_dy = "-12" if _px(end_y) - 12 >= 14 else "24"
    end_label = draw.text(
        SPARKLINE_TEXT_STRONG_CLASS, "100%", draw.percent_attr(end_y), end_text,
        attrs={"dx": "-4", "dy": end_dy, "text-anchor": "end", "aria-hidden": "true"})
    tick = _axis_day_label if daily else _axis_clock_label
    count = len(pairs)
    stops = [("0", 0, "start"), ("100%", count - 1, "end")]
    if count > 2:
        stops.insert(1, ("50%", count // 2, "middle"))
    ticks = "".join(
        draw.text(
            SPARKLINE_TEXT_CLASS, x, "100%", tick(pairs[index][1]),
            attrs={"dy": "-8", "text-anchor": anchor, "aria-hidden": "true"})
        for x, index, anchor in stops)
    return end_label + ticks


def _legend_row(text):
    """The caption under a chart whose threshold is off its range."""
    return (
        '<div class="%s"><span class="%s"><span class="%s" aria-hidden="true"></span>%s</span></div>'
    ) % (SPARKLINE_LEGEND_ROW_CLASS, SPARKLINE_LEGEND_CLASS, SPARKLINE_LEGEND_SWATCH_CLASS,
         escape_html(text))


def battery_sparkline_svg(rows, now=None, daily=False, unit=UNIT_MV, curve=None, latest_mv=None):
    """The battery-trend chart built server-side from `rows` (newest-first),
    with no external reference of any kind (`url(`, `<image`, a script
    tag). Every point carries a transparent, keyboard-focusable hit target
    with a `<title>` tooltip, so its reading is available with no script.

    The canvas has no `viewBox`: every x is a percentage of its width,
    every y a percentage of its fixed height, every size an absolute CSS
    pixel. Drawn: a light grid whose labels sit on the lines, a faded area,
    the line, a marker on the newest point with its value, three date
    ticks and the low-battery threshold (a dashed, labelled line with the
    zone below it tinted). The y range is fitted to the data; the
    threshold joins it only when the data comes near it, otherwise a
    caption below the chart says it is under the range.

    Returns `""` when fewer than `CHART_MIN_POINTS` rows carry a numeric
    `battery_mv`. `unit` is `UNIT_MV` or `UNIT_PERCENT` (the shared
    estimate of each reading). `daily=True` plots daily aggregates:
    date ticks and point readouts switch to their day-aware siblings.
    `latest_mv` is the newest raw reading: the end marker and its label
    show it (the gauge's value) even when the curve's last point is a
    daily average. It defaults to the last plotted reading.
    """
    if now is None:
        now = history_db.utc_now_iso()
    pairs = [
        (row.get("battery_mv"), row.get("ts"), row.get("reading_count"))
        for row in reversed(rows)
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool)
    ]
    if len(pairs) < CHART_MIN_POINTS:
        return ""
    percent_unit = unit == UNIT_PERCENT
    values = [_plot_value(unit, pair[0], curve) for pair in pairs]
    numeric = isinstance(latest_mv, int) and not isinstance(latest_mv, bool)
    end_value = _plot_value(unit, latest_mv, curve) if numeric else values[-1]
    threshold, label_text, off_range_text = _threshold_for(unit, curve)
    axis_min, axis_max, near = _fit_axis(
        values + [end_value], threshold, _STEP_PERCENT if percent_unit else _STEP_MV,
        ceiling=100 if percent_unit else None)
    axis = (axis_min, axis_max)
    threshold_y = _y_percent(threshold, *axis) if near else None

    points, points_markup = _points_and_marks(
        pairs, axis, now, daily, unit, curve, end_value)
    grid_lines, grid_labels = _grid(axis, unit, threshold_y)
    zone, rule, threshold_label = (
        _threshold_layers(threshold_y, label_text) if near else ("", "", ""))
    end_text = ("%d%%" % end_value) if percent_unit else "%d mV" % end_value
    labels = grid_labels + threshold_label + _end_and_date_labels(
        pairs, _y_percent(end_value, *axis), end_text, daily)

    heading = i18n.t(BATTERY_SECTION_HEADING)
    if percent_unit:
        heading = "%s \u2014 %s" % (heading, i18n.t(BATTERY_UNIT_PERCENT_LABEL))
    svg_html = draw.percent_canvas(
        draw.DRAWING_CHART_CANVAS_CLASS,
        zone + grid_lines + _area_layer(points) + rule + points_markup + labels,
        label=heading)
    return '<div class="%s">%s%s</div>' % (
        draw.DRAWING_CHART_GRID_CLASS, svg_html, "" if near else _legend_row(off_range_text))


def _unit_button(unit, label, selected):
    return (
        '<button type="button" role="radio" class="battery-unit__option" data-unit="%s" '
        'aria-checked="%s" tabindex="%s">%s</button>'
    ) % (unit, "true" if selected else "false", "0" if selected else "-1", escape_html(label))


def battery_unit_chart(
        rows, now=None, daily=False, curve=None, title_html="", latest_mv=None):
    """The chart block: a title row (`title_html`, already-safe markup, and
    the Percentage/Voltage control) over the two views, both built
    server-side from the same `rows` inside one `.battery-chart` wrapper.
    Percentage is the default view. `latest_mv` is the newest raw reading
    (see `battery_sparkline_svg()`). Returns `""` when there is nothing to
    plot.

    The control is `hidden` until `battery-trend.js` runs, since it only
    works with the script; without it the percentage chart simply stays
    visible. The script swaps which view is shown and never converts a
    value itself.
    """
    percent_chart = battery_sparkline_svg(
        rows, now=now, daily=daily, unit=UNIT_PERCENT, curve=curve, latest_mv=latest_mv)
    if not percent_chart:
        return ""
    mv_chart = battery_sparkline_svg(
        rows, now=now, daily=daily, unit=UNIT_MV, curve=curve, latest_mv=latest_mv)
    control = (
        '<div class="battery-unit" role="radiogroup" aria-label="%s" hidden>%s%s</div>'
    ) % (
        escape_html(i18n.t(BATTERY_UNIT_GROUP_LABEL)),
        _unit_button(UNIT_PERCENT, i18n.t(BATTERY_UNIT_PERCENT_LABEL), True),
        _unit_button(UNIT_MV, i18n.t(BATTERY_UNIT_MV_LABEL), False))
    return (
        '<div class="battery-chart"><div class="battery-chart__top">%s%s</div>'
        '<div class="battery-chart__view" data-unit="%s">%s</div>'
        '<div class="battery-chart__view" data-unit="%s" hidden>%s</div>'
        "</div>"
    ) % (title_html, control, UNIT_PERCENT, percent_chart, UNIT_MV, mv_chart)
