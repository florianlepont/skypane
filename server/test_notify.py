#!/usr/bin/env python3
"""Contract tests for server/notify.py.

Most tests below inject a fake `transport(url, title, body, timeout)`,
mirroring `server/test_calendar_rules.py`'s own `make_calendar_transport()`
idiom (`fetch_ics(transport=...)`'s injection seam) - no test here ever
makes a real network call, and the SSRF test additionally asserts the
transport was never even invoked (a call counter staying at zero), pinning
that `send_notification()`'s own `_url_is_safe()` gate runs BEFORE any
attempt to reach the network.

The tests exercising the REAL `default_notify_transport()` (the pinned
connection itself) use `server/test_http_fetch.py`'s own fake-socket
technique: a byte-at-a-time raw reader wrapped in `io.BufferedReader` so
the response is parsed through `http.client`'s real status-line/header
parser, and a fake SSL context recording `wrap_socket()` calls - no test
here opens a real socket either way.
"""
import io
import os
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.notify as notify  # noqa: E402
from server import http_fetch  # noqa: E402

# send_notification()'s first line is calendar_rules._url_is_safe(), which
# for a real "https://ntfy.sh/..." topic URL does a genuine
# socket.getaddrinfo("ntfy.sh", ...) DNS lookup as part of its SSRF
# public-address check (server/plane/calendar_rules.py:_host_is_safe()).
# conftest.py's non-loopback DNS guard correctly blocks that lookup in
# every test - stub it with a fixed, real, public IP (the historical
# example.com/example.org address, never actually connected to: every
# test below either injects its own fake transport or fakes the opener
# one level below it) so the SSRF gate itself still runs and still
# passes, rather than being bypassed outright.
_NTFY_SH_PUBLIC_ADDRINFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
]


@pytest.fixture(autouse=True)
def _stub_ntfy_sh_dns(monkeypatch):
    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, *args, **kwargs):
        if host == "ntfy.sh":
            return _NTFY_SH_PUBLIC_ADDRINFO
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


class _FakeNotifyResponse:
    """A hermetic stand-in for the `http_fetch.PinnedResponse`
    `default_notify_transport()` would otherwise return from a real
    call - built from a fixed status only, never a live call.
    """

    def __init__(self, status=200):
        self.status = status
        self.closed = False

    def close(self):
        self.closed = True


def make_notify_transport(status=200, raise_exc=None, calls=None):
    """Build a fake transport matching `send_notification()`'s injectable
    `transport(url, title, body, timeout)` contract. Records every URL it
    was invoked with (when `calls` is supplied), or raises `raise_exc`
    instead of returning, simulating a transport failure without ever
    touching a real socket.
    """

    def transport(url, title, body, timeout):
        if calls is not None:
            calls.append(url)
        if raise_exc is not None:
            raise raise_exc
        return _FakeNotifyResponse(status)

    return transport


def test_send_notification_returns_true_for_a_200_response_from_the_injected_transport():
    transport = make_notify_transport(status=200)
    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
    assert ok is True, "expected True for a 200 response, got %r" % (ok,)


def test_send_notification_returns_false_for_a_500_response_from_the_injected_transport():
    transport = make_notify_transport(status=500)
    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
    assert ok is False, "expected False for a 500 response, got %r" % (ok,)


def test_send_notification_returns_false_never_raises_when_the_transport_raises_timeout_error():
    transport = make_notify_transport(raise_exc=TimeoutError("simulated timeout"))
    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
    assert ok is False, "expected False when the transport raises TimeoutError, got %r" % (ok,)


def test_send_notification_returns_false_never_raises_when_the_transport_raises_an_arbitrary_exception():
    transport = make_notify_transport(raise_exc=RuntimeError("simulated failure"))
    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
    assert ok is False, "expected False when the transport raises an arbitrary exception, got %r" % (ok,)


def test_ssrf_gate_refuses_before_ever_calling_the_transport():
    """send_notification() returns False for a loopback, a localhost, a link-local cloud-metadata, and a file:// topic URL, without the injected transport ever being called."""
    hostile_urls = (
        "http://127.0.0.1:8080/x",
        "http://localhost/x",
        "http://169.254.169.254/latest/",
        "file:///etc/passwd",
    )
    for url in hostile_urls:
        calls = []
        transport = make_notify_transport(status=200, calls=calls)
        ok = notify.send_notification(url, "t", "b", transport=transport)
        assert ok is False, "send_notification(%r, ...) returned %r, expected False" % (url, ok)
        assert not calls, (
            "send_notification(%r, ...) reached the transport (calls=%r) - the SSRF gate must refuse "
            "before any network attempt" % (url, calls)
        )


# --- Fakes for the real default_notify_transport() -> http_fetch.
# pinned_request() path (no injected transport) - server/test_http_fetch.
# py's own technique: a byte-at-a-time raw reader wrapped in io.
# BufferedReader (so the response is parsed through http.client's real
# status-line/header parser) and a fake SSL context recording
# wrap_socket() calls, rather than a hand-rolled response stub.


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


def _canned_pinned_response(status_line="HTTP/1.1 200 OK", headers=None, body=b""):
    headers = dict(headers) if headers is not None else {"Content-Length": str(len(body))}
    lines = [status_line] + ["%s: %s" % (k, v) for k, v in headers.items()]
    header_bytes = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
    return header_bytes + body


class _FakePinnedSocket:
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


class _FakePinnedSSLContext:
    def __init__(self):
        self.wrap_calls = []

    def wrap_socket(self, sock, server_hostname=None):
        self.wrap_calls.append({"sock": sock, "server_hostname": server_hostname})
        return sock


def test_default_transport_builds_the_expected_request(monkeypatch):
    """default_notify_transport(), with no injected fake, connects through http_fetch.pinned_request(): the checked public address (from the autouse ntfy.sh DNS stub) is the one create_connection() is called with, the request line and headers carry the POST/Title/Content-Type this module builds, and the body bytes are sent."""
    fake_sock = _FakePinnedSocket(_canned_pinned_response(body=b""))
    cc_calls = []

    def fake_create_connection(address, timeout):
        cc_calls.append(address)
        return fake_sock

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(http_fetch, "_default_ssl_context", lambda: _FakePinnedSSLContext())

    response = notify.default_notify_transport("https://ntfy.sh/skypane-test", "Hello", "World", 5)

    assert cc_calls == [("93.184.216.34", 443)], "expected the checked public address, got %r" % (cc_calls,)
    assert response.status_code == 200, "expected a 200 response, got %r" % (response.status_code,)
    assert fake_sock.sent.startswith(b"POST /skypane-test HTTP/1.1"), (
        "expected a POST request line, got %r" % (fake_sock.sent[:40],))
    assert b"Title: Hello" in fake_sock.sent
    assert b"Content-Type: text/plain; charset=utf-8" in fake_sock.sent
    assert fake_sock.sent.endswith(b"World"), "expected the body bytes sent, got %r" % (fake_sock.sent[-20:],)


def test_no_redirect_handler_refuses_a_302_to_an_internal_address_and_never_fetches_it(monkeypatch):
    """default_notify_transport() never follows a redirect itself (http_fetch.pinned_request()'s own contract): a 302 pointing at an internal address (169.254.169.254) comes back unfollowed, send_notification() returns False, and only the ONE connection to the checked public address is ever made - the internal redirect target is never resolved or connected to."""
    fake_sock = _FakePinnedSocket(_canned_pinned_response(
        status_line="HTTP/1.1 302 Found",
        headers={"Location": "http://169.254.169.254/latest/meta-data/", "Content-Length": "0"},
    ))
    cc_calls = []

    def fake_create_connection(address, timeout):
        cc_calls.append(address)
        return fake_sock

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(http_fetch, "_default_ssl_context", lambda: _FakePinnedSSLContext())

    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b")

    assert ok is False, "expected send_notification() to return False for a 302 response, got %r" % (ok,)
    assert cc_calls == [("93.184.216.34", 443)], (
        "expected exactly one connection (the checked public address only) - the internal "
        "redirect target must never be connected to: %r" % (cc_calls,)
    )


def test_default_transport_passes_the_notify_deadline_to_pinned_request(monkeypatch):
    """default_notify_transport() passes NOTIFY_DEADLINE_S as pinned_request()'s deadline_s, alongside the POST method, the caller's timeout, and the Title/body it builds - proving the notify POST is bounded by the same total-wall-clock-deadline primitive the calendar fetch uses."""
    captured = {}

    def fake_pinned_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured.update(kwargs)
        return _FakeNotifyResponse(200)

    monkeypatch.setattr(http_fetch, "pinned_request", fake_pinned_request)

    notify.default_notify_transport("https://ntfy.sh/skypane-test", "Hello", "World", 5)

    assert captured["method"] == "POST"
    assert captured["url"] == "https://ntfy.sh/skypane-test"
    assert captured["timeout"] == 5
    assert captured["deadline_s"] == notify.NOTIFY_DEADLINE_S
    assert captured["headers"]["Title"] == "Hello"
    assert captured["body"] == b"World"


def test_body_for_lang_returns_french_or_falls_back_to_english():
    expected_fr = "Batterie revenue à la normale"
    got_fr = notify.body_for_lang(notify.BATTERY_OK_BODY, "fr")
    assert got_fr == expected_fr, "body_for_lang(BATTERY_OK_BODY, 'fr') returned %r, expected %r" % (got_fr, expected_fr)
    for other_lang in ("en", "de", None, ""):
        got = notify.body_for_lang(notify.BATTERY_OK_BODY, other_lang)
        assert got == notify.BATTERY_OK_BODY, (
            "body_for_lang(BATTERY_OK_BODY, %r) returned %r, expected the English source string unchanged"
            % (other_lang, got)
        )



