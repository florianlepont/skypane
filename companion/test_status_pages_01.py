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
from companion import draw, layout
from companion.pages import health_page
import companion.wake as wake
from companion_markup import parse_html
from server import device_config, history_db
from skypane_test_support import REPO_ROOT, child_env

_DEFAULT_DEVICE_WARN_S, _DEFAULT_DEVICE_ERROR_S = wake.device_staleness_thresholds(None)


# ==========================================================================
# companion/pages/health_page.py: the two freshness signals
# ==========================================================================


def test_render_shows_two_distinct_freshness_labels(tmp_path):
    """render() shows two distinct, separately-labelled freshness signals"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert health_page.DEVICE_FRESHNESS_LABEL in rendered
    assert health_page.PIPELINE_FRESHNESS_LABEL in rendered
    assert health_page.DEVICE_FRESHNESS_LABEL != health_page.PIPELINE_FRESHNESS_LABEL


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
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    # The title is now a full local timestamp, never the raw ISO — the
    # raw seeded ISO string must not survive verbatim on the page.
    assert ts not in rendered
    expected_title = layout.local_clock_text(
        layout.parse_iso(ts), layout._FULL_TIMESTAMP_SENTINEL_NOW)
    assert ('title="%s"' % layout.escape_html(expected_title)) in rendered
    assert re.search(r'\(<time datetime="[^"]*" data-relative>[^<]* ago</time>\)', rendered)


def test_independent_thresholds_one_warn_one_ok(tmp_path):
    """a stale device and a fresh pipeline read as independent per-tile modifiers
    (error vs ok) on their own wrappers, not a blended verdict, with only the dots
    that legitimately remain still healthy"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.ago(_DEFAULT_DEVICE_ERROR_S + 60), 4000)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))

    device_at = rendered.index(health_page.DEVICE_FRESHNESS_LABEL)
    device_tile_open = rendered.rindex('<div class="stat-tile ', 0, device_at)
    device_tile_tag = rendered[device_tile_open:rendered.index(">", device_tile_open)]
    assert "stat-tile--error" in device_tile_tag, (
        "expected the Device tile's wrapper to carry the error modifier, got %r"
        % device_tile_tag)

    pipeline_at = rendered.index(health_page.PIPELINE_FRESHNESS_LABEL)
    pipeline_tile_open = rendered.rindex('<div class="stat-tile ', 0, pipeline_at)
    pipeline_tile_tag = rendered[pipeline_tile_open:rendered.index(">", pipeline_tile_open)]
    assert "stat-tile--ok" in pipeline_tile_tag, (
        "expected the Pipeline tile's wrapper to carry the ok modifier, got %r"
        % pipeline_tile_tag)

    assert rendered.count("dot--ok") == 0
    assert "dot--warn" not in rendered
    assert "dot--error" not in rendered


def test_device_pipeline_tiles_have_no_duplicated_label(tmp_path):
    """the Device and Pipeline tiles carry their freshness label exactly once
    (caption only) plus exactly one Emphasis-role verdict and exactly one muted
    detail slot holding the mono timestamp, with zero stat-tile__value and no
    leftover dot-label"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.iso(now), 4200)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    tiles = shp.stat_tile_slices(rendered)
    for label in (health_page.DEVICE_FRESHNESS_LABEL, health_page.PIPELINE_FRESHNESS_LABEL):
        assert rendered.count(label) == 1, (
            "%r must appear exactly once on the whole rendered page" % label)
        matching = [tile for tile in tiles if label in tile]
        assert len(matching) == 1, (
            "expected exactly one .stat-tile carrying %r, got %d" % (label, len(matching)))
        tile_slice = matching[0]
        assert tile_slice.count('class="%s"' % health_page._TILE_VERDICT_CLASS) == 1, (
            "%r's tile must carry exactly one Emphasis-role verdict element" % label)
        assert tile_slice.count('class="stat-tile__value"') == 0, (
            "%r's tile must carry no stat-tile__value paragraph" % label)
        details = tile_slice.count('class="%s"' % health_page._TILE_DETAIL_CLASS)
        assert details == 1, "%r's tile must carry exactly one detail slot, got %d" % (label, details)
        detail_at = tile_slice.index('class="%s"' % health_page._TILE_DETAIL_CLASS)
        assert 'class="mono"' in tile_slice[detail_at:], (
            "%r's tile must carry its mono timestamp span INSIDE the detail slot" % label)
        assert "dot-label" not in tile_slice, (
            "%r's tile must carry no dot-label — the redundant body dot was removed" % label)


# ==========================================================================
# Battery section: empty state, ring, trend, disclosure, caption, day-1
# ==========================================================================


def test_battery_empty_state_no_sparkline(tmp_path):
    """zero battery rows render the good-news empty state and no sparkline"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert "No battery readings yet." in rendered
    doc = parse_html(rendered)
    assert not doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS), (
        "did not expect a sparkline trend-line segment with zero battery rows")
    assert not doc.find_all("circle", cls=health_page.SPARKLINE_DOT_CLASS), (
        "did not expect a sparkline dot with zero battery rows")


def test_battery_ring_agrees_with_its_own_readout(tmp_path):
    """Health's battery section draws exactly one ring whose drawn fraction —
    recovered from its own emitted radius and dash array — equals the percentage
    the readout beside it PRINTS; the <h2> still carries no glyph,
    battery_sparkline_svg()'s own output carries no ring class, and a device with
    no reading renders no ring at all rather than an empty one"""
    with_reading = tmp_path / "with-reading"
    with_reading.mkdir()
    no_reading = tmp_path / "no-reading"
    no_reading.mkdir()
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    # 3690 mV lands on 32% of the discharge curve, deliberately not a round
    # fraction, so a ring drawn from a plausible-but-wrong constant
    # (half/full/empty) cannot coincide with the right answer.
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 3600),
        (shp.iso(base - timedelta(minutes=1)), 3650),
        (shp.iso(base), 3690),
    ]
    shp.seed_device_health(str(with_reading), readings)
    rendered = health_page.render(shp.ctx(str(with_reading), now_value=shp.iso(base)))
    doc = parse_html(rendered)

    tracks = doc.find_all("circle", cls=draw.DRAWING_RING_TRACK_CLASS)
    values = doc.find_all("circle", cls=draw.DRAWING_RING_VALUE_CLASS)
    assert len(tracks) == 1 and len(values) == 1, (
        "expected exactly one ring on Health (one track, one value arc), got %d "
        "track(s) and %d value arc(s)" % (len(tracks), len(values)))

    radius = float(values[0].attrs["r"])
    dash_attr = values[0].attrs.get("stroke-dasharray")
    circumference = 2 * math.pi * radius
    drawn = float(dash_attr.split()[0]) if dash_attr else circumference
    drawn_fraction = drawn / circumference

    readout = doc.find("span", cls="battery-readout__value")
    printed = re.search(r"(\d+)%", readout.text())
    assert printed is not None, "expected the readout to print a percentage"
    printed_fraction = int(printed.group(1)) / 100.0
    assert abs(drawn_fraction - printed_fraction) <= 0.0005, (
        "the ring draws %.4f of its circumference while the readout beside it "
        "prints %r — the picture and the number disagree (CFG-40)"
        % (drawn_fraction, readout.text()))
    assert drawn_fraction not in (0.0, 0.5, 1.0), (
        "the seeded reading was chosen to land on no round fraction, so %r means "
        "the ring is drawing a constant rather than the reading" % (drawn_fraction,))

    for h2 in doc.find_all("h2"):
        assert not h2.find_all("svg"), (
            "a Health <h2> carries an <svg> — the battery heading's glyph must "
            "not come back")

    chart = health_page.battery_sparkline_svg(
        [{"ts": ts, "battery_mv": mv} for ts, mv in reversed(readings)],
        now=shp.iso(base))
    chart_doc = parse_html(chart)
    for cls in (draw.DRAWING_RING_TRACK_CLASS, draw.DRAWING_RING_VALUE_CLASS):
        assert not chart_doc.find_all("circle", cls=cls), (
            "battery_sparkline_svg()'s own output carries %r — this feature adds "
            "a ring BESIDE the chart, not inside it" % (cls,))

    blank_rendered = health_page.render(shp.ctx(str(no_reading), now_value=shp.iso(base)))
    blank_doc = parse_html(blank_rendered)
    for cls in (draw.DRAWING_RING_TRACK_CLASS, draw.DRAWING_RING_VALUE_CLASS):
        assert not blank_doc.find_all("circle", cls=cls), (
            "a device with no battery reading rendered %r — an empty ring reads "
            "as 0%%, a false statement about a device that has simply not "
            "checked in" % (cls,))


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
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    for _ts, mv in readings:
        assert str(mv) in rendered, "expected battery_mv=%d to appear (a trend, not just the latest)" % mv
    doc = parse_html(rendered)
    canvases = doc.find_all("svg", cls="sparkline__canvas")
    assert len(canvases) == 1, "expected exactly one sparkline canvas, got %d" % len(canvases)
    lines = doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "expected exactly 2 trend-line segments (n - 1 for 3 points), got %d" % len(lines)


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
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    for ts, _mv in readings:
        expected_span = layout.concise_timestamp_html(ts, shp.iso(base))
        assert rendered.count(expected_span) >= 1, (
            "expected concise_timestamp_html()'s own byte-identical span for %r "
            "in the rendered Battery Trend table" % ts)
    assert " ago)" in rendered


def test_battery_readings_collapsed_behind_closed_disclosure_after_chart(tmp_path):
    """the readings table is collapsed behind a closed-by-default disclosure, and
    the chart precedes it"""
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    assert '<details class="readings-disclosure"' in rendered
    details_tag = rendered[rendered.index('<details class="readings-disclosure"'):]
    details_open_tag = details_tag[:details_tag.index(">") + 1]
    assert " open" not in details_open_tag, "expected the readings disclosure to be closed by default"
    assert "View 3 readings" in rendered, "expected the disclosure summary to name the real plotted-row count"
    svg_index = rendered.index("<svg")
    details_index = rendered.index('<details class="readings-disclosure"')
    assert svg_index < details_index, "expected the chart to precede the collapsed readings table"


def test_battery_trend_heading_shows_d10_window_label(tmp_path):
    """the Battery trend heading shows the default 3-month window framing on an
    empty render"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert "Last 3 months" in rendered


def test_battery_chart_plots_daily_averages_not_raw_readings(tmp_path):
    """a multi-day seeded render plots the three DAILY AVERAGES (never any raw
    reading value) as points, keeps every raw reading visible in the disclosure
    table, and names the 3-month window"""
    base = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    readings = []
    day_values = [[4000, 4100, 4200], [4001, 4101, 4201], [4002, 4102, 4202]]
    for day, values in enumerate(day_values):
        for hour, mv in zip((2, 10, 18), values):
            ts = shp.iso((base - timedelta(days=day)).replace(hour=hour))
            readings.append((ts, mv))
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    doc = parse_html(rendered)
    for expected_mean in ("4100", "4101", "4102"):
        assert doc.find_all(attrs={"data-mv": expected_mean}), (
            "expected the daily average %s to appear as a plotted point's data-mv" % expected_mean)
    for raw in (4000, 4001, 4002, 4200, 4201, 4202):
        assert not doc.find_all(attrs={"data-mv": str(raw)}), (
            "raw reading %d must not be a plotted point once the chart is aggregated" % raw)
    lines = doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "three daily points means two trend-line segments, got %d" % len(lines)
    for _ts, mv in readings:
        assert str(mv) in rendered, "raw reading %d missing from the disclosure table" % mv
    assert "Last 3 months" in rendered, "expected the 3-month caption when the daily series is on screen"
    assert health_page.BATTERY_READOUT_ID in rendered, "the latest computed reading must still be on the page"


def test_battery_chart_falls_back_to_raw_series_on_day_one(tmp_path):
    """a same-day (fewer than two calendar days) seeded render still produces a
    chart and a readout, captioned honestly as readings rather than the 3-month
    window — the day-1 regression guard"""
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(base)))
    doc = parse_html(rendered)
    lines = doc.find_all("line", cls=health_page.SPARKLINE_LINE_CLASS)
    assert len(lines) == 2, "a same-day device must still get its raw-readings chart, got %d segments" % len(lines)
    assert health_page.BATTERY_READOUT_ID in rendered, (
        "the readout must not disappear on a device younger than two calendar days")
    assert ("Latest %d readings" % len(readings)) in rendered
    assert "Last 3 months" not in rendered, (
        "the caption must never describe a window the chart is not actually showing")


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
        rendered = health_page.render(shp.ctx(candidate_str))
        assert verdict == (health_page.ANOMALY_BANNER_TEXT in rendered), (
            "the severity path disagreed with render()'s banner for %r" % candidate_str)

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
    """the Battery trend caption is mode-honest across three renders — empty
    (3-month default), multi-day (3-month, daily average), and same-day (readings
    count)"""
    empty_dir = tmp_path / "empty"
    multiday_dir = tmp_path / "multiday"
    sameday_dir = tmp_path / "sameday"
    for d in (empty_dir, multiday_dir, sameday_dir):
        d.mkdir()
    base = shp.now()

    empty_rendered = health_page.render(shp.ctx(str(empty_dir), now_value=shp.iso(base)))
    assert "Last 3 months" in empty_rendered, "expected the default 3-month framing on an empty render"

    multiday_readings = [
        (shp.iso(base - timedelta(days=1)), 4100),
        (shp.iso(base - timedelta(days=2)), 4200),
    ]
    shp.seed_device_health(str(multiday_dir), multiday_readings)
    multiday_rendered = health_page.render(shp.ctx(str(multiday_dir), now_value=shp.iso(base)))
    assert "Last 3 months" in multiday_rendered, "expected the 3-month framing when the daily series is on screen"

    sameday_readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(str(sameday_dir), sameday_readings)
    sameday_rendered = health_page.render(shp.ctx(str(sameday_dir), now_value=shp.iso(base)))
    assert ("Latest %d readings" % len(sameday_readings)) in sameday_rendered, (
        "expected the readings-count framing on the same-day fallback")
    assert "Last 3 months" not in sameday_rendered, (
        "the same-day fallback must not claim the 3-month framing")


# ==========================================================================
# The anomaly banner's category naming / pill markup
# ==========================================================================


def test_anomaly_banner_names_real_categories_not_generic_only(tmp_path):
    """the anomaly banner names the real failing category (a disagreement), not
    only the generic fallback text"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.iso(now), 4200)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(str(tmp_path), [
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": False}])
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert "Data sources disagreed" in rendered, "expected the anomaly banner to name the real failing category"
    assert health_page.ANOMALY_BANNER_TEXT in rendered, (
        "expected ANOMALY_BANNER_TEXT to remain present as the banner's fallback tail")
    assert 'class="banner__pill"' in rendered, (
        "expected the anomaly banner to render banner__pill markup for the pill-based category naming")


def test_anomaly_categories_never_lowercase_a_leading_acronym():
    """_anomaly_category_text() lower-cases ordinary mid-sentence phrases but never
    a leading acronym (no 'aDS-B')"""
    # Driven through the real collect_anomalies() strings, in the real
    # order, rather than hand-written fixtures, so the check cannot drift
    # away from the copy it is protecting; a hand-written acronym-led
    # fixture below keeps the guard itself under test.
    anomalies = health_page.collect_anomalies(
        device_state="warn", pipeline_state="warn",
        battery_state="ok", disagreement_warn=True)
    text = health_page._anomaly_category_text(anomalies)
    assert "flight data is stale" in text and "data sources disagreed" in text, (
        "expected the real non-first phrases to be lower-cased mid-sentence, got %r" % (text,))

    acronym = health_page._anomaly_category_text(
        ["Device check-in is stale.",
         "ADS-B sources disagreed on the selected aircraft recently."])
    assert "aDS-B" not in acronym and "ADS-B sources" in acronym, (
        "a leading acronym was lower-cased for mid-sentence joining, producing %r" % (acronym,))

    # The guard must be narrow: an ordinary sentence-initial word in a
    # non-first position still lower-cases, or the joined clause reads
    # as a run of sentences again.
    ordinary = health_page._anomaly_category_text(
        ["Device check-in is stale.",
         "Battery dropped abnormally."])
    assert "battery dropped abnormally" in ordinary, (
        "expected an ordinary non-acronym phrase to still be lower-cased mid-sentence, got %r" % (ordinary,))


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


def test_anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping():
    """_anomaly_banner_html() reproduces layout.anomaly_banner()'s exact
    severity-to-class/role mapping, and carries one banner__pill per anomaly plus
    the accessible ANOMALY_BANNER_TEXT tail"""
    anomalies = ["Device check-in is stale."]
    error_banner = health_page._anomaly_banner_html("error", anomalies)
    assert 'class="banner banner--anomaly"' in error_banner and 'role="alert"' in error_banner, (
        "expected error severity to render banner--anomaly + role=\"alert\"")
    warn_banner = health_page._anomaly_banner_html("warn", anomalies)
    assert 'class="banner banner--warn"' in warn_banner and 'role="status"' in warn_banner, (
        "expected warn severity to render banner--warn + role=\"status\"")
    assert warn_banner.count('class="banner__pill"') == 1, (
        "expected exactly one banner__pill for a single-anomaly fixture")
    assert health_page.ANOMALY_BANNER_TEXT in warn_banner, (
        "expected ANOMALY_BANNER_TEXT to remain present as the banner's accessible tail")


def test_anomaly_banner_renders_one_pill_per_anomaly_on_the_page(tmp_path):
    """a two-anomaly fixture renders exactly two banner__pill elements inside one
    banner element on the real page"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.ago(_DEFAULT_DEVICE_ERROR_S + 60), 4000)])
    shp.seed_meta(str(tmp_path), **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert rendered.count('<div class="banner ') == 1, "expected exactly one banner element"
    assert rendered.count('class="banner__pill"') == 2, (
        "expected exactly two banner__pill elements for this two-anomaly fixture "
        "(stale device + stale pipeline), got %d" % rendered.count('class="banner__pill"'))


# ==========================================================================
# Corroboration's compact rows + closed-by-default explanations
# ==========================================================================


def test_corroboration_rows_compact_explanations_in_closed_disclosure(tmp_path):
    """Corroboration's three rows stay compact (dot/label/count only) and their
    explanations move into a closed-by-default disclosure"""
    now = shp.now()
    shp.seed_runway_events(str(tmp_path), [
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": True},
        {"ts": shp.iso(now), "hex": "def456", "corroborated": None},
        {"ts": shp.iso(now), "hex": "ghi789", "corroborated": False},
    ])
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
        assert explanation in rendered, "expected explanation %r to survive somewhere in the rendered page" % explanation
    details_start = rendered.index('<details class="readings-disclosure"')
    compact_rows_html = rendered[:details_start]
    for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
        assert explanation not in compact_rows_html, (
            "expected the compact corroboration rows to no longer carry the explanation "
            "clause inline: %r" % explanation)
    details_tag = rendered[details_start:]
    details_open_tag = details_tag[:details_tag.index(">") + 1]
    assert " open" not in details_open_tag, "expected the corroboration disclosure to be closed by default"
    assert "<dl>" in rendered and "<dt>" in rendered and "<dd>" in rendered, (
        "expected the disclosure's explanations to render as a <dl> of <dt>/<dd> pairs")


def test_corroboration_section_disagreement_flag_unchanged():
    """_corroboration_section()'s second return value (the disagreement flag) is
    unchanged by the disclosure rewrite"""
    _, has_disagreement = health_page._corroboration_section({"True": 1, "None": 0, "False": 2})
    assert has_disagreement is True, "expected the disagreement flag to be True when the False bucket is non-zero"
    _, no_disagreement = health_page._corroboration_section({"True": 1, "None": 2, "False": 0})
    assert no_disagreement is False, "expected the disagreement flag to be False when the False bucket is zero"


def test_corroboration_copy_has_no_decision_id_leak():
    """no corroboration row's explanation leaks a bare decision-ID parenthetical"""
    for _key, _label, _status, explanation in health_page._CORROBORATION_ROWS:
        assert "(D-" not in explanation, (
            "found a decision-ID leak in a corroboration row's explanation: %r" % explanation)


# ==========================================================================
# Concise timestamps, and the stale-view-banner reversal
# ==========================================================================


def test_device_and_pipeline_rows_use_concise_timestamp_format(tmp_path):
    """the Device check-in and ADS-B pipeline rows render via the concise
    timestamp format"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.iso(now), 4200)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert rendered.count('<span class="mono" title=') >= 2, (
        "expected at least two concise_timestamp_html() spans (Device + Pipeline rows)")


def test_health_pill_reversal_guard(tmp_path):
    """Health's manual Refresh link and stale-view banner are reversed: a live
    data-loaded-at timestamp survives, page_header() is called exactly once, and
    both retired markers are gone from the rendered page and the module itself"""
    # Pins the reversal's own rendered result and positively asserts both
    # retired literals are truly gone, so a later refactor cannot silently
    # bring them back.
    now_iso = shp.iso(shp.now())
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=now_iso))
    assert rendered.count("data-loaded-at") == 1, "expected exactly one data-loaded-at attribute"
    assert ('data-loaded-at="%s"' % now_iso) in rendered, (
        "expected data-loaded-at to carry the real, request-scoped now ISO value")
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


def test_battery_section_healthy_card_border_on_normal_trend(tmp_path):
    """Battery trend renders a healthy status-coloured card border on a normal
    trend, in place of the retired status_dot() badge"""
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4190),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
    assert "battery-trend-section--ok" in battery_tag, (
        "expected the battery-trend section's own tag to carry the ok status modifier, got %r"
        % battery_tag)
    assert rendered.count("dot--ok") == 0 and "dot--warn" not in rendered and "dot--error" not in rendered, (
        "expected zero dot classes of any colour in this fixture")
    for label, expect_class in (
            (health_page.DEVICE_FRESHNESS_LABEL, "stat-tile--ok"),
            (health_page.PIPELINE_FRESHNESS_LABEL, "stat-tile--ok")):
        at = rendered.index(label)
        tile_open = rendered.rindex('<div class="stat-tile ', 0, at)
        tile_tag = rendered[tile_open:rendered.index(">", tile_open)]
        assert expect_class in tile_tag, (
            "expected the %r tile's wrapper to carry %r, got %r" % (label, expect_class, tile_tag))


def test_battery_empty_history_ok_badge_no_anomaly_banner(tmp_path):
    """an empty/single-reading battery trend renders an ok badge and no anomaly
    banner (Assumption A1 regression guard)"""
    # The empty-history branch must stay "ok", or a freshly-provisioned
    # device with zero readings would display "A battery reading shows an
    # abnormal drop." — factually wrong copy.
    markup, state = health_page._battery_section([])
    assert state == "ok", "expected _battery_section([]) to return state 'ok', got %r" % (state,)
    assert "No battery readings yet." in markup, "expected the empty-history empty-state heading in the markup"
    assert "dot--error" not in markup and "dot--warn" not in markup and "dot--ok" not in markup, (
        "did not expect any status-dot class in the empty-history markup — the badge is retired")

    # Page-level proof: a fresh device with one healthy battery reading
    # never surfaces the abnormal-drop anomaly or its banner.
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.iso(now), 4200)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    assert "dot--error" not in rendered, "did not expect an error status class with a single battery reading"
    battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
    assert "battery-trend-section--ok" in battery_tag, (
        "expected the battery-trend section's own tag to carry the ok status modifier with a "
        "single, healthy battery reading, got %r" % battery_tag)
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, (
        "did not expect the anomaly banner with a single, healthy battery reading")
    assert "Battery dropped abnormally." not in rendered, (
        "did not expect the abnormal-drop copy with a single battery reading")


def test_battery_drop_drives_badge_and_banner_detail_copy_not_rendered(tmp_path):
    """a real battery drop drives both the card's own error border (retargeted
    from the retired badge) and the banner; the detail copy is no longer
    rendered"""
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ]
    shp.seed_device_health(str(tmp_path), readings)
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
    assert "battery-trend-section--warn" in battery_tag, (
        "expected the battery-trend section's own tag to carry the warn status modifier for a "
        "drop >= BATTERY_DROP_WARN_MV (demoted from error, D-05), got %r" % battery_tag)
    count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
    assert count == 1, "expected the anomaly banner copy exactly once, found %d" % count
    assert "Battery dropped abnormally." not in rendered, (
        "the abnormal-drop detail copy must no longer be rendered on the page")
    assert health_page.collect_anomalies("ok", "ok", "error", False) == ["Battery dropped abnormally."], (
        "collect_anomalies() must still compute the abnormal-drop item directly")


# ==========================================================================
# The retired anomaly-detail-list markup
# ==========================================================================


def test_anomaly_detail_list_markup_is_gone(tmp_path):
    """an unhealthy fixture renders the anomaly banner with zero <ul/<li list
    markup inside its own element slice (retargeted from a page-wide ban, which
    collided with a legitimate .data-cards list elsewhere on the page)"""
    now = shp.now()
    shp.seed_device_health(str(tmp_path), [(shp.ago(_DEFAULT_DEVICE_ERROR_S + 60), 4000)])
    shp.seed_meta(str(tmp_path), **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    banner_at = rendered.index('<div class="banner ')
    banner_end = rendered.index("</div>", banner_at) + len("</div>")
    banner_slice = rendered[banner_at:banner_end]
    assert banner_slice.count("<ul") == 0, "expected zero <ul occurrences inside the anomaly banner"
    assert banner_slice.count("<li") == 0, "expected zero <li occurrences inside the anomaly banner"
    count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
    assert count == 1, "expected the anomaly banner copy exactly once, found %d" % count


def test_none_of_the_four_anomaly_item_strings_render(tmp_path):
    """with all four anomaly signals unhealthy, none of collect_anomalies()'s
    four item strings is rendered"""
    now = shp.now()
    # Trip all four signals at once: stale device, stale pipeline, an
    # abnormal battery drop, and a disagreement within the corroboration
    # window.
    shp.seed_device_health(str(tmp_path), [
        (shp.ago(_DEFAULT_DEVICE_ERROR_S + 60), 4200),
        (shp.ago(_DEFAULT_DEVICE_ERROR_S + 30), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ])
    shp.seed_meta(str(tmp_path), **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    shp.seed_runway_events(str(tmp_path), [
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": False}])
    rendered = health_page.render(shp.ctx(str(tmp_path), now_value=shp.iso(now)))
    expected_items = health_page.collect_anomalies("error", "error", "error", True)
    assert len(expected_items) == 4, "expected collect_anomalies() to return all four items, got %r" % (expected_items,)
    count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
    assert count == 1, "expected the anomaly banner copy exactly once, found %d" % count
    for item in expected_items:
        assert item not in rendered, "anomaly item copy leaked into the rendered page: %r" % item


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

    # The newest plotted point is marked with a non-cosmetic mark (it
    # survives the density rule that suppresses cosmetic dots) — one
    # drawn marker per point, the last of them the mark.
    dots = doc.find_all("circle", cls=health_page.SPARKLINE_DOT_CLASS)
    marks = doc.find_all("circle", cls=health_page.SPARKLINE_MARK_CLASS)
    assert (len(dots), len(marks)) == (2, 1), (
        "expected 3 drawn markers for 3 points — 2 cosmetic dots plus 1 mark on the newest — "
        "got %d dots / %d marks" % (len(dots), len(marks)))

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
