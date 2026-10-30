"""Auth0 sign-in pieces for the companion: configuration, PKCE, the
authorize and logout URLs, ID-token claim validation, the token-endpoint
call and the pre-login attempt table.

Everything here is pure or takes its HTTP callable as an argument, so it
runs without a network in unit tests. Nothing in this module touches the
request handler or fleet.db.

The ID token is read only from the token-endpoint response, which arrives
over TLS straight from the identity provider. Its signature is therefore
not verified locally; every claim that binds it to this client, this
tenant and this login attempt is.

Errors carry short reason codes. No code, token, response body or client
secret ever appears in an exception message or a log line.
"""

import base64
import collections
import dataclasses
import hashlib
import hmac
import json
import math
import secrets
import threading
import time
import urllib.parse

import requests

ENV_DOMAIN = "SKYPANE_AUTH0_DOMAIN"
ENV_CLIENT_ID = "SKYPANE_AUTH0_CLIENT_ID"
ENV_CLIENT_SECRET = "SKYPANE_AUTH0_CLIENT_SECRET"
ENV_HOST = "SKYPANE_COMPANION_HOST"
ENV_PUBLIC_URL = "SKYPANE_COMPANION_PUBLIC_URL"
ENV_ALLOW_INSECURE = "SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK"

LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")

TOKEN_CONNECT_TIMEOUT = 3.05
TOKEN_READ_TIMEOUT = 10
TOKEN_TOTAL_DEADLINE = 15
TOKEN_MAX_BYTES = 64 * 1024

LEEWAY_SECONDS = 60
SUB_MAX_LENGTH = 255

ATTEMPT_CAPACITY = 4096
ATTEMPT_TTL_SECONDS = 600

KIND_INCOMPLETE = "incomplete"
KIND_EXPIRED = "expired"
KIND_UNAVAILABLE = "unavailable"


class Auth0ConfigError(Exception):
    """Misconfigured Auth0 settings; the message names variables only."""


class SignInError(Exception):
    """A sign-in step failed. `reason` is a short code, `kind` one of
    incomplete, expired or unavailable."""

    def __init__(self, reason, kind=KIND_INCOMPLETE):
        super().__init__(reason)
        self.reason = reason
        self.kind = kind


@dataclasses.dataclass(frozen=True)
class Claims:
    sub: str
    email: str
    email_verified: bool


@dataclasses.dataclass(frozen=True)
class HttpReply:
    status: int
    body: bytes


@dataclasses.dataclass(frozen=True)
class Auth0Config:
    domain: str
    client_id: str
    client_secret: str = dataclasses.field(repr=False)
    scheme: str
    public_url: str

    @property
    def base_url(self):
        return "%s://%s" % (self.scheme, self.domain)

    @property
    def issuer(self):
        return self.base_url + "/"

    @property
    def redirect_uri(self):
        return self.public_url + "/callback"

    @property
    def return_to(self):
        return self.public_url + "/login"

    @classmethod
    def from_env(cls, environ):
        names = (ENV_DOMAIN, ENV_CLIENT_ID, ENV_CLIENT_SECRET)
        values = {name: (environ.get(name) or "").strip() for name in names}
        present = [name for name in names if values[name]]
        if not present:
            return None
        missing = [name for name in names if not values[name]]
        if missing:
            raise Auth0ConfigError(
                "incomplete Auth0 configuration; missing: " + ", ".join(missing))
        allow_insecure = environ.get(ENV_ALLOW_INSECURE) == "1"
        domain = values[ENV_DOMAIN]
        scheme = _domain_scheme(domain, allow_insecure)
        return cls(
            domain=domain,
            client_id=values[ENV_CLIENT_ID],
            client_secret=values[ENV_CLIENT_SECRET],
            scheme=scheme,
            public_url=_public_url(environ, allow_insecure))


def _host_of(netloc):
    try:
        return urllib.parse.urlsplit("//" + netloc).hostname or ""
    except ValueError:
        return ""


def _domain_scheme(domain, allow_insecure):
    """https, or http only for a loopback domain behind the test flag."""
    if "://" in domain or "/" in domain or "@" in domain or "?" in domain:
        raise Auth0ConfigError(ENV_DOMAIN + " must be a bare host[:port]")
    if _host_of(domain) in LOOPBACK_HOSTS and allow_insecure:
        return "http"
    return "https"


def _public_url(environ, allow_insecure):
    override = (environ.get(ENV_PUBLIC_URL) or "").strip().rstrip("/")
    if override:
        return _checked_public_url(override, allow_insecure)
    host = (environ.get(ENV_HOST) or "").strip()
    if not host:
        raise Auth0ConfigError(
            "set %s or %s so the sign-in redirect address is known"
            % (ENV_HOST, ENV_PUBLIC_URL))
    return _checked_public_url("https://" + host, allow_insecure)


def _checked_public_url(url, allow_insecure):
    parts = urllib.parse.urlsplit(url)
    bad_shape = (parts.path not in ("", "/") or parts.query or parts.fragment
                 or not parts.netloc)
    if bad_shape or parts.scheme not in ("http", "https"):
        raise Auth0ConfigError(ENV_PUBLIC_URL + " must be an https origin")
    if parts.scheme == "http":
        loopback = (parts.hostname or "") in LOOPBACK_HOSTS
        if not (allow_insecure and loopback):
            raise Auth0ConfigError(ENV_PUBLIC_URL + " must use https")
    return "%s://%s" % (parts.scheme, parts.netloc)


# --- PKCE and URLs ----------------------------------------------------------

def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def new_pkce():
    """Return (verifier, S256 challenge)."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def new_token():
    return secrets.token_urlsafe(32)


def authorize_url(cfg, state, nonce, challenge):
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "scope": "openid email",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return "%s/authorize?%s" % (cfg.base_url, query)


def logout_url(cfg):
    """Auth0 sign-out address. Kept in one function so a move to the
    end_session_endpoint is a one-function change."""
    query = urllib.parse.urlencode(
        {"client_id": cfg.client_id, "returnTo": cfg.return_to})
    return "%s/v2/logout?%s" % (cfg.base_url, query)


# --- ID-token claim validation ---------------------------------------------

def _decode_segment(segment):
    try:
        padded = segment + "=" * (-len(segment) % 4)
        doc = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeError):
        raise SignInError("token_malformed") from None
    if not isinstance(doc, dict):
        raise SignInError("token_malformed")
    return doc


def _is_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _check_header(header):
    alg = header.get("alg")
    if not isinstance(alg, str) or alg.lower() == "none":
        raise SignInError("token_alg")


def _check_audience(payload, client_id):
    aud = payload.get("aud")
    if isinstance(aud, str):
        auds = [aud]
    elif isinstance(aud, list) and all(isinstance(a, str) for a in aud):
        auds = aud
    else:
        raise SignInError("token_aud")
    if client_id not in auds:
        raise SignInError("token_aud")
    if len(auds) > 1 or "azp" in payload:
        if payload.get("azp") != client_id:
            raise SignInError("token_azp")


def _check_times(payload, now, leeway):
    exp = payload.get("exp")
    if not _is_number(exp):
        raise SignInError("token_exp")
    if exp <= now - leeway:
        raise SignInError("token_expired", KIND_EXPIRED)
    iat = payload.get("iat")
    if not _is_number(iat) or iat > now + leeway:
        raise SignInError("token_iat")


def _check_nonce(payload, nonce):
    seen = payload.get("nonce")
    if not isinstance(seen, str) or not isinstance(nonce, str):
        raise SignInError("token_nonce")
    if not hmac.compare_digest(seen.encode("utf-8"), nonce.encode("utf-8")):
        raise SignInError("token_nonce")


def validate_id_token(token, cfg, nonce, now=None, leeway=LEEWAY_SECONDS):
    """Check the claims that bind the token to this client and attempt."""
    if now is None:
        now = time.time()
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        raise SignInError("token_malformed")
    _check_header(_decode_segment(parts[0]))
    payload = _decode_segment(parts[1])
    if payload.get("iss") != cfg.issuer:
        raise SignInError("token_iss")
    _check_audience(payload, cfg.client_id)
    _check_times(payload, now, leeway)
    _check_nonce(payload, nonce)
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub or len(sub) > SUB_MAX_LENGTH:
        raise SignInError("token_sub")
    email = payload.get("email")
    return Claims(
        sub=sub,
        email=email if isinstance(email, str) else "",
        email_verified=payload.get("email_verified") is True)


# --- token endpoint ---------------------------------------------------------

def exchange_code(cfg, code, verifier, post):
    """Trade an authorization code for the ID token string."""
    reply = post(cfg.base_url + "/oauth/token", {
        "grant_type": "authorization_code",
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": cfg.redirect_uri,
    })
    if reply.status != 200:
        raise SignInError("token_status_%d" % reply.status)
    try:
        doc = json.loads(reply.body)
    except (ValueError, UnicodeError):
        raise SignInError("token_response_not_json") from None
    token = doc.get("id_token") if isinstance(doc, dict) else None
    if not isinstance(token, str) or not token:
        raise SignInError("token_response_no_id_token")
    return token


def _read_capped(response, deadline):
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > TOKEN_MAX_BYTES:
            raise SignInError("token_response_too_large", KIND_UNAVAILABLE)
        if time.monotonic() > deadline:
            raise SignInError("token_response_slow", KIND_UNAVAILABLE)
        chunks.append(chunk)
    return b"".join(chunks)


def requests_post(url, data):
    """POST a form to the token endpoint with hardened settings: no proxy
    or netrc lookup, certificate verification on, no redirects, bounded
    timeouts, a capped body and an overall deadline."""
    deadline = time.monotonic() + TOKEN_TOTAL_DEADLINE
    session = requests.Session()
    session.trust_env = False
    session.verify = True
    try:
        response = session.post(
            url, data=data, allow_redirects=False, stream=True, verify=True,
            timeout=(TOKEN_CONNECT_TIMEOUT, TOKEN_READ_TIMEOUT))
        try:
            return HttpReply(response.status_code, _read_capped(response, deadline))
        finally:
            response.close()
    except requests.RequestException:
        raise SignInError("token_unreachable", KIND_UNAVAILABLE) from None
    finally:
        session.close()


# --- pre-login attempts -----------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Attempt:
    state: str
    nonce: str
    verifier: str
    challenge: str
    next_route: str
    created_at: float


class AttemptTable:
    """Bounded, expiring, in-memory record of started sign-ins. A pop
    consumes the attempt, so a callback can be used once."""

    def __init__(self, clock=time.time, capacity=ATTEMPT_CAPACITY,
                 ttl=ATTEMPT_TTL_SECONDS):
        self._clock = clock
        self._capacity = capacity
        self._ttl = ttl
        self._lock = threading.Lock()
        self._items = collections.OrderedDict()

    def create(self, next_route):
        verifier, challenge = new_pkce()
        now = self._clock()
        attempt = Attempt(new_token(), new_token(), verifier, challenge,
                          next_route, now)
        attempt_id = new_token()
        with self._lock:
            self._purge_expired(now)
            while len(self._items) >= self._capacity:
                self._items.popitem(last=False)
            self._items[attempt_id] = attempt
        return attempt_id, attempt

    def pop(self, attempt_id):
        with self._lock:
            attempt = self._items.pop(attempt_id, None)
        if attempt is None or self._clock() - attempt.created_at >= self._ttl:
            return None
        return attempt

    def _purge_expired(self, now):
        while self._items:
            oldest_id = next(iter(self._items))
            if now - self._items[oldest_id].created_at < self._ttl:
                break
            del self._items[oldest_id]


START_LIMIT = 30
START_WINDOW_SECONDS = 60
START_THROTTLE_MAX_KEYS = 4096


class StartThrottle:
    """Per-client sliding-window limit on starting a sign-in, so one client
    cannot fill `AttemptTable` and push out other people's pending
    attempts. Bounded: past `max_keys` clients, idle ones go first and then
    the least recently seen.
    """

    def __init__(self, clock=time.time, limit=START_LIMIT,
                 window=START_WINDOW_SECONDS, max_keys=START_THROTTLE_MAX_KEYS):
        self._clock = clock
        self._limit = limit
        self._window = window
        self._max_keys = max_keys
        self._lock = threading.Lock()
        self._starts = collections.OrderedDict()

    def allow(self, key):
        """Record a start for `key` and return True, or return False
        (recording nothing) when `key` has used up its window.
        """
        now = self._clock()
        with self._lock:
            times = self._starts.get(key)
            if times is None:
                self._make_room(now)
                times = self._starts[key] = collections.deque()
            else:
                self._starts.move_to_end(key)
            while times and now - times[0] >= self._window:
                times.popleft()
            if len(times) >= self._limit:
                return False
            times.append(now)
            return True

    def reset(self):
        with self._lock:
            self._starts.clear()

    def _make_room(self, now):
        if len(self._starts) < self._max_keys:
            return
        for key in list(self._starts):
            times = self._starts[key]
            if not times or now - times[-1] >= self._window:
                del self._starts[key]
        while len(self._starts) >= self._max_keys:
            self._starts.popitem(last=False)
