"""Read model of the Airline collection: which airlines the frame has seen.

Everything comes from the frame's own `runway_events` plus the curated
airline list; nothing is stored. The function only reads (SELECT only) and
creates no table.

A pass stored twice (the poll loop writes a second event when the
corroboration flag flips) is folded into one sighting with the same rule
Home and Flights use, so "seen n times" counts flights, not stored rows.
"""
import collections
import functools
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from companion import airline_display, flight_card, history_cache
from companion.pages import airline_sheet
from server import history_db
from server.plane import illustrations
from server.plane.render import text as render_text

# Sightings needed for each rarity level; below OCCASIONAL_MIN is Rare.
# The one threshold table: airlines and aircraft types both use it, and the
# page legend prints these numbers.
REGULAR_MIN = 10
OCCASIONAL_MIN = 3
# Spotted-airline counts that earn a collection badge.
BADGE_THRESHOLDS = (1, 5, 10, 25, 50)
# An airline whose first sighting is this recent carries the New pill.
NEW_WINDOW_DAYS = 7
# Recent callsigns kept per airline, newest first.
RECENT_CALLSIGNS = 5

RARITY_REGULAR = "regular"
RARITY_OCCASIONAL = "occasional"
RARITY_RARE = "rare"
# Not seen yet: no rarity.
RARITY_NONE = ""

_SELECT_EVENTS = (
    "SELECT id, ts, hex, callsign, aircraft_type, confirmed_state, origin, "
    "destination, airline FROM runway_events ORDER BY ts DESC, id DESC")


@dataclass(frozen=True)
class AirlineEntry:
    """One card: a curated airline, or an uncurated one the frame saw."""
    slug: str
    name: str
    picture_key: str
    curated: bool
    times_seen: int = 0
    first_ts: str = ""
    last_ts: str = ""
    first_day: object = None
    last_day: object = None
    types: tuple = ()
    callsigns: tuple = ()
    rarity: str = RARITY_NONE
    is_new: bool = False
    # `(aircraft type code, rarity)` in the same order as `types`; the
    # rarity is that of the type across every sighting the frame stored.
    type_rarities: tuple = ()
    # `(aircraft type code, sightings of this airline)`, most seen first.
    type_counts: tuple = ()

    @property
    def seen(self):
        return self.times_seen > 0


@dataclass(frozen=True)
class CollectionSummary:
    spotted: int = 0
    total: int = 0
    earned: tuple = field(default_factory=tuple)
    next_goal: object = None


def rarity_for(times_seen):
    """The rarity level of an airline sighted `times_seen` times."""
    if times_seen >= REGULAR_MIN:
        return RARITY_REGULAR
    if times_seen >= OCCASIONAL_MIN:
        return RARITY_OCCASIONAL
    if times_seen >= 1:
        return RARITY_RARE
    return RARITY_NONE


def _curated_index(overrides):
    """`(order, aliases)`: curated airlines in list order as
    `(key, display name, picture key)`, and a map from every key a flight
    may carry (the curated name, or the owner's rename) to its curated key."""
    order = []
    aliases = {}
    for builtin, _shapes in illustrations.target_variants_by_airline():
        key = illustrations.normalise_airline_key(builtin)
        if not key or key in aliases:
            continue
        sheet = airline_sheet.card_sheet(builtin, overrides or {})
        shown = sheet["name"] if sheet else builtin
        picture_key = illustrations.normalise_airline_key(shown) or key
        order.append((key, airline_display.shown_name(render_text.display_airline_name(shown)),
                      picture_key))
        aliases[key] = key
        aliases[picture_key] = key
    return order, aliases


def _sightings(conn):
    """Stored events newest first with repeated passes folded away."""
    return history_cache.cached(conn, "sightings", lambda: flight_card.fold_repeated_passes(
        [dict(row) for row in conn.execute(_SELECT_EVENTS).fetchall()]))


# The airline key of a name is a pure function of it, asked for once per stored
# event: remembered per distinct name.
_airline_key = functools.lru_cache(maxsize=2048)(illustrations.normalise_airline_key)


def _group(rows, aliases):
    """`{slug: [row, ...]}` (newest first) for rows carrying an airline name."""
    groups = collections.OrderedDict()
    for row in rows:
        airline = row.get("airline")
        if not isinstance(airline, str) or not airline.strip():
            continue
        key = _airline_key(airline.strip())
        if not key:
            continue
        groups.setdefault(aliases.get(key, key), []).append(row)
    return groups


def _ranked_types(rows):
    counts = collections.Counter(
        str(row["aircraft_type"]).strip().upper()
        for row in rows if row.get("aircraft_type") and str(row["aircraft_type"]).strip())
    return tuple(name for name, _count in counts.most_common())


def _ranked_type_counts(rows):
    counts = collections.Counter(
        str(row["aircraft_type"]).strip().upper()
        for row in rows if row.get("aircraft_type") and str(row["aircraft_type"]).strip())
    return tuple(counts.most_common())


def _recent_callsigns(rows):
    seen = []
    for row in rows:
        callsign = (row.get("callsign") or "").strip()
        if callsign and callsign not in seen:
            seen.append(callsign)
        if len(seen) >= RECENT_CALLSIGNS:
            break
    return tuple(seen)


def _is_new(first_ts, now):
    first = history_db.instant_or_none(first_ts)
    if first is None:
        return False
    return now - first <= timedelta(days=NEW_WINDOW_DAYS)


def _type_counts(events):
    """`{type code: sightings}` over every stored sighting."""
    return collections.Counter(
        str(row["aircraft_type"]).strip().upper()
        for row in events if row.get("aircraft_type") and str(row["aircraft_type"]).strip())


def _entry(slug, name, picture_key, curated, rows, now, type_counts):
    if not rows:
        return AirlineEntry(slug, name, picture_key, curated)
    first_ts = rows[-1]["ts"]
    last_ts = rows[0]["ts"]
    types = _ranked_types(rows)
    return AirlineEntry(
        slug, name, picture_key, curated,
        times_seen=len(rows), first_ts=first_ts, last_ts=last_ts,
        first_day=history_db.paris_day_or_none(first_ts),
        last_day=history_db.paris_day_or_none(last_ts),
        types=types, callsigns=_recent_callsigns(rows),
        rarity=rarity_for(len(rows)), is_new=_is_new(first_ts, now),
        type_rarities=tuple((code, rarity_for(type_counts[code])) for code in types),
        type_counts=_ranked_type_counts(rows))


def _summary(spotted, total):
    earned = tuple(n for n in BADGE_THRESHOLDS if spotted >= n)
    goals = [n for n in BADGE_THRESHOLDS if spotted < n]
    return CollectionSummary(spotted, total, earned, goals[0] if goals else None)


def _utc_now(now):
    parsed = history_db.instant_or_none(now) if now else None
    return parsed or datetime.now(timezone.utc)


def collection_from_events(events, now, overrides=None):
    """`(entries, summary)` from `events` (stored rows newest first, repeated
    passes already folded): one entry per curated airline in list order,
    then one per uncurated airline the frame saw (most recently seen first).
    `now` is a UTC ISO-8601 string. `overrides` is the owner's rename
    registry, so a renamed curated airline keeps its card and its history.
    """
    instant = _utc_now(now)
    order, aliases = _curated_index(overrides)
    groups = _group(events, aliases)
    type_counts = _type_counts(events)
    entries = [
        _entry(key, name, picture_key, True, groups.pop(key, []), instant, type_counts)
        for key, name, picture_key in order]
    for slug, rows in groups.items():
        name = airline_display.shown_name(
            render_text.display_airline_name(rows[0]["airline"].strip()))
        entries.append(_entry(slug, name, slug, False, rows, instant, type_counts))
    spotted = sum(1 for entry in entries if entry.seen)
    return entries, _summary(spotted, len(order))


def sightings_across(state_dirs):
    """The folded sightings of every frame in `state_dirs` merged newest
    first. A frame whose history cannot be read contributes nothing."""
    merged = []
    seen_dirs = set()
    for state_dir in state_dirs:
        if not state_dir or state_dir in seen_dirs:
            continue
        seen_dirs.add(state_dir)
        try:
            with history_db.open_db(state_dir) as conn:
                merged.extend(_sightings(conn))
        except (sqlite3.Error, OSError):
            continue
    merged.sort(key=lambda row: row.get("ts") or "", reverse=True)
    return merged


def airline_collection(conn, now, overrides=None):
    """`collection_from_events` over the connection's `runway_events`."""
    return collection_from_events(_sightings(conn), now, overrides)
