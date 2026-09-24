"""companion/test_browser_origin.py — SEC-03 (audit ledger 2026-09-23,
D-16): the browser-level half of the Origin/Sec-Fetch-Site proof
companion/test_post_origin.py already covers over plain HTTP — a REAL
browser proves the cross-origin rejection, and that same-origin forms and
the quick-switch fetch keep working.

Native pytest, collected directly (companion/test_login_throttle.py and
companion/test_health_offbox.py are the precedent, exempted from
companion/test_legacy_harness_shim.py's on-disk drift guard the same
way) — the first one that also needs a real browser, so it follows the
legacy harnesses' own skip-or-fail policy (_browser_required() below,
re-implemented rather than imported: companion/test_legacy_harness_shim.py
is itself a pytest test module, not a library to import from — the same
reasoning companion/test_login_throttle.py's own module docstring already
gives for not importing test_companion_app.py's Harness).
"""
import glob
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from companion import app
from companion.pages import config_page
from companion.test_browser_ux_helpers import _login, _persist_without_js
from companion.test_companion_app import TEST_PASSWORD
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
STARTUP_DEADLINE_S = 10.0


def _browser_required():
    """True in CI (GitHub sets CI=true) or with SKYPANE_REQUIRE_BROWSER=1
    — mirrors companion/test_legacy_harness_shim.py's own
    `_browser_required()` byte for byte (see this file's own module
    docstring for why it is copied rather than imported).
    """
    return (
        os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1"
        or os.environ.get("CI", "").lower() == "true"
    )


def _find_full_chromium_binary(browsers_path):
    """The full `chrome-linux/chrome` build, as opposed to the
    `chrome-headless-shell` binary Playwright's own default headless
    launch prefers since recent releases — used only as a fallback, see
    `_launch_chromium()` below, for the ONE known-benign cause of a
    launch failure: a browser cache pinned to an older revision than the
    installed `playwright` package expects, so the shell variant is
    simply absent while the full build is present and CDP-compatible.
    """
    if not browsers_path:
        return None
    candidates = sorted(
        glob.glob(os.path.join(browsers_path, "chromium-*", "chrome-linux", "chrome")))
    return candidates[-1] if candidates else None


def _launch_chromium(playwright):
    """Launch Chromium the normal way; on failure, retry once against the
    full `chrome-linux/chrome` binary in PLAYWRIGHT_BROWSERS_PATH,
    explicitly, still headless — a browser-cache/package version skew is
    not something a test can fix (`playwright install` is out of bounds
    here per phase policy), but launching the full build this repository's
    preinstalled cache DOES carry, instead of the missing headless-shell
    variant Playwright's default now prefers, costs nothing and keeps
    this test actually running rather than perpetually skipping.

    Returns `(browser, None)` on success, or `(None, reason)` when
    nothing launches at all.
    """
    try:
        return playwright.chromium.launch(), None
    except Exception as exc:
        fallback = _find_full_chromium_binary(os.environ.get("PLAYWRIGHT_BROWSERS_PATH"))
        if fallback is None:
            return None, "Chromium launch failed (%r)" % (exc,)
        try:
            return playwright.chromium.launch(executable_path=fallback, headless=True), None
        except Exception as exc2:
            return None, (
                "Chromium launch failed (%r); fallback binary %r also failed (%r)"
                % (exc, fallback, exc2))


@pytest.fixture(scope="module")
def chromium_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        if _browser_required():
            pytest.fail(
                "playwright not installed, but CI / SKYPANE_REQUIRE_BROWSER=1 "
                "requires it: %r" % (exc,))
        pytest.skip("playwright not installed (dev-only dependency)")

    with sync_playwright() as p:
        browser, reason = _launch_chromium(p)
        if browser is None:
            if _browser_required():
                pytest.fail(
                    "Chromium could not launch, but CI / SKYPANE_REQUIRE_BROWSER=1 "
                    "requires it: %s" % reason)
            pytest.skip("Chromium could not launch: %s" % reason)
        try:
            yield browser
        finally:
            browser.close()


# --- companion/app.py subprocess, isolated per scenario -----------------

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
    companion/test_post_origin.py's own class, reimplemented here for
    the same reason that one gives for not importing
    test_companion_app.py's Harness: each file owns its own subprocess
    fixture.
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
        env[app.auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
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


class _StaticOriginServer:
    """A tiny SECOND loopback origin (a different port from the companion
    under test) serving one HTML page — the attacker page in the
    cross-origin proof. An auto-submitting native form from here is a
    genuine cross-site POST: no companion code, no companion cookie
    scope, nothing but the browser's own cross-origin navigation.
    """

    def __init__(self, html_bytes):
        html = html_bytes

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def start(self):
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self._thread.join(timeout=5)


def _read_bytes_or_none(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


# --- Scenario 1: a cross-origin form is rejected, state unchanged -------

def test_cross_origin_form_post_is_rejected_and_device_config_unchanged(
        chromium_browser, tmp_path):
    server = _CompanionServer(tmp_path)
    server.start()
    context = chromium_browser.new_context()
    evil = None
    try:
        page = context.new_page()
        _login(page, server.base_url())

        config_path = device_config.device_config_path(str(tmp_path))
        before = _read_bytes_or_none(config_path)

        target = server.base_url() + app.QUICK_DISPLAY_ROUTE
        html = (
            "<!doctype html><html>"
            "<body onload=\"document.getElementById('f').submit()\">"
            '<form id="f" method="POST" action="%s">'
            '<input type="hidden" name="%s" value="%s">'
            '<input type="hidden" name="return_to" value="%s">'
            "</form></body></html>"
        ) % (
            target, app.layout.QUICK_STATE_FIELD, app.layout.QUICK_STATE_OFF,
            app.layout.HOME_ROUTE,
        )
        evil = _StaticOriginServer(html.encode("utf-8"))
        evil.start()

        with page.expect_navigation(
                url=lambda u: u.startswith(server.base_url())) as nav_info:
            page.goto(evil.base_url())
        response = nav_info.value
        assert response.status == 403

        after = _read_bytes_or_none(config_path)
        assert after == before, (
            "device_config.json changed on disk after a rejected cross-origin "
            "POST — the 403 gate must run before any write")
    finally:
        if evil is not None:
            evil.stop()
        context.close()
        server.stop()


# --- Scenario 2: same-origin forms and the quick-switch fetch still work -

def test_same_origin_quick_switch_and_settings_save_still_work(chromium_browser, tmp_path):
    server = _CompanionServer(tmp_path)
    server.start()
    context = chromium_browser.new_context()
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + app.layout.HOME_ROUTE)

        # (a) the real quick-switch control — a genuine same-origin fetch
        # POST (companion/static/quick-switch.js), never a synthetic form.
        before_enabled = device_config.load_device_config(str(tmp_path))["display_enabled"]
        switch = page.locator(
            '[aria-labelledby="%s"]' % app.layout.QUICK_SWITCH_SCREEN_LABEL_ID)
        switch.wait_for(state="visible")
        switch.click()

        deadline = time.time() + 5.0
        changed = False
        while time.time() < deadline:
            if (device_config.load_device_config(str(tmp_path))["display_enabled"]
                    != before_enabled):
                changed = True
                break
            time.sleep(0.05)
        assert changed, (
            "the quick-switch fetch POST did not change display_enabled on "
            "disk within 5s on the same origin — the SEC-03 gate must allow "
            "a matching Origin + Sec-Fetch-Site: same-origin request")

        # (b) a normal Settings form save — companion/
        # test_browser_ux_helpers.py's own operate-submit-reload-verify
        # helper, scripts blocked: a genuine native <form> POST, the other
        # shape a same-origin POST can take.
        result = _persist_without_js(
            chromium_browser, server.base_url(), app.layout.DEVICE_ROUTE,
            config_page.WAKE_INTERVAL_FIELD_NAME, "600",
            lambda: device_config.load_device_config(str(tmp_path))["wake_interval_s"],
            restore=False)
        assert str(result["stored"]) == "600"
    finally:
        context.close()
        server.stop()
