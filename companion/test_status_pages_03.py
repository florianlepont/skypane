"""Companion status-page tests: compute_health_state()'s never-ran-pipeline
detail, overall_severity()'s widened precedence table, Health's page-header
shape, the Server & data grid, the Resolution-rate tile, the registry card,
and the battery-trend section's post-move contract.

CSS/JS checks fetch served bytes from a running companion/app.py; everything
else calls health_page/layout/i18n/prefs/wake directly, in-process.
"""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

import companion.app as app
from companion import i18n, layout, prefs
from companion.pages import health_page
import companion.test_status_pages_helpers as shp
import companion.wake as wake
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, custom_properties, declarations_for, parse_html, rules_with_selector
from server import device_config, history_db


# --- module-scoped read-only server, for the served-CSS/JS checks only -----

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


@pytest.fixture(scope="module")
def battery_trend_js(_module_server):
    return served_asset(_module_server, "/static/battery-trend.js")


# --- shared helpers, local to this part (mirrors 33-26's own local copy) ---

def _battery_section_heading(lang="en"):
    """The battery-trend heading's own rendered text, computed the SAME
    way `_battery_trend_section_html()` computes it — a relationship
    against `BATTERY_SECTION_HEADING_TEMPLATE`/`BATTERY_TREND_WINDOW_DAYS`,
    never a typed literal."""
    return i18n.t_lang(health_page.BATTERY_SECTION_HEADING_TEMPLATE, lang) % (
        health_page.BATTERY_TREND_WINDOW_DAYS // 30)


def _tile_slice_by_caption(rendered, caption):
    matching = [tile for tile in shp.stat_tile_slices(rendered) if caption in tile]
    assert len(matching) == 1, (
        "expected exactly one .stat-tile carrying caption %r, got %d"
        % (caption, len(matching)))
    return matching[0]


# ==========================================================================
# compute_health_state()'s never-ran-pipeline detail fragment (B2)
# ==========================================================================


def test_compute_health_state_carries_pipeline_detail_html_has_run(tmp_path):
    """compute_health_state()'s pipeline_detail_html key, once the pipeline has run at least once,
    is verdict-free and embedded once inside pipeline_html, mirroring device_detail_html"""
    state_dir = str(tmp_path)
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.ago(120)})
    state = health_page.compute_health_state(state_dir, now=shp.iso(shp.now()))
    detail_only = state["pipeline_detail_html"]
    assert "widget-verdict" not in detail_only, (
        "expected pipeline_detail_html to carry no widget-verdict class")
    for verdict_text in health_page.PIPELINE_STATE_TEXT.values():
        assert verdict_text not in detail_only, (
            "expected pipeline_detail_html to carry no PIPELINE_STATE_TEXT verdict text, "
            "found %r" % (verdict_text,))
    assert detail_only in state["pipeline_html"], (
        "expected pipeline_detail_html to be the exact verdict-free fragment embedded "
        "inside pipeline_html")


def test_collect_anomalies_and_overall_severity_treat_pipeline_off_as_healthy():
    """collect_anomalies()/overall_severity() treat pipeline_state='off' (never ran) exactly like
    'ok' — never an anomaly, never a warn — while a genuinely stale pipeline_state still is"""
    assert health_page.collect_anomalies("ok", "off", "ok", False) == [], (
        "expected collect_anomalies() to treat pipeline_state='off' as no anomaly (B2)")
    assert health_page.overall_severity("ok", "off", "ok", False) == "ok", (
        "expected overall_severity() to treat pipeline_state='off' as healthy (B2)")
    # A genuinely stale pipeline (any other non-'ok' value) still counts,
    # proving 'off' is a real exemption, not an accidental membership-check
    # bug that swallowed every non-'ok' value.
    assert health_page.collect_anomalies("ok", "warn", "ok", False) == [
        health_page.i18n.t("Flight data is stale.")], (
        "expected collect_anomalies() to still flag a genuinely stale pipeline")
    assert health_page.overall_severity("ok", "warn", "ok", False) == "warn", (
        "expected overall_severity() to still warn for a genuinely stale pipeline")


# ==========================================================================
# battery_sparkline_svg() regression guards, hostile timestamps, and the
# Python/CSS/JS cross-file contract
# ==========================================================================


def test_single_reading_still_no_chart_no_readout_no_script(tmp_path):
    """battery_sparkline_svg() still returns '' for fewer than two numeric readings, and the page emits neither
    a readout element nor a chart script tag (regression guard)"""
    assert health_page.battery_sparkline_svg([{"ts": "t1", "battery_mv": 4200}]) == "", (
        "expected battery_sparkline_svg() to return '' for a single-row input")
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert "<script" not in rendered, "did not expect a <script tag with only one battery reading"
    assert health_page.BATTERY_READOUT_ID not in rendered, (
        "did not expect the readout element id with only one battery reading")
    assert health_page.SPARKLINE_LINE_CLASS not in rendered, (
        "did not expect a sparkline trend-line segment with only one battery reading")


def test_page_allows_exactly_one_scoped_script_no_inline_handlers(tmp_path):
    """a chart-bearing page emits exactly one scoped <script src> and zero inline event-handler attributes"""
    state_dir = str(tmp_path)
    base = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    assert rendered.count("<script") == 1, (
        "expected exactly one <script tag, got %d" % rendered.count("<script"))
    assert health_page.BATTERY_TREND_SCRIPT_SRC in rendered, (
        "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>")
    for forbidden in ("onclick=", "onmouseover=", "ontouchstart=", "onfocus=", "onload="):
        assert forbidden not in rendered, (
            "found forbidden inline event-handler attribute %r" % forbidden)


def test_empty_battery_history_stays_script_free(tmp_path):
    """the empty-history battery path stays script-free — no <script, no <svg, no readout element"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert "<script" not in rendered, "did not expect any <script tag with zero battery rows"
    assert health_page.SPARKLINE_LINE_CLASS not in rendered, (
        "did not expect a sparkline trend-line segment with zero battery rows")
    assert health_page.SPARKLINE_DOT_CLASS not in rendered, (
        "did not expect a sparkline dot with zero battery rows")
    assert health_page.BATTERY_READOUT_ID not in rendered, (
        "did not expect the readout element id with zero battery rows")


def test_hostile_timestamp_is_escaped_in_chart_markup(tmp_path):
    """a hostile timestamp reaching data-ts/<title> is escaped, never interpolated raw"""
    state_dir = str(tmp_path)
    base = shp.now()
    hostile_ts = '2024-01-01T00:00:00Z"><script>alert(1)</script>'
    shp.seed_device_health(state_dir, [
        (hostile_ts, 4200),
        (shp.iso(base), 4190),
    ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    assert hostile_ts not in rendered, (
        "the raw hostile timestamp fragment survived unescaped into the output")
    assert '"><script>alert(1)</script>' not in rendered, (
        "the raw quote-and-tag fragment survived unescaped into a double-quoted attribute")
    escaped_ts = health_page.escape_html(hostile_ts)
    assert escaped_ts in rendered, "expected the escaped form of the hostile timestamp to appear"


def test_cross_file_contract_drift_guard(tmp_path, battery_trend_js):
    """the Python/CSS/JS three-file contract (route + DOM literals) is guarded against silent drift"""
    assert app.SCRIPT_ROUTE == health_page.BATTERY_TREND_SCRIPT_SRC, (
        "companion.app.SCRIPT_ROUTE and health_page.BATTERY_TREND_SCRIPT_SRC have drifted apart")
    assert health_page.BATTERY_READOUT_ID in battery_trend_js, (
        "battery-trend.js no longer references BATTERY_READOUT_ID's literal value")
    assert health_page.SPARKLINE_HIT_CLASS in battery_trend_js, (
        "battery-trend.js no longer references SPARKLINE_HIT_CLASS's literal value")
    state_dir = str(tmp_path)
    base = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    assert health_page.BATTERY_READOUT_ID in rendered, (
        "expected BATTERY_READOUT_ID in a rendered chart-bearing page")
    assert health_page.SPARKLINE_HIT_CLASS in rendered, (
        "expected SPARKLINE_HIT_CLASS in a rendered chart-bearing page")


def test_battery_drop_flags_anomaly_gentle_decline_does_not():
    """a large consecutive-reading drop flags a battery warning (demoted from error); a gentle
    monotonic decline does not"""
    # battery_status() takes newest-first rows (matching battery_trend_rows()'s/
    # recent_device_health()'s own ordering) — t2 (newer) sorts before t1 (older)
    # in both fixtures below. A >= BATTERY_DROP_WARN_MV drop is a "warn",
    # demoted from "error" (a single sampling artefact must not paint the
    # whole page as an outage).
    drop_rows = [
        {"ts": "t2", "battery_mv": 4200 - health_page.BATTERY_DROP_WARN_MV},
        {"ts": "t1", "battery_mv": 4200},
    ]
    assert health_page.battery_status(drop_rows) == "warn", (
        "expected a drop >= BATTERY_DROP_WARN_MV to flag a battery warning")
    gentle_rows = [
        {"ts": "t3", "battery_mv": 4190},
        {"ts": "t2", "battery_mv": 4195},
        {"ts": "t1", "battery_mv": 4200},
    ]
    assert health_page.battery_status(gentle_rows) == "ok", (
        "expected a gentle monotonic decline to not flag the battery anomaly")


# ==========================================================================
# overall_severity()'s widened precedence table, and collect_anomalies()'s
# two matching new items
# ==========================================================================


def test_overall_severity_widened_precedence_table():
    """overall_severity()'s widened 6-input precedence table: source_fault wins outright, error states
    win next, then warn states/disagreement_warn/coverage_state=='warn', with the 4-argument call
    staying byte-for-byte backward compatible"""
    # The full 6-input precedence table, including the 4-argument
    # backward-compatible call (the two new keyword parameters both
    # default, so an existing 4-argument caller's behaviour is
    # byte-for-byte unchanged).
    assert health_page.overall_severity("ok", "ok", "ok", False) == "ok", (
        "expected the healthy 4-argument call to stay ok (backward compatible)")
    assert health_page.overall_severity("warn", "ok", "ok", False) == "warn", (
        "expected any warn state to produce warn")
    assert health_page.overall_severity("error", "ok", "ok", False) == "error", (
        "expected any error state to produce error")
    assert health_page.overall_severity("ok", "ok", "ok", True) == "warn", (
        "expected disagreement_warn alone to produce warn")
    assert health_page.overall_severity("ok", "ok", "ok", False, coverage_state="warn") == "warn", (
        "expected coverage_state='warn' alone to produce warn")
    assert health_page.overall_severity("ok", "ok", "ok", False, source_fault=True) == "error", (
        "expected source_fault=True alone to produce error")
    assert health_page.overall_severity(
        "error", "ok", "ok", False, coverage_state="warn", source_fault=True) == "error", (
        "expected source_fault to win outright over every other signal")
    assert health_page.overall_severity(
        "warn", "ok", "ok", False, coverage_state="ok", source_fault=False) == "warn", (
        "expected a warn state with no coverage/source_fault input to stay warn")


def test_overall_severity_acceptance_criteria_literal():
    """overall_severity()'s plan-cited acceptance triple: ('ok', 'error', 'warn')"""
    # The plan's own acceptance-criteria one-liner, run as a check rather
    # than only a shell command.
    results = (
        health_page.overall_severity("ok", "ok", "ok", False),
        health_page.overall_severity("ok", "ok", "ok", False, source_fault=True),
        health_page.overall_severity("ok", "ok", "ok", False, coverage_state="warn"),
    )
    assert results == ("ok", "error", "warn"), "expected ('ok', 'error', 'warn'), got %r" % (results,)


def test_source_fault_alone_produces_error_registry_alone_produces_warn(tmp_path):
    """compute_health_state() folds an active source_fault_raw alone into error severity, a non-empty
    registry alone into warn severity, and stays ok when both are clear"""
    now = shp.now()

    state_dir = str(tmp_path / "source-fault-alone")
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.iso(now),
        history_db.META_SOURCE_FAULT: "True",
    })
    state = health_page.compute_health_state(state_dir, now=shp.iso(now))
    assert state["severity"] == "error", (
        "expected an active source_fault_raw alone to produce error severity, got %r"
        % (state["severity"],))

    state_dir2 = str(tmp_path / "registry-alone")
    shp.seed_device_health(state_dir2, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir2, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_unresolved_prefixes(state_dir2, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    state2 = health_page.compute_health_state(state_dir2, now=shp.iso(now))
    assert state2["severity"] == "warn", (
        "expected a non-empty registry alone to produce warn severity, got %r" % (state2["severity"],))

    state_dir3 = str(tmp_path / "fully-healthy")
    shp.seed_device_health(state_dir3, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir3, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    state3 = health_page.compute_health_state(state_dir3, now=shp.iso(now))
    assert state3["severity"] == "ok", (
        "expected an empty registry with everything else healthy to stay ok, got %r"
        % (state3["severity"],))


def test_collect_anomalies_two_new_items():
    """collect_anomalies()'s two new items (source_fault, coverage_state) appear only when their own
    input is unhealthy, and a fully healthy 4-argument call still returns none"""
    assert "All data sources failed." in health_page.collect_anomalies(
        "ok", "ok", "ok", False, source_fault=True), (
        "expected the source_fault item to appear when source_fault=True")
    assert "Some airlines are unidentified." in health_page.collect_anomalies(
        "ok", "ok", "ok", False, coverage_state="warn"), (
        "expected the coverage item to appear when coverage_state='warn'")
    assert health_page.collect_anomalies("ok", "ok", "ok", False) == [], (
        "expected a fully healthy 4-argument call to still return no anomalies")


def test_device_staleness_pinned_from_both_directions_by_cadence(tmp_path, monkeypatch):
    """a device last seen 400 seconds ago is 'warn' at a 30s wake cadence but 'ok' at a 3600s cadence,
    pinned from both directions through the real compute_health_state() pipeline"""
    # 400s > the 300s floor (3 * 30s), so it reads "warn" at a 30s cadence,
    # but 400s < 3 * 3600s, so it reads "ok" at a 3600s cadence. The 30s
    # cadence is deployed via SKYPANE_SLEEP_S (the env fallback); the
    # 3600s cadence via a seeded device_config.json.
    now = shp.now()

    state_dir = str(tmp_path / "cadence-env-30")
    shp.seed_device_health(state_dir, [(shp.iso(now - timedelta(seconds=400)), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    monkeypatch.setenv(wake.SLEEP_ENV_VAR, "30")
    state = health_page.compute_health_state(state_dir, now=shp.iso(now))
    assert state["device_state"] == "warn", (
        "expected device_state='warn' for a 400s-old reading at a 30s cadence, got %r"
        % (state["device_state"],))

    state_dir2 = str(tmp_path / "cadence-cfg-3600")
    shp.seed_device_health(state_dir2, [(shp.iso(now - timedelta(seconds=400)), 4200)])
    shp.seed_meta(state_dir2, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    monkeypatch.delenv(wake.SLEEP_ENV_VAR, raising=False)
    device_config.save_device_config(state_dir2, wake_interval_s=3600)
    state2 = health_page.compute_health_state(state_dir2, now=shp.iso(now))
    assert state2["device_state"] == "ok", (
        "expected device_state='ok' for a 400s-old reading at a 3600s cadence, got %r"
        % (state2["device_state"],))


def test_corroboration_unknown_only_no_error_or_warn(tmp_path):
    """corroboration counts made only of the unknown state produce no error status class"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": None},
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": None},
    ])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert "dot--error" not in rendered, (
        "expected no error status class for an unknown-state-only corroboration count")
    assert "dot--warn" not in rendered, (
        "expected no warn status class either — this fixture is fully healthy otherwise")


def test_no_anomaly_banner_when_all_healthy(tmp_path):
    """a fully-healthy fixture renders no anomaly banner at all"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(now - timedelta(minutes=2)), 4200),
        (shp.iso(now), 4198),
    ])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": True}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, (
        "did not expect the anomaly banner when every signal is healthy")


def test_stale_pipeline_shows_banner_exactly_once(tmp_path):
    """a stale ADS-B pipeline shows the anomaly banner copy exactly once"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
    assert count == 1, "expected the anomaly banner copy exactly once, found %d" % count


def test_unreadable_database_degrades_without_raising(tmp_path):
    """a state directory that cannot hold a database renders the health-unavailable copy without raising"""
    blocked_state_dir = tmp_path / "blocked"
    blocked_state_dir.write_text("this is a file, not a directory")
    rendered = health_page.render(shp.ctx(str(blocked_state_dir)))
    assert health_page.HEALTH_UNAVAILABLE_TEXT in rendered, (
        "expected the health-unavailable copy when the database cannot be opened")


def test_source_fault_set_shows_landing_explanation(tmp_path):
    """with the source-fault meta key set, the landing explanation appears"""
    state_dir = str(tmp_path)
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    rendered = health_page.render(shp.ctx(state_dir))
    assert health_page.SOURCE_FAULT_HEADING in rendered, (
        "expected the CFG-05 landing explanation when the source-fault flag is set")


def test_source_fault_unset_hides_landing_explanation(tmp_path):
    """with the source-fault meta key unset, the landing explanation is absent"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert health_page.SOURCE_FAULT_HEADING not in rendered, (
        "did not expect the CFG-05 landing explanation with no source-fault flag set")


def test_health_page_never_imports_html_module():
    """companion/pages/health_page.py never imports the stdlib html module directly"""
    # rewrite: a bare `import html` binds the name `html`
    # directly into health_page's own module namespace, so hasattr() is a
    # real behavioural proof of the same fact the legacy check's source
    # grep asserted — never a source-text read.
    assert not hasattr(health_page, "html"), (
        "health_page.py must never import the stdlib html module directly")


def test_health_page_opens_with_shared_page_header(tmp_path):
    """Health opens with the shared layout.page_header() component, not a bare <h1>"""
    # 06.6.2-04 (): Health's top-level heading now goes through
    # layout.page_header() instead of an independent bare <h1>.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert '<h1 class="page-title">Health</h1>' in rendered, (
        "expected the page_header()-rendered <h1 class=\"page-title\">Health</h1>")
    assert '<h1 class="text-heading">' not in rendered, (
        "expected no bare <h1 class=\"text-heading\"> heading")


def test_health_page_purpose_sentence_present_after_refresh(tmp_path):
    """Health's .page-header carries a one-sentence purpose after the auto-refresh pill"""
    # PAGE_PURPOSE_TEXT reaches layout.page_header()'s `purpose`
    # parameter, renders inside .page-header, and follows the Refresh
    # link, matching the validated sketch's own DOM order.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    escaped_purpose = layout.escape_html(health_page.PAGE_PURPOSE_TEXT)
    assert rendered.count(escaped_purpose) == 1, (
        "expected the escaped page-purpose sentence exactly once, got %d"
        % rendered.count(escaped_purpose))
    header_start = rendered.index('<div class="page-header">')
    header_end = rendered.index("</div>", header_start) + len("</div>")
    header_slice = rendered[header_start:header_end]
    assert escaped_purpose in header_slice, (
        "expected the purpose sentence inside the .page-header div, not elsewhere on the page")
    # Retargeted from the retired "freshness-refresh" link class onto the
    # pill's own marker attribute — the ordering property this check
    # tests (the header's action slot precedes the purpose sentence) is
    # unchanged by that reversal.
    refresh_at = rendered.index("data-refresh-pill")
    purpose_at = rendered.index(escaped_purpose)
    assert refresh_at < purpose_at, (
        "expected the purpose sentence to follow the pill, matching the validated sketch's own "
        "DOM order")


def test_health_page_two_id_anchored_sections_correct_order_no_overview(tmp_path):
    """Health's body is two id-anchored sections (Screen, then Server & data), and the old 'Overview' heading
    is gone"""
    # Health's body is two id-anchored sections, Screen then Server &
    # data, replacing the single "Overview" heading + one dashboard-grid
    # shape.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert rendered.count(">Overview<") == 0, "expected the old 'Overview' heading to be gone"
    screen_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
        health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING)
    server_data_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
        health_page.SERVER_DATA_SECTION_ID,
        layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING))
    assert screen_heading in rendered, "expected the Screen section's id-anchored <h2>"
    assert server_data_heading in rendered, "expected the Server & data section's id-anchored <h2>"
    assert rendered.index(screen_heading) < rendered.index(server_data_heading), (
        "expected the Screen section to precede the Server & data section")
    assert rendered.count('<h2 id="') == 2, "expected exactly two id-anchored <h2> elements"
    # The section's own class attribute also carries a status modifier
    # (BATTERY_SECTION_CLASS + "--ok"/"--warn"/"--error"), so the bare
    # class-name substring appears TWICE inside that one attribute — the
    # open-tag prefix counts sections, not substrings.
    assert rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS) == 1, (
        "expected exactly one battery-trend section, got %d"
        % rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS))
    assert rendered.index(health_page.BATTERY_SECTION_CLASS) > rendered.index(screen_heading), (
        "expected the battery-trend section to follow the Screen heading")
    assert rendered.index(health_page.BATTERY_SECTION_CLASS) < rendered.index(server_data_heading), (
        "expected the battery-trend section to stay inside the Screen section, before Server & data")


def test_health_page_section_intros_pair_heading_with_description(tmp_path):
    """each of Health's two section headings is paired, in its own baseline-aligned .section-intro wrapper,
    with its own muted description"""
    # Slices each wrapper individually (rather than searching the whole
    # page) so the check cannot pass by finding the right description
    # next to the wrong heading.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    wrapper_count = rendered.count('<div class="section-intro">')
    assert wrapper_count == 2, "expected exactly two section-intro wrappers, got %d" % wrapper_count

    screen_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
        health_page.SCREEN_SECTION_ID, layout.escape_html(health_page.SCREEN_SECTION_HEADING))
    server_data_heading = '<h2 id="%s" class="text-heading">%s</h2>' % (
        health_page.SERVER_DATA_SECTION_ID, layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING))
    # Every expected substring is built through escape_html() — never
    # re-typed as a raw literal. The Screen description contains an
    # apostrophe ("how's the battery"), which escape_html(..., quote=True)
    # encodes; a raw-constant comparison would fail here for a reason that
    # has nothing to do with the markup being wrong.
    screen_description = layout.escape_html(health_page.SCREEN_SECTION_DESCRIPTION)
    server_data_description = layout.escape_html(health_page.SERVER_DATA_SECTION_DESCRIPTION)

    first_open = rendered.index('<div class="section-intro">')
    first_close = rendered.index("</div>", first_open) + len("</div>")
    first_wrapper = rendered[first_open:first_close]
    second_open = rendered.index('<div class="section-intro">', first_close)
    second_close = rendered.index("</div>", second_open) + len("</div>")
    second_wrapper = rendered[second_open:second_close]

    assert screen_heading in first_wrapper and screen_description in first_wrapper, (
        "expected the first section-intro wrapper to hold the Screen heading and description")
    assert first_wrapper.index(screen_heading) < first_wrapper.index(screen_description), (
        "expected the Screen heading to precede its own description")

    assert server_data_heading in second_wrapper and server_data_description in second_wrapper, (
        "expected the second section-intro wrapper to hold the Server & data heading and description")
    assert second_wrapper.index(server_data_heading) < second_wrapper.index(server_data_description), (
        "expected the Server & data heading to precede its own description")


def test_server_data_grid_holds_three_tiles_migrated_cards_outside_grid(tmp_path):
    """the Screen section's dashboard-grid holds exactly one tile, the Server & data dashboard-grid holds
    exactly three, the two migrated cards render as nested page-section elements outside both, and the
    source-fault block never carries that modifier (finding E, finding 4)"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    registry = {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    }
    shp.seed_unresolved_prefixes(state_dir, registry)
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    # The Screen section now also wraps its own single Device tile in a
    # dashboard-grid, so the page carries TWO dashboard-grid divs, not
    # one.
    assert rendered.count('<div class="dashboard-grid">') == 2, (
        "expected exactly two dashboard-grid divs (Screen's single-tile grid + Server & data's "
        "three-tile grid), got %d" % rendered.count('<div class="dashboard-grid">'))
    # Trailing space distinguishes a stat-tile wrapper div's own class
    # attribute (always "stat-tile <modifier>") from the Resolution-rate
    # tile's inner <p class="stat-tile__value"> figure, which this
    # fixture's 100%-resolved stats also emit.
    assert rendered.count('class="stat-tile ') == 4, (
        "expected exactly four stat-tile occurrences (Device in the Screen grid + Pipeline/"
        "Corroboration/Resolution-rate in the Server & data grid), got %d"
        % rendered.count('class="stat-tile '))

    server_data_heading_at = rendered.index(
        '<h2 id="%s" class="text-heading">' % health_page.SERVER_DATA_SECTION_ID)
    screen_grid_open = rendered.index('<div class="dashboard-grid">')
    server_data_grid_open = rendered.index('<div class="dashboard-grid">', server_data_heading_at)
    assert server_data_grid_open != screen_grid_open, (
        "expected two distinct dashboard-grid divs, found only one after the Server & data heading")

    # The Screen section's own grid holds exactly one tile.
    screen_grid_slice = rendered[screen_grid_open:server_data_heading_at]
    assert screen_grid_slice.count('class="stat-tile ') == 1, (
        "expected exactly one stat-tile occurrence inside the Screen section's dashboard-grid, "
        "got %d" % screen_grid_slice.count('class="stat-tile '))

    # The registry card's class attribute now also carries a status
    # modifier (coverage_status()'s own "--ok"/"--warn"), so the closing
    # quote no longer immediately follows "page-section--nested" — this
    # open-ended prefix still finds it, and
    # the slice-and-check below confirms which card it found.
    first_section_open = rendered.index('<section class="page-section page-section--nested')
    first_section_close = rendered.index("</section>", first_section_open) + len("</section>")
    first_section_slice = rendered[first_section_open:first_section_close]
    assert health_page.UNRESOLVED_SECTION_HEADING in first_section_slice, (
        "expected the first nested page-section card (found via its own open-tag prefix) to be "
        "the Unresolved-prefixes card, got %r" % first_section_slice[:120])
    assert first_section_open > server_data_grid_open, (
        "expected the first migrated page-section card to follow the Server & data dashboard-grid")
    grid_slice = rendered[server_data_grid_open:first_section_open]
    assert grid_slice.count('class="stat-tile ') == 3, (
        "expected exactly three stat-tile occurrences inside the Server & data dashboard-grid, "
        "got %d" % grid_slice.count('class="stat-tile '))
    assert health_page.UNRESOLVED_SECTION_HEADING not in grid_slice, (
        "the Unresolved-prefixes card must not appear inside the dashboard-grid")
    assert health_page.STATS_SECTION_HEADING not in grid_slice, (
        "the Resolution-statistics card must not appear inside the dashboard-grid")
    assert rendered.count('<section class="page-section page-section--nested') == 2, (
        "expected exactly two nested page-section cards (registry + stats), got %d"
        % rendered.count('<section class="page-section page-section--nested'))
    # The source-fault block's own page-section (rendered only when
    # META_SOURCE_FAULT is set, not seeded by this fixture) must never
    # carry the nested modifier — checked unconditionally against the
    # whole page, since the modifier-bearing count assertion above already
    # proves no OTHER page-section carries it either.
    assert 'class="page-section banner banner--anomaly page-section--nested"' not in rendered, (
        "the source-fault block must never carry the nested modifier")


def test_resolution_rate_tile_renders_percentage_and_window(tmp_path):
    """the Resolution-rate tile renders the resolved percentage and the window/event-count line for a seeded
    fixture, and the no-stats empty state for an empty one """
    state_dir = str(tmp_path / "seeded")
    now = shp.now()
    events = []
    for source in ("fresh_hit", "fresh_hit", "cache_hit", "miss"):
        events.append({"ts": shp.iso(now), "hex": "abc123", "route_source": source})
    shp.seed_runway_events(state_dir, events)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert health_page.RESOLUTION_RATE_LABEL in rendered, "expected the Resolution rate tile's caption"
    assert "75.0%" in rendered, "expected the resolved percentage in the tile's stat-tile__value"
    assert ("over the last %d days, 4 events" % health_page.RESOLUTION_WINDOW_DAYS) in rendered, (
        "expected the window/event-count text-label line")

    state_dir_empty = str(tmp_path / "empty")
    rendered_empty = health_page.render(shp.ctx(state_dir_empty))
    # The no-stats copy is now the windowed heading, interpolated with
    # RESOLUTION_WINDOW_DAYS — never the retired "No resolution data
    # yet." literal.
    expected_heading = health_page._NO_STATS_HEADING % health_page.RESOLUTION_WINDOW_DAYS
    assert expected_heading in rendered_empty, (
        "expected the no-stats empty-state heading with zero resolution history")


def test_registry_card_keeps_filter_bar_note_and_non_button_clear(tmp_path):
    """the migrated Unresolved-prefixes card keeps its filter bar, read-only note, and non-button Clear
    control"""
    state_dir = str(tmp_path)
    registry = {
        "ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
    }
    shp.seed_unresolved_prefixes(state_dir, registry)
    rendered = health_page.render(shp.ctx(state_dir))
    for marker in ("data-filter-input", "data-filter-count", "data-filter-clear", "data-filter-empty"):
        assert marker in rendered, (
            "expected the migrated filter bar's %r marker to survive the move" % marker)
    # The note was reworded to include an apostrophe ("row's") and drop
    # its second apostrophe ("prefix's") along with the word "prefix"
    # itself, which escape_html()'s quote=True mode renders as &#x27; —
    # compare against the escaped form, not the raw Python literal.
    assert layout.escape_html(health_page._READ_ONLY_NOTE) in rendered, (
        "expected the read-only note to survive the move verbatim (escaped)")
    section_start = rendered.index(
        '<h2 class="text-heading">%s</h2>' % health_page.UNRESOLVED_SECTION_HEADING)
    section_slice = rendered[section_start:section_start + 4000]
    assert "<button" not in section_slice, (
        "the migrated registry card's Clear control must not be a <button>")


def test_read_only_note_reworded_to_point_at_airlines_not_the_runbook(tmp_path):
    """the read-only note is reworded to name Airlines as the resolution surface, no longer points at
    the manual runbook, no longer says 'prefix' in either half, and is now split into a short
    visible sentence plus its moved instruction inside a readings-disclosure"""
    # The note now points at the Airlines page's per-row Resolve link
    # instead of the old manual runbook, and is split: `_READ_ONLY_NOTE`
    # (visible) carries "This list is read-only here."; the Airlines
    # instruction lives in `_READ_ONLY_NOTE_DETAIL`, inside a
    # <details class="readings-disclosure">.
    old_note_closing_phrase = "following the existing coverage-gap runbook."
    expected_visible = "This list is read-only here."
    expected_detail = (
        "Each row's Resolve link opens the Airlines page to name "
        "that airline (and add artwork, if it needs one).")
    assert health_page._READ_ONLY_NOTE == expected_visible, (
        "expected _READ_ONLY_NOTE to equal the CFG-79 shortened string, got %r"
        % (health_page._READ_ONLY_NOTE,))
    assert health_page._READ_ONLY_NOTE_DETAIL == expected_detail, (
        "expected _READ_ONLY_NOTE_DETAIL to equal the moved D-06 plain-language instruction, got %r"
        % (health_page._READ_ONLY_NOTE_DETAIL,))
    assert "prefix" not in health_page._READ_ONLY_NOTE.lower(), (
        "expected _READ_ONLY_NOTE to contain no occurrence of 'prefix'")
    assert "prefix" not in health_page._READ_ONLY_NOTE_DETAIL.lower(), (
        "expected _READ_ONLY_NOTE_DETAIL to contain no occurrence of 'prefix'")

    rendered = health_page.render(shp.ctx(str(tmp_path)))
    # Both contain an apostrophe ("row's"), which escape_html()'s
    # quote=True mode renders as &#x27; — compare against the escaped
    # form, the module's own single escaping choke-point discipline.
    visible_marker = '<p class="text-body section-caption">%s</p>' % layout.escape_html(expected_visible)
    assert visible_marker in rendered, (
        "expected the rendered page to contain the visible note verbatim (escaped)")
    detail_marker = (
        '<details class="readings-disclosure"><summary>%s</summary><p>%s</p></details>'
        % (layout.escape_html(i18n.t("More details")), layout.escape_html(expected_detail)))
    assert detail_marker in rendered, (
        "expected the moved instruction verbatim (escaped) inside a readings-disclosure")
    assert old_note_closing_phrase not in rendered, (
        "expected the old runbook-pointing phrase to be fully gone from the render")


def test_source_rows_gains_fifth_manual_entry(tmp_path):
    """_SOURCE_ROWS has a fifth 'manual' entry, resolution_stats() folds a seeded 'manual' route_source
    count into the total and a labelled row, and render() shows a 'Manual' row"""
    # _SOURCE_ROWS gains a fifth "manual" tuple so the resolution-rate
    # breakdown never folds a hand-resolved prefix into the
    # "airline_only" bucket, whose gloss says the static prefix table
    # did the work.
    assert len(health_page._SOURCE_ROWS) == 5, (
        "expected exactly 5 _SOURCE_ROWS entries, got %d" % len(health_page._SOURCE_ROWS))
    assert health_page._SOURCE_ROWS[4][0] == "manual", (
        "expected the fifth _SOURCE_ROWS entry's key to be 'manual', got %r"
        % (health_page._SOURCE_ROWS[4][0],))
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc001", "route_source": "fresh_hit"},
        {"ts": shp.iso(now), "hex": "abc002", "route_source": "manual"},
        {"ts": shp.iso(now), "hex": "abc003", "route_source": "manual"},
    ])
    with history_db.open_db(state_dir) as conn:
        stats = health_page.resolution_stats(conn, health_page.RESOLUTION_WINDOW_DAYS)
    assert stats["total"] == 3, (
        "expected the seeded 'manual' events to count toward the total, got %r" % (stats["total"],))
    manual_rows = [row for row in stats["rows"] if row[0] == "Manual"]
    assert len(manual_rows) == 1 and manual_rows[0][2] == 2, (
        "expected exactly one 'Manual' row with count 2, got %r" % (manual_rows,))

    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert ">Manual<" in rendered, (
        "expected the rendered resolution-statistics table to contain a 'Manual' row label")


# ==========================================================================
# Count every row, bucket the unknown as "other", and stop rendering an
# empty "How well we name flights" card
# ==========================================================================


def test_resolution_stats_counts_unknown_route_source_as_other(tmp_path):
    """resolution_stats() counts a NULL and an unrecognised route_source into one 'Other' bucket,
    the total equals every row in the window, and render() shows the 'Other' row"""
    # A NULL route_source (the field simply omitted, which
    # record_runway_event() stores as NULL) and an explicit unrecognised
    # string both land in the "Other" bucket, and the total counts every
    # row in the window — never fewer than the database actually holds.
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc001", "route_source": "fresh_hit"},
        {"ts": shp.iso(now), "hex": "abc002"},  # NULL route_source
        {"ts": shp.iso(now), "hex": "abc003", "route_source": "some_future_value"},
    ])
    with history_db.open_db(state_dir) as conn:
        stats = health_page.resolution_stats(conn, health_page.RESOLUTION_WINDOW_DAYS)
    assert stats["total"] == 3, (
        "expected every seeded row to count toward the total, got %r" % (stats["total"],))
    other_rows = [row for row in stats["rows"] if row[0] == health_page.i18n.t(
        health_page._OTHER_SOURCE_LABEL)]
    assert len(other_rows) == 1 and other_rows[0][2] == 2, (
        "expected exactly one 'Other' row with count 2 (the NULL row plus the unrecognised-string "
        "row), got %r" % (other_rows,))

    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert ">%s<" % health_page.i18n.t(health_page._OTHER_SOURCE_LABEL) in rendered, (
        "expected the rendered resolution-statistics table to contain an 'Other' row label")
    assert "No flight events recorded yet" not in rendered, (
        "expected no trace of the retired empty-state copy with real rows present")


def test_resolution_stats_known_sources_alone_gain_no_other_row(tmp_path):
    """resolution_stats() with only known route_source values renders exactly the five _SOURCE_ROWS
    rows and no 'Other' row — byte-identical to before this task"""
    # With rows whose route_source is one of the five known values, the
    # counts (and the absence of an 'Other' row) are unchanged from today —
    # an ordinary render is byte-identical to before this task.
    state_dir = str(tmp_path)
    now = shp.now()
    events = []
    for source in ("fresh_hit", "cache_hit", "airline_only", "miss", "manual"):
        events.append({"ts": shp.iso(now), "hex": "abc123", "route_source": source})
    shp.seed_runway_events(state_dir, events)
    with history_db.open_db(state_dir) as conn:
        stats = health_page.resolution_stats(conn, health_page.RESOLUTION_WINDOW_DAYS)
    assert len(stats["rows"]) == len(health_page._SOURCE_ROWS), (
        "expected exactly %d rows (no 'Other' row) when every seeded value is known, got %d"
        % (len(health_page._SOURCE_ROWS), len(stats["rows"])))
    assert stats["total"] == 5, (
        "expected the total to still equal 5 for five known-source rows, got %r" % (stats["total"],))


def test_stats_section_absent_when_empty_both_languages(tmp_path):
    """the empty 'How well we name flights' section is entirely absent from the rendered page in
    both English and French — never a heading over an empty body"""
    # With zero rows in the window, the whole "How well we name flights"
    # section is absent from the rendered HTML — not a heading with an
    # empty body — in both languages.
    state_dir = str(tmp_path)
    now = shp.now()
    rendered_en = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert health_page.STATS_SECTION_HEADING not in rendered_en, (
        "expected zero occurrences of the stats heading with no rows in the window (en)")
    try:
        prefs.set_request_prefs(lang="fr")
        rendered_fr = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    assert health_page.i18n.t(health_page.STATS_SECTION_HEADING) not in rendered_fr, (
        "expected zero occurrences of the stats heading with no rows in the window (fr)")


def test_resolution_rate_tile_shows_36_rows_never_no_events(tmp_path):
    """with 36 seeded rows (30 known, 6 with a NULL route_source) the resolution-rate tile shows a
    non-zero count for all 36, never the empty-state copy"""
    # The audit's own seed (36 runway events over 17h) is exactly the kind
    # of fixture the pre-fix bug would have silently undercounted if any of
    # those rows carried an unrecognised route_source — reproduced here
    # with a deliberate mix of known and unknown values summing to 36.
    state_dir = str(tmp_path)
    now = shp.now()
    events = []
    for i in range(30):
        events.append({"ts": shp.iso(now), "hex": "abc%03d" % i, "route_source": "fresh_hit"})
    for i in range(6):
        events.append({"ts": shp.iso(now), "hex": "def%03d" % i})  # NULL route_source
    shp.seed_runway_events(state_dir, events)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    tile_slice = _tile_slice_by_caption(rendered, health_page.RESOLUTION_RATE_LABEL)
    assert "No flight events recorded yet" not in tile_slice and "No flights in the last" not in tile_slice, (
        "expected a non-empty resolution-rate tile with 36 seeded rows in the window")
    assert ("over the last %d days, 36 events" % health_page.RESOLUTION_WINDOW_DAYS) in tile_slice, (
        "expected the window/event-count line to report all 36 seeded rows")


def test_no_stats_heading_derives_from_window_constant_not_hard_coded():
    """_NO_STATS_HEADING is an unformatted %d template with no hard-coded window literal, and
    interpolates RESOLUTION_WINDOW_DAYS at its one call site"""
    # The empty copy names the window and derives the number from
    # RESOLUTION_WINDOW_DAYS, never a hard-coded "30" in the string itself.
    assert "%d" in health_page._NO_STATS_HEADING, (
        "expected _NO_STATS_HEADING to be an unformatted %d template")
    assert "30" not in health_page._NO_STATS_HEADING, (
        "expected _NO_STATS_HEADING to carry no hard-coded window literal")
    formatted = health_page._NO_STATS_HEADING % health_page.RESOLUTION_WINDOW_DAYS
    assert str(health_page.RESOLUTION_WINDOW_DAYS) in formatted, (
        "expected the formatted heading to actually name the configured window")


def test_registry_resolve_link_pairs_desktop_and_mobile_and_escapes_hostile_input(tmp_path):
    """the registry's per-row Resolve link is paired identically (href/aria-label) across the desktop
    table and mobile card, with distinct visible text per representation, and a hostile prefix renders
    fully escaped in both (phase 13)"""
    # phase 13 (): each registry row's Resolve link is emitted twice —
    # once in the desktop <tr>'s sixth <td>, once in the mobile card's
    # .data-card__action block — sharing the identical href/aria-label,
    # differing only in visible link text.
    state_dir = str(tmp_path / "normal")
    os.makedirs(state_dir)
    shp.seed_unresolved_prefixes(state_dir, {
        "XYZ": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    rendered = health_page.render(shp.ctx(state_dir))
    expected_href = 'href="%s"' % (health_page.RESOLVE_LINK_HREF_TEMPLATE % "XYZ")
    expected_aria = 'aria-label="%s"' % (health_page.RESOLVE_LINK_ARIA_TEMPLATE % "XYZ")
    assert rendered.count(expected_href) == 2, (
        "expected %r exactly twice (table + card), got %d" % (expected_href, rendered.count(expected_href)))
    assert rendered.count(expected_aria) == 2, (
        "expected %r exactly twice (table + card), got %d" % (expected_aria, rendered.count(expected_aria)))
    assert rendered.count(">%s</a>" % health_page.RESOLVE_LINK_TEXT) == 1, (
        "expected the desktop anchor's link text 'Resolve' exactly once")
    assert rendered.count(">%s</a>" % health_page.RESOLVE_CARD_LINK_TEXT) == 1, (
        "expected the mobile anchor's link text 'Resolve this prefix' exactly once")

    # Hostile prefix — must render fully escaped in both representations,
    # no raw angle bracket or quote reaching output.
    state_dir_hostile = str(tmp_path / "hostile")
    os.makedirs(state_dir_hostile)
    hostile_prefix = '<x>"'
    shp.seed_unresolved_prefixes(state_dir_hostile, {
        hostile_prefix: {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "X"},
    })
    rendered_hostile = health_page.render(shp.ctx(state_dir_hostile))
    escaped_prefix = layout.escape_html(hostile_prefix)
    expected_href_h = 'href="%s"' % (health_page.RESOLVE_LINK_HREF_TEMPLATE % escaped_prefix)
    expected_aria_h = 'aria-label="%s"' % (health_page.RESOLVE_LINK_ARIA_TEMPLATE % escaped_prefix)
    assert rendered_hostile.count(expected_href_h) == 2, (
        "expected the escaped href exactly twice, got %d" % rendered_hostile.count(expected_href_h))
    assert rendered_hostile.count(expected_aria_h) == 2, (
        "expected the escaped aria-label exactly twice, got %d" % rendered_hostile.count(expected_aria_h))
    assert hostile_prefix not in rendered_hostile, (
        "expected no raw hostile prefix anywhere in the rendered page")
    assert "<x>" not in rendered_hostile, (
        "expected the hostile prefix's angle bracket to never reach the output raw")


# ==========================================================================
# Health still gains no form/state-changing control (phase 13)
# ==========================================================================


def _render_health_normal(state_dir):
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    return health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))


def _render_health_anomaly(state_dir):
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    return health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))


def _render_health_source_fault(state_dir):
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    return health_page.render(shp.ctx(state_dir))


def _render_health_empty(state_dir):
    return health_page.render(shp.ctx(state_dir))


_HEALTH_RENDER_STATES = {
    "normal": _render_health_normal,
    "anomaly": _render_health_anomaly,
    "source_fault": _render_health_source_fault,
    "empty": _render_health_empty,
}


@pytest.mark.parametrize("state_name", sorted(_HEALTH_RENDER_STATES))
def test_health_still_has_no_form_and_no_button_in_any_state(tmp_path, state_name):
    """companion/pages/health_page.py's render() emits zero <form> and zero <button> elements in
    every seeded state (normal, anomaly, source-fault, empty) — Health still gains no
    state-changing (form-submitting) control (phase 13, ; rewritten from a
    health_page.py source-text grep onto the parsed rendered output, by
     — the legacy check's own "exactly one '<button' occurrence" was a docstring
    mention in the SOURCE, never rendered markup: health_page.render() returns a content
    fragment only, with no shared nav chrome, so the true rendered contract has no allowed
    exception at all)"""
    state_dir = str(tmp_path)
    rendered = _HEALTH_RENDER_STATES[state_name](state_dir)
    doc = parse_html(rendered)
    assert doc.find_all("form") == [], (
        "expected zero <form> elements in the %r state, found %r"
        % (state_name, doc.find_all("form")))
    assert doc.find_all("button") == [], (
        "expected zero <button> elements in the %r state, found %r"
        % (state_name, doc.find_all("button")))


def test_quick_260902_gjj_muted_captions_compose_section_caption(tmp_path, css_text):
    """the battery heading's sibling caption <p> (retargeted from the retired trailing <span>)
    and the Unresolved-prefixes read-only note both compose
    section-caption with their existing sizing class, and style.css's .section-caption still declares
    exactly one property at the file's single 70% muted strength"""
    # Pins the markup pair AND the single muted strength together, so a
    # future edit cannot satisfy one half while forking the other. The
    # caption now lives in a SIBLING <p> immediately after </h2>, not the
    # heading's own retired trailing <span>.
    state_dir = str(tmp_path)
    rendered = health_page.render(shp.ctx(state_dir))
    heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(_battery_section_heading())
    heading_at = rendered.index(heading_marker)
    after_heading = rendered[heading_at + len(heading_marker):]
    assert after_heading.startswith('<p class="text-label section-caption">'), (
        "expected the battery heading's sibling caption <p> to compose text-label with "
        "section-caption immediately after </h2>, got %r" % after_heading[:80])

    # phase 13 (): the reworded note contains apostrophes, which
    # escape_html() renders as &#x27; — locate the escaped form, not the
    # raw Python literal.
    note_at = rendered.index(layout.escape_html(health_page._READ_ONLY_NOTE))
    note_open = rendered.rindex("<p", 0, note_at)
    note_tag = rendered[note_open:rendered.index(">", note_open) + 1]
    assert 'class="text-body section-caption"' in note_tag, (
        "expected the read-only note's own <p> to compose text-body with section-caption, got %r"
        % note_tag)

    decls = declarations_for(css_text, ".section-caption")
    assert len(decls) == 1 and decls.get("color") == (
        "color-mix(in srgb, var(--color-text) 70%, transparent)"), (
        "expected .section-caption to still declare exactly one property, the file's single "
        "70%% muted color-mix, got %r" % decls)


def test_migrated_cards_have_independent_failure_isolation(tmp_path):
    """corrupting only the database leaves the registry card rendering while the stats card degrades, and
    vice versa"""
    # The registry read (poll_loop.load_poll_state(), a filesystem/JSON
    # failure mode) and the stats read (_safe_query(), a SQLite failure
    # mode) must degrade independently — corrupting one source must never
    # take down the other card.
    db_broken = str(tmp_path / "db-broken")
    with history_db.open_db(db_broken):
        pass
    dbs = [f for f in os.listdir(db_broken) if f.endswith(".db")]
    assert dbs, "expected a database file to have been created"
    with open(os.path.join(db_broken, dbs[0]), "wb") as fh:
        fh.write(b"not a sqlite file at all")
    shp.seed_unresolved_prefixes(db_broken, {
        "ABC": {"count": 2, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
    })
    rendered = health_page.render(shp.ctx(db_broken))
    assert "ABC" in rendered, (
        "expected the registry rows to still render when only the database is broken")
    assert health_page.HEALTH_UNAVAILABLE_TEXT in rendered, (
        "expected the stats card to show the unavailable copy when the database is broken")

    registry_broken = str(tmp_path / "registry-broken")
    now = shp.now()
    shp.seed_runway_events(registry_broken, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    poll_state_path = os.path.join(registry_broken, "poll_state.json")
    with open(poll_state_path, "w") as fh:
        fh.write("not valid json {")
    rendered2 = health_page.render(shp.ctx(registry_broken, now_value=shp.iso(now)))
    assert "100.0% resolved" in rendered2, (
        "expected the resolution-rate stats to still render when only the registry file is malformed")
    assert health_page._NO_GAPS_HEADING in rendered2, (
        "expected the registry to degrade to its empty/no-gaps state, not crash the page")


def test_read_health_inputs_keeps_stats_separate(tmp_path):
    """_read_health_inputs() carries exactly nine keys — device_config and registry_rows now join it for
    severity's sake — while the stats read alone stays a separate call in
    render()"""
    inputs = health_page._read_health_inputs(str(tmp_path), shp.iso(shp.now()))
    expected_keys = {
        "device_health", "pipeline_ts", "last_detection", "source_fault_raw",
        "trend_rows", "daily_rows", "corroboration_counts",
        "device_config", "registry_rows",
    }
    assert set(inputs.keys()) == expected_keys, (
        "expected _read_health_inputs() to carry exactly these nine keys, got %r"
        % (set(inputs.keys()),))
    assert not any("stat" in k for k in inputs.keys()), (
        "D-11: the stats read must stay a separate call in render(), not join this dict")


def test_battery_section_keeps_everything_after_the_move(tmp_path):
    """the battery-trend section keeps its own status modifier (retargeted from the retired badge, quick
    task), readout, and single script tag after moving out of the grid"""
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    assert ">%s<" % _battery_section_heading() in rendered, (
        "expected the battery heading's own text inside an <h2>")
    assert "battery-trend-section--ok" in rendered, (
        "expected the battery-trend section's own healthy status modifier to survive the move")
    assert health_page.BATTERY_READOUT_ID in rendered, "expected the readout element id to survive the move"
    assert rendered.count("<script") == 1, (
        "expected exactly one <script occurrence, got %d" % rendered.count("<script"))
    assert health_page.BATTERY_TREND_SCRIPT_SRC in rendered, (
        "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>")
    # Slice to the battery section's own boundaries (its own matching
    # </section>, not "rest of the page") — the surviving tiles elsewhere
    # on the page would otherwise make a whole-tail "no stat-tile" search
    # trivially fail.
    section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    section_end = rendered.index("</section>", section_start) + len("</section>")
    section_html = rendered[section_start:section_end]
    assert "stat-tile" not in section_html, "the battery-trend section must carry no stat-tile class"


def test_battery_heading_is_short_and_precision_lives_in_a_sibling_caption(tmp_path):
    """the battery-trend heading carries ONLY its short fixed text (no inline precision span),
    immediately followed by a sibling <p class="text-label section-caption"> carrying
    _battery_trend_caption()'s own text, itself followed by the chart/table body —
    index(h2) < index(caption) < index(body)"""
    # The <h2> must carry ONLY its short, fixed, window-derived text (no
    # inline precision span); the precision _battery_trend_caption()
    # computes lives in a SIBLING <p class="text-label section-caption">
    # immediately after </h2>, itself followed by the chart/table body.
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))

    heading_text = _battery_section_heading()
    precision_text = health_page._battery_trend_caption(
        [{"ts": shp.iso(base - timedelta(minutes=1)), "battery_mv": 4200},
         {"ts": shp.iso(base), "battery_mv": 4190}],
        None)
    heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(heading_text)
    assert heading_marker in rendered, "expected the fixed heading marker %r, got none" % (heading_marker,)
    assert layout.escape_html(precision_text) not in rendered[
        rendered.index(heading_marker):rendered.index(heading_marker) + len(heading_marker)], (
        "the heading itself must not carry the precision text")

    heading_at = rendered.index(heading_marker)
    caption_marker = '<p class="text-label section-caption">%s</p>' % layout.escape_html(precision_text)
    caption_at = rendered.index(caption_marker)
    assert heading_at < caption_at, "expected the heading to precede its sibling caption"
    assert not rendered[heading_at + len(heading_marker):caption_at].strip(), (
        "expected the caption <p> to sit IMMEDIATELY after </h2>, found intervening markup %r"
        % rendered[heading_at + len(heading_marker):caption_at])

    # The chart/table body (the <details class="readings-disclosure"> that
    # always renders, chart or no chart) follows the caption.
    body_at = rendered.index('<details class="readings-disclosure"', caption_at)
    assert caption_at < body_at, "expected the caption to precede the chart/table body"


def test_battery_heading_equals_template_times_window_in_both_languages(tmp_path):
    """the battery-trend heading's rendered text equals i18n.t_lang(BATTERY_SECTION_HEADING_TEMPLATE,
    lang) % (BATTERY_TREND_WINDOW_DAYS // 30) in both English and French — a relationship against
    the real constants, not a typed literal"""
    # A RELATIONSHIP against the real constants, never a typed
    # "Batterie · 3 mois" literal, proven in both languages so a future
    # edit to either the template or BATTERY_TREND_WINDOW_DAYS is caught
    # here rather than only in English.
    state_dir = str(tmp_path)
    for lang in ("en", "fr"):
        try:
            prefs.set_request_prefs(lang=lang)
            rendered = health_page.render(shp.ctx(state_dir))
        finally:
            prefs.set_request_prefs(lang="en")
        expected = i18n.t_lang(health_page.BATTERY_SECTION_HEADING_TEMPLATE, lang) % (
            health_page.BATTERY_TREND_WINDOW_DAYS // 30)
        marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(expected)
        assert marker in rendered, (
            "%s: expected the heading to equal i18n.t_lang(BATTERY_SECTION_HEADING_TEMPLATE, lang) "
            "%% (BATTERY_TREND_WINDOW_DAYS // 30) == %r, marker %r not found" % (lang, expected, marker))


def test_battery_trend_caption_all_three_branches_render_in_sibling_caption(tmp_path):
    """all three _battery_trend_caption() branches (usable daily series, no rows at all, sub-two-day
    raw series) render their own exact text inside the sibling caption <p>, never inside the
    heading"""
    base = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)

    def _caption_paragraph(rendered):
        heading_text = _battery_section_heading()
        heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(heading_text)
        after = rendered[rendered.index(heading_marker) + len(heading_marker):]
        m = re.match(r'<p class="text-label section-caption">(.*?)</p>', after)
        assert m is not None, "expected a sibling caption <p> immediately after </h2>"
        return m.group(1)

    # Branch 1: a usable daily series (>= 2 Paris-day buckets) — the
    # 3-month/daily-average framing.
    daily_dir = str(tmp_path / "daily")
    readings = []
    for day, mv in enumerate((4000, 4100, 4200)):
        readings.append((shp.iso(base - timedelta(days=day)), mv))
    shp.seed_device_health(daily_dir, readings)
    rendered = health_page.render(shp.ctx(daily_dir, now_value=shp.iso(base)))
    expected = layout.escape_html(i18n.t("Last 3 months, daily average"))
    assert _caption_paragraph(rendered) == expected, (
        "daily-series branch: expected caption %r" % expected)

    # Branch 2: no rows at all (and the DB-unavailable case, which shares
    # the same 3-month framing) — an empty state dir.
    empty_dir = str(tmp_path / "empty")
    rendered = health_page.render(shp.ctx(empty_dir, now_value=shp.iso(base)))
    expected = layout.escape_html(i18n.t("Last 3 months, daily average"))
    assert _caption_paragraph(rendered) == expected, "no-rows branch: expected caption %r" % expected

    # Branch 3: a sub-two-day raw series (the day-1 fallback) — the real
    # reading count, never BATTERY_TREND_LIMIT.
    sameday_dir = str(tmp_path / "sameday")
    sameday_readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(sameday_dir, sameday_readings)
    rendered = health_page.render(shp.ctx(sameday_dir, now_value=shp.iso(base)))
    expected = layout.escape_html(i18n.t("Latest %d readings") % len(sameday_readings))
    assert _caption_paragraph(rendered) == expected, "sub-two-day branch: expected caption %r" % expected


def test_battery_readout_precedes_chart_class_list_and_live_region(tmp_path, battery_trend_js):
    """the battery readout precedes the chart and the script tag inside the battery-trend section, carries
    its single expected class plus role="status" plus both value/detail spans, and battery-trend.js
    still looks it up by id"""
    # The readout is now the section's scannable headline number, ahead
    # of the chart.
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    section_end = rendered.index("</section>", section_start) + len("</section>")
    section_html = rendered[section_start:section_end]

    readout_open = section_html.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
    readout_tag_close = section_html.index(">", readout_open) + 1
    readout_tag = section_html[readout_open:readout_tag_close]
    readout_close = section_html.index("</p>", readout_open) + len("</p>")
    readout_html = section_html[readout_open:readout_close]
    # The sparkline SVG is distinguishable from the section heading's icon
    # <svg class="icon"> by its own '<svg class="sparkline__canvas"'
    # opening — the heading icon carries no such class.
    sparkline_at = section_html.index('<svg class="sparkline__canvas"')
    script_at = section_html.index("<script")
    assert readout_open < sparkline_at < script_at, (
        "expected the readout to precede the sparkline, and the sparkline to precede the script "
        "tag, inside the battery-trend section")

    assert 'class="battery-readout"' in readout_tag, (
        "expected the readout's class list to be exactly 'battery-readout', got %r" % readout_tag)
    assert 'role="status"' in readout_tag, "expected role=\"status\" on the readout"
    assert 'battery-readout__value' in readout_html, "expected the readout's value span inside the readout"
    assert 'battery-readout__detail' in readout_html, "expected the readout's detail span inside the readout"

    assert health_page.BATTERY_READOUT_ID in battery_trend_js, (
        "expected battery-trend.js to still look up BATTERY_READOUT_ID's literal value — that "
        "property is what makes the reposition safe")


def test_battery_section_class_is_styled_in_stylesheet(css_text):
    """health_page.BATTERY_SECTION_CLASS is guarded against silent drift from companion/static/style.css"""
    assert rules_with_selector(css_text, "." + health_page.BATTERY_SECTION_CLASS), (
        "companion/static/style.css no longer styles BATTERY_SECTION_CLASS")


_CARD_STATUS_COMPONENTS = ("battery-trend-section", "page-section")
_CARD_STATUS_LEVELS = ("ok", "warn", "error")


def test_quick_260902_gjj_card_status_borders_render_correct_modifiers(tmp_path, css_text):
    """the battery-trend and Unresolved-prefixes cards each carry the status modifier
    layout.card_status_class() derives from battery_status()/coverage_status()'s own real return
    value on the same rows, the Resolution-statistics card carries none, and style.css declares all
    three doubled-form status rules for both card components"""
    # A real rendered page, with a seeded battery drop and a seeded
    # non-empty registry, proves the battery-trend and Unresolved-
    # prefixes cards each carry the modifier layout.card_status_class()
    # derives from the SAME function. Each section is located by its own
    # heading constant, never a document-wide substring search.
    state_dir = str(tmp_path)
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ]
    shp.seed_device_health(state_dir, readings)
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    # The Resolution-statistics card is omitted entirely when its window
    # holds zero rows — seed one so the card (and its "no status
    # modifier" assertion below) still renders.
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    battery_state = health_page.battery_status([
        {"ts": shp.iso(now), "battery_mv": readings[1][1]},
        {"ts": shp.iso(now - timedelta(minutes=1)), "battery_mv": readings[0][1]},
    ])
    assert battery_state == "warn", "expected the seeded battery fixture to compute a warn verdict (D-05 demotion)"
    battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    battery_tag = rendered[battery_open:rendered.index(">", battery_open) + 1]
    expected_battery_modifier = layout.card_status_class(health_page.BATTERY_SECTION_CLASS, battery_state)
    assert expected_battery_modifier in battery_tag, (
        "expected the battery-trend section's own tag to carry %r, got %r"
        % (expected_battery_modifier, battery_tag))

    coverage_state = health_page.coverage_status([("ABC", 1, "", "", "")])
    assert coverage_state == "warn", "expected the seeded registry fixture to compute a warn verdict"
    registry_heading_at = rendered.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
    registry_open = rendered.rindex('<section class="', 0, registry_heading_at)
    registry_tag = rendered[registry_open:rendered.index(">", registry_open) + 1]
    expected_registry_modifier = layout.card_status_class("page-section", coverage_state)
    assert expected_registry_modifier in registry_tag, (
        "expected the Unresolved-prefixes section's own tag to carry %r, got %r"
        % (expected_registry_modifier, registry_tag))
    assert "page-section--nested" in registry_tag, (
        "expected the registry card to keep its pre-existing nested modifier")

    stats_heading_at = rendered.index(">%s</h2>" % health_page.STATS_SECTION_HEADING)
    stats_open = rendered.rindex('<section class="', 0, stats_heading_at)
    stats_tag = rendered[stats_open:rendered.index(">", stats_open) + 1]
    assert stats_tag == '<section class="page-section page-section--nested">', (
        "expected the Resolution-statistics card to carry no status modifier at all (it computes "
        "no verdict), got %r" % stats_tag)

    for comp in _CARD_STATUS_COMPONENTS:
        for status in _CARD_STATUS_LEVELS:
            sel = ".%s.%s--%s" % (comp, comp, status)
            decls = declarations_for(css_text, sel)
            border_top = decls.get("border-top", "")
            assert "var(--color-status-%s)" % status in border_top and "3px" in border_top, (
                "expected the doubled-form status rule %r's border-top to declare a 3px border "
                "in var(--color-status-%s), got %r" % (sel, status, decls))


def _rule_index(rules, selector):
    for index, rule in enumerate(rules):
        if selector in rule.selectors:
            return index
    raise AssertionError("no rule found with selector %r" % (selector,))


_CARD_STATUS_HOVER_ORDER_COMPONENTS = (
    ("battery-trend-section", ("ok", "warn", "error")),
    ("page-section", ("ok", "warn", "error")),
    ("stat-tile", ("ok", "warn", "error", "accent")),
)
_HOVER_SELECTOR = {
    "battery-trend-section": ".battery-trend-section:hover",
    "page-section": ".page-section:hover",
    "stat-tile": ".stat-tile:not(.frame-strip):hover",
}


def test_card_status_modifiers_survive_hover_source_order(css_text):
    """every card-status modifier selector (battery-trend-section, page-section, and stat-tile) sits
    after that component's own :hover/:focus-within rule in the served stylesheet's rule order, so
    the status border survives hover and keyboard focus rather than losing to the hover shorthand"""
    # The load-bearing fact every card-status-border rule depends on:
    # each doubled-form status modifier selector must sit AFTER that
    # component's own ":hover, :focus-within" rule, or the hover rule's
    # `border-color: transparent` shorthand (equal specificity, later
    # rule wins) silently erases the status colour on hover or focus.
    rules = css_rules(css_text)
    for comp, statuses in _CARD_STATUS_HOVER_ORDER_COMPONENTS:
        hover_index = _rule_index(rules, _HOVER_SELECTOR[comp])
        for status in statuses:
            sel = ".%s.%s--%s" % (comp, comp, status)
            sel_index = _rule_index(rules, sel)
            assert sel_index > hover_index, (
                "%r must come after %r in the stylesheet's rule order, or hovering/focusing the "
                "card erases its status border" % (sel, _HOVER_SELECTOR[comp]))


def test_quick_260902_gjj_dot_removal_scoped_not_global(tmp_path):
    """the battery-trend and Unresolved-prefixes cards render no dot-label anywhere inside their own
    boundaries, the Corroboration tile's three dots survive untouched (proving the removal is scoped,
    not global), and BATTERY_STATUS_LABEL/_battery_badge_block are both gone via hasattr, never a
    source grep"""
    # Proves the two dot removals are SCOPED to the battery-trend and
    # Unresolved-prefixes cards, not a global regression that also strips
    # the three surviving Corroboration dots. Without the third
    # (positive) assertion below, the first two would pass even if
    # status_dot() itself had been broken everywhere.
    state_dir = str(tmp_path)
    now = shp.now()
    readings = [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ]
    shp.seed_device_health(state_dir, readings)
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": True}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    battery_open = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    battery_close = rendered.index("</section>", battery_open) + len("</section>")
    battery_slice = rendered[battery_open:battery_close]
    assert "dot-label" not in battery_slice, (
        "the battery-trend card must render no dot-label — its own badge is retired")

    registry_heading_at = rendered.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
    registry_open = rendered.rindex('<section class="', 0, registry_heading_at)
    registry_close = rendered.index("</section>", registry_open) + len("</section>")
    registry_slice = rendered[registry_open:registry_close]
    assert "dot-label" not in registry_slice, (
        "the Unresolved-prefixes card must render no dot-label — its own dot is retired")

    # The tile's visible caption is the plain-language
    # CORROBORATION_TILE_LABEL, not the literal "Corroboration" (which
    # only survives as this tile's caption_title tooltip).
    corrob_at = rendered.index(">%s<" % layout.escape_html(health_page.CORROBORATION_TILE_LABEL))
    corrob_open = rendered.rindex('<div class="stat-tile ', 0, corrob_at)
    corrob_close = rendered.index("</div>", corrob_open) + len("</div>")
    corrob_slice = rendered[corrob_open:corrob_close]
    assert "dot-label" in corrob_slice, (
        "expected the Corroboration tile's own dots to survive untouched — this check must fail "
        "if status_dot() itself breaks, not only if the two removals are wrong")

    assert not hasattr(health_page, "BATTERY_STATUS_LABEL"), (
        "expected health_page to no longer define the retired BATTERY_STATUS_LABEL")
    assert not hasattr(health_page, "_battery_badge_block"), (
        "expected health_page to no longer define the retired _battery_badge_block")


def test_quick_260901_tsa_css_dom_contract_guard(css_text):
    """style.css's .section-intro / .section-intro > p / .stat-tile__value .mono / .battery-readout rules
    each carry their load-bearing declaration, and .mono precedes .battery-readout in the
    stylesheet's rule order"""
    # The cross-file guard for every new/edited style.css rule this
    # markup depends on.
    expectations = (
        (".section-intro", "display", "flex"),
        (".section-intro > p", "margin", "0"),
        (".stat-tile__value .mono", "font-weight", "inherit"),
        (".battery-readout", "font-weight", "var(--weight-semibold)"),
    )
    for selector, prop, expected_value in expectations:
        decls = declarations_for(css_text, selector)
        assert decls.get(prop) == expected_value, (
            "expected %r's %r declaration to be %r, got %r" % (selector, prop, expected_value, decls))

    # The one source-order fact the Emphasis promotion actually rests on:
    # .mono's rule must precede .battery-readout's rule, since the
    # promotion wins by SOURCE ORDER (a later same-specificity rule), not
    # by selector specificity.
    rules = css_rules(css_text)
    assert _rule_index(rules, ".mono") < _rule_index(rules, ".battery-readout"), (
        "expected .mono's rule to precede .battery-readout's — moving .battery-readout above "
        ".mono would silently return the readout to regular weight")


def test_dashboard_grid_stretches_same_row_tiles(css_text):
    """style.css's .dashboard-grid declares an explicit cross-axis stretch (the reversal) and no
    longer declares start, and .dashboard-shell's own separate start-aligned declaration (sticky
    sidebar) is the file's only remaining one"""
    # .dashboard-grid must declare the stretch alignment (the
    # reversal) and must not declare the start alignment, and the file's
    # only remaining start-aligned declaration must be the desktop
    # .dashboard-shell rule's own.
    grid_decls = declarations_for(css_text, ".dashboard-grid")
    assert grid_decls.get("align-items") == "stretch", (
        "expected .dashboard-grid to declare align-items: stretch — a start-aligned .dashboard-"
        "grid returns the ragged-height tiles the developer measured (107.7 / 261.8 / 140.4px in "
        "one row), got %r" % grid_decls)

    start_count = sum(
        1 for rule in css_rules(css_text) for prop, value in rule.declarations
        if prop == "align-items" and value == "start")
    assert start_count == 1, (
        "expected exactly one remaining align-items: start declaration in the whole stylesheet, "
        "got %d" % start_count)

    shell_decls = declarations_for(
        css_text, ".dashboard-shell", at_rules=("@media (min-width: 960px)",))
    assert shell_decls.get("align-items") == "start", (
        "expected the one remaining align-items: start to be inside .dashboard-shell — D-21's "
        "sticky sidebar needs it; a different selector holding it would mean the UXA-06 reversal "
        "missed something")


def test_data_table_th_has_symmetric_nonzero_padding(css_text):
    """style.css's .data-table th declares a symmetric, non-zero vertical padding via the two-value shorthand"""
    # Pins both halves of the contract so a future edit cannot silently
    # return the top to zero (reintroducing the opaque-background-starts-
    # at-the-glyph-tops defect) or drift the top and bottom values apart.
    # Parses the declaration's own VALUE, not the whole rule body.
    decls = declarations_for(css_text, ".data-table th")
    assert "padding-top" not in decls and "padding-bottom" not in decls, (
        "expected the two-value shorthand form, not separate padding-top/padding-bottom "
        "declarations")
    padding = decls.get("padding")
    assert padding is not None, "expected a `padding` declaration inside `.data-table th`"
    parts = padding.split()
    assert len(parts) == 2, (
        "expected a two-value (vertical horizontal) padding shorthand, got %r" % (padding,))
    top_raw, _horizontal = parts
    assert top_raw.endswith("px") and top_raw[:-2].isdigit(), (
        "expected the top/bottom padding value to be a bare px literal, got %r" % top_raw)
    top_px = int(top_raw[:-2])
    assert top_px > 0, (
        "expected a non-zero top padding on .data-table th — zero top padding is the real "
        "mechanism behind the sticky header's opaque background starting exactly at the glyph "
        "tops")


def test_nested_heading_tier_promoted_to_sans_semibold_emphasis_role(tmp_path, css_text):
    """exactly the two migrated cards carry page-section--nested (located by their own heading constants),
    the source-fault block never carries it even when it renders, both .section-intro headings are
    untouched, and style.css's nested-heading rule declares the sans family, the Body size (16px)
    and the semibold weight explicitly (plus its retained bottom margin), sitting below a
    .text-heading section-heading tier confirmed still 22px/regular at the token level too"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    # Seed one runway event so both migrated cards still render,
    # unrelated to what this check is actually about.
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    assert rendered.count("page-section--nested") == 2, (
        "expected exactly two page-section--nested occurrences (the two migrated cards), got %d"
        % rendered.count("page-section--nested"))

    for heading in (health_page.UNRESOLVED_SECTION_HEADING, health_page.STATS_SECTION_HEADING):
        heading_marker = ">%s</h2>" % heading
        heading_at = rendered.index(heading_marker)
        section_open = rendered.rindex('<section class="', 0, heading_at)
        section_tag = rendered[section_open:rendered.index(">", section_open) + 1]
        assert "page-section--nested" in section_tag, (
            "expected the <section> carrying %r to declare page-section--nested, got %r"
            % (heading, section_tag))

    assert '<section class="page-section banner banner--anomaly">' in rendered, (
        "expected the source-fault block itself to render for this fixture")
    assert 'class="page-section banner banner--anomaly page-section--nested"' not in rendered, (
        "the source-fault block must never carry page-section--nested")

    for section_id, heading in (
            (health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING),
            (health_page.SERVER_DATA_SECTION_ID, health_page.SERVER_DATA_SECTION_HEADING)):
        intro_marker = '<h2 id="%s" class="text-heading">%s</h2>' % (section_id, layout.escape_html(heading))
        assert intro_marker in rendered, "expected %r's own .section-intro heading to be unmodified" % heading

    nested_decls = declarations_for(css_text, ".page-section--nested > h2")
    assert ".battery-trend-section > h2" in next(
        rule.selectors for rule in css_rules(css_text) if ".page-section--nested > h2" in rule.selectors), (
        "expected the promoted rule's selector list to still cover .battery-trend-section > h2")
    assert nested_decls.get("margin-bottom") == "var(--space-md)", (
        "expected the promoted rule to still declare its retained 260902-bl2 bottom margin — a "
        "missing bottom margin means this re-promotion over-reached and took the independently-"
        "justified spacing fix with it, got %r" % nested_decls)
    assert nested_decls.get("font-family") == "var(--font-ui)", (
        "expected the nested-heading rule to declare font-family: var(--font-ui) — D-09's second "
        "reversal moves this tier onto the sans Emphasis role, got %r" % nested_decls)
    assert nested_decls.get("font-size") == "var(--font-body-size)", (
        "expected the nested-heading rule to declare font-size: var(--font-body-size) (16px) — "
        "the same Emphasis-role size .stat-tile__value already uses, not a new fifth size, got %r"
        % nested_decls)
    assert nested_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected the nested-heading rule to declare font-weight: var(--weight-semibold) — a "
        "font-weight missing here means the D-09 re-promotion did not land, got %r" % nested_decls)

    heading_decls = declarations_for(css_text, ".text-heading")
    assert heading_decls.get("font-size") == "var(--font-heading-size)", (
        "expected .text-heading to still declare --font-heading-size — the section heading tier "
        "this nested title now sits below has no fallback of its own, got %r" % heading_decls)
    assert heading_decls.get("font-weight") == "var(--weight-regular)", (
        "expected .text-heading to stay --weight-regular — the section-heading tier must stay "
        "regular so the semibold nested card title below it reads as a distinct third tier, not "
        "more of the same weight, got %r" % heading_decls)
    tokens = custom_properties(css_text, ":root")
    assert tokens.get("--font-heading-size") == "22px", (
        "expected --font-heading-size to be 22px in :root — D-10 grew the section heading tier "
        "from 20px to 22px as part of the same ladder this rule is the bottom rung of, got %r"
        % tokens)


def test_stat_tile_caption_joins_the_unified_label_voice(css_text):
    """style.css's .stat-tile__caption converges on the one unified 12px uppercase label voice — sans
    family, 12px size, semibold weight, uppercase transform and 0.06em tracking all declared explicitly,
    with no serif token named anywhere in its rule body — while .stat-tile__value keeps its own untouched
    Emphasis-role size/weight, the nested card title stays on its own sans-semibold Body-size
    declarations, the shared h1/h2/h3/legend/.text-heading serif rule keeps its regular weight, and
    the token table reads 14/16/22px"""
    # The caption converges, together with .data-table th,
    # .data-card__label, .filter-bar__count, .banner__pill and
    # .airline-card__chip, on the one unified label voice: sans, 12px,
    # semibold, uppercase, 0.06em tracking.
    caption_decls = declarations_for(css_text, ".stat-tile__caption")
    assert caption_decls.get("font-family") == "var(--font-ui)", (
        "expected .stat-tile__caption to declare font-family: var(--font-ui) — D-13 retires the "
        "serif Label-role exception this caption used to be, got %r" % caption_decls)
    assert all("var(--font-serif)" not in value for value in caption_decls.values()), (
        "expected .stat-tile__caption's rule body to no longer name the serif token at all — a "
        "serif reference reappearing here is the retired Label-role exception returning, got %r"
        % caption_decls)
    assert caption_decls.get("font-size") == "12px", (
        "expected .stat-tile__caption to declare font-size: 12px — the unified label voice's own "
        "size, got %r" % caption_decls)
    assert caption_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected .stat-tile__caption to declare font-weight: var(--weight-semibold) — one of the "
        "unified label voice's four properties, got %r" % caption_decls)
    assert caption_decls.get("text-transform") == "uppercase", (
        "expected .stat-tile__caption to declare text-transform: uppercase — one of the unified "
        "label voice's four properties, got %r" % caption_decls)
    assert caption_decls.get("letter-spacing") == "0.06em", (
        "expected .stat-tile__caption to declare letter-spacing: 0.06em — one of the unified "
        "label voice's four properties, got %r" % caption_decls)

    value_decls = declarations_for(css_text, ".stat-tile__value")
    assert value_decls.get("font-size") == "var(--font-body-size)", (
        "expected .stat-tile__value to stay on the Body size (16px) — Finding 4's own contract, "
        "got %r" % value_decls)
    assert value_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected .stat-tile__value to stay semibold — Finding 4's own contract, got %r" % value_decls)

    # The nested card title's demotion is re-promoted a second time,
    # deliberately, as the bottom rung of the full type ladder.
    nested_decls = declarations_for(css_text, ".page-section--nested > h2")
    assert nested_decls.get("font-size") == "var(--font-body-size)", (
        "expected the nested card title to declare font-size: var(--font-body-size) (16px) — "
        "D-09's second reversal promotes it onto the sans Emphasis role, got %r" % nested_decls)
    assert nested_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected the nested card title to declare font-weight: var(--weight-semibold) — D-09's "
        "second reversal promotes it onto the sans Emphasis role, got %r" % nested_decls)

    heading_decls = declarations_for(css_text, ".text-heading")
    assert heading_decls.get("font-weight") == "var(--weight-regular)", (
        "expected the shared heading rule to stay regular weight — the section heading and the "
        "reverted nested card title both inherit this, and neither should ever carry its own "
        "weight override again, got %r" % heading_decls)

    # Token values themselves, so this check fails loudly (not silently)
    # if a future edit changes what 14/16/22 actually mean.
    tokens = custom_properties(css_text, ":root")
    for name, expected in (
            ("--font-label-size", "14px"),
            ("--font-body-size", "16px"),
            ("--font-heading-size", "22px")):
        assert tokens.get(name) == expected, "expected %s to be %s in :root, got %r" % (name, expected, tokens)


def _margin_bottom_token_px(css_text, selector, tokens):
    """The `var(--token)` name referenced by `selector`'s `margin-bottom`
    (or the last `var()` in a `margin` shorthand), and that token's own
    `:root` value as an int px count — both derived from `declarations_
    for()`'s already-structurally-extracted declaration VALUE, never from
    a second raw scan of the stylesheet text."""
    decls = declarations_for(css_text, selector)
    value = decls.get("margin-bottom") or decls.get("margin")
    assert value is not None, "expected %r to declare margin-bottom (or margin)" % (selector,)
    match = re.search(r"var\(--([a-z0-9-]+)\)", value)
    assert match is not None, "expected %r's margin declaration to reference a var() token, got %r" % (
        selector, value)
    token_name = "--" + match.group(1)
    token_value = tokens.get(token_name)
    assert token_value is not None and token_value.endswith("px"), (
        "expected %r to resolve to a real px token value in :root, got %r" % (token_name, token_value))
    return token_name, int(token_value[:-2])


def test_two_tier_hierarchy_carried_by_layout_not_type(tmp_path, css_text):
    """Health's two-tier hierarchy (section headings vs. the cards nested inside them) still reads
    apart with no font-size or font-weight distinction between the tiers: every level-2 heading (Battery
    trend, Unresolved prefixes, Resolution statistics) sits inside a bordered card <section>, both level-1
    headings (Screen, Server & data) sit inside the plain .section-intro row with no card class, a
    .dashboard-grid always intervenes between a level-1 heading and the first level-2 card in its own
    section, and the four spacing tiers that now carry the distinction stay strictly ordered against
    their real :root token values — in both the empty and seeded state"""
    # With font-size no longer distinguishing Health's two structural
    # tiers, this check pins the mechanism that replaced it — containment
    # and spacing, read from the real rendered DOM and cascade, not
    # asserted from memory.
    for seeded in (False, True):
        state_dir = str(tmp_path / ("seeded-%s" % seeded))
        now = shp.now()
        if seeded:
            shp.seed_device_health(state_dir, [
                (shp.iso(now - timedelta(minutes=3)), 4200),
                (shp.iso(now - timedelta(minutes=1)), 4190),
            ])
            shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
            shp.seed_unresolved_prefixes(state_dir, {
                "JAF": {"count": 4, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                        "example_callsign": "JAF412"},
            })
        rendered = health_page.render(shp.ctx(state_dir, now_value=shp.iso(now)))

        for section_id, heading in (
                (health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING),
                (health_page.SERVER_DATA_SECTION_ID, health_page.SERVER_DATA_SECTION_HEADING)):
            marker = '<h2 id="%s" class="text-heading">%s</h2>' % (section_id, layout.escape_html(heading))
            marker_at = rendered.index(marker)
            wrapper_open = rendered.rindex('<div class="', 0, marker_at)
            wrapper_tag = rendered[wrapper_open:rendered.index(">", wrapper_open) + 1]
            assert "section-intro" in wrapper_tag, (
                "seeded=%s: expected %r's <h2> to sit inside the plain .section-intro row, got "
                "wrapper %r" % (seeded, heading, wrapper_tag))
            assert "page-section" not in wrapper_tag and "battery-trend-section" not in wrapper_tag, (
                "seeded=%s: %r's own wrapper must carry no card class, got %r" % (seeded, heading, wrapper_tag))

        # Task 2 (B3): the Resolution-statistics card is now
        # omitted entirely (no heading at all) when its window holds zero
        # rows.
        headings_to_check = [
            _battery_section_heading(),
            health_page.UNRESOLVED_SECTION_HEADING,
        ]
        if seeded:
            headings_to_check.append(health_page.STATS_SECTION_HEADING)
        else:
            assert health_page.STATS_SECTION_HEADING not in rendered, (
                "seeded=False: expected the empty Resolution-statistics section to be entirely "
                "absent (B3, 22-03-PLAN.md Task 2)")
        for heading in headings_to_check:
            heading_marker_at = rendered.index(">%s" % heading)
            section_open = rendered.rindex('<section class="', 0, heading_marker_at)
            section_tag = rendered[section_open:rendered.index(">", section_open) + 1]
            assert (
                "page-section--nested" in section_tag
                or health_page.BATTERY_SECTION_CLASS in section_tag), (
                "seeded=%s: expected %r's enclosing <section> to carry a card class "
                "(page-section--nested or %s), got %r"
                % (seeded, heading, health_page.BATTERY_SECTION_CLASS, section_tag))

        # Adjacency: a .dashboard-grid always sits between a level-1
        # heading's own .section-intro row and the first level-2 card in
        # that same section — the two tiers are never immediately adjacent
        # on screen.
        screen_intro_at = rendered.index('id="%s"' % health_page.SCREEN_SECTION_ID)
        screen_intro_close = rendered.index("</div>", screen_intro_at) + len("</div>")
        after_screen_intro = rendered[screen_intro_close:screen_intro_close + 40]
        assert after_screen_intro.startswith('<div class="dashboard-grid">'), (
            "seeded=%s: expected a .dashboard-grid immediately after the Screen section-intro "
            "row, got %r" % (seeded, after_screen_intro))
        server_intro_at = rendered.index('id="%s"' % health_page.SERVER_DATA_SECTION_ID)
        server_intro_close = rendered.index("</div>", server_intro_at) + len("</div>")
        after_server_intro = rendered[server_intro_close:server_intro_close + 40]
        assert after_server_intro.startswith('<div class="dashboard-grid">'), (
            "seeded=%s: expected a .dashboard-grid immediately after the Server & data "
            "section-intro row, got %r" % (seeded, after_server_intro))

    # Stylesheet half: the four spacing values that now carry the
    # hierarchy, read from their own rules by selector and asserted to
    # form the strictly ordered set the layout inspection derived —
    # section-transition > same-section card-to-card > heading-to-content
    # inside a card > a section-intro heading's own rhythm — against
    # :root's real token values.
    tokens = custom_properties(css_text, ":root")
    section_token, section_gap = _margin_bottom_token_px(css_text, ".battery-trend-section", tokens)
    card_token, card_gap = _margin_bottom_token_px(css_text, ".page-section", tokens)
    grid_token, grid_gap = _margin_bottom_token_px(css_text, ".dashboard-grid", tokens)
    head_token, head_gap = _margin_bottom_token_px(css_text, ".page-section--nested > h2", tokens)
    intro_token, intro_gap = _margin_bottom_token_px(css_text, ".text-heading", tokens)

    assert card_gap == grid_gap, (
        "expected .page-section and .dashboard-grid to share one same-section card-to-card value "
        "(%s=%dpx vs %s=%dpx) — the pair 260902-ep7 pinned" % (card_token, card_gap, grid_token, grid_gap))
    assert section_gap > card_gap > head_gap > intro_gap, (
        "expected the layout hierarchy's four spacing tiers to stay strictly ordered "
        "(section-transition %dpx > card-to-card %dpx > heading-to-content %dpx > section-intro "
        "rhythm %dpx) — this ordering is what now carries the two-tier hierarchy quick task "
        "260902-iag removed the type-scale distinction from"
        % (section_gap, card_gap, head_gap, intro_gap))
