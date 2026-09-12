#!/usr/bin/env python3
"""server/notify.py — the ntfy-style push notification sender behind
D-25 (battery-low/frame-silent alerts, 20-CONTEXT.md) and D-27 (sent
from server/poll_loop.py, on transitions only).

One attempt, a five-second default timeout, never raises — the poll
cycle this feeds must never block or abort because a third-party push
endpoint is slow, unreachable, or misconfigured (T-20-17).

SSRF gate — reused, never re-derived (T-20-05, ASVS V5): the first
line of `send_notification()` calls
`server.plane.calendar_rules._url_is_safe()`, the exact scheme/
hostname/private-IP gate `fetch_ics()` already applies to the
operator-supplied calendar feed URL. A push topic URL is exactly as
attacker-reachable as a calendar feed URL (both are pasted into a
form by whoever holds the one shared companion password), so it goes
through the identical gate rather than a second, independently
written copy that could drift from it.

CR-01 fix (20-REVIEW.md): that gate only ever inspects the FIRST URL.
`fetch_ics()`'s own `default_calendar_transport()` disables automatic
redirect following (`requests`'s `allow_redirects=False`) precisely so
`fetch_ics()`'s own loop can re-validate every `Location` hop through
`_url_is_safe()` before ever following it — a validated public HTTPS
endpoint can still answer with a 3xx pointing anywhere, including
`http://169.254.169.254/...` or an internal admin endpoint. Before
this fix, `default_notify_transport()` called plain
`urllib.request.urlopen()`, whose default opener installs stdlib's own
`urllib.request.HTTPRedirectHandler` and therefore followed a 3xx
automatically, with no re-check at all — silently defeating the gate
above for this one call path. `default_notify_transport()` now goes
through `_NO_REDIRECT_OPENER` instead: `_NoRedirectHandler.redirect_request()`
below always returns `None`, refusing every hop outright (never a
bounded manual re-validation loop like `fetch_ics()`'s own, since a
push topic never legitimately redirects) — the stdlib idiom that turns
any 3xx response into a plain `urllib.error.HTTPError`, already caught
by this module's own broad `except Exception` a few lines down and
logged without the URL, exactly like any other transport failure.

Stdlib `urllib.request`/`urllib.error` only (D-25) — this module adds
no `requests` dependency; `server/plane/calendar_rules.py` already
carries that dependency for its own, unrelated reason (streamed,
redirect-aware GETs), which this module's simple one-shot POST does
not need.

Logging discipline (T-20-06, mirrors `fetch_ics()`'s own T-16-SECRET
rule at server/plane/calendar_rules.py): the only place this module
ever prints is the transport-exception catch below, and it prints
`type(exc).__name__` and a fixed description only — never the
exception object's own string form, and never the URL itself.
Several `urllib.error.URLError`/`HTTPError` forms embed the request
URL in their own default string form, and a topic URL is exactly as
secret-shaped as a calendar feed URL.
"""
import sys
import urllib.request

from server.plane import calendar_rules

# D-25/D-27, 20-UI-SPEC.md §G: the four transition body strings, English
# (the source language, D-01) — the French forms live in BODY_FR below,
# keyed by the identical English string, mirroring
# companion/i18n_fr.py's own "catalogue keyed by the English source
# string" convention without importing that module (this file must
# never import anything under companion/, D-27's own constraint).
BATTERY_LOW_BODY = "Battery low — %s mV (≈ %d%%)"
BATTERY_OK_BODY = "Battery back to normal"
FRAME_SILENT_BODY = "The frame has not checked in for %s"
FRAME_RECOVERED_BODY = "The frame is back"

# The "Send a test" button's own fixed title/body pair (20-11-PLAN.md) —
# never templated, so a test push never needs a real battery/staleness
# reading to send.
TEST_NOTIFICATION_TITLE = "SkyPane"
TEST_NOTIFICATION_BODY = "This is a test notification from SkyPane."

_BODY_FR = {
    "Battery low — %s mV (≈ %d%%)": "Batterie faible — %s mV (≈ %d %%)",
    "Battery back to normal": "Batterie revenue à la normale",
    "The frame has not checked in for %s": "Le cadre ne s'est pas connecté depuis %s",
    "The frame is back": "Le cadre est de retour",
    "This is a test notification from SkyPane.": "Ceci est une notification de test de SkyPane.",
}


def body_for_lang(text, lang):
    """Return the French form of `text` when `lang == "fr"` and `text`
    is a key in `_BODY_FR`; otherwise return `text` unchanged. Never
    raises — a missing key degrades to the English source string, the
    same fallback contract `companion/i18n.py.t()` documents for the
    UI catalogue (D-04), kept as an independent copy here so
    server/poll_loop.py never has to import anything under companion/
    (D-27).
    """
    if lang == "fr":
        return _BODY_FR.get(text, text)
    return text


def _response_status(response):
    """Read a response's HTTP status defensively: a real
    `http.client.HTTPResponse` exposes `.status` (py3.9+); a test's
    injected fake may instead only implement `.getcode()`. Returns 0
    for a response exposing neither, which the caller's `2xx` test
    then correctly reports as a failure rather than raising.
    """
    status = getattr(response, "status", None)
    if status is not None:
        return status
    getcode = getattr(response, "getcode", None)
    if callable(getcode):
        return getcode()
    return 0


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuses every 3xx redirect outright (CR-01 fix — see this
    module's own docstring above). `redirect_request()` returning
    `None` is the stdlib idiom for "never follow": the redirect
    handler chain then falls through to `HTTPDefaultErrorHandler`,
    which raises `urllib.error.HTTPError` for the original 3xx status
    — caught by `send_notification()`'s existing broad `except
    Exception` below, exactly like any other transport failure, and
    logged there by type name only, never the URL. Deliberately does
    not inspect `newurl` at all: unlike `fetch_ics()`'s calendar feed
    (which legitimately gets redirected by real hosting providers), an
    ntfy-style push topic has no legitimate reason to redirect, so this
    refuses every hop unconditionally rather than re-validating a
    bounded chain of them.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Built once at import time, reused by every `default_notify_transport()`
# call — one opener with `_NoRedirectHandler` installed in place of the
# default `HTTPRedirectHandler` (`build_opener()`'s own dedup rule: a
# passed-in subclass of a default handler class replaces it, rather than
# both being installed side by side).
_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def default_notify_transport(url, title, body, timeout):
    """POST `body` (UTF-8) to `url` with a `Title` header carrying
    `title` — the one-shot ntfy-style push. Stdlib
    `urllib.request.Request`/`urlopen` only (D-25). Returns the open
    response object; the caller reads and closes it.

    Goes through `_NO_REDIRECT_OPENER` (CR-01 fix), never plain
    `urllib.request.urlopen()` — the latter's default opener follows a
    3xx response automatically, with no re-check of `_url_is_safe()`
    on the redirect target.
    """
    data = body.encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Title": title,
            "Content-Type": "text/plain; charset=utf-8",
            "User-Agent": calendar_rules.USER_AGENT,
        },
    )
    return _NO_REDIRECT_OPENER.open(request, timeout=timeout)


def send_notification(topic_url, title, body, timeout=5, transport=None):
    """POST `body` to `topic_url` with a `Title: {title}` header — an
    ntfy-style push. Returns True on any 2xx response, False on any
    refusal (an unsafe URL, a non-2xx response, a timeout, or a
    transport exception) — never raises, matching `fetch_ics()`'s own
    contract. One attempt, no retry (D-27).
    """
    if not calendar_rules._url_is_safe(topic_url):
        return False
    send = transport or default_notify_transport
    try:
        response = send(topic_url, title, body, timeout)
    except Exception as exc:
        # Deliberately broad, mirroring fetch_ics()'s own transport-call
        # catch: a caller-supplied fake transport, or urllib itself, is
        # not guaranteed to only ever raise a URLError/HTTPError
        # subclass, and this send must never break the caller's poll
        # cycle no matter what raised. Log the exception TYPE only,
        # never `exc` itself, and never the URL (T-20-06).
        print(
            "notify: send_notification() transport call failed: %s"
            % type(exc).__name__,
            file=sys.stderr,
        )
        return False
    try:
        status = _response_status(response)
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return 200 <= status < 300
