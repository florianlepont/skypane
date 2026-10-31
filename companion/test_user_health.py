"""Render-level behaviour tests for the reduced user view of Display, Home
and Health: what a user principal's served markup omits, that the nav dot,
Home attention row and freshness token follow the frame only, and that
the admin rendering keeps every platform section.
"""
import pytest

import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import freshness, user_view
from companion.layout import escape_html
from companion.pages import config_page, health_page, home_page
from server import history_db

NOW = "2026-06-01T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset_principal():
    prefs.set_request_principal(None)
    prefs.set_request_prefs(lang="en")
    yield
    prefs.set_request_principal(None)
    prefs.set_request_prefs(lang="en")


def _as(role):
    prefs.set_request_principal(role, role)


def _live_ctx(state_dir):
    """A real lazy PageContext over `state_dir`, wired like a request's."""
    state_dir = str(state_dir)
    holder = {}

    def signals():
        return user_view.reduce_signals(
            health_page.safe_health_signals(state_dir, NOW, state_dir))

    values = {
        "state_dir": state_dir, "root_state_dir": state_dir, "now": NOW,
        "lang": "en", "ui_theme": "light", "device_config": {},
        "battery_critical": False,
    }
    ctx = page_context.PageContext(values, {
        "_health_signals": signals,
        "health_state": lambda: page_context._lazy_health_state(holder["ctx"]),
        "health_severity": lambda: page_context._lazy_health_severity(holder["ctx"]),
        "gallery_entries": lambda: [],
        "manual_resolutions": dict,
        "name_overrides": dict,
        "colour_rules": list,
    })
    holder["ctx"] = ctx
    return ctx


def _set_meta(state_dir, key, value):
    with history_db.open_db(str(state_dir)) as conn:
        history_db.set_meta(conn, key, value)


PLATFORM_TEXTS = (
    health_page.SERVER_DATA_SECTION_HEADING,
    health_page.UNRESOLVED_SECTION_HEADING,
    health_page._NOTHING_TO_RESOLVE_TEXT,
    health_page._NOTHING_TO_COMPARE_YET_TEXT,
)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_user_display_keeps_everyday_controls_and_drops_admin_ones(tmp_path, lang):
    cp.write_device_config(tmp_path, "sky", "3")
    ctx = {"state_dir": str(tmp_path), "device_config": {"theme": "sky"}, "now": NOW}
    prefs.set_request_prefs(lang=lang)
    _as("user")
    user_html = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert "quiet_hours_start" in user_html
    assert 'name="calendar_url"' in user_html
    assert 'name="timezone"' in user_html
    assert 'name="theme' in user_html
    assert 'name="%s"' % "tracked_runway" not in user_html
    assert config_page.RUNWAY_GROUP_HEADING_ID not in user_html
    for field in user_view.ADMIN_ONLY_SETTING_FIELDS:
        assert 'name="%s"' % field not in user_html

    _as("admin")
    admin_html = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert 'name="tracked_runway"' in admin_html


def test_user_cannot_render_device_scope(tmp_path):
    ctx = {"state_dir": str(tmp_path), "device_config": {}, "now": NOW}
    _as("user")
    html = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    for field in user_view.ADMIN_ONLY_SETTING_FIELDS:
        assert 'name="%s"' % field not in html
    assert "quick/led" not in html


def test_home_for_user_has_no_poll_trigger_or_led_control(tmp_path):
    ctx = _live_ctx(tmp_path)
    for role in ("user", "admin"):
        _as(role)
        html = home_page.render(ctx)
        assert "led_enabled" not in html
        assert "/quick/led" not in html
        assert "/poll" not in html


def test_user_health_shows_frame_card_and_no_platform_rows(tmp_path):
    ctx = _live_ctx(tmp_path)
    _as("admin")
    admin_html = health_page.render(ctx)
    _as("user")
    user_html = health_page.render(_live_ctx(tmp_path))

    assert i18n.t(health_page.SCREEN_SECTION_HEADING) in user_html
    assert i18n.t(health_page._LAST_CHECK_IN_TEXT) in user_html
    for text in PLATFORM_TEXTS:
        assert escape_html(i18n.t(text)) in admin_html, text
        assert escape_html(i18n.t(text)) not in user_html, text
    assert health_page.SERVER_DATA_SECTION_ID not in user_html
    assert health_page.UNRESOLVED_SECTION_ID not in user_html
    assert "resolve-dialog" not in user_html


def test_user_health_hides_source_fault_block(tmp_path):
    _set_meta(tmp_path, history_db.META_SOURCE_FAULT, "True")
    _as("admin")
    admin_html = health_page.render(_live_ctx(tmp_path))
    assert i18n.t(health_page.SOURCE_FAULT_HEADING) in admin_html
    _as("user")
    user_html = health_page.render(_live_ctx(tmp_path))
    assert i18n.t(health_page.SOURCE_FAULT_HEADING) not in user_html


def test_platform_only_faults_do_not_change_user_severity_but_do_for_admin(tmp_path):
    _as("user")
    baseline = _live_ctx(tmp_path)
    baseline_severity = baseline.health_severity
    baseline_anomalies = baseline.health_state["anomalies"]
    baseline_attention = home_page._action_needed_html(baseline)
    baseline_health = health_page.render(baseline)

    _set_meta(tmp_path, history_db.META_SOURCE_FAULT, "True")

    _as("admin")
    assert _live_ctx(tmp_path).health_severity == "error"

    _as("user")
    user_ctx = _live_ctx(tmp_path)
    assert user_ctx.health_severity == baseline_severity
    assert user_ctx.health_state["severity"] == baseline_severity
    assert user_ctx.health_state["anomalies"] == baseline_anomalies
    assert home_page._action_needed_html(user_ctx) == baseline_attention
    assert health_page.render(user_ctx) == baseline_health


def test_user_home_attention_ignores_pipeline_state():
    ctx = page_context.coerce({"health_state": {
        "device_state": "ok", "pipeline_state": "error", "battery_state": "ok"}})
    _as("admin")
    assert home_page._needs_attention(ctx) is True
    _as("user")
    assert home_page._needs_attention(ctx) is False
    ctx.health_state["battery_state"] = "warn"
    assert home_page._needs_attention(ctx) is True


def _token(state_dir):
    return freshness._page_freshness_token(
        layout.HEALTH_ROUTE, _live_ctx(state_dir), "")


def test_health_freshness_token_user_ignores_platform_inputs(tmp_path, monkeypatch):
    marker = tmp_path / "offbox.marker"
    monkeypatch.setenv(health_page.OFFBOX_MARKER_ENV_VAR, str(marker))
    _set_meta(tmp_path, history_db.META_LAST_PIPELINE_RUN, "2026-06-01T11:00:00+00:00")

    def platform_change():
        _set_meta(tmp_path, history_db.META_SOURCE_FAULT, "True")
        _set_meta(
            tmp_path, history_db.META_LAST_PIPELINE_RUN, "2026-06-01T11:30:00+00:00")
        marker.write_text("{}")

    _as("user")
    user_before = _token(tmp_path)
    _as("admin")
    admin_before = _token(tmp_path)
    platform_change()
    _as("user")
    assert _token(tmp_path) == user_before
    _as("admin")
    assert _token(tmp_path) != admin_before
