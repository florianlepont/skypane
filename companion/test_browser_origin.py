"""Browser-level proof that a cross-origin POST is rejected while same-origin forms and the
quick-switch fetch keep working (companion/test_post_origin.py checks the same behaviour over
plain HTTP, without a browser).

Drives Chromium via pytest-playwright's session-scoped `browser` fixture and the guarded
`page`/`new_context` fixtures from companion/conftest.py: a missing Chromium skips locally and
fails in CI (SKYPANE_REQUIRE_BROWSER=1).
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
    """A second loopback origin serving one HTML page: the attacker page for the cross-origin
    proof. An auto-submitting form from here is a genuine cross-site POST, independent of any
    companion code or cookie scope.
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


def test_same_origin_quick_switch_and_settings_save_still_work(app_server, page, new_context):
    _login(page, app_server.base_url())
    page.goto(app_server.base_url() + app.layout.HOME_ROUTE)

    # The quick-switch control fires a same-origin fetch POST (companion/static/quick-switch.js),
    # never a synthetic form.
    before_enabled = device_config.load_device_config(app_server.state_dir)["display_enabled"]
    switch = page.locator(
        '[aria-labelledby="%s"]' % app.layout.QUICK_SWITCH_SCREEN_LABEL_ID)
    switch.wait_for(state="visible")
    # Wait on the POST's own response rather than a fixed sleep: under a
    # loaded parallel run the server subprocess can take seconds to answer.
    with page.expect_response(
            lambda resp: resp.request.method == "POST"
            and app.QUICK_DISPLAY_ROUTE in resp.url,
            timeout=30000) as response_info:
        switch.click()
    assert response_info.value.status < 400, (
        "the same-origin quick-switch POST was refused with %d — the SEC-03 "
        "gate must allow a matching Origin + Sec-Fetch-Site: same-origin "
        "request" % response_info.value.status)

    deadline = time.time() + 10.0
    changed = False
    while time.time() < deadline:
        if (device_config.load_device_config(app_server.state_dir)["display_enabled"]
                != before_enabled):
            changed = True
            break
        time.sleep(0.05)
    assert changed, (
        "the accepted same-origin quick-switch POST did not change "
        "display_enabled on disk")

    # A native <form> POST (scripts blocked) is the other shape a same-origin POST can take;
    # it uses its own scripts-blocked context via the guarded `new_context` factory from
    # companion/conftest.py.
    result = _persist_without_js(
        new_context, app_server.base_url(), app.layout.DEVICE_ROUTE,
        config_page.WAKE_INTERVAL_FIELD_NAME, "600",
        lambda: device_config.load_device_config(app_server.state_dir)["wake_interval_s"],
        restore=False)
    assert str(result["stored"]) == "600"
