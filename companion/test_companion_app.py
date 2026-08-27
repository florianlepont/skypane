#!/usr/bin/env python3
"""Contract harness for the SkyPane companion service's auth and layout
building blocks (companion/auth.py, companion/layout.py).

Covers: constant-time password checking, fail-closed behaviour when no
password is configured, stateless signed session tokens (issue/verify
round trip, six distinct malformed-token rejections, forged-secret and
hand-built-expired coverage), session/logout cookie security flags,
cookie parsing, the process-global login-attempt throttle, the single
canonical HTML-escaping helper, the page shell's document shape and
active-nav/theme rendering, the status-dot/data-table component
builders, and that AuthNotConfigured never leaks the configured
password value.

Checks are grouped under two clearly-commented sections mirroring the
two modules this plan builds (companion/auth.py, companion/layout.py).
A third section — subprocess-driven route checks against
companion/app.py — arrives with plan 06-05, which extends this same
file rather than replacing it; do not restructure main() to merge that
section into these two when it lands.

Stdlib-only (hashlib, hmac, os, sys, time). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_companion_app.py
"""
import hashlib
import hmac
import html
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth, layout  # noqa: E402

TEST_PASSWORD = "companion-test-password-please-ignore"
EXPECTED_CHECK_COUNT = 20


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
            for route, _ in layout.NAV_TABS:
                slug = route.lstrip("/")
                href_needle = 'href="%s"' % route
                href_index = rendered.find(href_needle)
                if href_index == -1:
                    return False, "missing nav link for %r" % route
                tag_start = rendered.rfind("<a", 0, href_index)
                tag_end = rendered.find(">", href_index)
                tag = rendered[tag_start:tag_end]
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

        def _page_shell_escapes_hostile_body():
            escaped_hostile_body = layout.escape_html("<script>alert(1)</script>")
            rendered = layout.page_shell(title="Health", active="health", body=escaped_hostile_body)
            if "<script>" in rendered:
                return False, "an unescaped <script> tag reached the rendered page"
            return True, ""
        check(
            "page_shell()'s output contains no unescaped script tag for an escaped hostile body",
            _page_shell_escapes_hostile_body)

    finally:
        if previous_password is not None:
            os.environ[auth.PASSWORD_ENV_VAR] = previous_password
        else:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("companion-app: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
