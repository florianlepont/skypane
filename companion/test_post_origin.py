"""companion/test_post_origin.py — SEC-03 (audit ledger 2026-09-23, D-16):
`auth.post_origin_ok()` and the `do_POST()` Origin/Sec-Fetch-Site gate that
rejects any cross-site POST (login included) with a localized 403, before
any routing or form read.

Native pytest (Phase 32's conftest.py fixtures and no-network socket guard
apply automatically to this module).

Section 1 is pure in-process unit coverage of `auth.post_origin_ok()`.
Section 2 is HTTP integration coverage against a real companion/app.py
subprocess (companion/conftest.py's app_server/module_app_server_factory
fixtures, test-support/companion_app_server.py's HTTP client — Phase 33,
TST-10), over every POST route do_POST() dispatches. The route list below
is named explicitly from companion/app.py's own route constants — the
same names do_POST() itself branches on — never discovered by reading
do_POST()'s source text; a route added there later needs a line added
here too, but test_cross_site_origin_rejected_before_routing_on_unknown_path
below proves the gate does not actually depend on this list being
exhaustive, since it runs before any routing decision.
"""
import urllib.parse

import pytest

import companion_app_server
from companion import app, auth
from server import device_config

EVIL_ORIGIN = "https://evil.example"


# --- Section 1: auth.post_origin_ok() (unit) -----------------------------

def test_post_origin_ok_allows_neither_header():
    assert auth.post_origin_ok({}) is True


def test_post_origin_ok_allows_matching_origin_and_host():
    assert auth.post_origin_ok(
        {"Origin": "https://skypane.algernon.ovh", "Host": "skypane.algernon.ovh"}
    ) is True


def test_post_origin_ok_allows_matching_origin_default_https_port():
    assert auth.post_origin_ok(
        {"Origin": "https://skypane.algernon.ovh:443", "Host": "skypane.algernon.ovh"}
    ) is True


def test_post_origin_ok_allows_matching_loopback_origin_with_port():
    assert auth.post_origin_ok(
        {"Origin": "http://127.0.0.1:8650", "Host": "127.0.0.1:8650"}
    ) is True


def test_post_origin_ok_rejects_mismatched_origin():
    assert auth.post_origin_ok(
        {"Origin": EVIL_ORIGIN, "Host": "skypane.algernon.ovh"}
    ) is False


def test_post_origin_ok_rejects_null_origin():
    assert auth.post_origin_ok(
        {"Origin": "null", "Host": "skypane.algernon.ovh"}
    ) is False


def test_post_origin_ok_rejects_cross_site_fetch_metadata():
    assert auth.post_origin_ok({"Sec-Fetch-Site": "cross-site"}) is False


def test_post_origin_ok_rejects_same_site_fetch_metadata():
    assert auth.post_origin_ok({"Sec-Fetch-Site": "same-site"}) is False


def test_post_origin_ok_allows_same_origin_fetch_metadata_with_matching_origin():
    assert auth.post_origin_ok({
        "Sec-Fetch-Site": "same-origin",
        "Origin": "https://skypane.algernon.ovh",
        "Host": "skypane.algernon.ovh",
    }) is True


def test_post_origin_ok_allows_none_fetch_metadata():
    assert auth.post_origin_ok({"Sec-Fetch-Site": "none"}) is True


def test_post_origin_ok_rejects_origin_with_missing_host():
    assert auth.post_origin_ok({"Origin": "https://skypane.algernon.ovh"}) is False


# --- Section 2: HTTP integration, real companion/app.py subprocess ------

# Every `path == CONST` branch do_POST() dispatches on, named explicitly
# from app.py's own route constants (the same names do_POST() itself
# compares against) rather than discovered from its source text.
_EXACT_POST_ROUTES = (
    app.LOGIN_ROUTE,
    app.SETTINGS_ROUTE,
    app.POLL_ROUTE,
    app.QUICK_DISPLAY_ROUTE,
    app.QUICK_QUIET_HOURS_ROUTE,
    app.QUICK_LED_ROUTE,
    app.THEME_ROUTE,
    app.LANG_ROUTE,
    app.LOGOUT_ROUTE,
    app.airlines_page.RESOLVE_ROUTE,
    app.RULES_ADD_ROUTE,
    app.CALENDAR_DISCONNECT_ROUTE,
    app.CALENDAR_CONNECT_ROUTE,
    app.NOTIFICATIONS_TEST_ROUTE,
)

# Prefix routes do_POST() matches with startswith()/endswith() rather than
# `path ==` need one concrete example path each, built from the SAME
# prefix/suffix constants do_POST() itself compares against — never a
# hardcoded literal path.
_PREFIX_ROUTE_EXAMPLES = (
    app.airlines_page.MANUAL_DELETE_ROUTE_PREFIX + "AFR"
    + app.airlines_page.MANUAL_DELETE_ROUTE_SUFFIX,
    app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + "AFR" + ".png",
    app.RULES_DELETE_ROUTE_PREFIX + "airline/AFR" + app.RULES_DELETE_ROUTE_SUFFIX,
)

ALL_POST_ROUTE_PATHS = _EXACT_POST_ROUTES + _PREFIX_ROUTE_EXAMPLES


def _post(url, headers=None, data=b"", cookie=None):
    return companion_app_server.http_request(
        url, method="POST", data=data, cookie=cookie, extra_headers=headers)


@pytest.fixture(scope="module")
def origin_server(module_app_server_factory):
    """A read-only-shared server: every parametrized POST below is
    rejected by the Origin/Sec-Fetch-Site gate before it can mutate any
    state, so sharing one server across them is safe (33-MIGRATION-RULES.md
    section 2).
    """
    return module_app_server_factory()


@pytest.mark.parametrize(
    "path", ALL_POST_ROUTE_PATHS,
    ids=[p.replace("/", "_") for p in ALL_POST_ROUTE_PATHS])
def test_cross_site_origin_rejected_on_every_post_route(origin_server, path):
    status, _, _ = _post(origin_server.url(path), headers={"Origin": EVIL_ORIGIN})
    assert status == 403


@pytest.mark.parametrize(
    "path", ALL_POST_ROUTE_PATHS,
    ids=[p.replace("/", "_") for p in ALL_POST_ROUTE_PATHS])
def test_cross_site_fetch_metadata_rejected_on_every_post_route(origin_server, path):
    status, _, _ = _post(origin_server.url(path), headers={"Sec-Fetch-Site": "cross-site"})
    assert status == 403


def test_cross_site_origin_rejected_before_routing_on_unknown_path(origin_server):
    """The gate is the FIRST statement of do_POST(), before urlsplit() and
    any `path ==`/startswith() comparison — so a path do_POST() does not
    even recognise still gets the same 403, proving the gate's coverage
    does not actually depend on ALL_POST_ROUTE_PATHS being exhaustive.
    """
    status, _, _ = _post(origin_server.url("/no-such-route"), headers={"Origin": EVIL_ORIGIN})
    assert status == 403


def test_login_with_correct_password_and_cross_site_origin_is_rejected(origin_server):
    body = urllib.parse.urlencode({"password": companion_app_server.TEST_PASSWORD}).encode()
    status, headers, _ = _post(
        origin_server.url(app.LOGIN_ROUTE), headers={"Origin": EVIL_ORIGIN}, data=body)
    assert status == 403
    assert companion_app_server.cookie_value(headers) is None


def test_login_with_no_origin_or_fetch_metadata_behaves_as_before(origin_server):
    body = urllib.parse.urlencode({"password": companion_app_server.TEST_PASSWORD}).encode()
    status, headers, _ = _post(origin_server.url(app.LOGIN_ROUTE), data=body)
    assert status == 303
    assert companion_app_server.cookie_value(headers) is not None


def test_403_body_is_an_html_page_with_no_store(origin_server):
    status, headers, body = _post(origin_server.url(app.LOGIN_ROUTE), headers={"Origin": EVIL_ORIGIN})
    assert status == 403
    content_type = headers.get("Content-Type", "")
    assert content_type.startswith("text/html")
    assert headers.get("Cache-Control") == "no-store"
    assert b"<html" in body.lower()


def _read_bytes_or_none(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def test_quick_switch_cross_site_rejected_then_same_origin_applied(app_server):
    login_status, login_headers, _ = _post(
        app_server.url(app.LOGIN_ROUTE),
        data=urllib.parse.urlencode(
            {"password": companion_app_server.TEST_PASSWORD}).encode())
    assert login_status == 303
    cookie = companion_app_server.cookie_value(login_headers)
    assert cookie

    config_path = device_config.device_config_path(app_server.state_dir)
    before = _read_bytes_or_none(config_path)

    form = urllib.parse.urlencode({
        app.layout.QUICK_STATE_FIELD: app.layout.QUICK_STATE_OFF,
        "return_to": app.layout.HOME_ROUTE,
    }).encode()

    cross_site_status, _, _ = _post(
        app_server.url(app.QUICK_DISPLAY_ROUTE),
        headers={"Origin": EVIL_ORIGIN}, data=form, cookie=cookie)
    assert cross_site_status == 403
    assert _read_bytes_or_none(config_path) == before

    same_origin_status, _, _ = _post(
        app_server.url(app.QUICK_DISPLAY_ROUTE),
        headers={"Origin": app_server.base_url(), "Sec-Fetch-Site": "same-origin"},
        data=form, cookie=cookie)
    assert same_origin_status == 303
    after = _read_bytes_or_none(config_path)
    assert after is not None
    assert after != before
    assert device_config.load_device_config(app_server.state_dir)["display_enabled"] is False
