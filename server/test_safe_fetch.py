#!/usr/bin/env python3
"""Contract tests for server/net/safe_fetch.py - the one SSRF gate the
calendar feed fetch (server/plane/calendar_rules.py) calls.

Every test here fakes socket.getaddrinfo() rather than making a real DNS
lookup or network call, the same technique server/test_calendar_rules.py
uses for its own (now-moved) copy of these tests.
"""
import os
import socket
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# A real public unicast IPv4 address (no DNS lookup needed - urlparse()
# already sees a literal IP as the hostname, and socket.getaddrinfo()
# resolves a dotted-decimal literal without ever touching the network).
# Only its RANGE classification matters here, never actually connected to.
PUBLIC_IP = "93.184.216.34"

from server.net import safe_fetch  # noqa: E402
from server.plane import calendar_rules  # noqa: E402


def test_non_https_scheme_refused():
    """url_is_safe() refuses a non-https scheme (http, ftp, file, and a schemeless string)"""
    for bad in ("http://example.com/x", "http://%s/a.ics" % PUBLIC_IP,
                "ftp://%s/a.ics" % PUBLIC_IP, "file:///etc/passwd", "not-a-url"):
        if safe_fetch.url_is_safe(bad) is not False:
            pytest.fail("expected url_is_safe(%r) to be False" % (bad,))


def test_no_hostname_refused():
    """url_is_safe() refuses a URL with no hostname"""
    if safe_fetch.url_is_safe("https:///a.ics") is not False:
        pytest.fail("expected a hostless https URL to be refused")


def test_address_gate_refuses_every_unsafe_range():
    """url_is_safe() refuses loopback (v4/v6), three private ranges, the link-local metadata address, and a reserved address"""
    unsafe = (
        "https://127.0.0.1/a.ics",        # loopback v4
        "https://[::1]/a.ics",             # loopback v6
        "https://10.0.0.5/a.ics",          # private (RFC 1918)
        "https://172.16.0.1/a.ics",        # private (RFC 1918)
        "https://192.168.1.1/a.ics",       # private (RFC 1918)
        "https://169.254.169.254/a.ics",   # link-local (cloud metadata)
        "https://240.0.0.1/a.ics",         # reserved (Class E)
    )
    for url in unsafe:
        if safe_fetch.url_is_safe(url) is not False:
            pytest.fail("expected url_is_safe(%r) to be False" % (url,))


def test_unresolvable_hostname_refused(monkeypatch):
    """url_is_safe() refuses a hostname that fails to resolve at all"""
    def fake_getaddrinfo(host, *a, **k):
        raise socket.gaierror("simulated resolution failure for %r" % (host,))

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    if safe_fetch.url_is_safe("https://this-genuinely-does-not-resolve.invalid/a.ics") is not False:
        pytest.fail("expected an unresolvable hostname to be refused")


def test_hostname_resolving_only_to_a_private_address_refused(monkeypatch):
    """url_is_safe() refuses an https URL whose hostname resolves only to a private address"""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: [
        (2, 1, 6, "", ("10.0.0.1", 443)),
    ])
    if safe_fetch.url_is_safe("https://public-looking-name.example/a.ics") is not False:
        pytest.fail("expected a hostname resolving only to a private address to be refused")


def test_mixed_address_answer_refused(monkeypatch):
    """url_is_safe() refuses a hostname whose resolved addresses are a MIX of public and private - the DNS-rebinding case a hostname-only check would miss"""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: [
        (2, 1, 6, "", (PUBLIC_IP, 443)),
        (2, 1, 6, "", ("10.1.2.3", 443)),
    ])
    if safe_fetch.url_is_safe("https://public-looking-name.example/a.ics") is not False:
        pytest.fail("a hostname resolving to one private address among public ones must be refused")


def test_all_public_answer_accepted(monkeypatch):
    """url_is_safe() accepts a hostname when every resolved address is public"""
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port=None, *a, **k: [
        (2, 1, 6, "", (PUBLIC_IP, 443)),
    ])
    if safe_fetch.url_is_safe("https://public-looking-name.example/a.ics") is not True:
        pytest.fail("a hostname resolving to only public addresses should be accepted")


def test_calendar_rules_url_is_safe_is_the_same_function_object():
    """calendar_rules._url_is_safe is safe_fetch.url_is_safe by identity, not merely equivalent behaviour"""
    assert calendar_rules._url_is_safe is safe_fetch.url_is_safe, (
        "expected calendar_rules._url_is_safe and safe_fetch.url_is_safe to be the identical "
        "function object (one SSRF gate, not two copies)"
    )


def test_calendar_rules_user_agent_is_the_same_string_object():
    """calendar_rules.USER_AGENT is safe_fetch.USER_AGENT - one identification string, not a duplicate"""
    assert calendar_rules.USER_AGENT is safe_fetch.USER_AGENT, (
        "expected calendar_rules.USER_AGENT and safe_fetch.USER_AGENT to be the identical object"
    )


