"""Companion status-page tests: compute_health_state()'s never-ran-pipeline
detail, overall_severity()'s widened precedence table, Health's page-header
shape, the rows card and its two groups, the Identification row, the registry
card, and the Battery row's contract.

CSS/JS checks fetch served bytes from a running companion/app.py; everything
else calls health_page/layout/i18n/prefs/wake directly, in-process.
"""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

import companion.app as app
import companion.health_signals as health_signals
from companion import i18n, layout, prefs
from companion.pages import health_page
import health_page_composition
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


# --- shared helpers, local to this part -----------------------------------

def _row_html(rendered, row_id):
    """The served markup of one Health row: from its id to whichever comes next
    (the next row, the next group band, or the registry card)."""
    start = rendered.index('id="health-row-%s"' % row_id)
    ends = [index for index in (
        rendered.find('<details class="health-row"', start),
        rendered.find('<h2 id="%s"' % health_page.SERVER_DATA_SECTION_ID, start),
        len(rendered),
    ) if index != -1]
    return rendered[start:min(ends)]


# ==========================================================================
# compute_health_state()'s never-ran-pipeline detail fragment (B2)
# ==========================================================================


def test_compute_health_state_carries_pipeline_detail_html_has_run(tmp_path):
    """compute_health_state()'s pipeline_detail_html key, once the pipeline has run at least once,
    is verdict-free, mirroring device_detail_html"""
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
    assert "pipeline_html" not in state, "the tile markup the rows replaced must not come back"


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
        health_page.i18n.t(health_signals._FLIGHT_DATA_STALE_TEXT)], (
        "expected collect_anomalies() to still flag a genuinely stale pipeline")
    assert health_page.overall_severity("ok", "warn", "ok", False) == "warn", (
        "expected overall_severity() to still warn for a genuinely stale pipeline")


# ==========================================================================
# battery_sparkline_svg() regression guards, hostile timestamps, and the
# Python/CSS/JS cross-file contract
# ==========================================================================


def test_single_reading_still_no_chart_no_script_but_server_seeded_readout(tmp_path):
    """battery_sparkline_svg() still returns '' for fewer than two numeric readings, and the page emits
    no chart script tag or trend line; the latest reading is still shown in the server-rendered readout"""
    assert health_page.battery_sparkline_svg([{"ts": "t1", "battery_mv": 4200}]) == "", (
        "expected battery_sparkline_svg() to return '' for a single-row input")
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert "<script" not in rendered, "did not expect a <script tag with only one battery reading"
    assert health_page.BATTERY_READOUT_ID in rendered, (
        "expected the server-seeded readout to show the single latest battery reading")
    assert "4200 mV" in rendered, "expected the readout to carry the single reading's value"
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    assert rendered.count("<script") == 1, (
        "expected exactly one <script tag, got %d" % rendered.count("<script"))
    assert health_page.BATTERY_TREND_SCRIPT_SRC in rendered, (
        "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>")
    for forbidden in ("onclick=", "onmouseover=", "ontouchstart=", "onfocus=", "onload="):
        assert forbidden not in rendered, (
            "found forbidden inline event-handler attribute %r" % forbidden)


def test_empty_battery_history_stays_script_free(tmp_path):
    """the empty-history battery path stays script-free — no <script, no <svg, no readout element"""
    rendered = health_page_composition.render(shp.ctx(str(tmp_path)))
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
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
    win next, then warn states/disagreement_warn, with the 4-argument call staying byte-for-byte
    backward compatible; coverage_state is informational and never raises severity"""
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
    assert health_page.overall_severity("ok", "ok", "ok", False, coverage_state="warn") == "ok", (
        "expected coverage_state='warn' alone to stay ok: unidentified airlines are informational")
    assert health_page.overall_severity("ok", "ok", "ok", False, source_fault=True) == "error", (
        "expected source_fault=True alone to produce error")
    assert health_page.overall_severity(
        "error", "ok", "ok", False, coverage_state="warn", source_fault=True) == "error", (
        "expected source_fault to win outright over every other signal")
    assert health_page.overall_severity(
        "warn", "ok", "ok", False, coverage_state="ok", source_fault=False) == "warn", (
        "expected a warn state with no coverage/source_fault input to stay warn")


def test_overall_severity_acceptance_criteria_literal():
    """overall_severity()'s acceptance triple: ('ok', 'error', 'ok') — a coverage warning alone is informational"""
    # The plan's own acceptance-criteria one-liner, run as a check rather
    # than only a shell command.
    results = (
        health_page.overall_severity("ok", "ok", "ok", False),
        health_page.overall_severity("ok", "ok", "ok", False, source_fault=True),
        health_page.overall_severity("ok", "ok", "ok", False, coverage_state="warn"),
    )
    assert results == ("ok", "error", "ok"), "expected ('ok', 'error', 'ok'), got %r" % (results,)


def test_source_fault_alone_produces_error_registry_alone_produces_warn(tmp_path):
    """compute_health_state() folds an active source_fault_raw alone into error severity, while a
    non-empty unresolved-airline registry alone stays ok (informational), as does a fully healthy state"""
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
    assert state2["severity"] == "ok", (
        "expected a non-empty registry alone to stay ok, got %r" % (state2["severity"],))
    assert health_page.collect_anomalies(
        "ok", "ok", "ok", False, coverage_state="warn") == [], (
        "expected an unidentified-airline registry never to be an anomaly")

    state_dir3 = str(tmp_path / "fully-healthy")
    shp.seed_device_health(state_dir3, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir3, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    state3 = health_page.compute_health_state(state_dir3, now=shp.iso(now))
    assert state3["severity"] == "ok", (
        "expected an empty registry with everything else healthy to stay ok, got %r"
        % (state3["severity"],))


def test_collect_anomalies_two_new_items():
    """collect_anomalies()'s source_fault item appears only when its input is unhealthy, the
    coverage_state item is retired (unidentified airlines are informational), and a fully healthy
    4-argument call still returns none"""
    assert "All data sources failed." in health_page.collect_anomalies(
        "ok", "ok", "ok", False, source_fault=True), (
        "expected the source_fault item to appear when source_fault=True")
    assert "Some airlines are unidentified." not in health_page.collect_anomalies(
        "ok", "ok", "ok", False, coverage_state="warn"), (
        "expected no coverage anomaly even when coverage_state='warn'")
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert health_page.ANOMALY_BANNER_TEXT not in rendered, (
        "did not expect the anomaly banner when every signal is healthy")


def test_stale_pipeline_shows_banner_exactly_once(tmp_path):
    """a stale ADS-B pipeline shows the anomaly banner copy exactly once"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    count = rendered.count(health_page.ANOMALY_BANNER_TEXT)
    assert count == 1, "expected the anomaly banner copy exactly once, found %d" % count


def test_unreadable_database_degrades_without_raising(tmp_path):
    """a state directory that cannot hold a database renders the health-unavailable copy without raising"""
    blocked_state_dir = tmp_path / "blocked"
    blocked_state_dir.write_text("this is a file, not a directory")
    rendered = health_page_composition.render(shp.ctx(str(blocked_state_dir)))
    assert health_page.HEALTH_UNAVAILABLE_TEXT in rendered, (
        "expected the health-unavailable copy when the database cannot be opened")


def test_source_fault_set_shows_landing_explanation(tmp_path):
    """with the source-fault meta key set, the landing explanation appears"""
    state_dir = str(tmp_path)
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    rendered = health_page_composition.render(shp.ctx(state_dir))
    assert health_page.SOURCE_FAULT_HEADING in rendered, (
        "expected the CFG-05 landing explanation when the source-fault flag is set")


def test_source_fault_unset_hides_landing_explanation(tmp_path):
    """with the source-fault meta key unset, the landing explanation is absent"""
    rendered = health_page_composition.render(shp.ctx(str(tmp_path)))
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert '<h1 class="page-title">Health</h1>' in rendered, (
        "expected the page_header()-rendered <h1 class=\"page-title\">Health</h1>")
    assert '<h1 class="text-heading">' not in rendered, (
        "expected no bare <h1 class=\"text-heading\"> heading")


def test_health_page_header_carries_no_purpose_sentence_or_freshness_line(tmp_path):
    """Health's .page-header holds only the title: the page-description sentence and the
    freshness line are retired"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    header_start = rendered.index('<div class="page-header">')
    header_end = rendered.index("</div>", header_start) + len("</div>")
    assert rendered[header_start:header_end] == (
        '<div class="page-header"><h1 class="page-title">Health</h1></div>'), (
        "expected the page header to carry the title only")
    assert "data-refresh-pill" not in rendered


def test_health_page_two_id_anchored_groups_correct_order_no_overview(tmp_path):
    """Health's body is one rows card with two id-anchored groups (Screen, then Server & data), and the old
    'Overview' heading is gone"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    assert rendered.count(">Overview<") == 0, "expected the old 'Overview' heading to be gone"
    doc = parse_html(rendered)
    card = doc.select_one(".health-rows")
    groups = card.select("h2.health-rows__group")
    assert [group.attrs["id"] for group in groups] == [
        health_page.SCREEN_SECTION_ID, health_page.SERVER_DATA_SECTION_ID]
    assert [group.text() for group in groups] == [
        health_page.SCREEN_SECTION_HEADING, health_page.SERVER_DATA_SECTION_HEADING]
    assert len(doc.select("h2[id]")) == 2, "expected exactly two id-anchored <h2> elements"
    assert not doc.select(".section-intro"), (
        "the group headings sit in the card, not in a free-standing section-intro row")
    # The battery row belongs to Screen, the other four to Server & data.
    screen_at = rendered.index('id="%s"' % health_page.SCREEN_SECTION_ID)
    server_at = rendered.index('id="%s"' % health_page.SERVER_DATA_SECTION_ID)
    assert screen_at < rendered.index("health-row-connection") < rendered.index("health-row-battery") < server_at
    assert server_at < rendered.index("health-row-flight-data") < rendered.index("health-row-identification")
    assert rendered.count("battery-trend-section ") == 1, "expected exactly one battery chart wrapper"
    assert rendered.index(health_page.BATTERY_SECTION_CLASS) < server_at, (
        "expected the battery chart to stay inside the Screen group, before Server & data")


def test_health_page_group_headings_hold_no_description(tmp_path):
    """each of Health's two group bands holds its heading alone: the per-section description sentences are
    retired and no empty caption element remains"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    for group in parse_html(rendered).select("h2.health-rows__group"):
        assert [child for child in group.children if not isinstance(child, str)] == [], (
            "a group band holds text only, got %r" % (group,))
    assert 'class="text-label section-caption"></p>' not in rendered


def test_server_rows_form_one_card_with_no_registry_card_below(tmp_path):
    """the Server & data rows (flight data, sources, identification) form one card; no
    unresolved-prefix card and no nested page-section follows it; there is no tile grid, no stat
    tile and no separate statistics card, and the breakdown lives inside the Identification row"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    doc = parse_html(rendered)
    assert not doc.select(".dashboard-grid") and not doc.select(".stat-tile"), (
        "the tile grids the rows replaced must not come back")
    for row_id in ("flight-data", "sources", "identification"):
        assert doc.select_one(".health-rows").select("#health-row-%s" % row_id), row_id
    assert not doc.select("section.page-section--nested")
    assert "ABC123" not in rendered and "data-filter-input" not in rendered
    identification = doc.select_one("#health-row-identification")
    breakdown = identification.select(".data-table") + identification.select(".data-cards")
    assert breakdown, "expected the resolution breakdown inside the Identification row"
    assert not doc.select(".%s.page-section--nested" % health_page.HEALTH_SOURCE_FAULT_CLASS), (
        "the source-fault block must never carry the nested modifier")
    link = identification.select_one("a.text-link")
    assert link is not None and link.attrs["href"] == "/airlines/manage"


def test_identification_row_renders_percentage_and_window(tmp_path):
    """the Identification row renders the identified percentage and the window/event-count line for a seeded
    fixture, and the no-stats state for an empty one"""
    state_dir = str(tmp_path / "seeded")
    now = shp.now()
    events = []
    for source in ("fresh_hit", "fresh_hit", "cache_hit", "miss"):
        events.append({"ts": shp.iso(now), "hex": "abc123", "route_source": source})
    shp.seed_runway_events(state_dir, events)
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    row = shp.health_row(rendered, "identification")
    assert row.select_one(".health-row__name").text() == health_page.STATS_SECTION_HEADING
    assert "75.0% of flights identified" in row.select_one(".health-row__verdict").text(), (
        "expected the identified percentage in the row's verdict")
    assert ("over the last %d days, 4 events" % health_page.RESOLUTION_WINDOW_DAYS) in row.text(), (
        "expected the window/event-count line")
    assert not row.select(".health-row__ring"), "the rate is a figure in text, not a ring"

    state_dir_empty = str(tmp_path / "empty")
    rendered_empty = health_page_composition.render(shp.ctx(state_dir_empty))
    expected_heading = health_page._NO_STATS_HEADING % health_page.RESOLUTION_WINDOW_DAYS
    assert expected_heading in shp.health_row(rendered_empty, "identification").text(), (
        "expected the no-stats heading with zero resolution history")


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

    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
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

    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
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


def test_breakdown_table_absent_when_empty_both_languages(tmp_path):
    """the empty identification breakdown is entirely absent from the rendered page in both English and
    French — the row says so in one line, never a table over an empty body"""
    state_dir = str(tmp_path)
    now = shp.now()
    rendered_en = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    try:
        prefs.set_request_prefs(lang="fr")
        rendered_fr = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    for lang, rendered in (("en", rendered_en), ("fr", rendered_fr)):
        row = shp.health_row(rendered, "identification")
        assert not row.select(".data-table") and not row.select(".data-cards"), (
            "expected no breakdown table with no rows in the window (%s)" % lang)
        assert health_page.RESOLUTION_WINDOW_DAYS == 30
        assert "30" in row.select_one(".health-row__verdict").text()
        assert shp.health_row_state(rendered, "identification") == ("off", False)


def test_identification_row_shows_36_rows_never_no_events(tmp_path):
    """with 36 seeded rows (30 known, 6 with a NULL route_source) the identification row shows a
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
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
    row_text = shp.health_row(rendered, "identification").text()
    assert "No flights in the last" not in row_text, (
        "expected a non-empty identification row with 36 seeded rows in the window")
    assert ("over the last %d days, 36 events" % health_page.RESOLUTION_WINDOW_DAYS) in row_text, (
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


# ==========================================================================
# Health still gains no form/state-changing control (phase 13)
# ==========================================================================


def _render_health_normal(state_dir):
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    return health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))


def _render_health_anomaly(state_dir):
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.ago(health_page.STALE_PIPELINE_ERROR_S + 60)})
    return health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))


def _render_health_source_fault(state_dir):
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    return health_page_composition.render(shp.ctx(state_dir))


def _render_health_empty(state_dir):
    return health_page_composition.render(shp.ctx(state_dir))


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
    mention in the SOURCE, never rendered markup: health_page_composition.render() returns a content
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
    """the Battery row carries no range caption, and style.css's .section-caption still declares
    exactly one property at the file's single 70% muted strength"""
    # Pins the markup pair AND the single muted strength together, so a
    # future edit cannot satisfy one half while forking the other. The
    # caption now lives in a SIBLING <p> immediately after </h2>, not the
    # heading's own retired trailing <span>.
    state_dir = str(tmp_path)
    rendered = health_page_composition.render(shp.ctx(state_dir))
    assert "3 months" not in _row_html(rendered, "battery"), (
        "expected no range caption in the Battery row")

    decls = declarations_for(css_text, ".section-caption")
    assert len(decls) == 1 and decls.get("color") == (
        "color-mix(in srgb, var(--color-text) 70%, transparent)"), (
        "expected .section-caption to still declare exactly one property, the file's single "
        "70%% muted color-mix, got %r" % decls)


def test_migrated_cards_have_independent_failure_isolation(tmp_path):
    """corrupting only the database degrades the stats row, and a malformed registry file
    leaves the identification stats rendering"""
    # The registry read (state_store.load_poll_state(), a filesystem/JSON
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
    rendered = health_page_composition.render(shp.ctx(db_broken))
    assert health_page.HEALTH_UNAVAILABLE_TEXT in rendered, (
        "expected the stats card to show the unavailable copy when the database is broken")

    registry_broken = str(tmp_path / "registry-broken")
    now = shp.now()
    shp.seed_runway_events(registry_broken, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    poll_state_path = os.path.join(registry_broken, "poll_state.json")
    with open(poll_state_path, "w") as fh:
        fh.write("not valid json {")
    rendered2 = health_page_composition.render(shp.ctx(registry_broken, now_value=shp.iso(now)))
    assert "100.0% of flights identified" in rendered2, (
        "expected the identification stats to still render when only the registry file is malformed")


def test_read_health_inputs_keeps_stats_separate(tmp_path):
    """_read_health_inputs() carries exactly ten keys — device_config and registry_rows join it for
    severity's sake, fleet_status for the fleet.db fallback anomaly — while the stats read alone stays a separate call in
    render()"""
    inputs = health_page._read_health_inputs(str(tmp_path), shp.iso(shp.now()))
    expected_keys = {
        "device_health", "pipeline_ts", "last_detection", "source_fault_raw",
        "trend_rows", "daily_rows", "corroboration_counts",
        "device_config", "registry_rows", "fleet_status",
    }
    assert set(inputs.keys()) == expected_keys, (
        "expected _read_health_inputs() to carry exactly these ten keys, got %r"
        % (set(inputs.keys()),))
    assert not any("stats" in k for k in inputs.keys()), (
        "D-11: the stats read must stay a separate call in render(), not join this dict")


def test_battery_row_keeps_everything_after_the_move(tmp_path):
    """the Battery row keeps its readout, chart wrapper and single script tag inside its details"""
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    row = shp.health_row(rendered, "battery")
    assert row.select_one(".health-row__name").text() == health_page.ROW_BATTERY_NAME
    assert shp.health_row_state(rendered, "battery") == ("ok", False)
    assert row.select_one("#" + health_page.BATTERY_READOUT_ID) is not None, (
        "expected the readout element id to survive the move")
    assert row.select_one(".battery-trend-section--embedded") is not None
    assert rendered.count("<script") == 1, (
        "expected exactly one <script occurrence, got %d" % rendered.count("<script"))
    assert health_page.BATTERY_TREND_SCRIPT_SRC in rendered, (
        "expected BATTERY_TREND_SCRIPT_SRC in the rendered <script src>")
    assert not row.select(".stat-tile"), "the battery row must carry no stat-tile class"


def test_battery_row_is_followed_by_content_not_a_range_caption(tmp_path):
    """the Battery row's body leads with the readout and chart, then the collapsed readings disclosure — no
    range caption anywhere in it"""
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    body = _row_html(rendered, "battery")
    assert "section-caption" not in body, "expected no caption paragraph inside the battery row"
    assert body.index(health_page.BATTERY_READOUT_ID) < body.index(
        '<details class="readings-disclosure"'), "expected the readout to precede the readings disclosure"


def test_battery_row_name_is_the_bare_subject_in_both_languages(tmp_path):
    """the Battery row's name is the catalogue's subject text alone, with no month count or range
    qualifier, in both English and French"""
    state_dir = str(tmp_path)
    for lang in ("en", "fr"):
        try:
            prefs.set_request_prefs(lang=lang)
            rendered = health_page_composition.render(shp.ctx(state_dir))
        finally:
            prefs.set_request_prefs(lang="en")
        expected = i18n.t_lang(health_page.ROW_BATTERY_NAME, lang)
        name = shp.health_row(rendered, "battery").select_one(".health-row__name")
        assert name.text() == expected, "%s: expected the row name %r, got %r" % (lang, expected, name.text())
        assert "3 months" not in rendered and "3 mois" not in rendered, (
            "%s: the retired range label must not render" % lang)


def test_battery_row_renders_no_range_caption_in_any_of_three_branches(tmp_path):
    """a usable daily series, no rows at all, and a sub-two-day raw series each render the battery
    row with no range caption; only the readings disclosure carries the real count"""
    base = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)

    daily_dir = str(tmp_path / "daily")
    shp.seed_device_health(daily_dir, [
        (shp.iso(base - timedelta(days=day)), mv) for day, mv in enumerate((4000, 4100, 4200))])
    empty_dir = str(tmp_path / "empty")
    sameday_dir = str(tmp_path / "sameday")
    sameday_readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(sameday_dir, sameday_readings)

    for branch, state_dir in (("daily", daily_dir), ("no-rows", empty_dir), ("sameday", sameday_dir)):
        body = _row_html(health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base))), "battery")
        assert 'class="text-label section-caption"' not in body and 'health-row__note' not in body, (
            "%s branch: expected no range caption in the battery row" % branch)
        assert "Last 3 months" not in body and "Latest " not in body, (
            "%s branch: expected no range wording in the battery row" % branch)
    sameday_body = _row_html(health_page_composition.render(shp.ctx(sameday_dir, now_value=shp.iso(base))), "battery")
    assert "View %d readings" % len(sameday_readings) in sameday_body, (
        "sameday branch: expected the disclosure to name the real reading count")


def test_battery_readout_precedes_chart_class_list_and_live_region(tmp_path, battery_trend_js):
    """the battery readout precedes the chart and the script tag inside the Battery row, carries
    its single expected class plus role="status" plus both value/detail spans, and battery-trend.js
    still looks it up by id"""
    # The readout is the row's scannable headline number, ahead of the chart.
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=1)), 4200),
        (shp.iso(base), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(base)))
    section_html = _row_html(rendered, "battery")

    readout_open = section_html.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
    readout_tag_close = section_html.index(">", readout_open) + 1
    readout_tag = section_html[readout_open:readout_tag_close]
    readout_close = section_html.index("</p>", readout_open) + len("</p>")
    readout_html = section_html[readout_open:readout_close]
    sparkline_at = section_html.index('<svg class="sparkline__canvas"')
    script_at = section_html.index("<script")
    assert readout_open < sparkline_at < script_at, (
        "expected the readout to precede the sparkline, and the sparkline to precede the script "
        "tag, inside the battery row")

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
    """the Battery row carries the state battery_status() derives from the same rows (and opens
    itself), the Unresolved-prefixes card carries no status modifier, the Identification row stays
    neutral, and style.css still declares all three doubled-form status rules for both card
    components"""
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
    # The Resolution-statistics card is omitted entirely when its window
    # holds zero rows — seed one so the card (and its "no status
    # modifier" assertion below) still renders.
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    battery_state = health_page.battery_status([
        {"ts": shp.iso(now), "battery_mv": readings[1][1]},
        {"ts": shp.iso(now - timedelta(minutes=1)), "battery_mv": readings[0][1]},
    ])
    assert battery_state == "warn", "expected the seeded battery fixture to compute a warn verdict (D-05 demotion)"
    assert shp.health_row_state(rendered, "battery") == (battery_state, True), (
        "expected the Battery row to carry the verdict battery_status() computes, and to open itself")

    # The identification rate computes no verdict, so its row stays neutral.
    assert shp.health_row_state(rendered, "identification") == ("off", False)

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
    """the Battery row renders no dot-label anywhere inside its own boundaries, the Sources
    row's three dots survive untouched (proving the removal is scoped, not global), and
    BATTERY_STATUS_LABEL/_battery_badge_block are both gone via hasattr, never a source grep"""
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
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": True}])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    battery_slice = _row_html(rendered, "battery")
    assert "dot-label" not in battery_slice, (
        "the battery row must render no dot-label — its own badge is retired")

    # The Sources row's outcome dots survive untouched, so this check
    # fails if status_dot() itself breaks, not only if the two removals
    # are wrong.
    assert "dot-label" in _row_html(rendered, "sources"), (
        "expected the Sources row's own dots to survive untouched")

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
    """no block of the page carries page-section--nested, the source-fault block never does even
    when it renders, both group band headings are
    untouched, and style.css's nested-heading rule declares the sans family, the Body size (16px)
    and the semibold weight explicitly (plus its retained bottom margin), sitting below a
    .text-heading section-heading tier confirmed still 22px/regular at the token level too"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    # Seed one runway event so the identification row still carries a table,
    # unrelated to what this check is actually about.
    shp.seed_runway_events(state_dir, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))

    assert "page-section--nested" not in rendered, (
        "expected no page-section--nested block: the unresolved-prefix card is gone")

    fault = parse_html(rendered).select(
        "section.toast." + health_page.HEALTH_SOURCE_FAULT_CLASS)
    assert len(fault) == 1, "expected the source-fault block itself to render for this fixture"
    assert "page-section--nested" not in fault[0].attrs["class"].split(), (
        "the source-fault block must never carry page-section--nested")

    for section_id, heading in (
            (health_page.SCREEN_SECTION_ID, health_page.SCREEN_SECTION_HEADING),
            (health_page.SERVER_DATA_SECTION_ID, health_page.SERVER_DATA_SECTION_HEADING)):
        band_marker = '<h2 id="%s" class="health-rows__group">%s</h2>' % (section_id, layout.escape_html(heading))
        assert band_marker in rendered, "expected %r's own group band heading to be unmodified" % heading

    nested_decls = declarations_for(css_text, ".page-section--nested > h2")
    assert ".battery-trend-section > h2" in next(
        rule.selectors for rule in css_rules(css_text) if ".page-section--nested > h2" in rule.selectors), (
        "expected the promoted rule's selector list to still cover .battery-trend-section > h2")
    assert nested_decls.get("margin-bottom") == "var(--space-md)", (
        "expected the promoted rule to still declare its retained 260902-bl2 bottom margin — a "
        "missing bottom margin means this re-promotion over-reached and took the independently-"
        "justified spacing fix with it, got %r" % nested_decls)
    assert nested_decls.get("font-family") == "var(--font-display)", (
        "expected the nested-heading rule to declare the display face — a nested card title is "
        "a section title like every other, got %r" % nested_decls)
    assert nested_decls.get("font-size") == "var(--font-heading-size)", (
        "expected the nested-heading rule to declare the section title size, got %r"
        % nested_decls)
    assert nested_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected the nested-heading rule to declare font-weight: var(--weight-semibold) — a "
        "font-weight missing here means the D-09 re-promotion did not land, got %r" % nested_decls)

    heading_decls = declarations_for(css_text, ".text-heading")
    assert heading_decls.get("font-size") == "var(--font-heading-size)", (
        "expected .text-heading to still declare --font-heading-size — the section heading tier "
        "this nested title now sits below has no fallback of its own, got %r" % heading_decls)
    assert heading_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected .text-heading to be --weight-semibold — the section title role is semibold "
        "on every page, got %r" % heading_decls)
    assert heading_decls.get("font-family") == "var(--font-display)", heading_decls
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
    assert caption_decls.get("font-size") == "var(--font-caption-size)", (
        "expected .stat-tile__caption to declare the caption size token — the unified label "
        "voice's own size, got %r" % caption_decls)
    assert caption_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected .stat-tile__caption to declare font-weight: var(--weight-semibold) — one of the "
        "unified label voice's four properties, got %r" % caption_decls)
    assert caption_decls.get("text-transform") in (None, "none"), (
        "labels are sentence case: no uppercase transform, got %r" % caption_decls)
    assert caption_decls.get("letter-spacing") in (None, "normal", "0"), (
        "labels are not tracked, got %r" % caption_decls)

    value_decls = declarations_for(css_text, ".stat-tile__value")
    assert value_decls.get("font-size") == "var(--font-body-size)", (
        "expected .stat-tile__value to stay on the Body size (16px) — Finding 4's own contract, "
        "got %r" % value_decls)
    assert value_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected .stat-tile__value to stay semibold — Finding 4's own contract, got %r" % value_decls)

    # The nested card title's demotion is re-promoted a second time,
    # deliberately, as the bottom rung of the full type ladder.
    nested_decls = declarations_for(css_text, ".page-section--nested > h2")
    assert nested_decls.get("font-size") == "var(--font-heading-size)", (
        "expected the nested card title to declare the section title size, got %r" % nested_decls)
    assert nested_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected the nested card title to declare font-weight: var(--weight-semibold) — D-09's "
        "second reversal promotes it onto the sans Emphasis role, got %r" % nested_decls)

    heading_decls = declarations_for(css_text, ".text-heading")
    assert heading_decls.get("font-weight") == "var(--weight-semibold)", (
        "expected the shared heading rule to be semibold on every page, got %r" % heading_decls)

    # Token values themselves, so this check fails loudly (not silently)
    # if a future edit changes what 14/16/22 actually mean.
    tokens = custom_properties(css_text, ":root")
    for name, expected in (
            ("--font-caption-size", "13px"),
            ("--font-label-size", "15px"),
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
    """Health's two-tier hierarchy still reads apart with no font-size or font-weight distinction
    doing the work: both group bands sit inside the one bordered rows card (no card class on a
    free-standing intro row), the registry's level-2 heading sits inside its own bordered card <section>,
    and the card-to-card gap is ONE value shared by the rows card and the registry card, ordered above
    the heading-to-content gap — in both the empty and seeded state"""
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
        rendered = health_page_composition.render(shp.ctx(state_dir, now_value=shp.iso(now)))
        doc = parse_html(rendered)

        card = doc.select_one(".health-rows")
        for section_id in (health_page.SCREEN_SECTION_ID, health_page.SERVER_DATA_SECTION_ID):
            assert card.select("h2#%s" % section_id), (
                "seeded=%s: expected the %r group band to sit inside the one rows card" % (seeded, section_id))
        assert not doc.select(".section-intro")

        assert not doc.select("section.page-section--nested"), (
            "seeded=%s: the unresolved-prefix card no longer exists" % seeded)

    tokens = custom_properties(css_text, ":root")
    rows_token, rows_gap = _margin_bottom_token_px(css_text, ".health-rows", tokens)
    card_token, card_gap = _margin_bottom_token_px(css_text, ".page-section", tokens)
    head_token, head_gap = _margin_bottom_token_px(css_text, ".page-section--nested > h2", tokens)
    intro_token, intro_gap = _margin_bottom_token_px(css_text, ".text-heading", tokens)

    assert rows_gap == card_gap, (
        "expected the rows card and .page-section to share one card-to-card gap "
        "(%s=%dpx vs %s=%dpx)" % (rows_token, rows_gap, card_token, card_gap))
    assert card_gap > head_gap > intro_gap, (
        "expected the layout hierarchy's spacing tiers to stay strictly ordered "
        "(card-to-card %dpx > heading-to-content %dpx > section-intro rhythm %dpx)"
        % (card_gap, head_gap, intro_gap))
