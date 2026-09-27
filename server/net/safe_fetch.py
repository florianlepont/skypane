"""The single SSRF gate for user-configured outbound URLs.

Both the calendar feed URL (`server.plane.calendar_rules`) and the ntfy
topic URL (`server.notify`) are operator-chosen, attacker-reachable
destinations, so both call `url_is_safe()` before any network attempt is
made. This module holds that one gate rather than each leaf module
carrying its own copy.

`url_is_safe()`'s own resolve-then-check is an early, cheap refusal
only; the actual protection against a changed DNS answer (DNS rebinding)
is that both callers go through `http_fetch.pinned_request()`, which
resolves once more of its own accord, checks every address that second
resolution returns, and connects only to one it already checked -- never
re-resolving between the check and the connect.
"""
from __future__ import annotations

import socket
from urllib.parse import urlparse

from server import http_fetch

# Self-identification for this module's callers' one outbound call each,
# matching detect.py's/enrich.py's own USER_AGENT convention.
USER_AGENT = (
    "skypane-server/0.1 "
    "(hobby project, Phase 16 calendar-linked flight highlighting; "
    "see server/README.md for what this traffic is)"
)


def _address_is_public(ip_text: str) -> bool:
    """`True` when `ip_text` parses as a public unicast address, `False`
    otherwise -- including on a parse failure.

    Delegates to `http_fetch.address_is_public()` -- the identical
    classification `pinned_request()`'s own resolution check applies, so
    this early gate and the real connection agree by construction on
    what counts as public.
    """
    return http_fetch.address_is_public(ip_text)


def host_is_safe(hostname: str, port: int | None = None) -> bool:
    """`True` only when every address `hostname` resolves to is a public
    unicast address; `False` on a resolution failure or if even one
    resolved address is not public.

    An early refusal only -- this resolution is never reused by the real
    connection. The actual protection against a changed DNS answer (DNS
    rebinding) is that the real transport goes through `http_fetch`'s
    own pinned request primitive, which resolves once more of its own
    accord, checks every address that second resolution returns, and
    connects only to one it already checked -- never re-resolving
    between the check and the connect. This function's own
    resolve-then-check is still useful as a cheap, early "obviously
    unsafe" refusal (e.g. a literal loopback/private/link-local address
    needs no network fetch to reject), and every redirect hop a caller
    follows repeats it before ever calling the transport. Never raises.
    """
    try:
        infos = socket.getaddrinfo(hostname, port)
    except (socket.gaierror, UnicodeError, OSError):
        return False
    if not infos:
        return False
    for info in infos:
        sockaddr = info[4]
        address_text = sockaddr[0]
        if not _address_is_public(address_text):
            return False
    return True


def url_is_safe(url: str) -> bool:
    """`True` only when `url`'s scheme is exactly `https`, it has a
    hostname, and `host_is_safe()` accepts every address that hostname
    resolves to. Never raises.

    Deliberately does not recognise `webcal` or any non-`https` scheme --
    a caller with its own scheme convention (e.g. the calendar feed's
    `webcal://`) normalises that away before ever reaching this gate,
    keeping "acceptable scheme" defined in one place.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme != "https":
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    return host_is_safe(hostname, port)
