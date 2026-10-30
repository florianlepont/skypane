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
"""
import time

import pytest

from companion import access, routes, static_files
from companion_app_server import (
    InProcessAppServer, auth0_env, http_request,
    login_via_auth0)
from fake_auth0 import FakeAuth0
from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, REACHED_BODY, Recorder, probe_path,
    probe_routes, seed_matrix_fleet, session_cookie_for, stub_routes)
from server import fleet_db, fleet_sessions

# --- the hand-written policy -------------------------------------------------

PUBLIC = "public"
SIGNED_IN = "signed-in"
ADMIN_ONLY = "admin-only"

_PUBLIC_PATHS = ("/login", "/login/auth0", "/callback")
_STATIC_PATHS = tuple(static_files.STATIC_ROUTES)

ROUTE_POLICY = {
    ("GET", "/login"): PUBLIC,
    ("GET", "/login/auth0"): PUBLIC,
    ("GET", "/callback"): PUBLIC,
    ("GET", "/account"): SIGNED_IN,
    ("POST", "/ui-theme"): SIGNED_IN,
    ("POST", "/ui-lang"): SIGNED_IN,
    ("POST", "/logout"): SIGNED_IN,
    ("GET", "/"): ADMIN_ONLY,
    ("GET", "/display"): ADMIN_ONLY,
    ("GET", "/device"): ADMIN_ONLY,
    ("GET", "/flights"): ADMIN_ONLY,
    ("GET", "/health"): ADMIN_ONLY,
    ("GET", "/airlines"): ADMIN_ONLY,
    ("GET", "/update"): ADMIN_ONLY,
    ("GET", "/settings"): ADMIN_ONLY,
    ("GET", "/history"): ADMIN_ONLY,
    ("GET", "/preview"): ADMIN_ONLY,
    ("GET", "/gallery/{}"): ADMIN_ONLY,
    ("GET", "/runway-image/{}.png"): ADMIN_ONLY,
    ("GET", "/illustration/{}.png"): ADMIN_ONLY,
    ("GET", "/theme-preview/{}.png"): ADMIN_ONLY,
    ("GET", "/frame-preview/{}.png"): ADMIN_ONLY,
    ("POST", "/settings"): ADMIN_ONLY,
    ("POST", "/poll-now"): ADMIN_ONLY,
    ("POST", "/quick/display"): ADMIN_ONLY,
    ("POST", "/quick/quiet-hours"): ADMIN_ONLY,
    ("POST", "/quick/led"): ADMIN_ONLY,
    ("POST", "/airlines/resolve"): ADMIN_ONLY,
    ("POST", "/airlines/rename"): ADMIN_ONLY,
    ("POST", "/airlines/rename/reset"): ADMIN_ONLY,
    ("POST", "/airlines/manual-resolutions/{}/delete"): ADMIN_ONLY,
    ("POST", "/illustration/{}.png"): ADMIN_ONLY,
    ("POST", "/settings/rules/add"): ADMIN_ONLY,
    ("POST", "/settings/calendar/disconnect"): ADMIN_ONLY,
    ("POST", "/settings/calendar/connect"): ADMIN_ONLY,
    ("POST", "/update/install"): ADMIN_ONLY,
    ("POST", "/update/cancel"): ADMIN_ONLY,
    ("POST", "/settings/rules/{}/delete"): ADMIN_ONLY,
}
ROUTE_POLICY.update({("GET", path): PUBLIC for path in _STATIC_PATHS})

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
}
PRINCIPAL_NAMES = ("anonymous", "owner", "other", "admin")

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


def test_no_route_is_declared_twice():
    assert len(_REAL_KEYS) == len(set(_REAL_KEYS))


def test_a_dummy_route_without_a_row_is_reported(monkeypatch):
    dummy = routes.Route(
        "GET", routes.Exact("/zz-new-page"), lambda h, m: None, routes.ADMIN_ONLY)
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (dummy,))
    keys = {_route_key(r) for r in routes.ROUTES}
    assert ("GET", "/zz-new-page") in keys - set(ROUTE_POLICY)


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


def _never_owner(_device_id):
    raise AssertionError("a global route must not look up a device owner")


@pytest.mark.parametrize("key,name", _CELLS, ids=_CELL_IDS)
def test_decide_matches_the_policy_table(key, name):
    route = next(r for r in _REAL_ROUTES if _route_key(r) == key)
    outcome = access.decide(_PRINCIPALS[name], route.access, None, _never_owner)
    assert _DECISION_WORDS[outcome] == OUTCOMES[ROUTE_POLICY[key]][name]


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
        return http_request(
            self.server.url(path), method="POST", data=b"", cookie=cookie,
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
    expected = OUTCOMES[ROUTE_POLICY[key]][name]

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


def test_a_user_404_shows_no_health_dot_and_no_admin_navigation(rig, stubbed):
    user_body = _unknown_path_404(rig, rig.cookies["owner"]).decode("utf-8")
    admin_body = _unknown_path_404(rig, rig.cookies["admin"]).decode("utf-8")
    assert 'href="/health"' in admin_body
    for marker in ('href="/health"', 'href="/display"', 'href="/airlines"'):
        assert marker not in user_body


# --- device-scoped probe family ---------------------------------------------

MALFORMED_IDS = (
    "d_ZZZZZZZZ", "..", "d_" + "0" * 40, "a/b", "d_0000000", "D_00000000", "",
    "d_00000000/..",
)
UNKNOWN_ID = "d_00000000"


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
