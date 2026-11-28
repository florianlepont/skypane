# SPDX-License-Identifier: AGPL-3.0-only
"""Home's flight card: the picture the frame shows beside the flight it shows.

The picture is the newest archived render (the figure `freshness.js` swaps
with the rest of the card); the text is the first recent flight row, read
once with the strip's rows: a direction badge, the callsign, the airline, the
route and aircraft, and when the flight was detected. A frame with no picture yet shows the empty box,
and with no flight the card holds the picture alone.
"""
from datetime import timezone

import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
from companion.layout import escape_html
from companion.pages import home_recent_strip
from server.plane import render as panel_render

HEADING_ID = "home-flight"
GALLERY_ROUTE_PREFIX = "/gallery/"
HEADING_TEXT = i18n.msg("home.flight_heading", "Latest flight")
DETECTED_TEXT = i18n.msg("home.flight_detected", "Detected %s")
NO_PANEL_BODY = i18n.msg(
    "home.the_server_saves_a_copy_of_each_picture_it",
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = i18n.msg(
    "home.the_picture_currently_on_the_frame",
    "The picture currently on the frame")
PANEL_FLIGHT_ALT_TEMPLATE = i18n.msg(
    "home.the_picture_currently_on_the_frame_flight",
    "The picture currently on the frame: %s")
DEVICE_NO_IMAGE_HEADING = i18n.msg("home.device_no_image_heading", "No picture yet")
DEVICE_NO_IMAGE_BODY = i18n.msg(
    "home.device_no_image_body",
    "The first image appears after a poll or the frame’s first wake.")
# Owned by companion/i18n_fr/flights.py: the wording the Flights card uses
# for a missing airline.
AIRLINE_UNKNOWN_TEXT = i18n.msg("flights.airline_unknown", "Airline unknown")

_DIRECTION_ICONS = {"departing": "icon-departure", "arriving": "icon-arrival"}


def _route_text(row):
    origin = row.get("origin") or ""
    destination = row.get("destination") or ""
    if origin and destination:
        return "%s → %s" % (origin, destination)
    return ""


def flight_line(row):
    """"<airline> · <route> · <direction>", skipping any empty part:
    the picture's accessible name. `airline` and `route` are data and never
    translated."""
    airline = panel_render.display_airline_name(row.get("airline")) or ""
    direction = home_recent_strip.direction_text(row.get("confirmed_state"))
    return " · ".join(
        part for part in (airline, _route_text(row), i18n.t(direction) if direction else "")
        if part)


def picture_html(ctx, row):
    """The current picture alone: the newest archived render, whose alt text
    carries the flight line when a flight is known; or the empty box."""
    ctx = page_context.coerce(ctx)
    entries = ctx.gallery_entries or []
    newest = entries[0] if entries else None
    if not newest:
        device = ctx.device
        body = (
            DEVICE_NO_IMAGE_BODY if device is not None and not device.is_live
            else NO_PANEL_BODY)
        return (
            '<figure class="preview-frame preview-frame--empty">'
            '<div class="preview-empty"%s>%s<p class="preview-empty__heading">%s</p></div>'
            '<figcaption class="visually-hidden">%s</figcaption></figure>' % (
                device_scope.current_frame_shape_attr(),
                layout.icon_html("icon-device", 32, "preview-empty__glyph"),
                escape_html(i18n.t(DEVICE_NO_IMAGE_HEADING)), escape_html(i18n.t(body))))
    profile = device_scope.profile_for(device_scope.current_device())
    width, height = (profile.width, profile.height) if profile.width > profile.height else (600, 800)
    alt = i18n.t(PANEL_ALT_TEXT)
    if row:
        callsign = row.get("callsign") or row.get("hex") or "—"
        line = flight_line(row)
        alt = i18n.t(PANEL_FLIGHT_ALT_TEMPLATE) % (callsign + ((" · " + line) if line else ""))
    return (
        '<figure class="preview-frame">'
        '<img class="preview-frame__image" src="%s" alt="%s" '
        'width="%d" height="%d" decoding="async" fetchpriority="high"%s>'
        "</figure>"
    ) % (
        escape_html(device_scope.scoped(GALLERY_ROUTE_PREFIX + newest)),
        escape_html(alt), width, height, device_scope.frame_shape_attr(profile))


def _badge_html(state):
    direction = home_recent_strip.direction_text(state)
    if not direction:
        return ""
    icon = _DIRECTION_ICONS.get(state)
    return '<span class="home-flight__badge">%s%s</span>' % (
        layout.icon_html(icon, 16) if icon else "", escape_html(i18n.t(direction)))


def _meta_html(row, now):
    callsign = row.get("callsign") or row.get("hex") or "—"
    airline = panel_render.display_airline_name(row.get("airline")) or ""
    ts = row.get("ts")
    detected = (
        escape_html(i18n.t(DETECTED_TEXT)).replace("%s", layout.relative_time_html(ts, now))
        if ts else "")
    details = [part for part in (_route_text(row), row.get("aircraft_type") or "") if part]
    return (
        '<div class="home-flight__meta">%s<div class="home-flight__call tnum">%s</div>'
        '<div class="home-flight__airline">%s</div>%s'
        '<div class="home-flight__detected">%s</div></div>'
    ) % (
        _badge_html(row.get("confirmed_state")), escape_html(callsign),
        escape_html(airline or i18n.t(AIRLINE_UNKNOWN_TEXT)),
        '<div class="home-flight__details">%s</div>' % escape_html(" · ".join(details))
        if details else "", detected)


def ring_html(next_triple, now):
    """The thin ring around the picture: the share of the frame cycle already
    elapsed, from the same next-update instant the title block's sentence
    reads. Decorative (the sentence is the text alternative). The progress is
    rendered as attributes (no style attribute, for the CSP) and
    relative-time.js repaints it from `data-ring-next` / `data-ring-interval`
    each second. "" without a known next update."""
    next_iso, interval_s, _hold = next_triple
    parsed = layout.parse_iso(next_iso) if next_iso else None
    now_parsed = layout.parse_iso(now)
    if parsed is None or now_parsed is None or not interval_s:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    remaining = parsed.timestamp() - now_parsed.timestamp()
    progress = min(1.0, max(0.0, 1.0 - remaining / float(interval_s)))
    rect = (
        '<rect class="home-ring__%s" x="0" y="0" width="100%%" height="100%%" '
        'pathLength="100"%s/>')
    return (
        '<svg class="home-ring" aria-hidden="true" focusable="false" data-cycle-ring '
        'data-ring-next="%s" data-ring-interval="%d">%s%s</svg>'
    ) % (
        escape_html(parsed.astimezone(timezone.utc).isoformat(timespec="seconds")),
        int(interval_s), rect % ("track", ""),
        rect % ("bar", ' stroke-dasharray="100 100" stroke-dashoffset="%.2f"' % (
            100.0 * (1.0 - progress))))


def card_html(ctx, row, ring=""):
    """The flight card for the first recent flight `row` (or None); `ring`
    is the cycle ring drawn around its picture."""
    profile = device_scope.profile_for(device_scope.current_device())
    landscape = profile.width > profile.height
    css = "home-flight home-flight--%s reveal" % ("landscape" if landscape else "portrait")
    return (
        '<section class="%s" aria-labelledby="%s"><h2 class="visually-hidden" id="%s">%s</h2>'
        '<div class="home-flight__picture">%s%s</div>%s</section>'
    ) % (
        css, HEADING_ID, HEADING_ID, escape_html(i18n.t(HEADING_TEXT)),
        picture_html(ctx, row), ring, _meta_html(row, ctx.now) if row else "")
