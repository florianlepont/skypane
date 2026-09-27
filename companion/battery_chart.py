"""companion/battery_chart.py: the battery-trend sparkline, built entirely
on companion/draw.py's shared scale and shape primitives.

Never imports a page module: this is presentation logic for one drawing,
consumed by companion/pages/health_page.py (which re-exports every name a
test or another module reads as `health_page.X`, so nothing outside this
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
import functools
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
SPARKLINE_DOT_CLASS = draw.DRAWING_CHART_DOT_CLASS
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
SPARKLINE_AXIS_LABEL_CLASS = draw.DRAWING_CHART_AXIS_LABEL_CLASS

# "%d" is interpolated with BATTERY_TREND_WINDOW_DAYS // 30 at the one
# call site below, never a typed literal, so the heading cannot silently
# drift from the window the chart plots. health_page.py's own visible
# `<h2>` heading interpolates the same two constants, imported from here.
BATTERY_SECTION_HEADING_TEMPLATE = "Battery · %d months"

BATTERY_TREND_WINDOW_DAYS = 90  # The chart's primary window, locked at
# 3 months by explicit request. A display window only: nothing is deleted.

# No hand-estimated gutter: the CSS-grid label column is sized `auto`,
# so the browser measures the real widest-label width. With no viewBox,
# cx is a percentage of the canvas's own rendered width, so the canvas
# is the plot area edge to edge.

# Declared once here and in style.css's `.battery-trend-section
# svg:not(.icon)` rule: every point coordinate is a percentage of this
# height, so a responsive height would silently move every point.
_SPARKLINE_CANVAS_HEIGHT_PX = 160

# Vertical margin the plotted line never crosses, as a percent of canvas
# height: at least the marker's own radius so no dot is clipped, and set
# to half the axis label's line box so labels centre on the level they name.
_SPARKLINE_VERTICAL_INSET_PERCENT = 3.75

# A fixed Y-axis range, never auto-scaled: auto-scaling pinned a flat
# series to the canvas bottom and stretched a tiny real wiggle to fill
# the whole range. The percentage beside the chart comes from a
# different, piecewise discharge curve, so equal vertical distances here
# are not equal percentages. A reading below 3000 mV clamps to the floor.
SPARKLINE_Y_MIN_MV = 3000
SPARKLINE_Y_MAX_MV = 4200

_SPARKLINE_DOT_RADIUS_PX = 3
_SPARKLINE_HIT_RADIUS_PX = 8

# Strictly larger than the dot radius so the mark reads as a mark, and
# no larger than the vertical inset so it isn't clipped at the edge.
_SPARKLINE_MARK_RADIUS_PX = 5

# The point count at which the daily chart's cosmetic dots stop reading
# as separate marks. Derived from a live-measured 226px canvas width at
# a 375px viewport with a 90-day dataset.
_SPARKLINE_NARROWEST_CANVAS_PX = 226


def _sparkline_dense_threshold(canvas_width_px):
    """The first integer point count at which evenly spread points sit
    closer together than the cosmetic dot's own diameter, for a canvas
    `canvas_width_px` CSS pixels wide. The server cannot know a client's
    actual rendered width (no viewBox), so this is always called with
    the narrowest width this project has measured — conservative, not a
    guarantee for a still-narrower container.
    """
    spacing_ceiling_px = 2 * _SPARKLINE_DOT_RADIUS_PX
    return int(canvas_width_px / spacing_ceiling_px + 1) + 1


_SPARKLINE_DENSE_POINT_THRESHOLD = _sparkline_dense_threshold(_SPARKLINE_NARROWEST_CANVAS_PX)

# The reduced hit-target radius at/above the density threshold: smaller
# than the normal 8px so heavily overlapping hit circles no longer
# nearly-fully overlap; every point stays reachable via the
# roving-tabindex/arrow-key keyboard path, which is unaffected.
_SPARKLINE_DENSE_HIT_RADIUS_PX = 4

# The y position `value` gets on the battery chart, as a percentage of
# canvas height. Shared by every non-reading chart element (area
# baseline, threshold line) so none can drift from the plotted line.
# Clamped into the fixed Y range by draw.percent_y() itself, so an
# out-of-range value draws pinned at the canvas edge; inverted there to
# match SVG's top-down axis. A functools.partial, not a `def`: the
# geometry is entirely draw.percent_y()'s own, this only binds the
# chart's fixed domain and inset to it.
sparkline_point_y = functools.partial(
    draw.percent_y, domain_min=SPARKLINE_Y_MIN_MV, domain_max=SPARKLINE_Y_MAX_MV,
    inset_percent=_SPARKLINE_VERTICAL_INSET_PERCENT)

# The hover/tap readout's text, as constants so the French catalogue
# (companion/i18n_fr/health.py) carries them.
BATTERY_AVERAGE_WHEN_ONE_TEMPLATE = "%s — daily average (%d reading)"
BATTERY_AVERAGE_WHEN_MANY_TEMPLATE = "%s — daily average (%d readings)"
BATTERY_AVERAGE_WHEN_BARE_TEMPLATE = "%s — daily average"

# The drawn low-battery threshold's label names what the line means, not
# just what it is worth. Prints the percentage beside the level because
# the level is the millivolt reading at which battery.py's estimate
# returns that percentage, tying the line to the same figure the readout
# and ring print above the chart.
BATTERY_THRESHOLD_LABEL_TEMPLATE = "Low battery — %d mV (≈ %d%%)"

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


def _battery_reading_parts(mv, ts, now):
    """The plain-text `(value, when)` pair every rendering of one
    battery reading shares, computed once so they can't drift apart.
    `value` is "≈ NN% · {mv} mV" when the estimate resolves, else bare
    "{mv} mV" (the frame's own warning uses the exact mV threshold, not
    this estimate). Returns unescaped text, not markup: `battery-trend.js`
    rewrites the readout via `textContent`, which would destroy markup.
    """
    pct = battery.battery_percent(mv)
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


def _sparkline_axis_chrome(point_count):
    """The six axis/tick <rect> elements: the Y axis, the X axis, then
    the Y max/min ticks (poking into the label gap) and the X oldest/
    newest ticks (hanging below the axis).
    """
    return "".join((
        draw.rect(SPARKLINE_AXIS_CLASS, 0, 0, 1, "100%", attrs={"aria-hidden": "true"}),
        draw.rect(SPARKLINE_AXIS_CLASS, 0, "100%", "100%", 1, attrs={"aria-hidden": "true"}),
        draw.rect(SPARKLINE_AXIS_CLASS, -4, draw.percent_attr(sparkline_point_y(SPARKLINE_Y_MAX_MV)),
                  4, 1, attrs={"aria-hidden": "true"}),
        draw.rect(SPARKLINE_AXIS_CLASS, -4, draw.percent_attr(sparkline_point_y(SPARKLINE_Y_MIN_MV)),
                  4, 1, attrs={"aria-hidden": "true"}),
        draw.rect(SPARKLINE_AXIS_CLASS, draw.percent_attr(draw.percent_x(0, point_count)),
                  "100%", 1, 4, attrs={"aria-hidden": "true"}),
        draw.rect(SPARKLINE_AXIS_CLASS, draw.percent_attr(draw.percent_x(point_count - 1, point_count)),
                  "100%", 1, 4, attrs={"aria-hidden": "true"}),
    ))


def _sparkline_area_layer(plotted):
    """The filled area under the trend line: a nested, private-viewBox
    <svg> (percentages aren't permitted in a <polygon> points list), its
    vertices at the exact coordinates the chart's own points plot, closed
    at the axis minimum rather than the canvas edge — the scale's own
    floor, not a per-render min/max. Fill is `currentColor` at reduced
    opacity (style.css), never a `<linearGradient>`, which could only be
    referenced via `url(#id)` — forbidden by companion/draw.py's
    no-external-reference guarantee.
    """
    baseline_y = sparkline_point_y(SPARKLINE_Y_MIN_MV)
    points = " ".join("%.2f,%.2f" % (x, y) for x, y in plotted) + " %.2f,%.2f %.2f,%.2f" % (
        plotted[-1][0], baseline_y, plotted[0][0], baseline_y)
    return draw.area_canvas(
        SPARKLINE_AREA_LAYER_CLASS, 100, 100,
        draw.polygon(SPARKLINE_AREA_CLASS, points))


def _sparkline_points_and_marks(pairs, point_count, now, daily):
    """`(plotted, markup)` for every reading: `plotted` is the
    `[(x, y), ...]` coordinate list the area layer plots against, and
    `markup` is every line segment, cosmetic dot/mark and hit-target
    circle, in SVG paint order (a cosmetic marker immediately before its
    own hit target, never after — `.sparkline-dot`'s `pointer-events:
    none` is what actually lets a tap reach the target regardless of
    order).
    """
    dense = point_count >= _SPARKLINE_DENSE_POINT_THRESHOLD
    hit_radius = _SPARKLINE_DENSE_HIT_RADIUS_PX if dense else _SPARKLINE_HIT_RADIUS_PX

    plotted = []
    line_segments = []
    circles = []
    prev_point = None
    for index, (value, ts, reading_count) in enumerate(pairs):
        x = draw.percent_x(index, point_count)
        y = sparkline_point_y(value)
        plotted.append((x, y))
        if prev_point is not None:
            prev_x, prev_y = prev_point
            line_segments.append(draw.line(
                SPARKLINE_LINE_CLASS, draw.percent_attr(prev_x), draw.percent_attr(prev_y),
                draw.percent_attr(x), draw.percent_attr(y)))
        prev_point = (x, y)

        # Computed from `pairs`, never the caller's raw rows: the newest
        # stored row may carry no battery_mv, and a mark derived from it
        # would point at a reading the chart never plotted.
        is_latest = index == point_count - 1
        cx, cy = draw.percent_attr(x), draw.percent_attr(y)

        # Above the density threshold the cosmetic dot is suppressed but
        # the hit target below still emits at a reduced radius, so every
        # point stays reachable. The latest point always gets the mark
        # (a different class, emitted here rather than a second circle
        # appended afterwards, to stay inside the roving-tabindex
        # sequence the hit targets establish).
        if is_latest:
            circles.append(draw.circle(
                SPARKLINE_MARK_CLASS, cx, cy, _SPARKLINE_MARK_RADIUS_PX,
                attrs={"aria-hidden": "true"}))
        elif not dense:
            circles.append(draw.circle(
                SPARKLINE_DOT_CLASS, cx, cy, _SPARKLINE_DOT_RADIUS_PX,
                attrs={"aria-hidden": "true"}))

        if daily:
            _value_text, when_text = _daily_reading_parts(value, ts, reading_count)
        else:
            _value_text, when_text = _battery_reading_parts(value, ts, now)
        # Tooltip, aria-label and data-when carry the same string, never
        # a "value — when" composite: battery-trend.js's reveal() writes
        # data-mv into the readout separately and prepends its own
        # " — ", so duplicating the value here would print it twice.
        # Passed RAW (never pre-escaped) into `attrs`: draw._attrs()
        # escapes every value exactly once, so pre-escaping here would
        # double-escape. `ts` is coerced to "" for a non-string value
        # (e.g. None) the same way `escape_html(None)` used to.
        ts_text = ts if isinstance(ts, str) else ""
        # Roving tabindex: only the latest (rightmost) point is a normal
        # Tab stop; every other point is reachable via
        # battery-trend.js's arrow-key handler instead.
        tabindex = "0" if is_latest else "-1"
        circles.append(draw.circle(
            SPARKLINE_HIT_CLASS, cx, cy, hit_radius, attrs={
                "tabindex": tabindex,
                "role": "button",
                "data-mv": value,
                "data-ts": ts_text,
                "data-when": when_text,
                "aria-label": when_text,
                "title": when_text,
            }))
    return plotted, "".join(line_segments) + "".join(circles)


def _sparkline_threshold(pairs):
    """`(rect_markup, legend_markup)` for the low-battery threshold, or
    `("", "")` when `battery.LOW_BATTERY_DISPLAY_MV` falls outside the
    chart's fixed range — `sparkline_point_y()` clamps, so an
    out-of-range threshold would draw pinned to the axis edge and
    falsely read as "low starts at the bottom". Placed by the same
    `sparkline_point_y()` every reading uses, so it cannot drift from
    the readings it is compared against.
    """
    threshold_mv = battery.LOW_BATTERY_DISPLAY_MV
    if not (isinstance(threshold_mv, int) and not isinstance(threshold_mv, bool)
            and SPARKLINE_Y_MIN_MV < threshold_mv < SPARKLINE_Y_MAX_MV):
        return "", ""
    rect_markup = draw.rect(
        SPARKLINE_THRESHOLD_CLASS, 0, draw.percent_attr(sparkline_point_y(threshold_mv)),
        "100%", 1, attrs={"aria-hidden": "true"})
    # A legend in its own row, not a third Y-label (the threshold sits
    # at its own level, not top/bottom/middle). Not aria-hidden, unlike
    # the axis labels: nothing else announces where "low" starts.
    legend_markup = (
        '<div class="%s">'
        '<span class="%s"><span class="%s" aria-hidden="true"></span>%s</span>'
        "</div>"
    ) % (
        SPARKLINE_LEGEND_ROW_CLASS, SPARKLINE_LEGEND_CLASS, SPARKLINE_LEGEND_SWATCH_CLASS,
        escape_html(i18n.t(BATTERY_THRESHOLD_LABEL_TEMPLATE)
                    % (threshold_mv, battery.LOW_BATTERY_DISPLAY_PERCENT)),
    )
    return rect_markup, legend_markup


def _sparkline_axis_labels(pairs, daily):
    """`(y_labels_html, x_labels_html)`: the fixed Y max/min level labels
    and the oldest/newest X labels, every one a `draw.label_span()` in
    the chart's own axis-label class. Document order places max above
    min, oldest before newest (both flex containers use
    space-between). The Y labels print the fixed SPARKLINE_Y_MIN_MV/MAX_MV
    constants, never a per-render min/max, so the axis matches the
    fixed range `sparkline_point_y()` draws against.
    """
    y_labels_html = '<div class="%s">%s%s</div>' % (
        draw.DRAWING_CHART_Y_LABELS_CLASS,
        draw.label_span("%d mV" % SPARKLINE_Y_MAX_MV, class_name=SPARKLINE_AXIS_LABEL_CLASS),
        draw.label_span("%d mV" % SPARKLINE_Y_MIN_MV, class_name=SPARKLINE_AXIS_LABEL_CLASS))
    axis_label = _axis_day_label if daily else _axis_clock_label
    x_labels_html = '<div class="%s">%s%s</div>' % (
        draw.DRAWING_CHART_X_LABELS_CLASS,
        draw.label_span(axis_label(pairs[0][1]), class_name=SPARKLINE_AXIS_LABEL_CLASS),
        draw.label_span(axis_label(pairs[-1][1]), class_name=SPARKLINE_AXIS_LABEL_CLASS))
    return y_labels_html, x_labels_html


def battery_sparkline_svg(rows, now=None, daily=False):
    """A minimal, dependency-free battery-trend chart built server-side
    from `rows` (newest-first). No external reference of any kind
    (`url(`, `<image`, a script tag). Each plotted point carries a
    cosmetic marker plus a transparent, enlarged, keyboard-focusable hit
    target with a `<title>` tooltip, so the reading is available on
    hover/tap with no JavaScript.

    Returns a `<div class="sparkline">` grid wrapper. The inner `<svg>`
    has no `viewBox`, so every horizontal position is a percentage and
    every size is an absolute CSS pixel at every container width; the
    trend line is `n - 1` `<line>` segments, since a `<polyline>` cannot
    take percentage coordinates. Also draws an area under the line (its
    own nested `<svg>` with a private viewBox), a mark on the newest
    point, and a low-battery threshold line read from
    `companion/battery.py`.

    Returns `""` when fewer than two rows carry a numeric `battery_mv`.
    `daily=True` plots daily aggregates instead of individual readings:
    axis and point labels switch to their day-aware siblings, and
    cosmetic dots suppress above `_SPARKLINE_DENSE_POINT_THRESHOLD`.

    Every mark, tick and label position comes from `draw.percent_x()`/
    `draw.percent_y()`, and every shape/label from companion/draw.py's
    own primitives — this function only sequences them.
    """
    if now is None:
        now = history_db.utc_now_iso()
    chronological = list(reversed(rows))
    pairs = [
        (row.get("battery_mv"), row.get("ts"), row.get("reading_count"))
        for row in chronological
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool)
    ]
    if len(pairs) < 2:
        return ""
    point_count = len(pairs)

    plotted, points_markup = _sparkline_points_and_marks(pairs, point_count, now, daily)
    area_layer = _sparkline_area_layer(plotted)
    axis_chrome = _sparkline_axis_chrome(point_count)
    threshold_rect, legend_html = _sparkline_threshold(pairs)
    y_labels_html, x_labels_html = _sparkline_axis_labels(pairs, daily)

    # Recomputed the same way the visible heading is, so the two can
    # never disagree.
    heading = i18n.t(BATTERY_SECTION_HEADING_TEMPLATE) % (BATTERY_TREND_WINDOW_DAYS // 30)
    svg_html = draw.percent_canvas(
        draw.DRAWING_CHART_CANVAS_CLASS,
        area_layer + axis_chrome + threshold_rect + points_markup,
        label=heading)

    # Grid document order: Y-label column, canvas, X-label row, then the
    # threshold legend (grid-column: 1 / -1 in style.css) — "" when no
    # threshold is drawn, so the row simply does not exist.
    return '<div class="%s">%s%s%s%s</div>' % (
        draw.DRAWING_CHART_GRID_CLASS, y_labels_html, svg_html, x_labels_html, legend_html)
