"""The shared-password session gate for the SkyPane companion service.

No per-user accounts. Stdlib-only — must never import Pillow, sqlite3,
or anything under server/.

Session tokens are stateless: `expiry.signature`, HMAC-SHA256 keyed by
a signing key *derived* from the password (`_signing_key()`), never the
raw password — a leaked pair is not an offline password oracle. The
in-memory revocation set below is the one stateful exception: pruned by
expiry, lost on restart.
"""
import collections
import hashlib
import hmac
import ipaddress
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

PASSWORD_ENV_VAR = "SKYPANE_COMPANION_PASSWORD"
SESSION_TTL_S = 12 * 3600
SESSION_COOKIE_NAME = "sp_session"
UI_THEME_COOKIE_NAME = "sp_ui_theme"
# Shares secure_cookie_flag() with UI_THEME_COOKIE_NAME, so the Secure
# flag can never drift between them.
UI_LANG_COOKIE_NAME = "sp_ui_lang"
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_S = 300
INSECURE_COOKIES_ENV_VAR = "SKYPANE_COMPANION_INSECURE_COOKIES"

# Never leaves this process. Mixed into the signing key so a leaked
# (expiry, signature) pair cannot brute-force the password offline. A
# process restart regenerates it, invalidating every outstanding session.
_PROCESS_SALT = secrets.token_bytes(32)


def _signing_key():
    """HMAC-as-KDF over the shared password and the process salt —
    deriving rather than reusing the password directly makes a leaked
    signature useless for guessing it offline.
    """
    return hmac.new(
        configured_password(), _PROCESS_SALT, hashlib.sha256).digest()


# The Sign out revocation set. Maps a presented token string to its own
# embedded expiry (an int), so pruning never needs to touch auth.py's
# other stateless machinery. Guarded by _REVOKED_LOCK, mirroring
# companion/app.py's own _POLL_LOCK precedent for a lock around small
# shared mutable state under ThreadingHTTPServer.
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
    """Raised when PASSWORD_ENV_VAR is unset or empty — fails closed
    rather than starting with auth silently disabled. The message names
    only the environment variable, never a value.
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
    """Constant-time check of `submitted` against the configured
    password. Never uses `==` — a plain comparison leaks timing
    information proportional to the matching prefix length. A
    non-string submission degrades to "wrong password", never a 500.
    """
    if not isinstance(submitted, str):
        submitted = ""
    return hmac.compare_digest(submitted.encode(), configured_password())


def issue_session_token():
    """Build and sign a fresh session token: "<expiry>.<hex signature>".
    `expiry` is nanosecond-resolution: at second resolution, two logins
    in the same second would share a token, so revoking one on Sign out
    would silently revoke the other too.
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


def secure_cookie_flag():
    """The `"; Secure"` cookie-attribute fragment, or `""`. On by
    default (Caddy terminates TLS in production); the opt-out exists
    only so a plain-http LAN/dev run isn't unwinnably bounced back to
    /login. Read fresh every call; fails closed on anything but "1".
    """
    if os.environ.get(INSECURE_COOKIES_ENV_VAR) == "1":
        return ""
    return "; Secure"


def session_set_cookie_header(token):
    """Return the Set-Cookie header *value* for a fresh session.

    HttpOnly keeps the token out of reach of any injected script;
    SameSite=Strict is the CSRF control for the state-changing
    endpoints (there is exactly one origin and no legitimate cross-site
    use); Secure is on by default, off only via the explicit dev-only
    SKYPANE_COMPANION_INSECURE_COOKIES=1 opt-out (see
    secure_cookie_flag()).
    """
    return (
        "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
        % (SESSION_COOKIE_NAME, token, secure_cookie_flag(), SESSION_TTL_S))


def logout_set_cookie_header():
    """Return a Set-Cookie header value that expires the session cookie
    immediately (empty value, Max-Age=0), carrying the same security
    flags as the cookie it replaces.
    """
    return (
        "%s=; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=0"
        % (SESSION_COOKIE_NAME, secure_cookie_flag()))


def parse_cookies(header_value):
    """Parse a raw Cookie header into a plain {name: value} dict. A
    missing or malformed header yields an empty dict rather than
    raising, never a 500 an attacker could trigger.
    """
    if not header_value:
        return {}
    jar = SimpleCookie()
    try:
        jar.load(header_value)
    except Exception:
        return {}
    return {name: morsel.value for name, morsel in jar.items()}


def client_ip(peer, xff):
    """The address that identifies a caller for login-throttle purposes.
    `X-Forwarded-For` is trusted only when the TCP peer is loopback
    (Caddy, the only reverse proxy here, overwrites rather than appends
    to XFF); any other peer sets its own header, so is never trusted.
    Falls back to the peer string on any unparsable value.
    """
    try:
        parsed_peer = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    mapped = getattr(parsed_peer, "ipv4_mapped", None)
    peer_is_loopback = parsed_peer.is_loopback or (
        mapped is not None and mapped.is_loopback)
    if peer_is_loopback and xff:
        candidate = xff.split(",")[-1].strip()
        if candidate:
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return str(parsed_peer)


def login_throttle_key(peer, xff):
    """The LoginThrottle bucket key for a request: client_ip(), with an
    IPv6 result collapsed to its /64 network so a single host cannot buy
    itself unlimited fresh buckets out of its own /64 allocation.
    """
    ip = client_ip(peer, xff)
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if parsed.version == 6:
        return str(ipaddress.ip_network(ip + "/64", strict=False))
    return ip


class LoginThrottle:
    """A failed-login guard keyed on the caller's address, not a single
    shared counter — one stranger's wrong guesses must not lock out the
    site's real owner. A courtesy guard for a single-user tool, not a
    defence against a distributed attacker; the real strength is the
    shared secret's length.

    The bucket table is bounded by `max_entries`: on an insert that
    would exceed the cap, unlocked-and-idle entries are dropped first,
    then least-recently-touched entries regardless of lock state. A
    spraying attacker can evict and reset their own bucket, never
    anyone else's.
    """

    def __init__(self, limit=LOGIN_FAILURE_LIMIT, lockout_s=LOGIN_LOCKOUT_S,
                 max_entries=4096, clock=time.time):
        self._limit = limit
        self._lockout_s = lockout_s
        self._max_entries = max_entries
        self._clock = clock
        self._entries = collections.OrderedDict()
        # Shared across every request thread under ThreadingHTTPServer;
        # mirrors _REVOKED_LOCK's precedent above.
        self._lock = threading.Lock()

    def _evict_locked(self):
        # Must be called with self._lock already held.
        if len(self._entries) < self._max_entries:
            return
        now = self._clock()
        for key in list(self._entries.keys()):
            if len(self._entries) < self._max_entries:
                break
            failures, locked_until, last_seen = self._entries[key]
            unlocked = now >= locked_until
            stale = (now - last_seen) > self._lockout_s
            if unlocked and stale:
                del self._entries[key]
        while len(self._entries) >= self._max_entries:
            self._entries.popitem(last=False)

    def _touch_locked(self, key):
        # Must be called with self._lock held. Returns the mutable
        # [failures, locked_until, last_seen] entry, creating it if needed.
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]
        self._evict_locked()
        entry = [0, 0.0, self._clock()]
        self._entries[key] = entry
        return entry

    def record_failure(self, key):
        # Once the lockout window has fully elapsed, a failure starts a
        # fresh count rather than re-arming from a saturated counter —
        # otherwise one stray guess per window keeps the lockout permanent.
        with self._lock:
            entry = self._touch_locked(key)
            now = self._clock()
            failures = entry[0]
            if failures >= self._limit and now >= entry[1]:
                failures = 0
            failures += 1
            entry[0] = failures
            if failures >= self._limit:
                entry[1] = now + self._lockout_s
            entry[2] = now

    def record_success(self, key):
        with self._lock:
            entry = self._touch_locked(key)
            entry[0] = 0
            entry[1] = 0.0
            entry[2] = self._clock()

    def locked_out(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            return self._clock() < entry[1]

    def seconds_remaining(self, key):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 0
            remaining = entry[1] - self._clock()
        return int(remaining) if remaining > 0 else 0


# Defence in depth on SameSite=Strict: catches pre-SameSite browsers
# and same-site sibling hosts SameSite=Strict can't distinguish.
# Header-less requests are allowed (no security gain blocking them).
# Origin vs Host, not a hardcoded name: both are set independently by
# a well-behaved client and unspoofable by an attacker page.
_ORIGIN_DEFAULT_PORT = {"https": "443", "http": "80"}


def post_origin_ok(headers):
    """True when `headers` describes a POST this service should
    accept; False when it looks cross-site (403 before any routing or
    form read).

    1. `Sec-Fetch-Site: cross-site`/`same-site` -> reject (checked
       first: the most specific signal, and what catches a same-site
       sibling host).
    2. No `Origin` header -> allow (header-less clients).
    3. `Origin: null` -> reject (an opaque origin, never this site's own).
    4. Otherwise `Origin`'s netloc must equal `Host`, default ports
       stripped from both sides; a present `Origin` with no `Host` is
       rejected.
    """
    sfs = headers.get("Sec-Fetch-Site")
    if sfs is not None and sfs.strip().lower() in ("cross-site", "same-site"):
        return False

    origin = headers.get("Origin")
    if origin is None:
        return True
    if origin == "null":
        return False

    parsed = urlsplit(origin)
    netloc = (parsed.hostname or "").lower()
    if parsed.port is not None and str(parsed.port) != _ORIGIN_DEFAULT_PORT.get(parsed.scheme):
        netloc = "%s:%d" % (netloc, parsed.port)

    host = (headers.get("Host") or "").lower()
    for suffix in (":443", ":80"):
        if host.endswith(suffix):
            host = host[: -len(suffix)]
            break

    return bool(host) and netloc == host
