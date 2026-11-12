"""Consistency check between a resolved route and the airport the frame
watches.

adsbdb maps a callsign to a route, and some carriers rotate callsigns
between aircraft, so a cached route can be stale. A route that cannot be
true for the observed direction is dropped rather than displayed: an
arrival cannot originate at the watched airport and a departure cannot
end there.
"""
from __future__ import annotations

import math

import server.airports as airports
import server.detection as detection
import server.plane.runway_config as runway_config

# Display id of the legacy default runway (Paris-Orly runway 3), which has
# no airport prefix.
_LEGACY_RUNWAY_AIRPORT_ICAO = "LFPO"
_EARTH_RADIUS_NM = 3440.065


def _distance_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def _runway_airport_iata(display_id):
    """IATA code of the airport a runway display id ("LFPG:08L/26R", or
    the legacy "3") belongs to; empty when it cannot be told."""
    if not isinstance(display_id, str):
        return frozenset()
    icao = display_id.split(":", 1)[0] if ":" in display_id else _LEGACY_RUNWAY_AIRPORT_ICAO
    try:
        airport = airports.find_airport(icao)
    except ValueError:
        return frozenset()
    return frozenset([airport.iata]) if airport is not None else frozenset()


def _position_airports_iata(zone):
    """IATA codes of the catalogue airports inside a position zone."""
    try:
        catalogue = airports.load_catalogue()
    except ValueError:
        return frozenset()
    return frozenset(
        airport.iata for airport in catalogue.values()
        if _distance_nm(zone.lat, zone.lon, airport.lat, airport.lon) <= zone.radius_nm)


def watched_iata_codes(spec, tracked_runway_id):
    """IATA codes of the airports the frame watches: the runway's airport
    in runway mode, the airports inside the zone in position mode. Empty
    when unknown, in which case no route is ever judged contradictory."""
    if spec is not None and spec.mode == detection.POSITION_MODE:
        return _position_airports_iata(spec.zone)
    return _runway_airport_iata(tracked_runway_id)


def route_contradicts(route, state, watched):
    """True when `route` cannot belong to an aircraft seen in `state`: an
    arrival whose origin is a watched airport, or a departure whose
    destination is one. Any other state (including the position-mode
    "overhead", which has no direction) never contradicts."""
    if not watched or not isinstance(route, dict):
        return False
    if state == runway_config.STATE_ARRIVING:
        return route.get("origin_iata") in watched
    if state == runway_config.STATE_DEPARTING:
        return route.get("destination_iata") in watched
    return False
