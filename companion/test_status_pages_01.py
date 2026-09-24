"""Part 01 of the `companion/test_status_pages.py` migration chain
(33-25-PLAN.md): the original harness's `check()` calls #1-#19, covering
`companion/pages/health_page.py`'s two freshness signals (Device/
Pipeline), `companion/wake.py`'s staleness-threshold/env/effective-
interval contract and its import boundary, `companion/layout.py`'s
`absolute_and_relative()` timestamp helper, and the Battery section's
ring/trend/disclosure/caption behaviour through the day-1 raw-series
fallback.

One check is pulled forward out of order (33-MIGRATION-RULES.md's rubric
T): the root-unsafe `anomaly_active()` degrade-safely check, originally
near the end of the legacy harness's Section 1 (~line 8201). Every
"missing state_dir" input now uses a `tmp_path` subpath instead of a
fixed absolute path outside the repo that production code could create
as root — a real host-filesystem write the audit flagged (T-33-25-01).
Since a `tmp_path` subpath is always writable (unlike a root-owned path
elsewhere on the host), the missing-path case can no longer exercise the
"database unopenable because the path can't even be created" branch a
non-root run of the original fixed path happened to hit — it now takes
the same schema-gets-created path the pre-existing empty-directory case
already covers, so both are asserted the same way: no raise, a real
bool, and agreement with `render()`'s own banner presence.

Every check in this module calls `companion.pages.health_page`/
`companion.wake`/`companion.layout` directly, in-process — none of this
half of the slice needs a running `companion/app.py` server.
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
    5-minute cadence, and falls back to the floors for None (19-05-PLAN.md D-05/A-23)"""
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
    leftover dot-label (quick task 260901-tsa finding C, retargeted by
    22-12-PLAN.md Task 1's X8 anatomy)"""
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
    no reading renders no ring at all rather than an empty one (CFG-40)"""
    with_reading = tmp_path / "with-reading"
    with_reading.mkdir()
    no_reading = tmp_path / "no-reading"
    no_reading.mkdir()
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    # 3690 mV lands on 32% of the DEVICE-05 discharge curve, deliberately
    # not a round fraction, so a ring drawn from a plausible-but-wrong
    # constant (half/full/empty) cannot coincide with the right answer.
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
    exactly one <svg> with exactly n - 1 trend-line segments (260902-ep7:
    retargeted from the retired single-<polyline> marker)"""
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
    """Battery Trend's Timestamp column shows the D-09 concise format (full ISO
    demoted to title), matching the Device/pipeline rows, and _battery_section()
    stays single-argument"""
    # _battery_section() must stay callable with exactly one positional
    # argument (06.5-02's own pinned automated gate, matching the real
    # call site inside render()) — proven directly by calling it with
    # just one, not by inspecting its signature (TST-12/G2 forbids
    # `inspect.*` in a migrated test).
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
    the chart precedes it (D-08)"""
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
    empty render (260902-l0b, retargeted from the retired D-10 'Latest 20
    readings' label)"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert "Last 3 months" in rendered


def test_battery_chart_plots_daily_averages_not_raw_readings(tmp_path):
    """a multi-day seeded render plots the three DAILY AVERAGES (never any raw
    reading value) as points, keeps every raw reading visible in the disclosure
    table, and names the 3-month window (260902-l0b)"""
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
    window — the day-1 regression guard (260902-l0b)"""
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
# Rubric T out-of-order pull: anomaly_active()'s root-unsafe degrade-safely
# check (originally near line ~8201 of the legacy harness)
# ==========================================================================


def test_anomaly_active_never_raises_on_hostile_inputs(tmp_path):
    """anomaly_active() runs on every page render and must never raise —
    missing/empty/file/corrupt-db inputs all degrade safely"""
    # anomaly_active() runs on every authenticated page render via
    # page_context() (companion/app.py) — it may never fault a page that
    # has nothing to do with Health.
    #
    # A never-existed-before tmp_path subpath and a pre-created empty
    # tmp_path directory take the SAME code path: history_db.open_db()
    # creates the directory (os.makedirs(..., exist_ok=True)) and the
    # schema in both cases, because tmp_path is always writable — unlike
    # the original harness's fixed absolute path outside the repo, whose
    # degrade-safely behaviour only held when the process lacked
    # permission to create it (never true for root, which is exactly
    # T-33-25-01: this check used to create a real directory on the host
    # when the suite ran as root). Both are asserted the same way: no
    # raise, a real bool, and agreement with render()'s own banner
    # presence — the property this check actually protects.
    for candidate in (tmp_path / "absent" / "nested", tmp_path / "empty"):
        candidate_str = str(candidate)
        verdict = health_page.anomaly_active(candidate_str)
        assert isinstance(verdict, bool), (
            "expected a bool (no raise) for %r, got %r" % (candidate_str, verdict))
        rendered = health_page.render(shp.ctx(candidate_str))
        assert verdict == (health_page.ANOMALY_BANNER_TEXT in rendered), (
            "anomaly_active() disagreed with render()'s banner for %r" % candidate_str)

    # A database file that exists but is not a valid SQLite file: every
    # read maps to _DB_UNAVAILABLE, which every section builder treats
    # as "ok" — collect_anomalies() must return False, not raise.
    corrupt_db_dir = tmp_path / "empty"
    dbs = [p for p in corrupt_db_dir.iterdir() if p.suffix == ".db"]
    assert dbs, "expected a database file to have been created by the loop above"
    dbs[0].write_bytes(b"not a sqlite file at all")
    assert health_page.anomaly_active(str(corrupt_db_dir)) is False, (
        "expected False for a corrupt database, not a raise")

    # A state_dir path that is a regular file, not a directory:
    # os.makedirs(..., exist_ok=True) raises FileExistsError against an
    # existing non-directory path regardless of who runs the process.
    regular_file = tmp_path / "not-a-directory"
    regular_file.write_bytes(b"")
    assert health_page.anomaly_active(str(regular_file)) is False, (
        "expected False for a state_dir that is a regular file, not a directory")
