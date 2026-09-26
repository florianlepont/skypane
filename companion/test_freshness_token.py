"""Light freshness check: a conditional GET on a page's own URL, answered
with a bodiless 304 from a server-computed input token, with the page
never rendered to answer an unchanged tick.

`_page_freshness_token()` is built from the page's inputs alone (three
per-table MAX(id) watermarks, two meta keys, the shared `health_signals()`
snapshot, a handful of file stats, the newest gallery filename, lang, UI
theme, route and the raw query string - plus, for Home/Display, the
resolved frame state, and for Health, the pipeline-run meta key and the
Europe/Paris date) - never from the rendered body. `_render_tab()` checks
it only after `require_session()`, and only for a request that identifies
itself with `X-Requested-With: freshness`.

Every behaviour here is asserted against a REAL running `companion/app.py`
(`app_server_in_process`, the only fixture family whose monkeypatches take
effect in the same interpreter the server thread runs in), never against
source text, matching `companion/test_page_context.py`'s own convention.
"""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import companion.app as app
from companion import auth, layout
from companion.pages import health_page, history_page
from companion_app_server import http_request, login
from server import device_config, history_db

_ETAG_RE = re.compile(r'^"[0-9a-f]{32}"$')
_TOKEN_ATTR_RE = re.compile(r'data-refresh-token="([0-9a-f]{32})"')

_FRESHNESS_ROUTES = (
    layout.HOME_ROUTE, layout.DISPLAY_ROUTE, layout.HEALTH_ROUTE, layout.FLIGHTS_ROUTE,
)


def _get(server, route, cookie, extra_headers=None):
    return http_request(server.url(route), cookie=cookie, extra_headers=extra_headers)


def _token(server, route, cookie):
    """GET `route` and return its ETag's bare 32-hex token, asserting the
    ETag and the `data-refresh-token` body attribute agree.
    """
    status, headers, body = _get(server, route, cookie)
    assert status == 200, "expected 200 from GET %s, got %d" % (route, status)
    etag = headers.get("ETag", "")
    assert _ETAG_RE.match(etag), "expected a quoted 32-hex ETag from %s, got %r" % (route, etag)
    match = _TOKEN_ATTR_RE.search(body.decode("utf-8"))
    assert match, "expected a data-refresh-token attribute on %s" % (route,)
    assert '"%s"' % match.group(1) == etag, (
        "expected the body's data-refresh-token to equal the ETag on %s" % (route,))
    return match.group(1)


# ==========================================================================
# Shape: ETag/body-attribute agreement on the four refresh pages; neither
# on Device/Airlines.
# ==========================================================================


def test_every_refresh_page_carries_an_etag_matching_its_body_token(app_server_in_process):
    """/, /display, /health and /flights each carry a 32-hex ETag equal to the body's
    data-refresh-token attribute"""
    server = app_server_in_process
    session = login(server)
    for route in _FRESHNESS_ROUTES:
        _token(server, route, session)  # raises on any mismatch


def test_device_and_airlines_carry_neither_etag_nor_refresh_token(app_server_in_process):
    """/device and /airlines are not refresh pages: no ETag header, no data-refresh-token
    attribute at all"""
    server = app_server_in_process
    session = login(server)
    for route in (layout.DEVICE_ROUTE, layout.AIRLINES_ROUTE):
        status, headers, body = _get(server, route, session)
        assert status == 200, "expected 200 from GET %s, got %d" % (route, status)
        assert "ETag" not in headers, "expected no ETag on %s, got %r" % (route, headers)
        assert "data-refresh-token" not in body.decode("utf-8"), (
            "expected no data-refresh-token attribute on %s" % (route,))


# ==========================================================================
# The 304 path itself.
# ==========================================================================


def test_matching_freshness_conditional_gets_304_without_calling_render(
        app_server_in_process, monkeypatch):
    """a freshness tick (X-Requested-With: freshness) whose If-None-Match already matches gets a
    bodiless 304 (same ETag, Cache-Control: no-store, hardening headers), and history_page.render
    - Flights' own render() - is never called for it"""
    server = app_server_in_process
    session = login(server)

    real_render = history_page.render
    calls = []

    def counting_render(*args, **kwargs):
        calls.append(1)
        return real_render(*args, **kwargs)

    monkeypatch.setattr(history_page, "render", counting_render)

    status, headers, _body = _get(server, layout.FLIGHTS_ROUTE, session)
    assert status == 200, "expected 200 on the first GET, got %d" % status
    assert len(calls) == 1, "expected exactly one render() call on the first GET, got %d" % (
        len(calls),)
    etag = headers["ETag"]

    calls.clear()
    status2, headers2, body2 = _get(
        server, layout.FLIGHTS_ROUTE, session,
        extra_headers={"X-Requested-With": "freshness", "If-None-Match": etag})
    assert status2 == 304, "expected 304 on the matching freshness tick, got %d" % status2
    assert body2 == b"", "expected an empty body on 304, got %d bytes" % len(body2)
    assert headers2.get("ETag") == etag, "expected the same ETag on the 304"
    assert headers2.get("Cache-Control") == "no-store"
    assert headers2.get("X-Content-Type-Options") == "nosniff"
    assert headers2.get("X-Frame-Options") == "DENY"
    assert len(calls) == 0, (
        "expected render() to be skipped entirely on a matching 304, got %d calls" % len(calls))


def test_matching_if_none_match_without_the_freshness_header_still_gets_200(
        app_server_in_process):
    """a normal navigation (no X-Requested-With: freshness) carrying a stale but matching
    If-None-Match is never answered 304 - only a request that identifies itself as a freshness
    tick is eligible"""
    server = app_server_in_process
    session = login(server)
    etag_before = None
    status, headers, _body = _get(server, layout.HOME_ROUTE, session)
    assert status == 200
    etag_before = headers["ETag"]

    status2, headers2, body2 = _get(
        server, layout.HOME_ROUTE, session, extra_headers={"If-None-Match": etag_before})
    assert status2 == 200, (
        "expected 200 for a matching If-None-Match with no freshness header, got %d" % status2)
    assert body2, "expected a real HTML body, not a 304's empty one"


def test_unauthenticated_freshness_request_gets_login_redirect_never_a_304(
        app_server_in_process, monkeypatch):
    """an unauthenticated freshness-tick-shaped request (any If-None-Match) gets the ordinary
    303-to-/login redirect, and _page_freshness_token() is never called - the conditional check
    runs only after require_session()"""
    server = app_server_in_process

    real_token_fn = app._page_freshness_token
    calls = []

    def counting_token(*args, **kwargs):
        calls.append(1)
        return real_token_fn(*args, **kwargs)

    monkeypatch.setattr(app, "_page_freshness_token", counting_token)

    status, headers, _body = _get(
        server, layout.FLIGHTS_ROUTE, cookie=None,
        extra_headers={
            "X-Requested-With": "freshness",
            "If-None-Match": '"deadbeefdeadbeefdeadbeefdeadbeef"',
        })
    assert status == 303, "expected a login redirect, got %d" % status
    assert headers.get("Location", "").startswith(app.LOGIN_ROUTE)
    assert len(calls) == 0, (
        "expected zero _page_freshness_token() calls pre-auth, got %d" % len(calls))


# ==========================================================================
# Stability: no change -> same token, across both a page reload and a
# repeated, identical poll cycle.
# ==========================================================================


def test_two_requests_with_no_change_get_the_same_token(app_server_in_process):
    """two GETs of the same refresh page with nothing changed in between produce the same
    token"""
    server = app_server_in_process
    session = login(server)
    for route in _FRESHNESS_ROUTES:
        first = _token(server, route, session)
        second = _token(server, route, session)
        assert first == second, "expected a stable token for %s, got %r then %r" % (
            route, first, second)


def test_identical_second_poll_cycle_leaves_home_display_flights_tokens_unchanged(
        app_server_in_process):
    """a second, identical poll_loop.run_once() cycle (fake providers, empty sky) leaves the
    Home, Display and Flights tokens unchanged - Health is excluded, since its own
    last_pipeline_run meta key genuinely advances every cycle"""
    import efficiency_probe

    server = app_server_in_process
    session = login(server)
    stable_routes = (layout.HOME_ROUTE, layout.DISPLAY_ROUTE, layout.FLIGHTS_ROUTE)

    # The first cycle establishes state (panel.bin written, meta rows set);
    # only the SECOND, identical cycle is the "nothing changed" case the
    # must-have describes.
    efficiency_probe.cycle_probe(server.state_dir, latency_s=0, records=None)
    before = {route: _token(server, route, session) for route in stable_routes}
    efficiency_probe.cycle_probe(server.state_dir, latency_s=0, records=None)
    after = {route: _token(server, route, session) for route in stable_routes}

    for route in stable_routes:
        assert before[route] == after[route], (
            "expected %s's token unchanged after two identical empty-sky cycles, got %r then %r"
            % (route, before[route], after[route]))


# ==========================================================================
# A database fault still answers 200 with a token, never a 500.
# ==========================================================================


def test_a_database_fault_still_returns_200_with_a_token(app_server_in_process, monkeypatch):
    """sqlite3.connect raising: every refresh page still answers 200 with a well-shaped token -
    the literal "unavailable" is hashed into it, never raised through the response"""
    server = app_server_in_process
    session = login(server)  # succeeds before the fault is injected

    def _raising_connect(*args, **kwargs):
        raise sqlite3.OperationalError("database unavailable (fault injected for this test)")

    monkeypatch.setattr(sqlite3, "connect", _raising_connect)

    for route in _FRESHNESS_ROUTES:
        status, headers, body = _get(server, route, session)
        assert status == 200, "expected 200 from GET %s with the database down, got %d" % (
            route, status)
        etag = headers.get("ETag", "")
        assert _ETAG_RE.match(etag), (
            "expected a well-shaped token from %s even with the database down, got %r"
            % (route, etag))
        assert _TOKEN_ATTR_RE.search(body.decode("utf-8")), (
            "expected a data-refresh-token attribute from %s even with the database down"
            % (route,))


# ==========================================================================
# Completeness: each input, mutated alone, changes the token on its
# affected route(s).
# ==========================================================================


def _seed_history_row(state_dir, callsign="AFR900"):
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, hex="39a1b2", callsign=callsign, aircraft_type="A320",
            confirmed_state="departure", corroborated=True, route_source="fresh_hit",
            airline="Air France", origin="ORY", destination="JFK", tracked_runway="3")


def test_new_runway_event_changes_flights_and_home_tokens(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before_flights = _token(server, layout.FLIGHTS_ROUTE, session)
    before_home = _token(server, layout.HOME_ROUTE, session)

    _seed_history_row(server.state_dir)

    after_flights = _token(server, layout.FLIGHTS_ROUTE, session)
    after_home = _token(server, layout.HOME_ROUTE, session)
    assert after_flights != before_flights, "expected a new runway event to change /flights"
    assert after_home != before_home, "expected a new runway event to change /"


def test_new_device_health_row_changes_home_and_health_tokens(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before_home = _token(server, layout.HOME_ROUTE, session)
    before_health = _token(server, layout.HEALTH_ROUTE, session)

    with history_db.open_db(server.state_dir) as conn:
        history_db.record_device_health(
            conn, ts=history_db.utc_now_iso(), battery_mv=4100, fw_version="1.0.0",
            boot_reason="timer", rssi="-55")

    after_home = _token(server, layout.HOME_ROUTE, session)
    after_health = _token(server, layout.HEALTH_ROUTE, session)
    assert after_home != before_home, "expected a new device_health row to change /"
    assert after_health != before_health, "expected a new device_health row to change /health"


def test_device_config_save_changes_display_and_home_tokens(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before_display = _token(server, layout.DISPLAY_ROUTE, session)
    before_home = _token(server, layout.HOME_ROUTE, session)

    device_config.save_device_config(server.state_dir, quiet_hours_enabled=True)

    after_display = _token(server, layout.DISPLAY_ROUTE, session)
    after_home = _token(server, layout.HOME_ROUTE, session)
    assert after_display != before_display, "expected a device_config save to change /display"
    assert after_home != before_home, "expected a device_config save to change /"


def test_new_gallery_png_changes_flights_token(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before = _token(server, layout.FLIGHTS_ROUTE, session)

    gallery_dir = os.path.join(server.state_dir, app.GALLERY_DIRNAME)
    os.makedirs(gallery_dir, exist_ok=True)
    with open(os.path.join(gallery_dir, "99999999T999999Z.png"), "wb") as fh:
        fh.write(b"not-a-real-png-but-thats-fine-for-this-test")

    after = _token(server, layout.FLIGHTS_ROUTE, session)
    assert after != before, "expected a new gallery PNG to change /flights"


def test_offbox_marker_touched_changes_health_token(app_server_in_process, monkeypatch):
    server = app_server_in_process
    session = login(server)
    marker_path = os.path.join(server.state_dir, "offbox-marker.txt")
    monkeypatch.setenv(health_page.OFFBOX_MARKER_ENV_VAR, marker_path)
    with open(marker_path, "w") as fh:
        fh.write("skypane-state-20260101T000000Z.tar.gz")

    before = _token(server, layout.HEALTH_ROUTE, session)

    with open(marker_path, "w") as fh:
        fh.write("skypane-state-20260102T000000Z.tar.gz")

    after = _token(server, layout.HEALTH_ROUTE, session)
    assert after != before, "expected touching the off-box marker to change /health"


def test_staleness_threshold_crossed_changes_health_and_home_tokens(
        app_server_in_process, monkeypatch):
    """monkeypatching history_db.utc_now_iso() forward, past every staleness floor, changes
    both /health (the tile verdicts) and / (the shared signals snapshot, and the frame-strip's
    own resolved state)"""
    server = app_server_in_process
    session = login(server)
    with history_db.open_db(server.state_dir) as conn:
        history_db.record_device_health(
            conn, ts=history_db.utc_now_iso(), battery_mv=4000, fw_version="1.0.0",
            boot_reason="timer", rssi="-60")

    before_health = _token(server, layout.HEALTH_ROUTE, session)
    before_home = _token(server, layout.HOME_ROUTE, session)

    future = datetime.now(timezone.utc) + timedelta(hours=2)
    future_iso = future.isoformat(timespec="seconds")

    def fake_utc_now_iso():
        return future_iso

    monkeypatch.setattr(history_db, "utc_now_iso", fake_utc_now_iso)

    after_health = _token(server, layout.HEALTH_ROUTE, session)
    after_home = _token(server, layout.HOME_ROUTE, session)
    assert after_health != before_health, "expected a 2h time jump to change /health"
    assert after_home != before_home, "expected a 2h time jump to change /"


def test_pipeline_run_meta_advance_changes_only_health_token(app_server_in_process):
    """META_LAST_PIPELINE_RUN advancing (while the pipeline stays "ok" throughout, so its
    derived state category never flips) changes only Health's own token - Home/Flights never
    embed the raw meta value, only the derived pipeline_state, which does not change here"""
    server = app_server_in_process
    session = login(server)
    base = datetime.now(timezone.utc)
    first_run = (base - timedelta(seconds=20)).isoformat(timespec="seconds")
    second_run = (base - timedelta(seconds=10)).isoformat(timespec="seconds")

    with history_db.open_db(server.state_dir) as conn:
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, first_run)

    before_health = _token(server, layout.HEALTH_ROUTE, session)
    before_home = _token(server, layout.HOME_ROUTE, session)
    before_flights = _token(server, layout.FLIGHTS_ROUTE, session)

    with history_db.open_db(server.state_dir) as conn:
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, second_run)

    after_health = _token(server, layout.HEALTH_ROUTE, session)
    after_home = _token(server, layout.HOME_ROUTE, session)
    after_flights = _token(server, layout.FLIGHTS_ROUTE, session)

    assert after_health != before_health, "expected the pipeline-run advance to change /health"
    assert after_home == before_home, "expected / to be unaffected by the pipeline-run advance"
    assert after_flights == before_flights, (
        "expected /flights to be unaffected by the pipeline-run advance")


def test_lang_cookie_changes_the_token(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before = _token(server, layout.HEALTH_ROUTE, session)

    fr_cookie = session + "; " + auth.UI_LANG_COOKIE_NAME + "=fr"
    after = _token(server, layout.HEALTH_ROUTE, fr_cookie)
    assert after != before, "expected the lang cookie to change the token"


def test_theme_cookie_changes_the_token(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    before = _token(server, layout.DISPLAY_ROUTE, session)

    dark_cookie = session + "; " + auth.UI_THEME_COOKIE_NAME + "=dark"
    after = _token(server, layout.DISPLAY_ROUTE, dark_cookie)
    assert after != before, "expected the theme cookie to change the token"


def test_flights_limit_query_changes_the_token(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    status, headers, body = _get(server, layout.FLIGHTS_ROUTE, session)
    assert status == 200
    before = _TOKEN_ATTR_RE.search(body.decode("utf-8")).group(1)

    status2, headers2, body2 = _get(
        server, layout.FLIGHTS_ROUTE + "?" + history_page.FLIGHTS_LIMIT_QUERY_PARAM + "=5",
        session)
    assert status2 == 200
    after = _TOKEN_ATTR_RE.search(body2.decode("utf-8")).group(1)
    assert after != before, "expected the ?limit= query string to change the token"
