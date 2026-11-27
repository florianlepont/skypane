"""Pure zone identity, capacity ordering and device activity rules.

A zone is the exact (centre latitude, centre longitude, radius) triple a
device is polled for. Two devices share a zone, and therefore one upstream
request set, only when all three numbers are identical; nothing is rounded
or merged here. No I/O and no clock: callers pass every input in.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

# A device that has not checked in for this long is skipped by the fleet cycle.
INACTIVE_AFTER_S: float = 7 * 86400


def _finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("zone %s must be a number" % name)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("zone %s must be finite" % name)
    # Adding 0.0 turns -0.0 into 0.0 so equal zones always share one key.
    return number + 0.0


@dataclass(frozen=True)
class Zone:
    """A validated polling area: centre in degrees, radius in nautical miles."""

    lat: float
    lon: float
    radius_nm: float

    def __post_init__(self) -> None:
        lat = _finite_float(self.lat, "latitude")
        lon = _finite_float(self.lon, "longitude")
        radius = _finite_float(self.radius_nm, "radius")
        if not -90.0 <= lat <= 90.0:
            raise ValueError("zone latitude out of range")
        if not -180.0 <= lon <= 180.0:
            raise ValueError("zone longitude out of range")
        if radius <= 0:
            raise ValueError("zone radius must be positive")
        object.__setattr__(self, "lat", lat)
        object.__setattr__(self, "lon", lon)
        object.__setattr__(self, "radius_nm", radius)

    @property
    def key(self) -> str:
        """Exact-pair identity; `repr` of a float round-trips, so no merging."""
        return "%r|%r|%r" % (self.lat, self.lon, self.radius_nm)


@dataclass(frozen=True)
class ZoneEntry:
    """One zone as seen by the cycle, with whether the live frame is in it."""

    zone: Zone
    has_live: bool = False


def zone_from_geofence(geofence: Any) -> Zone:
    """Build a Zone from a geofence document's `center` and `radius_nm`."""
    try:
        center = geofence["center"]
        return Zone(center["lat"], center["lon"], geofence["radius_nm"])
    except (KeyError, TypeError) as exc:
        raise ValueError("malformed geofence: %s" % type(exc).__name__) from exc


def order_zones(entries: Iterable[ZoneEntry], last_served: Mapping[str, float]) -> list[Zone]:
    """Serving order: live-frame zones first, then oldest-served first.

    A zone absent from `last_served` has never been served and sorts before
    every served zone. Ties break on the zone key, so the result does not
    depend on the input order. Duplicate zones collapse into one, live if any
    of its entries is live.
    """
    live: dict[str, bool] = {}
    zones: dict[str, Zone] = {}
    for entry in entries:
        key = entry.zone.key
        zones[key] = entry.zone
        live[key] = live.get(key, False) or entry.has_live

    def sort_key(key: str) -> tuple[bool, float, str]:
        served = last_served.get(key)
        return (not live[key], -math.inf if served is None else float(served), key)

    return [zones[key] for key in sorted(zones, key=sort_key)]


def device_is_active(
    is_live: bool,
    created_epoch: float | None,
    last_check_in_epoch: float | None,
    now: float,
) -> bool:
    """Whether the fleet cycle should serve a device.

    The live frame is always active. A device that checked in within
    `INACTIVE_AFTER_S` is active; one with no check-in is active only while
    it was created less than that long ago. Timestamps in the future count as
    recent so a skewed clock never skips a device.
    """
    if is_live:
        return True
    reference = last_check_in_epoch if last_check_in_epoch is not None else created_epoch
    if reference is None:
        return False
    return now - reference < INACTIVE_AFTER_S
