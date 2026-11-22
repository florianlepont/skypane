"""Companion status-page tests: the shared regularity-grid drawing, row verdicts, and Paris-local-time
and resolution-rate copy.

CSS/JS checks fetch served bytes from a running companion/app.py; everything
else calls health_page/draw/wake/layout directly, in-process.
"""
import re
from datetime import timedelta

import pytest

from companion import draw, i18n, layout, prefs
from companion.pages import health_page
import health_page_composition
import companion.test_status_pages_helpers as shp
import companion.wake as wake
from companion_app_server import served_asset, served_stylesheet
from companion_markup import parse_html
from server import history_db

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


# --- shared helper for the row-anatomy sweep (used from Task 2 onward) ----

def _card_verdict(rendered, key):
    """The System card's `(data-state, verdict text)` pair."""
    card = parse_html(rendered).select_one("#system-card-%s" % key)
    return card.attrs["data-state"], card.select_one(".sys-card__verdict").text()


# ==========================================================================
# battery_sparkline_svg(): axis labels, flat/wiggle/clamp, area, marks,
# the low-battery threshold
# ==========================================================================


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


# --- Health carries no check-in regularity grid ------------------------


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_battery_page_renders_no_check_in_regularity_grid(tmp_path, lang):
    """Even with check-in history seeded, the Battery page draws no regularity grid,
    legend or caption, and reports observations only."""
    state_dir = str(tmp_path)
    now = shp.now()
    today = now.astimezone(layout.LOCAL_TZ).replace(hour=1, minute=0, second=0, microsecond=0)
    shp.seed_device_health(state_dir, [
        (shp.iso(today - timedelta(days=1)), 4200),
        (shp.iso(today), 4180),
        (shp.iso(today + timedelta(hours=6)), 4160),
    ])
    try:
        prefs.set_request_prefs(lang=lang)
        rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    doc = parse_html(rendered)
    assert not doc.select(".check-in-grid"), "the Battery page must not draw the regularity grid"
    assert not doc.select(".drawing-cell"), "the Battery page must not draw regularity cells"
    assert not doc.select(".check-in-key"), "the Battery page must not draw the regularity key"
    # The page reports observations, never a rate of wakes the frame kept.
    lowered = rendered.lower()
    for banned in ("honoured", "punctual", "punctualité", "ponctual"):
        assert banned not in lowered, "the Battery page contains %r" % (banned,)


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
        en_rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
        prefs.set_request_prefs(lang="fr")
        fr_rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
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


@pytest.mark.parametrize(
    ("age_s", "expected_state"),
    [(0, "ok"), (_DEFAULT_DEVICE_WARN_S + 60, "warn"), (_DEFAULT_DEVICE_ERROR_S + 60, "error")],
    ids=["ok", "warn", "error"])
def test_connection_tile_verdict_matches_state_at_each_severity(tmp_path, age_s, expected_state):
    """the Connection tile's verdict matches DEVICE_STATE_TEXT at each of the
    three severities a real frame_tiles() call can produce, and its state names
    the same severity"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now - timedelta(seconds=age_s)), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    tile = health_page.frame_tiles(shp.ctx(state_dir, now_value=shp.iso(now))).connection
    assert (tile.state, tile.verdict) == (
        expected_state, i18n.t(health_page.DEVICE_STATE_TEXT[expected_state]))


@pytest.mark.parametrize(
    ("age_s", "expected_state"),
    [(0, "ok"), (health_page.STALE_PIPELINE_WARN_S + 30, "warn"), (health_page.STALE_PIPELINE_ERROR_S + 30, "error")],
    ids=["ok", "warn", "error"])
def test_flight_data_card_and_tile_verdict_match_state_at_each_severity(tmp_path, age_s, expected_state):
    """the Flight data tile and the System view's flight data card carry the
    PIPELINE_STATE_TEXT verdict of the same state at each of the three severities"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now - timedelta(seconds=age_s))})
    ctx = shp.ctx(state_dir, now_value=shp.iso(now))
    verdict = i18n.t(health_page.PIPELINE_STATE_TEXT[expected_state])
    tile = health_page.frame_tiles(ctx).flight
    assert (tile.state, tile.verdict) == (expected_state, verdict)
    assert _card_verdict(health_page.system_html(ctx), "flight-data") == (expected_state, verdict)


@pytest.mark.parametrize(
    ("corroborated", "expected_state"), [(True, "ok"), (False, "warn")],
    ids=["agree", "disagree"])
def test_sources_card_verdict_matches_disagreement_state(tmp_path, corroborated, expected_state):
    """the System view's Sources card verdict matches CORROBORATION_STATE_TEXT for both the
    agreement and disagreement states"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": corroborated}])
    rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert _card_verdict(rendered, "sources") == (
        expected_state, i18n.t(health_page.CORROBORATION_STATE_TEXT[expected_state]))


def test_identification_card_carries_no_judgement(tmp_path):
    """the Identification card is neutral: it states the rate and the number left to
    resolve, with no pass/fail state of its own (an "ok" or "warn" card would assert
    a pass mark this page does not define)"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc%03d" % index,
         "route_source": "miss" if index == 0 else "fresh_hit"}
        for index in range(4)])
    rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert _card_verdict(rendered, "identification") == ("off", "75.0 % of flights identified")


# --- One row anatomy -------------------------------------------------------
#
# Every row renders the same slots, in the same order: an icon (with its
# spoken state word), a name, a verdict and a value inside the summary,
# then the evidence in the body.


@pytest.mark.parametrize("seed", [True, False], ids=["seeded", "fresh"])
def test_the_battery_row_has_one_anatomy_seeded_and_on_a_fresh_install(tmp_path, seed):
    """the row on a rendered Battery page — seeded and on a fresh install alike —
    carries exactly one icon, one name, one verdict and one value in its summary, in
    that fixed order, a body, and no 22px serif heading anywhere inside it"""
    state_dir = str(tmp_path)
    now = shp.now()
    if seed:
        shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    doc = parse_html(rendered)
    rows = doc.select("div.health-row")
    assert [row.attrs["id"] for row in rows] == ["health-row-battery"], (
        "expected the battery row alone")
    assert not doc.select(".stat-tile"), "no stat tile may remain on the Battery page"
    for row in rows:
        summary = row.select_one(".health-row__summary")
        slots = [child.attrs.get("class") for child in summary.children if hasattr(child, "attrs")]
        assert slots == [
            "health-row__icon", "health-row__name", "health-row__verdict", "health-row__value"], (
            "expected the summary's four slots in order, got %r" % (slots,))
        icon = summary.select_one(".health-row__icon")
        assert icon.select("svg") and icon.select(".visually-hidden"), (
            "the state needs an icon shape and a spoken word, never colour alone")
        assert row.select_one(".health-row__body") is not None
        assert not row.select(".text-heading"), (
            "expected no serif .text-heading inside any row, got %r" % (row,))


@pytest.mark.parametrize(
    ("lang", "agree_label", "single_label"),
    [("en", "Both agree", "Only one saw it"), ("fr", "Les deux concordent", "Une seule l’a vu")])
def test_only_one_saw_it_is_neutral_and_still_distinct(tmp_path, lang, agree_label, single_label):
    """the System view's 'Only one saw it' corroboration outcome renders the neutral
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
        rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    card = parse_html(rendered).select_one("#system-card-sources")
    body_html = rendered[rendered.index('id="system-card-sources"'):rendered.index('id="system-card-identification"')]
    single_row = '<span class="dot dot--off"></span><span class="dot-label">%s</span>' % single_label
    assert single_row in body_html, (
        "expected the single-source row to render the neutral dot with its own visible label "
        "(%s), got body %r" % (lang, card.text()))
    agree_row = '<span class="dot dot--ok"></span><span class="dot-label">%s</span>' % agree_label
    assert agree_row in body_html, "expected 'Both agree' to keep the ok dot (%s)" % (lang,)
    assert agree_label != single_label, "expected the two labels to differ (%s)" % (lang,)
    assert '<span class="dot dot--ok"></span><span class="dot-label">%s' % single_label not in body_html, (
        "expected the single-source row NEVER to take the ok dot again (%s)" % (lang,))
    assert "dot--warn" not in body_html, (
        "expected no warn dot in a card with no disagreement (%s) — a neutral state must not be "
        "escalated instead of de-escalated" % (lang,))


def test_empty_state_default_form_is_byte_identical_and_compact_is_opt_in():
    """layout.empty_state()'s two-argument output is byte-identical to its
    pre-compact form (proven against the literal markup), an explicit
    compact=False matches it, data_table()'s no-rows fallback is compact, and compact=True renders its own modifier plus the 16px
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
    compact = layout.empty_state(heading, body, compact=True)
    # data_table()'s no-rows fallback is the compact form.
    assert layout.data_table(["A"], []) == layout.empty_state(
        "No data yet.", "Nothing to show here yet.", compact=True), (
        "expected data_table()'s no-rows fallback to render the compact empty state")
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


def test_health_empty_states_are_all_compact(tmp_path):
    """on a fresh install the one Health empty state, the in-row one (Battery), uses the
    compact form"""
    state_dir = str(tmp_path)
    now = shp.now()
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    doc = parse_html(rendered)
    in_row = [row for row in doc.select("div.health-row") if row.select(".empty-state")]
    assert [row.attrs["id"] for row in in_row] == ["health-row-battery"], (
        "expected exactly one in-row empty state on a fresh install (Battery), got %r"
        % ([row.attrs["id"] for row in in_row],))
    assert in_row[0].select(".empty-state--compact"), "expected the in-row empty state to use the compact form"
    assert not doc.select("#unresolved-prefixes"), "the unresolved-prefix card is gone"


_RESOLUTION_SINGULAR_CASES = [
    (1, "en", "Last %d days: 1 flight" % health_page.RESOLUTION_WINDOW_DAYS, "1 flights"),
    (1, "fr", "%d derniers jours : 1 vol" % health_page.RESOLUTION_WINDOW_DAYS, "1 vols"),
    (2, "en", "Last %d days: 2 flights" % health_page.RESOLUTION_WINDOW_DAYS, None),
    (2, "fr", "%d derniers jours : 2 vols" % health_page.RESOLUTION_WINDOW_DAYS, None),
]


@pytest.mark.parametrize(
    ("total", "lang", "expected", "forbidden"), _RESOLUTION_SINGULAR_CASES,
    ids=["total=1-en", "total=1-fr", "total=2-en", "total=2-fr"])
def test_resolution_window_line_has_a_singular_form(tmp_path, total, lang, expected, forbidden):
    """the Identification card's window line has a singular form, so a
    window holding exactly one detection never reads '1 flights' /
    '1 vols', in both languages"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc%03d" % index, "route_source": "fresh_hit"}
        for index in range(total)])
    try:
        prefs.set_request_prefs(lang=lang)
        rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    text = parse_html(rendered).select_one("#system-card-identification").text().replace("\u00a0", " ")
    assert expected in text, "expected %r for total=%d in %s" % (expected, total, lang)
    if forbidden is not None:
        assert forbidden not in text, "expected no %r anywhere for total=%d in %s" % (forbidden, total, lang)


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
    META_LAST_DETECTION) renders the neutral verdict on the flight data card and tile,
    zero dot--warn, zero battery-fallback text, no dated facts, and no banner
    when the device is healthy"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    ctx = shp.ctx(state_dir, now_value=shp.iso(now))
    rendered = health_page.system_html(ctx)
    never = i18n.t(health_page.PIPELINE_STATE_TEXT["off"])
    assert _card_verdict(rendered, "flight-data") == ("off", never)
    tile = health_page.frame_tiles(ctx).flight
    assert (tile.state, tile.verdict) == ("off", never)
    card = parse_html(rendered).select_one("#system-card-flight-data")
    card_html = rendered[rendered.index('id="system-card-flight-data"'):rendered.index('id="system-card-sources"')]
    assert "dot--warn" not in card_html, "expected zero dot--warn occurrences in a never-ran pipeline card"
    assert layout.escape_html("no reading yet") not in card_html, "expected zero battery-fallback occurrences in a never-ran pipeline card"
    assert i18n.t(health_page.LAST_DETECTION_LABEL) not in card.text(), (
        "expected no 'Last aircraft detected' fact in a never-ran pipeline card — last_detection is "
        "falsy by definition here, so the sentence below says so instead of a dated fact")
    assert i18n.t(health_page.PIPELINE_NEVER_RAN_DETAIL_TEXT) in card.text()
    assert "sys-banner" not in rendered, "expected no banner for a never-ran pipeline with a healthy device"


def test_pipeline_never_ran_renders_neutral_in_french(tmp_path):
    """the same never-ran flight data card reads in French — 'Aucune détection
    pour l’instant.', zero dot--warn, zero French battery-fallback text"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    card = parse_html(rendered).select_one("#system-card-flight-data")
    assert card.select_one(".sys-card__label").text() == "Données de vol"
    assert "Aucune détection pour l’instant" in card.text(), "expected the French never-ran verdict text in the flight data card"
    card_html = rendered[rendered.index('id="system-card-flight-data"'):rendered.index('id="system-card-sources"')]
    assert "dot--warn" not in card_html, "expected zero dot--warn occurrences in a never-ran pipeline card under French"
    assert "aucune mesure pour l’instant" not in card_html, "expected zero French battery-fallback occurrences in a never-ran pipeline card"


def test_compute_health_state_carries_pipeline_detail_html_never_ran(tmp_path):
    """compute_health_state()'s pipeline_detail_html key, for a never-ran
    pipeline, is the bare PIPELINE_NEVER_RAN_DETAIL_TEXT sentence — no
    widget-verdict class, no PIPELINE_STATE_TEXT verdict text — and the same
    sentence is what the System view's flight data card shows"""
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
    rendered = health_page.system_html(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert detail_only in rendered, (
        "expected the flight data card to show the same verdict-free sentence Home reads")
