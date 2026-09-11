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
an HMAC-SHA256 of the decimal expiry timestamp (nanosecond-resolution,
see `issue_session_token()`), keyed by a signing key
*derived* from the shared password (see `_signing_key()` below, A-33/
D-16) — never the raw password itself, so a leaked `(expiry,
signature)` pair is not an offline password oracle. The one deliberate
departure from a purely stateless design is the small in-memory
revocation set below (`revoke()`/`is_revoked()`), consulted on Sign
out: it is pruned by each entry's own embedded expiry on every access,
so it cannot grow unbounded over the 12h `SESSION_TTL_S` window, and it
is lost on restart exactly like everything else in this module — that
is acceptable for one household (19-CONTEXT.md D-16), not a general
session store.
"""
import hashlib
import hmac
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie

PASSWORD_ENV_VAR = "SKYPANE_COMPANION_PASSWORD"
SESSION_TTL_S = 12 * 3600
SESSION_COOKIE_NAME = "sp_session"
UI_THEME_COOKIE_NAME = "sp_ui_theme"
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_S = 300

# A-33/D-16: a per-process random salt, generated once at import time,
# that never leaves this process (never embedded in a cookie, never
# logged). issue_session_token()/verify_session_token() mix it into the
# signing key via _signing_key() below so that a leaked (expiry,
# signature) pair cannot be used to brute-force the shared password
# offline — the attacker would also need this salt, which they cannot
# get. A side effect, explicitly accepted for one household: a process
# restart regenerates the salt and therefore invalidates every
# outstanding session.
_PROCESS_SALT = secrets.token_bytes(32)


def _signing_key():
    """The HMAC signing key for session tokens: HMAC-as-KDF over the
    shared password and this process's random salt. This is a
    standard, well-understood construction, not a hand-rolled one
    (19-RESEARCH.md's own Don't Hand-Roll guidance) — deriving rather
    than reusing configured_password() directly is what makes a leaked
    token's signature useless for guessing the password offline.
    """
    return hmac.new(
        configured_password(), _PROCESS_SALT, hashlib.sha256).digest()


# A-33/D-16: the Sign out revocation set. Maps a presented token string
# to its own embedded expiry (an int), so pruning never needs to touch
# auth.py's other stateless machinery. Guarded by _REVOKED_LOCK,
# mirroring companion/app.py's own _POLL_LOCK precedent for a lock
# around small shared mutable state under ThreadingHTTPServer.
_REVOKED = {}
_REVOKED_LOCK = threading.Lock()


def _prune_revoked_locked():
    """Drop every revoked entry whose embedded expiry has already
    passed. Caller must hold _REVOKED_LOCK."""
    now = time.time_ns()
    expired = [token for token, expiry in _REVOKED.items() if expiry <= now]
    for token in expired:
        del _REVOKED[token]


def revoke(token):
    """Add `token` to the revocation set, pruning expired entries on
    the way in so the set stays bounded. A malformed or already-expired
    token is ignored (not stored, never raises) — there is nothing
    useful to revoke once a token can no longer verify anyway.

    `token`'s embedded expiry is a nanosecond timestamp, matching
    issue_session_token()'s field (see that function's docstring).
    """
    if not isinstance(token, str) or "." not in token:
        return
    expiry_str, _signature = token.split(".", 1)
    try:
        expiry = int(expiry_str)
    except ValueError:
        return
    with _REVOKED_LOCK:
        _prune_revoked_locked()
        if expiry > time.time_ns():
            _REVOKED[token] = expiry


def is_revoked(token):
    """True if `token` is in the revocation set. Prunes expired entries
    first, so a revoked-but-since-expired token correctly stops
    counting against the set's bound. Returns False for a non-string or
    empty token rather than raising.
    """
    if not isinstance(token, str) or not token:
        return False
    with _REVOKED_LOCK:
        _prune_revoked_locked()
        return token in _REVOKED


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
    """Build and sign a fresh session token: "<expiry>.<hex signature>".

    `expiry` is a nanosecond-resolution Unix timestamp (`time.time_ns()`),
    not seconds. This is a deviation from the original second-resolution
    field, made while adding the revocation set (A-33/D-16): tokens are
    otherwise a pure function of (expiry, signing key), so two logins
    landing in the same wall-clock SECOND used to produce byte-identical
    tokens — meaning revoking one session's token on Sign out could
    silently also revoke a different, still-legitimate session that
    happened to be issued in that same second. Nanosecond resolution
    makes that collision practically impossible while leaving the
    "<int>.<hex>" two-field shape, and every existing caller/round-trip
    check, unchanged.
    """
    expiry = str(time.time_ns() + SESSION_TTL_S * 1_000_000_000)
    signature = hmac.new(
        _signing_key(), expiry.encode(), hashlib.sha256).hexdigest()
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
        secret = _signing_key()
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
    return expiry > time.time_ns()


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

    Per-IP throttling was considered (19-CONTEXT.md Deferred Ideas) and
    deliberately deferred — the global counter stays, because there is
    one shared password and no notion of distinct clients worth
    tracking separately.
    """

    def __init__(self, limit=LOGIN_FAILURE_LIMIT, lockout_s=LOGIN_LOCKOUT_S):
        self._limit = limit
        self._lockout_s = lockout_s
        self._failures = 0
        self._locked_until = 0.0

    def record_failure(self):
        # A-32/D-15: once the previous lockout window has fully elapsed,
        # a new failure must start a fresh count rather than re-arming
        # the lockout from an already-saturated counter — otherwise one
        # stray wrong password per window keeps the lockout permanent.
        # Contract: five fresh failures per window, never permanent.
        if self._failures >= self._limit and time.time() >= self._locked_until:
            self._failures = 0
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
