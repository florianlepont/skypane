"""Companion status-page tests: `health_page`'s freshness signals, `wake.py`'s
staleness thresholds, `layout.py`'s timestamps, and the battery section.

Every check calls `health_page`/`wake`/`layout` directly, in-process; missing
state_dir cases use a `tmp_path` subpath, writable even when running as root.
"""
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import companion.test_status_pages_helpers as shp
from companion import draw, layout, prefs
from companion.pages import health_page
import health_page_composition
import companion.wake as wake
from companion_markup import parse_html
from server import device_config, history_db
from skypane_test_support import REPO_ROOT, child_env

_DEFAULT_DEVICE_WARN_S, _DEFAULT_DEVICE_ERROR_S = wake.device_staleness_thresholds(None)


# ==========================================================================
# companion/pages/health_page.py: the two freshness signals
# ==========================================================================


def test_staleness_status_boundaries():
    """staleness_status() returns ok/warn/error at the right boundaries, warn for a
    never-seen signal"""
    warn_s, error_s = 100, 200
    assert health_page.staleness_status(50, warn_s, error_s) == "ok"
    assert health_page.staleness_status(warn_s, warn_s, error_s) == "warn"
    assert health_page.staleness_status(error_s, warn_s, error_s) == "error"
    assert health_page.staleness_status(None, warn_s, error_s) == "warn"


# ==========================================================================
# companion/wake.py
# ==========================================================================


def test_device_staleness_thresholds_floors_and_multipliers():
    """wake.device_staleness_thresholds() floors at (300, 1200), multiplies at a
    5-minute cadence, and falls back to the floors for None"""
    assert wake.device_staleness_thresholds(30) == (300, 1200)
    assert wake.device_staleness_thresholds(300) == (900, 3600)
    assert wake.device_staleness_thresholds(None) == (300, 1200)


def test_device_staleness_thresholds_warn_always_under_error():
    """wake.device_staleness_thresholds() guarantees warn_s < error_s for every input"""
    for candidate in (None, 1, 30, 60, 300, 3600):
        warn_s, error_s = wake.device_staleness_thresholds(candidate)
        assert warn_s < error_s, (
            "expected warn_s < error_s for wake_interval_s=%r, got (%r, %r)"
            % (candidate, warn_s, error_s))


def test_env_sleep_s_reads_unclamped_and_degrades(monkeypatch):
    """wake.env_sleep_s() reads SKYPANE_SLEEP_S unclamped (no [60, 3600] range check)
    and degrades to None for unset/empty/non-numeric/non-positive values"""
    monkeypatch.setenv(wake.SLEEP_ENV_VAR, "30")
    assert wake.env_sleep_s() == 30
    for bad in ("", "abc", "0"):
        monkeypatch.setenv(wake.SLEEP_ENV_VAR, bad)
        assert wake.env_sleep_s() is None, "expected env_sleep_s() to degrade to None for %r" % bad
    monkeypatch.delenv(wake.SLEEP_ENV_VAR, raising=False)
    assert wake.env_sleep_s() is None


def test_effective_wake_interval_s_precedence():
    """wake.effective_wake_interval_s() prefers the screen-off cadence, otherwise a
    configured wake_interval_s, and degrades to None for a missing config"""
    off_cfg = {"display_enabled": False, "wake_interval_s": 900}
    assert wake.effective_wake_interval_s(off_cfg) == device_config.DISPLAY_OFF_SLEEP_S
    on_cfg = {"display_enabled": True, "wake_interval_s": 120}
    assert wake.effective_wake_interval_s(on_cfg) == 120
    assert wake.effective_wake_interval_s(None) is None


def test_wake_module_never_imports_pages_or_app():
    """companion/wake.py's source never mentions the pages package or app.py"""
    # The observable consequence a source grep stood in for: importing
    # companion.wake in a fresh child interpreter must never pull
    # companion.pages or companion.app into sys.modules (an import cycle
    # for the latter, a layering violation for the former).
    script = (
        "import sys\n"
        "import companion.wake\n"
        "bad = sorted(m for m in sys.modules "
        "if m.startswith((\"companion.pages\", \"companion.app\")))\n"
        "print(bad)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT,
        env=child_env(dict(os.environ)), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "[]", (
        "expected companion.wake to import neither companion.pages nor companion.app, "
        "got %s" % result.stdout)


# ==========================================================================
# companion/layout.py: absolute_and_relative()
# ==========================================================================


def test_layout_absolute_and_relative_covers_every_documented_case():
    """layout.absolute_and_relative() covers every documented case: ordering,
    Z-suffix parsing, default/explicit fallback, unparseable-timestamp
    degradation, missing now_ts"""
    assert layout.absolute_and_relative(
        "2026-08-28T13:58:02+00:00", "2026-08-28T14:01:02+00:00") == (
        "2026-08-28T13:58:02+00:00 (3m ago)")
    assert layout.absolute_and_relative(
        "2026-08-28T13:58:02Z", "2026-08-28T13:58:32+00:00").endswith("(30s ago)")
    assert layout.absolute_and_relative(None, "2026-08-28T14:01:02+00:00") == "no reading yet"
    assert layout.absolute_and_relative(
        "", "2026-08-28T14:01:02+00:00", fallback="") == ""
    assert layout.absolute_and_relative(
        "not-a-date", "2026-08-28T14:01:02+00:00") == "not-a-date"
    assert layout.absolute_and_relative("2026-08-28T13:58:02+00:00", None) == (
        "2026-08-28T13:58:02+00:00")


def test_health_page_timestamp_helpers_promoted_not_duplicated(tmp_path):
    """health_page's private timestamp helpers are gone (a move, not a copy) and the
    Device row still renders the absolute-plus-relative format, now as a parenthesised
    <time data-relative> element"""
    for name in ("_parse_iso", "_age_seconds", "_relative_age_text"):
        assert not hasattr(health_page, name), (
            "health_page still defines %r — helpers were copied, not promoted" % name)
    now = shp.now()
    ts = shp.iso(now - timedelta(minutes=3))
    shp.seed_device_health(str(tmp_path), [(ts, 4200)])
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    # The title is now a full local timestamp, never the raw ISO — the
    # raw seeded ISO string must not survive verbatim on the page.
    assert ts not in rendered
    expected_title = layout.local_clock_text(
        layout.parse_iso(ts), layout._FULL_TIMESTAMP_SENTINEL_NOW)
    assert ('title="%s"' % layout.escape_html(expected_title)) in rendered
    assert re.search(r'\(<time datetime="[^"]*" data-relative>[^<]* ago</time>\)', rendered)


# ==========================================================================
# Battery section: empty state, ring, trend, disclosure, caption, day-1
# ==========================================================================


def test_battery_empty_state_no_sparkline(tmp_path):
    """zero battery rows render the good-news empty state and no sparkline"""
    rendered = health_page_composition.render(shp.ctx(str(tmp_path)))
    assert "No battery readings yet." in rendered
    doc = parse_html(rendered)
    assert not doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS), (
        "did not expect a sparkline trend-line segment with zero battery rows")


def _gauge_fraction(arc):
    """The fraction of the gauge's visible track a value arc draws, recovered
    from its own emitted radius, stroke and dash array (draw.arc_gauge()'s
    construction: the dash is shortened by one stroke for the round caps)."""
    radius = float(arc.attrs["r"])
    stroke = float(arc.attrs["stroke-width"])
    sweep = 2 * math.pi * radius * draw.ARC_SWEEP_DEGREES / 360.0
    return (float(arc.attrs["stroke-dasharray"].split()[0]) + stroke) / (sweep + stroke)


def test_battery_gauge_agrees_with_its_own_percentage(tmp_path):
    """Health's battery card draws exactly one gauge whose drawn fraction, recovered from its
    own emitted geometry, equals the percentage printed in its centre; the <h2> still carries
    no glyph, battery_sparkline_svg()'s own output carries no gauge class, and a device with no
    reading renders no gauge at all rather than an empty one"""
    with_reading = tmp_path / "with-reading"
    with_reading.mkdir()
    no_reading = tmp_path / "no-reading"
    no_reading.mkdir()
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    # 3690 mV lands on 32% of the discharge curve, deliberately not a round
    # fraction, so a gauge drawn from a plausible-but-wrong constant
    # (half/full/empty) cannot coincide with the right answer.
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 3600),
        (shp.iso(base - timedelta(minutes=1)), 3650),
        (shp.iso(base), 3690),
    ]
    shp.seed_device_health(str(with_reading), readings)
    rendered = health_page_composition.render(shp.ctx(str(with_reading), now_value=shp.iso(base)))
    doc = parse_html(rendered)

    tracks = doc.find_all("circle", cls=draw.DRAWING_ARC_TRACK_CLASS)
    values = doc.find_all("circle", cls=draw.DRAWING_ARC_VALUE_CLASS)
    assert len(tracks) == 1 and len(values) == 1, (
        "expected exactly one gauge on Health (one track, one value arc), got %d "
        "track(s) and %d value arc(s)" % (len(tracks), len(values)))
    drawn_fraction = _gauge_fraction(values[0])
    printed = doc.find("div", cls="battery-gauge__value").find("b").text()
    assert abs(drawn_fraction - int(printed) / 100.0) <= 0.0005, (
        "the gauge draws %.4f of its track while its centre prints %r" % (drawn_fraction, printed))
    assert drawn_fraction not in (0.0, 0.5, 1.0), (
        "the seeded reading lands on no round fraction, so %r means the gauge draws a constant"
        % (drawn_fraction,))
    assert len(doc.find_all("line", cls=draw.DRAWING_ARC_TICK_CLASS)) == 1, (
        "expected one low-battery tick on the gauge")
    # The level is stated once: the gauge carries the percentage, the voltage sits beside it.
    assert doc.find("span", cls="battery-volt").text().startswith("3690")

    for h2 in doc.find_all("h2"):
        assert not h2.find_all("svg"), "a Health <h2> carries an <svg>"

    chart = health_page.battery_sparkline_svg(
        [{"ts": ts, "battery_mv": mv} for ts, mv in reversed(readings)], now=shp.iso(base))
    for cls in (draw.DRAWING_ARC_TRACK_CLASS, draw.DRAWING_ARC_VALUE_CLASS):
        assert not parse_html(chart).find_all("circle", cls=cls), (
            "battery_sparkline_svg()'s own output carries %r: the gauge sits beside the chart" % (cls,))

    blank_doc = parse_html(health_page_composition.render(
        shp.ctx(str(no_reading), now_value=shp.iso(base))))
    for cls in (draw.DRAWING_ARC_TRACK_CLASS, draw.DRAWING_ARC_VALUE_CLASS):
        assert not blank_doc.find_all("circle", cls=cls), (
            "a device with no battery reading rendered %r: an empty gauge reads as 0%%" % (cls,))


def _voltage_view(doc):
    """The server-rendered default (voltage) chart view: the page also
    carries a hidden percentage twin of the same series."""
    return doc.find("div", cls="battery-chart__view", attrs={"data-unit": "mv"})


def test_battery_trend_shows_all_readings_and_one_sparkline(tmp_path):
    """three battery rows render the full trend (not just the latest value) and
    exactly one <svg> with exactly n - 1 trend-line segments (retargeted from the
    retired single-<polyline> marker)"""
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    for _ts, mv in readings:
        assert str(mv) in rendered, "expected battery_mv=%d to appear (a trend, not just the latest)" % mv
    doc = parse_html(rendered)
    canvases = _voltage_view(doc).find_all("svg", cls="sparkline__canvas")
    assert len(canvases) == 1, "expected exactly one sparkline canvas per view, got %d" % len(canvases)
    assert len(doc.find_all("svg", cls="sparkline__canvas")) == 2, (
        "expected the voltage view plus its percentage twin")
    lines = _voltage_view(doc).find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "expected exactly 2 trend-line segments (n - 1 for 3 points), got %d" % len(lines)


def test_battery_chart_ships_a_percentage_twin_calculated_by_the_server(tmp_path):
    """the page carries the percentage chart visibly (the default) and a hidden voltage twin; the
    percentage readings are the server's own battery estimate, and the Percentage/Voltage radio
    group is hidden until the script runs"""
    from companion import battery
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 3800),
        (shp.iso(base), 3600),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    doc = parse_html(health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base))))
    voltage = _voltage_view(doc)
    percent = doc.find("div", cls="battery-chart__view", attrs={"data-unit": "percent"})
    assert "hidden" in voltage.attrs and "hidden" not in percent.attrs
    group = doc.find("div", cls="battery-unit")
    assert "hidden" in group.attrs, "the control needs the script, so it ships hidden"
    assert group.attrs["role"] == "radiogroup"
    buttons = group.find_all("button")
    assert [b.attrs["data-unit"] for b in buttons] == ["percent", "mv"]
    assert [b.attrs["role"] for b in buttons] == ["radio", "radio"]
    assert [b.attrs["aria-checked"] for b in buttons] == ["true", "false"]
    assert [b.attrs["tabindex"] for b in buttons] == ["0", "-1"]
    hits = percent.find_all("circle", cls=health_page.SPARKLINE_HIT_CLASS)
    assert len(hits) == 3
    for hit in hits:
        expected = "≈ %d%%" % battery.battery_percent(int(hit.attrs["data-mv"]))
        assert hit.attrs["data-reading"] == expected
    assert not percent.find_all(attrs={"data-reading": "≈ 0%"})


def test_battery_unit_control_is_localised(tmp_path):
    """the Percentage/Voltage control and its group label render in French on a French request"""
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    shp.seed_device_health(str(tmp_path), [
        (shp.iso(base - timedelta(minutes=1)), 3900), (shp.iso(base), 3800)])
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    finally:
        prefs.set_request_prefs(lang="en")
    assert ">Pourcentage</button>" in rendered and ">Tension</button>" in rendered
    assert 'aria-label="Unité du graphique de batterie"' in rendered


def test_battery_trend_timestamps_show_concise_format(tmp_path):
    """Battery Trend's Timestamp column shows the concise format (full ISO
    demoted to title), matching the Device/pipeline rows, and _battery_section()
    stays single-argument"""
    # _battery_section() must stay callable with exactly one positional
    # argument, matching the real call site inside render() — proven by
    # calling it with just one argument, not by inspecting its signature.
    health_page._battery_section([])
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    for ts, _mv in readings:
        expected_span = layout.concise_timestamp_html(ts, shp.iso(base))
        assert rendered.count(expected_span) >= 1, (
            "expected concise_timestamp_html()'s own byte-identical span for %r "
            "in the rendered Battery Trend table" % ts)
    assert " ago)" in rendered


def test_battery_trend_ages_read_against_the_page_now_not_the_wall_clock(tmp_path, monkeypatch):
    """the readings table's ages come from the render's own `now`: a wall clock
    a minute ahead of it (a stalled runner) must not change any rendered age"""
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    monkeypatch.setattr(
        history_db, "utc_now_iso", lambda: shp.iso(base + timedelta(seconds=61)))
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    for ts, _mv in readings:
        assert layout.concise_timestamp_html(ts, shp.iso(base)) in rendered


def test_battery_readings_are_shown_open_after_chart(tmp_path):
    """the readings table is shown open under its heading, and
    the chart precedes it"""
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    assert '<section class="battery-readings"' in rendered
    assert "readings-disclosure" not in rendered, "expected the readings to be shown, not folded"
    assert "Readings (3)" in rendered, "expected the heading to name the real plotted-row count"
    svg_index = rendered.index("<svg")
    section_index = rendered.index('<section class="battery-readings"')
    assert svg_index < section_index, "expected the chart to precede the readings table"


def test_battery_trend_heading_names_only_the_subject(tmp_path):
    """the Battery row is named by its bare subject, carries no window label, and the
    retired "Last 3 months" range caption does not render on an empty render"""
    rendered = health_page_composition.render(shp.ctx(str(tmp_path)))
    name = shp.health_row(rendered, "battery").select_one(".health-row__name")
    assert name.text() == "Battery"
    assert "3 months" not in rendered
    assert "Last 3 months" not in rendered


def test_battery_chart_plots_daily_averages_not_raw_readings(tmp_path):
    """a multi-day seeded render plots the three DAILY AVERAGES (never any raw
    reading value) as points, keeps every raw reading visible in the disclosure
    table, with no range caption"""
    base = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    readings = []
    day_values = [[4000, 4100, 4200], [4001, 4101, 4201], [4002, 4102, 4202]]
    for day, values in enumerate(day_values):
        for hour, mv in zip((2, 10, 18), values):
            ts = shp.iso((base - timedelta(days=day)).replace(hour=hour))
            readings.append((ts, mv))
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    doc = parse_html(rendered)
    for expected_mean in ("4100", "4101", "4102"):
        assert doc.find_all(attrs={"data-mv": expected_mean}), (
            "expected the daily average %s to appear as a plotted point's data-mv" % expected_mean)
    for raw in (4000, 4001, 4002, 4200, 4201, 4202):
        assert not doc.find_all(attrs={"data-mv": str(raw)}), (
            "raw reading %d must not be a plotted point once the chart is aggregated" % raw)
    lines = _voltage_view(doc).find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "three daily points means two trend-line segments, got %d" % len(lines)
    for _ts, mv in readings:
        assert str(mv) in rendered, "raw reading %d missing from the disclosure table" % mv
    assert doc.find("span", cls="battery-chart__caption").text() == "Last 90 daysDaily averages"
    assert health_page.BATTERY_READOUT_ID in rendered, "the latest computed reading must still be on the page"


def test_battery_chart_falls_back_to_raw_series_on_day_one(tmp_path):
    """a same-day (fewer than two calendar days) seeded render still produces a
    chart and a readout, with the disclosure naming the real reading count and no
    range caption — the day-1 regression guard"""
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    doc = parse_html(rendered)
    lines = _voltage_view(doc).find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "a same-day device must still get its raw-readings chart, got %d segments" % len(lines)
    assert health_page.BATTERY_READOUT_ID in rendered, (
        "the readout must not disappear on a device younger than two calendar days")
    assert ("Readings (%d)" % len(readings)) in rendered, (
        "the readings disclosure must name the real reading count")
    assert doc.find("span", cls="battery-chart__caption").text() == "Latest %d readings" % len(readings), (
        "the caption must name the series the chart is actually showing")
    assert "Last 3 months" not in rendered


# ==========================================================================
# The nav-tab severity path's root-unsafe degrade-safely check
# ==========================================================================


def _anomaly_active(state_dir, now=None):
    # The live nav-tab severity path app.py's page_context() calls
    # (health_page.safe_health_state()), reduced to a single "is there an
    # anomaly" bool.
    state = health_page.safe_health_state(state_dir, now)
    severity = state["severity"] if state else "ok"
    return severity != "ok"


def test_anomaly_active_never_raises_on_hostile_inputs(tmp_path):
    """the nav-tab severity path runs on every page render and must never raise —
    missing/empty/file/corrupt-db inputs all degrade safely"""
    # The severity path runs on every page render (page_context() in
    # companion/app.py), so it may never raise. Missing/empty/corrupt-db
    # state_dir inputs all reach the same tmp_path-backed code path —
    # tmp_path stays writable even when the test process runs as root,
    # unlike a fixed host path outside the repo.
    for candidate in (tmp_path / "absent" / "nested", tmp_path / "empty"):
        candidate_str = str(candidate)
        verdict = _anomaly_active(candidate_str)
        assert isinstance(verdict, bool), (
            "expected a bool (no raise) for %r, got %r" % (candidate_str, verdict))
        assert health_page_composition.render(shp.ctx(candidate_str))

    # A database file that exists but is not a valid SQLite file: every
    # read maps to _DB_UNAVAILABLE, which every section builder treats
    # as "ok" — collect_anomalies() must return False, not raise.
    corrupt_db_dir = tmp_path / "empty"
    dbs = [p for p in corrupt_db_dir.iterdir() if p.suffix == ".db"]
    assert dbs, "expected a database file to have been created by the loop above"
    dbs[0].write_bytes(b"not a sqlite file at all")
    assert _anomaly_active(str(corrupt_db_dir)) is False, (
        "expected False for a corrupt database, not a raise")

    # A state_dir path that is a regular file, not a directory:
    # os.makedirs(..., exist_ok=True) raises FileExistsError against an
    # existing non-directory path regardless of who runs the process.
    regular_file = tmp_path / "not-a-directory"
    regular_file.write_bytes(b"")
    assert _anomaly_active(str(regular_file)) is False, (
        "expected False for a state_dir that is a regular file, not a directory")


def test_battery_caption_is_mode_honest_across_renders(tmp_path):
    """the Battery chart's caption is honest in each of three modes: absent when empty, the daily
    average when several days are on screen, and the real reading count on the same-day fallback"""
    empty_dir = tmp_path / "empty"
    multiday_dir = tmp_path / "multiday"
    sameday_dir = tmp_path / "sameday"
    for d in (empty_dir, multiday_dir, sameday_dir):
        d.mkdir()
    base = shp.now()

    empty_rendered = health_page_composition.render(shp.ctx(str(empty_dir), now_value=shp.iso(base)))
    assert "battery-chart__caption" not in empty_rendered, "expected no chart caption on an empty render"

    multiday_readings = [
        (shp.iso(base - timedelta(days=1)), 4100),
        (shp.iso(base - timedelta(days=2)), 4200),
    ]
    shp.seed_device_health(str(multiday_dir), multiday_readings)
    multiday_rendered = health_page_composition.render(shp.ctx(str(multiday_dir), now_value=shp.iso(base)))
    assert "Last 90 days" in multiday_rendered and "Daily averages" in multiday_rendered, "expected the daily-average caption"

    sameday_readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(str(sameday_dir), sameday_readings)
    sameday_rendered = health_page_composition.render(shp.ctx(str(sameday_dir), now_value=shp.iso(base)))
    assert ("Latest %d readings" % len(sameday_readings)) in sameday_rendered
    assert ("Readings (%d)" % len(sameday_readings)) in sameday_rendered, (
        "expected the readings disclosure to name the real count on the same-day fallback")
    assert "Last 3 months" not in sameday_rendered, (
        "the same-day fallback must not claim the 3-month framing")


# ==========================================================================
# The anomaly banner's category naming / pill markup
# ==========================================================================


def test_anomaly_category_labels_are_pill_text_not_full_sentences():
    """_anomaly_category_labels() returns one period-stripped label per anomaly,
    distinct from collect_anomalies()'s own full literal sentences"""
    anomalies = health_page.collect_anomalies(
        device_state="error", pipeline_state="error",
        battery_state="ok", disagreement_warn=False)
    labels = health_page._anomaly_category_labels(anomalies)
    assert len(labels) == len(anomalies), (
        "expected one label per anomaly, got %d labels for %d anomalies" % (len(labels), len(anomalies)))
    for label, anomaly in zip(labels, anomalies):
        assert label != anomaly, (
            "expected a pill label to differ from collect_anomalies()'s full literal sentence, got %r" % (label,))
        assert not label.endswith("."), "expected a pill label's trailing period to be stripped, got %r" % (label,)


# ==========================================================================
# Corroboration's compact rows + closed-by-default explanations
# ==========================================================================


def test_sources_row_disagreement_flag_unchanged():
    """the disagreement flag the Sources row keys its state on is unchanged"""
    assert health_page._disagreement_warn({"True": 1, "None": 0, "False": 2}) is True, (
        "expected the disagreement flag to be True when the False bucket is non-zero")
    assert health_page._disagreement_warn({"True": 1, "None": 2, "False": 0}) is False, (
        "expected the disagreement flag to be False when the False bucket is zero")


def test_corroboration_copy_has_no_decision_id_leak():
    """no corroboration row's explanation leaks a bare decision-ID parenthetical"""
    for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
        assert "(D-" not in explanation, (
            "found a decision-ID leak in a corroboration row's explanation: %r" % explanation)


# ==========================================================================
# Concise timestamps, and the stale-view-banner reversal
# ==========================================================================


def test_health_pill_reversal_guard(tmp_path):
    """Health's manual Refresh link and stale-view banner stay retired, and its freshness
    line (and the data-loaded-at marker it carried) is gone too; page_header() is called
    exactly once"""
    # Pins the reversal's own rendered result and positively asserts both
    # retired literals are truly gone, so a later refactor cannot silently
    # bring them back.
    now_iso = shp.iso(shp.now())
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=now_iso))
    assert "data-loaded-at" not in rendered, "expected the retired freshness line to be gone"
    assert "page-header__freshness" not in rendered
    assert rendered.count('<h1 class="page-title"') == 1, "expected page_header() to be called exactly once"
    assert "data-stale-banner" not in rendered, (
        "expected the retired stale-view banner marker to be gone from the rendered page")
    assert "may be out of date" not in rendered, (
        "expected the retired stale-view banner's copy to be gone from the rendered page")
    assert "freshness-refresh" not in rendered, (
        "expected the retired manual Refresh link's class to be gone from the rendered page")
    assert not hasattr(health_page, "_STALE_VIEW_BANNER_HTML"), (
        "expected health_page to no longer define the retired _STALE_VIEW_BANNER_HTML constant")


# ==========================================================================
# The badge-to-card-border retargets
# ==========================================================================


def test_battery_row_healthy_on_a_normal_trend(tmp_path):
    """the Battery row reads healthy (and stays closed) on a normal trend"""
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4190),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert shp.health_row_state(rendered, "battery") == "ok"
    assert rendered.count("dot--ok") == 0 and "dot--warn" not in rendered and "dot--error" not in rendered, (
        "expected zero dot classes of any colour in this fixture")
    wrapper = shp.health_row(rendered, "battery").select_one("." + health_page.BATTERY_SECTION_CLASS)
    assert "battery-trend-section--embedded" in wrapper.attrs["class"].split(), (
        "the chart's wrapper must be the card-less embedded variant inside a row")


def test_battery_empty_history_is_neutral_with_no_anomaly_banner(tmp_path):
    """an empty/single-reading battery trend renders a neutral or ok row and no anomaly
    banner (Assumption A1 regression guard)"""
    # The empty-history branch must stay "ok", or a freshly-provisioned
    # device with zero readings would display "A battery reading shows an
    # abnormal drop." — factually wrong copy.
    markup, state = health_page._battery_section([])
    assert state == "ok", "expected _battery_section([]) to return state 'ok', got %r" % (state,)
    assert "No battery readings yet." in markup, "expected the empty-history empty-state heading in the markup"
    assert "dot--error" not in markup and "dot--warn" not in markup and "dot--ok" not in markup, (
        "did not expect any status-dot class in the empty-history markup — the badge is retired")

    # No history at all: a neutral row, never a verdict about a drop.
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty = health_page_composition.render(shp.ctx(str(empty_dir)))
    assert shp.health_row_state(empty, "battery") == "off"
    assert "Battery dropped abnormally." not in empty

    # Page-level proof: a fresh device with one healthy battery reading
    # never surfaces the abnormal-drop anomaly or its banner.
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.iso(now), 4200)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert "dot--error" not in rendered, "did not expect an error status class with a single battery reading"
    assert shp.health_row_state(rendered, "battery") == "ok", (
        "expected the Battery row to read healthy with a single, healthy battery reading")
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, (
        "did not expect the anomaly banner with a single, healthy battery reading")
    assert "Battery dropped abnormally." not in rendered, (
        "did not expect the abnormal-drop copy with a single battery reading")


def test_battery_drop_drives_the_row_and_detail_copy_not_rendered(tmp_path):
    """a real battery drop drives the Battery row's warn state; the detail copy is not
    rendered"""
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page_composition.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert shp.health_row_state(rendered, "battery") == "warn", (
        "expected the Battery row to read warn for a drop >= "
        "BATTERY_DROP_WARN_MV (demoted from error, D-05)")
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, "the Battery page carries no banner"
    assert "Battery dropped abnormally." not in rendered, (
        "the abnormal-drop detail copy must no longer be rendered on the page")
    assert health_page.collect_anomalies("ok", "ok", "error", False) == ["Battery dropped abnormally."], (
        "collect_anomalies() must still compute the abnormal-drop item directly")


# ==========================================================================
# The retired anomaly-detail-list markup
# ==========================================================================


# ==========================================================================
# battery_sparkline_svg(): external-reference ban and per-point hit targets
# ==========================================================================


def test_sparkline_has_no_external_reference():
    """battery_sparkline_svg() emits no url(, <image, or <script — no external
    reference at all"""
    # This check's scope is narrower than it first appears — it exercises
    # only battery_sparkline_svg()'s own return value, which never gains
    # a script/url/image reference no matter how much interactive markup
    # a point carries.
    rows = [
        {"ts": "t1", "battery_mv": 4200},
        {"ts": "t2", "battery_mv": 4100},
        {"ts": "t3", "battery_mv": 4050},
    ]
    svg = health_page.battery_sparkline_svg(rows)
    for forbidden in ("url(", "<image", "<script"):
        assert forbidden not in svg, "found forbidden %r in the sparkline SVG" % forbidden


def test_sparkline_svg_has_per_point_interactive_markup():
    """battery_sparkline_svg() emits per-point interactive hit targets with
    data-mv/data-ts/<title>, in chronological order, with roving tabindex on the
    latest point only"""
    rows = [
        {"ts": "2024-01-03T00:00:00", "battery_mv": 4050},
        {"ts": "2024-01-02T00:00:00", "battery_mv": 4100},
        {"ts": "2024-01-01T00:00:00", "battery_mv": 4200},
    ]
    svg = health_page.battery_sparkline_svg(rows)
    doc = parse_html(svg)

    hits = doc.find_all("circle", cls=health_page.SPARKLINE_HIT_CLASS)
    assert len(hits) == 3, "expected exactly 3 hit-target circles, got %d" % len(hits)

    marks = doc.find_all("circle", cls=health_page.SPARKLINE_MARK_CLASS)
    assert len(marks) == 1, "expected one marker, on the newest point, got %d" % len(marks)

    assert sum(1 for h in hits if "data-mv" in h.attrs) == 3, "expected exactly 3 data-mv attributes"
    assert sum(1 for h in hits if "data-ts" in h.attrs) == 3, "expected exactly 3 data-ts attributes"
    assert len(doc.find_all("title")) == 3, "expected exactly 3 <title elements"

    # Roving tabindex: exactly one hit target is a normal Tab stop (the
    # chronologically-latest point), the rest are removed from the
    # natural Tab order.
    tabindex_0 = [h for h in hits if h.attrs.get("tabindex") == "0"]
    tabindex_neg1 = [h for h in hits if h.attrs.get("tabindex") == "-1"]
    assert len(tabindex_0) == 1, (
        "expected exactly 1 tabindex=\"0\" hit target (roving tabindex), got %d" % len(tabindex_0))
    assert len(tabindex_neg1) == 2, "expected exactly 2 tabindex=\"-1\" hit targets, got %d" % len(tabindex_neg1)

    lines = doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "expected exactly 2 trend-line segments (n - 1 for 3 points), got %d" % len(lines)

    for row in rows:
        mv = row["battery_mv"]
        assert any(h.attrs.get("data-mv") == str(mv) for h in hits), (
            "expected battery_mv=%d to appear inside a data-mv attribute" % mv)

    ordered_ts = ["2024-01-01T00:00:00", "2024-01-02T00:00:00", "2024-01-03T00:00:00"]
    assert [h.attrs.get("data-ts") for h in hits] == ordered_ts, (
        "expected timestamps in chronological (oldest-first) document order, matching the "
        "trend line's own left-to-right ordering")

    by_ts = {h.attrs.get("data-ts"): h for h in hits}
    assert by_ts[ordered_ts[-1]].attrs.get("tabindex") == "0", (
        "expected the chronologically-latest point's hit target to carry tabindex=\"0\"")
