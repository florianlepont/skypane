#!/usr/bin/env python3
"""Contract harness for the SkyPane companion service: companion/auth.py,
companion/layout.py, and (plan 06-05) the real subprocess-launched
companion/app.py route table.

Covers: constant-time password checking, fail-closed behaviour when no
password is configured, stateless signed session tokens (issue/verify
round trip, six distinct malformed-token rejections, forged-secret and
hand-built-expired coverage), session/logout cookie security flags,
cookie parsing, the process-global login-attempt throttle, the single
canonical HTML-escaping helper, the page shell's document shape and
active-nav/theme rendering, the status-dot/data-table component
builders, that AuthNotConfigured never leaks the configured password
value, the D-02 whole-site auth gate asserted route by route against a
real running service, the login failure/success flow and its cookie
flags, the 404 copy, the preview PNG path (missing file vs. a real
960,000-byte panel), gallery path-traversal rejection with a canary
file, and the server-global (not per-session) poll-trigger cooldown.

Checks are grouped under three clearly-commented sections: Section 1
(companion/auth.py) and Section 2 (companion/layout.py) are pure
in-process unit checks against the imported modules. Section 3 (plan
06-05) launches companion/app.py as a real subprocess on a free local
port and drives it with urllib.request, mirroring
stub-server/test_poll_cycle.py's Harness/http_request()/readiness-poll
pattern.

Stdlib-only (hashlib, hmac, html, os, shutil, socket, subprocess, sys,
tempfile, time, urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_companion_app.py
"""
import hashlib
import hmac
import html
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

from companion import auth, layout  # noqa: E402

TEST_PASSWORD = "companion-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
IMAGE_BYTES = 960000  # server/panel_format.py's IMAGE_BYTES, duplicated as a
# plain literal so this harness never has to import Pillow (or
# server.panel_format) itself, matching panel_format.py's own documented
# precedent for stub-server/make_test_panel.py's independent duplication.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 62  # 56 + 5 (06.6.1-04 Task 1: icon sprite) + 1 (Task 3: nav notification dot)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return None from redirect_request() so a 303 (or any other
    redirect) is surfaced to the caller as an HTTPError instead of being
    silently followed — the auth-gate and flash-key checks below need to
    see the raw status code and Location/Set-Cookie headers, not the page
    the redirect points at.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# A single shared opener with redirects disabled. Deliberately NOT built
# with urllib.request.HTTPCookieProcessor: this test server runs over
# plain HTTP, and companion/auth.py's session cookie always carries the
# `Secure` flag (correctly, for production) - http.cookiejar honours that
# flag and silently refuses to store or resend a Secure cookie over a
# non-HTTPS connection, which would make an automatic cookie jar quietly
# drop the session cookie in exactly this harness. Cookies are instead
# captured from Set-Cookie response headers and threaded through
# explicitly as plain Cookie request headers below.
_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    """Minimal stdlib HTTP client (mirrors
    stub-server/test_poll_cycle.py's http_request()): returns
    (status, headers_dict, raw_bytes) for both success and HTTP-error
    responses; connection-level failures propagate.
    """
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
    """Extract just the "name=value" portion of a Set-Cookie response
    header (dropping the trailing attribute flags), or None.
    """
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Owns the companion/app.py subprocess lifecycle: a free port, an
    isolated temp state directory, startup readiness polling, and clean
    teardown - structurally mirrors
    stub-server/test_poll_cycle.py's own Harness class.
    """

    def __init__(self, extra_args=()):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-companion-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None
        self.extra_args = list(extra_args)

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
        ] + self.extra_args
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
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
    """POST /login with `password` and return the session cookie's
    "name=value" pair. Raises AssertionError if login did not succeed -
    callers that expect failure should call http_request() directly.
    """
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def _sign_with_secret(payload, secret):
    """Hand-build an "expiry.signature" token signed with an arbitrary
    secret — used to construct forged/malformed tokens that never go
    through auth.issue_session_token().
    """
    signature = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (payload, signature)


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

    previous_password = os.environ.get(auth.PASSWORD_ENV_VAR)
    os.environ[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
    try:
        # ==================================================================
        # Section 1: companion/auth.py
        # ==================================================================

        def _password_ok_correct_and_wrong():
            if not auth.password_ok(TEST_PASSWORD):
                return False, "expected password_ok(correct) to be True"
            if auth.password_ok("definitely-the-wrong-password"):
                return False, "expected password_ok(wrong) to be False"
            return True, ""
        check(
            "password_ok() accepts the correct password and rejects a wrong one",
            _password_ok_correct_and_wrong)

        def _password_ok_unconfigured_fails_closed():
            saved = os.environ.pop(auth.PASSWORD_ENV_VAR, None)
            try:
                auth.password_ok("anything")
                return False, "expected AuthNotConfigured to be raised"
            except auth.AuthNotConfigured:
                return True, ""
            finally:
                if saved is not None:
                    os.environ[auth.PASSWORD_ENV_VAR] = saved
        check(
            "password_ok() raises AuthNotConfigured when the password env var is unset",
            _password_ok_unconfigured_fails_closed)

        def _issue_and_verify_round_trip():
            token = auth.issue_session_token()
            if not auth.verify_session_token(token):
                return False, "a freshly-issued token failed verification"
            return True, ""
        check(
            "verify_session_token(issue_session_token()) is True",
            _issue_and_verify_round_trip)

        def _verify_rejects_five_malformed_inputs():
            cases = {
                "empty string": "",
                "no separator": "nodotshere",
                "non-integer expiry": _sign_with_secret("not-a-number", TEST_PASSWORD),
                "different-secret signature": _sign_with_secret(
                    str(int(time.time()) + 3600), "a-completely-different-secret"),
                "expiry in the past": _sign_with_secret(
                    str(int(time.time()) - 100), TEST_PASSWORD),
            }
            for label, value in cases.items():
                if auth.verify_session_token(value) is not False:
                    return False, "expected False for %s (%r)" % (label, value)
            return True, ""
        check(
            "verify_session_token() returns False for five malformed inputs without raising",
            _verify_rejects_five_malformed_inputs)

        def _verify_rejects_flipped_signature():
            token = auth.issue_session_token()
            expiry, signature = token.split(".", 1)
            flipped_char = "0" if signature[0] != "0" else "1"
            flipped_signature = flipped_char + signature[1:]
            flipped_token = "%s.%s" % (expiry, flipped_signature)
            if auth.verify_session_token(flipped_token) is not False:
                return False, "flipping one signature character should invalidate the token"
            return True, ""
        check(
            "flipping a single hex character of a valid signature invalidates the token",
            _verify_rejects_flipped_signature)

        def _session_cookie_header_carries_security_flags():
            header = auth.session_set_cookie_header(auth.issue_session_token())
            for needle in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/"):
                if needle not in header:
                    return False, "missing %r in session cookie header: %r" % (needle, header)
            return True, ""
        check(
            "session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path",
            _session_cookie_header_carries_security_flags)

        def _logout_cookie_expires_immediately():
            header = auth.logout_set_cookie_header()
            if "Max-Age=0" not in header:
                return False, "expected Max-Age=0 in the logout cookie header: %r" % (header,)
            return True, ""
        check(
            "logout_set_cookie_header() expires the cookie immediately",
            _logout_cookie_expires_immediately)

        def _parse_cookies_multi_and_malformed():
            parsed = auth.parse_cookies(
                "%s=abc123; %s=dark" % (auth.SESSION_COOKIE_NAME, auth.UI_THEME_COOKIE_NAME))
            if parsed.get(auth.SESSION_COOKIE_NAME) != "abc123":
                return False, "expected the session cookie to parse, got %r" % (parsed,)
            if parsed.get(auth.UI_THEME_COOKIE_NAME) != "dark":
                return False, "expected the theme cookie to parse, got %r" % (parsed,)
            if auth.parse_cookies(None) != {}:
                return False, "expected an empty dict for a missing cookie header"
            if auth.parse_cookies("\x00\x01\x02 not a cookie") != {}:
                return False, "expected a malformed header to yield an empty dict, not raise"
            return True, ""
        check(
            "parse_cookies() returns each cookie by name and never raises on a bad header",
            _parse_cookies_multi_and_malformed)

        def _login_throttle_allows_locks_and_resets():
            throttle = auth.LoginThrottle(limit=3, lockout_s=60)
            for _ in range(2):
                if throttle.locked_out():
                    return False, "should not be locked out before reaching the failure limit"
                throttle.record_failure()
            throttle.record_failure()  # the 3rd failure reaches the limit
            if not throttle.locked_out():
                return False, "expected locked_out() True after reaching the failure limit"
            if throttle.seconds_remaining() <= 0:
                return False, "expected seconds_remaining() > 0 while locked out"
            throttle.record_success()
            if throttle.locked_out():
                return False, "expected record_success() to clear the lockout"
            return True, ""
        check(
            "LoginThrottle allows attempts up to its limit, locks out, then resets on success",
            _login_throttle_allows_locks_and_resets)

        def _forged_token_different_secret_rejected():
            forged = _sign_with_secret(
                str(int(time.time()) + 3600), "attacker-controlled-secret")
            if auth.verify_session_token(forged) is not False:
                return False, "a token signed with a different secret must not verify"
            return True, ""
        check(
            "a forged token signed with a different secret is rejected",
            _forged_token_different_secret_rejected)

        def _hand_built_expired_token_rejected():
            expiry = str(int(time.time()) - 1)
            token = _sign_with_secret(expiry, TEST_PASSWORD)
            if auth.verify_session_token(token) is not False:
                return False, "a token expired by exactly one second must be rejected"
            return True, ""
        check(
            "a hand-built token expired by one second is rejected despite a correct signature",
            _hand_built_expired_token_rejected)

        def _auth_not_configured_message_omits_password():
            saved = os.environ.pop(auth.PASSWORD_ENV_VAR, None)
            try:
                auth.configured_password()
                return False, "expected AuthNotConfigured to be raised"
            except auth.AuthNotConfigured as exc:
                if TEST_PASSWORD in str(exc):
                    return False, "the exception text must never contain the password value"
                return True, ""
            finally:
                if saved is not None:
                    os.environ[auth.PASSWORD_ENV_VAR] = saved
        check(
            "AuthNotConfigured's message never contains the configured password value",
            _auth_not_configured_message_omits_password)

        # ==================================================================
        # Section 2: companion/layout.py
        # (the route-driven check section arrives with plan 06-05's
        # companion/app.py)
        # ==================================================================

        def _escape_html_all_special_chars():
            hostile = "<script>&\"'</script>"
            escaped = layout.escape_html(hostile)
            # '&' legitimately survives *as the start of an entity* (e.g.
            # "&amp;", "&lt;") - compare against the stdlib's own reference
            # escaping instead of a naive per-character containment check,
            # which would false-positive on "&amp;" containing "&".
            expected = html.escape(hostile, quote=True)
            if escaped != expected:
                return False, "escape_html() diverged from html.escape(): %r != %r" % (escaped, expected)
            for literal_special_char in ("<", ">", '"', "'"):
                if literal_special_char in escaped:
                    return False, "unescaped %r survived in %r" % (literal_special_char, escaped)
            return True, ""
        check(
            "escape_html() escapes all five HTML-special characters",
            _escape_html_all_special_chars)

        def _escape_html_non_string_inputs():
            if layout.escape_html(None) != "":
                return False, "expected escape_html(None) == ''"
            if layout.escape_html(42) != "42":
                return False, "expected escape_html(42) == '42'"
            return True, ""
        check(
            "escape_html() coerces None to an empty string and non-strings to their string form",
            _escape_html_non_string_inputs)

        def _page_shell_document_shape():
            rendered = layout.page_shell(title="Health", active="health", body="<p>x</p>")
            if rendered.count("<html") != 1:
                return False, "expected exactly one <html occurrence, got %d" % rendered.count("<html")
            if 'lang="en"' not in rendered:
                return False, "expected a lang=\"en\" attribute"
            if "width=device-width" not in rendered:
                return False, "expected a viewport meta tag"
            if "/static/style.css" not in rendered:
                return False, "expected a stylesheet link"
            if layout.SITE_TITLE not in rendered:
                return False, "expected the site title to appear"
            missing = [
                route for route, _ in layout.NAV_TABS
                if ('href="%s"' % route) not in rendered]
            if missing:
                return False, "missing nav link hrefs: %r" % (missing,)
            return True, ""
        check(
            "page_shell() renders one document with lang/viewport/stylesheet/title/five nav links",
            _page_shell_document_shape)

        def _page_shell_marks_only_the_active_nav_tab():
            rendered = layout.page_shell(title="Health", active="health", body="")
            # Scope to the horizontal <nav class="nav-bar"> only — page_shell()
            # now also renders a vertical sidebar copy of the same links
            # (06.3-01's dashboard-shell rework), so searching the whole
            # document would match whichever copy comes first in source order.
            nav_start = rendered.find('<nav class="nav-bar">')
            nav_end = rendered.find("</nav>", nav_start)
            nav_bar_html = rendered[nav_start:nav_end]
            for route, _ in layout.NAV_TABS:
                slug = route.lstrip("/")
                href_needle = 'href="%s"' % route
                href_index = nav_bar_html.find(href_needle)
                if href_index == -1:
                    return False, "missing nav link for %r" % route
                tag_start = nav_bar_html.rfind("<a", 0, href_index)
                tag_end = nav_bar_html.find(">", href_index)
                tag = nav_bar_html[tag_start:tag_end]
                is_active_class_present = "nav-tab--active" in tag
                if slug == "health" and not is_active_class_present:
                    return False, "expected the active tab (%r) to carry the active class" % route
                if slug != "health" and is_active_class_present:
                    return False, "expected a non-active tab (%r) to not carry the active class" % route
            return True, ""
        check(
            "the nav link matching `active` carries a distinguishing class, the others do not",
            _page_shell_marks_only_the_active_nav_tab)

        def _theme_resolution():
            rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="dark")
            if 'data-ui-theme="dark"' not in rendered:
                return False, "expected data-ui-theme=\"dark\" in the rendered document"
            if layout.ui_theme_from_cookie({}) != "auto":
                return False, "expected ui_theme_from_cookie({}) == 'auto' for a missing cookie"
            unrecognised = {layout.UI_THEME_COOKIE_NAME: "not-a-real-theme"}
            if layout.ui_theme_from_cookie(unrecognised) != "auto":
                return False, "expected an unrecognised theme cookie to fall back to 'auto'"
            return True, ""
        check(
            "page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto",
            _theme_resolution)

        def _status_dot_states():
            ok_markup = layout.status_dot("ok", "All good")
            if "dot--ok" not in ok_markup or "All good" not in ok_markup:
                return False, "expected the ok-state class and the escaped label"
            unknown_markup = layout.status_dot("not-a-real-state", "<b>hi</b>")
            if "dot--warn" not in unknown_markup:
                return False, "expected an unrecognised state to fall back to the warn class"
            if "<b>" in unknown_markup:
                return False, "expected the label to be escaped"
            return True, ""
        check(
            "status_dot() encodes the state as a fixed class, escapes the label, falls back to warn",
            _status_dot_states)

        def _data_table_escapes_and_empty_state():
            table_markup = layout.data_table(["Name", "<x>"], [["<b>a</b>", "1"]])
            if "<b>a</b>" in table_markup or "<x>" in table_markup:
                return False, "expected header and cell values to be escaped"
            empty_markup = layout.data_table(["Name"], [])
            if "<table" in empty_markup:
                return False, "expected the empty-state block instead of a <table> for zero rows"
            return True, ""
        check(
            "data_table() escapes every header/cell and emits the empty-state block for zero rows",
            _data_table_escapes_and_empty_state)

        def _data_table_wrapped_for_horizontal_scroll():
            # 2026-08-28 mobile-cropping fix: a wide table (History's
            # timestamp/callsign/hex/airline/type columns, Airlines'
            # unresolved-prefix table) must scroll horizontally on a
            # phone viewport instead of overflowing past it uncropped.
            table_markup = layout.data_table(["A", "B"], [["1", "2"]])
            if '<div class="data-table-wrap">' not in table_markup:
                return False, "expected data_table() to wrap its <table> in a scrollable container"
            return True, ""
        check(
            "data_table() wraps its <table> in a horizontally-scrollable container",
            _data_table_wrapped_for_horizontal_scroll)

        def _sidebar_nav_renders_all_tabs_with_one_active():
            markup = layout.sidebar_nav("history")
            if 'aria-label="Primary navigation"' not in markup:
                return False, "expected the Primary navigation landmark label"
            for route, label in layout.NAV_TABS:
                if route not in markup or label not in markup:
                    return False, "expected every NAV_TABS route/label present"
            if markup.count("sidebar-link--active") != 1:
                return False, "expected exactly one active sidebar link"
            return True, ""
        check(
            "sidebar_nav() renders every NAV_TABS link with exactly one active",
            _sidebar_nav_renders_all_tabs_with_one_active)

        def _sidebar_nav_escapes_hostile_active():
            markup = layout.sidebar_nav("<script>alert(1)</script>")
            if "<script>" in markup:
                return False, "expected no raw <script> substring"
            if markup.count("sidebar-link--active") != 0:
                return False, "expected zero active links for a non-matching active slug"
            return True, ""
        check(
            "sidebar_nav() matches no tab and stays script-free for a hostile active value",
            _sidebar_nav_escapes_hostile_active)

        def _stat_tile_status_classes_caption_escape_and_content_passthrough():
            for status, expected_class in (
                ("ok", "stat-tile--ok"),
                ("warn", "stat-tile--warn"),
                ("error", "stat-tile--error"),
            ):
                markup = layout.stat_tile("c", "x", status)
                if expected_class not in markup:
                    return False, "expected %r to map to %r" % (status, expected_class)
            if "stat-tile--accent" not in layout.stat_tile("c", "x"):
                return False, "expected status=None to fall back to stat-tile--accent"
            if "stat-tile--accent" not in layout.stat_tile("c", "x", "not-a-real-state"):
                return False, "expected an unrecognised status to fall back to stat-tile--accent"
            if "<b>" in layout.stat_tile("<b>hi</b>", "x"):
                return False, "expected the caption to be escaped"
            dot_markup = layout.status_dot("ok", "All good")
            tile_markup = layout.stat_tile("Device", dot_markup, "ok")
            if "dot--ok" not in tile_markup:
                return False, "expected content_html to reach the output unmodified"
            return True, ""
        check(
            "stat_tile() maps status to a fixed class with an accent fallback, escapes the "
            "caption, and passes content_html through unmodified",
            _stat_tile_status_classes_caption_escape_and_content_passthrough)

        def _page_shell_renders_dashboard_shell_with_sidebar_and_duplicate_nav_theme():
            rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
            for needle in (
                '<div class="dashboard-shell">',
                '<aside class="dashboard-sidebar">',
                '<main class="page-content dashboard-main">',
            ):
                if needle not in rendered:
                    return False, "expected %r in the rendered shell" % needle
            if rendered.count('aria-label="Primary navigation"') != 1:
                return False, "expected exactly one Primary navigation landmark"
            if rendered.count('class="nav-bar"') != 1:
                return False, "expected exactly one horizontal nav-bar"
            if rendered.count('action="/ui-theme"') != 2:
                return False, "expected both theme-form copies posting to /ui-theme"
            return True, ""
        check(
            "page_shell() wraps header+sidebar+main in .dashboard-shell with both nav copies "
            "and both theme-form copies present",
            _page_shell_renders_dashboard_shell_with_sidebar_and_duplicate_nav_theme)

        def _page_shell_escapes_hostile_body():
            escaped_hostile_body = layout.escape_html("<script>alert(1)</script>")
            rendered = layout.page_shell(title="Health", active="health", body=escaped_hostile_body)
            if "<script>" in rendered:
                return False, "an unescaped <script> tag reached the rendered page"
            return True, ""
        check(
            "page_shell()'s output contains no unescaped script tag for an escaped hostile body",
            _page_shell_escapes_hostile_body)

        # --- 06.6.1-04 Task 1: icon sprite, whitelisted builder, stat_tile() icon slot ---

        def _icon_sprite_integrity():
            import re
            if len(layout.ICON_IDS) != 5:
                return False, "expected exactly five ICON_IDS, got %d" % len(layout.ICON_IDS)
            if len(set(layout.ICON_IDS)) != 5:
                return False, "expected ICON_IDS to have no duplicates"
            symbol_ids = re.findall(r'<symbol[^>]*id="([^"]+)"', layout.ICON_DEFS_HTML)
            if sorted(symbol_ids) != sorted(layout.ICON_IDS):
                return False, "sprite symbol ids %r do not match ICON_IDS %r" % (
                    symbol_ids, layout.ICON_IDS)
            if layout.ICON_DEFS_HTML.count("<symbol") != 5:
                return False, "expected exactly five <symbol occurrences, got %d" % (
                    layout.ICON_DEFS_HTML.count("<symbol"))
            if 'stroke="currentColor"' not in layout.ICON_DEFS_HTML:
                return False, "expected stroke=\"currentColor\" in the sprite"
            if 'fill="#' in layout.ICON_DEFS_HTML:
                return False, "a hard-coded hex fill would defeat the per-status tint"
            return True, ""
        check(
            "layout.ICON_IDS has exactly five unique members, each a symbol id in ICON_DEFS_HTML and vice versa",
            _icon_sprite_integrity)

        def _icon_html_whitelist_enforcement():
            for icon_id in layout.ICON_IDS:
                out = layout.icon_html(icon_id)
                if not out or "<use" not in out:
                    return False, "expected non-empty <use markup for %r, got %r" % (icon_id, out)
            for bad in ("not-an-icon", "", None):
                if layout.icon_html(bad) != "":
                    return False, "expected icon_html(%r) == ''" % (bad,)
            hostile = '"><script>alert(1)</script>'
            if layout.icon_html(hostile) != "":
                return False, "expected a hostile id to render nothing"
            if hostile in layout.icon_html(hostile):
                return False, "a hostile id string must never reach icon_html()'s output"
            return True, ""
        check(
            "icon_html() returns markup for every whitelisted id and '' for an unknown/empty/None/hostile id",
            _icon_html_whitelist_enforcement)

        def _stat_tile_backcompat_and_icon_slot():
            default_call = layout.stat_tile("c", "x")
            explicit_none = layout.stat_tile("c", "x", None)
            if default_call != explicit_none:
                return False, "expected stat_tile('c','x') == stat_tile('c','x',None)"
            if "<svg" in default_call:
                return False, "expected no <svg when icon is omitted"
            valid_icon = layout.ICON_IDS[0]
            with_icon = layout.stat_tile("Cap", "<p>y</p>", "ok", icon=valid_icon)
            if with_icon.count("<svg") != 1:
                return False, "expected exactly one <svg when a valid icon is supplied"
            if layout.STAT_TILE_ICON_CLASS not in with_icon:
                return False, "expected the tint class on the tile's icon"
            if "stat-tile--ok" not in with_icon:
                return False, "expected the status class to still be present"
            if with_icon.index("<svg") >= with_icon.index("Cap"):
                return False, "expected the icon markup to precede the caption text"
            return True, ""
        check(
            "stat_tile() is byte-identical with icon omitted and places a valid icon before the caption text",
            _stat_tile_backcompat_and_icon_slot)

        def _page_shell_emits_sprite_once_no_inline_styles():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if doc.count("<defs") != 1:
                return False, "expected exactly one <defs, got %d" % doc.count("<defs")
            if doc.count("<symbol") != 5:
                return False, "expected exactly five <symbol, got %d" % doc.count("<symbol")
            if doc.index("icon-defs") >= doc.index("dashboard-shell"):
                return False, "expected the sprite to precede the dashboard-shell div"
            if ' style="' in doc:
                return False, "page_shell() must emit no inline styles"
            return True, ""
        check(
            "page_shell() emits exactly one sprite (one <defs, five <symbol) before dashboard-shell, no inline styles",
            _page_shell_emits_sprite_once_no_inline_styles)

        def _icon_classes_match_stylesheet():
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for cls in ("icon-defs", "icon", layout.STAT_TILE_ICON_CLASS):
                if cls not in css:
                    return False, "expected class %r to be styled in companion/static/style.css" % cls
            return True, ""
        check(
            "the icon/icon-defs/STAT_TILE_ICON_CLASS class names all appear in companion/static/style.css",
            _icon_classes_match_stylesheet)

        # --- 06.6.1-04 Task 3: Health nav-tab notification dot ---

        def _health_nav_notification_dot():
            on = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert=True)
            off = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert=False)
            default = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if on.count(layout.NAV_NOTIFICATION_CLASS) != 1:
                return False, "expected the notification class exactly once when health_alert=True"
            if on.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 1:
                return False, "expected the alert suffix text exactly once when health_alert=True"
            if off.count(layout.NAV_NOTIFICATION_CLASS) != 0:
                return False, "expected zero notification-class occurrences when health_alert=False"
            if off.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 0:
                return False, "expected zero alert-suffix occurrences when health_alert=False"
            if default != off:
                return False, "expected the health_alert flag to default to off"
            side = on[on.index("sidebar-nav"):]
            href_index = side.index('href="/health"')
            dot_index = side.index(layout.NAV_NOTIFICATION_CLASS)
            anchor_close_index = side.index("</a>", href_index)
            if not (href_index < dot_index < anchor_close_index):
                return False, "expected the dot to sit inside the Health sidebar link"
            other_active = layout.page_shell(
                title="T", active="config", body="", health_alert=True)
            if other_active.count(layout.NAV_NOTIFICATION_CLASS) != 1:
                return False, "expected exactly one link to carry the dot regardless of the active tab"
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            if layout.NAV_NOTIFICATION_CLASS not in css:
                return False, "expected the notification class to be styled"
            if "visually-hidden" not in css:
                return False, "expected the visually-hidden utility class to be styled"
            return True, ""
        check(
            "the Health nav-tab notification dot appears only inside the Health sidebar link when health_alert=True, "
            "nowhere when False/omitted, and never on another link",
            _health_nav_notification_dot)

    finally:
        if previous_password is not None:
            os.environ[auth.PASSWORD_ENV_VAR] = previous_password
        else:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)

    # ==================================================================
    # Section 3: companion/app.py (plan 06-05) — a real companion/app.py
    # subprocess, launched on a free local port, driven with
    # urllib.request. This section owns its own harness lifecycle
    # (independent of Section 1/2's env-var save/restore above), and
    # tolerates the ADS-B aggregators being unreachable in this sandboxed
    # environment — the poll-trigger checks below assert on the flash
    # outcome and the cooldown behaviour, never on a flight being
    # detected.
    # ==================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()

        # --- D-02 whole-site auth gate: nine routes, asserted individually ---
        # A single forgotten require_session() call is a full auth
        # bypass, so each route below is its own check, not a shared loop
        # collapsed into one assertion.

        def _unauth_redirects_to_login(method, path, data=None):
            def _run():
                status, headers, body = http_request(base + path, method=method, data=data)
                if status != 303:
                    return False, "expected 303, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                if body:
                    return False, "expected an empty redirect body, got %d bytes of content" % len(body)
                return True, ""
            return _run

        for _tab_path in ("/config", "/health", "/airlines", "/history", "/preview"):
            check(
                "unauthenticated GET %s redirects to /login without page content" % _tab_path,
                _unauth_redirects_to_login("GET", _tab_path))

        check(
            "unauthenticated GET /preview.png redirects to /login without page content",
            _unauth_redirects_to_login("GET", "/preview.png"))

        check(
            "unauthenticated GET of a gallery image route redirects to /login without page content",
            _unauth_redirects_to_login("GET", "/gallery/whatever.png"))

        check(
            "unauthenticated POST /config redirects to /login without page content",
            _unauth_redirects_to_login(
                "POST", "/config",
                data=urllib.parse.urlencode({"ui_theme": "sky"}).encode()))

        check(
            "unauthenticated POST /poll-now redirects to /login without page content",
            _unauth_redirects_to_login("POST", "/poll-now"))

        # --- stylesheet: public, no session required ---

        def _stylesheet_public():
            status, headers, body = http_request(base + "/static/style.css")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/css" not in content_type:
                return False, "expected a text/css content type, got %r" % content_type
            if not body:
                return False, "expected a non-empty stylesheet body"
            return True, ""
        check(
            "GET /static/style.css succeeds without a session and returns a CSS content type",
            _stylesheet_public)

        # --- battery-trend script: public, no session required (06.5-01, D-02) ---

        def _battery_trend_script_public():
            status, headers, body = http_request(base + "/static/battery-trend.js")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/javascript" not in content_type:
                return False, "expected a text/javascript content type, got %r" % content_type
            if not body:
                return False, "expected a non-empty script body"
            cache_control = headers.get("Cache-Control", "")
            if "max-age=300" not in cache_control:
                return False, "expected Cache-Control max-age=300, got %r" % cache_control
            return True, ""
        check(
            "GET /static/battery-trend.js succeeds without a session and returns a JavaScript content type",
            _battery_trend_script_public)

        # --- login: wrong password, right password, cookie flags ---

        def _login_wrong_password():
            status, headers, body = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode({"password": "not-the-real-password"}).encode())
            if status != 401:
                return False, "expected 401 for a wrong password, got %d" % status
            if b"Incorrect password. Try again." not in body:
                return False, "expected the exact login-failure copy in the response body"
            if "Set-Cookie" in headers:
                return False, "expected no Set-Cookie header on a failed login"
            return True, ""
        check(
            "a login POST with the wrong password re-renders the form with the exact copy and sets no cookie",
            _login_wrong_password)

        def _login_correct_password():
            status, headers, _ = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode({"password": TEST_PASSWORD}).encode())
            if status != 303:
                return False, "expected a 303 redirect on successful login, got %d" % status
            if headers.get("Location") != "/config":
                return False, "expected a redirect to /config, got %r" % headers.get("Location")
            set_cookie = headers.get("Set-Cookie", "")
            for needle in ("HttpOnly", "Secure", "SameSite=Strict"):
                if needle not in set_cookie:
                    return False, "missing %r in the session cookie header: %r" % (needle, set_cookie)
            return True, ""
        check(
            "a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict and redirects to /config",
            _login_correct_password)

        session_cookie = _login(harness)

        # --- authenticated: all five tabs return 200 with their own heading ---

        for _tab_path, _heading in (
            ("/config", "Config"), ("/health", "Health"),
            ("/airlines", "Airlines"), ("/history", "History"),
            ("/preview", "Preview"),
        ):
            def _tab_ok(tab_path=_tab_path, heading=_heading):
                status, _headers, body = http_request(base + tab_path, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if heading.encode() not in body:
                    return False, "expected the %r heading in the response body" % heading
                return True, ""
            check(
                "authenticated GET %s returns 200 and contains its own %r heading" % (_tab_path, _heading),
                _tab_ok)

        # --- logout clears the cookie; a subsequent tab request is refused again ---

        def _logout_clears_cookie():
            status, headers, _ = http_request(base + "/logout", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect on logout, got %d" % status
            set_cookie = headers.get("Set-Cookie", "")
            if "Max-Age=0" not in set_cookie:
                return False, "expected the logout cookie header to carry Max-Age=0, got %r" % set_cookie
            return True, ""
        check("GET /logout clears the session cookie (Max-Age=0)", _logout_clears_cookie)

        def _tab_refused_after_logout():
            # Sessions are stateless signed cookies (companion/auth.py has
            # no server-side revocation store, by design) - logout works
            # by clearing the *client's* cookie, not by invalidating the
            # token server-side. A real browser discards the cookie the
            # instant it sees Max-Age=0, so the faithful way to prove "a
            # subsequent tab request is refused again" is to present no
            # cookie at all on the next request, exactly as a browser
            # would - resending the stale cookie value would prove
            # nothing (it would still verify, by design).
            status, headers, _ = http_request(base + "/config")
            if status != 303 or headers.get("Location") != "/login":
                return False, "expected a redirect to /login for a post-logout request, got %d/%r" % (
                    status, headers.get("Location"))
            return True, ""
        check(
            "a tab request after logout (no cookie presented) is refused again",
            _tab_refused_after_logout)

        # Re-authenticate for the remaining checks below.
        session_cookie = _login(harness)

        # --- 404 ---

        def _unknown_path_404():
            status, _headers, body = http_request(base + "/this-route-does-not-exist")
            if status != 404:
                return False, "expected 404, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check("an unknown path returns 404 with the exact 'Page not found.' copy", _unknown_path_404)

        # --- preview.png: missing file, then a real panel ---

        def _preview_missing():
            status, _headers, _body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 with no panel.bin present, got %d" % status
            return True, ""
        check("GET /preview.png with no panel file present returns 404", _preview_missing)

        def _preview_real_panel():
            with open(harness.state_path("panel.bin"), "wb") as fh:
                fh.write(b"\x11" * IMAGE_BYTES)  # an all-white, legal-nibble panel
            status, headers, body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 after writing a valid panel, got %d" % status
            if not body.startswith(PNG_SIGNATURE):
                return False, "expected the response body to start with the PNG signature"
            if headers.get("Content-Type") != "image/png":
                return False, "expected an image/png content type, got %r" % headers.get("Content-Type")
            return True, ""
        check(
            "GET /preview.png after writing a valid 960,000-byte panel returns a body starting with the PNG signature",
            _preview_real_panel)

        # --- gallery path-traversal rejection, with a canary file one level up ---

        os.makedirs(harness.state_path("gallery"), exist_ok=True)
        canary_marker = "TOP-SECRET-CANARY-MARKER-DO-NOT-SERVE"
        with open(harness.state_path("canary.txt"), "w") as fh:
            fh.write(canary_marker)

        _traversal_payloads = (
            ("parent-directory segments", "../canary.txt"),
            ("an absolute path", harness.state_path("canary.txt")),
            ("a null byte", "canary.txt\x00.png"),
        )
        _traversal_bodies = []

        for _label, _payload in _traversal_payloads:
            def _traversal_404(label=_label, payload=_payload):
                encoded = urllib.parse.quote(payload, safe="")
                status, _headers, body = http_request(
                    base + "/gallery/" + encoded, cookie=session_cookie)
                _traversal_bodies.append(body)
                if status != 404:
                    return False, "expected 404 for %s (%r), got %d" % (label, payload, status)
                return True, ""
            check("a gallery request with %s returns 404" % _label, _traversal_404)

        def _canary_never_returned():
            if not _traversal_bodies:
                return False, "no traversal responses were captured to inspect"
            for body in _traversal_bodies:
                if canary_marker.encode() in body:
                    return False, "the canary file's content leaked into a traversal response body"
            return True, ""
        check(
            "the canary file placed one level above the gallery directory never appears in any traversal response",
            _canary_never_returned)

        # --- poll-trigger cooldown: server-global, not per-session ---

        def _poll_trigger_first_call():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_triggered" not in location:
                return False, "expected the poll_triggered flash key in the redirect, got %r" % location
            return True, ""
        check(
            "a first poll trigger redirects with the poll_triggered flash key",
            _poll_trigger_first_call)

        def _poll_trigger_cooldown_same_session():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, "expected the poll_cooldown flash key in the redirect, got %r" % location
            return True, ""
        check(
            "an immediate second poll trigger redirects with the poll_cooldown flash key",
            _poll_trigger_cooldown_same_session)

        def _poll_trigger_cooldown_second_opener():
            second_session_cookie = _login(harness)
            status, headers, _ = http_request(
                base + "/poll-now", method="POST", cookie=second_session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, (
                    "expected a fresh second-opener session to also see the "
                    "poll_cooldown flash key, got %r" % location)
            return True, ""
        check(
            "a fresh second-opener session is refused by the same cooldown (server-global, not per-session)",
            _poll_trigger_cooldown_second_opener)

        # 2026-08-28 fix: a genuine run_once() failure (e.g. an unreadable
        # --geofence path, exactly what production hit when
        # deploy/skypane-companion.service never passed --geofence at all
        # and the relative default didn't resolve under its
        # WorkingDirectory) must redirect with the distinct poll_failed
        # flash key, never the misleading save_failed one - a poll
        # trigger failing has nothing to do with "couldn't save settings".
        def _poll_trigger_failure_uses_distinct_flash_key():
            broken_harness = Harness(extra_args=["--geofence", "/nonexistent/no-such-geofence.json"])
            try:
                broken_harness.start()
                broken_session = _login(broken_harness)
                status, headers, _ = http_request(
                    broken_harness.base_url() + "/poll-now", method="POST", cookie=broken_session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=poll_failed" not in location:
                    return False, "expected the poll_failed flash key, got %r" % location
                if "flash=save_failed" in location:
                    return False, "a poll-trigger failure must never reuse save_failed's misleading copy"
                return True, ""
            finally:
                broken_harness.stop()
                broken_harness.cleanup()
        check(
            "a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never save_failed",
            _poll_trigger_failure_uses_distinct_flash_key)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("companion-app: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
