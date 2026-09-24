"""companion/test_browser_origin.py — SEC-03 (audit ledger 2026-09-23,
D-16): the browser-level half of the Origin/Sec-Fetch-Site proof
companion/test_post_origin.py already covers over plain HTTP — a REAL
browser proves the cross-origin rejection, and that same-origin forms and
the quick-switch fetch keep working.

Native pytest (companion/test_login_throttle.py established the shape),
drives Chromium through pytest-playwright's own session-scoped `browser`
fixture and the guarded `page`/`new_context` fixtures companion/conftest.py
overrides (Phase 33, TST-11): no launch of its own and no fallback binary
— a missing/unlaunchable Chromium is a visible pytest skip locally and a
hard failure in CI / SKYPANE_REQUIRE_BROWSER=1, exactly like every other
browser test in this tree.
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from companion import app
from companion.pages import config_page
from companion.test_browser_ux_helpers import _login, _persist_without_js
from server import device_config

pytestmark = pytest.mark.browser


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

def test_cross_origin_form_post_is_rejected_and_device_config_unchanged(app_server, page):
    _login(page, app_server.base_url())

    config_path = device_config.device_config_path(app_server.state_dir)
    before = _read_bytes_or_none(config_path)

    target = app_server.base_url() + app.QUICK_DISPLAY_ROUTE
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
    try:
        with page.expect_navigation(
                url=lambda u: u.startswith(app_server.base_url())) as nav_info:
            page.goto(evil.base_url())
        response = nav_info.value
        assert response.status == 403

        after = _read_bytes_or_none(config_path)
        assert after == before, (
            "device_config.json changed on disk after a rejected cross-origin "
            "POST — the 403 gate must run before any write")
    finally:
        evil.stop()


# --- Scenario 2: same-origin forms and the quick-switch fetch still work -

def test_same_origin_quick_switch_and_settings_save_still_work(app_server, page, browser):
    _login(page, app_server.base_url())
    page.goto(app_server.base_url() + app.layout.HOME_ROUTE)

    # (a) the real quick-switch control — a genuine same-origin fetch
    # POST (companion/static/quick-switch.js), never a synthetic form.
    before_enabled = device_config.load_device_config(app_server.state_dir)["display_enabled"]
    switch = page.locator(
        '[aria-labelledby="%s"]' % app.layout.QUICK_SWITCH_SCREEN_LABEL_ID)
    switch.wait_for(state="visible")
    switch.click()

    deadline = time.time() + 5.0
    changed = False
    while time.time() < deadline:
        if (device_config.load_device_config(app_server.state_dir)["display_enabled"]
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
    # shape a same-origin POST can take. It opens its own scripts-blocked
    # context on the shared `browser` handle (guard rule G10 exempts
    # companion/test_browser_ux_helpers.py itself, not this file — this
    # file never calls browser.new_context()/new_page() directly).
    result = _persist_without_js(
        browser, app_server.base_url(), app.layout.DEVICE_ROUTE,
        config_page.WAKE_INTERVAL_FIELD_NAME, "600",
        lambda: device_config.load_device_config(app_server.state_dir)["wake_interval_s"],
        restore=False)
    assert str(result["stored"]) == "600"
