"""companion/test_post_origin.py — SEC-03 (audit ledger 2026-09-23, D-16):
`auth.post_origin_ok()` and the `do_POST()` Origin/Sec-Fetch-Site gate that
rejects any cross-site POST (login included) with a localized 403, before
any routing or form read.

Native pytest (Phase 32's conftest.py fixtures and no-network socket guard
apply automatically to this module) — deliberately not a stdlib
check()/EXPECTED_CHECK_COUNT harness, `companion/test_login_throttle.py`'s
own precedent.

Section 1 is pure in-process unit coverage of `auth.post_origin_ok()`.
Section 2 is HTTP integration coverage against a real companion/app.py
subprocess, over every POST route `do_POST()` itself dispatches — the
route list is discovered from `do_POST()`'s own source (never hardcoded
here), so a route added later is covered automatically.
"""
import collections
import http.client
import inspect
import os
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlencode, urlsplit

import pytest

from companion import app, auth
from server import device_config

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from skypane_test_support import FakeProviders, child_env  # noqa: E402

APP_PATH = os.path.join(HERE, "app.py")
TEST_PASSWORD = "companion-origin-test-password-please-ignore"
STARTUP_DEADLINE_S = 10.0

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

def _pick_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


class _CompanionServer:
    """Owns a companion/app.py subprocess: a free port, an isolated temp
    state directory, startup readiness polling, and clean teardown —
    mirrors companion/test_login_throttle.py's own _CompanionServer,
    deliberately re-implemented rather than imported (that class is
    file-local, the same "own subprocess, own Harness" precedent
    companion/test_login_throttle.py itself records against
    test_companion_app.py's Harness).
    """

    def __init__(self, state_dir):
        self.state_dir = str(state_dir)
        self.port = _pick_free_port()
        self.stdout_path = os.path.join(self.state_dir, "app.stdout.log")
        self.proc = None

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def start(self):
        env = child_env(
            dict(os.environ), fake_providers=FakeProviders(), state_dir=self.state_dir)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.state_dir,
        ]
        with open(self.stdout_path, "w") as stdout_fh:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "companion/app.py exited early (code %s) before accepting "
                    "connections" % self.proc.returncode)
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(
            "companion/app.py did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None


_Response = collections.namedtuple("_Response", "status headers body")


def _post(base_url, path, headers=None, body=b"", cookie=None, timeout=10):
    parts = urlsplit(base_url)
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=timeout)
    try:
        req_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            req_headers.update(headers)
        if cookie:
            req_headers["Cookie"] = cookie
        conn.request("POST", path, body=body, headers=req_headers)
        resp = conn.getresponse()
        data = resp.read()
        return _Response(resp.status, resp.getheaders(), data)
    finally:
        conn.close()


def _header(resp, name):
    name = name.lower()
    for key, value in resp.headers:
        if key.lower() == name:
            return value
    return None


def _extract_session_cookie(resp):
    value = _header(resp, "Set-Cookie")
    assert value, "expected a Set-Cookie header on a successful login response"
    return value.split(";", 1)[0]


# --- Route discovery: read do_POST()'s own source, never hardcode here --

_ROUTE_EQ_RE = re.compile(r"\bpath == ([A-Za-z_][A-Za-z0-9_.]*)")


def _resolve_dotted(name):
    obj = app
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj


def _exact_post_routes():
    """Every `path == CONST` branch do_POST() checks, discovered from its
    own source — a route constant added to do_POST() later is covered
    here automatically, with no edit to this test file.
    """
    src = inspect.getsource(app.Handler.do_POST)
    seen = []
    for name in _ROUTE_EQ_RE.findall(src):
        route = _resolve_dotted(name)
        if route not in seen:
            seen.append(route)
    return seen


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

ALL_POST_ROUTE_PATHS = tuple(_exact_post_routes()) + _PREFIX_ROUTE_EXAMPLES


@pytest.fixture(scope="module")
def origin_server(tmp_path_factory):
    state_dir = tmp_path_factory.mktemp("post-origin")
    server = _CompanionServer(state_dir)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.mark.parametrize(
    "path", ALL_POST_ROUTE_PATHS,
    ids=[p.replace("/", "_") for p in ALL_POST_ROUTE_PATHS])
def test_cross_site_origin_rejected_on_every_post_route(origin_server, path):
    resp = _post(origin_server.base_url(), path, headers={"Origin": EVIL_ORIGIN})
    assert resp.status == 403


@pytest.mark.parametrize(
    "path", ALL_POST_ROUTE_PATHS,
    ids=[p.replace("/", "_") for p in ALL_POST_ROUTE_PATHS])
def test_cross_site_fetch_metadata_rejected_on_every_post_route(origin_server, path):
    resp = _post(origin_server.base_url(), path, headers={"Sec-Fetch-Site": "cross-site"})
    assert resp.status == 403


def test_login_with_correct_password_and_cross_site_origin_is_rejected(origin_server):
    body = urlencode({"password": TEST_PASSWORD}).encode()
    resp = _post(
        origin_server.base_url(), app.LOGIN_ROUTE, headers={"Origin": EVIL_ORIGIN}, body=body)
    assert resp.status == 403
    assert _header(resp, "Set-Cookie") is None


def test_login_with_no_origin_or_fetch_metadata_behaves_as_before(origin_server):
    body = urlencode({"password": TEST_PASSWORD}).encode()
    resp = _post(origin_server.base_url(), app.LOGIN_ROUTE, body=body)
    assert resp.status == 303
    assert _header(resp, "Set-Cookie") is not None


def test_403_body_is_an_html_page_with_no_store(origin_server):
    resp = _post(origin_server.base_url(), app.LOGIN_ROUTE, headers={"Origin": EVIL_ORIGIN})
    assert resp.status == 403
    content_type = _header(resp, "Content-Type") or ""
    assert content_type.startswith("text/html")
    assert _header(resp, "Cache-Control") == "no-store"
    assert b"<html" in resp.body.lower()


def _read_bytes_or_none(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def test_quick_switch_cross_site_rejected_then_same_origin_applied(tmp_path):
    server = _CompanionServer(tmp_path)
    server.start()
    try:
        login_resp = _post(
            server.base_url(), app.LOGIN_ROUTE,
            body=urlencode({"password": TEST_PASSWORD}).encode())
        assert login_resp.status == 303
        cookie = _extract_session_cookie(login_resp)

        config_path = device_config.device_config_path(str(tmp_path))
        before = _read_bytes_or_none(config_path)

        form = urlencode({
            app.layout.QUICK_STATE_FIELD: app.layout.QUICK_STATE_OFF,
            "return_to": app.layout.HOME_ROUTE,
        }).encode()

        cross_site_resp = _post(
            server.base_url(), app.QUICK_DISPLAY_ROUTE,
            headers={"Origin": EVIL_ORIGIN}, body=form, cookie=cookie)
        assert cross_site_resp.status == 403
        assert _read_bytes_or_none(config_path) == before

        same_origin_resp = _post(
            server.base_url(), app.QUICK_DISPLAY_ROUTE,
            headers={"Origin": server.base_url(), "Sec-Fetch-Site": "same-origin"},
            body=form, cookie=cookie)
        assert same_origin_resp.status == 303
        after = _read_bytes_or_none(config_path)
        assert after is not None
        assert after != before
        assert device_config.load_device_config(str(tmp_path))["display_enabled"] is False
    finally:
        server.stop()
