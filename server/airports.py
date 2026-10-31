"""Read-only France runway catalogue and airport search.

The catalogue is the committed server/data/airports_fr.json, generated
offline by scripts/build_airports.py. It is loaded once per process and
never fetched or written at run time. Lookups are dict lookups on strictly
validated keys, so an untrusted identifier can never reach a path, a query
or a format string.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any

CATALOGUE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "airports_fr.json"
)

_ICAO_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2}\Z", re.ASCII)
_DESIGNATOR_RE = re.compile(r"^\d{2}[LRC]?/\d{2}[LRC]?\Z", re.ASCII)

MAX_QUERY_CHARS = 60
DEFAULT_SEARCH_LIMIT = 20


@dataclass(frozen=True)
class Runway:
    """One full runway pair; thresholds are (lat, lon), lower number first."""

    designator: str
    le: str
    he: str
    thresholds: tuple[tuple[float, float], tuple[float, float]]
    length_m: int
    bearing_deg: float
    surface: str | None
    half_width_m: float
    ground_half_width_m: float


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    municipality: str
    lat: float
    lon: float
    runways: tuple[Runway, ...]


def _runway_from_json(raw: Mapping[str, Any]) -> Runway:
    first, second = raw["thresholds"]
    surface = raw["surface"]
    if surface is not None and not isinstance(surface, str):
        raise ValueError("runway surface must be a string or null")
    return Runway(
        designator=str(raw["designator"]),
        le=str(raw["le"]),
        he=str(raw["he"]),
        thresholds=(
            (float(first["lat"]), float(first["lon"])),
            (float(second["lat"]), float(second["lon"])),
        ),
        length_m=int(raw["length_m"]),
        bearing_deg=float(raw["bearing_deg"]),
        surface=surface,
        half_width_m=float(raw["half_width_m"]),
        ground_half_width_m=float(raw["ground_half_width_m"]),
    )


def _airport_from_json(raw: Mapping[str, Any]) -> Airport:
    icao = str(raw["icao"])
    if not _ICAO_RE.match(icao):
        raise ValueError("malformed airport identifier in catalogue")
    runways = tuple(_runway_from_json(r) for r in raw["runways"])
    for runway in runways:
        if not _DESIGNATOR_RE.match(runway.designator) or runway.half_width_m <= 0:
            raise ValueError("malformed runway in catalogue")
    return Airport(
        icao=icao,
        iata=str(raw["iata"]),
        name=str(raw["name"]),
        municipality=str(raw["municipality"]),
        lat=float(raw["lat"]),
        lon=float(raw["lon"]),
        runways=runways,
    )


@lru_cache(maxsize=1)
def load_catalogue() -> Mapping[str, Airport]:
    """Immutable mapping of ICAO identifier to airport.

    Raises ValueError when the file is missing or malformed; nothing is
    read at import time.
    """
    try:
        with open(CATALOGUE_PATH, encoding="utf-8") as handle:
            document = json.load(handle)
        airports = [_airport_from_json(raw) for raw in document["airports"]]
    except (OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("airport catalogue unreadable: %s" % type(exc).__name__) from exc
    return MappingProxyType({airport.icao: airport for airport in airports})


def find_airport(icao: object) -> Airport | None:
    """The airport with exactly this upper-case ICAO identifier, else None."""
    if not isinstance(icao, str) or not _ICAO_RE.match(icao):
        return None
    return load_catalogue().get(icao)


def find_runway(icao: object, designator: object) -> Runway | None:
    """The runway with exactly this "08L/26R" designator at the airport."""
    if not isinstance(designator, str) or not _DESIGNATOR_RE.match(designator):
        return None
    airport = find_airport(icao)
    if airport is None:
        return None
    for runway in airport.runways:
        if runway.designator == designator:
            return runway
    return None


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


@lru_cache(maxsize=1)
def _search_index() -> tuple[tuple[Airport, str, str, tuple[str, ...]], ...]:
    """(airport, folded icao, folded iata, folded searchable fields) rows.
    The fields stay separate so a query never matches across a boundary."""
    return tuple(
        (
            airport,
            _fold(airport.icao),
            _fold(airport.iata),
            tuple(
                _fold(field)
                for field in (airport.icao, airport.iata, airport.name, airport.municipality)
            ),
        )
        for airport in load_catalogue().values()
    )


def search_airports(
    query: object, limit: int = DEFAULT_SEARCH_LIMIT
) -> tuple[list[Airport], int]:
    """Airports matching the query and the total number of matches.

    Matching is a case- and accent-insensitive substring test over ICAO,
    IATA, name and municipality, each field on its own. An exact ICAO or IATA match sorts first,
    then by name, then by ICAO. A non-string, empty or control-character
    query matches nothing; the query is capped at MAX_QUERY_CHARS.
    """
    if not isinstance(query, str):
        return [], 0
    capped = query[:MAX_QUERY_CHARS]
    if any(unicodedata.category(c) == "Cc" for c in capped):
        return [], 0
    needle = _fold(capped)
    if not needle:
        return [], 0
    hits = [
        (0 if needle in (icao, iata) else 1, _fold(airport.name), airport.icao, airport)
        for airport, icao, iata, fields in _search_index()
        if any(needle in field for field in fields)
    ]
    hits.sort(key=lambda hit: hit[:3])
    return [hit[3] for hit in hits[: max(0, limit)]], len(hits)
