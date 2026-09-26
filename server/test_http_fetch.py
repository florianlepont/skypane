"""Behaviour tests for server/http_fetch.py: bounded_get's total
wall-clock deadline and byte cap over a streamed requests.get(), and
pinned_request's single-resolution, checked-address-only HTTPS
connection -- both proven without opening a real socket (fake resolver,
fake socket, fake SSL context).
"""

import io
import json
import socket
import ssl
import time as time_module

import pytest
import requests

from server import http_fetch


class _FakeStreamResponse:
    """Stands in for a requests.Response: only the bounded_get() surface
    (status_code, headers, iter_content, close). Each chunk yielded
    advances a shared fake clock by one second, simulating a slow
    trickle upstream one read at a time.
    """

    def __init__(self, clock_state, status_code=200, headers=None, chunk_count=20):
        self.status_code = status_code
        self.headers = headers if headers is not None else {}
        self.closed = False
        self.chunks_yielded = 0
        self._clock_state = clock_state
        self._chunk_count = chunk_count

    def iter_content(self, chunk_size=8192):
        for _ in range(self._chunk_count):
            self._clock_state["t"] += 1.0
            self.chunks_yielded += 1
            yield b"x"

    def close(self):
        self.closed = True


def _fixed_body_response(body_bytes, headers=None, status_code=200):
    class _Response:
        def __init__(self):
            self.status_code = status_code
            self.headers = headers if headers is not None else {}
            self.closed = False

        def iter_content(self, chunk_size=8192):
            yield body_bytes

        def close(self):
            self.closed = True

    return _Response()


def test_bounded_get_raises_deadline_exceeded_on_slow_trickle(monkeypatch):
    clock_state = {"t": 0.0}
    fake_response = _FakeStreamResponse(clock_state)
    monkeypatch.setattr(
        requests, "get", lambda *a, **k: fake_response
    )

    with pytest.raises(http_fetch.DeadlineExceeded):
        http_fetch.bounded_get(
            "https://example.invalid/data",
            timeout=2,
            deadline_s=5,
            max_bytes=1_000_000,
            clock=lambda: clock_state["t"],
        )

    assert fake_response.closed is True
    assert fake_response.chunks_yielded <= 6


def test_deadline_exceeded_is_a_requests_timeout_and_request_exception():
    assert issubclass(http_fetch.DeadlineExceeded, requests.exceptions.Timeout)
    assert issubclass(http_fetch.DeadlineExceeded, requests.exceptions.RequestException)


def test_response_too_large_is_a_request_exception():
    assert issubclass(http_fetch.ResponseTooLarge, requests.exceptions.RequestException)


def test_bounded_get_raises_response_too_large_ignoring_content_length(monkeypatch):
    fake = _fixed_body_response(b"x" * 11, headers={"Content-Length": "1"})
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    with pytest.raises(http_fetch.ResponseTooLarge):
        http_fetch.bounded_get(
            "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
        )

    assert fake.closed is True


def test_bounded_get_allows_exactly_max_bytes(monkeypatch):
    fake = _fixed_body_response(b"x" * 10)
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    result = http_fetch.bounded_get(
        "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
    )

    assert result.content == b"x" * 10
    assert result.status_code == 200
    assert fake.closed is True


@pytest.mark.parametrize("status", [404, 503])
def test_bounded_get_returns_non_2xx_without_raising(monkeypatch, status):
    fake = _fixed_body_response(b"", status_code=status)
    monkeypatch.setattr(requests, "get", lambda *a, **k: fake)

    result = http_fetch.bounded_get(
        "https://example.invalid/data", timeout=2, deadline_s=5, max_bytes=10
    )

    assert result.status_code == status
    assert fake.closed is True


def test_bounded_get_calls_requests_get_with_stream_and_timeout(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, timeout=None, stream=None):
        captured.update(url=url, headers=headers, timeout=timeout, stream=stream)
        return _fixed_body_response(b"ok")

    monkeypatch.setattr(requests, "get", fake_get)

    http_fetch.bounded_get(
        "https://example.invalid/data",
        headers={"X-Test": "1"},
        timeout=3,
        deadline_s=5,
        max_bytes=100,
    )

    assert captured["stream"] is True
    assert captured["timeout"] == 3
    assert captured["headers"] == {"X-Test": "1"}


def test_bounded_get_streams_fake_provider_response(fake_providers):
    result = http_fetch.bounded_get(
        "https://opendata.adsb.fi/v2/point/1/1/1",
        timeout=5,
        deadline_s=5,
        max_bytes=100_000,
    )

    assert result.status_code == 200
    assert result.content == json.dumps({"aircraft": []}).encode("utf-8")


# --- pinned_request fakes -------------------------------------------------
#
# No test here opens a real socket: the resolver, the socket
# create_connection() returns, and the SSL context are all fakes injected
# through pinned_request's own seams. The fake socket's makefile("rb")
# wraps a raw reader that hands back exactly one byte per readinto() call
# (io.BufferedReader forwards whatever the raw layer gives it, so a
# response.read(1) still triggers exactly one raw read) -- the response is
# parsed through http.client's own real status-line/header parser, the
# same code path production uses.


class _RawByteAtATimeReader(io.RawIOBase):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._pos = 0

    def readable(self):
        return True

    def readinto(self, b):
        if self._pos >= len(self._data):
            return 0
        b[0] = self._data[self._pos]
        self._pos += 1
        return 1


def _canned_response(status_line="HTTP/1.1 200 OK", headers=None, body=b""):
    headers = dict(headers) if headers is not None else {"Content-Length": str(len(body))}
    lines = [status_line] + ["%s: %s" % (k, v) for k, v in headers.items()]
    header_bytes = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
    return header_bytes + body


class _FakeSocket:
    """The object create_connection() returns and ssl_context.wrap_socket()
    is handed in these tests -- kept as one object throughout (the fake
    SSL context below returns it unchanged), since only its recorded
    calls matter, not a real TLS handshake.
    """

    def __init__(self, response_bytes):
        self.sent = b""
        self.timeouts = []
        self._response_bytes = response_bytes
        self.closed = False

    def sendall(self, data):
        self.sent += data

    def makefile(self, mode="r", *args, **kwargs):
        return io.BufferedReader(_RawByteAtATimeReader(self._response_bytes))

    def settimeout(self, value):
        self.timeouts.append(value)

    def close(self):
        self.closed = True


class _FakeSSLContext:
    def __init__(self):
        self.wrap_calls = []

    def wrap_socket(self, sock, server_hostname=None):
        self.wrap_calls.append({"sock": sock, "server_hostname": server_hostname})
        return sock


def _make_create_connection(socket_by_address, calls):
    def create_connection(address, timeout):
        calls.append({"address": address, "timeout": timeout})
        result = socket_by_address[address[0]]
        if isinstance(result, BaseException):
            raise result
        return result

    return create_connection


def _resolver_sequence(*answers):
    """A fake resolve_public_addresses() resolver: each call to the
    returned function consumes the next `answers` entry (a list of
    address strings), repeating the last one if called more times than
    `answers` has entries -- used to prove a second call would have seen a
    different (private) answer, while asserting the resolver was in fact
    called only once.
    """
    calls = []
    remaining = list(answers)

    def resolver(hostname, port, type=None):
        calls.append((hostname, port))
        current = remaining.pop(0) if remaining else answers[-1]
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port))
            for addr in current
        ]

    resolver.calls = calls
    return resolver


@pytest.mark.parametrize(
    "ip,expected",
    [
        ("8.8.8.8", True),
        ("127.0.0.1", False),
        ("10.0.0.1", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("0.0.0.0", False),
        ("not-an-ip", False),
    ],
)
def test_address_is_public(ip, expected):
    assert http_fetch.address_is_public(ip) is expected


def test_default_ssl_context_verifies_hostname_and_certificate():
    ctx = http_fetch._default_ssl_context()
    assert ctx.check_hostname is True
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_pinned_request_connects_to_checked_address_and_sends_request():
    resolver = _resolver_sequence(["93.184.216.34"], ["127.0.0.1"])
    fake_sock = _FakeSocket(_canned_response(body=b'{"ok": true}'))
    cc_calls = []
    create_connection = _make_create_connection(
        {"93.184.216.34": fake_sock}, cc_calls
    )

    result = http_fetch.pinned_request(
        "GET",
        "https://calendar.example/a.ics?token=x",
        timeout=5,
        deadline_s=5,
        resolver=resolver,
        create_connection=create_connection,
        ssl_context=_FakeSSLContext(),
    )

    assert cc_calls[0]["address"] == ("93.184.216.34", 443)
    assert len(resolver.calls) == 1
    assert result.status_code == 200
    assert fake_sock.sent.startswith(b"GET /a.ics?token=x HTTP/1.1")
    assert b"Host: calendar.example" in fake_sock.sent


def test_pinned_request_records_server_hostname_for_tls():
    resolver = _resolver_sequence(["93.184.216.34"])
    fake_sock = _FakeSocket(_canned_response(body=b"{}"))
    ssl_context = _FakeSSLContext()
    create_connection = _make_create_connection({"93.184.216.34": fake_sock}, [])

    http_fetch.pinned_request(
        "GET",
        "https://calendar.example/a.ics",
        timeout=5,
        deadline_s=5,
        resolver=resolver,
        create_connection=create_connection,
        ssl_context=ssl_context,
    )

    assert ssl_context.wrap_calls[0]["server_hostname"] == "calendar.example"


def test_pinned_request_refuses_when_any_resolved_address_is_private():
    resolver = _resolver_sequence(["93.184.216.34", "10.0.0.1"])
    cc_calls = []
    create_connection = _make_create_connection({}, cc_calls)

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "https://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
            create_connection=create_connection,
            ssl_context=_FakeSSLContext(),
        )

    assert cc_calls == []


def test_pinned_request_refuses_when_resolver_raises_gaierror():
    def resolver(hostname, port, type=None):
        raise socket.gaierror("nope")

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "https://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
        )


def test_pinned_request_refuses_when_resolver_returns_no_addresses():
    def resolver(hostname, port, type=None):
        return []

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "https://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
        )


def test_pinned_request_refuses_non_https_scheme_without_resolving():
    resolver = _resolver_sequence(["93.184.216.34"])

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "http://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
        )

    assert resolver.calls == []


def test_pinned_request_tries_next_address_on_connection_refused():
    resolver = _resolver_sequence(["93.184.216.1", "93.184.216.2"])
    good_sock = _FakeSocket(_canned_response(body=b"{}"))
    cc_calls = []
    create_connection = _make_create_connection(
        {"93.184.216.1": ConnectionRefusedError(), "93.184.216.2": good_sock},
        cc_calls,
    )

    result = http_fetch.pinned_request(
        "GET",
        "https://calendar.example/a.ics",
        timeout=5,
        deadline_s=5,
        resolver=resolver,
        create_connection=create_connection,
        ssl_context=_FakeSSLContext(),
    )

    assert [c["address"][0] for c in cc_calls] == ["93.184.216.1", "93.184.216.2"]
    assert result.status_code == 200


def test_pinned_request_returns_redirect_without_following():
    resolver = _resolver_sequence(["93.184.216.34"])
    fake_sock = _FakeSocket(
        _canned_response(
            status_line="HTTP/1.1 302 Found",
            headers={
                "Location": "https://calendar.example/b.ics",
                "Content-Length": "0",
            },
        )
    )
    cc_calls = []
    create_connection = _make_create_connection(
        {"93.184.216.34": fake_sock}, cc_calls
    )

    result = http_fetch.pinned_request(
        "GET",
        "https://calendar.example/a.ics",
        timeout=5,
        deadline_s=5,
        resolver=resolver,
        create_connection=create_connection,
        ssl_context=_FakeSSLContext(),
    )

    assert result.is_redirect is True
    assert result.headers.get("Location") == "https://calendar.example/b.ics"
    assert len(cc_calls) == 1


def test_pinned_request_post_sends_body_and_content_length():
    resolver = _resolver_sequence(["93.184.216.34"])
    fake_sock = _FakeSocket(_canned_response(body=b"{}"))
    create_connection = _make_create_connection({"93.184.216.34": fake_sock}, [])
    body = b'{"title": "hi"}'

    result = http_fetch.pinned_request(
        "POST",
        "https://ntfy.example/topic",
        timeout=5,
        deadline_s=5,
        body=body,
        headers={"Content-Type": "application/json"},
        resolver=resolver,
        create_connection=create_connection,
        ssl_context=_FakeSSLContext(),
    )

    assert fake_sock.sent.startswith(b"POST /topic HTTP/1.1")
    assert ("Content-Length: %d" % len(body)).encode() in fake_sock.sent
    assert fake_sock.sent.endswith(body)
    assert result.status_code == 200


def test_pinned_response_iter_content_raises_deadline_exceeded_and_bounds_settimeout():
    """Direct PinnedResponse construction (bypassing pinned_request's own
    connect/request machinery) isolates iter_content's own deadline and
    settimeout-clamping behaviour from response parsing.
    """
    clock_state = {"t": 0.0}

    def clock():
        return clock_state["t"]

    class _TrickleBody:
        status = 200
        reason = "OK"
        headers = {}

        def read(self, n):
            clock_state["t"] += 1.0
            return b"x"

        def close(self):
            pass

    class _Sock:
        def __init__(self):
            self.timeouts = []

        def settimeout(self, value):
            self.timeouts.append(value)

    read_timeout = 2
    deadline_s = 5
    sock = _Sock()
    response = http_fetch.PinnedResponse(
        _TrickleBody(), sock, deadline=clock() + deadline_s, clock=clock, timeout=read_timeout,
    )

    chunks = []
    with pytest.raises(http_fetch.DeadlineExceeded):
        for chunk in response.iter_content(chunk_size=1):
            chunks.append(chunk)

    assert len(chunks) == deadline_s
    assert all(t <= read_timeout for t in sock.timeouts)
    assert all(t > 0 for t in sock.timeouts)


def test_bounded_get_raises_deadline_exceeded_before_any_content_is_read(monkeypatch):
    """The deadline can already be gone when the response arrives (a slow
    connect/handshake ate the whole budget) -- no chunk needs to be read
    for this to fire.
    """
    clock_state = {"t": 0.0}

    class _AlreadyLateResponse:
        status_code = 200
        headers = {}

        def __init__(self):
            self.closed = False
            self.iter_content_called = False

        def iter_content(self, chunk_size=8192):
            self.iter_content_called = True
            yield b"too late"

        def close(self):
            self.closed = True

    fake = _AlreadyLateResponse()

    def fake_get(url, headers=None, timeout=None, stream=None):
        clock_state["t"] = 999.0  # the "connect" consumed the whole deadline
        return fake

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(http_fetch.DeadlineExceeded):
        http_fetch.bounded_get(
            "https://example.invalid/data",
            timeout=2,
            deadline_s=5,
            max_bytes=100,
            clock=lambda: clock_state["t"],
        )

    assert fake.closed is True
    assert fake.iter_content_called is False


def test_pinned_response_getcode_and_close_and_normal_completion():
    class _Body:
        status = 200
        reason = "OK"
        headers = {}

        def __init__(self, chunks):
            self._chunks = list(chunks)
            self.closed = False

        def read(self, n):
            return self._chunks.pop(0) if self._chunks else b""

        def close(self):
            self.closed = True

    class _Sock:
        def settimeout(self, value):
            pass

    body = _Body([b"a", b"b", b""])
    response = http_fetch.PinnedResponse(
        body, _Sock(), deadline=time_module.monotonic() + 60, clock=time_module.monotonic, timeout=5,
    )

    assert response.getcode() == 200
    assert list(response.iter_content(chunk_size=1)) == [b"a", b"b"]

    response.close()
    assert body.closed is True


def test_pinned_request_closes_connection_on_request_failure():
    class _FailingSocket(_FakeSocket):
        def sendall(self, data):
            raise BrokenPipeError("write failed")

    resolver = _resolver_sequence(["93.184.216.34"])
    fake_sock = _FailingSocket(_canned_response(body=b"{}"))
    create_connection = _make_create_connection({"93.184.216.34": fake_sock}, [])

    with pytest.raises(BrokenPipeError):
        http_fetch.pinned_request(
            "GET",
            "https://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
            create_connection=create_connection,
            ssl_context=_FakeSSLContext(),
        )

    assert fake_sock.closed is True


def test_pinned_request_refuses_url_with_no_hostname():
    resolver = _resolver_sequence(["93.184.216.34"])

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "https:///no-host",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
        )

    assert resolver.calls == []


def test_pinned_request_refuses_when_every_checked_address_refuses():
    resolver = _resolver_sequence(["93.184.216.1", "93.184.216.2"])
    create_connection = _make_create_connection(
        {
            "93.184.216.1": ConnectionRefusedError(),
            "93.184.216.2": ConnectionRefusedError(),
        },
        [],
    )

    with pytest.raises(http_fetch.UnsafeDestination):
        http_fetch.pinned_request(
            "GET",
            "https://calendar.example/a.ics",
            timeout=5,
            deadline_s=5,
            resolver=resolver,
            create_connection=create_connection,
            ssl_context=_FakeSSLContext(),
        )
