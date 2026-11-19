"""Auth0 Management API client: create a database user and a password-change
ticket so an invited person can set a password and sign in.

Required Management API scopes for the machine-to-machine application, and
no others:

    create:users          POST /api/v2/users
    create:user_tickets   POST /api/v2/tickets/password-change

The client credential is read only from the environment (the environment
file on the server); it is never written anywhere. This module does not log
at all and its results carry short reason codes only: the client secret, the
access token, the generated password and the ticket link never appear in an
exception, a reason, a repr or a log record. The ticket link is returned to
the caller once and kept nowhere here.

Sign-in stays gated by the local invite row; an Auth0 account alone grants
nothing. The user payload carries no role and no metadata.

Every public function returns a result and never raises, so an Auth0 outage
cannot break the caller's local invite.
"""

import dataclasses
import json
import secrets
import time
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any

import requests

ENV_DOMAIN = "SKYPANE_AUTH0_DOMAIN"
ENV_CLIENT_ID = "SKYPANE_AUTH0_MGMT_CLIENT_ID"
ENV_CLIENT_SECRET = "SKYPANE_AUTH0_MGMT_CLIENT_SECRET"
ENV_CONNECTION = "SKYPANE_AUTH0_DB_CONNECTION"
ENV_CONNECTION_ID = "SKYPANE_AUTH0_DB_CONNECTION_ID"
ENV_ALLOW_INSECURE = "SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK"

LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")

CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 10
TOTAL_DEADLINE = 15
MAX_BYTES = 64 * 1024

TICKET_TTL_SECONDS = 5 * 24 * 3600
EMAIL_MAX_LENGTH = 254

REASON_NOT_CONFIGURED = "not_configured"
REASON_BAD_EMAIL = "bad_email"
REASON_BAD_RESULT_URL = "bad_result_url"
REASON_UNREACHABLE = "unreachable"
REASON_TOKEN = "token_failed"
REASON_CREATE = "create_failed"
REASON_TICKET = "ticket_failed"
REASON_BAD_RESPONSE = "bad_response"
REASON_EXISTS_NO_CONNECTION_ID = "user_exists_connection_id_missing"


@dataclasses.dataclass(frozen=True)
class Reply:
    status: int
    body: bytes


class TransportError(Exception):
    """The request could not be completed; carries no detail."""


# A transport takes (url, json document, headers) and returns a Reply or
# raises TransportError.
Transport = Callable[[str, Mapping[str, Any], Mapping[str, str]], Reply]


@dataclasses.dataclass(frozen=True)
class Result:
    ok: bool
    reason: str = ""
    link: str = dataclasses.field(default="", repr=False)


@dataclasses.dataclass(frozen=True)
class MgmtConfig:
    base_url: str
    client_id: str
    client_secret: str = dataclasses.field(repr=False)
    connection: str = ""
    connection_id: str = ""

    @property
    def audience(self) -> str:
        return self.base_url + "/api/v2/"


def _scheme(domain: str, allow_insecure: bool) -> str:
    """https, or http only for a loopback domain behind the test flag;
    an empty string when the domain is not a bare host[:port]."""
    if any(mark in domain for mark in ("://", "/", "@", "?", "#", " ")):
        return ""
    try:
        host = urllib.parse.urlsplit("//" + domain).hostname or ""
    except ValueError:
        return ""
    if not host:
        return ""
    if host in LOOPBACK_HOSTS and allow_insecure:
        return "http"
    return "https"


def from_env(environ: Mapping[str, str]) -> MgmtConfig | None:
    """The configuration, or None when the credential is absent or
    incomplete (the invitation then stays local)."""
    def value(name: str) -> str:
        return (environ.get(name) or "").strip()

    domain = value(ENV_DOMAIN)
    client_id = value(ENV_CLIENT_ID)
    secret = value(ENV_CLIENT_SECRET)
    connection = value(ENV_CONNECTION)
    if not (domain and client_id and secret and connection):
        return None
    scheme = _scheme(domain, environ.get(ENV_ALLOW_INSECURE) == "1")
    if not scheme:
        return None
    return MgmtConfig(
        base_url="%s://%s" % (scheme, domain), client_id=client_id,
        client_secret=secret, connection=connection,
        connection_id=value(ENV_CONNECTION_ID))


def configured(environ: Mapping[str, str]) -> bool:
    return from_env(environ) is not None


def _read_capped(response: Any, deadline: float) -> bytes:
    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_BYTES or time.monotonic() > deadline:
            raise TransportError()
        chunks.append(chunk)
    return b"".join(chunks)


def requests_post_json(url: str, document: Mapping[str, Any],
                       headers: Mapping[str, str]) -> Reply:
    """POST JSON with hardened settings: no proxy or netrc lookup,
    certificate verification on, no redirects, bounded timeouts, a capped
    body and an overall deadline."""
    deadline = time.monotonic() + TOTAL_DEADLINE
    session = requests.Session()
    session.trust_env = False
    session.verify = True
    try:
        response = session.post(
            url, json=document, headers=dict(headers), allow_redirects=False,
            stream=True, verify=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        try:
            return Reply(response.status_code, _read_capped(response, deadline))
        finally:
            response.close()
    except requests.RequestException:
        raise TransportError() from None
    finally:
        session.close()


def _json_object(reply: Reply) -> dict[str, Any] | None:
    try:
        doc = json.loads(reply.body)
    except (ValueError, UnicodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _call(post: Transport, url: str, document: Mapping[str, Any],
          headers: Mapping[str, str]) -> tuple[Reply | None, str]:
    try:
        return post(url, document, headers), ""
    except TransportError:
        return None, REASON_UNREACHABLE
    except Exception:  # a broken transport must not escape to the caller
        return None, REASON_UNREACHABLE


def _access_token(cfg: MgmtConfig, post: Transport) -> tuple[str, str]:
    """(token, "") or ("", reason). Only the audience is requested."""
    reply, reason = _call(post, cfg.base_url + "/oauth/token", {
        "grant_type": "client_credentials",
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "audience": cfg.audience,
    }, {})
    if reply is None:
        return "", reason
    doc = _json_object(reply)
    token = doc.get("access_token") if doc else None
    if reply.status != 200:
        return "", REASON_TOKEN
    if not isinstance(token, str) or not token:
        return "", REASON_BAD_RESPONSE
    return token, ""


def _create_user(cfg: MgmtConfig, post: Transport, auth: Mapping[str, str],
                 email: str) -> tuple[str, str]:
    """(user_id, "") for a new user, ("", "exists") on a conflict, or
    ("", reason). The random password is never kept or returned."""
    reply, reason = _call(post, cfg.base_url + "/api/v2/users", {
        "email": email,
        "email_verified": False,
        "connection": cfg.connection,
        "password": secrets.token_urlsafe(32),
        "verify_email": False,
    }, auth)
    if reply is None:
        return "", reason
    if reply.status == 409:
        return "", "exists"
    if reply.status != 201:
        return "", REASON_CREATE
    doc = _json_object(reply)
    user_id = doc.get("user_id") if doc else None
    if not isinstance(user_id, str) or not user_id:
        return "", REASON_BAD_RESPONSE
    return user_id, ""


def _ticket(cfg: MgmtConfig, post: Transport, auth: Mapping[str, str],
            who: Mapping[str, str], result_url: str) -> Result:
    document: dict[str, Any] = dict(who)
    document.update({
        "result_url": result_url,
        "ttl_sec": TICKET_TTL_SECONDS,
        "mark_email_as_verified": True,
    })
    reply, reason = _call(
        post, cfg.base_url + "/api/v2/tickets/password-change", document, auth)
    if reply is None:
        return Result(False, reason)
    if reply.status != 201:
        return Result(False, REASON_TICKET)
    doc = _json_object(reply)
    link = doc.get("ticket") if doc else None
    if not isinstance(link, str) or not link:
        return Result(False, REASON_BAD_RESPONSE)
    return Result(True, link=link)


def _valid_email(email: str) -> bool:
    if not isinstance(email, str) or not 3 <= len(email) <= EMAIL_MAX_LENGTH:
        return False
    if any(ord(ch) < 33 or ord(ch) == 127 for ch in email):
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain and "@" not in domain


def _valid_result_url(url: str, allow_insecure: bool) -> bool:
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or ""
    except (ValueError, AttributeError):
        return False
    if parts.username or parts.password or not host:
        return False
    if parts.scheme == "https":
        return True
    return parts.scheme == "http" and allow_insecure and host in LOOPBACK_HOSTS


def create_invitation(environ: Mapping[str, str], email: str, result_url: str,
                      post: Transport = requests_post_json) -> Result:
    """Create the Auth0 user for `email` (or reuse an existing one) and
    return a one-time password-change ticket link in `Result.link`.

    `result_url` is where the person lands after setting the password; the
    caller passes its own validated application URL. Never raises.
    """
    cfg = from_env(environ)
    if cfg is None:
        return Result(False, REASON_NOT_CONFIGURED)
    if not _valid_email(email):
        return Result(False, REASON_BAD_EMAIL)
    if not _valid_result_url(result_url, environ.get(ENV_ALLOW_INSECURE) == "1"):
        return Result(False, REASON_BAD_RESULT_URL)
    token, reason = _access_token(cfg, post)
    if not token:
        return Result(False, reason)
    auth = {"Authorization": "Bearer " + token}
    user_id, reason = _create_user(cfg, post, auth, email)
    if user_id:
        return _ticket(cfg, post, auth, {"user_id": user_id}, result_url)
    if reason != "exists":
        return Result(False, reason)
    if not cfg.connection_id:
        return Result(False, REASON_EXISTS_NO_CONNECTION_ID)
    return _ticket(cfg, post, auth,
                   {"email": email, "connection_id": cfg.connection_id},
                   result_url)
