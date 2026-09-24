"""companion/auth.py — the shared-password session gate for the SkyPane
companion service (D-01/D-02, 06-CONTEXT.md).

There are no per-user accounts: a single shared password protects the
entire site uniformly (D-02). This module is stdlib-only (collections,
hashlib, hmac, http.cookies, ipaddress, os, time, secrets,
urllib.parse) — it must never import Pillow, sqlite3, or anything
under server/, matching this project's stdlib-first discipline
(06-RESEARCH.md).

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
# D-02 (20-01-PLAN.md Task 2): the language per-browser cookie, added
# directly beside UI_THEME_COOKIE_NAME — both share secure_cookie_
# flag() below, so the Secure flag can never drift between them.
UI_LANG_COOKIE_NAME = "sp_ui_lang"
# D-17 (21-01-PLAN.md Task 1): the sibling per-browser cookie that
# backed the now-removed simple/full display-mode switch is deleted
# along with the feature. A browser that still holds a stale copy of
# that cookie is simply never read again — no migration, no
# explicit-ignore branch; nothing under companion/ names that cookie
# any more.
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_S = 300
INSECURE_COOKIES_ENV_VAR = "SKYPANE_COMPANION_INSECURE_COOKIES"

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


def secure_cookie_flag():
    """The `"; Secure"` cookie-attribute fragment, or `""` — A-34/D-17.

    Caddy terminating TLS in front of this service is still the
    production posture, and `Secure` stays on by default for exactly
    that reason. This flag exists solely so a plain-http LAN or dev run
    (no Caddy/TLS in front) is not silently, unwinnably bounced back to
    /login on every login attempt, because a browser will never send a
    Secure cookie back over plain http.

    Read fresh from the environment on every call (matching
    configured_password()'s own read-fresh idiom, so a systemd unit
    change needs no code change), and fails closed: any value other
    than exactly "1" — including "true", "yes", or an empty string —
    leaves Secure ON.
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
    SKYPANE_COMPANION_INSECURE_COOKIES=1 opt-out (A-34/D-17, see
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


def client_ip(peer, xff):
    """The address that identifies a caller for login-throttle purposes.

    `X-Forwarded-For` is only trusted when the TCP peer itself is
    loopback — that is Caddy, the only reverse proxy in front of this
    service, and Caddy overwrites (never appends to) a client-supplied
    XFF value. Any other peer is talking to this process directly (dev/
    LAN use, or a future misconfiguration), so a header it could set
    itself must never be trusted: the peer address is the identity.
    When XFF is trusted, its right-most entry is used — that is the
    hop Caddy itself appended, never a value an upstream client wrote.
    An unparsable peer or XFF value falls back to the peer string as
    given, so a malformed header can never turn into an exception on
    the request path.
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
    """A failed-login guard keyed on the caller's address (client_ip()/
    login_throttle_key() above), not a single process-global counter.

    D-01/D-02 mean there are no distinct user accounts on this site, so
    a per-session counter would be trivially defeated by opening a
    second tab — the same reasoning 06-RESEARCH.md's Pitfall 8 applies
    to the CFG-07 poll-trigger cooldown applies here. A single shared
    global counter, however, has the opposite problem: one stranger's
    wrong guesses lock out the site's real owner. Keying on the caller's
    address gives each address its own bucket, so failures from one
    address never lock another, while still sharing one lockout window
    per address — this remains a courtesy guard for a single-user
    personal tool, not a defence against a distributed attacker; the
    real strength of this site's auth is the length of the
    operator-generated shared secret.

    The bucket table (`collections.OrderedDict`, key -> [failures,
    locked_until, last_seen]) is bounded by `max_entries`: without a
    cap, an attacker spraying distinct source addresses could grow the
    table without limit. On an insert that would exceed the cap,
    entries that are both unlocked and idle for longer than the lockout
    window are dropped first (they are almost certainly done mattering)
    and, if that alone is not enough, the least-recently-touched entries
    are evicted next, regardless of lock state. A spraying attacker can
    thereby evict and reset their own locked bucket, but never anyone
    else's — an accepted trade for bounded memory.
    """

    def __init__(self, limit=LOGIN_FAILURE_LIMIT, lockout_s=LOGIN_LOCKOUT_S,
                 max_entries=4096, clock=time.time):
        self._limit = limit
        self._lockout_s = lockout_s
        self._max_entries = max_entries
        self._clock = clock
        self._entries = collections.OrderedDict()
        # WR-03 (19-REVIEW.md): this instance is a single process-global
        # object shared across every request thread under
        # ThreadingHTTPServer (see the class docstring above), so the
        # table must not be read-then-written by two threads at once.
        # Mirrors _REVOKED_LOCK's own precedent a few functions above in
        # this same file.
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
        # Must be called with self._lock already held. Returns the
        # mutable [failures, locked_until, last_seen] entry for key,
        # creating it (evicting first if the table is full) and moving
        # it to the most-recently-seen end.
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]
        self._evict_locked()
        entry = [0, 0.0, self._clock()]
        self._entries[key] = entry
        return entry

    def record_failure(self, key):
        # A-32/D-15: once the previous lockout window has fully elapsed,
        # a new failure must start a fresh count rather than re-arming
        # the lockout from an already-saturated counter — otherwise one
        # stray wrong password per window keeps the lockout permanent.
        # Contract: five fresh failures per window, never permanent.
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


# SEC-03 (37-05-PLAN.md Task 1, D-16, T-37-22/T-37-23): defence in depth
# on top of SameSite=Strict (A-33/D-16 above), not a replacement for it.
# SameSite=Strict already stops a cross-site browser navigation or fetch
# from carrying the session cookie at all in every browser that honours
# it; this check exists for the two things that discipline alone does not
# cover — a browser that predates SameSite=Strict enforcement, and a
# same-site sibling host (another name under the same registrable domain,
# e.g. a second *.nip.io label) that SameSite=Strict itself does NOT
# distinguish from this site (T-37-23). Fetch Metadata's Sec-Fetch-Site
# header names that distinction directly ("cross-site" vs "same-site" vs
# "same-origin"), so it is checked first and rejects both.
#
# Header-less requests are allowed on purpose (T-37-24, accepted): a
# request carrying neither Sec-Fetch-Site nor Origin still needs a valid
# session cookie to do anything, and refusing it here would only break
# non-browser and older-browser clients for no security gain — the
# accepted risk is an old browser's cross-site POST reaching the gate
# with SameSite=Strict already having stripped its cookie, not a
# meaningfully more permissive request.
#
# Comparing Origin against Host (rather than a hardcoded hostname) is
# sound specifically because this is a same-process comparison of two
# request headers a well-behaved client sets independently: a browser
# always sets Origin to the page's own origin and Host to the request's
# real target, and an attacker page can set neither on the victim's
# behalf. Caddy passes Host through unchanged by default, so this holds
# identically in production (behind Caddy) and in a bare-loopback test.
_ORIGIN_DEFAULT_PORT = {"https": "443", "http": "80"}


def post_origin_ok(headers):
    """True when `headers` (any mapping with a `.get()` keyed by the
    exact header names browsers send — `http.server`'s own per-request
    `self.headers` is already case-insensitive on lookup, and a plain
    test dict simply uses those same names) describes a POST this
    service should accept; False when it looks cross-site and must be
    rejected with a 403 before any routing or form read (see
    companion/app.py's `do_POST()`).

    Rule, in order:
    1. `Sec-Fetch-Site: cross-site` or `same-site` -> reject (T-37-22/
       T-37-23) — checked first because it is the most specific signal a
       modern browser sends, and it is what catches a same-site sibling
       host Origin/Host comparison alone would not.
    2. No `Origin` header at all -> allow (header-less clients, T-37-24).
    3. `Origin: null` -> reject (an opaque origin — a sandboxed iframe, a
       data: URL, or a redirect chain — is never this site's own origin).
    4. Otherwise, `Origin`'s netloc must equal `Host`, compared
       case-insensitively with each side's own default port (443 for
       https, 80 for http) stripped so `https://h` and `https://h:443`
       compare equal to a bare `Host: h`. A present `Origin` with no
       `Host` at all is rejected rather than treated as unverifiable.
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
