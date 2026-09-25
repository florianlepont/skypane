"""The ONE shared companion/app.py test-server implementation (33-02-PLAN.md,
TST-10). Every companion test that used to build its own copy of
`Harness`, `_InProcessHarness`, `http_request` or `_NoRedirectHandler`
(companion/test_companion_app.py, test_config_page.py, test_status_pages.py,
test_view_pages.py) now gets the same behaviour from `companion/conftest.py`'s
fixtures, which are all built on this module.

Stdlib-only, plus `skypane_test_support` (`child_env`, `FakeProviders`) and
`companion.auth` / `companion.app` (imported lazily where that keeps a
cheap import path cheap). No pytest import here: a subprocess or a plain
script can use `AppServer` directly, the same way `skypane_test_support`
itself stays pytest-light.
"""
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from skypane_test_support import REPO_ROOT, FakeProviders, child_env

TEST_PASSWORD = "companion-test-password-please-ignore"
APP_PATH = os.path.join(REPO_ROOT, "companion", "app.py")
STARTUP_DEADLINE_S = 10.0

# Duplicated from companion/app.py's STYLE_ROUTE rather than imported at
# module scope, so importing this module never pays for companion/app.py's
# own (heavier) import graph (Pillow, argparse, the full route table) just
# to resolve one constant string.
_STYLE_ROUTE = "/static/style.css"


def pick_free_port():
    """Bind a loopback TCP socket to port 0, read back the OS-assigned
    free port, then release it — the same technique every prior Harness
    class used under its own name.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


# --- HTTP client: never follows redirects --------------------------------

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return None from redirect_request() so a 303 (or any other
    redirect) is surfaced to the caller as an HTTPError instead of being
    silently followed — callers need to see the raw status code and
    Location/Set-Cookie headers, not the page the redirect points at.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# A single shared opener with redirects disabled. Deliberately NOT built
# with urllib.request.HTTPCookieProcessor: companion/app.py's session
# cookie always carries the Secure flag, and http.cookiejar silently
# refuses to store/resend a Secure cookie over a plain-HTTP test
# connection. Cookies are instead captured from Set-Cookie response
# headers and threaded through explicitly as Cookie request headers.
_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(
        url, method="GET", data=None, cookie=None, timeout=10,
        content_type=None, extra_headers=None):
    """Minimal stdlib HTTP client: returns (status, headers_dict,
    raw_bytes) for both success and HTTP-error responses;
    connection-level failures propagate.
    """
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if content_type is not None:
        headers["Content-Type"] = content_type
    elif data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def cookie_value(headers):
    """Extract just the "name=value" portion of a Set-Cookie response
    header (dropping the trailing attribute flags), or None.
    """
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


def login(server, password=TEST_PASSWORD):
    """POST /login with `password` against `server` and return the
    session cookie's "name=value" pair. Raises AssertionError if login
    did not succeed — callers that expect failure should call
    http_request() directly.
    """
    status, headers, _ = http_request(
        server.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError(
            "expected a 303 redirect on successful login, got %d" % status)
    cookie = cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def get(server, path, cookie=None):
    """GET `path` from `server` through http_request(), never following
    redirects.
    """
    return http_request(server.base_url() + path, cookie=cookie)


def served_stylesheet(server):
    """GET the app's style route and assert a 200 with a text/css
    Content-Type; return the decoded stylesheet text.
    """
    status, headers, body = get(server, _STYLE_ROUTE)
    assert status == 200, (
        "expected 200 from %s, got %d" % (_STYLE_ROUTE, status))
    content_type = headers.get("Content-Type", "")
    assert content_type.startswith("text/css"), (
        "expected a text/css Content-Type from %s, got %r"
        % (_STYLE_ROUTE, content_type))
    return body.decode("utf-8")


def served_asset(server, path):
    """GET a served static asset (e.g. a /static/*.js route) and assert a
    200; return the decoded text.
    """
    status, headers, body = get(server, path)
    assert status == 200, "expected 200 from %s, got %d" % (path, status)
    return body.decode("utf-8")


# --- Real subprocess server -----------------------------------------------

class AppServer:
    """Owns a real `companion/app.py` subprocess: a free loopback port, an
    isolated state directory the caller provides, startup readiness
    polling, and process-GROUP teardown (start_new_session=True + killpg
    SIGTERM->SIGKILL), so an orphaned grandchild the app process itself
    spawned never survives stop().
    """

    def __init__(
            self, state_dir, *, extra_args=(), fake_providers=False,
            password=TEST_PASSWORD, env_overrides=None):
        self.state_dir = state_dir
        self.tmpdir = state_dir  # alias: some callers migrate from Harness.tmpdir
        self.extra_args = list(extra_args)
        self.fake_providers = fake_providers
        self.password = password
        self.env_overrides = env_overrides
        self.port = pick_free_port()
        self.stdout_path = os.path.join(state_dir, "app.stdout.log")
        self.proc = None

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def url(self, path):
        return self.base_url() + path

    @property
    def pid(self):
        return self.proc.pid if self.proc is not None else None

    def start(self):
        from companion import auth

        os.makedirs(self.state_dir, exist_ok=True)
        fake_providers = (
            FakeProviders() if self.fake_providers is True
            else (self.fake_providers or None)
        )
        env = child_env(
            dict(os.environ), fake_providers=fake_providers, state_dir=self.state_dir)
        env[auth.PASSWORD_ENV_VAR] = self.password
        if self.env_overrides:
            env.update(self.env_overrides)

        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.state_dir,
        ] + self.extra_args
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env,
                start_new_session=True)
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "companion/app.py exited early (code %s) before "
                    "accepting connections:\n%s"
                    % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(
            "companion/app.py did not start listening within %.0fs:\n%s"
            % (STARTUP_DEADLINE_S, self.read_stdout()))

    def stop(self):
        """Idempotent: SIGTERM the whole process group first (SIGTERM
        lets coverage's sigterm=true save data), wait, then SIGKILL the
        group if it is still alive. start_new_session=True made the
        child its own session/process-group leader, so its pid IS the
        pgid — any grandchild it spawned without its own setsid() shares
        that group and is killed the same way.
        """
        if self.proc is None:
            return
        pid = self.proc.pid
        if self.proc.poll() is None:
            self._killpg(pid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._killpg(pid, signal.SIGKILL)
                self.proc.wait(timeout=5)
        self.proc = None

    @staticmethod
    def _killpg(pid, sig):
        try:
            os.killpg(os.getpgid(pid), sig)
        except ProcessLookupError:
            pass  # already gone

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def fake_provider_calls(self):
        """The fake ADS-B/adsbdb providers' call log for THIS server's
        child — what companion/app.py's run_once() actually queried.
        """
        return FakeProviders.read_calls_log(
            os.path.join(self.state_dir, "fake-providers.json"))


# --- In-process server (for tests that need to monkeypatch a module the
# real subprocess would import into a separate interpreter) -------------

class InProcessAppServer:
    """A real `companion/app.py` `ThreadingHTTPServer`, running in a
    background thread of the CALLING process rather than a subprocess —
    for tests that need to monkeypatch a companion/server module in the
    same interpreter the running server uses (a `Harness` subprocess is a
    separate interpreter with its own separate copy of every module, so a
    monkeypatch there has no effect). Mirrors companion/app.py's own
    main() construction exactly: `Handler.args` set at class level, then
    a ThreadingHTTPServer built the identical way.
    """

    def __init__(self, state_dir):
        import argparse
        import threading
        from http.server import ThreadingHTTPServer

        import companion.app as app_module
        from companion import auth

        os.makedirs(state_dir, exist_ok=True)
        self.state_dir = state_dir
        self._app_module = app_module
        self._previous_password = os.environ.get(auth.PASSWORD_ENV_VAR)
        os.environ[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        self.port = pick_free_port()
        app_module.Handler.args = argparse.Namespace(
            state_dir=state_dir, geofence=None)
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), app_module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def url(self, path):
        return self.base_url() + path

    def stop(self):
        from companion import auth

        self.server.shutdown()
        self.server.server_close()
        if self._previous_password is None:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)
        else:
            os.environ[auth.PASSWORD_ENV_VAR] = self._previous_password
