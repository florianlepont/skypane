#!/usr/bin/env python3
"""The ntfy-style push notification sender behind the battery-low/
frame-silent alerts. One attempt, a five-second default timeout, never
raises.

Reuses `server.plane.calendar_rules._url_is_safe()`, the same SSRF gate
`fetch_ics()` applies to calendar feed URLs, since a push topic URL is
exactly as attacker-reachable. That gate only inspects the first URL, so
redirects are refused outright here (`_NoRedirectHandler`, below) rather
than re-validated like `fetch_ics()`'s bounded hop-following - a push
topic never legitimately redirects. Logging never includes the URL or
the raw exception string, only the exception type: several
`urllib.error` forms embed the request URL in their default string, and
a topic URL is as secret-shaped as a calendar feed URL.
"""
import sys
import urllib.request

from server.plane import calendar_rules

# English source strings; French forms live in _BODY_FR below, keyed by
# the identical English string (this file must never import companion/).
BATTERY_LOW_BODY = "Battery low — %s mV (≈ %d%%)"
BATTERY_OK_BODY = "Battery back to normal"
FRAME_SILENT_BODY = "The frame has not checked in for %s"
FRAME_RECOVERED_BODY = "The frame is back"

# Real battery-low/frame-silent pushes use this title, kept distinct from
# TEST_NOTIFICATION_TITLE below even though both hold the same text today,
# so the two can vary independently later.
ALERT_TITLE = "SkyPane"

# The "Send a test" button's fixed title/body pair - never templated, so a
# test push needs no real battery/staleness reading.
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
    """The French form of `text` when `lang == "fr"` and `text` is a key
    in `_BODY_FR`; otherwise `text` unchanged. Never raises.
    """
    if lang == "fr":
        return _BODY_FR.get(text, text)
    return text


def _response_status(response):
    """A response's HTTP status via `.status` or the older `.getcode()`
    fallback; 0 if neither is present.
    """
    status = getattr(response, "status", None)
    if status is not None:
        return status
    getcode = getattr(response, "getcode", None)
    if callable(getcode):
        return getcode()
    return 0


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuses every 3xx redirect outright (see module docstring): a push
    topic has no legitimate reason to redirect, so `redirect_request()`
    returning `None` turns any 3xx into an `HTTPError`, caught like any
    other transport failure.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Built once at import time: one opener with `_NoRedirectHandler` in
# place of the default `HTTPRedirectHandler`.
_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def default_notify_transport(url, title, body, timeout):
    """POST `body` (UTF-8) to `url` with a `Title` header. Returns the
    open response; the caller reads and closes it. Goes through
    `_NO_REDIRECT_OPENER`, never plain `urlopen()`, which would follow a
    3xx automatically with no re-check of `_url_is_safe()`.
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
    """POST `body` to `topic_url` with a `Title` header. True on any 2xx
    response; False on any refusal (unsafe URL, non-2xx, timeout,
    transport exception) - never raises. One attempt, no retry.
    """
    if not calendar_rules._url_is_safe(topic_url):
        return False
    send = transport or default_notify_transport
    try:
        response = send(topic_url, title, body, timeout)
    except Exception as exc:
        # Broad on purpose: this send must never break the caller's poll
        # cycle. Log the exception type only, never `exc` or the URL.
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
