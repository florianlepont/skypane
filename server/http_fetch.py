"""Bounded outbound HTTP for SkyPane's own outgoing calls.

`bounded_get` adds a total wall-clock deadline over a streamed
`requests.get()`, on top of `timeout`'s own per-connect/per-read bound --
`requests`' `timeout=` never bounds the whole transfer, so one slow
upstream trickling one byte at a time can otherwise hang a call (and the
poll cycle that made it) indefinitely. It also caps the response body by
a running byte count, never trusting a declared `Content-Length` (a body
can lie about its own size).

`pinned_request` resolves a hostname once (`resolve_public_addresses`),
refuses the whole host if any answer is not a public unicast address, and
connects only to an address it already checked -- closing the gap where
`requests`/`urllib` re-resolve the hostname again at connect time, so a
DNS answer checked once (DNS rebinding) can differ from the one the
socket actually reaches. Certificate verification still checks the
hostname (SNI and `server_hostname`), via an unmodified
`ssl.create_default_context()`. It never follows a redirect (a caller
that needs one, e.g. the calendar feed's own hop-by-hop fetch, resolves
and pins each hop itself) and never honours an environment HTTP(S) proxy
-- `http.client.HTTPSConnection` is driven directly; nothing here reads
`HTTP_PROXY`/`HTTPS_PROXY`.

Both primitives raise exceptions that are also `requests.exceptions.
RequestException` (`DeadlineExceeded` a `requests.exceptions.Timeout`
subclass, `ResponseTooLarge` and `UnsafeDestination` plain
`RequestException`/`ConnectionError` subclasses), so every existing
`except requests.RequestException` / `except requests.Timeout` handler in
this codebase keeps working unchanged once a caller migrates onto these
primitives.

Kept as one small module for now; a future refactor is expected to absorb
it, plus `calendar_rules._url_is_safe`, into a shared `net/safe_fetch.py`.
"""

import collections
import http.client
import ipaddress
import socket
import ssl
import time
import urllib.parse

import requests


class DeadlineExceeded(requests.exceptions.Timeout):
    """A bounded call's total wall-clock deadline elapsed. A `requests.
    Timeout` subclass so an existing `except requests.Timeout` (or the
    broader `except requests.RequestException`) handler keeps working
    unchanged.
    """


class ResponseTooLarge(requests.exceptions.RequestException):
    """A streamed body exceeded its byte cap. Raised on the running byte
    count as chunks arrive, never on a declared `Content-Length` -- a body
    can lie about its own size.
    """


class UnsafeDestination(requests.exceptions.ConnectionError):
    """A URL/hostname was refused before, or instead of, connecting: a
    non-`https` scheme, a DNS resolution failure or empty answer, or a
    resolved address that is not a public unicast address. A `requests.
    exceptions.ConnectionError` subclass so an existing
    `except requests.RequestException` (or `except requests.exceptions.
    ConnectionError`) handler keeps working unchanged.
    """


FetchResult = collections.namedtuple("FetchResult", "status_code content headers")


_CHUNK_SIZE = 8192


def bounded_get(url, *, headers=None, timeout, deadline_s, max_bytes, clock=None):
    """GET `url` streamed, bound by a total wall-clock deadline
    (`deadline_s` seconds from this call's start) in addition to
    `timeout`'s own per-connect/per-read bound, and by `max_bytes` of
    response body.

    Raises `DeadlineExceeded` if the deadline has already passed when the
    response arrives, or after any chunk. Raises `ResponseTooLarge` once
    the running byte count exceeds `max_bytes` (a declared
    `Content-Length` is never trusted). Does not raise on a non-2xx
    status -- the caller decides what to do with it. Always closes the
    response, including when an exception is raised.

    The documented bound on a slow trickle: deadline + one read timeout --
    the chunk in flight when the deadline check fires can still take up to
    `timeout` to arrive (or fail) before `iter_content` yields control
    back here.

    `requests.get` is looked up on the `requests` module at call time
    (not imported directly as a name), so a test that monkeypatches
    `requests.get` (e.g. this project's `FakeProviders`) is honoured here
    too.
    """
    clock = clock or time.monotonic
    deadline = clock() + deadline_s

    response = requests.get(url, headers=headers, timeout=timeout, stream=True)
    try:
        if clock() > deadline:
            raise DeadlineExceeded(
                "bounded_get: deadline exceeded before any content was read"
            )
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
            total += len(chunk)
            if total > max_bytes:
                raise ResponseTooLarge(
                    "bounded_get: response exceeded %d bytes" % max_bytes
                )
            chunks.append(chunk)
            if clock() > deadline:
                raise DeadlineExceeded(
                    "bounded_get: deadline exceeded while reading the response"
                )
        return FetchResult(response.status_code, b"".join(chunks), response.headers)
    finally:
        response.close()


def address_is_public(ip_text):
    """`True` when `ip_text` parses as a public unicast address, `False`
    otherwise -- including on a parse failure.

    Same classification `calendar_rules._address_is_public` already uses:
    delegates range classification to `ipaddress` rather than hand-rolled
    CIDR arithmetic, so both IPv4 and IPv6 go through one call.
    """
    try:
        address = ipaddress.ip_address(ip_text)
    except (ValueError, TypeError):
        return False
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        return False
    return True


def resolve_public_addresses(hostname, port, resolver=None):
    """Resolve `hostname` exactly once (`resolver`, or `socket.getaddrinfo`
    looked up at call time) and return its addresses, de-duplicated in
    answer order, only if every one of them is a public unicast address.

    Raises `UnsafeDestination` on a resolution failure, an empty answer,
    or the first non-public address found -- a single private answer
    among several public ones refuses the whole hostname, since only the
    addresses actually returned can be checked (a hostname can resolve to
    a public address at check time and a private one at connect time --
    DNS rebinding -- so re-resolving later would defeat the check; this
    is why the caller must connect only to an address this function
    already returned, never resolve again).
    """
    getaddrinfo = resolver or socket.getaddrinfo
    try:
        infos = getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError) as exc:
        raise UnsafeDestination(
            "resolve_public_addresses: could not resolve %r" % (hostname,)
        ) from exc
    if not infos:
        raise UnsafeDestination(
            "resolve_public_addresses: %r resolved to no addresses" % (hostname,)
        )
    addresses = []
    for info in infos:
        address_text = info[4][0]
        if not address_is_public(address_text):
            raise UnsafeDestination(
                "resolve_public_addresses: %r resolved to a non-public "
                "address" % (hostname,)
            )
        if address_text not in addresses:
            addresses.append(address_text)
    return addresses


def _default_ssl_context():
    """`ssl.create_default_context()` unchanged -- hostname checking on,
    `CERT_REQUIRED`. A separate function so a test can patch it, or a
    caller can pass its own `ssl_context=` (e.g. a fake in tests).
    """
    return ssl.create_default_context()


_REDIRECT_STATUSES = (301, 302, 303, 307, 308)


class PinnedResponse:
    """A `pinned_request()` response: the `http.client.HTTPResponse`
    surface `calendar_rules.fetch_ics` and `notify.send_notification`
    need (`status_code`, `headers.get(...)`, `iter_content`, `close`),
    plus `is_redirect` and `getcode()`. Never follows a redirect itself --
    `is_redirect` only reports one is present.
    """

    def __init__(self, http_response, sock, *, deadline, clock, timeout):
        self._http_response = http_response
        self._sock = sock
        self._deadline = deadline
        self._clock = clock
        self._timeout = timeout
        self.status_code = http_response.status
        self.status = http_response.status
        self.reason = http_response.reason
        self.headers = http_response.headers
        self.is_redirect = (
            self.status_code in _REDIRECT_STATUSES
            and self.headers.get("Location") is not None
        )

    def iter_content(self, chunk_size=8192):
        """Yield the body in `chunk_size` reads. Before each read, clamps
        the underlying socket's timeout to `min(timeout, time left)` and
        raises `DeadlineExceeded` once no time is left -- the same total
        wall-clock bound `bounded_get` applies to a `requests` stream.
        """
        while True:
            time_left = self._deadline - self._clock()
            if time_left <= 0:
                raise DeadlineExceeded(
                    "PinnedResponse.iter_content: deadline exceeded"
                )
            self._sock.settimeout(min(self._timeout, time_left))
            chunk = self._http_response.read(chunk_size)
            if not chunk:
                return
            yield chunk

    def getcode(self):
        return self.status_code

    def close(self):
        self._http_response.close()


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """An `http.client.HTTPSConnection` whose `connect()` dials the one
    address `pinned_request` already resolved and checked, instead of
    resolving `self.host` again (the default `HTTPSConnection.connect()`
    calls `socket.create_connection((self.host, self.port), ...)`, which
    would re-resolve the hostname and could reach a different address --
    exactly the DNS-rebinding gap this module closes).
    """

    def __init__(self, hostname, port, pinned_address, *, timeout, create_connection, ssl_context):
        super().__init__(hostname, port, timeout=timeout)
        self._pinned_address = pinned_address
        self._create_connection = create_connection
        self._ssl_context = ssl_context

    def connect(self):
        sock = self._create_connection((self._pinned_address, self.port), self.timeout)
        self.sock = self._ssl_context.wrap_socket(sock, server_hostname=self.host)


def pinned_request(
    method,
    url,
    *,
    headers=None,
    body=None,
    timeout,
    deadline_s,
    resolver=None,
    create_connection=None,
    ssl_context=None,
    clock=None,
):
    """Issue one HTTPS request whose connection is pinned to an address
    `resolve_public_addresses` already checked -- the DNS answer the
    safety check saw is the address the socket connects to, always, since
    the hostname is never resolved a second time.

    `https` only (anything else raises `UnsafeDestination` immediately,
    without resolving). Tries each checked address in order, using the
    first that connects (a refused first address is not itself a safety
    failure -- it just means that address is not currently reachable);
    raises `UnsafeDestination` only if none connects. Never follows a
    redirect and never reads an environment HTTP(S) proxy.
    """
    clock = clock or time.monotonic
    create_connection = create_connection or socket.create_connection
    ssl_context = ssl_context or _default_ssl_context()
    deadline = clock() + deadline_s

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise UnsafeDestination(
            "pinned_request: only https is supported, got %r" % (parsed.scheme,)
        )
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeDestination("pinned_request: no hostname in %r" % (url,))
    port = parsed.port or 443

    addresses = resolve_public_addresses(hostname, port, resolver=resolver)

    path = parsed.path or "/"
    if parsed.query:
        path = path + "?" + parsed.query

    conn = None
    last_exc = None
    for address in addresses:
        time_left = deadline - clock()
        connect_timeout = min(timeout, time_left) if time_left > 0 else 0
        candidate = _PinnedHTTPSConnection(
            hostname,
            port,
            address,
            timeout=connect_timeout,
            create_connection=create_connection,
            ssl_context=ssl_context,
        )
        try:
            candidate.connect()
        except OSError as exc:
            last_exc = exc
            continue
        conn = candidate
        break
    if conn is None:
        raise UnsafeDestination(
            "pinned_request: could not connect to any checked address for %r"
            % (hostname,)
        ) from last_exc

    request_headers = dict(headers or {})
    request_headers["Host"] = hostname if port == 443 else "%s:%d" % (hostname, port)
    if body is not None:
        request_headers["Content-Length"] = str(len(body))

    try:
        time_left = deadline - clock()
        conn.sock.settimeout(min(timeout, time_left) if time_left > 0 else 0)
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for key, value in request_headers.items():
            conn.putheader(key, value)
        conn.endheaders(body)

        time_left = deadline - clock()
        conn.sock.settimeout(min(timeout, time_left) if time_left > 0 else 0)
        http_response = conn.getresponse()
    except BaseException:
        conn.close()
        raise

    return PinnedResponse(
        http_response, conn.sock, deadline=deadline, clock=clock, timeout=timeout
    )
