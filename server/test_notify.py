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
import os
import sys

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
# urlopen()). Re-derived by RUNNING the harness, not by arithmetic, per
# this repo's own documented discipline.
EXPECTED_CHECK_COUNT = 7


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

        class _FakeUrlopenResponse:
            status = 200

            def close(self):
                pass

        def fake_urlopen(request, timeout=None):
            captured["method"] = request.get_method()
            captured["title"] = request.get_header("Title")
            captured["content_type"] = request.get_header("Content-type")
            captured["data"] = request.data
            captured["timeout"] = timeout
            return _FakeUrlopenResponse()

        original_urlopen = notify.urllib.request.urlopen
        notify.urllib.request.urlopen = fake_urlopen
        try:
            notify.default_notify_transport("https://ntfy.sh/skypane-test", "Hello", "World", 5)
        finally:
            notify.urllib.request.urlopen = original_urlopen

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
        "default_notify_transport() builds a POST request with the body UTF-8 encoded, a Title header, and the caller's timeout, against a faked urlopen()",
        _default_transport_builds_the_expected_request,
    )

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("notify: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
