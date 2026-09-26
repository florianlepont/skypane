"""Bounded outbound HTTP for SkyPane's own outgoing calls.

`bounded_get` adds a total wall-clock deadline over a streamed
`requests.get()`, on top of `timeout`'s own per-connect/per-read bound --
`requests`' `timeout=` never bounds the whole transfer, so one slow
upstream trickling one byte at a time can otherwise hang a call (and the
poll cycle that made it) indefinitely. It also caps the response body by
a running byte count, never trusting a declared `Content-Length` (a body
can lie about its own size).

`pinned_request` (a later addition to this module) resolves a hostname
once, refuses the whole host if any answer is not a public unicast
address, and connects only to an address it already checked -- closing
the gap where `requests`/`urllib` re-resolve the hostname again at
connect time, so a DNS answer checked once (DNS rebinding) can differ
from the one the socket actually reaches.

Both primitives raise exceptions that are also `requests.exceptions.
RequestException` (`DeadlineExceeded` a `requests.exceptions.Timeout`
subclass, `ResponseTooLarge` and `UnsafeDestination` plain
`RequestException` subclasses), so every existing
`except requests.RequestException` / `except requests.Timeout` handler in
this codebase keeps working unchanged once a caller migrates onto these
primitives.

Kept as one small module for this phase; a later phase (ARC-03) is
expected to absorb it, plus `calendar_rules._url_is_safe`, into
`net/safe_fetch.py`.
"""

import collections
import time

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
