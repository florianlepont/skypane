#!/usr/bin/env python3
"""Contract tests for server/notify.py (D-25/D-27, 20-02-PLAN.md Task 2).

Every test below injects its own fake `transport(url, title, body, timeout)`,
mirroring `server/test_calendar_rules.py`'s own `make_calendar_transport()`
idiom (`fetch_ics(transport=...)`'s injection seam) - no test here ever
makes a real network call, and the SSRF test additionally asserts the
transport was never even invoked (a call counter staying at zero), pinning
that `send_notification()`'s own `_url_is_safe()` gate runs BEFORE any
attempt to reach the network (T-20-05).
"""
import io
import os
import socket
import sys
import urllib.request
from urllib.response import addinfourl

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.notify as notify  # noqa: E402

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
    """A hermetic stand-in for the response object
    `default_notify_transport()` would otherwise return from a real
    `urllib.request.urlopen()` call - built from a fixed status only,
    never a live call.
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


def test_default_transport_builds_the_expected_request(monkeypatch):
    captured = {}

    class _FakeOpener:
        def open(self, request, timeout=None):
            captured["method"] = request.get_method()
            captured["title"] = request.get_header("Title")
            captured["content_type"] = request.get_header("Content-type")
            captured["data"] = request.data
            captured["timeout"] = timeout
            return _FakeNotifyResponse(200)

    # CR-01 fix: default_notify_transport() now goes through
    # `_NO_REDIRECT_OPENER.open()`, not `urllib.request.urlopen()` - patch
    # the module's opener itself rather than `urlopen`.
    monkeypatch.setattr(notify, "_NO_REDIRECT_OPENER", _FakeOpener())

    notify.default_notify_transport("https://ntfy.sh/skypane-test", "Hello", "World", 5)

    assert captured.get("method") == "POST", "expected method POST, got %r" % (captured.get("method"),)
    assert captured.get("title") == "Hello", "expected Title header 'Hello', got %r" % (captured.get("title"),)
    assert captured.get("data") == b"World", "expected body b'World', got %r" % (captured.get("data"),)
    assert captured.get("timeout") == 5, "expected timeout 5, got %r" % (captured.get("timeout"),)


def test_no_redirect_handler_refuses_a_302_to_an_internal_address_and_never_fetches_it(monkeypatch):
    """default_notify_transport()'s _NoRedirectHandler refuses a 302 pointing at an internal address (169.254.169.254) outright - send_notification() returns False and the redirect target is never fetched."""
    # CR-01 fix (20-REVIEW.md): default_notify_transport() must never
    # automatically follow a redirect - a validated public HTTPS topic URL
    # can still answer with a 3xx pointing at an internal address (e.g.
    # http://169.254.169.254/...). This drives the REAL
    # default_notify_transport()/_NO_REDIRECT_OPENER wiring, not an
    # injected fake transport (which would bypass the fix entirely) - a
    # fake urllib handler stands in for the network layer only, one level
    # below the opener, mirroring server/test_calendar_rules.py's own
    # "assert the redirect target's call count stays at zero" style.
    calls = []
    internal_target = "http://169.254.169.254/latest/meta-data/"

    class _FakeRedirectingHandler(urllib.request.BaseHandler):
        # Lower than the real HTTPHandler/HTTPSHandler's default 500, so
        # this fake always answers first and no real socket is ever
        # opened.
        handler_order = 100

        def http_open(self, req):
            calls.append(req.full_url)
            resp = addinfourl(io.BytesIO(b""), {"location": internal_target}, req.full_url, 302)
            resp.msg = "Found"
            return resp

        https_open = http_open

    fake_opener = urllib.request.build_opener(_FakeRedirectingHandler(), notify._NoRedirectHandler())
    monkeypatch.setattr(notify, "_NO_REDIRECT_OPENER", fake_opener)

    ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b")

    assert ok is False, "expected send_notification() to return False for a 302 response, got %r" % (ok,)
    assert calls == ["https://ntfy.sh/skypane-test"], (
        "expected exactly one request (the original URL only) and the internal redirect target %r "
        "to never be fetched: %r" % (internal_target, calls)
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
