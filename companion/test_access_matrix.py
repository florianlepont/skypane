"""Default-deny proof: every route in `routes.ROUTES` against every kind of
caller, plus the owner dimension on a test-only device-scoped probe family.

Three layers:
- a pure layer calling `access.decide` for each route x principal cell;
- a completeness check that fails, naming the route, when a route exists
  that the hand-written policy table below does not list;
- an HTTP layer over a real in-process server whose handlers are all
  replaced by recording stubs, so a request that is allowed proves it
  reached the handler and a refused one proves the handler never ran.

The policy table is written by hand and states the intended policy per
route independently of each route's own `access` field. When a real
device-scoped route (`/d/<id>/...`) is added to the table it needs a row
here; the completeness test names the missing route.

Routes that act on one device also resolve under `/devices/<id>/...`. The
hand-written `DEVICE_SCOPED` set names them, and each is exercised under a
real device prefix with the same expectation as its un-prefixed counterpart:
anonymous is sent to sign-in, a role below the route's minimum gets the
unknown-path 404, and the device is only looked up after that decision (an
anonymous caller gets the same sign-in redirect for an unknown id).
"""
import time

import pytest

from companion import access, app, auth, routes, static_files
from companion_app_server import (
    InProcessAppServer, auth0_env, http_request,
    login_via_auth0)
from fake_auth0 import FakeAuth0
from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, REACHED_BODY, Recorder, probe_path,
    probe_routes, seed_matrix_fleet, session_cookie_for, stub_routes)
import matrix_rows_lifecycle
import matrix_rows_locations
import matrix_rows_pairing
import matrix_rows_users
from server import fleet_db, fleet_sessions

# --- the hand-written policy -------------------------------------------------

PUBLIC = "public"
SIGNED_IN = "signed-in"
ADMIN_ONLY = "admin-only"
OWNER_DEVICE = "owner-device"

_PUBLIC_PATHS = ("/login", "/login/auth0", "/callback")
_STATIC_PATHS = tuple(static_files.STATIC_ROUTES)

ROUTE_POLICY = {
    ("GET", "/login"): PUBLIC,
    ("GET", "/login/auth0"): PUBLIC,
    ("GET", "/callback"): PUBLIC,
    ("GET", "/credits"): PUBLIC,
    # Self-authenticating: the handler checks its own bearer token and never
    # looks at a session cookie, so the cookie gate has nothing to add.
    ("GET", "/api/export/battery-history"): PUBLIC,
    ("GET", "/account"): SIGNED_IN,
    ("POST", "/ui-theme"): SIGNED_IN,
    ("POST", "/ui-lang"): SIGNED_IN,
    ("POST", "/logout"): SIGNED_IN,
    ("GET", "/"): OWNER_DEVICE,
    ("GET", "/display"): OWNER_DEVICE,
    ("GET", "/device"): ADMIN_ONLY,
    ("GET", "/detection"): OWNER_DEVICE,
    ("GET", "/flights"): OWNER_DEVICE,
    ("GET", "/health"): OWNER_DEVICE,
    ("GET", "/airlines"): OWNER_DEVICE,
    ("GET", "/update"): ADMIN_ONLY,
    ("GET", "/settings"): OWNER_DEVICE,
    ("GET", "/history"): OWNER_DEVICE,
    ("GET", "/preview"): OWNER_DEVICE,
    ("GET", "/gallery/{}"): OWNER_DEVICE,
    ("GET", "/runway-image/{}.png"): ADMIN_ONLY,
    ("GET", "/illustration/{}.png"): OWNER_DEVICE,
    ("GET", "/theme-preview/{}.png"): OWNER_DEVICE,
    ("GET", "/frame-preview/{}.png"): OWNER_DEVICE,
    ("POST", "/settings"): OWNER_DEVICE,
    ("POST", "/detection"): OWNER_DEVICE,
    ("POST", "/quick/display"): OWNER_DEVICE,
    ("POST", "/quick/quiet-hours"): OWNER_DEVICE,
    ("POST", "/quick/led"): ADMIN_ONLY,
    ("POST", "/airlines/resolve"): OWNER_DEVICE,
    ("POST", "/airlines/rename"): OWNER_DEVICE,
    ("POST", "/airlines/rename/reset"): OWNER_DEVICE,
    ("POST", "/airlines/manual-resolutions/{}/delete"): OWNER_DEVICE,
    ("POST", "/illustration/{}.png"): OWNER_DEVICE,
    ("POST", "/settings/rules/add"): OWNER_DEVICE,
    ("POST", "/settings/calendar/disconnect"): OWNER_DEVICE,
    ("POST", "/settings/calendar/connect"): OWNER_DEVICE,
    ("POST", "/update/install"): ADMIN_ONLY,
    ("POST", "/update/cancel"): ADMIN_ONLY,
    ("POST", "/settings/rules/{}/delete"): OWNER_DEVICE,
}
ROUTE_POLICY.update({("GET", path): PUBLIC for path in _STATIC_PATHS})

# The routes that act on one device and so also resolve under a
# `/devices/<id>` prefix. Every other route must refuse the prefix.
DEVICE_SCOPED = frozenset(
    [("GET", path) for path in (
        "/", "/display", "/detection", "/device", "/flights", "/health", "/airlines",
        "/settings", "/history", "/preview", "/gallery/{}",
        "/illustration/{}.png", "/theme-preview/{}.png",
        "/frame-preview/{}.png")]
    + [("POST", path) for path in (
        "/settings", "/detection", "/quick/display", "/quick/quiet-hours",
        "/quick/led", "/airlines/resolve", "/airlines/rename",
        "/airlines/rename/reset", "/airlines/manual-resolutions/{}/delete",
        "/illustration/{}.png", "/settings/rules/add",
        "/settings/calendar/disconnect", "/settings/calendar/connect",
        "/settings/rules/{}/delete")])

# Policy -> principal -> outcome, hand-written. A disabled, deleted or
# expired session resolves to no principal, so it reads as anonymous.
OUTCOMES = {
    PUBLIC: {
        "anonymous": "allow", "owner": "allow", "other": "allow",
        "admin": "allow"},
    SIGNED_IN: {
        "anonymous": "login", "owner": "allow", "other": "allow",
        "admin": "allow"},
    ADMIN_ONLY: {
        "anonymous": "login", "owner": "not-found", "other": "not-found",
        "admin": "allow"},
    OWNER_DEVICE: {
        "anonymous": "login", "owner": "allow", "other": "not-found",
        "admin": "allow"},
}
# The un-prefixed form of a device-scoped route acts on the live frame and is
# admin-only for every policy kind.
UNPREFIXED_OUTCOMES = {
    "anonymous": "login", "owner": "not-found", "other": "not-found",
    "admin": "allow"}
PRINCIPAL_NAMES = ("anonymous", "owner", "other", "admin")

# The kinds whose prefixed form reaches a frame only through the ownership gate.
_MIN_ROLE_OF_KIND = {
    PUBLIC: access.ANONYMOUS, SIGNED_IN: access.USER, ADMIN_ONLY: access.ADMIN,
    OWNER_DEVICE: access.USER}

MALFORMED_IDS = (
    "d_ZZZZZZZZ", "..", "d_" + "0" * 40, "a/b", "d_0000000", "D_00000000", "",
    "d_00000000/..",
)
UNKNOWN_ID = "d_00000000"

# One concrete middle per templated route.
SAMPLE_MIDDLE = {
    "/gallery/{}": "sample.png",
    "/runway-image/{}.png": "09",
    "/illustration/{}.png": "air-france",
    "/theme-preview/{}.png": "midnight",
    "/frame-preview/{}.png": "white",
    "/airlines/manual-resolutions/{}/delete": "RYR",
    "/settings/rules/{}/delete": "callsign/AFR",
}

# The console areas keep their own rows in test-support/matrix_rows_*.py so
# each can be filled in without touching this file.
for _rows in (
        matrix_rows_pairing, matrix_rows_lifecycle, matrix_rows_users,
        matrix_rows_locations):
    ROUTE_POLICY.update(_rows.ROWS)
    SAMPLE_MIDDLE.update(_rows.SAMPLES)


def _template(route):
    matcher = route.matcher
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return matcher.prefix + "{}" + matcher.suffix


def _route_key(route):
    return (route.method, _template(route))


def _sample_path(key):
    template = key[1]
    if "{}" not in template:
        return template
    return template.replace("{}", SAMPLE_MIDDLE[template])


def _sample_path_for(route):
    """KeyError naming the template when a templated route has no sample."""
    return _sample_path(_route_key(route))


_REAL_ROUTES = tuple(routes.ROUTES)
_REAL_KEYS = [_route_key(r) for r in _REAL_ROUTES]
_CELLS = [(key, name) for key in _REAL_KEYS for name in PRINCIPAL_NAMES]
_CELL_IDS = [
    "%s_%s_%s" % (key[0], key[1].strip("/").replace("/", "_") or "root", name)
    for key, name in _CELLS]
_SCOPED_KEYS = [key for key in _REAL_KEYS if key in DEVICE_SCOPED]
_UNSCOPED_KEYS = [key for key in _REAL_KEYS if key not in DEVICE_SCOPED]
_SCOPED_CELLS = [(key, name) for key in _SCOPED_KEYS for name in PRINCIPAL_NAMES]
_SCOPED_CELL_IDS = [
    "%s_%s_%s" % (key[0], key[1].strip("/").replace("/", "_") or "root", name)
    for key, name in _SCOPED_CELLS]

# --- completeness ------------------------------------------------------------


def test_every_route_has_a_policy_row_and_every_row_has_a_route():
    actual = set(_REAL_KEYS)
    expected = set(ROUTE_POLICY)
    missing = sorted(actual - expected)
    stale = sorted(expected - actual)
    assert not missing, (
        "routes with no expectation row, add them to ROUTE_POLICY in "
        "companion/test_access_matrix.py (and a sample middle if the path "
        "is templated): %r" % (missing,))
    assert not stale, "policy rows with no route in routes.ROUTES: %r" % (stale,)


def test_poll_now_is_not_a_route_at_any_prefix():
    assert ("POST", "/poll-now") not in set(_REAL_KEYS)
    assert routes.match("POST", "/poll-now", "") is None
    assert routes.match("POST", "/devices/d_00000000/poll-now", "") is None


def test_no_route_is_declared_twice():
    assert len(_REAL_KEYS) == len(set(_REAL_KEYS))


def test_the_device_scoped_set_is_exactly_the_hand_written_one():
    actual = {_route_key(r) for r in _REAL_ROUTES if r.device_scoped}
    assert actual == DEVICE_SCOPED
    assert DEVICE_SCOPED <= set(ROUTE_POLICY)


def test_no_public_route_resolves_under_a_device_prefix():
    for route in _REAL_ROUTES:
        if route.device_scoped:
            assert route.access.min_role != access.ANONYMOUS


def test_a_prefixed_route_never_has_less_access_than_its_base_route():
    for key in _SCOPED_KEYS:
        base = next(r for r in _REAL_ROUTES if _route_key(r) == key)
        prefixed, match = routes.match(
            key[0], "/devices/d_00000000" + _sample_path(key), "")
        assert match.device_id == "d_00000000"
        assert prefixed.access.min_role == base.access.min_role
        assert prefixed.access.min_role == _MIN_ROLE_OF_KIND[ROUTE_POLICY[key]]
        expected_arg = "device" if ROUTE_POLICY[key] == OWNER_DEVICE else None
        assert prefixed.access.device_arg == expected_arg
        # The un-prefixed form acts on the live frame: admin-only, no id.
        base_route, base_match = routes.match(key[0], _sample_path(key), "")
        assert app._effective_access(base_route, base_match) == (routes.ADMIN_ONLY, None)
        effective, captured = app._effective_access(prefixed, match)
        assert effective == prefixed.access and captured == "d_00000000"


def test_a_dummy_route_without_a_row_is_reported(monkeypatch):
    dummy = routes.Route(
        "GET", routes.Exact("/zz-new-page"), lambda h, m: None, routes.ADMIN_ONLY)
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (dummy,))
    keys = {_route_key(r) for r in routes.ROUTES}
    assert ("GET", "/zz-new-page") in keys - set(ROUTE_POLICY)


def test_a_console_route_without_a_row_is_reported_by_name(monkeypatch):
    dummy = routes.Route(
        "GET", routes.Exact("/zz-console-page"), lambda h, m: None, routes.ADMIN_ONLY)
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (dummy,))
    keys = {_route_key(r) for r in routes.ROUTES}
    assert ("GET", "/zz-console-page") in keys - set(ROUTE_POLICY)


def test_the_console_row_modules_are_merged_into_the_matrix():
    for module in (
            matrix_rows_pairing, matrix_rows_lifecycle, matrix_rows_users,
            matrix_rows_locations):
        for key, kind in module.ROWS.items():
            assert ROUTE_POLICY[key] == kind
        for template, middle in module.SAMPLES.items():
            assert SAMPLE_MIDDLE[template] == middle


def test_the_export_route_is_the_only_api_route_and_is_public_and_global():
    export_key = ("GET", "/api/export/battery-history")
    api_keys = {key for key in _REAL_KEYS if key[1].startswith("/api/")}
    assert api_keys == {export_key}
    route = next(r for r in _REAL_ROUTES if _route_key(r) == export_key)
    assert route.access == routes.PUBLIC
    assert not route.device_scoped
    assert export_key not in DEVICE_SCOPED
    assert routes.match("GET", "/devices/d_00000000" + export_key[1], "") is None
    assert routes.match("POST", export_key[1], "") is None


def test_the_probe_family_is_not_in_the_production_table():
    assert all(not _template(r).startswith("/d/") for r in _REAL_ROUTES)


# --- pure layer --------------------------------------------------------------

_PRINCIPALS = {
    "anonymous": None,
    "owner": access.Principal(access.KIND_USER, 1, OWNER_EMAIL, "user"),
    "other": access.Principal(access.KIND_USER, 2, OTHER_EMAIL, "user"),
    "admin": access.Principal(access.KIND_USER, 3, ADMIN_EMAIL, "admin"),
}
_DECISION_WORDS = {
    access.ALLOW: "allow", access.LOGIN: "login", access.NOT_FOUND: "not-found"}


_PURE_DEVICE = "d_0000beef"


def _never_owner(_device_id):
    raise AssertionError("a global route must not look up a device owner")


def _owner_one(device_id):
    return 1 if device_id == _PURE_DEVICE else None


def _pure_outcome(principal, method, path, owner_lookup):
    route, route_match = routes.match(method, path, "")
    route_access, captured = app._effective_access(route, route_match)
    return _DECISION_WORDS[
        access.decide(principal, route_access, captured, owner_lookup)]


@pytest.mark.parametrize("key,name", _CELLS, ids=_CELL_IDS)
def test_decide_matches_the_policy_table(key, name):
    scoped = key in DEVICE_SCOPED
    outcome = _pure_outcome(
        _PRINCIPALS[name], key[0], _sample_path(key),
        _never_owner if not scoped else _owner_one)
    expected = (
        UNPREFIXED_OUTCOMES[name] if scoped else OUTCOMES[ROUTE_POLICY[key]][name])
    assert outcome == expected


@pytest.mark.parametrize("key,name", _SCOPED_CELLS, ids=_SCOPED_CELL_IDS)
def test_decide_matches_the_policy_table_under_a_device_prefix(key, name):
    outcome = _pure_outcome(
        _PRINCIPALS[name], key[0], "/devices/%s%s" % (_PURE_DEVICE, _sample_path(key)),
        _owner_one)
    assert outcome == OUTCOMES[ROUTE_POLICY[key]][name]


def test_the_owner_gate_is_never_asked_about_a_foreign_or_unknown_id_as_owner():
    for device_id in ("d_00000000", "d_1111beef"):
        for key in _SCOPED_KEYS:
            if ROUTE_POLICY[key] != OWNER_DEVICE:
                continue
            outcome = _pure_outcome(
                _PRINCIPALS["owner"], key[0],
                "/devices/%s%s" % (device_id, _sample_path(key)), _owner_one)
            assert outcome == "not-found"


def test_every_templated_route_has_a_sample_middle():
    for route in _REAL_ROUTES:
        _sample_path_for(route)


# --- HTTP layer --------------------------------------------------------------

class MatrixRig:
    def __init__(self, server, fake, fleet, cookies):
        self.server = server
        self.fake = fake
        self.fleet = fleet
        self.cookies = cookies
        self.state_dir = server.state_dir

    def request(self, method, path, cookie=None):
        if method == "GET":
            return http_request(self.server.url(path), cookie=cookie)
        body = b""
        if cookie:
            token = cookie.split("=", 1)[1]
            body = ("%s=%s" % (routes.CSRF_FIELD, auth.csrf_token(token))).encode("ascii")
        return http_request(
            self.server.url(path), method="POST", data=body, cookie=cookie,
            extra_headers={"Origin": self.server.base_url()})

    def conn(self):
        return fleet_db.connect(self.state_dir)

    def add_user(self, email, role="user"):
        conn = self.conn()
        try:
            return fleet_db.add_user(conn, email, role)
        finally:
            conn.close()


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    state_dir = str(tmp_path_factory.mktemp("matrix") / "state")
    server = InProcessAppServer(state_dir)
    fake = FakeAuth0(
        "test-client-id", "test-client-secret-placeholder",
        server.base_url() + "/callback",
        allowed_logout_urls=[server.base_url() + "/login"]).start()
    server.apply_env(auth0_env(fake, server.base_url()))
    fleet = seed_matrix_fleet(state_dir)
    cookies = {"anonymous": None}
    for name, email in (
            ("owner", OWNER_EMAIL), ("other", OTHER_EMAIL), ("admin", ADMIN_EMAIL)):
        result = login_via_auth0(
            server, fake, sub="auth0|" + name, email=email)
        assert result.status == 200
        cookies[name] = result.session_cookie
    yield MatrixRig(server, fake, fleet, cookies)
    server.stop()
    fake.stop()


@pytest.fixture
def stubbed(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(
        routes, "ROUTES",
        stub_routes(_REAL_ROUTES, recorder) + probe_routes(recorder))
    return recorder


def _unknown_path_404(rig, cookie):
    status, _headers, body = rig.request("GET", "/no-such-page-anywhere", cookie)
    assert status == 404
    return body


@pytest.mark.parametrize("key,name", _CELLS, ids=_CELL_IDS)
def test_http_outcome_matches_the_policy_table(rig, stubbed, key, name):
    method = key[0]
    path = _sample_path(key)
    cookie = rig.cookies[name]
    expected = (
        UNPREFIXED_OUTCOMES[name] if key in DEVICE_SCOPED
        else OUTCOMES[ROUTE_POLICY[key]][name])

    status, headers, body = rig.request(method, path, cookie)

    if expected == "allow":
        assert status == 200 and body == REACHED_BODY
        assert stubbed.calls == [(method, path)]
    elif expected == "login":
        assert status == 303
        location = headers.get("Location")
        assert location == "/login" or location.startswith("/login?next=")
        assert stubbed.calls == []
    else:
        assert status == 404
        assert body == _unknown_path_404(rig, cookie)
        assert stubbed.calls == []


@pytest.mark.parametrize("name", ("owner", "other", "admin"))
def test_posting_to_poll_now_is_a_404_and_runs_no_cycle(rig, monkeypatch, name):
    import server.poll_cycle as poll_cycle
    calls = []
    monkeypatch.setattr(poll_cycle, "run_once", lambda **kw: calls.append(kw))
    cookie = rig.cookies[name]
    unknown = _unknown_path_404(rig, cookie)

    for path in (
            "/poll-now",
            "/devices/%s/poll-now" % rig.fleet.owner_device,
            "/devices/d_00000000/poll-now"):
        status, _headers, body = rig.request("POST", path, cookie)
        assert status == 404, path
        assert body == unknown, path
    assert calls == []


def _scoped_path(device_id, key):
    return "/devices/" + device_id + _sample_path(key)


@pytest.mark.parametrize("key,name", _SCOPED_CELLS, ids=_SCOPED_CELL_IDS)
def test_http_outcome_under_a_device_prefix_matches_the_base_route(
        rig, stubbed, key, name):
    method = key[0]
    cookie = rig.cookies[name]
    expected = OUTCOMES[ROUTE_POLICY[key]][name]

    status, headers, body = rig.request(
        method, _scoped_path(rig.fleet.owner_device, key), cookie)

    if expected == "allow":
        assert status == 200 and body == REACHED_BODY
        assert stubbed.calls == [(method, _sample_path(key))]
    elif expected == "login":
        assert status == 303
        location = headers.get("Location")
        assert location == "/login" or location.startswith("/login?next=")
        assert stubbed.calls == []
    else:
        assert status == 404
        assert body == _unknown_path_404(rig, cookie)
        assert stubbed.calls == []


@pytest.mark.parametrize("key", _SCOPED_KEYS, ids=[
    "%s_%s" % (k[0], k[1].strip("/").replace("/", "_") or "root")
    for k in _SCOPED_KEYS])
def test_an_unknown_device_id_is_404_for_a_permitted_caller_and_login_for_anonymous(
        rig, stubbed, key):
    method = key[0]
    path = _scoped_path(UNKNOWN_ID, key)
    for who in ("owner", "other", "admin"):
        status, _h, body = rig.request(method, path, rig.cookies[who])
        assert status == 404
        assert body == _unknown_path_404(rig, rig.cookies[who])
    status, headers, _b = rig.request(method, path, None)
    # Sign-in first: an anonymous caller never learns whether the id exists.
    assert status == 303 and headers["Location"].startswith("/login")
    known_status, known_headers, _b = rig.request(
        method, _scoped_path(rig.fleet.owner_device, key), None)
    assert known_status == 303
    assert known_headers["Location"].startswith("/login")
    assert stubbed.calls == []


@pytest.mark.parametrize("raw", MALFORMED_IDS)
@pytest.mark.parametrize("who", ["owner", "other", "admin"])
def test_a_malformed_device_id_under_a_prefix_is_an_identical_404(
        rig, stubbed, who, raw):
    cookie = rig.cookies[who]
    unknown = _unknown_path_404(rig, cookie)
    for method, page in (("GET", "/display"), ("POST", "/settings")):
        status, _h, body = rig.request(method, "/devices/" + raw + page, cookie)
        assert status == 404 and body == unknown
    assert stubbed.calls == []


_ADMIN_ONLY_DEVICE_KEYS = [
    key for key in _SCOPED_KEYS if ROUTE_POLICY[key] == ADMIN_ONLY]


def test_the_device_update_and_led_routes_stay_admin_only_in_both_forms():
    assert {key[1] for key in _ADMIN_ONLY_DEVICE_KEYS} == {
        "/device", "/quick/led"}
    for path in ("/update", "/update/install", "/update/cancel",
                 "/runway-image/{}.png"):
        assert any(key[1] == path and ROUTE_POLICY[key] == ADMIN_ONLY
                   for key in _REAL_KEYS)


@pytest.mark.parametrize("key", _ADMIN_ONLY_DEVICE_KEYS, ids=[
    "%s_%s" % (k[0], k[1].strip("/").replace("/", "_") or "root")
    for k in _ADMIN_ONLY_DEVICE_KEYS])
def test_an_admin_only_device_route_refuses_its_owner_in_both_forms(
        rig, stubbed, key):
    cookie = rig.cookies["owner"]
    unknown = _unknown_path_404(rig, cookie)
    for path in (_sample_path(key), _scoped_path(rig.fleet.owner_device, key)):
        status, _h, body = rig.request(key[0], path, cookie)
        assert status == 404 and body == unknown
    assert stubbed.calls == []


@pytest.mark.parametrize("key", _UNSCOPED_KEYS, ids=[
    "%s_%s" % (k[0], k[1].strip("/").replace("/", "_") or "root")
    for k in _UNSCOPED_KEYS])
def test_a_global_route_is_not_reachable_under_a_device_prefix(rig, stubbed, key):
    method = key[0]
    path = _scoped_path(rig.fleet.owner_device, key)
    for who in ("anonymous", "admin"):
        cookie = rig.cookies[who]
        status, headers, body = rig.request(method, path, cookie)
        if who == "anonymous":
            assert status == 404 and body == _unknown_path_404(rig, None)
        else:
            assert status == 404 and body == _unknown_path_404(rig, cookie)
    assert stubbed.calls == []


def test_a_user_404_shows_no_health_dot_and_no_admin_navigation(rig, stubbed):
    user_body = _unknown_path_404(rig, rig.cookies["owner"]).decode("utf-8")
    admin_body = _unknown_path_404(rig, rig.cookies["admin"]).decode("utf-8")
    assert 'href="/health"' in admin_body
    for marker in ('href="/health"', 'href="/display"', 'href="/airlines"'):
        assert marker not in user_body


# --- device-scoped probe family ---------------------------------------------


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_probe_owner_reaches_own_device_only(rig, stubbed, method):
    own = probe_path(rig.fleet.owner_device)
    status, _h, body = rig.request(method, own, rig.cookies["owner"])
    assert (status, body) == (200, REACHED_BODY)
    assert stubbed.calls == [(method, own)]

    stubbed.clear()
    foreign = probe_path(rig.fleet.other_device)
    status, _h, foreign_body = rig.request(method, foreign, rig.cookies["owner"])
    assert status == 404
    status, _h, unknown_body = rig.request(
        method, probe_path(UNKNOWN_ID), rig.cookies["owner"])
    assert status == 404
    assert foreign_body == unknown_body == _unknown_path_404(rig, rig.cookies["owner"])
    assert stubbed.calls == []


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_probe_other_user_cannot_reach_a_foreign_device(rig, stubbed, method):
    status, _h, body = rig.request(
        method, probe_path(rig.fleet.owner_device), rig.cookies["other"])
    assert status == 404
    assert body == _unknown_path_404(rig, rig.cookies["other"])
    assert stubbed.calls == []
    status, _h, _b = rig.request(
        method, probe_path(rig.fleet.other_device), rig.cookies["other"])
    assert status == 200


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("who", ["admin"])
def test_probe_admin_reaches_existing_devices_but_not_unknown_ones(
        rig, stubbed, method, who):
    for device_id in (rig.fleet.owner_device, rig.fleet.other_device):
        status, _h, body = rig.request(method, probe_path(device_id), rig.cookies[who])
        assert (status, body) == (200, REACHED_BODY)
    stubbed.clear()
    status, _h, body = rig.request(method, probe_path(UNKNOWN_ID), rig.cookies[who])
    assert status == 404
    assert body == _unknown_path_404(rig, rig.cookies[who])
    assert stubbed.calls == []


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("who", ["owner", "admin"])
@pytest.mark.parametrize("raw", MALFORMED_IDS)
def test_probe_malformed_ids_are_an_identical_404(rig, stubbed, method, who, raw):
    path = "/d/" + raw + "/_probe"
    status, _h, body = rig.request(method, path, rig.cookies[who])
    assert status == 404
    assert body == _unknown_path_404(rig, rig.cookies[who])
    assert stubbed.calls == []
    # the server keeps answering after a hostile id
    assert rig.request("GET", "/account", rig.cookies[who])[0] == 200


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_probe_anonymous_is_sent_to_login(rig, stubbed, method):
    status, headers, _b = rig.request(
        method, probe_path(rig.fleet.owner_device), None)
    assert status == 303
    assert headers["Location"].startswith("/login")
    assert stubbed.calls == []


# --- session state is re-read on every request -------------------------------

_SESSION_PATH = "/account"


def _expect_signed_in(rig, cookie):
    assert rig.request("GET", _SESSION_PATH, cookie)[0] == 200


def _expect_signed_out(rig, cookie):
    status, headers, _b = rig.request("GET", _SESSION_PATH, cookie)
    assert status == 303 and headers["Location"].startswith("/login")


def _user_with_session(rig, email, role="user"):
    user_id = rig.add_user(email, role)
    cookie = session_cookie_for(
        rig.state_dir, fleet_sessions.PRINCIPAL_USER, user_id, int(time.time()))
    return user_id, cookie


def test_a_disabled_user_is_refused_on_the_next_request(rig, stubbed):
    _uid, cookie = _user_with_session(rig, "disabled@example.test")
    _expect_signed_in(rig, cookie)
    conn = rig.conn()
    try:
        assert fleet_db.set_user_disabled(conn, "disabled@example.test", True)
    finally:
        conn.close()
    _expect_signed_out(rig, cookie)


def test_a_session_of_a_deleted_user_is_refused(rig, stubbed):
    uid, cookie = _user_with_session(rig, "deleted@example.test")
    _expect_signed_in(rig, cookie)
    conn = rig.conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    finally:
        conn.close()
    _expect_signed_out(rig, cookie)


def test_an_expired_session_is_refused(rig, stubbed):
    uid = rig.add_user("expired@example.test")
    long_ago = int(time.time()) - 31 * 86400
    cookie = session_cookie_for(
        rig.state_dir, fleet_sessions.PRINCIPAL_USER, uid, long_ago)
    _expect_signed_out(rig, cookie)


@pytest.mark.parametrize("retired_flag", [None, "0", "1"])
def test_a_legacy_session_is_refused_whatever_the_retired_flag_says(
        rig, stubbed, retired_flag):
    cookie = session_cookie_for(
        rig.state_dir, fleet_sessions.PRINCIPAL_LEGACY_ADMIN, None, int(time.time()))
    rig.server.apply_env({"SKYPANE_LEGACY_PASSWORD_LOGIN": retired_flag})
    try:
        status, headers, _b = rig.request("GET", "/", cookie)
        assert status == 303 and headers["Location"].startswith("/login")
    finally:
        rig.server.apply_env({"SKYPANE_LEGACY_PASSWORD_LOGIN": None})
    # The refused row was deleted, so it cannot be revived either.
    assert rig.request("GET", "/", cookie)[0] == 303


def test_a_demoted_admin_loses_admin_pages_without_signing_in_again(rig, stubbed):
    uid, cookie = _user_with_session(rig, "demoted@example.test", role="admin")
    assert rig.request("GET", "/", cookie)[0] == 200
    conn = rig.conn()
    try:
        conn.execute("UPDATE users SET role = 'user' WHERE id = ?", (uid,))
    finally:
        conn.close()
    assert rig.request("GET", "/", cookie)[0] == 404
    assert rig.request("GET", "/account", cookie)[0] == 200
