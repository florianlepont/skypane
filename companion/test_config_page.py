#!/usr/bin/env python3
"""Contract harness for companion/pages/config_page.py — CFG-01's theme
picker, CFG-12's runway picker, and CFG-07's manual poll-trigger control
(06-CONTEXT.md).

Covers: render() emitting both fieldsets from server.device_config's own
registries with the current values pre-selected, both helper texts
appearing escaped-verbatim, the poll-trigger button's enabled/disabled
states, handle_post()'s server-side membership-test validation (a
non-member theme or runway writes nothing and reports the save-failure
flash key, a partial-field post carries the other setting forward
unchanged, two adversarial path-traversal/SQL-shaped payloads are
rejected by the same membership test), and one end-to-end HTTP round
trip proving the D-07 confirmation copy reaches a real browser response
after a real save.

Stdlib-only (json, os, shutil, socket, subprocess, sys, tempfile, time,
urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_config_page.py
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import app as companion_app  # noqa: E402
from companion import auth  # noqa: E402
from companion.layout import escape_html  # noqa: E402
from companion.pages import config_page  # noqa: E402
from server import device_config  # noqa: E402

TEST_PASSWORD = "config-page-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 23


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Same rationale as companion/test_companion_app.py's own copy: the
    end-to-end check below needs to see the real 303 and its Location
    header (to follow the save redirect by hand), not have it silently
    auto-followed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    """Minimal stdlib HTTP client, mirroring
    companion/test_companion_app.py's own http_request()."""
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Owns the companion/app.py subprocess lifecycle — structurally
    identical to companion/test_companion_app.py's own Harness class.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def state_path(self, *parts):
        return os.path.join(self.tmpdir, *parts)

    def start(self):
        env = dict(os.environ)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()

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

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def _login(harness, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def _write_device_config(state_dir, theme, tracked_runway, led_enabled=None):
    os.makedirs(state_dir, exist_ok=True)
    doc = {"theme": theme, "tracked_runway": tracked_runway}
    if led_enabled is not None:
        doc["led_enabled"] = led_enabled
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump(doc, fh)


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # Section 1: unit checks against render()/theme_fieldset()/
    # runway_fieldset()/poll_trigger_section() (Task 1 behavior bullets)
    # and handle_post() (Task 2 behavior bullets), each driven against a
    # temporary state directory and a hand-built ctx dict.
    # ==================================================================

    def _render_shape_three_fieldsets_and_save_button():
        ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if rendered.count("<fieldset") != 3:
            return False, "expected exactly 3 <fieldset occurrences, got %d" % rendered.count("<fieldset")
        if "Save Settings" not in rendered:
            return False, "expected the 'Save Settings' submit button copy"
        return True, ""
    check(
        "render() emits exactly three fieldsets and a Save Settings submit button",
        _render_shape_three_fieldsets_and_save_button)

    def _theme_fieldset_one_radio_per_registry_entry():
        rendered = config_page.theme_fieldset("sky")
        radio_count = rendered.count('name="theme"')
        if radio_count != len(device_config.THEMES):
            return False, (
                "expected %d theme radios (len(THEMES)), got %d"
                % (len(device_config.THEMES), radio_count))
        return True, ""
    check(
        "theme_fieldset() emits one radio per THEMES registry entry",
        _theme_fieldset_one_radio_per_registry_entry)

    def _runway_fieldset_exactly_three_radios():
        rendered = config_page.runway_fieldset("3")
        radio_count = rendered.count('name="tracked_runway"')
        if radio_count != 3:
            return False, "expected exactly 3 runway radios, got %d" % radio_count
        return True, ""
    check(
        "runway_fieldset() emits exactly three runway radio inputs",
        _runway_fieldset_exactly_three_radios)

    def _helper_texts_appear_escaped_verbatim():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        if escape_html(config_page.THEME_HELPER_TEXT) not in rendered:
            return False, "theme helper text missing (escaped-verbatim)"
        if escape_html(config_page.RUNWAY_HELPER_TEXT) not in rendered:
            return False, "runway helper text missing (escaped-verbatim)"
        if escape_html(config_page.LED_HELPER_TEXT) not in rendered:
            return False, "LED helper text missing (escaped-verbatim)"
        return True, ""
    check(
        "the theme, runway, and LED helper texts all appear escaped-verbatim in render()'s output",
        _helper_texts_appear_escaped_verbatim)

    def _current_theme_and_runway_are_selected():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "06-24"},
            "poll_cooldown_remaining": 0,
        })
        if 'value="06-24" checked' not in rendered:
            return False, "expected the non-default saved runway (06-24) to be marked selected"
        if 'value="3" checked' in rendered:
            return False, "expected runway 3 (not the saved value) to NOT be marked selected"
        if 'value="sky" checked' not in rendered:
            return False, "expected the saved theme (sky) to be marked selected"
        return True, ""
    check(
        "the currently-saved theme and (non-default) runway are the ones marked selected",
        _current_theme_and_runway_are_selected)

    def _poll_trigger_enabled_at_zero_cooldown():
        rendered = config_page.poll_trigger_section(0)
        if "disabled" in rendered:
            return False, "expected no disabled attribute at zero cooldown"
        if "Trigger Poll Now" not in rendered:
            return False, "expected the Trigger Poll Now button copy"
        return True, ""
    check(
        "poll_trigger_section(0) renders an enabled button",
        _poll_trigger_enabled_at_zero_cooldown)

    def _poll_trigger_disabled_with_remaining_seconds():
        rendered = config_page.poll_trigger_section(17)
        if "disabled" not in rendered:
            return False, "expected a disabled attribute at a non-zero cooldown"
        if "17" not in rendered:
            return False, "expected the remaining-seconds figure (17) in the visible copy"
        return True, ""
    check(
        "poll_trigger_section(17) renders a disabled button and the remaining-seconds copy",
        _poll_trigger_disabled_with_remaining_seconds)

    def _valid_save_writes_both_and_returns_saved_key():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky", "tracked_runway": "06-24"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk != {"theme": "sky", "tracked_runway": "06-24", "led_enabled": True}:
                return False, "on-disk config does not match the posted values: %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a valid theme and runway writes both and returns the saved flash key",
        _valid_save_writes_both_and_returns_saved_key)

    def _nonmember_theme_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "not-a-real-theme", "tracked_runway": "06-24"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member theme writes nothing and returns the save-failure flash key",
        _nonmember_theme_writes_nothing)

    def _nonmember_runway_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky", "tracked_runway": "not-a-real-runway"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member runway writes nothing and returns the save-failure flash key",
        _nonmember_runway_writes_nothing)

    def _theme_only_post_carries_runway_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "sky"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a theme but no runway field carries the existing runway forward unchanged",
        _theme_only_post_carries_runway_forward)

    def _path_traversal_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "../../etc/passwd", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a path-traversal-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a directory-traversal-shaped theme value is rejected by the membership test",
        _path_traversal_theme_rejected)

    def _sql_fragment_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky'; DROP TABLE flights; --", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a SQL-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a SQL-fragment-shaped theme value is rejected by the membership test",
        _sql_fragment_theme_rejected)

    def _save_oserror_returns_failure_key_not_raise():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            original_save = device_config.save_device_config

            def _raising_save(*args, **kwargs):
                raise OSError("simulated disk failure")

            device_config.save_device_config = _raising_save
            try:
                flash_key = config_page.handle_post(
                    {"theme": "sky", "tracked_runway": "3"}, ctx)
            finally:
                device_config.save_device_config = original_save
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED when save_device_config() raises OSError, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a save that raises OSError returns the save-failure flash key rather than propagating",
        _save_oserror_returns_failure_key_not_raise)

    # ------------------------------------------------------------------
    # LED section checks (Task 2, D-01/D-02/T-06.2-02) - a-f are unit
    # checks; g-h (below, inside the Harness block) drive real HTTP.
    # ------------------------------------------------------------------

    def _led_fieldset_checked_true():
        rendered = config_page.led_fieldset(True)
        if "checked" not in rendered:
            return False, "expected a checked attribute for led_fieldset(True)"
        if rendered.count('name="led_enabled"') != 1:
            return False, "expected exactly one name=\"led_enabled\" input"
        return True, ""
    check(
        "led_fieldset(True) contains a checked attribute and one name=\"led_enabled\" input",
        _led_fieldset_checked_true)

    def _led_fieldset_unchecked_false():
        rendered = config_page.led_fieldset(False)
        if "checked" in rendered:
            return False, "expected no checked attribute for led_fieldset(False)"
        return True, ""
    check(
        "led_fieldset(False) contains no checked attribute",
        _led_fieldset_unchecked_false)

    def _render_has_second_form_for_led_route():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'action="/config"' not in rendered:
            return False, "expected the /config form action to be present"
        if 'action="/config-led"' not in rendered:
            return False, "expected a second, distinct /config-led form action"
        return True, ""
    check(
        "render() emits a second <form whose action is the LED route, distinct from the /config form",
        _render_has_second_form_for_led_route)

    def _handle_led_post_unchecked_persists_false():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected led_enabled False on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_led_post({}, ctx) - the shape a browser sends for an unchecked checkbox - persists led_enabled False and returns the saved flash key",
        _handle_led_post_unchecked_persists_false)

    def _handle_led_post_checked_persists_true():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post(
                {"led_enabled": config_page.LED_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not True:
                return False, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_led_post({\"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True and returns the saved flash key",
        _handle_led_post_checked_persists_true)

    def _handle_led_post_crafted_value_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3", led_enabled=True)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_led_post(
                {"led_enabled": "<script>alert(1)</script>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted led_enabled value, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_led_post with a crafted non-checkbox value returns FLASH_SAVE_FAILED and leaves device_config.json byte-identical",
        _handle_led_post_crafted_value_rejected)

    # ==================================================================
    # Section 2: one end-to-end check — launches the real companion/app.py
    # subprocess, logs in, posts a valid theme-and-runway pair, follows
    # the redirect, and asserts the rendered page carries D-07's
    # confirmation copy verbatim and shows the newly-saved runway
    # selected. No unit check can establish that the router, this page
    # module, and the persistence layer actually agree end to end.
    # ==================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        def _save_round_trip_shows_confirmation_and_new_selection():
            status, headers, _ = http_request(
                base + "/config", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode(
                    {"theme": "sky", "tracked_runway": "06-24"}).encode())
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            redirect_status, _redirect_headers, body = http_request(
                base + location, cookie=session_cookie)
            if redirect_status != 200:
                return False, "expected 200 following the save redirect, got %d" % redirect_status
            # D-07's confirmation sentence is defined exactly once in the
            # repository, in companion/app.py's FLASH_MESSAGES mapping —
            # referenced here rather than re-typed, so this file is never
            # a second place that literal sentence lives.
            confirmation = escape_html(
                companion_app.FLASH_MESSAGES[companion_app.FLASH_KEY_SAVED])
            if confirmation.encode() not in body:
                return False, "expected D-07's exact confirmation copy in the response body"
            if b'value="06-24" checked' not in body:
                return False, "expected the newly-saved runway (06-24) to be shown selected"
            return True, ""
        check(
            "a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway selected",
            _save_round_trip_shows_confirmation_and_new_selection)

        def _led_post_empty_body_saves_false_and_renders_unchecked():
            status, headers, _ = http_request(
                base + "/config-led", method="POST", cookie=session_cookie,
                data=b"")
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected on-disk led_enabled False after an empty-body POST, got %r" % (on_disk["led_enabled"],)
            get_status, _get_headers, body = http_request(
                base + "/config", cookie=session_cookie)
            if get_status != 200:
                return False, "expected 200 on the follow-up GET /config, got %d" % get_status
            if b'name="led_enabled" value="on" checked' in body:
                return False, "expected the LED checkbox to render unchecked after saving False"
            return True, ""
        check(
            "a live authenticated POST /config-led with an empty body 303-redirects to /config?flash=saved, persists led_enabled False, and a follow-up GET /config renders the control unchecked",
            _led_post_empty_body_saves_false_and_renders_unchecked)

        def _led_post_unauthenticated_redirects_to_login_and_writes_nothing():
            config_path = device_config.device_config_path(harness.tmpdir)
            existed_before = os.path.exists(config_path)
            before = open(config_path, "rb").read() if existed_before else None
            status, headers, _ = http_request(
                base + "/config-led", method="POST", data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            exists_after = os.path.exists(config_path)
            if not existed_before and exists_after:
                return False, "an unauthenticated POST /config-led created device_config.json"
            if existed_before:
                after = open(config_path, "rb").read()
                if before != after:
                    return False, "an unauthenticated POST /config-led modified device_config.json"
            return True, ""
        check(
            "an unauthenticated POST /config-led redirects to /login and writes nothing",
            _led_post_unauthenticated_redirects_to_login_and_writes_nothing)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-page: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
