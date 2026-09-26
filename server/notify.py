#!/usr/bin/env python3
"""The ntfy-style push notification sender behind the battery-low/
frame-silent alerts. One attempt, a five-second default timeout, never
raises.

A push topic URL is exactly as attacker-reachable as the calendar feed
URL, so it gets the same two defences: `server.plane.calendar_rules.
_url_is_safe()` refuses an unsafe scheme/address before any network
attempt is made, and the default transport connects through `server.
http_fetch`'s pinned request primitive - one DNS resolution, every
answer checked public, the socket dialled only to an address already
checked (closing the gap where a second resolution at connect time
could see a different, unsafe answer), and a certificate verified
against the topic's own hostname. That primitive never follows a
redirect itself, so a 3xx response comes back unfollowed and this
module's own 2xx check turns it into a plain failure - a push topic
never legitimately redirects, and revalidating a `Location` target the
way `fetch_ics()` does would be pointless machinery for a feature with
no legitimate redirect to revalidate.

Bounded by `NOTIFY_DEADLINE_S`, the same total-wall-clock-deadline shape
`calendar_rules.fetch_ics()` applies, on top of the per-call `timeout`
argument. Logging never includes the URL or the raw exception string,
only the exception type: several exception forms this module's
transport can raise embed the request URL in their default string, and
a topic URL is as secret-shaped as a calendar feed URL.
"""
import sys

from server import http_fetch
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

# Total wall-clock deadline for one notification POST, on top of the
# per-call `timeout` argument - a push topic is one request with no
# redirect hops, so this is sized smaller than the calendar feed's own
# CALENDAR_FETCH_DEADLINE_S.
NOTIFY_DEADLINE_S = 5.0

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


def default_notify_transport(url, title, body, timeout):
    """POST `body` (UTF-8) to `url` with a `Title` header, through
    `http_fetch`'s pinned request primitive (see module docstring).
    Returns the open response; the caller reads `.status`/`.getcode()`
    and closes it. Never follows a redirect itself, so a 3xx comes back
    unfollowed rather than being retried against a different target with
    no re-check of `_url_is_safe()`.
    """
    return http_fetch.pinned_request(
        "POST",
        url,
        headers={
            "Title": title,
            "Content-Type": "text/plain; charset=utf-8",
            "User-Agent": calendar_rules.USER_AGENT,
        },
        body=body.encode("utf-8"),
        timeout=timeout,
        deadline_s=NOTIFY_DEADLINE_S,
    )


def send_notification(topic_url, title, body, timeout=5, transport=None):
    """POST `body` to `topic_url` with a `Title` header. True on any 2xx
    response; False on any refusal (unsafe URL, non-2xx including an
    unfollowed redirect, timeout, transport exception) - never raises.
    One attempt, no retry.
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
