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
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
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
EXPECTED_CHECK_COUNT = 108  # quick task 260902-qkm (2026-09-02): 1 new
# check pinning both nav-link geometries apart after restoring
# .mobile-nav__link's 44px/Body-size tap target (D-05 reached it by
# mistake) while .sidebar-link keeps its D-05 32px/Label-size compaction.
# 107 = quick task 260902-l9w Task 2 Commit B: 1 new
# check pinning both halves of the hidden-runway-radio touch-target fix:
# the new input.visually-hidden/select.visually-hidden rule exists, and
# the global input/select rule still declares both 44px minimums.
# 106 = quick task 260902-gjj Task 2 Commit A: 1 new
# check (card_status_class() maps to base_class + a fixed suffix for the
# three whitelisted states, empty string for None/unrecognised, diverging
# from stat_tile()'s own accent fallback).
# 105 = 06.6.4.1-08 Task 2: 3 new checks (NAV_TABS holds
# exactly 4 entries in settled order; sidebar_nav()/the mobile dropdown
# each render exactly 4 links with exactly one active; the eye glyph
# (icon-nav-preview) stays an ICON_IDS whitelist member and icon_html()
# returns non-empty markup for it) — the unauthenticated-redirect loop's
# "/preview" iteration was retargeted into its own explicit check in
# place (still a net +0 for that piece, folded into Task 1's own count
# below), not counted twice. # 102 = 06.6.4.1-08 Task 1: net +1 (101 -> 102) — 2 new
# checks (authenticated GET /preview redirects to /history; the same
# request with an arbitrary query string — including a next=-shaped and
# an https://evil.example-shaped value — still redirects to the
# identical /history location) minus 1 removed (the pre-existing
# "authenticated GET /preview returns 200 with the Preview heading"
# tab-iteration entry, retargeted away since D-22 retires the page and it
# can no longer return 200/a page heading). The unauthenticated-redirect
# and preview.png/gallery-image checks already covered the session-gate
# and byte-serving-route acceptance criteria and needed no change. # 101 =
# 06.6.4.1-07 Task 3: 1 new standing route-contract guard (nav tuple/page-titles dict/icon map size+key-set agreement, settings route constant equals NAV_TABS[0][0]) — the literal sweep found no remaining stale /config or /config-led occurrence in this file to fix, and three "five nav links"-shaped prose descriptions were reworded to stop hardcoding a route count that changes again in plan 08 (no check-count effect, prose only). # 100 = 06.6.4.1-07 Task 1: 4 new settings-route-rename checks (old path 404s authenticated, POST /settings redirects with flash, ?next=/settings hidden-field round trip, route/icon-map cross-module contract) — the five pre-existing tab-tuple/redirect/login-default/logout-refusal checks were retargeted from /config to /settings in place, not counted as new. # 96 = 06.6.4.1-02 Task 3: 4 new panel-lookup.js checks (pre-auth serving, ES5-dialect, route/src agreement, six-script-tag count) # 92 = 06.6.4.1-02 Task 2: 4 new illustration-image-route checks (real key, unknown key, traversal, unauthenticated) # 88 = 85 + 3 (heading-color-consistency: serif-heading contract both directions, single error token)  # 06.6.3-01 Task 2: 4 new pre-auth static-script
# regression checks (dirty-state.js/list-filter.js/copy-button.js/
# freshness.js, one each) + 1 new cross-file *_SCRIPT_ROUTE/*_SCRIPT_SRC
# DOM-contract-guard check, mirroring _three_file_nav_dom_contract_guard()'s
# own pattern; previously 80 = 06.6.2-08 code-review fix CR-01 added 1 regression check
# (skip-link tabindex="-1"); before that 79 = 73 (72 (71 (70 (69 (68: 06.6.1's own additions: 62 + 2
# (06.6.1-05 Task 1: nav-dropdown.js) + 4 (Task 3:
# toggle/dropdown/DOM-contract/no-JS)) + 1 (2026-08-29 quick task 260829-0rl,
# merged independently via origin/main PR #19: the gallery route's private
# caching-scope regression check, WR-02 from 06.4-REVIEW.md)) + 1
# (06.6.2-02: the genuine two-thread concurrent POST /poll-now check
# proving _POLL_LOCK serializes execution)) + 1 (06.6.2-03 Task 2: the new
# nav-dropdown.js progressive-enhancement state-machine check — the
# existing no-JS check was rewritten in place, not counted as new)) + 1
# (06.6.2-05 Task 3: GET /logout now 404s (D-11) — the pre-existing
# logout-cookie check was renamed to POST /logout, not counted as new)) + 1
# (06.6.2-06 Task 3: a new check pinning health_alert="warn"'s dot--warn
# treatment — the pre-existing health-nav-dot check was updated in place
# to True/False -> "error"/None, not counted as new)) + 6 (06.6.2-07 Task 3:
# deep-link-return round-trip, two open-redirect-rejection checks
# (https://evil.example and //evil.example, both exercised — the plan's
# own text names one "(or the other)" but both are cheap and directly
# threat-model-relevant, T-06.6.2-12), the GET-path next= validation
# no-hidden-field check, the login_shell() markup check, and the D-01/
# UXA-09 page_shell()/login_shell() lang="en" agreement guard — the five
# pre-existing NAV_TABS-redirect checks and the one POST /config redirect
# check were updated in place for the new ?next= carrying behavior, not
# counted as new).


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
            "page_shell() renders one document with lang/viewport/stylesheet/title/a nav link "
            "for every NAV_TABS route",
            _page_shell_document_shape)

        def _page_shell_marks_only_the_active_dropdown_link():
            rendered = layout.page_shell(title="Health", active="health", body="")
            # Scope to the dropdown's own <nav class="mobile-nav__nav" ...>
            # only — page_shell() also renders a vertical sidebar copy of
            # the same links (06.3-01's dashboard-shell rework), so
            # searching the whole document would match whichever copy
            # comes first in source order. This check was already
            # rescoped once, in 06.3-01, for that same "two copies of the
            # same links" reason; 06.6.1-05 rescopes it a second time, at
            # the surviving hamburger dropdown that replaced the
            # horizontal strip this check originally targeted.
            nav_start = rendered.find('<nav class="mobile-nav__nav"')
            nav_end = rendered.find("</nav>", nav_start)
            dropdown_nav_html = rendered[nav_start:nav_end]
            for route, _ in layout.NAV_TABS:
                slug = route.lstrip("/")
                href_needle = 'href="%s"' % route
                href_index = dropdown_nav_html.find(href_needle)
                if href_index == -1:
                    return False, "missing dropdown link for %r" % route
                tag_start = dropdown_nav_html.rfind("<a", 0, href_index)
                tag_end = dropdown_nav_html.find(">", href_index)
                tag = dropdown_nav_html[tag_start:tag_end]
                is_active_class_present = "mobile-nav__link--active" in tag
                if slug == "health" and not is_active_class_present:
                    return False, "expected the active link (%r) to carry the active class" % route
                if slug != "health" and is_active_class_present:
                    return False, "expected a non-active link (%r) to not carry the active class" % route
            return True, ""
        check(
            "the dropdown link matching `active` carries a distinguishing class, the others do not",
            _page_shell_marks_only_the_active_dropdown_link)

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

        def _nav_tabs_shrunk_to_four_settled_order():
            # 06.6.4.1-08 (D-22): NAV_TABS shrinks from five entries to
            # four — Preview is retired, its whole content absorbed into
            # History (06.6.4.1-05). Order matters: every nav renderer
            # walks NAV_TABS in this exact order.
            if len(layout.NAV_TABS) != 4:
                return False, "expected exactly 4 NAV_TABS entries, got %d" % len(layout.NAV_TABS)
            expected_routes = ("/settings", "/health", "/airlines", "/history")
            actual_routes = tuple(route for route, _ in layout.NAV_TABS)
            if actual_routes != expected_routes:
                return False, (
                    "expected NAV_TABS routes in order %r, got %r"
                    % (expected_routes, actual_routes))
            return True, ""
        check(
            "layout.NAV_TABS holds exactly 4 entries, in order settings/health/airlines/history",
            _nav_tabs_shrunk_to_four_settled_order)

        def _sidebar_and_dropdown_render_exactly_four_links_one_active_each():
            sidebar_markup = layout.sidebar_nav("history")
            sidebar_link_count = sidebar_markup.count('<a class="sidebar-link')
            if sidebar_link_count != 4:
                return False, "expected exactly 4 sidebar nav links, got %d" % sidebar_link_count
            if sidebar_markup.count("sidebar-link--active") != 1:
                return False, "expected exactly one active sidebar link"

            doc = layout.page_shell(title="T", active="history", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            dropdown_link_count = panel.count('<a class="mobile-nav__link')
            if dropdown_link_count != 4:
                return False, "expected exactly 4 mobile dropdown links, got %d" % dropdown_link_count
            if panel.count("mobile-nav__link--active") != 1:
                return False, "expected exactly one active mobile dropdown link"
            return True, ""
        check(
            "a rendered authenticated page contains exactly four sidebar nav links and exactly "
            "four mobile dropdown links, with exactly one marked active in each",
            _sidebar_and_dropdown_render_exactly_four_links_one_active_each)

        def _eye_glyph_survives_nav_shrink():
            # 06.6.4.1-08 (D-22): "icon-nav-preview" (the eye glyph) stays
            # in the ICON_IDS whitelist even though NAV_ICON_IDS no longer
            # maps a "preview" slug to it — companion/pages/history_page.py's
            # View-panel trigger is its sole remaining consumer.
            if "icon-nav-preview" not in layout.ICON_IDS:
                return False, "expected icon-nav-preview to remain an ICON_IDS whitelist member"
            markup = layout.icon_html("icon-nav-preview")
            if not markup or "<svg" not in markup:
                return False, "expected icon_html('icon-nav-preview') to return non-empty <svg markup"
            return True, ""
        check(
            "the eye glyph (icon-nav-preview) is still a whitelist member and icon_html() returns "
            "non-empty markup for it, even though its nav-slug mapping was removed",
            _eye_glyph_survives_nav_shrink)

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

        def _card_status_class_whitelist_and_empty_fallback():
            # quick task 260902-gjj (ISSUE 2): card_status_class()'s own
            # contract, following stat_tile()'s check above in shape —
            # the three whitelisted mappings, and the empty string (not
            # an accent fallback class) for both None and an unrecognised
            # status, per that function's own documented divergence from
            # stat_tile()'s accent fallback.
            for status, expected_class in (
                ("ok", "page-section--ok"),
                ("warn", "page-section--warn"),
                ("error", "page-section--error"),
            ):
                got = layout.card_status_class("page-section", status)
                if got != expected_class:
                    return False, "expected %r to map to %r, got %r" % (status, expected_class, got)
            if layout.card_status_class("page-section", None) != "":
                return False, "expected status=None to fall back to the empty string"
            if layout.card_status_class("page-section", "not-a-real-state") != "":
                return False, "expected an unrecognised status to fall back to the empty string"
            if layout.card_status_class("battery-trend-section", "ok") != "battery-trend-section--ok":
                return False, "expected base_class to be reused verbatim in the modifier's own prefix"
            return True, ""
        check(
            "card_status_class() maps status to base_class + a fixed suffix for the three whitelisted "
            "states, and falls back to the empty string (not an accent class) for None or an unrecognised "
            "status — the divergence from stat_tile()'s own fallback (quick task 260902-gjj, ISSUE 2)",
            _card_status_class_whitelist_and_empty_fallback)

        def _page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme():
            rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
            for needle in (
                '<div class="dashboard-shell">',
                '<aside class="dashboard-sidebar">',
                '<main class="page-content dashboard-main" id="main-content" tabindex="-1">',
            ):
                if needle not in rendered:
                    return False, "expected %r in the rendered shell" % needle
            # 06.6.1-05: two nav landmarks now exist — sidebar_nav() and
            # the hamburger dropdown's _mobile_nav_html() — deliberately
            # sharing the same "Primary navigation" aria-label
            # (06.6.1-UI-SPEC.md's Layout Contract); CSS alone decides
            # which is visible at a given width, so both are always in
            # the DOM. This was "exactly one" before this plan, when the
            # horizontal strip carried no landmark of its own.
            if rendered.count('aria-label="Primary navigation"') != 2:
                return False, "expected exactly two Primary navigation landmarks (sidebar + dropdown)"
            if rendered.count('id="%s"' % layout.MOBILE_NAV_ID) != 1:
                return False, "expected exactly one dropdown panel"
            if rendered.count('action="/ui-theme"') != 2:
                return False, "expected both theme-form copies posting to /ui-theme"
            return True, ""
        check(
            "page_shell() wraps header+sidebar+main in .dashboard-shell with both nav landmarks "
            "and both theme-form copies present",
            _page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme)

        def _page_shell_skip_link_target_is_focusable():
            # CR-01: the skip link's href="#main-content" target must
            # itself be focusable (tabindex="-1") or activating the link
            # scrolls the viewport without moving keyboard focus, per the
            # HTML fragment-navigation focusing steps (WCAG SCR28/G1).
            rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
            if '<a class="skip-link" href="#main-content">Skip to content</a>' not in rendered:
                return False, "expected the skip link to point at #main-content"
            if 'id="main-content" tabindex="-1"' not in rendered:
                return False, "expected the skip link's target to carry tabindex=\"-1\""
            return True, ""
        check(
            "page_shell()'s skip link target carries tabindex=\"-1\" so it actually receives focus",
            _page_shell_skip_link_target_is_focusable)

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
            # 06.6.3: the whitelist grew from ten to fourteen members
            # (icon-check/icon-copy/icon-refresh/icon-search, D-05/
            # D-23/D-12/D-20) — see layout.py's own header comment on
            # ICON_IDS for the supersession note.
            if len(layout.ICON_IDS) != 14:
                return False, "expected exactly fourteen ICON_IDS, got %d" % len(layout.ICON_IDS)
            if len(set(layout.ICON_IDS)) != 14:
                return False, "expected ICON_IDS to have no duplicates"
            symbol_ids = re.findall(r'<symbol[^>]*id="([^"]+)"', layout.ICON_DEFS_HTML)
            if sorted(symbol_ids) != sorted(layout.ICON_IDS):
                return False, "sprite symbol ids %r do not match ICON_IDS %r" % (
                    symbol_ids, layout.ICON_IDS)
            if layout.ICON_DEFS_HTML.count("<symbol") != 14:
                return False, "expected exactly fourteen <symbol occurrences, got %d" % (
                    layout.ICON_DEFS_HTML.count("<symbol"))
            if 'stroke="currentColor"' not in layout.ICON_DEFS_HTML:
                return False, "expected stroke=\"currentColor\" in the sprite"
            if 'fill="#' in layout.ICON_DEFS_HTML:
                return False, "a hard-coded hex fill would defeat the per-status tint"
            return True, ""
        check(
            "layout.ICON_IDS has exactly fourteen unique members, each a symbol id in ICON_DEFS_HTML and vice versa",
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
            if doc.count("<symbol") != 14:
                return False, "expected exactly fourteen <symbol, got %d" % doc.count("<symbol")
            if doc.index("icon-defs") >= doc.index("dashboard-shell"):
                return False, "expected the sprite to precede the dashboard-shell div"
            if ' style="' in doc:
                return False, "page_shell() must emit no inline styles"
            return True, ""
        check(
            "page_shell() emits exactly one sprite (one <defs, fourteen <symbol) before dashboard-shell, "
            "no inline styles",
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

        # --- heading-color-consistency debug session -------------------
        #
        # D-03's serif-headings contract lived only as an allow-list in a
        # style.css comment, and `legend` was never added to it — so
        # `<legend>Diagnostic LED</legend>` rendered sans-serif semibold
        # directly above a serif-regular `<h2 class="text-heading">Poll
        # </h2>` at the same 20px size on the Config page. These two
        # checks make the contract executable in both directions: every
        # heading role IS serif, and no dense/tabular role IS NOT.

        def _every_heading_role_is_serif():
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            # The single selector that grants the serif family. Every
            # heading role in the app must be a member of it.
            start = css.find("h1,\nh2,\nh3,\nlegend,\n.text-heading {")
            if start == -1:
                return False, (
                    "expected one combined serif-heading selector listing "
                    "h1, h2, h3, legend and .text-heading — a heading role "
                    "was removed from it, or the selector was reformatted "
                    "(if reformatted, update this check deliberately)")
            block = css[start:css.index("}", start)]
            for declaration in (
                    "font-family: var(--font-serif)",
                    "font-weight: var(--weight-regular)"):
                if declaration not in block:
                    return False, (
                        "the serif-heading rule no longer declares %r"
                        % (declaration,))
            # legend must not restate font-weight in its own later rule:
            # both selectors are bare `legend` (0,0,1), so a weight
            # declared there silently beats the rule above regardless of
            # what the rule above says. This is the exact defect.
            legend_start = css.find("\nlegend {")
            if legend_start == -1:
                return False, "expected a bare `legend` rule in style.css"
            legend_block = css[legend_start:css.index("}", legend_start)]
            if "font-weight" in legend_block:
                return False, (
                    "the standalone `legend` rule declares font-weight "
                    "again; at equal specificity it wins over the serif "
                    "heading rule and re-breaks legend/h2 consistency")
            return True, ""
        check(
            "every heading role (h1/h2/h3/legend/.text-heading) shares one "
            "serif rule, and `legend` does not override its weight",
            _every_heading_role_is_serif)

        def _serif_never_reaches_dense_content():
            # D-03's other half: serif is headings-only. Body, tables,
            # form controls, nav links and mono content stay on
            # --font-ui. Guards against the rejected "serif partout"
            # option creeping back in one rule at a time.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            forbidden = (
                ".data-table", ".cell-primary", ".cell-secondary",
                ".mono", ".text-body", ".sidebar-link", ".mobile-nav__link")
            for selector in forbidden:
                index = css.find("\n%s {" % selector)
                if index == -1:
                    continue
                block = css[index:css.index("}", index)]
                if "--font-serif" in block:
                    return False, (
                        "%s applies --font-serif; serif is a headings-only "
                        "treatment (D-03), never dense/tabular content"
                        % selector)
            return True, ""
        check(
            "--font-serif never reaches table, body, mono or nav-link rules "
            "(D-03's headings-only boundary)",
            _serif_never_reaches_dense_content)

        def _nav_link_geometries_stay_diverged():
            # 260902-qkm: D-05 (06.6.4-04) reached .mobile-nav__link by
            # mistake — the mobile dropdown is the phone's only nav, with
            # no desktop compactness argument to trade against, while
            # .sidebar-link is structurally desktop-only (hidden below
            # 960px). The two renderings are now deliberately different
            # sizes: the mobile link keeps a real tap target, the desktop
            # sidebar stays compact, and neither may drift into the other.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()

            def block_for(selector):
                index = css.find("\n%s {" % selector)
                if index == -1:
                    return None
                return css[index:css.index("}", index)]

            mobile_block = block_for(".mobile-nav__link")
            if mobile_block is None:
                return False, "expected a `.mobile-nav__link` rule in style.css"
            if "min-height: 44px" not in mobile_block:
                return False, (
                    ".mobile-nav__link lost its restored min-height: 44px "
                    "tap target (260902-qkm)")
            if "font-size: var(--font-body-size)" not in mobile_block:
                return False, (
                    ".mobile-nav__link's font size drifted off "
                    "var(--font-body-size) (260902-qkm)")

            sidebar_block = block_for(".sidebar-link")
            if sidebar_block is None:
                return False, "expected a `.sidebar-link` rule in style.css"
            if "height: 32px" not in sidebar_block:
                return False, (
                    ".sidebar-link's D-05 32px desktop compaction was "
                    "reverted — it is structurally desktop-only and "
                    "should stay compact, unlike the mobile dropdown link")
            if "font-size: var(--font-label-size)" not in sidebar_block:
                return False, (
                    ".sidebar-link's font size drifted off "
                    "var(--font-label-size)")
            return True, ""
        check(
            "mobile dropdown nav link keeps its restored 44px/Body-size "
            "tap target while the desktop sidebar link stays at its D-05 "
            "32px/Label-size compaction (260902-qkm)",
            _nav_link_geometries_stay_diverged)

        def _one_error_signal_token():
            # --color-destructive and --color-status-error held identical
            # values in all four token blocks while being used
            # interchangeably for one concept, so "change the error
            # colour" silently meant "change two tokens in four places".
            # The duplicate is gone; this keeps it gone.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            # Comments are stripped first: the rules that used to read
            # this token now carry comments explaining why they no
            # longer do, and that prose must not trip the check it
            # documents.
            declarations = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            if "--color-destructive" in declarations:
                return False, (
                    "--color-destructive is back; it duplicated "
                    "--color-status-error exactly and is the reason the two "
                    "could drift. Use --color-status-error")
            return True, ""
        check(
            "there is exactly one error-signal colour token "
            "(--color-status-error), no --color-destructive duplicate",
            _one_error_signal_token)

        # --- 06.6.1-04 Task 3 / 06.6.1-05: Health nav notification dot ---
        #
        # Retargeted a third time by 06.6.1-05, beyond the plan's own
        # stated two — 06.6.1-05-PLAN.md's Task 3 read_first names only
        # the active-link and dashboard-shell checks as broken by Task 2,
        # but this one (from plan 06.6.1-04) also assumed a single nav
        # renderer and needs the same one-dot-per-renderer update the
        # plan's own Task 2 acceptance criteria already specifies
        # ("exactly two notification dots, one inside each Health link").

        def _health_nav_notification_dot():
            on = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert="error")
            off = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert=None)
            default = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if on.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected the notification class exactly twice (one per nav renderer) when health_alert='error'"
            if on.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 2:
                return False, "expected the alert suffix text exactly twice when health_alert='error'"
            if off.count(layout.NAV_NOTIFICATION_CLASS) != 0:
                return False, "expected zero notification-class occurrences when health_alert=None"
            if off.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 0:
                return False, "expected zero alert-suffix occurrences when health_alert=None"
            if default != off:
                return False, "expected the health_alert flag to default to off"
            side = on[on.index("sidebar-nav"):on.index("</aside>")]
            side_href_index = side.index('href="/health"')
            side_dot_index = side.index(layout.NAV_NOTIFICATION_CLASS)
            side_anchor_close_index = side.index("</a>", side_href_index)
            if not (side_href_index < side_dot_index < side_anchor_close_index):
                return False, "expected the dot to sit inside the Health sidebar link"
            dropdown = on[on.index('id="%s"' % layout.MOBILE_NAV_ID):on.index("</header>")]
            drop_href_index = dropdown.index('href="/health"')
            drop_dot_index = dropdown.index(layout.NAV_NOTIFICATION_CLASS)
            drop_anchor_close_index = dropdown.index("</a>", drop_href_index)
            if not (drop_href_index < drop_dot_index < drop_anchor_close_index):
                return False, "expected the dot to sit inside the Health dropdown link"
            other_active = layout.page_shell(
                title="T", active="config", body="", health_alert="error")
            if other_active.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected exactly two dot occurrences (one per nav renderer) regardless of the active tab"
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            if layout.NAV_NOTIFICATION_CLASS not in css:
                return False, "expected the notification class to be styled"
            if "visually-hidden" not in css:
                return False, "expected the visually-hidden utility class to be styled"
            return True, ""
        check(
            "the Health notification dot appears inside the Health link in both nav renderers "
            "when health_alert='error', nowhere when None/omitted, and never on another link",
            _health_nav_notification_dot)

        def _hidden_form_control_floor_and_global_floor_both_survive():
            # quick task 260902-l9w: the runway radio's own utility class
            # (visually-hidden) is inert on an <input> unless the global
            # `input, select` rule's 44px minimums are separately cleared
            # for it — a rule that only asserts the new clearing rule
            # would still pass after someone deleted the global 44px
            # floor site-wide, and a rule that only asserts the floor
            # would still pass after someone deleted the clearing fix.
            # This check fails if either half is missing.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            if "input.visually-hidden" not in css:
                return False, (
                    "expected an input.visually-hidden (or "
                    "select.visually-hidden) rule clearing the global "
                    "44px touch-target floor off hidden form controls "
                    "(the runway radio's own utility class is otherwise "
                    "clamped back up to 44x44 by the global input/select "
                    "rule below)")
            global_start = css.find("\ninput,\nselect {")
            if global_start == -1:
                return False, (
                    "expected the global `input,\\nselect {` rule; it may "
                    "have been reformatted (update this check "
                    "deliberately) or removed")
            global_block = css[global_start:css.index("}", global_start)]
            for declaration in ("min-height: 44px", "min-width: 44px"):
                if declaration not in global_block:
                    return False, (
                        "the global input/select rule no longer declares "
                        "%r; this is a deliberate, developer-accepted "
                        "WCAG 2.5.5 floor for every native field except "
                        "the ones explicitly scoped away from it (D-08, "
                        "the LED checkbox, and now the hidden runway "
                        "radio) and must survive byte-identical"
                        % (declaration,))
            return True, ""
        check(
            "input.visually-hidden/select.visually-hidden clears the 44px "
            "touch-target floor off hidden form controls, and the global "
            "input/select rule still declares both 44px minimums for "
            "every other field",
            _hidden_form_control_floor_and_global_floor_both_survive)

        def _health_nav_notification_dot_warn_severity():
            warn = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert="warn")
            if warn.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected the notification class exactly twice (one per nav renderer) when health_alert='warn'"
            if "dot--warn" not in warn:
                return False, "expected dot--warn to appear when health_alert='warn'"
            if "dot--error" in warn:
                return False, "expected no dot--error class anywhere when health_alert='warn'"
            return True, ""
        check(
            "layout.page_shell(..., health_alert='warn') also renders the notification dot, "
            "using dot--warn rather than dot--error",
            _health_nav_notification_dot_warn_severity)

        # --- 06.6.1-05 Task 1: nav-dropdown.js ES5-safe/side-effect-free dialect ---

        def _nav_dropdown_script_es5_safe_and_side_effect_free():
            # These are standing constraints on the file, not incidental
            # facts — companion/static/battery-trend.js's own header
            # states the same rules for the same reasons: no build step,
            # ES5-safe subset, no network call, no timer, no persistent
            # state.
            js_path = os.path.join(HERE, "static", "nav-dropdown.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
                "setTimeout", "setInterval", "innerHTML", "document.write",
                "eval(")
            for token in banned:
                if token in src:
                    return False, "nav-dropdown.js must not contain %r" % token
            if "aria-expanded" not in src:
                return False, "expected the open state to be read from aria-expanded"
            return True, ""
        check(
            "nav-dropdown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "fetch/XHR/timers/innerHTML/document.write/eval) — standing constraints on the file",
            _nav_dropdown_script_es5_safe_and_side_effect_free)

        # --- 06.6.1-05 Task 3: toggle ARIA contract, dropdown contents, ---
        # --- three-file DOM contract, no-JS floor                      ---

        def _toggle_aria_contract_and_fixed_label():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if 'type="button"' not in doc:
                return False, "expected the toggle to be type=\"button\""
            if ('id="%s"' % layout.NAV_TOGGLE_ID) not in doc:
                return False, "expected the toggle id in the document"
            if 'aria-expanded="false"' not in doc:
                return False, "expected the toggle to render aria-expanded=\"false\""
            if ('aria-controls="%s"' % layout.MOBILE_NAV_ID) not in doc:
                return False, "expected aria-controls to name the panel id"
            if layout.NAV_TOGGLE_LABEL not in doc:
                return False, "expected the fixed toggle label in the document"
            if "Close menu" in doc:
                return False, "the toggle's accessible label must never swap to a close verb"
            if layout.MOBILE_NAV_OPEN_CLASS in doc:
                return False, "the panel must never render carrying the open class"
            return True, ""
        check(
            "the hamburger toggle carries type=button/id/aria-expanded=false/aria-controls and the "
            "fixed accessible label (never a close-verb variant), and the panel never renders open",
            _toggle_aria_contract_and_fixed_label)

        def _dropdown_contents_and_order():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            for route, _label in layout.NAV_TABS:
                if ('href="%s"' % route) not in panel:
                    return False, "missing dropdown href for %r" % route
            if panel.count("mobile-nav__link--active") != 1:
                return False, "expected exactly one active dropdown link"
            theme_index = panel.find('action="/ui-theme"')
            if theme_index == -1:
                return False, "expected the theme form inside the dropdown"
            for route, _label in layout.NAV_TABS:
                href_index = panel.index('href="%s"' % route)
                if href_index > theme_index:
                    return False, "expected every nav link to precede the theme form in the dropdown"
            return True, ""
        check(
            "the dropdown panel holds every NAV_TABS link (exactly one active) followed by the "
            "theme form, in that order",
            _dropdown_contents_and_order)

        def _three_file_nav_dom_contract_guard():
            # Replicates the Python/CSS/JS drift guard 06.5-02 established
            # for the battery chart — a menu that never opens on a phone
            # would otherwise ship with every individual file still valid
            # on its own and no automated signal.
            js_path = os.path.join(HERE, "static", "nav-dropdown.js")
            with open(js_path) as fh:
                js = fh.read()
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for literal in (
                layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID,
                layout.MOBILE_NAV_OPEN_CLASS,
            ):
                if literal not in js:
                    return False, "DOM contract drift: %r is not looked up by nav-dropdown.js" % literal
            for cls in (
                "site-nav-toggle", "mobile-nav", "mobile-nav--open",
                "mobile-nav__nav", "mobile-nav__link",
            ):
                if cls not in css:
                    return False, "DOM contract drift: %r is not styled in style.css" % cls
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            for literal in (layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID):
                if literal not in doc:
                    return False, "DOM contract drift: %r is not rendered" % literal
            import companion.app as app_module
            if app_module.NAV_SCRIPT_ROUTE != layout.NAV_DROPDOWN_SCRIPT_SRC:
                return False, "nav script route drift: %r vs %r" % (
                    app_module.NAV_SCRIPT_ROUTE, layout.NAV_DROPDOWN_SCRIPT_SRC)
            return True, ""
        check(
            "companion.app.NAV_SCRIPT_ROUTE, layout's nav DOM-contract literals, nav-dropdown.js "
            "and style.css all agree with each other and with a rendered document",
            _three_file_nav_dom_contract_guard)

        def _dropdown_survives_with_javascript_disabled():
            # UXA-02/UXA-12's joint fix, verified against the
            # server-rendered document only (this harness has no real
            # browser). The SSR default must be unclipped/complete — the
            # `.js .mobile-nav` CSS clipping rule and nav-dropdown.js's
            # `panel.hidden` toggling only ever apply once client-side
            # script has run, never from the server.
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            if " hidden" in panel or 'hidden="' in panel:
                return False, "the no-JS floor requires the panel stay in the accessibility tree"
            if "display:" in panel:
                return False, "the no-JS floor requires the panel carry no inline display style"
            for route, _label in layout.NAV_TABS:
                if ('href="%s"' % route) not in panel:
                    return False, "missing dropdown href for %r with JavaScript disabled" % route
            html_tag_end = doc.index(">", doc.index("<html"))
            html_tag = doc[:html_tag_end]
            if 'class="js"' in html_tag or ' js"' in html_tag or ' js ' in html_tag:
                return False, "server-rendered <html> tag must never carry the .js marker class"
            return True, ""
        check(
            "with JavaScript disabled every nav link stays present in the dropdown panel's DOM "
            "(the collapsed look is a CSS max-height constraint, not a hidden attribute or "
            "display:none) and the server-rendered <html> tag carries no .js marker class",
            _dropdown_survives_with_javascript_disabled)

        def _nav_dropdown_js_progressive_enhancement_state_machine():
            # UXA-02/UXA-12's joint fix, client-side half. The .js marker
            # add must run before the dropdown-specific element lookup
            # (so pages without a dropdown still get the marker), and the
            # hidden-attribute/transitionend/reduced-motion state machine
            # must be present exactly as the plan specifies.
            js_path = os.path.join(
                os.path.dirname(__file__), "static", "nav-dropdown.js")
            with open(js_path) as fh:
                js = fh.read()
            marker_idx = js.index('className += " js"')
            toggle_idx = js.index('getElementById("site-nav-toggle")')
            if marker_idx >= toggle_idx:
                return False, ".js marker class must be added before the dropdown lookup"
            for needle in (
                "panel.hidden = true", "panel.hidden = false",
                "transitionend", "matchMedia", "prefers-reduced-motion",
            ):
                if needle not in js:
                    return False, "nav-dropdown.js is missing %r" % needle
            css_path = os.path.join(
                os.path.dirname(__file__), "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for needle in (".js .mobile-nav {", ".js .mobile-nav--open {"):
                if needle not in css:
                    return False, "style.css is missing %r" % needle
            return True, ""
        check(
            "nav-dropdown.js adds the .js marker class before its dropdown element lookup and "
            "implements the hidden-attribute/transitionend/reduced-motion state machine, matched "
            "by style.css's .js-scoped clipping rules",
            _nav_dropdown_js_progressive_enhancement_state_machine)

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

        def _unauth_redirects_to_login(method, path, data=None, next_route=None):
            # 06.6.2-07 (UXA-03): require_session() now carries an
            # allowlisted `next` query param for any requested path that
            # is one of layout.NAV_TABS's known routes (settings/health/
            # airlines/history, 06.6.4.1-07 renamed the first from config;
            # 06.6.4.1-08 removed preview — D-22 retires that page) —
            # regardless of HTTP method, since it only ever looks at
            # self.path. A path outside that set (poll-now, the retired
            # /preview redirect source, preview.png, a gallery image)
            # still redirects to the bare /login exactly as before this
            # plan.
            expected_location = (
                "/login?next=%s" % urllib.parse.quote(next_route, safe="")
                if next_route else "/login")

            def _run():
                status, headers, body = http_request(base + path, method=method, data=data)
                if status != 303:
                    return False, "expected 303, got %d" % status
                if headers.get("Location") != expected_location:
                    return False, "expected a redirect to %r, got %r" % (
                        expected_location, headers.get("Location"))
                if body:
                    return False, "expected an empty redirect body, got %d bytes of content" % len(body)
                return True, ""
            return _run

        for _tab_path in ("/settings", "/health", "/airlines", "/history"):
            check(
                "unauthenticated GET %s redirects to /login carrying that route as ?next=" % _tab_path,
                _unauth_redirects_to_login("GET", _tab_path, next_route=_tab_path))

        check(
            "unauthenticated GET /preview (the retired Preview page's redirect source) redirects "
            "to /login without page content (D-22 removed it from NAV_TABS, so no ?next= is carried "
            "— it lands on /login, not /history, proving the redirect branch keeps its own session gate)",
            _unauth_redirects_to_login("GET", "/preview"))

        check(
            "unauthenticated GET /preview.png redirects to /login without page content "
            "(not a NAV_TABS route, so no ?next= is carried)",
            _unauth_redirects_to_login("GET", "/preview.png"))

        check(
            "unauthenticated GET of a gallery image route redirects to /login without page content "
            "(not a NAV_TABS route, so no ?next= is carried)",
            _unauth_redirects_to_login("GET", "/gallery/whatever.png"))

        check(
            "unauthenticated POST /settings redirects to /login carrying /settings as ?next=",
            _unauth_redirects_to_login(
                "POST", "/settings",
                data=urllib.parse.urlencode({"ui_theme": "sky"}).encode(),
                next_route="/settings"))

        check(
            "unauthenticated POST /poll-now redirects to /login without page content "
            "(not a NAV_TABS route, so no ?next= is carried)",
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
            cache_control = headers.get("Cache-Control", "")
            directives = [part.strip() for part in cache_control.split(",")]
            if "public" not in directives:
                return False, (
                    "expected a shared-cacheable (public) Cache-Control scope, "
                    "got %r" % cache_control)
            if "max-age=300" not in directives:
                return False, (
                    "expected a 300-second max-age on the stylesheet's "
                    "Cache-Control header, got %r" % cache_control)
            return True, ""
        check(
            "GET /static/style.css succeeds without a session, returns a CSS "
            "content type, and stays shared-cacheable (public, max-age=300) — "
            "this route is a deliberate D-02 gate exemption with no per-user "
            "content",
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

        # --- nav-dropdown script: public, no session required (06.6.1-05, D-06) ---

        def _nav_dropdown_script_public():
            status, headers, body = http_request(base + "/static/nav-dropdown.js")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/javascript" not in content_type:
                return False, "expected a text/javascript content type, got %r" % content_type
            if b"site-nav-toggle" not in body:
                return False, "expected the toggle-id literal in the served body, proving the real file was served"
            return True, ""
        check(
            "GET /static/nav-dropdown.js succeeds without a session, returns a JavaScript content type, "
            "and serves the real file",
            _nav_dropdown_script_public)

        # --- 06.6.3: four more pre-auth static scripts, same shape as
        # _nav_dropdown_script_public() above ---

        def _static_script_public(route):
            def _run():
                status, headers, body = http_request(base + route)
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
            return _run

        for _script_route in (
                "/static/dirty-state.js", "/static/list-filter.js",
                "/static/copy-button.js", "/static/freshness.js"):
            check(
                "GET %s succeeds without a session and returns a shared-cacheable "
                "JavaScript content type" % _script_route,
                _static_script_public(_script_route))

        def _four_new_static_routes_dom_contract_guard():
            # Cross-file-equality half, mirroring
            # _three_file_nav_dom_contract_guard()'s own pattern: each new
            # companion.app.py *_SCRIPT_ROUTE constant must equal its
            # matching companion/layout.py *_SCRIPT_SRC constant, and
            # page_shell() must emit a <script src="..."> tag for each.
            import companion.app as app_module
            pairs = (
                (app_module.DIRTY_STATE_SCRIPT_ROUTE, layout.DIRTY_STATE_SCRIPT_SRC),
                (app_module.LIST_FILTER_SCRIPT_ROUTE, layout.LIST_FILTER_SCRIPT_SRC),
                (app_module.COPY_BUTTON_SCRIPT_ROUTE, layout.COPY_BUTTON_SCRIPT_SRC),
                (app_module.FRESHNESS_SCRIPT_ROUTE, layout.FRESHNESS_SCRIPT_SRC),
            )
            for route_const, src_const in pairs:
                if route_const != src_const:
                    return False, "script route drift: %r vs %r" % (route_const, src_const)
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            for _route_const, src_const in pairs:
                if ('<script src="%s" defer></script>' % src_const) not in doc:
                    return False, "expected a deferred <script> tag for %r" % src_const
            return True, ""
        check(
            "companion.app.py's 4 new *_SCRIPT_ROUTE constants equal companion/layout.py's 4 new "
            "*_SCRIPT_SRC constants, and page_shell() emits a <script> tag for each",
            _four_new_static_routes_dom_contract_guard)

        # --- 06.6.4.1-02 Task 3: panel-lookup.js (D-20) ---

        check(
            "GET /static/panel-lookup.js succeeds without a session and returns a shared-cacheable "
            "JavaScript content type",
            _static_script_public("/static/panel-lookup.js"))

        def _panel_lookup_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "panel-lookup.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
                "setTimeout", "setInterval", "innerHTML", "document.write",
                "eval(")
            for token in banned:
                if token in src:
                    return False, "panel-lookup.js must not contain %r" % token
            return True, ""
        check(
            "panel-lookup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "fetch/XHR/timers/innerHTML/document.write/eval)",
            _panel_lookup_script_es5_safe_and_no_html_write)

        def _panel_lookup_script_route_src_agree():
            import companion.app as app_module
            if layout.PANEL_LOOKUP_SCRIPT_SRC != app_module.PANEL_LOOKUP_SCRIPT_ROUTE:
                return False, "panel-lookup script route drift: %r vs %r" % (
                    layout.PANEL_LOOKUP_SCRIPT_SRC, app_module.PANEL_LOOKUP_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.PANEL_LOOKUP_SCRIPT_SRC equals companion.app.PANEL_LOOKUP_SCRIPT_ROUTE",
            _panel_lookup_script_route_src_agree)

        def _six_deferred_scripts_before_closing_body():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            body_close = doc.index("</body>")
            head = doc[:body_close]
            count = head.count('<script src=')
            if count != 6:
                return False, "expected exactly 6 deferred <script src= tags before </body>, got %d" % count
            if ('<script src="%s" defer></script>' % layout.PANEL_LOOKUP_SCRIPT_SRC) not in doc:
                return False, "expected a deferred <script> tag for PANEL_LOOKUP_SCRIPT_SRC"
            return True, ""
        check(
            "a rendered authenticated page contains exactly six deferred <script src= tags before "
            "the closing body tag, including panel-lookup.js",
            _six_deferred_scripts_before_closing_body)

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
            if headers.get("Location") != "/settings":
                return False, "expected a redirect to /settings, got %r" % headers.get("Location")
            set_cookie = headers.get("Set-Cookie", "")
            for needle in ("HttpOnly", "Secure", "SameSite=Strict"):
                if needle not in set_cookie:
                    return False, "missing %r in the session cookie header: %r" % (needle, set_cookie)
            return True, ""
        check(
            "a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict and redirects to /settings",
            _login_correct_password)

        # --- 06.6.2-07 (UXA-03): deep-link return, open-redirect rejection,
        # login_shell() markup, D-01 language-policy regression ---

        def _deep_link_return_round_trip():
            # An unauthenticated GET /health carries the requested route
            # as an allowlisted ?next= (T-06.6.2-12) ...
            status, headers, _ = http_request(base + "/health")
            if status != 303:
                return False, "expected 303 for GET /health, got %d" % status
            if headers.get("Location") != "/login?next=%2Fhealth":
                return False, "expected Location /login?next=%%2Fhealth, got %r" % headers.get("Location")
            # ... and a subsequent correct-password POST /login carrying
            # that same next value returns the user to /health, not /settings.
            status, headers, _ = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode(
                    {"password": TEST_PASSWORD, "next": "/health"}).encode())
            if status != 303:
                return False, "expected 303 on login POST, got %d" % status
            if headers.get("Location") != "/health":
                return False, "expected Location /health after login with next=/health, got %r" % headers.get("Location")
            return True, ""
        check(
            "an unauthenticated GET /health redirects with ?next=%2Fhealth, and logging in "
            "with that next value returns the user to /health, not /settings",
            _deep_link_return_round_trip)

        def _open_redirect_rejected(next_value):
            def _run():
                status, headers, _ = http_request(
                    base + "/login", method="POST",
                    data=urllib.parse.urlencode(
                        {"password": TEST_PASSWORD, "next": next_value}).encode())
                if status != 303:
                    return False, "expected 303 on login POST, got %d" % status
                location = headers.get("Location", "")
                if location != "/settings":
                    return False, "expected the safe /settings fallback, got %r" % location
                if "evil.example" in location:
                    return False, "the crafted next value leaked into the redirect Location"
                return True, ""
            return _run

        for _crafted_next in ("https://evil.example", "//evil.example"):
            check(
                "a login POST with the correct password and next=%r redirects to the "
                "/settings fallback, never to the crafted value (T-06.6.2-12)" % _crafted_next,
                _open_redirect_rejected(_crafted_next))

        def _login_get_with_unrecognised_next_carries_no_hidden_field():
            status, _headers, body = http_request(
                base + "/login?next=/nonexistent-route")
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'name="next"' in body:
                return False, (
                    "an unrecognised ?next= value must not render a hidden next "
                    "field — _validated_next_route() must be applied on the GET "
                    "path too, not only the POST path")
            return True, ""
        check(
            "GET /login?next=/nonexistent-route (not a real NAV_TABS member) renders "
            "the plain login form with no hidden next input",
            _login_get_with_unrecognised_next_carries_no_hidden_field)

        def _login_page_uses_dedicated_login_shell():
            status, _headers, body = http_request(base + "/login")
            if status != 200:
                return False, "expected 200, got %d" % status
            text = body.decode("utf-8", errors="replace")
            if '<html lang="en"' not in text:
                return False, "expected <html lang=\"en\" in the login page"
            if 'autocomplete="current-password"' not in text:
                return False, "expected autocomplete=\"current-password\" on the password field"
            for absent in ("sidebar-nav", "dashboard-shell", "site-nav-toggle"):
                if absent in text:
                    return False, (
                        "the login page must render layout.login_shell(), not "
                        "page_shell() — found %r in the response body" % absent)
            return True, ""
        check(
            "GET /login (no session) is rendered by the dedicated login_shell(), not "
            "page_shell() — no sidebar/mobile-nav markup, autocomplete present",
            _login_page_uses_dedicated_login_shell)

        def _both_shells_agree_on_document_language():
            # D-01/UXA-09: a single, cheap, permanent guard that
            # page_shell() and login_shell() can never diverge on
            # document language.
            page_doc = layout.page_shell(
                title="Config", active="config", body="<p>x</p>")
            login_doc = layout.login_shell("<p>x</p>")
            if 'lang="en"' not in page_doc:
                return False, "expected lang=\"en\" in page_shell()'s output"
            if 'lang="en"' not in login_doc:
                return False, "expected lang=\"en\" in login_shell()'s output"
            return True, ""
        check(
            "page_shell() and login_shell() both emit lang=\"en\" (D-01/UXA-09 "
            "language-policy regression guard)",
            _both_shells_agree_on_document_language)

        session_cookie = _login(harness)

        # --- authenticated: every NAV_TABS tab returns 200 with its own heading ---
        # 06.6.4.1-08 (D-22): "/preview" removed from this tuple here (not in
        # Task 2, which shrinks NAV_TABS itself) — the harness must stay
        # green immediately after this task's own commit, and /preview no
        # longer returns 200/a page heading the instant the redirect below
        # lands. See the dedicated redirect checks just below instead.

        for _tab_path, _heading in (
            ("/settings", "Settings"), ("/health", "Health"),
            ("/airlines", "Airlines"), ("/history", "History"),
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

        # --- 06.6.4.1-08 (D-22): the retired Preview page route now redirects
        # to History with a fixed literal target — never derived from a query
        # parameter, so a crafted next-style parameter provably cannot steer it ---

        def _preview_redirects_to_history():
            status, headers, body = http_request(base + "/preview", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            if headers.get("Location") != "/history":
                return False, "expected a redirect to /history exactly, got %r" % headers.get("Location")
            if body:
                return False, "expected an empty redirect body, got %d bytes of content" % len(body)
            return True, ""
        check(
            "authenticated GET /preview (the retired Preview page route) redirects to /history (D-22)",
            _preview_redirects_to_history)

        def _preview_redirect_ignores_query_string():
            status, headers, _body = http_request(
                base + "/preview?next=/settings&evil=https://evil.example",
                cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            if headers.get("Location") != "/history":
                return False, (
                    "expected the redirect location to stay /history regardless of an "
                    "arbitrary query string, got %r" % headers.get("Location"))
            return True, ""
        check(
            "authenticated GET /preview carrying an arbitrary query string (including a "
            "next=-shaped and an https://evil.example-shaped value) still redirects to the "
            "identical /history location — no request value influences the target",
            _preview_redirect_ignores_query_string)

        # Session gate on the retired route: covered by the "unauthenticated
        # GET /preview ... redirects to /login without page content" check
        # above (06.6.4.1-08 Task 2 removed /preview from NAV_TABS, so it no
        # longer carries a ?next=) — an unauthenticated caller lands on
        # /login, not /history, proving the redirect branch keeps its
        # require_session() gate. Both byte-serving image routes
        # (/preview.png, a real /gallery/{name}.png) already have their own
        # authenticated-200/unauthenticated-redirect checks elsewhere in
        # this file (_preview_real_panel/_preview_missing and the gallery
        # checks below, plus the unauthenticated-redirect loop above) — confirmed still
        # passing untouched by this task.

        # --- 06.6.4.1-07 (D-26): settings route rename — old path 404s
        # by design (no redirect), the merged form's POST target is
        # live, the ?next= round trip works for the new slug, and the
        # route/icon-map cross-module contract holds ---

        def _old_settings_path_404s_authenticated():
            status, _headers, body = http_request(
                base + "/config", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for the retired /config path, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "authenticated GET /config (the retired settings path) returns 404 — D-26 "
            "declines a redirect since this is a fresh URL at inception, not a deprecated bookmark",
            _old_settings_path_404s_authenticated)

        def _settings_post_redirects_to_settings_with_flash():
            status, headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie, data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if not location.startswith("/settings?flash="):
                return False, "expected a redirect to /settings?flash=..., got %r" % location
            return True, ""
        check(
            "an authenticated POST /settings redirects to /settings carrying a flash query",
            _settings_post_redirects_to_settings_with_flash)

        def _login_get_with_settings_next_carries_hidden_field():
            status, _headers, body = http_request(base + "/login?next=/settings")
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'name="next" value="/settings"' not in body:
                return False, (
                    "expected the recognised /settings ?next= value to survive the "
                    "round trip as a rendered hidden field")
            return True, ""
        check(
            "GET /login?next=/settings (a real NAV_TABS member) renders a hidden next "
            "field carrying /settings, surviving the round trip",
            _login_get_with_settings_next_carries_hidden_field)

        def _settings_route_and_icon_map_cross_module_contract():
            import companion.app as app_module
            from companion.pages import config_page
            if not (app_module.SETTINGS_ROUTE == config_page.SETTINGS_ROUTE
                    == layout.NAV_TABS[0][0]):
                return False, (
                    "expected app.SETTINGS_ROUTE == config_page.SETTINGS_ROUTE == "
                    "layout.NAV_TABS[0][0], got %r / %r / %r"
                    % (app_module.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE,
                       layout.NAV_TABS[0][0]))
            nav_slugs = {route.lstrip("/") for route, _ in layout.NAV_TABS}
            if set(layout.NAV_ICON_IDS) != nav_slugs:
                return False, (
                    "expected NAV_ICON_IDS' keys to equal the set of nav route "
                    "slugs, got %r vs %r" % (set(layout.NAV_ICON_IDS), nav_slugs))
            return True, ""
        check(
            "app.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE, and layout.NAV_TABS[0][0] all "
            "agree, and NAV_ICON_IDS' keys equal the nav route slugs one-to-one",
            _settings_route_and_icon_map_cross_module_contract)

        def _nav_page_titles_icon_route_standing_contract_guard():
            # 06.6.4.1-07 Task 3: a standing guard mirroring this file's
            # existing three-file DOM-contract guards
            # (_three_file_nav_dom_contract_guard(),
            # _four_new_static_routes_dom_contract_guard() above) — makes
            # the next nav-route change (plan 08) fail loudly here
            # instead of silently, if any of these four route
            # collections is missed: the nav tuple itself, the
            # page-titles dict, the slug-to-icon map, and the settings
            # page module's own route constant.
            import companion.app as app_module
            nav_routes = [route for route, _ in layout.NAV_TABS]
            nav_slugs = {route.lstrip("/") for route in nav_routes}
            page_title_keys = set(app_module._PAGE_TITLES)
            if page_title_keys != set(nav_routes):
                return False, (
                    "expected _PAGE_TITLES' keys to equal the set of NAV_TABS "
                    "routes, got %r vs %r" % (page_title_keys, set(nav_routes)))
            if len(app_module._PAGE_TITLES) != len(layout.NAV_TABS):
                return False, (
                    "expected _PAGE_TITLES and NAV_TABS to have the same "
                    "length, got %d vs %d"
                    % (len(app_module._PAGE_TITLES), len(layout.NAV_TABS)))
            icon_slugs = set(layout.NAV_ICON_IDS)
            if icon_slugs != nav_slugs:
                return False, (
                    "expected NAV_ICON_IDS' keys to equal the set of NAV_TABS "
                    "slugs one-to-one, got %r vs %r" % (icon_slugs, nav_slugs))
            if app_module.SETTINGS_ROUTE != layout.NAV_TABS[0][0]:
                return False, (
                    "expected app.SETTINGS_ROUTE to equal NAV_TABS' first "
                    "route, got %r vs %r"
                    % (app_module.SETTINGS_ROUTE, layout.NAV_TABS[0][0]))
            return True, ""
        check(
            "the nav tuple, the page-titles dict, and the slug-to-icon map all agree in size "
            "and key set, and the settings page module's own route constant is the nav "
            "tuple's first route — a standing guard against silent drift when the route "
            "set changes again",
            _nav_page_titles_icon_route_standing_contract_guard)

        # --- logout clears the cookie; a subsequent tab request is refused again ---

        def _logout_clears_cookie():
            # D-11: /logout moved from GET to POST, so a stray prefetch,
            # crawler, or <img src="/logout">-shaped link can no longer
            # end a session — see the sibling GET check just below.
            status, headers, _ = http_request(
                base + "/logout", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect on logout, got %d" % status
            set_cookie = headers.get("Set-Cookie", "")
            if "Max-Age=0" not in set_cookie:
                return False, "expected the logout cookie header to carry Max-Age=0, got %r" % set_cookie
            return True, ""
        check("POST /logout clears the session cookie (Max-Age=0)", _logout_clears_cookie)

        def _get_logout_no_longer_ends_session():
            status, _headers, _body = http_request(base + "/logout", cookie=session_cookie)
            if status != 404:
                return False, "expected GET /logout to 404 (D-11), got %d" % status
            return True, ""
        check(
            "GET /logout no longer accepts the request (404) — D-11 closes the GET-triggered logout hole",
            _get_logout_no_longer_ends_session)

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
            status, headers, _ = http_request(base + "/settings")
            # 06.6.2-07 (UXA-03): /settings is a NAV_TABS route (renamed
            # from /config, 06.6.4.1-07), so require_session() now carries
            # it as ?next= too — the same allowlisted-return behavior
            # every other unauthenticated NAV_TABS request gets.
            if status != 303 or headers.get("Location") != "/login?next=%2Fsettings":
                return False, "expected a redirect to /login?next=%%2Fsettings for a post-logout request, got %d/%r" % (
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

        def _gallery_response_is_never_shared_cacheable():
            gallery_filename = "260829-0rl-cache-control-fixture.png"
            gallery_path = os.path.join(
                harness.state_path("gallery"), gallery_filename)
            with open(gallery_path, "wb") as fh:
                fh.write(PNG_SIGNATURE + b"not-a-real-panel-just-a-fixture")
            status, headers, _body = http_request(
                base + "/gallery/" + gallery_filename, cookie=session_cookie)
            if status != 200:
                return False, (
                    "expected 200 for a gallery fixture written to %r, got %d "
                    "(a 404 here means the fixture landed in the wrong "
                    "directory, not that the caching header is wrong)"
                    % (gallery_path, status))
            cache_control = headers.get("Cache-Control", "")
            directives = [part.strip() for part in cache_control.split(",")]
            if "public" in directives:
                return False, (
                    "an authenticated gallery image must never be advertised "
                    "as storable by a shared cache — got Cache-Control: %r"
                    % cache_control)
            if "private" not in directives:
                return False, (
                    "expected the non-shared (private) Cache-Control scope on "
                    "an authenticated gallery response, got %r" % cache_control)
            if "max-age=3600" not in directives:
                return False, (
                    "expected a 3600-second max-age on the gallery response, "
                    "got %r" % cache_control)
            return True, ""
        check(
            "an authenticated gallery image is never advertised as storable "
            "by a shared/intermediary cache (WR-02)",
            _gallery_response_is_never_shared_cacheable)

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

        # --- illustration image route (D-15, 06.6.4.1-02) ---

        def _illustration_real_key_returns_png():
            status, headers, body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for a real illustration key, got %d" % status
            if headers.get("Content-Type") != "image/png":
                return False, "expected Content-Type image/png, got %r" % headers.get("Content-Type")
            if not body:
                return False, "expected a non-empty response body"
            return True, ""
        check(
            "an authenticated GET /illustration/air-france.png returns 200, image/png, and a non-empty body",
            _illustration_real_key_returns_png)

        def _illustration_unknown_key_404():
            status, _headers, _body = http_request(
                base + "/illustration/not-a-real-airline.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for a key not in the membership set, got %d" % status
            return True, ""
        check(
            "an authenticated GET for an illustration key not in the membership set returns 404",
            _illustration_unknown_key_404)

        def _illustration_traversal_key_404():
            adversarial_paths = [
                "/illustration/..%2F..%2Fetc%2Fpasswd.png",
                "/illustration/../../../etc/passwd.png",
                "/illustration/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, body = http_request(
                    base + adversarial_path, cookie=session_cookie)
                if status != 404:
                    return False, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)
                if body and b"root:" in body:
                    return False, "adversarial path %r returned file content" % (adversarial_path,)
            return True, ""
        check(
            "authenticated GET requests for adversarial illustration paths (path traversal) all return 404 with no file content",
            _illustration_traversal_key_404)

        def _illustration_unauthenticated_redirects_to_login():
            status, headers, body = http_request(base + "/illustration/air-france.png")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            if body.startswith(PNG_SIGNATURE):
                return False, "unauthenticated request must never return image bytes"
            return True, ""
        check(
            "an unauthenticated GET /illustration/air-france.png redirects to /login, never returns image bytes",
            _illustration_unauthenticated_redirects_to_login)

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

        # UXA-15: two genuinely overlapping threads issuing POST
        # /poll-now against the same running subprocess, on a session
        # with zero cooldown, must never both reach run_once() — the
        # server-side _POLL_LOCK (companion/app.py) is the correctness
        # boundary, not merely a claim verified by reading the source.
        # A fresh Harness/session is used (rather than reusing the
        # cooldown-exhausted session_cookie above) so the cooldown gate
        # never confounds which flash key each response carries.
        def _poll_now_concurrent_requests_serialize_on_the_lock():
            concurrent_harness = Harness()
            try:
                concurrent_harness.start()
                cbase = concurrent_harness.base_url()
                concurrent_cookie = _login(concurrent_harness)

                start_event = threading.Event()
                responses = []
                responses_lock = threading.Lock()

                def _worker():
                    start_event.wait()
                    status, headers, _ = http_request(
                        cbase + "/poll-now", method="POST", cookie=concurrent_cookie)
                    with responses_lock:
                        responses.append((status, headers.get("Location", "")))

                threads = [threading.Thread(target=_worker) for _ in range(2)]
                for t in threads:
                    t.start()
                # Released together, after both threads are already
                # blocked on it — the tightest overlap this harness can
                # produce without instrumenting the server itself.
                start_event.set()
                for t in threads:
                    t.join(timeout=30)

                if len(responses) != 2:
                    return False, "expected two responses, got %d: %r" % (len(responses), responses)
                for status, _location in responses:
                    if status != 303:
                        return False, "expected both responses to be 303 redirects, got %r" % (responses,)
                already_running_count = sum(
                    1 for _status, location in responses
                    if "flash=poll_already_running" in location)
                if already_running_count != 1:
                    return False, (
                        "expected exactly one of the two overlapping /poll-now "
                        "requests to receive the poll_already_running flash key "
                        "(the other must complete/fail on its own honest "
                        "outcome), got %d of 2: %r" % (already_running_count, responses))
                return True, ""
            finally:
                concurrent_harness.stop()
                concurrent_harness.cleanup()
        check(
            "two genuinely overlapping POST /poll-now requests: exactly one gets the poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution",
            _poll_now_concurrent_requests_serialize_on_the_lock)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("companion-app: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
