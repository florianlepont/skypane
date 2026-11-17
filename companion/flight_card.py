"""What Flights and Home share about a flight: the fold that makes a pass
stored twice read as one flight, and the route fallback wording.
Page modules cannot import each other, which is why these helpers live here.
"""
import companion.i18n as i18n
import companion.layout as layout
from server.plane import render as panel_render

# Two stored events for the same pass within this many seconds read as one
# flight on Home and Flights.
DUPLICATE_WINDOW_S = 60

ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
# Held as a local literal so the French catalogue can carry it. It equals
# panel_render.ROUTE_FALLBACK_TEXT by construction, so the wording never
# drifts between the panel and the companion.
ROUTE_FALLBACK_TEXT = i18n.msg("flights.route_unavailable", "Route unavailable")
assert ROUTE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT


def _pass_key(row):
    """What makes two stored events the same pass on screen: same
    aircraft, callsign, route and direction."""
    return tuple(row.get(name) for name in (
        "hex", "callsign", "origin", "destination", "confirmed_state"))


def _seconds_between(newer_ts, older_ts):
    """Absolute seconds between two stored timestamps, or None when
    either does not parse."""
    newer, older = layout.parse_iso(newer_ts), layout.parse_iso(older_ts)
    if newer is None or older is None:
        return None
    try:
        return abs((newer - older).total_seconds())
    except TypeError:
        return None


def fold_repeated_passes(rows, limit=None):
    """`rows` (newest first) with repeated passes folded away, stopping at
    `limit` kept rows when given. The poll loop stores a new event whenever
    the corroboration flag changes (one feed missing a cycle turns True
    into None), so a single pass can be stored twice 30 s apart. A row is
    dropped when it has the same pass key as the row just before it and
    the two timestamps are under `DUPLICATE_WINDOW_S` apart; the newest one
    stays. Storage is untouched. Home and Flights share this fold so both
    pages list the same flights.
    """
    kept = []
    previous = None
    for row in rows:
        if previous is not None and _pass_key(row) == _pass_key(previous):
            gap = _seconds_between(previous.get("ts"), row.get("ts"))
            if gap is not None and gap < DUPLICATE_WINDOW_S:
                # The kept (newest) row keeps the picture of the pass's first sighting.
                if row.get("gallery_name") and not kept[-1].get("gallery_name"):
                    kept[-1] = dict(kept[-1], gallery_name=row["gallery_name"])
                previous = row
                continue
        previous = row
        kept.append(row)
        if limit is not None and len(kept) >= limit:
            break
    return kept
