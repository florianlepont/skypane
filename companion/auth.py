"""Session-token, cookie and client-address helpers for the SkyPane
companion service. Stdlib-only: must never import Pillow, sqlite3, or anything under
server/.

A session is an opaque random token. The cookie carries the token and only
its sha256 is stored server-side (server/fleet_sessions.py), so a session
outlives a restart and no derived value is ever accepted as a session.
"""
import hashlib
import hmac
import ipaddress
import os
import secrets
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

SESSION_COOKIE_NAME = "sp_session"
OIDC_COOKIE_NAME = "sp_oidc"
OIDC_COOKIE_MAX_AGE_S = 600
# Server-side sessions live 30 days at most; the cookie matches that.
SESSION_COOKIE_MAX_AGE_S = 30 * 86400
UI_THEME_COOKIE_NAME = "sp_ui_theme"
# Shares secure_cookie_flag() with UI_THEME_COOKIE_NAME, so the Secure
# flag can never drift between them.
UI_LANG_COOKIE_NAME = "sp_ui_lang"
INSECURE_COOKIES_ENV_VAR = "SKYPANE_COMPANION_INSECURE_COOKIES"

def new_session_token():
    """A fresh opaque 256-bit session token for the cookie. Only its
    hash_session_token() is ever stored server-side.
    """
    return secrets.token_urlsafe(32)


def hash_session_token(token):
    """Hex sha256 of a session token: the only form the database holds."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token(session_token):
    """The per-session anti-forgery token embedded in protected forms: hex
    sha256 of a fixed prefix plus the raw session token. The database holds
    only hash_session_token(), so a leaked database cannot yield it, and the
    cookie is HttpOnly so page script cannot read the source value.
    """
    return hashlib.sha256(b"csrf-v1:" + session_token.encode("utf-8")).hexdigest()


def csrf_ok(session_token, submitted):
    """True only when `submitted` is exactly csrf_token(session_token)
    (constant-time compare). Empty or missing values are always refused.
    """
    if not session_token or not isinstance(submitted, str) or not submitted:
        return False
    return hmac.compare_digest(
        csrf_token(session_token).encode("ascii"), submitted.encode("utf-8"))


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
        % (SESSION_COOKIE_NAME, token, secure_cookie_flag(), SESSION_COOKIE_MAX_AGE_S))


def logout_set_cookie_header():
    """Return a Set-Cookie header value that expires the session cookie
    immediately (empty value, Max-Age=0), carrying the same security
    flags as the cookie it replaces.
    """
    return (
        "%s=; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=0"
        % (SESSION_COOKIE_NAME, secure_cookie_flag()))


def oidc_attempt_set_cookie_header(attempt_id):
    """Set-Cookie value for the pre-login cookie that ties the browser to a
    started sign-in. SameSite=Lax is required: the callback is a
    cross-site top-level navigation from the identity provider, and Strict
    would withhold the cookie. It carries only an opaque attempt id and is
    sent to /callback alone.
    """
    return (
        "%s=%s; HttpOnly%s; SameSite=Lax; Path=/callback; Max-Age=%d"
        % (OIDC_COOKIE_NAME, attempt_id, secure_cookie_flag(), OIDC_COOKIE_MAX_AGE_S))


def oidc_attempt_clear_cookie_header():
    """Set-Cookie value that expires the pre-login cookie."""
    return (
        "%s=; HttpOnly%s; SameSite=Lax; Path=/callback; Max-Age=0"
        % (OIDC_COOKIE_NAME, secure_cookie_flag()))


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
    """The sign-in throttle bucket key for a request: client_ip(), with an
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
