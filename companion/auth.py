"""companion/auth.py — the shared-password session gate for the SkyPane
companion service (D-01/D-02, 06-CONTEXT.md).

There are no per-user accounts: a single shared password protects the
entire site uniformly (D-02). This module is stdlib-only (hashlib, hmac,
http.cookies, os, time, secrets) — it must never import Pillow, sqlite3,
or anything under server/, matching this project's stdlib-first
discipline (06-RESEARCH.md).

Constants:

- PASSWORD_ENV_VAR ("SKYPANE_COMPANION_PASSWORD"): the environment
  variable holding the shared password. Plan 06-11 adds the matching
  entry to deploy/skypane.env.example and the matching
  EnvironmentFile= reference in the new systemd unit (D-01). Per D-01's
  secrets discipline, the value is read from the process environment
  only: this module never writes it to a file, never emits it via
  print/logging, and never lets it reach an exception message.

- SESSION_TTL_S (12h): long enough that a single operator is not
  re-prompted for a password during a normal working session, short
  enough that a leaked cookie does not stay valid indefinitely
  (06-RESEARCH.md Open Question 3). This is a tunable, not an
  architectural commitment.

- SESSION_COOKIE_NAME / UI_THEME_COOKIE_NAME: the two cookies this
  service sets — the signed session token, and the CFG-09 UI theme
  preference (read by companion/layout.py, never written by it).

- LOGIN_FAILURE_LIMIT / LOGIN_LOCKOUT_S: LoginThrottle's failed-attempt
  guard thresholds (see LoginThrottle below).

Session tokens are stateless: `expiry.signature`, where `signature` is
an HMAC-SHA256 of the decimal expiry timestamp, keyed by the shared
password. There is no server-side session store to leak, to grow
unbounded, or to lose on restart — appropriate for one shared secret
with no per-user revocation requirement.
"""
import hashlib
import hmac
import os
import time
from http.cookies import SimpleCookie

PASSWORD_ENV_VAR = "SKYPANE_COMPANION_PASSWORD"
SESSION_TTL_S = 12 * 3600
SESSION_COOKIE_NAME = "sp_session"
UI_THEME_COOKIE_NAME = "sp_ui_theme"
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_S = 300


class AuthNotConfigured(RuntimeError):
    """Raised when PASSWORD_ENV_VAR is unset or empty.

    A missing password must fail closed, never open — companion/app.py
    (plan 06-05) turns this into a startup refusal, so the service can
    never come up with authentication silently disabled. The message
    names only the environment variable, never a value, and must never
    be re-worded to interpolate the configured password.
    """


def configured_password():
    """Return the shared password as bytes, or raise AuthNotConfigured.

    Never include the environment value in the raised exception.
    """
    value = os.environ.get(PASSWORD_ENV_VAR)
    if not value:
        raise AuthNotConfigured(
            "%s is not set in the process environment — refusing to "
            "authenticate rather than running with auth silently "
            "disabled." % PASSWORD_ENV_VAR)
    return value.encode()


def password_ok(submitted):
    """Constant-time check of `submitted` against the configured password.

    Never uses `==` — a plain string-equality comparison on a secret
    leaks timing information proportional to the matching prefix length
    (06-RESEARCH.md Pitfall 4). A non-string submission is coerced to an
    empty string rather than raising, so a malformed login POST body
    degrades to "wrong password" instead of a 500.
    """
    if not isinstance(submitted, str):
        submitted = ""
    return hmac.compare_digest(submitted.encode(), configured_password())


def issue_session_token():
    """Build and sign a fresh session token: "<expiry>.<hex signature>"."""
    expiry = str(int(time.time()) + SESSION_TTL_S)
    signature = hmac.new(
        configured_password(), expiry.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (expiry, signature)


def verify_session_token(value):
    """Return True only for a token this server issued and that has not
    expired. Never raises — every malformed shape (non-string, missing
    separator, wrong signature, non-integer expiry) returns False, and
    the caller is never told which check failed.

    The signature is verified *before* the expiry field is parsed, so a
    forged or truncated token cannot influence control flow through its
    own payload.
    """
    if not isinstance(value, str) or "." not in value:
        return False
    expiry_str, signature = value.split(".", 1)
    try:
        secret = configured_password()
    except AuthNotConfigured:
        return False
    expected_signature = hmac.new(
        secret, expiry_str.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return False
    try:
        expiry = int(expiry_str)
    except ValueError:
        return False
    return expiry > time.time()


def session_set_cookie_header(token):
    """Return the Set-Cookie header *value* for a fresh session.

    HttpOnly keeps the token out of reach of any injected script;
    SameSite=Strict is the CSRF control for the state-changing
    endpoints (there is exactly one origin and no legitimate cross-site
    use); Secure is unconditional because Caddy always terminates TLS
    in front of this service (06-RESEARCH.md Pitfall 3).
    """
    return (
        "%s=%s; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=%d"
        % (SESSION_COOKIE_NAME, token, SESSION_TTL_S))


def logout_set_cookie_header():
    """Return a Set-Cookie header value that expires the session cookie
    immediately (empty value, Max-Age=0), carrying the same security
    flags as the cookie it replaces.
    """
    return (
        "%s=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0"
        % (SESSION_COOKIE_NAME,))


def parse_cookies(header_value):
    """Parse a raw Cookie header into a plain {name: value} dict.

    A missing or malformed header yields an empty dict rather than
    raising — this must never be a code path an attacker can use to
    trigger a 500 by sending a garbled Cookie header.
    """
    if not header_value:
        return {}
    jar = SimpleCookie()
    try:
        jar.load(header_value)
    except Exception:
        return {}
    return {name: morsel.value for name, morsel in jar.items()}


class LoginThrottle:
    """A process-global (not per-session) failed-login guard.

    D-01/D-02 mean there are no distinct users on this site, so a
    per-session counter would be trivially defeated by opening a second
    tab — the same reasoning 06-RESEARCH.md's Pitfall 8 applies to the
    CFG-07 poll-trigger cooldown applies here to login attempts. This is
    a courtesy guard for a single-user personal tool, not a defence
    against a distributed attacker; the real strength of this site's
    auth is the length of the operator-generated shared secret.
    """

    def __init__(self, limit=LOGIN_FAILURE_LIMIT, lockout_s=LOGIN_LOCKOUT_S):
        self._limit = limit
        self._lockout_s = lockout_s
        self._failures = 0
        self._locked_until = 0.0

    def record_failure(self):
        self._failures += 1
        if self._failures >= self._limit:
            self._locked_until = time.time() + self._lockout_s

    def record_success(self):
        self._failures = 0
        self._locked_until = 0.0

    def locked_out(self):
        return time.time() < self._locked_until

    def seconds_remaining(self):
        remaining = self._locked_until - time.time()
        return int(remaining) if remaining > 0 else 0
