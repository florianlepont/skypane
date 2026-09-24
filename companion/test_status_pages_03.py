"""Part 03 of the `companion/test_status_pages.py` migration chain
(33-27-PLAN.md): the original harness's `check()` calls #86-#139 — the
continuation of Section 1 (`companion/pages/health_page.py`'s contract):
`compute_health_state()`'s never-ran-pipeline detail fragment, the
D-05/A-23 `overall_severity()`/`collect_anomalies()` widened precedence
table and its device-cadence pinning, the anomaly-banner/source-fault/
degrade-not-raise trio, Health's page-header/two-section/section-intro
shape, the Server & data grid's tile-count/nesting invariants, the
Resolution-rate tile and B3's "count every row, bucket the unknown as
Other" fix, the registry card's filter bar/read-only note/Resolve-link
pair, the battery-trend section's post-move heading/caption/readout
contract (quick tasks 260901-tsa/260901-uzi/260902-gjj/260902-ep7/
29-06-PLAN.md), the card-status-border doubled-form/hover-source-order
mechanism, the nested-card-heading-tier/label-voice CSS contracts
(06.6.4.1.1 D-09/D-13), and the D-10 two-tier-hierarchy-carried-by-layout
closing check.

Two checks in this slice read production source/CSS/JS from disk in the
legacy harness (TST-12 rubric S/J) and are ported here differently:

- `_health_page_never_imports_html_module()`'s raw `health_page.py` read
  (grepping for a literal `import html` line) becomes `not hasattr(
  health_page, "html")` — a bare `import html` binds the name `html`
  directly into the module's own namespace, so this is a real behavioural
  proof, not a source-text read.
- `_health_still_has_no_form_and_exactly_one_button_literal()`'s raw
  `health_page.py` read (counting `"<form"`/`"<button"` occurrences in
  the SOURCE, which is why the legacy count was "1" — a docstring
  mention, never rendered markup) is rewritten as a rendered/parsed
  check (TST-12 rubric S, `<slice>`'s named rewrite): Health is rendered
  in four seeded states (normal, anomaly, source-fault, empty) and the
  parsed tree is asserted to contain zero `<form>` and zero `<button>`
  elements in every one of them — `health_page.render()` returns a
  content fragment only (no shared nav chrome), so this is the page's
  own true contract, not an artefact of what the shared layout adds
  elsewhere.
- `_cross_file_contract_drift_guard()`'s raw `battery-trend.js` read
  becomes `served_asset()` against a running `companion/app.py` (the
  `battery_trend_js` fixture below), per rubric J.

Every CSS check in this slice (rubric C) fetches the stylesheet
`companion/app.py` actually serves and asserts on it structurally via
`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`
— never a regex/substring probe over the raw served text (33-FOLLOWUPS.md
F-01) — using the same single module-scoped read-only server 33-26
established (`_module_server`/`css_text`/`battery_trend_js`), since none
of the checks below mutate server state.

Every other check in this module calls `companion.pages.health_page`/
`companion.layout`/`companion.i18n`/`companion.prefs`/`companion.wake`
directly, in-process.
"""
import os
from datetime import timedelta

import pytest

import companion.app as app
from companion import i18n, layout, prefs
from companion.pages import health_page
import companion.test_status_pages_helpers as shp
import companion.wake as wake
from companion_app_server import served_asset, served_stylesheet
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
    is verdict-free and embedded once inside pipeline_html, mirroring device_detail_html (B2,
    22-03-PLAN.md Task 1)"""
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
    'ok' — never an anomaly, never a warn — while a genuinely stale pipeline_state still is (B2,
    22-03-PLAN.md Task 1)"""
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
    a readout element nor a chart script tag (D-09 regression guard)"""
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
    """a large consecutive-reading drop flags a battery warning (demoted from error, D-05); a gentle
    monotonic decline does not"""
    # battery_status() takes newest-first rows (matching battery_trend_rows()'s/
    # recent_device_health()'s own ordering) — t2 (newer) sorts before t1 (older)
    # in both fixtures below.
    #
    # 19-05-PLAN.md Task 3 (D-05/A-23): a >= BATTERY_DROP_WARN_MV drop is a
    # "warn", demoted from "error" (a single sampling artefact must not paint
    # the whole page as an outage).
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
# 19-05-PLAN.md Task 3 (D-05/A-23): overall_severity()'s widened
# precedence table, and collect_anomalies()'s two matching new items
# ==========================================================================


def test_overall_severity_widened_precedence_table():
    """overall_severity()'s widened 6-input precedence table: source_fault wins outright, error states
    win next, then warn states/disagreement_warn/coverage_state=='warn', with the 4-argument call
    staying byte-for-byte backward compatible (19-05-PLAN.md Task 3/D-05)"""
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
    """overall_severity()'s plan-cited acceptance triple: ('ok', 'error', 'warn') (19-05-PLAN.md Task 3)"""
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
    registry alone into warn severity, and stays ok when both are clear (19-05-PLAN.md Task 3/D-05)"""
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
    input is unhealthy, and a fully healthy 4-argument call still returns none (19-05-PLAN.md Task 3)"""
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
    pinned from both directions through the real compute_health_state() pipeline (19-05-PLAN.md
    Task 3/D-05, A-23)"""
    # A device last seen 400 seconds ago is "warn" at a 30s cadence (400 >
    # the 300s floor: 3 * 30 = 90, floored up to 300) but "ok" at a 3600s
    # cadence (400 < 3 * 3600 = 10800) — the A-23 defect, pinned from both
    # directions against the real compute_health_state() pipeline. The 30s
    # cadence is deployed via SKYPANE_SLEEP_S (device_config.save_device_
    # config()'s own wake_interval_s validation enforces [60, 3600] — 30 can
    # only reach effective_wake_interval_s() via the env fallback, exactly
    # like the real shipped SKYPANE_SLEEP_S=30 deployment); the 3600s cadence
    # is deployed via a seeded device_config.json, at the top of that same
    # valid range.
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
    """with the source-fault meta key set, the CFG-05 landing explanation appears"""
    state_dir = str(tmp_path)
    shp.seed_meta(state_dir, **{history_db.META_SOURCE_FAULT: "True"})
    rendered = health_page.render(shp.ctx(state_dir))
    assert health_page.SOURCE_FAULT_HEADING in rendered, (
        "expected the CFG-05 landing explanation when the source-fault flag is set")


def test_source_fault_unset_hides_landing_explanation(tmp_path):
    """with the source-fault meta key unset, the CFG-05 landing explanation is absent"""
    rendered = health_page.render(shp.ctx(str(tmp_path)))
    assert health_page.SOURCE_FAULT_HEADING not in rendered, (
        "did not expect the CFG-05 landing explanation with no source-fault flag set")


def test_health_page_never_imports_html_module():
    """companion/pages/health_page.py never imports the stdlib html module directly"""
    # TST-12 rubric S rewrite: a bare `import html` binds the name `html`
    # directly into health_page's own module namespace, so hasattr() is a
    # real behavioural proof of the same fact the legacy check's source
    # grep asserted — never a source-text read.
    assert not hasattr(health_page, "html"), (
        "health_page.py must never import the stdlib html module directly")


def test_health_page_opens_with_shared_page_header(tmp_path):
    """Health opens with the shared layout.page_header() component, not a bare <h1>"""
    # 06.6.2-04 (D-16): Health's top-level heading now goes through
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
    """Health's .page-header carries a one-sentence purpose after the auto-refresh pill (quick task
    260901-tsa, finding A; retargeted in place by 260902-chc)"""
    # quick task 260901-tsa (finding A): PAGE_PURPOSE_TEXT reaches
    # layout.page_header()'s `purpose` parameter, renders inside
    # .page-header, and — per that component's own reordered emission
    # (Task 1) — follows the Refresh link, matching the validated sketch's
    # own DOM order.
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
    # 260902-chc: retargeted from the retired "freshness-refresh" link
    # class onto the pill's own marker attribute — the ordering property
    # this check tests (the header's action slot precedes the purpose
    # sentence) is unchanged by that reversal.
    refresh_at = rendered.index("data-refresh-pill")
    purpose_at = rendered.index(escaped_purpose)
    assert refresh_at < purpose_at, (
        "expected the purpose sentence to follow the pill, matching the validated sketch's own "
        "DOM order")


def test_health_page_two_id_anchored_sections_correct_order_no_overview(tmp_path):
    """Health's body is two id-anchored sections (Screen, then Server & data), and the old 'Overview' heading
    is gone (D-10)"""
    # 06.6.4.1-04 (D-10): Health's body is now two id-anchored sections,
    # Screen then Server & data, replacing the single "Overview" heading +
    # one dashboard-grid shape.
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
    # quick task 260902-gjj: the section's own class attribute also carries
    # a status modifier (BATTERY_SECTION_CLASS + "--ok"/"--warn"/"--error"),
    # so the bare class-name substring appears TWICE inside that one
    # attribute — the open-tag prefix counts sections, not substrings.
    assert rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS) == 1, (
        "expected exactly one battery-trend section, got %d"
        % rendered.count('<section class="%s' % health_page.BATTERY_SECTION_CLASS))
    assert rendered.index(health_page.BATTERY_SECTION_CLASS) > rendered.index(screen_heading), (
        "expected the battery-trend section to follow the Screen heading")
    assert rendered.index(health_page.BATTERY_SECTION_CLASS) < rendered.index(server_data_heading), (
        "expected the battery-trend section to stay inside the Screen section, before Server & data")


def test_health_page_section_intros_pair_heading_with_description(tmp_path):
    """each of Health's two section headings is paired, in its own baseline-aligned .section-intro wrapper,
    with its own muted description (quick task 260901-tsa, finding B)"""
    # quick task 260901-tsa (finding B): each section's <h2> is now paired
    # with its own muted description inside a .section-intro wrapper.
    # Slices each wrapper individually (rather than searching the whole
    # page) so the check cannot pass by finding the right description next
    # to the wrong heading.
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
    source-fault block never carries that modifier (D-11/finding E, quick task 260901-uzi finding 4)"""
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
    # quick task 260901-tsa (finding E): the Screen section now also wraps
    # its own single Device tile in a dashboard-grid, so the page carries
    # TWO dashboard-grid divs, not one.
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

    # quick task 260902-gjj (ISSUE 2): the registry card's class attribute
    # now also carries a status modifier (coverage_status()'s own
    # "--ok"/"--warn"), so the closing quote no longer immediately follows
    # "page-section--nested" — this open-ended prefix still finds it, and
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
    fixture, and the no-stats empty state for an empty one (D-10/D-11)"""
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
    # 22-03-PLAN.md Task 2 (B3): the no-stats copy is now the windowed
    # heading, interpolated with RESOLUTION_WINDOW_DAYS — never the retired
    # "No resolution data yet." literal.
    expected_heading = health_page._NO_STATS_HEADING % health_page.RESOLUTION_WINDOW_DAYS
    assert expected_heading in rendered_empty, (
        "expected the no-stats empty-state heading with zero resolution history")


def test_registry_card_keeps_filter_bar_note_and_non_button_clear(tmp_path):
    """the migrated Unresolved-prefixes card keeps its filter bar, read-only note, and non-button Clear
    control (D-12)"""
    state_dir = str(tmp_path)
    registry = {
        "ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"},
    }
    shp.seed_unresolved_prefixes(state_dir, registry)
    rendered = health_page.render(shp.ctx(state_dir))
    for marker in ("data-filter-input", "data-filter-count", "data-filter-clear", "data-filter-empty"):
        assert marker in rendered, (
            "expected the migrated filter bar's %r marker to survive the move" % marker)
    # phase 13 (D-10) reworded this note to include an apostrophe
    # ("row's" — 19-06-PLAN.md Task 3, D-06 dropped the note's second
    # apostrophe, "prefix's", along with the word "prefix" itself), which
    # escape_html()'s quote=True mode renders as &#x27; — compare against
    # the escaped form, matching this module's own single-escaping-choke-
    # point discipline, not the raw Python literal.
    assert layout.escape_html(health_page._READ_ONLY_NOTE) in rendered, (
        "expected the read-only note to survive the move verbatim (escaped)")
    section_start = rendered.index(
        '<h2 class="text-heading">%s</h2>' % health_page.UNRESOLVED_SECTION_HEADING)
    section_slice = rendered[section_start:section_start + 4000]
    assert "<button" not in section_slice, (
        "the migrated registry card's Clear control must not be a <button>")


def test_read_only_note_reworded_to_point_at_airlines_not_the_runbook(tmp_path):
    """the read-only note is reworded to name Airlines as the resolution surface, no longer points at
    the manual runbook (phase 13 D-10), no longer says 'prefix' in either half (19-06-PLAN.md
    Task 3, D-06), and (29-06-PLAN.md Task 2, CFG-79) is now split into a short visible sentence
    plus its moved instruction inside a readings-disclosure"""
    # phase 13 (D-10): the note now tells the operator where resolution
    # happens (the Airlines page, via the per-row Resolve link) instead of
    # pointing at the old manual runbook.
    #
    # 29-06-PLAN.md Task 2 (CFG-79): the note is now split. `_READ_ONLY_
    # NOTE` (the visible sentence) carries only "This list is read-only
    # here."; the Airlines-pointing instruction now lives in `_READ_ONLY_
    # NOTE_DETAIL`, moved verbatim into the card's own <details
    # class="readings-disclosure"> — both must render, the visible one
    # outside it, the detail one inside it.
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
    count into the total and a labelled row, and render() shows a 'Manual' row (phase 13 D-02)"""
    # phase 13 (D-02): _SOURCE_ROWS gains a fifth "manual" tuple so the
    # resolution-rate breakdown never folds a hand-resolved prefix into the
    # "airline_only" bucket, whose gloss says the static prefix table did
    # the work.
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
# 22-03-PLAN.md Task 2 (B3): count every row, bucket the unknown as
# "other", and stop rendering an empty "How well we name flights" card
# ==========================================================================


def test_resolution_stats_counts_unknown_route_source_as_other(tmp_path):
    """resolution_stats() counts a NULL and an unrecognised route_source into one 'Other' bucket,
    the total equals every row in the window, and render() shows the 'Other' row (B3,
    22-03-PLAN.md Task 2)"""
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
    rows and no 'Other' row — byte-identical to before this task (B3, 22-03-PLAN.md Task 2)"""
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
    both English and French — never a heading over an empty body (B3, 22-03-PLAN.md Task 2)"""
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
    non-zero count for all 36, never the empty-state copy (B3, 22-03-PLAN.md Task 2)"""
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
    interpolates RESOLUTION_WINDOW_DAYS at its one call site (B3, 22-03-PLAN.md Task 2)"""
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
    fully escaped in both (phase 13 D-10, T-13-05)"""
    # phase 13 (D-10): each registry row's Resolve link is emitted twice —
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
