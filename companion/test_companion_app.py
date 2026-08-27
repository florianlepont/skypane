#!/usr/bin/env python3
"""Contract harness for the SkyPane companion service's auth and layout
building blocks (companion/auth.py, companion/layout.py).

Covers: constant-time password checking, fail-closed behaviour when no
password is configured, stateless signed session tokens (issue/verify
round trip, five distinct malformed-token rejections, a flipped-
signature rejection), session/logout cookie security flags, cookie
parsing, and the process-global login-attempt throttle.

Checks are grouped under clearly-commented sections mirroring the
modules this plan builds (companion/auth.py, companion/layout.py). A
route-driven section (subprocess checks against companion/app.py)
arrives with plan 06-05, which extends this same file rather than
replacing it; do not restructure main() to merge that section into
these when it lands.

Stdlib-only (hashlib, hmac, os, sys, time). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_companion_app.py
"""
import hashlib
import hmac
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth  # noqa: E402

TEST_PASSWORD = "companion-test-password-please-ignore"
EXPECTED_CHECK_COUNT = 9


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
