"""Lazy `page_context()` and markup-free severity.

`page_context()` used to build the full Health markup, the gallery
listing, the manual-resolutions/colour-rules/calendar registries, and
the poll cooldown on every request, only for the nav-tab dot in the
common case. It now returns an `_LazyContext`: every expensive value is
a loader resolved at most once, only if a route's own `render()` or the
nav-dot read in `_page_shell_for()` actually touches it.

Every behaviour here is asserted against a REAL running
`companion/app.py` (`app_server_in_process`, the only fixture family
whose monkeypatches take effect in the same interpreter the server
thread runs in), never against source text - matching
`companion/test_request_connections.py`'s own convention.
"""
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import companion.app as app
import companion.health_signals as health_signals
import efficiency_probe

from companion import layout
from companion.pages import config_page, health_page
from companion_app_server import http_request, login
from server import history_db
from server.plane import calendar_rules, colour_rules, manual_resolutions

NAV_ROUTES = tuple(route for route, _label in layout.NAV_TABS)

_NAV_DOT_RE = re.compile(rb'class="dot (dot--\w+) nav-notification"')
_BANNER_RE = re.compile(rb'class="banner (banner--\w+)"')
_DOT_TO_SEVERITY = {b"dot--warn": "warn", b"dot--error": "error"}
_BANNER_TO_SEVERITY = {b"banner--warn": "warn", b"banner--anomaly": "error"}


def _seed_warn_scenario(state_dir):
    """A device check-in 600s stale - past the default warn floor (300s,
    `wake.STALE_WARN_FLOOR_S`) but well under the default error floor
    (1200s) - with a fresh pipeline run, so the resulting severity comes
    from the device state alone. Verified empirically (not asserted
    against wake.py's own thresholds a second time here) to resolve to
    "warn" via `health_page.health_signals()`.
    """
    now = datetime.now(timezone.utc)
    stale_ts = (now - timedelta(seconds=600)).isoformat()
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(
            conn, ts=stale_ts, battery_mv=4200, fw_version="1.0.0",
            boot_reason="timer", rssi="-60")
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, now.isoformat())


# ==========================================================================
# _LazyContext itself - unit-level, no server needed.
# ==========================================================================


def test_lazy_context_eager_values_are_present_without_a_loader():
    """an eagerly-supplied value resolves through __getitem__/get()/__contains__ with no
    loaders dict at all"""
    ctx = app._LazyContext({"k": "v"}, {})
    assert ctx["k"] == "v"
    assert ctx.get("k") == "v"
    assert "k" in ctx
    assert "absent" not in ctx


def test_lazy_context_getitem_resolves_a_loader_once():
    """ctx["k"] as the FIRST access still resolves the loader exactly once, caching the result"""
    calls = []

    def _load():
        calls.append(1)
        return 42

    ctx = app._LazyContext({}, {"lazy": _load})
    assert ctx["lazy"] == 42
    assert ctx["lazy"] == 42
    assert len(calls) == 1, "expected the loader to run exactly once, got %d" % len(calls)


def test_lazy_context_contains_never_triggers_the_loader():
    """"k" in ctx sees a pending loader as present without resolving it - dict.__contains__()
    would otherwise never even see a pending key, since it is not yet a real dict entry"""
    calls = []

    def _load():
        calls.append(1)
        return "computed"

    ctx = app._LazyContext({}, {"lazy": _load})
    assert "lazy" in ctx
    assert len(calls) == 0, "expected 'in' to never resolve the loader"
    assert "missing" not in ctx


def test_lazy_context_get_resolves_once_and_falls_back_on_a_real_default():
    """ctx.get("k") resolves and caches a pending loader exactly like ctx["k"]; ctx.get("missing",
    7) == 7 for a key with neither a loader nor an eager value"""
    calls = []

    def _load():
        calls.append(1)
        return "computed"

    ctx = app._LazyContext({}, {"lazy": _load})
    assert ctx.get("lazy") == "computed"
    assert ctx.get("lazy") == "computed"
    assert len(calls) == 1, "expected the loader to run exactly once via .get(), got %d" % len(
        calls)
    assert ctx.get("missing", 7) == 7


def test_lazy_context_getitem_keeps_a_raising_loader_pending_for_retry():
    """a loader that raises leaves its key exactly as pending as it found it - neither resolved
    nor forgotten - so a second read retries the SAME loader (and can raise the SAME original
    exception) instead of falling through to a masking KeyError"""
    calls = []

    def _flaky_load():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("simulated loader failure")
        return "computed on retry"

    ctx = app._LazyContext({}, {"lazy": _flaky_load})
    with pytest.raises(RuntimeError):
        ctx["lazy"]
    assert "lazy" in ctx, "expected the key to remain a pending loader after the raise"
    assert ctx["lazy"] == "computed on retry"
    assert len(calls) == 2, "expected exactly one retry after the first raise, got %d calls" % len(calls)


# ==========================================================================
# Health markup builds only where a page reads health_state.
# ==========================================================================


def test_health_markup_builds_only_on_home_and_health(app_server_in_process, monkeypatch):
    """with health_state_from_signals wrapped by a counter: GET /display, /device, /flights,
    /airlines build zero markup; GET / and /health build exactly one; health_signals runs
    exactly once on every one of the six tab routes, whether or not the route reads markup"""
    server = app_server_in_process
    efficiency_probe.seed_history(server.state_dir)
    session = login(server)

    real_health_signals = health_signals.health_signals
    real_health_state_from_signals = health_page.health_state_from_signals
    signals_calls = []
    state_calls = []

    def counting_health_signals(*args, **kwargs):
        signals_calls.append(1)
        return real_health_signals(*args, **kwargs)

    def counting_health_state_from_signals(*args, **kwargs):
        state_calls.append(1)
        return real_health_state_from_signals(*args, **kwargs)

    # Patched on the health_signals module itself, not on health_page's
    # re-export: safe_health_signals() is DEFINED in companion/health_signals.py,
    # and its own bare-name call to health_signals() resolves in that
    # module's globals — a patch on health_page.health_signals would never
    # be seen by it. health_state_from_signals() stays patched on
    # health_page, since companion/app.py's _lazy_health_state() calls it
    # through a `health_page.health_state_from_signals(...)` attribute
    # lookup at every request.
    monkeypatch.setattr(health_signals, "health_signals", counting_health_signals)
    monkeypatch.setattr(
        health_page, "health_state_from_signals", counting_health_state_from_signals)

    for route in NAV_ROUTES:
        signals_calls.clear()
        state_calls.clear()
        status, _headers, _body = http_request(server.url(route), cookie=session)
        assert status == 200, "expected 200 from GET %s, got %d" % (route, status)
        assert len(signals_calls) == 1, (
            "expected exactly one health_signals() call for GET %s, got %d"
            % (route, len(signals_calls)))
        expected_state_calls = 1 if route in (layout.HOME_ROUTE, layout.HEALTH_ROUTE) else 0
        assert len(state_calls) == expected_state_calls, (
            "expected %d health_state_from_signals() call(s) for GET %s, got %d"
            % (expected_state_calls, route, len(state_calls)))


def test_nav_dot_shows_warn_on_flights_and_equals_the_health_banner(app_server_in_process):
    """seeded stale-device (warn) scenario: the nav dot on /flights shows the warn state, and on
    /health the nav dot's severity equals the banner's severity, parsed from the same response -
    they can never disagree since both come from the one shared health_signals() snapshot"""
    server = app_server_in_process
    _seed_warn_scenario(server.state_dir)
    session = login(server)

    status, _headers, body = http_request(server.url(layout.FLIGHTS_ROUTE), cookie=session)
    assert status == 200, "expected 200 from GET /flights, got %d" % status
    dot_match = _NAV_DOT_RE.search(body)
    assert dot_match, "expected a nav notification dot on Flights for the seeded warn scenario"
    assert dot_match.group(1) == b"dot--warn", (
        "expected the Flights nav dot to show warn, got %r" % dot_match.group(1))

    status2, _headers2, body2 = http_request(server.url(layout.HEALTH_ROUTE), cookie=session)
    assert status2 == 200, "expected 200 from GET /health, got %d" % status2
    dot_match2 = _NAV_DOT_RE.search(body2)
    banner_match = _BANNER_RE.search(body2)
    assert dot_match2 and banner_match, (
        "expected both a nav dot and an anomaly banner on the seeded Health page")
    dot_severity = _DOT_TO_SEVERITY[dot_match2.group(1)]
    banner_severity = _BANNER_TO_SEVERITY[banner_match.group(1)]
    assert dot_severity == banner_severity, (
        "expected the nav dot's severity (%r) to equal the Health banner's severity (%r) in "
        "the same response" % (dot_severity, banner_severity))


# ==========================================================================
# The 404/403 error pages: severity from health_signals alone, and only
# when authenticated.
# ==========================================================================


def test_404_severity_is_authenticated_only_and_never_builds_markup(
        app_server_in_process, monkeypatch):
    """authenticated GET /no-such-page -> 404 with the warn dot, sourced from health_signals()
    alone (health_state_from_signals() never runs for an error page); unauthenticated -> 404,
    health_signals() never runs either, so Health's warn/error state never leaks pre-auth"""
    server = app_server_in_process
    _seed_warn_scenario(server.state_dir)
    session = login(server)

    real_health_signals = health_signals.health_signals
    real_health_state_from_signals = health_page.health_state_from_signals
    signals_calls = []
    state_calls = []

    def counting_health_signals(*args, **kwargs):
        signals_calls.append(1)
        return real_health_signals(*args, **kwargs)

    def counting_health_state_from_signals(*args, **kwargs):
        state_calls.append(1)
        return real_health_state_from_signals(*args, **kwargs)

    # See test_health_markup_builds_only_on_home_and_health()'s own
    # comment: health_signals() is patched on its defining module, since
    # safe_health_signals()'s bare-name call to it resolves there, never
    # on health_page's re-export.
    monkeypatch.setattr(health_signals, "health_signals", counting_health_signals)
    monkeypatch.setattr(
        health_page, "health_state_from_signals", counting_health_state_from_signals)

    status, _headers, body = http_request(server.url("/no-such-page"), cookie=session)
    assert status == 404, "expected 404 from an authenticated unknown route, got %d" % status
    dot_match = _NAV_DOT_RE.search(body)
    assert dot_match and dot_match.group(1) == b"dot--warn", (
        "expected an authenticated 404 to carry the warn nav dot for the seeded scenario")
    assert len(signals_calls) == 1, (
        "expected exactly one health_signals() call for an authenticated 404, got %d"
        % len(signals_calls))
    assert len(state_calls) == 0, (
        "expected zero health_state_from_signals() calls for a 404 - it never renders markup, "
        "got %d" % len(state_calls))

    signals_calls.clear()
    state_calls.clear()
    status2, _headers2, body2 = http_request(server.url("/no-such-page"))
    assert status2 == 404, "expected 404 from an unauthenticated unknown route, got %d" % status2
    assert _NAV_DOT_RE.search(body2) is None, (
        "expected no nav dot on an unauthenticated 404, even with a real warn scenario seeded")
    assert len(signals_calls) == 0, (
        "expected zero health_signals() calls for an unauthenticated 404 - Health's severity "
        "must never leak pre-auth, got %d" % len(signals_calls))
    assert len(state_calls) == 0


# ==========================================================================
# Expensive registries: lazy, at most once per request, shared where they
# overlap.
# ==========================================================================


def test_expensive_registries_load_lazily_at_most_once_per_request(
        app_server_in_process, monkeypatch):
    """gallery_entries, manual_resolutions.load_manual_resolutions, colour_rules.
    load_colour_rules and calendar_rules.load_calendar_registry (shared by three separate
    calendar_* ctx keys - config_page.render() reads all three) run at most once per request on
    every tab route; on /flights, the three Airlines/Display/Device-only registries never run at
    all, while gallery_entries runs exactly once (history_page.py itself reads
    ctx.get("gallery_entries"))"""
    server = app_server_in_process
    efficiency_probe.seed_history(server.state_dir)
    session = login(server)

    real_gallery = app.gallery_entries
    real_manual = manual_resolutions.load_manual_resolutions
    real_colour = colour_rules.load_colour_rules
    real_calendar = calendar_rules.load_calendar_registry

    counters = {"gallery": [], "manual": [], "colour": [], "calendar": []}

    def _wrap(name, real):
        def wrapper(*args, **kwargs):
            counters[name].append(1)
            return real(*args, **kwargs)
        return wrapper

    monkeypatch.setattr(app, "gallery_entries", _wrap("gallery", real_gallery))
    monkeypatch.setattr(
        manual_resolutions, "load_manual_resolutions", _wrap("manual", real_manual))
    monkeypatch.setattr(colour_rules, "load_colour_rules", _wrap("colour", real_colour))
    monkeypatch.setattr(
        calendar_rules, "load_calendar_registry", _wrap("calendar", real_calendar))

    for route in NAV_ROUTES:
        for calls in counters.values():
            calls.clear()
        status, _headers, _body = http_request(server.url(route), cookie=session)
        assert status == 200, "expected 200 from GET %s, got %d" % (route, status)
        for name, calls in counters.items():
            assert len(calls) <= 1, (
                "expected at most one %s load for GET %s, got %d" % (name, route, len(calls)))

    for calls in counters.values():
        calls.clear()
    status, _headers, _body = http_request(server.url(layout.FLIGHTS_ROUTE), cookie=session)
    assert status == 200, "expected 200 from GET /flights, got %d" % status
    assert len(counters["manual"]) == 0, (
        "expected zero manual-resolutions loads on Flights, got %d" % len(counters["manual"]))
    assert len(counters["colour"]) == 0, (
        "expected zero colour-rules loads on Flights, got %d" % len(counters["colour"]))
    assert len(counters["calendar"]) == 0, (
        "expected zero calendar-registry loads on Flights, got %d" % len(counters["calendar"]))
    assert len(counters["gallery"]) == 1, (
        "expected exactly one gallery load on Flights - history_page.py itself reads "
        "ctx.get('gallery_entries') - got %d" % len(counters["gallery"]))


# ==========================================================================
# A database fault degrades every page to 200 instead of 500ing it.
# ==========================================================================


def test_a_database_fault_degrades_every_page_to_200_instead_of_500ing(
        app_server_in_process, monkeypatch):
    """sqlite3.connect raising: GET /flights and GET / (neither of which ever reads
    poll_cooldown_remaining) still return 200 with their sections' own pre-existing unavailable
    blocks; GET /device (which does read it) also returns 200, with the poll-trigger button
    rendered enabled rather than the page 500ing over one meta-table read"""
    server = app_server_in_process
    session = login(server)  # succeeds before the fault is injected

    def _raising_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database unavailable (fault injected for this test)")

    monkeypatch.setattr(sqlite3, "connect", _raising_connect)

    status_home, _headers, _body = http_request(server.url(layout.HOME_ROUTE), cookie=session)
    assert status_home == 200, (
        "expected Home to degrade to 200 with the database unavailable, got %d" % status_home)

    status_flights, _headers2, _body2 = http_request(
        server.url(layout.FLIGHTS_ROUTE), cookie=session)
    assert status_flights == 200, (
        "expected Flights to degrade to 200 with the database unavailable, got %d"
        % status_flights)

    status_device, _headers3, body3 = http_request(server.url(layout.DEVICE_ROUTE), cookie=session)
    assert status_device == 200, (
        "expected Device to degrade to 200 with the database unavailable, got %d" % status_device)
    button_match = re.search(
        rb'<button type="submit" id="%s"[^>]*>' % config_page.POLL_TRIGGER_BUTTON_ID.encode(),
        body3)
    assert button_match, "expected the poll-trigger button to render at all on Device"
    assert b"disabled" not in button_match.group(0), (
        "expected poll_cooldown_remaining to degrade to 0 (an enabled button) rather than the "
        "database fault raising through the page render, got %r" % button_match.group(0))


# ==========================================================================
# A plain dict ctx (every existing page unit test's own shape) still works.
# ==========================================================================


def test_a_plain_dict_context_still_works_for_a_page_modules_render(tmp_path):
    """page_context() now returns a _LazyContext, but no page module may come to depend on that
    concrete type: a plain, ordinary dict built the way every existing page unit test does still
    renders correctly"""
    plain_ctx = {
        "state_dir": str(tmp_path), "device_config": {}, "poll_cooldown_remaining": 0,
        "ui_theme": "auto", "now": history_db.utc_now_iso(),
        "wake_interval_env_default": None,
    }
    body = config_page.render(plain_ctx, scope=config_page.SCOPE_DEVICE)
    assert config_page.POLL_TRIGGER_BUTTON_ID in body, (
        "expected config_page.render() to accept a plain dict ctx and still render the poll "
        "trigger button")
