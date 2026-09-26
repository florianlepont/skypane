"""Light freshness check: a conditional GET on a page's own URL, answered
with a bodiless 304 from a server-computed input token, with the page
never rendered to answer an unchanged tick.

`_page_freshness_token()` is built from the page's inputs alone (three
per-table MAX(id) watermarks, two meta keys, the shared `health_signals()`
snapshot, a handful of file stats, the newest gallery filename, lang, UI
theme, route and the raw query string - plus, for Home/Display, the
resolved frame state, for Health and Home, the pipeline-run meta key
(Home's Flight-data tile renders that same timestamp), and for Health,
the Europe/Paris date) - never from the rendered body. `_render_tab()`
checks it only after `require_session()`, and only for a request that
identifies itself with `X-Requested-With: freshness`.

Every behaviour here is asserted against a REAL running `companion/app.py`
(`app_server_in_process`, the only fixture family whose monkeypatches take
effect in the same interpreter the server thread runs in), never against
source text, matching `companion/test_page_context.py`'s own convention.

The `@pytest.mark.browser` tests below exercise `companion/static/freshness.js`
itself, through a real Chromium session driven by Playwright: the token
header round trip (If-None-Match sent, a 304 treated as success with no
swap), a changed tick's swap and token update, the periodic forced full
refresh, and the loaded-at bookkeeping a 304's own Date header drives.
"""
import email.utils
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import pytest

import companion.app as app
from companion import auth, layout
from companion.pages import health_page, history_page
from companion_app_server import http_request, login
from companion.test_browser_ux_helpers import _login, seed_state_dir
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


def test_identical_second_poll_cycle_leaves_display_and_flights_tokens_unchanged(
        app_server_in_process):
    """a second, identical poll_loop.run_once() cycle (fake providers, empty sky) leaves the
    Display and Flights tokens unchanged - Home and Health are both excluded here, since
    each renders last_pipeline_run as plain text (Health's Pipeline tile, Home's Flight-data
    tile), and that meta key genuinely advances every cycle"""
    import efficiency_probe

    server = app_server_in_process
    session = login(server)
    stable_routes = (layout.DISPLAY_ROUTE, layout.FLIGHTS_ROUTE)

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


def test_identical_second_poll_cycle_still_changes_the_home_token(app_server_in_process):
    """a second, identical poll_loop.run_once() cycle (fake providers, empty sky) still changes
    Home's own token - the Flight-data tile renders the same last_pipeline_run timestamp
    Health's Pipeline tile does, as plain text, so it must keep tracking that meta key even
    when nothing else about the cycle changed"""
    import efficiency_probe

    server = app_server_in_process
    session = login(server)

    efficiency_probe.cycle_probe(server.state_dir, latency_s=0, records=None)
    before_home = _token(server, layout.HOME_ROUTE, session)
    efficiency_probe.cycle_probe(server.state_dir, latency_s=0, records=None)
    after_home = _token(server, layout.HOME_ROUTE, session)

    assert after_home != before_home, (
        "expected /'s token to change after an identical empty-sky cycle, since the "
        "Flight-data tile's own pipeline-run timestamp still advances")


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


def test_pipeline_run_meta_advance_changes_health_and_home_tokens(app_server_in_process):
    """META_LAST_PIPELINE_RUN advancing (while the pipeline stays "ok" throughout, so its
    derived pipeline_state category never flips) still changes both Health's own token - the
    Pipeline tile - and Home's - the Flight-data tile renders the same raw timestamp as plain
    text via pipeline_detail_html, so it must track the meta value, not just its derived
    state. Flights never embeds the raw meta value at all, so its token is unaffected"""
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
    assert after_home != before_home, (
        "expected the pipeline-run advance to change / (the Flight-data tile's own timestamp)")
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


# ==========================================================================
# Browser: freshness.js's own token round trip, through a real Chromium
# session.
# ==========================================================================


def _recording_send_response(recorded):
    """A `send_response` wrapper recording `(code, If-None-Match,
    X-Requested-With)` for every response this Handler instance sends -
    the one seam every browser check below reads to prove what the
    REAL browser actually sent and received, without touching source
    text.
    """
    original = app.Handler.send_response

    def wrapper(self, code, message=None):
        recorded.append(
            (code, self.headers.get("If-None-Match"), self.headers.get("X-Requested-With")))
        return original(self, code, message)

    return wrapper


def _wait_for_freshness_hit(page, recorded, timeout_s=5, since=0):
    """Poll (real wall-clock time, never the page's virtualised clock)
    until MORE than `since` recorded responses carry the freshness
    X-Requested-With value - `since` lets a caller wait for the NEXT
    tick specifically, across a loop of several, rather than matching
    a tick a previous iteration already recorded.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline and len(
            [hit for hit in recorded if hit[2] == "freshness"]) <= since:
        page.wait_for_timeout(50)
    page.wait_for_timeout(50)  # let the fetch's own .then() handler finish running


@pytest.mark.browser
def test_an_unchanged_tick_gets_a_304_with_no_swap_and_no_failure_badge(
        app_server_in_process, monkeypatch, page):
    """/flights, unchanged state: after page.clock.run_for(46000) the server recorded a
    freshness request answered 304, the rows are unchanged, and no reconnecting/failure state
    is shown"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    server = app_server_in_process
    seed_state_dir(server.state_dir)

    recorded = []
    monkeypatch.setattr(app.Handler, "send_response", _recording_send_response(recorded))

    # Installed BEFORE the navigation below, so the interval
    # freshness.js's own script schedules on load is itself registered
    # against the fake clock from the start - installing it after the
    # page has already scheduled a real setInterval leaves that timer
    # running on the real clock, unaffected by run_for() below.
    _login(page, server.base_url())
    page.clock.install()
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_load_state("networkidle")
    rows_before = page.locator("[data-flight-id]").count()

    recorded.clear()
    page.clock.run_for(46000)
    _wait_for_freshness_hit(page, recorded)

    freshness_codes = [code for code, _inm, xrw in recorded if xrw == "freshness"]
    assert freshness_codes, "expected at least one freshness request on the unchanged page"
    assert all(code == 304 for code in freshness_codes), (
        "expected every freshness request on an unchanged page to be 304, got %r"
        % freshness_codes)

    badge = page.locator("[data-refresh-state-pill]")
    assert badge.count() == 0 or badge.get_attribute("hidden") is not None, (
        "expected no visible failure/reconnecting badge after a successful 304")
    rows_after = page.locator("[data-flight-id]").count()
    assert rows_after == rows_before, "expected the rows unchanged after an unchanged 304 tick"


@pytest.mark.browser
def test_a_changed_tick_swaps_in_the_new_row_and_updates_the_token(
        app_server_in_process, monkeypatch, page):
    """after seeding a new runway event, the next tick receives 200, the new row appears (the
    swap happened), and the body's data-refresh-token equals the new token"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    server = app_server_in_process
    seed_state_dir(server.state_dir)

    _login(page, server.base_url())
    page.clock.install()
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_load_state("networkidle")
    token_before = page.get_attribute("body", "data-refresh-token")

    with history_db.open_db(server.state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=history_db.utc_now_iso(), hex="39ffff", callsign="AFR999",
            aircraft_type="A320", confirmed_state="departure", corroborated=True,
            route_source="fresh_hit", airline="Air France", origin="ORY",
            destination="JFK", tracked_runway="3")

    page.clock.run_for(46000)
    # state="attached" (not the default "visible"): both the phone-card and
    # desktop-table renderings of a row are swapped every tick, and CSS
    # hides whichever one this fixture's own viewport does not use - the
    # DOM's presence is the swap proof, not on-screen visibility here.
    page.wait_for_selector("text=AFR999", state="attached", timeout=10000)

    token_after = page.get_attribute("body", "data-refresh-token")
    assert token_after != token_before, "expected the swap to carry a new data-refresh-token"


@pytest.mark.browser
def test_forced_full_refresh_lands_within_seven_ticks(app_server_in_process, monkeypatch, page):
    """across 7 consecutive ticks on an unchanged page, at least one freshness request carries
    no If-None-Match at all (a forced full refresh) and still gets 200"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    server = app_server_in_process
    seed_state_dir(server.state_dir)

    recorded = []
    monkeypatch.setattr(app.Handler, "send_response", _recording_send_response(recorded))

    _login(page, server.base_url())
    page.clock.install()
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_load_state("networkidle")

    recorded.clear()
    freshness_count = 0
    for _ in range(7):
        page.clock.run_for(46000)
        _wait_for_freshness_hit(page, recorded, timeout_s=5, since=freshness_count)
        freshness_count = len([hit for hit in recorded if hit[2] == "freshness"])

    freshness_hits = [(code, inm) for code, inm, xrw in recorded if xrw == "freshness"]
    assert len(freshness_hits) >= 7, (
        "expected at least 7 freshness ticks, got %d" % len(freshness_hits))
    forced = [hit for hit in freshness_hits if hit[1] is None]
    assert forced, (
        "expected at least one of 7 consecutive ticks to carry no If-None-Match at all "
        "(a forced full refresh), got %r" % freshness_hits)
    assert all(code == 200 for code, _inm in forced), (
        "expected a forced full refresh (no If-None-Match) to get 200, got %r" % forced)


@pytest.mark.browser
def test_a_304_updates_loaded_at_from_the_response_date_header(
        app_server_in_process, monkeypatch, page):
    """a 304's own Date header (not Date.now() at receipt time) is what freshness.js stores as
    loadedAtMs: forcing every Date header ten minutes stale and then simulating the tab's return
    from background triggers an IMMEDIATE catch-up freshness request - proof that loadedAtMs
    really carries the stale value the header named, not a fresh one"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    server = app_server_in_process
    seed_state_dir(server.state_dir)

    recorded = []
    monkeypatch.setattr(app.Handler, "send_response", _recording_send_response(recorded))

    stale_date = email.utils.formatdate(time.time() - 600, usegmt=True)
    original_send_header = app.Handler.send_header

    def stale_date_send_header(self, keyword, value):
        if keyword == "Date":
            value = stale_date
        return original_send_header(self, keyword, value)

    monkeypatch.setattr(app.Handler, "send_header", stale_date_send_header)

    _login(page, server.base_url())
    page.clock.install()
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_load_state("networkidle")

    recorded.clear()
    page.clock.run_for(46000)
    _wait_for_freshness_hit(page, recorded)
    assert any(code == 304 and xrw == "freshness" for code, _inm, xrw in recorded), (
        "expected a 304 freshness tick carrying the forced stale Date header")

    recorded.clear()
    page.evaluate(
        "() => {"
        "  Object.defineProperty(document, 'hidden',"
        "    {configurable: true, get: () => true});"
        "  document.dispatchEvent(new Event('visibilitychange'));"
        "}")
    page.evaluate(
        "() => {"
        "  Object.defineProperty(document, 'hidden',"
        "    {configurable: true, get: () => false});"
        "  document.dispatchEvent(new Event('visibilitychange'));"
        "}")
    _wait_for_freshness_hit(page, recorded)
    assert any(xrw == "freshness" for _code, _inm, xrw in recorded), (
        "expected the tab's return to trigger an immediate catch-up freshness request, proving "
        "loadedAtMs was set from the 304's own stale Date header rather than Date.now()")
