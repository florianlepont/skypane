"""Companion status-page tests: battery_sparkline_svg()'s axis/label/density
contract, the check-in regularity grid, tile verdicts, and Paris-local-time
and resolution-rate copy.

CSS/JS checks fetch served bytes from a running companion/app.py; everything
else calls health_page/draw/wake/layout directly, in-process.
"""
import re
from datetime import datetime, timedelta

import pytest

from companion import battery, draw, i18n, layout, prefs
from companion.pages import health_page
import companion.test_status_pages_helpers as shp
import companion.wake as wake
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for, rules_with_selector
from server import device_config, history_db

_DEFAULT_DEVICE_WARN_S, _DEFAULT_DEVICE_ERROR_S = wake.device_staleness_thresholds(None)


# --- module-scoped read-only server, for the served-CSS/JS checks only ---

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


@pytest.fixture(scope="module")
def battery_trend_js(_module_server):
    return served_asset(_module_server, "/static/battery-trend.js")


# --- sparkline point-geometry helper (shared by the flat/wiggle/clamp trio) -

def _extract_point_ys(svg):
    """The cy="%.2f%%" value off every sparkline-hit circle, in document
    order — the exact y coordinate _point_y() computed for each plotted
    point, read back out of the rendered markup rather than recomputed
    independently."""
    return [float(m.group(1)) for m in re.finditer(
        r'<circle class="%s"[^>]*cy="([0-9.]+)%%"' % health_page.SPARKLINE_HIT_CLASS, svg)]


# --- shared helpers for the check-in regularity section (this part only) ---

_CELL_RE = re.compile(
    r'<rect class="drawing-cell ([^"]+)"[^>]*><title>([^<]*)</title></rect>')


def _check_in_cells(rendered):
    """[(state class, title), ...] in document order."""
    return [(m.group(1), m.group(2)) for m in _CELL_RE.finditer(rendered)]


def _seeded_regularity_page(state_dir, now, wake_interval_s=300):
    """Seed a device_config cadence plus two days of check-ins whose
    gaps land on three different verdicts, and render Health."""
    if wake_interval_s is not None:
        device_config.save_device_config(state_dir, wake_interval_s=wake_interval_s)
    today = now.astimezone(layout.LOCAL_TZ).replace(
        hour=1, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    shp.seed_device_health(state_dir, [
        # Yesterday: a 20-minute gap. At a 300s cadence that is past warn
        # (900s) and short of error (3600s) — late.
        (shp.iso(yesterday), 4200),
        (shp.iso(yesterday + timedelta(minutes=20)), 4190),
        # Today: a 10-minute gap, then a 6-hour one.
        (shp.iso(today), 4180),
        (shp.iso(today + timedelta(minutes=10)), 4170),
        (shp.iso(today + timedelta(hours=6)), 4160),
    ])
    return health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))


# --- shared helper for the tile-anatomy sweep (used from Task 2 onward) ----

def _tile_slice_by_caption(rendered, caption):
    matching = [tile for tile in shp.stat_tile_slices(rendered) if caption in tile]
    assert len(matching) == 1, (
        "expected exactly one .stat-tile carrying caption %r, got %d"
        % (caption, len(matching)))
    return matching[0]


# ==========================================================================
# battery_sparkline_svg(): axis labels, flat/wiggle/clamp, area, marks,
# the low-battery threshold
# ==========================================================================


def test_sparkline_axis_labels_present_with_fixed_range():
    """battery_sparkline_svg() emits exactly four aria-hidden axis-label text
    nodes carrying the FIXED SPARKLINE_Y_MIN_MV/SPARKLINE_Y_MAX_MV values (not
    the fixture's own real min/max), with every prior no-external-reference
    guarantee intact"""
    rows = [
        {"ts": "2024-01-01T08:00:00", "battery_mv": 4200},
        {"ts": "2024-01-01T09:00:00", "battery_mv": 3850},
        {"ts": "2024-01-01T10:00:00", "battery_mv": 4000},
    ]
    svg = health_page.battery_sparkline_svg(rows)
    tag_start = 0
    label_texts = []
    while True:
        idx = svg.find('<span class="sparkline-axis-label"', tag_start)
        if idx == -1:
            break
        tag_end = svg.index(">", idx)
        tag = svg[idx:tag_end + 1]
        assert 'aria-hidden="true"' in tag, (
            "expected every sparkline-axis-label <span> to carry aria-hidden=\"true\" on its own tag")
        text_end = svg.index("</span>", tag_end)
        label_texts.append(svg[tag_end + 1:text_end])
        tag_start = tag_end
    assert len(label_texts) == 4, (
        "expected exactly four sparkline-axis-label elements, got %d" % len(label_texts))
    # Document order: max label first, min label second — asserted against
    # each label's own isolated text, not a page-wide substring search,
    # because a per-point tooltip legitimately contains this fixture's own
    # real mV values elsewhere on the same markup.
    expected_max_label = "%d mV" % health_page.SPARKLINE_Y_MAX_MV
    expected_min_label = "%d mV" % health_page.SPARKLINE_Y_MIN_MV
    assert label_texts[0] == expected_max_label, (
        "expected the first Y axis label to be the fixed %r, got %r"
        % (expected_max_label, label_texts[0]))
    assert label_texts[1] == expected_min_label, (
        "expected the second Y axis label to be the fixed %r, got %r"
        % (expected_min_label, label_texts[1]))
    assert svg.count(health_page.SPARKLINE_LINE_CLASS) == 2, (
        "expected exactly 2 trend-line segments (n - 1 for 3 points) after adding axis labels, got %d"
        % svg.count(health_page.SPARKLINE_LINE_CLASS))
    for forbidden in ("url(", "<image", "<script"):
        assert forbidden not in svg, "found forbidden %r in the axis-labeled sparkline SVG" % forbidden


def test_sparkline_flat_series_draws_flat_not_pinned_to_bottom():
    """battery_sparkline_svg() draws a flat series (every value identical) at
    one consistent y level, never pinned to the canvas edge by a collapsed
    min==max range"""
    rows = [{"ts": "t%d" % i, "battery_mv": 3800} for i in range(4)]
    svg = health_page.battery_sparkline_svg(rows)
    ys = _extract_point_ys(svg)
    assert len(ys) == 4, "expected four plotted points for a four-row flat fixture, got %d" % len(ys)
    assert len(set(ys)) == 1, (
        "expected every point of a flat series to share the same y coordinate, got %r" % ys)


def test_sparkline_small_wiggle_stays_small_not_a_cliff():
    """battery_sparkline_svg() draws a small (15mV) wiggle as a small y
    movement, well under a tenth of the fixed range's full excursion — not a
    cliff spanning the whole canvas"""
    rows = [
        {"ts": "t0", "battery_mv": 3800},
        {"ts": "t1", "battery_mv": 3785},
        {"ts": "t2", "battery_mv": 3800},
        {"ts": "t3", "battery_mv": 3785},
    ]
    svg = health_page.battery_sparkline_svg(rows)
    ys = _extract_point_ys(svg)
    assert len(ys) == 4, "expected four plotted points for this wiggle fixture, got %d" % len(ys)
    wiggle_span_percent = max(ys) - min(ys)
    full_span_percent = 100 - 2 * health_page._SPARKLINE_VERTICAL_INSET_PERCENT
    assert wiggle_span_percent < full_span_percent * 0.10, (
        "expected a 15mV wiggle to move the plotted y by well under 10%% of the full "
        "min-to-max canvas excursion (%.2f%% of %.2f%%), got %.2f%%"
        % (10.0, full_span_percent, wiggle_span_percent))


def test_sparkline_out_of_range_values_clamp_not_rescale():
    """battery_sparkline_svg() clamps out-of-range values (2500mV, 4500mV) to
    the canvas edge rather than escaping it or rescaling the fixed axis
    labels"""
    # `rows` is newest-first (battery_trend_rows()'s own ordering);
    # battery_sparkline_svg() plots chronologically (oldest first), so the
    # 2500mV reading (oldest here) becomes the LEFTMOST point.
    rows = [
        {"ts": "t2", "battery_mv": 4500},
        {"ts": "t1", "battery_mv": 3800},
        {"ts": "t0", "battery_mv": 2500},
    ]
    svg = health_page.battery_sparkline_svg(rows)
    ys = _extract_point_ys(svg)
    assert len(ys) == 3, "expected three plotted points for this out-of-range fixture, got %d" % len(ys)
    inset = health_page._SPARKLINE_VERTICAL_INSET_PERCENT
    clamped_low_y = ys[0]  # 2500mV (oldest, leftmost), below SPARKLINE_Y_MIN_MV -> clamped to the min edge
    clamped_high_y = ys[2]  # 4500mV (newest, rightmost), above SPARKLINE_Y_MAX_MV -> clamped to the max edge
    assert abs(clamped_low_y - (100 - inset)) <= 0.01, (
        "expected the below-range point to clamp to the bottom inset edge, got %r" % clamped_low_y)
    assert abs(clamped_high_y - inset) <= 0.01, (
        "expected the above-range point to clamp to the top inset edge, got %r" % clamped_high_y)
    assert ("%d mV" % health_page.SPARKLINE_Y_MAX_MV) in svg, (
        "expected the axis max label to stay the fixed constant, not rescale to 4500")
    assert ("%d mV" % health_page.SPARKLINE_Y_MIN_MV) in svg, (
        "expected the axis min label to stay the fixed constant, not rescale to 2500")
    assert "4500 mV" not in svg.split('class="sparkline__y"')[1].split("</div>")[0], (
        "expected the Y axis label column NOT to rescale to the out-of-range 4500 value")


def test_sparkline_dense_threshold_is_width_derived():
    """_sparkline_dense_threshold() derives a different threshold for
    different canvas widths, proving the density rule is width-derived
    rather than a typed constant"""
    narrow = health_page._sparkline_dense_threshold(226)
    wide = health_page._sparkline_dense_threshold(900)
    assert narrow != wide, "expected two different canvas widths to derive two different thresholds"
    assert narrow > 1 and wide > 1, "expected both derived thresholds to be well above 1"
    assert health_page._SPARKLINE_DENSE_POINT_THRESHOLD == narrow, (
        "expected the module-level _SPARKLINE_DENSE_POINT_THRESHOLD to equal "
        "_sparkline_dense_threshold(_SPARKLINE_NARROWEST_CANVAS_PX)")


def test_sparkline_scale_bounded_at_one_across_real_container_widths(css_text):
    """battery_sparkline_svg()'s <svg> carries no viewBox/preserveAspectRatio
    (no scale factor exists), every cx/cy is a percentage inside [0, 100]
    with strictly increasing chronological marker x-positions, marker/hit-
    target radii stay the unchanged absolute 3/8, and the served stylesheet
    declares the canvas height exactly once for this selector and never
    inside a @media block"""
    rows = [
        {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
        for i in range(5)]
    svg = health_page.battery_sparkline_svg(rows)

    svg_tag = svg[svg.index("<svg"):svg.index(">", svg.index("<svg"))]
    assert "viewBox" not in svg_tag, (
        "expected no viewBox attribute on the sparkline <svg> — a scaling transform must not exist")
    assert "preserveAspectRatio" not in svg_tag, (
        "expected no preserveAspectRatio attribute on the sparkline <svg> — there is no scaled "
        "canvas to apply it to")

    cx_values = re.findall(r'cx="([\d.]+)%"', svg)
    cy_values = re.findall(r'cy="([\d.]+)%"', svg)
    assert len(cx_values) == 10 and len(cy_values) == 10, (
        "expected 10 percentage cx and 10 percentage cy values (5 markers + 5 hit targets for a "
        "5-row fixture), got %d/%d" % (len(cx_values), len(cy_values)))
    for value in cx_values + cy_values:
        assert 0.0 <= float(value) <= 100.0, "expected every cx/cy percentage inside [0, 100], got %r" % value

    # Document order interleaves each point's marker then its own hit
    # target (both at the same x), so every other cx value (starting at
    # index 0) is the chronological run of marker x-positions.
    marker_xs = [float(v) for v in cx_values[::2]]
    assert marker_xs == sorted(marker_xs) and len(set(marker_xs)) == len(marker_xs), (
        "expected strictly increasing, distinct marker x-positions (chronological order), got %r"
        % marker_xs)

    # Every radius is an ABSOLUTE pixel value that no container width can
    # scale — the newest point is a mark rather
    # than a cosmetic dot, so the 5-point fixture draws 4 dots at r=3, 1
    # mark at its own named radius, and 5 unchanged r=8 hit targets. The
    # hit-target radius in particular is asserted unchanged here: nothing
    # this plan adds may shrink a tap target.
    expected_radii = (
        ('r="%d"' % health_page._SPARKLINE_DOT_RADIUS_PX, 4),
        ('r="%d"' % health_page._SPARKLINE_MARK_RADIUS_PX, 1),
        ('r="%d"' % health_page._SPARKLINE_HIT_RADIUS_PX, 5),
    )
    for radius_text, expected_count in expected_radii:
        assert svg.count(radius_text) == expected_count, (
            "expected the unchanged absolute radii (4 dots, 1 mark, 5 hit targets) — %s appeared "
            "%d times, expected %d" % (radius_text, svg.count(radius_text), expected_count))

    decls = declarations_for(css_text, ".battery-trend-section svg:not(.icon)")
    assert re.match(r"\d", decls.get("height", "")), (
        "expected a fixed px height declaration on `.battery-trend-section svg:not(.icon)`, got %r"
        % decls)

    # The hazard this design introduces: every point coordinate is a
    # percentage of this declared height, so a responsive height inside a
    # media query would silently move every point with no other visual
    # signal.
    for rule in css_rules(css_text):
        if ".battery-trend-section svg:not(.icon)" in rule.selectors and rule.at_rules:
            decl_map = dict(rule.declarations)
            assert not re.match(r"\d", decl_map.get("height", "")), (
                "expected .battery-trend-section svg:not(.icon) to declare no height inside any "
                "@media block (%r) — every point coordinate is a percentage of the single declared "
                "height, so a responsive height would silently move every point" % (rule.at_rules,))


def test_sparkline_area_sits_under_the_line_in_its_own_nested_viewbox(css_text):
    """battery_sparkline_svg() fills an area under the trend line from a
    NESTED viewBox'd <svg> (percentages are illegal in a points list) whose
    vertices land on the exact coordinates the chart's own marks did, closed
    at the axis minimum rather than the canvas edge, painted before the
    line, in currentColor at a translucent fill-opacity, with the outer
    canvas still carrying no viewBox, no url(/image/script reference, no
    colour literal, no rule of its own for the layer, and nothing at all
    below two points"""
    rows = [
        {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
        for i in range(5)]
    svg = health_page.battery_sparkline_svg(rows)

    outer_tag = svg[svg.index("<svg"):svg.index(">", svg.index("<svg"))]
    assert "viewBox" not in outer_tag and "preserveAspectRatio" not in outer_tag, (
        "expected the OUTER canvas to keep no viewBox and no preserveAspectRatio after the area "
        "was added, got %r" % outer_tag)

    layers = re.findall(r'<svg class="sparkline__area"[^>]*>', svg)
    assert len(layers) == 1, "expected exactly one nested area layer <svg>, got %d" % len(layers)
    layer = layers[0]
    for needed in ('viewBox="0 0 100 100"', 'preserveAspectRatio="none"', 'aria-hidden="true"'):
        assert needed in layer, (
            "expected the nested area layer to carry %s — without it the polygon's user units do "
            "not map onto the outer scheme's percentages; got %r" % (needed, layer))

    polygons = re.findall(r'<polygon class="sparkline-area" points="([^"]*)"\s*/>', svg)
    assert len(polygons) == 1, "expected exactly one <polygon class=\"sparkline-area\">, got %d" % len(polygons)

    # Paint order: SVG paints in document order, so an area emitted after
    # the line would cover it. Asserted by index, not by reading a comment.
    assert svg.index('<svg class="sparkline__area"') < svg.index(
        '<line class="%s"' % health_page.SPARKLINE_LINE_CLASS), (
        "expected the area layer to be emitted BEFORE the first trend-line segment")

    vertices = []
    for pair in polygons[0].split(" "):
        x_text, _, y_text = pair.partition(",")
        vertices.append((float(x_text), float(y_text)))
    assert len(vertices) == 7, (
        "expected 7 polygon vertices for a 5-point series (5 along the line, then two baseline "
        "corners), got %d" % len(vertices))

    drawn = [(float(cx), float(cy)) for cx, cy in re.findall(
        r'<circle class="%s"[^>]*cx="([\d.]+)%%" cy="([\d.]+)%%"' % health_page.SPARKLINE_HIT_CLASS, svg)]
    assert len(drawn) == 5, "expected to read back 5 plotted point coordinates, got %d" % len(drawn)
    for index, (drawn_point, vertex) in enumerate(zip(drawn, vertices[:5])):
        assert abs(drawn_point[0] - vertex[0]) <= 0.005 and abs(drawn_point[1] - vertex[1]) <= 0.005, (
            "expected the area's vertex %d to sit exactly on the point the chart drew %r, got %r — "
            "the area and the line are then two different scales" % (index, drawn_point, vertex))

    # The baseline is the SCALE's own floor (the level the "3000 mV" label
    # names), never the canvas edge: closing the area at y=100 would add
    # the vertical inset to every reading as a constant.
    baseline = health_page.sparkline_point_y(health_page.SPARKLINE_Y_MIN_MV)
    assert abs(vertices[5][1] - baseline) <= 0.005 and abs(vertices[6][1] - baseline) <= 0.005, (
        "expected the area's two baseline corners at the axis minimum's own y (%.2f%%), got %r and %r"
        % (baseline, vertices[5], vertices[6]))
    assert abs(vertices[5][0] - drawn[-1][0]) <= 0.005 and abs(vertices[6][0] - drawn[0][0]) <= 0.005, (
        "expected the baseline corners to span exactly the plotted x range (newest then oldest), "
        "got %r and %r" % (vertices[5], vertices[6]))

    # The no-external-reference guarantee, re-asserted AT the area: a flat
    # translucent fill instead of url(#gradient). No colour value is
    # introduced either — the fill is currentColor in CSS.
    for forbidden in ("url(", "<image", "<script"):
        assert forbidden not in svg, "found forbidden %r in the sparkline SVG after adding the area" % forbidden
    literal = re.search(r'#[0-9a-fA-F]{3,8}|rgb\(', svg)
    assert literal is None, "found a raw colour literal %r in the emitted markup" % (
        literal.group(0) if literal else None)

    # The "" floor below two points takes the area with it.
    one_point = health_page.battery_sparkline_svg([{"ts": "2024-01-01T00:00:00", "battery_mv": 4000}])
    assert one_point == "", (
        "expected no chart at all (and so no area) below two plotted points, got %r" % one_point[:80])

    decls = declarations_for(css_text, ".sparkline-area")
    assert decls.get("fill") == "currentColor", (
        "expected `.sparkline-area` to fill with currentColor — the area's colour must be the "
        "LINE's own colour, so dark mode is correct by the same mechanism; got %r" % decls)
    opacity = decls.get("fill-opacity")
    assert opacity is not None, (
        "expected `.sparkline-area` to declare a fill-opacity — an opaque area hides the axis "
        "beneath it")
    assert 0.0 < float(opacity) < 1.0, "expected a translucent fill-opacity strictly between 0 and 1, got %r" % opacity

    # The nested layer must carry NO rule of its own: its box comes from
    # the single `.battery-trend-section svg:not(.icon)` declaration the
    # check above pins, which is what makes the area layer and the canvas
    # it sits inside impossible to size differently.
    assert not rules_with_selector(css_text, ".sparkline__area"), (
        "expected NO `.sparkline__area` rule in style.css — the area layer's box must come from "
        "the one `.battery-trend-section svg:not(.icon)` height declaration, not a second one")


def test_sparkline_marks_the_newest_plotted_point_not_the_newest_row():
    """the battery chart marks the newest PLOTTED point (never the newest raw
    row, which may carry no battery_mv at all) with its own non-dot class at
    a named radius that fits the canvas's vertical inset, last in document
    order, carrying the same timestamp its hit target does, leaving the
    roving-tabindex path byte-identical, and surviving the density rule that
    suppresses cosmetic dots"""
    # The fixture's newest row deliberately carries NO battery_mv: a mark
    # derived from the raw rows would mark a row the chart never plotted.
    # The mark must come from the SAME single-pass filtered pair list the
    # points do.
    rows = [
        {"ts": "2024-01-05T05:00:00"},
        {"ts": "2024-01-04T04:00:00", "battery_mv": 3900},
        {"ts": "2024-01-03T03:00:00", "battery_mv": 4000},
        {"ts": "2024-01-02T02:00:00", "battery_mv": 4100},
    ]
    svg = health_page.battery_sparkline_svg(rows, now="2024-01-05T06:00:00")

    marks = re.findall(
        r'<circle class="%s"[^>]*cx="([\d.]+)%%" cy="([\d.]+)%%" r="(\d+)"[^>]*/>'
        % health_page.SPARKLINE_MARK_CLASS, svg)
    assert len(marks) == 1, "expected exactly one marked point, got %d" % len(marks)
    mark_x, mark_y, mark_r = float(marks[0][0]), float(marks[0][1]), int(marks[0][2])
    assert abs(mark_x - 100.0) <= 0.005, "expected the mark at the rightmost (newest) x=100%%, got %.2f%%" % mark_x
    expected_y = health_page.sparkline_point_y(3900)
    assert abs(mark_y - expected_y) <= 0.005, (
        "expected the mark at the newest PLOTTED reading's own level (%.2f%%, for 3900 mV), got "
        "%.2f%% — a mark derived from the raw rows lands on the newest row instead, which has no "
        "battery_mv at all" % (expected_y, mark_y))
    assert "2024-01-05" not in svg, "the row with no battery_mv reached the chart — it must be dropped, mark included"

    # The mark is NOT a cosmetic dot, and that is the density rule's
    # written-down exception rather than an accident of naming.
    assert health_page.SPARKLINE_MARK_CLASS not in health_page.SPARKLINE_DOT_CLASS and (
        health_page.SPARKLINE_DOT_CLASS not in health_page.SPARKLINE_MARK_CLASS), (
        "expected the mark and dot class names to be distinct, neither a substring of the other")
    dots = [m.start() for m in re.finditer(
        r'<circle class="%s"' % health_page.SPARKLINE_DOT_CLASS, svg)]
    assert len(dots) == 2, "expected 2 cosmetic dots (3 plotted points, the last one marked instead), got %d" % len(dots)
    mark_at = svg.index('<circle class="%s"' % health_page.SPARKLINE_MARK_CLASS)
    assert not any(dot_at > mark_at for dot_at in dots), "expected the mark to be the LAST plotted marker in document order"

    # The mark reads as the current value only if the hit target at the
    # same place carries that reading's own timestamp.
    hits = re.findall(
        r'<circle class="%s"[^>]*data-ts="([^"]*)"[^>]*>(?:<title>([^<]*)</title>)?'
        % health_page.SPARKLINE_HIT_CLASS, svg)
    assert len(hits) == 3, "expected 3 hit targets, got %d" % len(hits)
    assert hits[-1][0] == "2024-01-04T04:00:00", (
        "expected the last hit target to carry the newest PLOTTED row's timestamp, got %r" % hits[-1][0])
    assert hits[-1][1], "expected the marked point's hit target to keep its own <title>"

    # The keyboard path is untouched: one Tab stop, on the last point, and
    # one tabindex per point.
    assert svg.count("tabindex=") == 3 and svg.count('tabindex="0"') == 1, (
        "expected one tabindex per point with exactly one Tab stop, got %d tabindex / %d zero"
        % (svg.count("tabindex="), svg.count('tabindex="0"')))
    assert svg.index('tabindex="0"') >= mark_at, "expected the single Tab stop to be the marked (latest) point's own hit target"

    # The mark's radius is a named constant and fits inside the vertical
    # inset the canvas reserves.
    assert mark_r == health_page._SPARKLINE_MARK_RADIUS_PX, (
        "expected the mark's radius to come from _SPARKLINE_MARK_RADIUS_PX, got %d" % mark_r)
    inset_px = health_page._SPARKLINE_VERTICAL_INSET_PERCENT / 100.0 * health_page._SPARKLINE_CANVAS_HEIGHT_PX
    assert mark_r <= inset_px, "expected the mark's %dpx radius to fit inside the canvas's %.2fpx vertical inset" % (mark_r, inset_px)
    assert mark_r > health_page._SPARKLINE_DOT_RADIUS_PX, "expected the mark to be visibly larger than a cosmetic dot"

    # The density rule's exception, asserted rather than commented: above
    # the threshold the cosmetic dots go and the mark stays.
    dense_rows = [
        {"ts": "2026-06-%02d" % ((i % 28) + 1), "battery_mv": 4000 + i}
        for i in range(health_page._SPARKLINE_DENSE_POINT_THRESHOLD + 5)]
    dense_svg = health_page.battery_sparkline_svg(
        dense_rows, now="2026-09-02T12:00:00+00:00", daily=True)
    assert health_page.SPARKLINE_DOT_CLASS not in dense_svg, "expected no cosmetic dots above the density threshold"
    assert dense_svg.count('<circle class="%s"' % health_page.SPARKLINE_MARK_CLASS) == 1, (
        "expected the marked point to SURVIVE the density rule — it is not a cosmetic dot, and "
        "marking the current reading is the whole reason it is drawn")


def test_sparkline_low_battery_threshold_is_read_from_battery_py_and_labelled(css_text, monkeypatch):
    """the chart's low-battery threshold is a full-width rect placed by the
    same sparkline_point_y() the readings are, its value READ from
    companion/battery.py, labelled by meaning in a non-aria-hidden <span>
    outside the canvas in both languages, painted with the status-warn
    token the legend's own swatch shares, and absent entirely — line and
    label — when the value falls outside the chart's fixed range"""
    rows = [
        {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
        for i in range(5)]
    svg = health_page.battery_sparkline_svg(rows)

    rects = re.findall(r'<rect class="%s"([^>]*)/>' % health_page.SPARKLINE_THRESHOLD_CLASS, svg)
    assert len(rects) == 1, "expected exactly one drawn low-battery threshold, got %d" % len(rects)
    attrs = rects[0]
    expected_y = 'y="%.2f%%"' % health_page.sparkline_point_y(battery.LOW_BATTERY_DISPLAY_MV)
    assert expected_y in attrs, (
        "expected the threshold at sparkline_point_y(battery.LOW_BATTERY_DISPLAY_MV) = %s, got %r "
        "— a threshold with its own arithmetic drifts from the readings by the vertical inset"
        % (expected_y, attrs))
    for needed in ('x="0"', 'width="100%"', 'height="1"', 'aria-hidden="true"'):
        assert needed in attrs, "expected the threshold rect to carry %s, got %r" % (needed, attrs)

    # The label names what the line MEANS, is outside the SVG as a <span>
    # in the chart's own grid, and is NOT aria-hidden: unlike the axis
    # labels (whose values every point already announces), nothing else on
    # this page says where "low" starts.
    legend = re.search(
        r'<div class="%s">\s*<span class="%s"([^>]*)>(.*?)</span>\s*</div>'
        % (health_page.SPARKLINE_LEGEND_ROW_CLASS, health_page.SPARKLINE_LEGEND_CLASS),
        svg, re.S)
    assert legend is not None, "expected a threshold legend <span> inside the chart's own label grid"
    assert "aria-hidden" not in legend.group(1), (
        "expected the threshold legend NOT to be aria-hidden — the axis labels are hidden because "
        "every point already announces its value, and nothing announces this one")
    legend_text = re.sub(r"<[^>]*>", "", legend.group(2))
    assert str(battery.LOW_BATTERY_DISPLAY_MV) in legend_text, (
        "expected the legend to name the threshold's level, got %r" % legend_text)
    assert str(battery.LOW_BATTERY_DISPLAY_PERCENT) in legend_text, (
        "expected the legend to name the percentage the level corresponds to, tying the line to "
        "the estimate printed beside the chart, got %r" % legend_text)
    assert legend_text.strip() != "%d mV" % battery.LOW_BATTERY_DISPLAY_MV, (
        "expected the legend to say what the line MEANS, not a bare number on a chart")
    assert svg.index('<div class="%s">' % health_page.SPARKLINE_LEGEND_ROW_CLASS) >= svg.index("</svg>"), (
        "expected the legend OUTSIDE the canvas, after it in the grid")

    # Both languages.
    try:
        prefs.set_request_prefs(lang="fr")
        fr_svg = health_page.battery_sparkline_svg(rows)
    finally:
        prefs.set_request_prefs(lang="en")
    fr_legend = re.search(r'<span class="%s"[^>]*>(.*?)</span>' % health_page.SPARKLINE_LEGEND_CLASS, fr_svg, re.S)
    assert fr_legend is not None, "expected the threshold legend to render in French too"
    fr_text = re.sub(r"<[^>]*>", "", fr_legend.group(1))
    assert fr_text != legend_text, "expected a French translation of the threshold legend, got the English string %r" % fr_text

    # Out of range: no line, and no label for a line that is not there.
    # This guards a later change to the threshold, not today's value.
    for bad in (health_page.SPARKLINE_Y_MIN_MV - 100, health_page.SPARKLINE_Y_MIN_MV,
                health_page.SPARKLINE_Y_MAX_MV + 100):
        monkeypatch.setattr(battery, "LOW_BATTERY_DISPLAY_MV", bad)
        out = health_page.battery_sparkline_svg(rows)
        assert health_page.SPARKLINE_THRESHOLD_CLASS not in out, (
            "expected NO threshold drawn for an out-of-range value (%d) — the clamp would pin it "
            "to the axis edge, where it reads as a threshold AT the chart floor" % bad)
        assert health_page.SPARKLINE_LEGEND_CLASS not in out, "expected no threshold legend when no threshold is drawn (%d)" % bad

    threshold_decls = declarations_for(css_text, ".sparkline-threshold")
    assert any("var(--color-status-warn)" in v for v in threshold_decls.values()), (
        "expected `.sparkline-threshold` to be filled with the app's existing status-warn token — "
        "the threshold is a judgement, not axis chrome, and accent is reserved")
    swatch_decls = declarations_for(css_text, ".sparkline-swatch")
    assert any("var(--color-status-warn)" in v for v in swatch_decls.values()), (
        "expected the legend's swatch to be painted with the SAME token as the drawn line, so the "
        "legend cannot come to describe a colour the chart does not use")


# ==========================================================================
# The check-in regularity grid
#
# THESE FOUR TESTS COVER companion/draw.py, NOT A PAGE, and they live here
# rather than in companion/test_companion_app.py because this harness, not
# that one, is where their migration landed.
# ==========================================================================


def test_regularity_grid_has_four_states_and_never_conflates_them():
    """draw.cell_class() maps the classifier's four verdicts to four
    DISTINCT classes, all of them in DRAWING_CLASSES, and falls to the
    no-observation class for anything else — so a bucket with no
    observation can never emit the on-cadence or the missing class — and
    regularity_grid() raises rather than emitting a cell with no <title>"""
    states = (wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE,
              wake.CHECK_IN_MISSING, wake.CHECK_IN_UNKNOWN)
    classes = [draw.cell_class(state) for state in states]
    assert len(set(classes)) == 4, (
        "expected four DISTINCT cell classes for the four states, got %r — two states painted by "
        "one class cannot be told apart" % (classes,))
    for state, class_name in zip(states, classes):
        assert class_name in draw.DRAWING_CLASSES, (
            "cell_class(%r) returned %r, which is not in draw.DRAWING_CLASSES — 24-01's own "
            "style.css resolution check cannot see it" % (state, class_name))
    none_class = draw.cell_class(wake.CHECK_IN_UNKNOWN)
    for bogus in (None, "", "ok", "honoured", 0, True, "on-cadence"):
        got = draw.cell_class(bogus)
        assert got == none_class, (
            "cell_class(%r) returned %r — an unrecognised verdict must fall to the no-observation "
            "class %r, never to a verdict the data does not support" % (bogus, got, none_class))
    markup, dropped = draw.regularity_grid(
        [(state, "cell %d" % i) for i, state in enumerate(states)])
    assert not dropped, "four cells dropped %d — nothing should be bounded out" % (dropped,)
    for state, class_name in zip(states, classes):
        assert markup.count('class="%s %s"' % (draw.DRAWING_CELL_CLASS, class_name)) == 1, (
            "expected exactly one cell carrying %r for state %r in %r" % (class_name, state, markup))
    # The no-observation cell, isolated: it must carry neither of the two
    # classes a reader would act on.
    alone, _ = draw.regularity_grid([(wake.CHECK_IN_UNKNOWN, "no record")])
    for forbidden in (draw.cell_class(wake.CHECK_IN_ON_CADENCE), draw.cell_class(wake.CHECK_IN_MISSING)):
        assert not re.search(r'(?<![-\w])%s(?![-\w])' % re.escape(forbidden), alone), (
            "a bucket with no observation emitted %r: %r" % (forbidden, alone))
    assert alone.count("<title>") == 1 and "no record" in alone, (
        "expected the lone cell to carry its caller's <title>: %r" % (alone,))
    # A cell with no title RAISES rather than emitting a silent one.
    for empty in (None, "", "   "):
        with pytest.raises(ValueError):
            draw.regularity_grid([(wake.CHECK_IN_LATE, empty)])


def test_regularity_grid_cells_are_sized_from_the_360px_floor():
    """the regularity grid sizes its cells DOWN from the measured 278px card
    width at the 360px floor: grid_columns() returns the most columns whose
    cells still clear the 24px minimum and one more column would not, a
    narrower card reduces the columns rather than the cells, every cell is
    square, inside the viewBox, spread across every column and row with
    exactly CELL_GAP_PX of clear ground, and no colour literal is emitted"""
    width = draw.CARD_DRAWING_WIDTH_PX
    columns = draw.grid_columns(width)
    size = draw.grid_cell_size(width, columns)
    assert size >= draw.CELL_MIN_SIZE_PX, (
        "at the measured %spx card width, %d columns give a %.2fpx cell — under the %spx minimum. "
        "The bucket count must come DOWN, never the cell size" % (width, columns, size, draw.CELL_MIN_SIZE_PX))
    # One more column must be under the floor, or `columns` is not the most
    # that fits and the grid is wasting width it has.
    over = draw.grid_cell_size(width, columns + 1)
    assert over < draw.CELL_MIN_SIZE_PX, (
        "%d columns would still give a %.2fpx cell at %spx, so grid_columns() is not returning the "
        "most that fit — the floor is not what is deciding" % (columns + 1, over, width))
    # A narrow card reduces the COLUMNS, and never below one.
    for narrow in (10, 24, 27, 40, 100):
        few = draw.grid_columns(narrow)
        assert few >= 1, "grid_columns(%d) returned %d — a grid needs a column" % (narrow, few)
        if few > 1:
            assert draw.grid_cell_size(narrow, few) >= draw.CELL_MIN_SIZE_PX, (
                "grid_columns(%d) returned %d, whose cells are %.2fpx — under the floor"
                % (narrow, few, draw.grid_cell_size(narrow, few)))
    # Geometry: every cell inside the canvas, at the declared size.
    cells = [(wake.CHECK_IN_ON_CADENCE, "c%d" % i) for i in range(columns * 3)]
    markup, dropped = draw.regularity_grid(cells, width=width)
    assert not dropped, "three full rows dropped %d cells" % (dropped,)
    view = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', markup)
    assert view, "expected a viewBox on the grid canvas: %r" % (markup[:200],)
    box_w, box_h = float(view.group(1)), float(view.group(2))
    assert abs(box_w - width) <= 0.01, (
        "the canvas is %.2fpx wide against the %spx it was given — a grid that does not fill the "
        "width it was handed has an unexplained margin" % (box_w, width))
    rects = re.findall(
        r'<rect class="[^"]*" x="([\d.-]+)" y="([\d.-]+)" width="([\d.]+)" height="([\d.]+)"', markup)
    assert len(rects) == len(cells), "expected %d cell rects, got %d" % (len(cells), len(rects))
    for x, y, w, h in ((float(a), float(b), float(c), float(d)) for a, b, c, d in rects):
        assert abs(w - size) <= 0.01 and abs(h - size) <= 0.01, (
            "a cell measures %.2fx%.2f against the %.2fpx square the constants derive" % (w, h, size))
        assert x >= -0.01 and y >= -0.01 and x + w <= box_w + 0.01 and y + h <= box_h + 0.01, (
            "a cell at (%.2f, %.2f) is outside the %.2fx%.2f viewBox — a mark painted outside its "
            "own box is clipped in one browser and not in another" % (x, y, box_w, box_h))
    # THE FLOOR, not only the ceiling: the columns really are used.
    xs = sorted({round(float(r[0]), 2) for r in rects})
    assert len(xs) == columns, (
        "expected %d distinct cell x positions, got %d (%r) — the cells are not spread across the "
        "row" % (columns, len(xs), xs))
    ys = sorted({round(float(r[1]), 2) for r in rects})
    assert len(ys) == 3, "expected 3 rows of cells, got %d (%r)" % (len(ys), ys)
    # The last column's right edge reaches the canvas's own right edge —
    # measured against a whole-pixel cell size, which leaves exactly this
    # 1px shortfall.
    assert abs((xs[-1] + size) - box_w) <= 0.01, (
        "the last column's right edge is at %.2f against a %.2fpx canvas — the grid does not reach "
        "its own right edge, so the label row beneath it names a column that is not there"
        % (xs[-1] + size, box_w))
    gaps = {round(b - a - size, 2) for a, b in zip(xs, xs[1:])}
    assert gaps == {float(draw.CELL_GAP_PX)}, (
        "the clear ground between columns is %r, not the %spx CELL_GAP_PX declares" % (gaps, draw.CELL_GAP_PX))
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b|rgb\(|hsl\(", markup), "the grid emitted a colour literal: %r" % (markup,)


def test_regularity_grid_is_bounded_and_keeps_the_newest_buckets():
    """the regularity grid's element count is bounded by its own geometry
    and never by the caller's window — at capacity it keeps the NEWEST
    buckets, reports exactly how many it dropped, and paints none of the
    dropped verdicts — while one cell still draws one full-size cell and no
    cells draw nothing"""
    columns = draw.grid_columns(draw.CARD_DRAWING_WIDTH_PX)
    capacity = columns * draw.GRID_MAX_ROWS
    cells = [(wake.CHECK_IN_ON_CADENCE, "day %03d" % i) for i in range(capacity + 17)]
    cells[0] = (wake.CHECK_IN_MISSING, cells[0][1])
    markup, dropped = draw.regularity_grid(cells, width=draw.CARD_DRAWING_WIDTH_PX)
    assert dropped == 17, (
        "expected the 17 buckets over capacity to be reported dropped, got %d — a caption cannot "
        "be honest about a window the drawing silently truncated" % (dropped,))
    titles = re.findall(r"<title>([^<]*)</title>", markup)
    assert len(titles) == capacity, (
        "expected the grid bounded at %d cells (%d columns x %d rows), got %d"
        % (capacity, columns, draw.GRID_MAX_ROWS, len(titles)))
    assert titles[-1] == "day %03d" % (capacity + 16), (
        "the last cell is %r, not the newest bucket supplied — a bounded grid that keeps the "
        "OLDEST cells draws a window that has already ended" % (titles[-1],))
    assert titles[0] == "day 017", "the first cell is %r, not the oldest bucket that still fits" % (titles[0],)
    # And the dropped oldest cell's own verdict left with it.
    assert not re.search(
        r'(?<![-\w])%s(?![-\w])' % re.escape(draw.cell_class(wake.CHECK_IN_MISSING)), markup), (
        "the dropped oldest bucket's verdict is still painted in the grid")
    # A single cell is a real grid, not a degenerate one.
    one, _ = draw.regularity_grid([(wake.CHECK_IN_LATE, "only")], width=draw.CARD_DRAWING_WIDTH_PX)
    size = draw.grid_cell_size(draw.CARD_DRAWING_WIDTH_PX, columns)
    assert 'height="%s"' % draw._number(size) in one, "a one-cell grid is %r — it must still be one full-size cell tall" % (one,)
    empty, empty_dropped = draw.regularity_grid([])
    assert empty == "" and not empty_dropped, (
        "no cells at all must draw nothing and drop nothing (the caller owns the empty state), "
        "got %r/%r" % (empty, empty_dropped))


def test_draw_cell_vocabulary_is_the_classifiers_own():
    """draw.CELL_STATE_CLASSES is keyed on EXACTLY wake.classify_check_in_gap()'s
    own four CHECK_IN_* values — the one coupling a stdlib-only geometry
    module cannot express as an import"""
    # draw.py is stdlib-only and may not import the server package, so the
    # four verdict strings are re-typed there by necessity. This is what
    # stops that necessity becoming a drift: rename a CHECK_IN_* value in
    # server/wake.py and the grid would paint every cell in the
    # no-observation colour with nothing else failing.
    vocabulary = {wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE,
                  wake.CHECK_IN_MISSING, wake.CHECK_IN_UNKNOWN}
    assert set(draw.CELL_STATE_CLASSES) == vocabulary, (
        "draw.CELL_STATE_CLASSES is keyed on %r, the classifier's vocabulary is %r — a verdict "
        "wake.classify_check_in_gap() returns that this table does not carry paints as no "
        "observation at all" % (sorted(draw.CELL_STATE_CLASSES), sorted(vocabulary)))


# --- the Health section's regularity caption --------------------------
#
# THE CAPTION'S THREE CLAUSES GET THREE TESTS, one each, because they are
# three separate claims and a later editor will be tempted to trim the
# third as noise. A single test over the whole caption would go green on
# two clauses out of three.


def test_the_caption_says_what_the_grid_shows(tmp_path):
    """CLAUSE 1 — Health's regularity caption says what the grid SHOWS: one
    cell is one day of OBSERVED check-in regularity"""
    rendered = _seeded_regularity_page(str(tmp_path), shp.now())
    clause = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_OBSERVED))
    assert clause in rendered, (
        "the caption does not carry its first clause %r — a grid whose reader cannot tell what "
        "one cell means is a texture" % (clause,))
    assert health_page.CHECK_IN_SECTION_HEADING.lower() != "wake punctuality", (
        "the heading is the roadmap's own superseded phrasing")


def test_the_caption_names_the_cadence_it_judged_against_and_says_it_is_todays(tmp_path):
    """CLAUSE 2 — Health's regularity caption names the cadence the grid was
    judged against, by its value and in this app's own duration form, and
    says that cadence is the one configured NOW rather than the one in
    force on an earlier day"""
    now = shp.now()
    rendered = _seeded_regularity_page(str(tmp_path), now, wake_interval_s=300)
    # The VALUE, formatted the one way this app formats a length of time —
    # never re-derived here as "5 minutes".
    expected = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_CADENCE) % layout.duration_text(300))
    assert expected in rendered, "the caption does not name the cadence it judged against: expected %r" % expected
    assert "5m" in rendered or "5 min" in rendered, "the configured 300s cadence is not named by its value anywhere"


def test_the_caption_says_a_gap_is_not_proof_of_a_missed_wake(tmp_path):
    """CLAUSE 3 — Health's regularity caption says a day with no record is
    NOT proof the frame did not wake, naming the log rotation that leaves
    the same gap"""
    # This is the clause a later editor trims as noise, and it is the
    # difference between reporting an observation and accusing the
    # device: the record cannot tell a missed wake from a log range the
    # ingest lost.
    rendered = _seeded_regularity_page(str(tmp_path), shp.now())
    clause = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_NOT_PROOF))
    assert clause in rendered, (
        "the caption does not carry its third clause %r — without it the grid accuses the device "
        "of missing wakes the record cannot show it missed" % (clause,))


def test_with_no_determinable_cadence_the_caption_names_the_floors(tmp_path, monkeypatch):
    """with a config yielding no cadence at all, Health's regularity caption
    says the grid is judged against the fallback staleness floors and does
    NOT name a configured value"""
    monkeypatch.delenv(wake.SLEEP_ENV_VAR, raising=False)
    now = shp.now()
    # No device_config.json and no SKYPANE_SLEEP_S: exactly the
    # freshly-provisioned deployment device_staleness_thresholds() degrades
    # to its bare floors for.
    rendered = _seeded_regularity_page(str(tmp_path), now, wake_interval_s=None)
    assert wake.effective_wake_interval_s(None) is None, "the fixture still resolves a cadence — this check measures nothing"
    floors = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_CADENCE_FALLBACK))
    assert floors in rendered, "with no determinable cadence the caption must name the fallback floors: expected %r" % floors
    configured = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_CADENCE).split("%s")[0])
    assert configured not in rendered, (
        "the caption still claims a CONFIGURED cadence (%r) for a deployment that has none — a "
        "silently assumed default is the one thing this clause exists to prevent" % (configured,))


def test_every_cell_verdict_is_the_classifiers_own_output(tmp_path):
    """every cell's verdict equals wake.classify_check_in_gap()'s own output
    for that day's longest observed gap — computed in this check from the
    classifier, never hard-coded — every unobserved day carries the
    no-observation class, and the page's own regularity builders call the
    classifier while referencing no threshold constant of their own"""
    now = shp.now()
    state_dir = str(tmp_path)
    rendered = _seeded_regularity_page(state_dir, now, wake_interval_s=300)
    cells = _check_in_cells(rendered)
    assert len(cells) == health_page.CHECK_IN_WINDOW_DAYS, (
        "expected one cell per day of the %d-day window, got %d" % (health_page.CHECK_IN_WINDOW_DAYS, len(cells)))
    # The expectation is COMPUTED from the classifier over the reader's own
    # rows — never a hard-coded colour.
    with history_db.open_db(state_dir) as conn:
        rows = history_db.check_in_gaps(conn)
    worst = {}
    for row in rows:
        day, gap = row["day"], row["gap_s"]
        if day is None or gap is None:
            continue
        worst[day] = max(gap, worst.get(day, gap))
    assert len(worst) == 2, (
        "the fixture seeded gaps on %d Paris days, expected 2 — this check would be measuring "
        "something other than what it seeded" % (len(worst),))
    expected = {}
    for day, gap in worst.items():
        state = wake.classify_check_in_gap(gap, 300)
        parsed_day = datetime.strptime(day, "%Y-%m-%d")
        expected["%d %s" % (parsed_day.day, layout.month_abbr(parsed_day.month))] = state
    assert set(expected.values()) == {wake.CHECK_IN_LATE, wake.CHECK_IN_MISSING}, (
        "the fixture's own verdicts are %r — it must exercise more than one verdict or the "
        "mapping below is untested" % (sorted(expected.values()),))
    seen = 0
    for class_name, title in cells:
        for label, state in expected.items():
            if title.startswith(label):
                seen += 1
                assert class_name == draw.cell_class(state), (
                    "the cell titled %r carries %r; the classifier says %r for its own longest "
                    "observed gap, which is %r" % (title, class_name, state, draw.cell_class(state)))
                break
        else:
            assert class_name == draw.cell_class(wake.CHECK_IN_UNKNOWN), (
                "the cell titled %r carries %r for a day the record says nothing about — it must "
                "carry the no-observation class %r" % (title, class_name, draw.cell_class(wake.CHECK_IN_UNKNOWN)))
    assert seen == len(expected), "found %d of the %d seeded days in the grid" % (seen, len(expected))
    # AND THE PAGE COMPUTES NO INTERVAL OF ITS OWN. Read off the compiled
    # functions' own referenced names, never their source text, so a
    # docstring can neither pass nor fail this.
    builders = [health_page._check_in_regularity_cells, health_page._check_in_regularity_section_html]
    names = set()
    for fn in builders:
        names |= set(fn.__code__.co_names)
    assert "classify_check_in_gap" in names, (
        "no regularity builder calls wake.classify_check_in_gap() — the verdicts are coming from "
        "somewhere other than the one definition of 'late'")
    for forbidden in ("device_staleness_thresholds", "MISSED_WAKES_WARN", "MISSED_WAKES_ERROR",
                      "STALE_WARN_FLOOR_S", "STALE_ERROR_FLOOR_S"):
        assert forbidden not in names, (
            "a regularity builder references %r — this page consumes verdicts and derives no "
            "threshold of its own" % (forbidden,))


def test_with_no_observations_the_section_still_renders_its_grid(tmp_path):
    """with no observations at all the regularity section still renders — a
    full grid of no-observation cells, none of them on-cadence or missing,
    under its own caption saying there is nothing recorded yet"""
    now = shp.now()
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, wake_interval_s=300)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    heading = layout.escape_html(i18n.t(health_page.CHECK_IN_SECTION_HEADING))
    assert heading in rendered, (
        "a deployment with no check-ins renders no regularity section at all — an absent section "
        "is a worse answer than an honest empty one")
    cells = _check_in_cells(rendered)
    assert len(cells) == health_page.CHECK_IN_WINDOW_DAYS, (
        "expected a full %d-cell grid of no-observation cells, got %d" % (health_page.CHECK_IN_WINDOW_DAYS, len(cells)))
    none_class = draw.cell_class(wake.CHECK_IN_UNKNOWN)
    wrong = [c for c, _ in cells if c != none_class]
    assert not wrong, (
        "a deployment with no check-ins painted %r — with no observations there is nothing to be "
        "on cadence about and nothing to be missing" % (set(wrong),))
    empty = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_EMPTY))
    assert empty in rendered, "the empty grid carries no caption of its own saying so: expected %r" % (empty,)


def test_the_rendered_page_never_claims_punctuality_in_either_language(tmp_path):
    """the rendered Health page contains neither 'honoured' nor 'punctual'
    (nor 'punctualité') in EITHER language while carrying the full grid in
    both, and the section heading has a real French sibling rather than an
    English string inside a French page"""
    # The roadmap's own phrasing for this drawing was "wake punctuality",
    # and the expected interval is not recoverable, so a page using that
    # word would assert something this deployment cannot observe. The
    # blunt grep is the point — it is re-runnable from a terminal by
    # anyone, with no parser to trust.
    now = shp.now()
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, wake_interval_s=300)
    try:
        prefs.set_request_prefs(lang="en")
        en_rendered = _seeded_regularity_page(state_dir, now)
        prefs.set_request_prefs(lang="fr")
        fr_rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    for lang_name, rendered in (("EN", en_rendered), ("FR", fr_rendered)):
        lowered = rendered.lower()
        for banned in ("honoured", "punctual", "punctualité", "ponctual"):
            assert banned not in lowered, (
                "the %s-rendered Health page contains %r — this grid reports an OBSERVATION, and "
                "no name in this app may call it a rate of wakes the device kept" % (lang_name, banned))
        assert len(_check_in_cells(rendered)) == health_page.CHECK_IN_WINDOW_DAYS, (
            "the %s render carries no regularity grid, so this check is scanning a page without "
            "the drawing it is about" % (lang_name,))
    fr_heading = health_page.i18n.t_lang(health_page.CHECK_IN_SECTION_HEADING, "fr")
    assert fr_heading != health_page.CHECK_IN_SECTION_HEADING, (
        "the section heading has no French sibling — it would render in English inside a French page")
    assert layout.escape_html(fr_heading) in fr_rendered, "the French render does not carry the French heading"


_DISCLOSURE_CASES = [
    ("observed, cadence known", True, 300),
    ("observed, cadence unknown", True, None),
    ("not observed, cadence known", False, 300),
    ("not observed, cadence unknown", False, None),
]


def _section_slice(rendered):
    heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(
        i18n.t(health_page.CHECK_IN_SECTION_HEADING))
    start = rendered.index(heading_marker)
    end = rendered.index("</section>", start) + len("</section>")
    return rendered[start:end]


def _visible_caption(section_html):
    m = re.search(r'<p class="text-label section-caption">(.*?)</p>', section_html)
    assert m is not None, "expected a visible caption <p> in the check-in card"
    return m.group(1)


def _disclosure_body(section_html):
    m = re.search(
        r'<details class="readings-disclosure"><summary>[^<]*</summary><p>(.*?)</p></details>',
        section_html)
    assert m is not None, "expected a readings-disclosure <details> in the check-in card"
    return m.group(1)


@pytest.mark.parametrize(
    ("case_name", "observed", "wake_interval_s"), _DISCLOSURE_CASES,
    ids=[case[0] for case in _DISCLOSURE_CASES])
def test_check_in_disclosure_moved_clauses_render_across_all_four_cases(
        tmp_path, monkeypatch, case_name, observed, wake_interval_s):
    """for all four check-in-card cases (observed x cadence-known), the
    visible caption carries EXACTLY CHECK_IN_CAPTION_OBSERVED and every
    other clause that case renders moves, byte-identical, into the card's
    own <details class="readings-disclosure"> — 'moved, not cut' proven as
    a relationship, case and clause named on failure"""
    monkeypatch.delenv(wake.SLEEP_ENV_VAR, raising=False)
    if wake_interval_s is None:
        assert wake.effective_wake_interval_s(None) is None, (
            "%s: the environment still resolves a cadence — this case measures nothing" % (case_name,))
    state_dir = str(tmp_path)
    now = shp.now()
    if observed:
        rendered = _seeded_regularity_page(state_dir, now, wake_interval_s=wake_interval_s)
    else:
        if wake_interval_s is not None:
            device_config.save_device_config(state_dir, wake_interval_s=wake_interval_s)
        rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    section_html = _section_slice(rendered)
    visible = _visible_caption(section_html)
    expected_visible = layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_OBSERVED))
    assert visible == expected_visible, (
        "%s: expected the visible caption to be EXACTLY %r, got %r" % (case_name, expected_visible, visible))

    disclosure = _disclosure_body(section_html)
    expected_disclosure_clauses = []
    if not observed:
        expected_disclosure_clauses.append(layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_EMPTY)))
    if wake_interval_s is not None:
        expected_disclosure_clauses.append(layout.escape_html(
            i18n.t(health_page.CHECK_IN_CAPTION_CADENCE) % layout.duration_text(wake_interval_s)))
    else:
        expected_disclosure_clauses.append(layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_CADENCE_FALLBACK)))
    expected_disclosure_clauses.append(layout.escape_html(i18n.t(health_page.CHECK_IN_CAPTION_NOT_PROOF)))
    for clause in expected_disclosure_clauses:
        assert clause in disclosure, (
            "%s: expected clause %r inside the disclosure — missing (the 'moved, not cut' "
            "guarantee is broken)" % (case_name, clause))
        assert clause not in visible, (
            "%s: expected clause %r to be MOVED out of the visible caption, still found there"
            % (case_name, clause))


def test_sparkline_axis_chrome_present():
    """battery_sparkline_svg() draws real axis chrome — at least one
    full-height vertical axis <rect>, at least one full-width horizontal
    axis <rect>, and at least two tick <rect> elements, all carrying
    SPARKLINE_AXIS_CLASS and aria-hidden="true" on their own tags"""
    rows = [
        {"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4000 + i * 40}
        for i in range(5)]
    svg = health_page.battery_sparkline_svg(rows)

    axis_rects = []
    tag_start = 0
    while True:
        idx = svg.find('<rect class="%s"' % health_page.SPARKLINE_AXIS_CLASS, tag_start)
        if idx == -1:
            break
        tag_end = svg.index(">", idx)
        tag = svg[idx:tag_end + 1]
        assert 'aria-hidden="true"' in tag, "expected every sparkline-axis <rect> to carry aria-hidden=\"true\" on its own tag"
        axis_rects.append(tag)
        tag_start = tag_end

    vertical = [t for t in axis_rects if 'height="100%"' in t]
    horizontal = [t for t in axis_rects if 'width="100%"' in t]
    assert vertical, "expected at least one full-height vertical axis <rect> (height=\"100%\")"
    assert horizontal, "expected at least one full-width horizontal axis <rect> (width=\"100%\")"

    ticks = [t for t in axis_rects if t not in vertical and t not in horizontal]
    assert len(ticks) >= 2, "expected at least two tick <rect> elements (neither full-height nor full-width), got %d" % len(ticks)


def test_sparkline_daily_mode_shows_date_endpoints_not_clock():
    """battery_sparkline_svg(daily=True) renders day-plus-month date
    endpoint labels ('31 Aug'/'2 Sep'), never the clock-format labels a day
    string would otherwise silently print"""
    # In daily mode, the X-axis endpoints must be day-plus-month date
    # labels (_axis_day_label()), never the clock-format labels a day
    # string would otherwise silently render as.
    rows = [
        {"ts": "2026-09-02", "battery_mv": 4100, "reading_count": 12},
        {"ts": "2026-09-01", "battery_mv": 4101, "reading_count": 9},
        {"ts": "2026-08-31", "battery_mv": 4102, "reading_count": 1},
    ]
    svg = health_page.battery_sparkline_svg(rows, now="2026-09-02T12:00:00+00:00", daily=True)
    labels = re.findall(r'<span class="sparkline-axis-label"[^>]*>([^<]*)</span>', svg)
    assert len(labels) == 4, "expected exactly four axis labels (2 Y, 2 X), got %r" % (labels,)
    x_labels = labels[2:]
    assert x_labels == ["31 Aug", "2 Sep"], "expected the oldest-then-newest date endpoints '31 Aug'/'2 Sep', got %r" % (x_labels,)
    assert not re.search(r">\d{2}:\d{2}<", svg), "found a clock-format (HH:MM) label — a day string must never render through the clock formatter"


def test_sparkline_daily_point_label_names_day_and_average_count():
    """each daily chart point's data-when names its day, says it is a daily
    average, and gives the singular/plural-correct contributing reading
    count"""
    rows = [
        {"ts": "2026-09-02", "battery_mv": 4100, "reading_count": 12},
        {"ts": "2026-09-01", "battery_mv": 4101, "reading_count": 9},
        {"ts": "2026-08-31", "battery_mv": 4102, "reading_count": 1},
    ]
    svg = health_page.battery_sparkline_svg(rows, now="2026-09-02T12:00:00+00:00", daily=True)
    whens = re.findall(r'data-when="([^"]*)"', svg)
    assert len(whens) == 3, "expected one humanised label per point, got %r" % (whens,)
    newest = whens[-1]
    assert "2 Sep" in newest and "12" in newest, "expected the newest point's label to name its day and its 12-reading count: %r" % newest
    assert "average" in newest.lower(), "expected the newest point's label to say it is a daily average: %r" % newest
    oldest = whens[0]
    assert re.search(r"\b1 reading\b", oldest), "expected a single-reading day to read singular ('1 reading', not '1 readings'): %r" % oldest


def test_sparkline_density_rule_suppresses_dots_only_above_threshold():
    """the density rule suppresses cosmetic dots only at/above the derived
    threshold (every hit target still reachable, at the reduced radius),
    survives untouched just below it, and a below-threshold non-daily call
    stays byte-for-byte what it is today"""
    threshold_names = [name for name in dir(health_page) if "DENSE" in name]
    assert threshold_names, "expected a named, documented DENSE* density-threshold constant, not a literal in the loop"
    threshold = max(
        getattr(health_page, name) for name in threshold_names
        if isinstance(getattr(health_page, name), int) and getattr(health_page, name) > 10)

    dense_rows = [
        {"ts": "2026-06-%02d" % ((i % 28) + 1), "battery_mv": 4000 + i}
        for i in range(threshold + 5)]
    dense_svg = health_page.battery_sparkline_svg(dense_rows, now="2026-09-02T12:00:00+00:00", daily=True)
    assert health_page.SPARKLINE_DOT_CLASS not in dense_svg, "expected no cosmetic dots above the density threshold"
    assert dense_svg.count(health_page.SPARKLINE_HIT_CLASS) == len(dense_rows), (
        "expected every point to keep its own hit target above the density threshold")
    assert 'r="8"' not in dense_svg, "expected the reduced dense hit radius above the threshold, not the normal r=\"8\""
    assert dense_svg.count(health_page.SPARKLINE_LINE_CLASS) == len(dense_rows) - 1, (
        "expected the thin trend line to still carry one segment per adjacent pair above the threshold")

    just_under_rows = [
        {"ts": "2026-06-%02d" % ((i % 28) + 1), "battery_mv": 4000 + i}
        for i in range(threshold - 1)]
    just_under_svg = health_page.battery_sparkline_svg(just_under_rows, now="2026-09-02T12:00:00+00:00", daily=True)
    assert health_page.SPARKLINE_DOT_CLASS in just_under_svg, "expected cosmetic dots to survive just below the density threshold"
    assert 'r="8"' in just_under_svg, "expected the normal, full-size hit radius just below the density threshold"

    sparse_rows = [{"ts": "2024-01-01T0%d:00:00" % i, "battery_mv": 4200 - i * 10} for i in range(3)]
    sparse_svg = health_page.battery_sparkline_svg(sparse_rows)
    assert health_page.SPARKLINE_DOT_CLASS in sparse_svg, "a below-threshold, non-daily call must keep its cosmetic dots (regression guard)"
    assert 'r="8"' in sparse_svg, "a below-threshold, non-daily call must keep its normal hit radius (regression guard)"
    assert re.search(r">\d{2}:\d{2}<", sparse_svg), "a below-threshold, non-daily call must keep its clock endpoint labels (regression guard)"


def test_battery_readout_seeded_with_latest_reading_not_placeholder(tmp_path, monkeypatch):
    """the battery readout's initial markup equals the humanised (value,
    when) pair the latest reading's own helper builds, split across its
    value/detail spans, and the retired placeholder prompt no longer
    appears"""
    # health_page._battery_section() deliberately computes its own `now`
    # via history_db.utc_now_iso() rather than the render() ctx's injected
    # `now`, so the real wall clock humanises the readout's "ago" text.
    # Pinning utc_now_iso() to `base` makes the two `now` values agree.
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    monkeypatch.setattr(history_db, "utc_now_iso", lambda: shp.iso(base))
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    value_text, when_text = health_page._battery_reading_parts(4190, shp.iso(base), shp.iso(base))
    # The detail span's title is when_text itself (a full Europe/Paris
    # local timestamp), never the raw ISO, and the span carries the
    # .time-value role.
    expected_inner = (
        '<span class="battery-readout__value mono">%s</span>'
        '<span class="battery-readout__detail time-value" title="%s"> — %s</span>'
    ) % (
        health_page.escape_html(value_text),
        health_page.escape_html(when_text),
        health_page.escape_html(when_text),
    )
    readout_start = rendered.index('id="%s"' % health_page.BATTERY_READOUT_ID)
    readout_tag_end = rendered.index(">", readout_start)
    readout_text_end = rendered.index("</p>", readout_tag_end)
    readout_inner = rendered[readout_tag_end + 1:readout_text_end]
    assert readout_inner == expected_inner, (
        "expected the readout's inner markup to equal the humanised (value, when) pair built by "
        "_battery_reading_parts(), got %r" % (readout_inner,))
    assert "Tap or hover a point" not in rendered, (
        "did not expect the retired BATTERY_READOUT_PLACEHOLDER prompt text anywhere on the page")


def test_battery_reading_parts_value_carries_the_percentage_estimate():
    """_battery_reading_parts()'s value text leads with a '≈ NN%' estimate
    ahead of the exact millivolt figure, for a numeric reading
    battery.battery_percent() can estimate"""
    value_text, _when_text = health_page._battery_reading_parts(
        3750, "2026-09-11T10:00:00+00:00", "2026-09-11T10:05:00+00:00")
    assert value_text.startswith("≈"), "expected the value text to start with the estimate's ≈ marker, got %r" % value_text
    assert "%" in value_text, "expected a percentage sign in the value text, got %r" % value_text
    assert "3750 mV" in value_text, "expected the exact millivolt figure to survive as a substring, got %r" % value_text


def test_battery_reading_parts_value_has_no_estimate_when_percent_is_none():
    """_battery_reading_parts()'s value text stays a bare millivolt figure,
    with no ≈ marker, when battery.battery_percent() cannot estimate the
    reading"""
    # battery.battery_percent(0) returns None (the non-positive guard) —
    # the value text must fall back to the bare millivolt figure, with no
    # stray "≈", rather than raising on a reading the estimate cannot be
    # computed for.
    value_text, _when_text = health_page._battery_reading_parts(
        0, "2026-09-11T10:00:00+00:00", "2026-09-11T10:05:00+00:00")
    assert "≈" not in value_text, "expected no ≈ marker when battery.battery_percent() returns None, got %r" % value_text
    assert value_text == "0 mV", "expected the bare millivolt figure with no estimate, got %r" % value_text


# ==========================================================================
# layout.local_clock_text() is the only formatter for a visible battery
# time — the readout, every sparkline point's tooltip/aria-label/data-when,
# and the axis clock labels all read Paris local text, and the literal
# " UTC" appears nowhere in the rendered page.
# ==========================================================================


def test_axis_clock_label_is_paris_local_not_utc():
    """_axis_clock_label() renders Europe/Paris local time, not the
    unconverted UTC clock: 22:30 UTC in September prints '00:30', not
    '22:30'"""
    # 22:30 UTC in September (CEST, Europe/Paris = UTC+2) is 00:30 the
    # NEXT Paris day.
    clock = health_page._axis_clock_label("2026-09-02T22:30:00+00:00")
    assert clock == "00:30", "expected the Paris-local clock '00:30', got %r" % clock


def test_axis_day_label_names_the_paris_day():
    """_axis_day_label() names the Europe/Paris calendar day an instant
    falls on, not its UTC day"""
    # Same instant as above: 22:30 UTC on 2026-09-02 is 00:30 Paris on
    # 2026-09-03 — the axis day label must name the LATER day.
    day = health_page._axis_day_label("2026-09-02T22:30:00+00:00")
    assert day == "3 Sep", "expected the Paris day label '3 Sep', got %r" % day


def test_sparkline_point_title_aria_data_when_are_one_string():
    """a sparkline point's <title>, aria-label and data-when carry the SAME
    string — one formatted value, never three independently-derived ones"""
    rows = [
        {"ts": "2026-09-11T22:30:00+00:00", "battery_mv": 4100},
        {"ts": "2026-09-12T10:00:00+00:00", "battery_mv": 4050},
    ]
    svg = health_page.battery_sparkline_svg(rows, now="2026-09-12T12:00:00+00:00")
    hit_start = svg.rindex('class="%s"' % health_page.SPARKLINE_HIT_CLASS)
    tag_end = svg.index(">", hit_start)
    tag = svg[hit_start:tag_end + 1]
    title_match = re.search(r"<title>([^<]*)</title>", svg[tag_end:])
    aria_match = re.search(r'aria-label="([^"]*)"', tag)
    when_match = re.search(r'data-when="([^"]*)"', tag)
    assert title_match and aria_match and when_match, "expected a title, aria-label and data-when on the latest hit target"
    assert title_match.group(1) == aria_match.group(1) == when_match.group(1), (
        "expected the tooltip, aria-label and data-when to carry the same string, got title=%r "
        "aria-label=%r data-when=%r" % (title_match.group(1), aria_match.group(1), when_match.group(1)))
    assert "UTC" not in when_match.group(1), "expected zero occurrences of 'UTC' in a sparkline point's data-when"


def test_health_page_has_zero_utc_literal_in_either_language(tmp_path):
    """a seeded Health page renders zero occurrences of the literal ' UTC'
    in either English or French"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(now - timedelta(days=2)), 4200),
        (shp.iso(now - timedelta(days=1)), 4150),
        (shp.iso(now), 4100),
    ])
    try:
        prefs.set_request_prefs(lang="en")
        en_rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
        prefs.set_request_prefs(lang="fr")
        fr_rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    for lang_name, rendered in (("EN", en_rendered), ("FR", fr_rendered)):
        assert " UTC" not in rendered, "expected zero ' UTC' occurrences in the %s-rendered Health page" % lang_name


# ==========================================================================
# The client-side hover swap reads only pre-formatted server text (no date
# parsing/formatting of its own, and no raw-ISO fallback), and
# concise_timestamp_html()'s title is a local full timestamp, never the
# raw ISO.
# ==========================================================================


def test_battery_trend_js_has_no_client_side_date_math(battery_trend_js):
    """battery-trend.js contains no client-side date parsing or formatting
    (new Date(), toISOString, getHours, getMinutes), sets title to the
    pre-formatted 'when' text rather than the raw ts, and its fallback no
    longer shows a raw ISO string"""
    js_source = battery_trend_js
    assert not re.search(r"new Date\(|toISOString|getHours|getMinutes", js_source), (
        "expected zero client-side date-parsing/formatting calls in battery-trend.js")
    assert 'setAttribute("title", ts)' not in js_source, "expected the raw-ts title write to be gone"
    assert 'setAttribute("title", when)' in js_source, "expected the hover swap to set title to the pre-formatted 'when' text"
    assert 'mv + " mV — " + ts' not in js_source, "expected the raw-ISO fallback line to be gone"


def test_concise_timestamp_html_title_is_a_full_local_timestamp_not_raw_iso():
    """concise_timestamp_html()'s title is a full Europe/Paris local
    timestamp ('D Mon HH:MM'), never the raw ISO string and never a 'UTC'
    suffix"""
    now_iso = "2026-09-12T12:00:00+00:00"
    ts = "2026-09-11T22:30:00+00:00"  # 00:30 Paris the NEXT day (CEST)
    rendered = layout.concise_timestamp_html(ts, now_iso)
    assert ts not in rendered, "expected zero occurrences of the raw ISO string in concise_timestamp_html()'s output"
    title_match = re.search(r'title="([^"]*)"', rendered)
    assert title_match is not None, "expected a title attribute"
    assert re.search(r"^\d{1,2} \w+ \d{2}:\d{2}$", title_match.group(1)), (
        "expected a full 'D Mon HH:MM' local timestamp in the title, got %r" % title_match.group(1))
    assert "UTC" not in rendered, "expected zero occurrences of 'UTC' in concise_timestamp_html()'s output"


def test_seeded_render_shows_both_the_estimate_and_the_millivolt_figure(tmp_path):
    """a seeded health_page.render() call's battery-readout__value span
    carries both the '≈' estimate and the ' mV' millivolt figure"""
    state_dir = str(tmp_path)
    base = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 3750),
    ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    readout_start = rendered.index('id="%s"' % health_page.BATTERY_READOUT_ID)
    value_start = rendered.index('class="battery-readout__value mono"', readout_start)
    value_tag_end = rendered.index(">", value_start) + 1
    value_end = rendered.index("</span>", value_tag_end)
    value_html = rendered[value_tag_end:value_end]
    assert "≈" in value_html, "expected the ≈ estimate marker inside the readout's value span"
    assert " mV" in value_html, "expected the millivolt figure inside the readout's value span"


# --- Text verdicts on the Device/Pipeline/Corroboration stat tiles --------
# (WCAG 1.4.1)
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("age_s", "expected_state"),
    [(0, "ok"), (_DEFAULT_DEVICE_WARN_S + 60, "warn"), (_DEFAULT_DEVICE_ERROR_S + 60, "error")],
    ids=["ok", "warn", "error"])
def test_device_tile_verdict_matches_state_at_each_severity(tmp_path, age_s, expected_state):
    """the Device tile's widget-verdict paragraph matches DEVICE_STATE_TEXT
    at each of the three severities a real health_page.render() call can
    produce"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now - timedelta(seconds=age_s)), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    expected_verdict_html = '<p class="text-body widget-verdict">%s</p>' % health_page.escape_html(
        health_page.DEVICE_STATE_TEXT[expected_state])
    tile_slice = _tile_slice_by_caption(rendered, health_page.DEVICE_FRESHNESS_LABEL)
    assert expected_verdict_html in tile_slice, (
        "expected the Device tile's verdict paragraph for state %r, got tile %r" % (expected_state, tile_slice))


@pytest.mark.parametrize(
    ("age_s", "expected_state"),
    [(0, "ok"), (health_page.STALE_PIPELINE_WARN_S + 30, "warn"), (health_page.STALE_PIPELINE_ERROR_S + 30, "error")],
    ids=["ok", "warn", "error"])
def test_pipeline_tile_verdict_matches_state_at_each_severity(tmp_path, age_s, expected_state):
    """the Pipeline tile's widget-verdict paragraph matches
    PIPELINE_STATE_TEXT at each of the three severities a real
    health_page.render() call can produce"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now - timedelta(seconds=age_s))})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    expected_verdict_html = '<p class="text-body widget-verdict">%s</p>' % health_page.escape_html(
        health_page.PIPELINE_STATE_TEXT[expected_state])
    tile_slice = _tile_slice_by_caption(rendered, health_page.PIPELINE_FRESHNESS_LABEL)
    assert expected_verdict_html in tile_slice, (
        "expected the Pipeline tile's verdict paragraph for state %r, got tile %r" % (expected_state, tile_slice))


@pytest.mark.parametrize(
    ("corroborated", "expected_state"), [(True, "ok"), (False, "warn")],
    ids=["agree", "disagree"])
def test_corroboration_tile_verdict_matches_disagreement_state(tmp_path, corroborated, expected_state):
    """the Corroboration tile's widget-verdict paragraph matches
    CORROBORATION_STATE_TEXT for both the agreement and disagreement
    states a real health_page.render() call can produce"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": corroborated}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    expected_verdict_html = '<p class="text-body widget-verdict">%s</p>' % health_page.escape_html(
        health_page.CORROBORATION_STATE_TEXT[expected_state])
    tile_slice = _tile_slice_by_caption(rendered, "Corroboration")
    assert expected_verdict_html in tile_slice, (
        "expected the Corroboration tile's verdict paragraph for state %r, got tile %r" % (expected_state, tile_slice))


def test_resolution_rate_tile_carries_no_verdict(tmp_path):
    """the Resolution-rate tile deliberately carries no widget-verdict
    paragraph"""
    # The Resolution-rate tile is the one deliberate exception: it is
    # passed status=None and has no status function of its own, so
    # inventing a verdict word for it would assert a judgement this page
    # does not make.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    tile_slice = _tile_slice_by_caption(rendered, health_page.RESOLUTION_RATE_LABEL)
    assert "widget-verdict" not in tile_slice, (
        "expected the Resolution-rate tile to carry no widget-verdict paragraph, got tile %r" % (tile_slice,))


# --- One tile anatomy ------------------------------------------------------
#
# The Emphasis slot is ONE element per tile, but two class names can
# legitimately carry it: a verdict word (three tiles) and a figure (the
# Resolution-rate tile, which carries no verdict of its own).
# The empty form is a third, and is the compact empty_state()'s own
# heading. The muted detail slot is the same two-way split.
_EMPHASIS_SLOT_CLASSES = (
    'class="%s"' % health_page._TILE_VERDICT_CLASS,
    'class="stat-tile__value"',
    'class="empty-state__heading text-body"',
)
_DETAIL_SLOT_CLASSES = (
    'class="%s"' % health_page._TILE_DETAIL_CLASS,
    'class="empty-state__body text-label section-caption"',
)


@pytest.mark.parametrize("seed", [True, False], ids=["seeded", "fresh"])
def test_one_tile_anatomy_across_every_health_tile(tmp_path, seed):
    """every .stat-tile on a rendered Health page — seeded and on a fresh
    install alike — carries exactly one label, exactly one Emphasis-role
    element, exactly one muted detail slot, in that fixed order, and no
    22px serif heading anywhere inside it"""
    # Walks EVERY .stat-tile on a rendered page and asserts the four slots
    # in their fixed order.
    state_dir = str(tmp_path)
    now = shp.now()
    if seed:
        shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
        shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
        shp.seed_runway_events(state_dir, [
            {"ts": shp.iso(now), "hex": "abc001", "route_source": "fresh_hit", "corroborated": True},
            {"ts": shp.iso(now), "hex": "abc002", "route_source": "manual", "corroborated": None},
        ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    tiles = shp.stat_tile_slices(rendered)
    assert len(tiles) == 4, "expected exactly 4 .stat-tile elements on Health, got %d" % len(tiles)
    for tile in tiles:
        captions = tile.count('class="text-label stat-tile__caption"')
        assert captions == 1, "expected exactly one label slot per tile, got %d in %r" % (captions, tile[:200])
        emphasis = [tile.index(token) for token in _EMPHASIS_SLOT_CLASSES if token in tile]
        assert len(emphasis) == 1 and sum(tile.count(token) for token in _EMPHASIS_SLOT_CLASSES) == 1, (
            "expected exactly one Emphasis-role element per tile — the 'double bold verdict' X8 "
            "removed is two — got %r" % (tile,))
        detail = [tile.index(token) for token in _DETAIL_SLOT_CLASSES if token in tile]
        assert len(detail) == 1 and sum(tile.count(token) for token in _DETAIL_SLOT_CLASSES) == 1, (
            "expected exactly one muted detail slot per tile, got %r" % (tile,))
        caption_at = tile.index('class="text-label stat-tile__caption"')
        assert caption_at < emphasis[0] < detail[0], (
            "expected the label/verdict/detail slots in that fixed order, got offsets %d/%d/%d in %r"
            % (caption_at, emphasis[0], detail[0], tile))
        # C1/X8: never a 22px serif heading inside a tile whose own caption
        # is 12px.
        assert "text-heading" not in tile, "expected no serif .text-heading inside any .stat-tile, got %r" % (tile,)


@pytest.mark.parametrize(
    ("lang", "agree_label", "single_label"),
    [("en", "Both agree", "Only one saw it"), ("fr", "Les deux concordent", "Une seule l’a vu")])
def test_only_one_saw_it_is_neutral_and_still_distinct(tmp_path, lang, agree_label, single_label):
    """Health's 'Only one saw it' corroboration row renders the neutral
    dot--off with its own distinct visible dot-label while 'Both agree'
    keeps dot--ok — in both languages, and never a warn dot — so the two
    states are readable with colour vision entirely absent"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc001", "corroborated": True},
        {"ts": shp.iso(now), "hex": "abc002", "corroborated": None},
    ])
    try:
        prefs.set_request_prefs(lang=lang)
        rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    tile = _tile_slice_by_caption(
        rendered, health_page.CORROBORATION_TILE_LABEL if lang == "en" else "Corroboration")
    single_row = '<span class="dot dot--off"></span><span class="dot-label">%s</span>' % single_label
    assert single_row in tile, (
        "expected the single-source row to render the neutral dot with its own visible label "
        "(%s), got tile %r" % (lang, tile))
    agree_row = '<span class="dot dot--ok"></span><span class="dot-label">%s</span>' % agree_label
    assert agree_row in tile, "expected 'Both agree' to keep the ok dot (%s), got tile %r" % (lang, tile)
    assert agree_label != single_label, "expected the two labels to differ (%s)" % (lang,)
    assert '<span class="dot dot--ok"></span><span class="dot-label">%s' % single_label not in tile, (
        "expected the single-source row NEVER to take the ok dot again (%s)" % (lang,))
    assert "dot--warn" not in tile, (
        "expected no warn dot in a tile with no disagreement (%s) — a neutral state must not be "
        "escalated instead of de-escalated" % (lang,))


def test_empty_state_default_form_is_byte_identical_and_compact_is_opt_in():
    """layout.empty_state()'s two-argument output is byte-identical to its
    pre-compact form (proven against the literal markup AND against
    data_table()'s own real no-rows caller), an explicit compact=False
    matches it, and compact=True renders its own modifier plus the 16px
    sans / 14px muted pair through the empty state's own class names, still
    escaped"""
    # The compact variant must not be able to change an existing caller.
    # The default form's expected markup is written out as a LITERAL
    # here, copied from the pre-change function, so this check fails even
    # if layout.empty_state() and the expectation are edited together.
    heading, body = "No data yet.", "Nothing to show here yet."
    expected_default = (
        '<div class="empty-state">'
        '<p class="empty-state__heading text-heading">No data yet.</p>'
        '<p class="empty-state__body text-body">Nothing to show here yet.</p>'
        "</div>")
    assert layout.empty_state(heading, body) == expected_default, (
        "expected the two-argument empty_state() output to be byte-identical to its pre-compact "
        "form, got %r" % (layout.empty_state(heading, body),))
    assert layout.empty_state(heading, body, compact=False) == expected_default, (
        "expected an explicit compact=False to be byte-identical too")
    # The default form is what data_table()'s own no-rows fallback emits —
    # an existing caller, proven rather than asserted.
    assert layout.data_table(["A"], []) == expected_default, (
        "expected data_table()'s no-rows fallback (a real existing caller) to render the "
        "unchanged default empty state, got %r" % (layout.data_table(["A"], []),))
    compact = layout.empty_state(heading, body, compact=True)
    assert compact != expected_default, "expected compact=True to render a different block"
    assert "text-heading" not in compact, "expected the compact form to carry no 22px serif .text-heading, got %r" % (compact,)
    assert 'class="empty-state empty-state--compact"' in compact, "expected the compact form to carry its own modifier class"
    assert 'class="empty-state__heading text-body"' in compact, "expected the compact heading on the Emphasis role's own size class"
    assert 'class="empty-state__body text-label section-caption"' in compact, (
        "expected the compact body at the label size and the 70% muted strength")
    assert "widget-verdict" not in compact and "widget-detail" not in compact, (
        "expected the compact form to reach its treatment through its OWN class names — borrowing "
        ".widget-verdict would break the Resolution-rate tile's D-03/A-21 no-verdict pin on its "
        "own empty branch")
    # Escaping is unchanged on both paths.
    hostile = layout.empty_state("<b>h</b>", "<i>b</i>", compact=True)
    assert "<b>" not in hostile and "<i>" not in hostile, "expected the compact form to escape both arguments"


def test_health_in_tile_empty_states_are_compact_and_card_ones_are_not(tmp_path):
    """on a fresh install Health's two IN-TILE empty states (Corroboration,
    Resolution rate) use the compact form while its two full-width card
    empty states (Battery trend, Unresolved prefixes) keep the default
    22px serif one"""
    # The compact form belongs to the two empty states that land INSIDE a
    # .stat-tile. The two full-width card empty states on the same page
    # keep the default form — the variant is a tile fix, not a page-wide
    # restyle.
    state_dir = str(tmp_path)
    now = shp.now()
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    tiles = shp.stat_tile_slices(rendered)
    in_tile = [tile for tile in tiles if "empty-state" in tile]
    assert len(in_tile) == 2, (
        "expected exactly two in-tile empty states on a fresh install (Corroboration and "
        "Resolution rate), got %d" % (len(in_tile),))
    for tile in in_tile:
        assert "empty-state--compact" in tile, "expected every in-tile empty state to use the compact form"
    # ...and the full-card ones are untouched.
    outside = rendered
    for tile in tiles:
        outside = outside.replace(tile, "")
    default_blocks = outside.count('<div class="empty-state">')
    assert default_blocks == 2, (
        "expected the two full-width card empty states (Battery trend, Unresolved prefixes) to "
        "keep the default form, got %d" % (default_blocks,))
    assert "empty-state--compact" not in outside, (
        "expected no compact empty state outside a .stat-tile — the variant is a tile fix, not a "
        "page-wide restyle")


_RESOLUTION_SINGULAR_CASES = [
    (1, "en", "over the last %d days, 1 event" % health_page.RESOLUTION_WINDOW_DAYS, "1 events"),
    (1, "fr", "au cours des %d derniers jours, 1 événement" % health_page.RESOLUTION_WINDOW_DAYS,
     "1 événements"),
    (2, "en", "over the last %d days, 2 events" % health_page.RESOLUTION_WINDOW_DAYS, None),
    (2, "fr", "au cours des %d derniers jours, 2 événements" % health_page.RESOLUTION_WINDOW_DAYS, None),
]


@pytest.mark.parametrize(
    ("total", "lang", "expected", "forbidden"), _RESOLUTION_SINGULAR_CASES,
    ids=["total=1-en", "total=1-fr", "total=2-en", "total=2-fr"])
def test_resolution_detail_line_has_a_singular_form(tmp_path, total, lang, expected, forbidden):
    """the Resolution-rate tile's detail line has a singular form, so a
    window holding exactly one detection never reads '1 events' /
    '1 événements', in both languages"""
    # The last plural on this page with no singular form — a window
    # holding exactly one detection read "over the last 30 days, 1
    # events".
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc%03d" % index, "route_source": "fresh_hit"}
        for index in range(total)])
    try:
        prefs.set_request_prefs(lang=lang)
        rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    assert expected in rendered, "expected %r for total=%d in %s" % (expected, total, lang)
    if forbidden is not None:
        assert forbidden not in rendered, "expected no %r anywhere for total=%d in %s" % (forbidden, total, lang)


def test_resolution_detail_templates_have_french_catalogue_entries():
    """the Resolution-rate tile's singular and plural detail templates both
    exist as separate constants with their own French catalogue entries,
    never a runtime add-an-s"""
    for template in (health_page._RESOLUTION_DETAIL_TEMPLATE, health_page._RESOLUTION_DETAIL_SINGULAR_TEMPLATE):
        assert health_page.i18n.t_lang(template, "fr") != template, (
            "expected %r to have its own French catalogue entry" % (template,))


def test_state_text_dicts_have_expected_key_sets():
    """DEVICE_STATE_TEXT has exactly ok/warn/error/off (widened for the
    frame's own held state), PIPELINE_STATE_TEXT has exactly
    ok/warn/error/off and CORROBORATION_STATE_TEXT has exactly ok/warn (it
    has no error state)"""
    # DEVICE_STATE_TEXT gains the fourth "off" key
    # (frame_state.STATE_HELD's own neutral device_state);
    # CORROBORATION_STATE_TEXT is deliberately unwidened.
    assert set(health_page.DEVICE_STATE_TEXT) == {"ok", "warn", "error", "off"}, (
        "expected DEVICE_STATE_TEXT's keys to be exactly ok/warn/error/off, got %r" % (set(health_page.DEVICE_STATE_TEXT),))
    assert set(health_page.PIPELINE_STATE_TEXT) == {"ok", "warn", "error", "off"}, (
        "expected PIPELINE_STATE_TEXT's keys to be exactly ok/warn/error/off, got %r" % (set(health_page.PIPELINE_STATE_TEXT),))
    assert set(health_page.CORROBORATION_STATE_TEXT) == {"ok", "warn"}, (
        "expected CORROBORATION_STATE_TEXT's keys to be exactly ok/warn, got %r" % (set(health_page.CORROBORATION_STATE_TEXT),))


# ==========================================================================
# A real neutral never-ran pipeline state, and a verdict-free
# pipeline_detail_html for Home.
# ==========================================================================


def test_pipeline_never_ran_renders_neutral_no_warn_no_banner(tmp_path):
    """a genuinely never-ran pipeline (no META_LAST_PIPELINE_RUN, no
    META_LAST_DETECTION) renders the neutral verdict with the existing
    dot--off class, zero dot--warn, zero battery-fallback text, no second
    detail line, and no anomaly banner when the device is healthy"""
    # A pipeline that has genuinely never run renders the neutral "No
    # detection yet" verdict — proven against a real health_page.render()
    # call, with the device seeded healthy so only the pipeline signal is
    # under test.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    tile_slice = _tile_slice_by_caption(rendered, health_page.PIPELINE_FRESHNESS_LABEL)
    expected_verdict_html = (
        '<p class="text-body widget-verdict">'
        '<span class="dot dot--off"></span>%s</p>'
        % health_page.escape_html(health_page.PIPELINE_STATE_TEXT["off"]))
    assert expected_verdict_html in tile_slice, "expected the never-ran neutral verdict paragraph, got tile %r" % (tile_slice,)
    assert "dot--warn" not in tile_slice, "expected zero dot--warn occurrences in a never-ran pipeline tile"
    assert layout.escape_html("no reading yet") not in tile_slice, "expected zero battery-fallback occurrences in a never-ran pipeline tile"
    assert health_page.LAST_DETECTION_LABEL not in tile_slice, (
        "expected no second 'Last aircraft detected' line in a never-ran pipeline tile — "
        "last_detection is falsy by definition here, so that line would always render the "
        "battery fallback")
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, "expected no anomaly banner for a never-ran pipeline with a healthy device"


def test_pipeline_never_ran_renders_neutral_in_french(tmp_path):
    """the same never-ran pipeline tile reads in French — 'Aucune détection
    pour l’instant.', dot--off, zero dot--warn, zero French battery-
    fallback text"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    tile_slice = _tile_slice_by_caption(rendered, "Dernière mise à jour des données de vol")
    assert "Aucune détection pour l’instant." in tile_slice, "expected the French never-ran verdict text in the pipeline tile"
    assert "dot--warn" not in tile_slice, "expected zero dot--warn occurrences in a never-ran pipeline tile under French"
    assert "aucune mesure pour l’instant" not in tile_slice, "expected zero French battery-fallback occurrences in a never-ran pipeline tile"


def test_compute_health_state_carries_pipeline_detail_html_never_ran(tmp_path):
    """compute_health_state()'s pipeline_detail_html key, for a never-ran
    pipeline, is the bare PIPELINE_NEVER_RAN_DETAIL_TEXT sentence — no
    widget-verdict class, no PIPELINE_STATE_TEXT verdict text — embedded
    once inside pipeline_html"""
    state_dir = str(tmp_path)
    now = shp.now()
    state = health_page.compute_health_state(state_dir, now=shp.iso(now))
    assert "pipeline_detail_html" in state, "expected a pipeline_detail_html key on compute_health_state()'s dict"
    detail_only = state["pipeline_detail_html"]
    assert "widget-verdict" not in detail_only, "expected pipeline_detail_html to carry no widget-verdict class"
    for verdict_text in health_page.PIPELINE_STATE_TEXT.values():
        assert verdict_text not in detail_only, (
            "expected pipeline_detail_html to carry no PIPELINE_STATE_TEXT verdict text, found %r" % (verdict_text,))
    expected = health_page.escape_html(i18n.t(health_page.PIPELINE_NEVER_RAN_DETAIL_TEXT))
    assert detail_only == expected, (
        "expected pipeline_detail_html to equal the never-ran detail sentence exactly, got %r" % (detail_only,))
    assert detail_only in state["pipeline_html"], (
        "expected pipeline_detail_html to be the exact verdict-free fragment embedded inside pipeline_html")
