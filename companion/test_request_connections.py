"""One SQLite connection per companion request.

`companion/app.py`'s `do_GET`/`do_POST` each open one
`history_db.connection_scope()` for the whole request, so however many of
the module's ~16 `open_db()` call sites a route touches, only one real
`sqlite3.connect()` ever happens - and a request that touches none (a
static asset, the login page, an unauthenticated tab's redirect) opens
zero. `POST /poll-now` shares that same connection with the whole poll
cycle it runs, since `poll_cycle.run_once()` nests its own
`connection_scope()` inside an already-active one for the same state
directory.

Counted against a REAL running companion/app.py (`app_server_in_process`,
the only fixture family whose `sqlite3.connect`/`history_db.init_schema`
monkeypatches - via `efficiency_probe.count_db()` - take effect in the
same interpreter the server thread runs in), never by reading source
text.
"""
import re
import sqlite3
import threading

import efficiency_probe

from companion import layout
from companion.pages import config_page
from companion_app_server import http_request, login
from server.plane import enrich

import companion.app as app

NAV_ROUTES = tuple(route for route, _label in layout.NAV_TABS)


def test_each_nav_tab_route_opens_exactly_one_connection_per_request(app_server_in_process):
    """a GET of every live NAV_TABS route opens exactly one connection, however many of the
    route's own open_db() call sites (page_context()'s reads plus the page module's own render())
    it touches"""
    server = app_server_in_process
    efficiency_probe.seed_history(server.state_dir)
    session = login(server)

    for route in NAV_ROUTES:
        with efficiency_probe.count_db() as counts:
            status, _headers, _body = http_request(server.url(route), cookie=session)
        assert status == 200, "expected 200 from GET %s, got %d" % (route, status)
        assert counts.connections == 1, (
            "expected exactly one connection for GET %s, got %d"
            % (route, counts.connections))


def test_static_login_and_unauthenticated_requests_open_no_connection(app_server_in_process):
    """a static asset, the pre-auth login page, and an unauthenticated tab's redirect-to-login
    never open a database connection at all"""
    server = app_server_in_process

    with efficiency_probe.count_db() as counts:
        status, _headers, _body = http_request(server.url("/static/style.css"))
    assert status == 200, "expected 200 from the stylesheet route, got %d" % status
    assert counts.connections == 0, (
        "expected zero connections for a static asset, got %d" % counts.connections)

    with efficiency_probe.count_db() as counts:
        status, _headers, _body = http_request(server.url(app.LOGIN_ROUTE))
    assert status == 200, "expected 200 from the login page, got %d" % status
    assert counts.connections == 0, (
        "expected zero connections for the pre-auth login page, got %d" % counts.connections)

    with efficiency_probe.count_db() as counts:
        status, _headers, _body = http_request(server.url(layout.HEALTH_ROUTE))
    assert status == 303, (
        "expected a 303 redirect to login for an unauthenticated tab, got %d" % status)
    assert counts.connections == 0, (
        "expected zero connections for an unauthenticated tab's redirect, got %d"
        % counts.connections)


def test_a_second_request_runs_init_schema_zero_times(app_server_in_process):
    """the schema/WAL-pragma guard (server/history_db.py's per-process _SCHEMA_READY) means a
    second request against an already-warm process never re-runs init_schema()"""
    server = app_server_in_process
    session = login(server)
    status, _headers, _body = http_request(server.url(layout.HOME_ROUTE), cookie=session)
    assert status == 200, "expected 200 warming up the first request, got %d" % status

    with efficiency_probe.count_db() as counts:
        status, _headers, _body = http_request(server.url(layout.HOME_ROUTE), cookie=session)
    assert status == 200, "expected 200 from the second request, got %d" % status
    assert counts.init_schema == 0, (
        "expected init_schema to run zero times on a second request against an already-warm "
        "process, got %d" % counts.init_schema)


def test_poll_now_uses_one_connection_for_the_whole_cycle_and_persists_the_cooldown(
        app_server_in_process, monkeypatch):
    """POST /poll-now shares its request's one connection with the whole poll cycle
    poll_cycle.run_once() performs, and the cooldown it writes to history.db's meta table is
    durable - a later GET (its own fresh request, its own fresh connection) still sees it"""
    server = app_server_in_process
    session = login(server)
    # An unresolved-callsign response, never a real HTTP call - matches
    # efficiency_probe.cycle_probe()'s own fake for exactly the same reason.
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))

    with efficiency_probe.fake_provider_latency(0.0), efficiency_probe.count_db() as counts:
        status, headers, _body = http_request(
            server.url(app.POLL_ROUTE), method="POST", cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=%s" % app.FLASH_KEY_POLL_TRIGGERED in location, (
        "expected the poll_triggered flash key, got %r" % location)
    assert counts.connections == 1, (
        "expected exactly one connection for the whole POST /poll-now request including the "
        "poll cycle it runs, got %d" % counts.connections)

    # A fresh request, on the same session: the Device page's poll button
    # renders disabled with a positive data-cooldown attribute only once the
    # trigger this test just made is visible from a brand-new connection.
    status2, _headers2, body2 = http_request(server.url(layout.DEVICE_ROUTE), cookie=session)
    assert status2 == 200, "expected 200 from the Device page, got %d" % status2
    match = re.search(
        rb'id="%s"[^>]*disabled[^>]*data-cooldown="(\d+)"'
        % config_page.POLL_TRIGGER_BUTTON_ID.encode(), body2)
    assert match, (
        "expected the Device page's poll button to render disabled with a data-cooldown "
        "attribute once the trigger's cooldown meta write is visible, got %r" % body2)
    assert int(match.group(1)) > 0, (
        "expected a positive cooldown remaining right after triggering a poll, got %r"
        % match.group(1))


def test_a_database_fault_attempts_the_connection_exactly_once_per_request(
        app_server_in_process, monkeypatch):
    """a database that cannot be opened (sqlite3.connect raising) is attempted exactly once for
    the whole request, however many of page_context()'s own call sites read the database before
    poll_cooldown_remaining() - unguarded today - re-raises the connection_scope()'s remembered
    failure; do not assert the response status here (the lazy-context plan makes this degrade to
    a normal 200, this plan only proves there is no retry storm)"""
    server = app_server_in_process
    session = login(server)  # succeeds before the fault is injected

    connect_attempts = []

    def _raising_connect(*args, **kwargs):
        connect_attempts.append(1)
        raise sqlite3.OperationalError("database unavailable (fault injected for this test)")

    monkeypatch.setattr(sqlite3, "connect", _raising_connect)
    try:
        http_request(server.url(layout.FLIGHTS_ROUTE), cookie=session)
    except Exception:
        # An unguarded call site re-raising the scope's remembered failure
        # breaks the connection rather than returning a response today -
        # this test only proves the retry count, not the response shape.
        pass
    assert len(connect_attempts) == 1, (
        "expected exactly one sqlite3.connect() attempt for the whole request despite several "
        "open_db() call sites reading the database, got %d (no retry storm)"
        % len(connect_attempts))


def test_two_concurrent_requests_each_get_their_own_connection(app_server_in_process):
    """two genuinely overlapping GETs, each on its own ThreadingHTTPServer request thread, each
    open their own connection (never sharing one across threads, and never a sqlite3
    ProgrammingError from a connection crossing a thread boundary)"""
    server = app_server_in_process
    session = login(server)

    start_event = threading.Event()
    results = []
    results_lock = threading.Lock()

    def _worker():
        start_event.wait()
        try:
            status, _headers, _body = http_request(server.url(layout.HOME_ROUTE), cookie=session)
        except Exception as exc:  # pragma: no cover - only on a real cross-thread failure
            with results_lock:
                results.append(exc)
            return
        with results_lock:
            results.append(status)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    with efficiency_probe.count_db() as counts:
        for t in threads:
            t.start()
        start_event.set()
        for t in threads:
            t.join(timeout=30)

    assert len(results) == 2, "expected two results, got %d: %r" % (len(results), results)
    for result in results:
        assert result == 200, "expected both concurrent requests to succeed with 200, got %r" % (
            results,)
    assert counts.connections == 2, (
        "expected each of the two concurrent requests to open its own connection, got %d"
        % counts.connections)
