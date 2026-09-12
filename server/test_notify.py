#!/usr/bin/env python3
"""Contract harness for server/notify.py (D-25/D-27, 20-02-PLAN.md Task 2).

Stdlib-only. Every check below injects its own fake `transport(url, title,
body, timeout)`, mirroring `server/test_calendar_rules.py`'s own
`make_calendar_transport()` idiom (`fetch_ics(transport=...)`'s injection
seam) — no check here ever makes a real network call, and the four SSRF
checks additionally assert the transport was never even invoked (a call
counter staying at zero), pinning that `send_notification()`'s own
`_url_is_safe()` gate runs BEFORE any attempt to reach the network
(T-20-05).

Exits 0 only when every check below passes.

Usage:
    server/.venv/bin/python3 server/test_notify.py
"""
import io
import os
import sys
import urllib.request
from urllib.response import addinfourl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Initial value for this file, introduced by 20-02-PLAN.md Task 2 (D-25's
# SSRF-gated, never-raising, transport-injectable notification sender: a
# success/failure/timeout/arbitrary-exception quartet against
# send_notification(), four SSRF-refusal cases proving the transport is
# never reached, a body_for_lang() round trip, and a
# default_notify_transport() request-shape check against a faked
# opener). CR-01 fix (20-REVIEW.md) added one more: a fake urllib
# handler proving a 302 to an internal address is refused by
# `_NoRedirectHandler` and never actually fetched. Re-derived by
# RUNNING the harness, not by arithmetic, per this repo's own
# documented discipline.
EXPECTED_CHECK_COUNT = 8


class _FakeNotifyResponse:
    """A hermetic stand-in for the response object
    `default_notify_transport()` would otherwise return from a real
    `urllib.request.urlopen()` call — built from a fixed status only,
    never a live call.
    """

    def __init__(self, status=200):
        self.status = status
        self.closed = False

    def close(self):
        self.closed = True


def make_notify_transport(status=200, raise_exc=None, calls=None):
    """Build a fake transport matching `send_notification()`'s injectable
    `transport(url, title, body, timeout)` contract. Records every URL
    it was invoked with (when `calls` is supplied), or raises `raise_exc`
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


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.notify as notify
    except ImportError as exc:
        print("FAIL import server.notify - %r" % (exc,))
        print("notify: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    def _success_response_returns_true():
        transport = make_notify_transport(status=200)
        ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
        if ok is not True:
            return False, "expected True for a 200 response, got %r" % (ok,)
        return True, ""

    check("send_notification() returns True for a 200 response from the injected transport", _success_response_returns_true)

    def _non_2xx_response_returns_false():
        transport = make_notify_transport(status=500)
        ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
        if ok is not False:
            return False, "expected False for a 500 response, got %r" % (ok,)
        return True, ""

    check("send_notification() returns False for a 500 response from the injected transport", _non_2xx_response_returns_false)

    def _timeout_never_propagates():
        transport = make_notify_transport(raise_exc=TimeoutError("simulated timeout"))
        ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
        if ok is not False:
            return False, "expected False when the transport raises TimeoutError, got %r" % (ok,)
        return True, ""

    check("send_notification() returns False (never raises) when the transport raises TimeoutError", _timeout_never_propagates)

    def _arbitrary_exception_never_propagates():
        transport = make_notify_transport(raise_exc=RuntimeError("simulated failure"))
        ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b", transport=transport)
        if ok is not False:
            return False, "expected False when the transport raises an arbitrary exception, got %r" % (ok,)
        return True, ""

    check("send_notification() returns False (never raises) when the transport raises an arbitrary Exception", _arbitrary_exception_never_propagates)

    def _ssrf_gate_refuses_before_ever_calling_the_transport():
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
            if ok is not False:
                return False, "send_notification(%r, ...) returned %r, expected False" % (url, ok)
            if calls:
                return False, "send_notification(%r, ...) reached the transport (calls=%r) - the SSRF gate must refuse before any network attempt" % (url, calls)
        return True, ""

    check(
        "send_notification() returns False for a loopback, a localhost, a link-local cloud-metadata, and a file:// topic URL, without the injected transport ever being called",
        _ssrf_gate_refuses_before_ever_calling_the_transport,
    )

    def _body_for_lang_returns_french_or_falls_back_to_english():
        expected_fr = "Batterie revenue à la normale"
        got_fr = notify.body_for_lang(notify.BATTERY_OK_BODY, "fr")
        if got_fr != expected_fr:
            return False, "body_for_lang(BATTERY_OK_BODY, 'fr') returned %r, expected %r" % (got_fr, expected_fr)
        for other_lang in ("en", "de", None, ""):
            got = notify.body_for_lang(notify.BATTERY_OK_BODY, other_lang)
            if got != notify.BATTERY_OK_BODY:
                return False, "body_for_lang(BATTERY_OK_BODY, %r) returned %r, expected the English source string unchanged" % (other_lang, got)
        return True, ""

    check(
        "body_for_lang() returns the French form for 'fr' and the English source string unchanged for every other language argument",
        _body_for_lang_returns_french_or_falls_back_to_english,
    )

    def _default_transport_builds_the_expected_request():
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
        # `_NO_REDIRECT_OPENER.open()`, not `urllib.request.urlopen()` -
        # patch the module's opener itself rather than `urlopen`.
        original_opener = notify._NO_REDIRECT_OPENER
        notify._NO_REDIRECT_OPENER = _FakeOpener()
        try:
            notify.default_notify_transport("https://ntfy.sh/skypane-test", "Hello", "World", 5)
        finally:
            notify._NO_REDIRECT_OPENER = original_opener

        if captured.get("method") != "POST":
            return False, "expected method POST, got %r" % (captured.get("method"),)
        if captured.get("title") != "Hello":
            return False, "expected Title header 'Hello', got %r" % (captured.get("title"),)
        if captured.get("data") != b"World":
            return False, "expected body b'World', got %r" % (captured.get("data"),)
        if captured.get("timeout") != 5:
            return False, "expected timeout 5, got %r" % (captured.get("timeout"),)
        return True, ""

    check(
        "default_notify_transport() builds a POST request with the body UTF-8 encoded, a Title header, and the caller's timeout, against a faked opener",
        _default_transport_builds_the_expected_request,
    )

    # CR-01 fix (20-REVIEW.md): default_notify_transport() must never
    # automatically follow a redirect - a validated public HTTPS topic
    # URL can still answer with a 3xx pointing at an internal address
    # (e.g. http://169.254.169.254/...). This drives the REAL
    # default_notify_transport()/_NO_REDIRECT_OPENER wiring, not an
    # injected fake transport (which would bypass the fix entirely) -
    # a fake urllib handler stands in for the network layer only, one
    # level below the opener, mirroring server/test_calendar_rules.py's
    # own "assert the redirect target's call count stays at zero" style.
    def _redirect_to_internal_address_refused_and_never_fetched():
        calls = []
        internal_target = "http://169.254.169.254/latest/meta-data/"

        class _FakeRedirectingHandler(urllib.request.BaseHandler):
            # Lower than the real HTTPHandler/HTTPSHandler's default 500,
            # so this fake always answers first and no real socket is
            # ever opened.
            handler_order = 100

            def http_open(self, req):
                calls.append(req.full_url)
                resp = addinfourl(io.BytesIO(b""), {"location": internal_target}, req.full_url, 302)
                resp.msg = "Found"
                return resp

            https_open = http_open

        fake_opener = urllib.request.build_opener(_FakeRedirectingHandler(), notify._NoRedirectHandler())
        original_opener = notify._NO_REDIRECT_OPENER
        notify._NO_REDIRECT_OPENER = fake_opener
        try:
            ok = notify.send_notification("https://ntfy.sh/skypane-test", "t", "b")
        finally:
            notify._NO_REDIRECT_OPENER = original_opener

        if ok is not False:
            return False, "expected send_notification() to return False for a 302 response, got %r" % (ok,)
        if calls != ["https://ntfy.sh/skypane-test"]:
            return False, (
                "expected exactly one request (the original URL only) and the internal redirect "
                "target %r to never be fetched: %r" % (internal_target, calls)
            )
        return True, ""

    check(
        "default_notify_transport()'s _NoRedirectHandler refuses a 302 pointing at an internal "
        "address (169.254.169.254) outright - send_notification() returns False and the redirect "
        "target is never fetched",
        _redirect_to_internal_address_refused_and_never_fetched,
    )

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("notify: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
