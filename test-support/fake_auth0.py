# SPDX-License-Identifier: AGPL-3.0-only
"""A loopback stand-in for Auth0, for tests.

It enforces what the companion relies on - PKCE S256, an exact registered
redirect_uri, the client secret, single-use authorization codes and a
logout allow-list - and can be told to misbehave in the ways the app must
survive (see KNOBS). Minted ID tokens carry a junk signature so nothing
can come to depend on verifying it.

Standard library only; no pytest import, so subprocess and in-process app
fixtures can both use it. Placeholder values only.
"""

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KNOBS = (
    "claims",            # dict of payload overrides; a None value removes the claim
    "alg",               # JWT header alg (default RS256)
    "redirect_state",    # state returned to the app instead of the real one
    "redirect_error",    # error code returned instead of an authorization code
    "token_status",      # HTTP status for /oauth/token (non-200 fails the exchange)
    "token_body",        # raw body for /oauth/token
    "omit_id_token",     # leave id_token out of a successful response
    "token_delay_s",     # sleep before answering /oauth/token
    "reuse_code",        # do not consume codes on use
    "wrong_redirect_uri",  # remember a different redirect_uri for the code
    "issuer_host",       # host written into iss, when it differs from `domain`
    "mgmt_token_status",   # HTTP status for the Management token request
    "mgmt_users_status",   # HTTP status for POST /api/v2/users
    "mgmt_users_body",     # raw body for POST /api/v2/users
    "mgmt_ticket_status",  # HTTP status for POST /api/v2/tickets/password-change
    "mgmt_ticket_body",    # raw body for POST /api/v2/tickets/password-change
    "mgmt_delay_s",        # sleep before answering any Management call
)

MGMT_TOKEN = "fake-mgmt-access-token"


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _segment(doc):
    return _b64url(json.dumps(doc, separators=(",", ":")).encode("utf-8"))


class FakeAuth0:
    def __init__(self, client_id, client_secret, redirect_uri,
                 allowed_logout_urls=()):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.allowed_logout_urls = list(allowed_logout_urls)
        self.calls = []
        self._lock = threading.Lock()
        self._codes = {}
        self._knobs = {}
        self._identity = {"sub": "auth0|fake-user", "email": "user@example.test",
                          "email_verified": True}
        self._server = None
        self._thread = None
        self.mgmt = None

    # --- lifecycle ---

    def start(self):
        handler = _make_handler(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        # A short poll interval makes shutdown() return in milliseconds, not 0.5 s.
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.01}, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def port(self):
        return self._server.server_address[1]

    @property
    def domain(self):
        return "127.0.0.1:%d" % self.port

    # --- test controls ---

    def next_login(self, sub="auth0|fake-user", email="user@example.test",
                   email_verified=True):
        self._identity = {"sub": sub, "email": email,
                          "email_verified": email_verified}

    def set_knob(self, name, value):
        if name not in KNOBS:
            raise KeyError("unknown knob %r" % name)
        self._knobs[name] = value

    def clear_knobs(self):
        self._knobs = {}

    def knob(self, name, default=None):
        return self._knobs.get(name, default)

    def register_with_env(self, env):
        """Return `env` plus the Auth0 variables pointing at this fake."""
        merged = dict(env)
        merged.update({
            "SKYPANE_AUTH0_DOMAIN": self.domain,
            "SKYPANE_AUTH0_CLIENT_ID": self.client_id,
            "SKYPANE_AUTH0_CLIENT_SECRET": self.client_secret,
            "SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK": "1",
        })
        return merged

    def enable_management(self, client_id, client_secret, connection,
                          connection_id, scopes=("create:users",
                                                 "create:user_tickets")):
        """Turn on the Management endpoints with a machine-to-machine
        application. Requests are recorded in `mgmt.requests` (path, JSON
        body, bearer token seen) for assertions."""
        self.mgmt = _Management(client_id, client_secret, connection,
                                connection_id, tuple(scopes), self)
        return self.mgmt

    def mgmt_env(self, env=None):
        """`env` plus the Management variables pointing at this fake."""
        merged = dict(env or {})
        merged.update({
            "SKYPANE_AUTH0_DOMAIN": self.domain,
            "SKYPANE_AUTH0_MGMT_CLIENT_ID": self.mgmt.client_id,
            "SKYPANE_AUTH0_MGMT_CLIENT_SECRET": self.mgmt.client_secret,
            "SKYPANE_AUTH0_DB_CONNECTION": self.mgmt.connection,
            "SKYPANE_AUTH0_DB_CONNECTION_ID": self.mgmt.connection_id,
            "SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK": "1",
        })
        return merged

    def calls_to(self, path):
        return [c for c in self.calls if c[1] == path]

    # --- protocol, called from the request handler ---

    def record(self, method, path, params):
        with self._lock:
            self.calls.append((method, path, params))

    def authorize(self, params):
        """Return (status, location_or_message)."""
        problem = self._authorize_problem(params)
        if problem:
            return 400, problem
        state = self.knob("redirect_state", params["state"])
        if self.knob("redirect_error"):
            return 302, self._back({"error": self.knob("redirect_error"),
                                    "state": state})
        code = secrets.token_urlsafe(24)
        redirect_uri = self.knob("wrong_redirect_uri") or params["redirect_uri"]
        with self._lock:
            self._codes[code] = {
                "challenge": params["code_challenge"],
                "nonce": params.get("nonce", ""),
                "redirect_uri": redirect_uri,
                "identity": dict(self._identity),
            }
        return 302, self._back({"code": code, "state": state})

    def _authorize_problem(self, params):
        if params.get("response_type") != "code":
            return "bad response_type"
        if params.get("client_id") != self.client_id:
            return "bad client_id"
        if params.get("redirect_uri") != self.redirect_uri:
            return "redirect_uri not registered"
        if params.get("code_challenge_method") != "S256":
            return "PKCE S256 required"
        if not params.get("code_challenge") or not params.get("state"):
            return "missing code_challenge or state"
        if "openid" not in params.get("scope", "").split():
            return "openid scope required"
        return ""

    def _back(self, extra):
        return self.redirect_uri + "?" + urllib.parse.urlencode(extra)

    def token(self, form):
        """Return (status, body_text, extra_headers)."""
        if form.get("grant_type") == "client_credentials":
            if self.mgmt is None:
                return 400, json.dumps({"error": "unsupported_grant_type"}), {}
            return self.mgmt.token(form)
        delay = self.knob("token_delay_s", 0)
        if delay:
            time.sleep(delay)
        status = self.knob("token_status", 200)
        if status != 200:
            headers = {"Location": "/oauth/redirected"} if 300 <= status < 400 else {}
            return status, self.knob("token_body", "{}"), headers
        failure, entry = self._token_failure(form)
        if failure:
            return failure[0], json.dumps({"error": failure[1]}), {}
        if self.knob("token_body") is not None:
            return 200, self.knob("token_body"), {}
        return 200, json.dumps(self._token_response(entry)), {}

    def _token_failure(self, form):
        if form.get("client_id") != self.client_id:
            return (401, "invalid_client"), None
        if not hmac.compare_digest(
                form.get("client_secret", "").encode("utf-8"),
                self.client_secret.encode("utf-8")):
            return (401, "invalid_client"), None
        if form.get("grant_type") != "authorization_code":
            return (400, "unsupported_grant_type"), None
        entry = self._take_code(form.get("code", ""))
        if entry is None:
            return (400, "invalid_grant"), None
        if form.get("redirect_uri") != entry["redirect_uri"]:
            return (400, "invalid_grant"), None
        digest = _b64url(hashlib.sha256(
            form.get("code_verifier", "").encode("utf-8")).digest())
        if not hmac.compare_digest(digest.encode("ascii"),
                                   entry["challenge"].encode("utf-8")):
            return (400, "invalid_grant"), None
        return None, entry

    def _take_code(self, code):
        with self._lock:
            if self.knob("reuse_code"):
                return self._codes.get(code)
            return self._codes.pop(code, None)

    def _token_response(self, entry):
        response = {
            "access_token": "fake-access-token",
            "token_type": "Bearer",
            "expires_in": 86400,
        }
        if not self.knob("omit_id_token"):
            response["id_token"] = self._mint(entry)
        return response

    def _mint(self, entry):
        now = int(time.time())
        identity = entry["identity"]
        issuer_host = self.knob("issuer_host") or self.domain
        payload = {
            "iss": "http://%s/" % issuer_host,
            "aud": self.client_id,
            "sub": identity["sub"],
            "email": identity["email"],
            "email_verified": identity["email_verified"],
            "nonce": entry["nonce"],
            "iat": now,
            "exp": now + 3600,
        }
        for name, value in (self.knob("claims") or {}).items():
            if value is None:
                payload.pop(name, None)
            else:
                payload[name] = value
        header = {"alg": self.knob("alg", "RS256"), "typ": "JWT"}
        return "%s.%s.junk-signature" % (_segment(header), _segment(payload))

    def logout(self, params):
        return_to = params.get("returnTo", "")
        if params.get("client_id") == self.client_id and \
                return_to in self.allowed_logout_urls:
            return 302, return_to
        return 400, "returnTo is not in the allowed logout URLs"


class _Management:
    """Management API stand-in: client-credentials token, user creation and
    password-change tickets. Placeholder values only."""

    def __init__(self, client_id, client_secret, connection, connection_id,
                 scopes, fake):
        self.client_id = client_id
        self.client_secret = client_secret
        self.connection = connection
        self.connection_id = connection_id
        self.scopes = scopes
        self.fake = fake
        self.users = {}
        self.requests = []
        self.token_forms = []

    def _pause(self):
        delay = self.fake.knob("mgmt_delay_s", 0)
        if delay:
            time.sleep(delay)

    def token(self, form):
        self._pause()
        self.token_forms.append(dict(form))
        status = self.fake.knob("mgmt_token_status", 200)
        if status != 200:
            return status, json.dumps({"error": "access_denied"}), {}
        good = (form.get("client_id") == self.client_id
                and hmac.compare_digest(
                    form.get("client_secret", "").encode("utf-8"),
                    self.client_secret.encode("utf-8"))
                and form.get("audience") == "http://%s/api/v2/" % self.fake.domain)
        if not good:
            return 401, json.dumps({"error": "access_denied"}), {}
        return 200, json.dumps({
            "access_token": MGMT_TOKEN, "token_type": "Bearer",
            "expires_in": 86400, "scope": " ".join(self.scopes)}), {}

    def call(self, path, bearer, body):
        """Return (status, body_text) for POST /api/v2/users or
        /api/v2/tickets/password-change."""
        self._pause()
        self.requests.append((path, body, bearer))
        if bearer != "Bearer " + MGMT_TOKEN or not isinstance(body, dict):
            return 401, json.dumps({"error": "Unauthorized"})
        if path == "/api/v2/users":
            return self._create_user(body)
        if path == "/api/v2/tickets/password-change":
            return self._ticket(body)
        return 404, "not found"

    def _create_user(self, body):
        if "create:users" not in self.scopes:
            return 403, json.dumps({"error": "Forbidden"})
        status = self.fake.knob("mgmt_users_status")
        if status:
            return status, self.fake.knob("mgmt_users_body", "{}")
        if body.get("connection") != self.connection:
            return 400, json.dumps({"error": "bad connection"})
        email = str(body.get("email", "")).lower()
        if not email or not body.get("password"):
            return 400, json.dumps({"error": "bad payload"})
        if email in self.users:
            return 409, json.dumps({"error": "The user already exists."})
        user_id = "auth0|" + secrets.token_hex(12)
        self.users[email] = user_id
        return 201, json.dumps({"user_id": user_id, "email": email})

    def _ticket(self, body):
        if "create:user_tickets" not in self.scopes:
            return 403, json.dumps({"error": "Forbidden"})
        status = self.fake.knob("mgmt_ticket_status")
        if status:
            return status, self.fake.knob("mgmt_ticket_body", "{}")
        known = set(self.users.values())
        by_id = body.get("user_id") in known
        by_email = (str(body.get("email", "")).lower() in self.users
                    and body.get("connection_id") == self.connection_id)
        if not (by_id or by_email):
            return 400, json.dumps({"error": "unknown user"})
        ticket = "http://%s/lo/reset?ticket=%s" % (
            self.fake.domain, secrets.token_urlsafe(16))
        return 201, json.dumps({"ticket": ticket})


def _make_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def _send(self, status, body="", headers=None):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _redirect_or_error(self, status, where):
            if status == 302:
                self._send(302, "", {"Location": where})
            else:
                self._send(status, where, {"Content-Type": "text/plain"})

        def do_GET(self):
            parts = urllib.parse.urlsplit(self.path)
            params = dict(urllib.parse.parse_qsl(parts.query))
            fake.record("GET", parts.path, params)
            if parts.path == "/authorize":
                self._redirect_or_error(*fake.authorize(params))
            elif parts.path == "/v2/logout":
                self._redirect_or_error(*fake.logout(params))
            else:
                self._send(404, "not found")

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            if "json" in (self.headers.get("Content-Type") or ""):
                try:
                    doc = json.loads(raw)
                except ValueError:
                    return {}
                return doc if isinstance(doc, dict) else {}
            return dict(urllib.parse.parse_qsl(raw))

        def _management(self, path, body):
            fake.record("POST", path, {})
            if fake.mgmt is None:
                self._send(404, "not found")
                return
            status, text = fake.mgmt.call(
                path, self.headers.get("Authorization"), body)
            self._send(status, text, {"Content-Type": "application/json"})

        def do_POST(self):
            form = self._read_body()
            parts = urllib.parse.urlsplit(self.path)
            if parts.path.startswith("/api/v2/"):
                self._management(parts.path, form)
                return
            if parts.path != "/oauth/token":
                fake.record("POST", parts.path, {})
                self._send(404, "not found")
                return
            logged = {k: form[k] for k in ("grant_type", "client_id",
                                           "redirect_uri") if k in form}
            fake.record("POST", parts.path, logged)
            status, body, headers = fake.token(form)
            headers = dict(headers, **{"Content-Type": "application/json"})
            self._send(status, body, headers)

    return Handler
