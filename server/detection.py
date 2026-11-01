"""Per-device detection spec for runway and position modes.

`spec_for` turns a device's stored configuration into a zone to poll and a
geofence-shaped document that server.plane.detect consumes unchanged, so
every runway shares one set of gating functions and differs only in data.

The three legacy Orly ids ("3", "06-24", "02-20") resolve to the catalogue's
LFPO rows but keep a frozen bounding box, centre, radius and ceiling taken
from adsb-test/runway3.json. The generic corridor rectangle is not clipped
the way the hand-tuned box is, so deriving the box generically would change
decisions at the corridor tips; carrying the frozen values keeps the Orly
frame's behaviour and its zone key unchanged.

Position mode polls the area around the device's location. The location is
rounded to two decimals (about 1 km) in `position_zone`, the only place a
position zone is built, so no provider URL, log line or stored document ever
carries the unrounded home coordinate; equal rounded inputs share one zone.

Pure: no clock and no network. The only I/O is reading the legacy geofence
file when the kill switch is on.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from server import airports, device_config, fleet_zones
from server.plane import detect

# Setting this environment variable to "1" puts the legacy ids back on the
# hand-tuned geofence file instead of the generated document.
LEGACY_GEOFENCE_ENV = "SKYPANE_LEGACY_ORLY_GEOFENCE"

# True forces the legacy ids onto the geofence file regardless of the
# environment; left False while the generated document is proven identical.
LEGACY_ORLY_DEFAULT_TO_FILE = False

LEGACY_RUNWAY_MAP: Mapping[str, tuple[str, str]] = {
    "3": ("LFPO", "07/25"),
    "06-24": ("LFPO", "06/24"),
    "02-20": ("LFPO", "02/20"),
}
_LEGACY_BY_RUNWAY = {value: key for key, value in LEGACY_RUNWAY_MAP.items()}

# Frozen copy of adsb-test/runway3.json's zone and prefilter values.
LEGACY_ORLY_BBOX: Mapping[str, float] = {
    "lat_min": 48.712,
    "lat_max": 48.734,
    "lon_min": 2.325,
    "lon_max": 2.435,
}
LEGACY_ORLY_CENTER = (48.7233, 2.3794)
LEGACY_ORLY_RADIUS_NM = 5.0
LEGACY_ORLY_ALT_CEILING_FT = 3000

RUNWAY_MODE = "runway"
ZONE_RADIUS_NM = 5.0
ALT_CEILING_FT = 3000
EXTENSION_M = 2500
AXIS_TOLERANCE_DEG = 30
_FALLBACK_ID = "3"

POSITION_MODE = detect.POSITION_MODE
POSITION_ID_PREFIX = "position:"
NO_LOCATION_DISPLAY_ID = "position:none"
NO_LOCATION_TAG_TEXT = "SET A LOCATION"
NO_LOCATION_HEADING = "Set a location"
# Stand-in zone of a no-location spec; it is never fetched.
_NO_LOCATION_ZONE = fleet_zones.Zone(46.6, 2.5, 1.0)
# The circle centre is rounded to 2 decimals, which can move it up to about
# 0.7 km (0.005 deg of latitude plus 0.005 deg of longitude) from the true
# location. At the minimum radius the true location is therefore always
# inside the circle, and coverage around it is guaranteed to about 1.3 km.
RADIUS_KM_MIN = 2
RADIUS_KM_MAX = 28
KM_PER_NM = 1.852

# Coarse guard around metropolitan France and Corsica, derived from the
# airport extremes. It is deliberately not a border test: it admits slivers
# of neighbouring countries and the sea. Checked on the rounded values.
FRANCE_LAT_MIN = 41.30
FRANCE_LAT_MAX = 51.15
FRANCE_LON_MIN = -5.20
FRANCE_LON_MAX = 9.60


@dataclass(frozen=True)
class DetectionSpec:
    """What one device polls and how its aircraft are gated and labelled."""

    mode: str
    display_id: str
    zone: fleet_zones.Zone
    geofence: dict[str, Any]
    tag_text: str
    empty_heading: str
    # True for a position-mode device with no usable location: it polls
    # nothing and its frame shows the set-a-location screen.
    no_location: bool = False


class NoLocationError(ValueError):
    """The device is in position mode but has no usable location."""


def runway_display_id(icao: str, designator: str) -> str:
    """Display id of a catalogue runway, e.g. "LFPG:08L/26R"."""
    return "%s:%s" % (icao, designator)


def _corridor_bbox(
    runway: airports.Runway, half_width_m: float, thresholds: list[dict[str, float]]
) -> dict[str, float]:
    """Bounding box of the corridor rectangle, in detect's own arithmetic."""
    probe = {"runways": {"r": {"runway": {"thresholds": thresholds}}}}
    axis = detect.runway_axis(probe, runway_id="r")
    if axis is None:
        raise ValueError("runway has no usable axis")
    lats: list[float] = []
    lons: list[float] = []
    for along in (-EXTENSION_M, axis["length_m"] + EXTENSION_M):
        for cross in (-half_width_m, half_width_m):
            x = along * axis["ux"] - cross * axis["uy"]
            y = along * axis["uy"] + cross * axis["ux"]
            lats.append(axis["lat0"] + y / detect._M_PER_DEG_LAT)
            lons.append(axis["lon0"] + x / axis["lon_scale"])
    # Rounded outward to 6 decimals so every corner stays inside the box.
    return {
        "lat_min": math.floor(min(lats) * 1e6) / 1e6,
        "lat_max": math.ceil(max(lats) * 1e6) / 1e6,
        "lon_min": math.floor(min(lons) * 1e6) / 1e6,
        "lon_max": math.ceil(max(lons) * 1e6) / 1e6,
    }


def runway_geofence_doc(
    airport: airports.Airport,
    runway: airports.Runway,
    display_id: str,
    legacy: bool = False,
) -> dict[str, Any]:
    """Geofence-shaped document for one catalogue runway.

    `runways[display_id]` is always populated, otherwise detect would fall
    back to the default runway and gate on nothing. `legacy` substitutes the
    frozen Orly bounding box, centre, radius and ceiling.
    """
    thresholds = [{"lat": lat, "lon": lon} for lat, lon in runway.thresholds]
    if legacy:
        bbox = dict(LEGACY_ORLY_BBOX)
        center = {"lat": LEGACY_ORLY_CENTER[0], "lon": LEGACY_ORLY_CENTER[1]}
        radius_nm = LEGACY_ORLY_RADIUS_NM
        ceiling = LEGACY_ORLY_ALT_CEILING_FT
    else:
        bbox = _corridor_bbox(runway, runway.half_width_m, thresholds)
        center = {"lat": round(airport.lat, 4), "lon": round(airport.lon, 4)}
        radius_nm = ZONE_RADIUS_NM
        ceiling = ALT_CEILING_FT
    return {
        "center": center,
        "radius_nm": radius_nm,
        "bbox": bbox,
        "alt_ceiling_ft": ceiling,
        "runways": {
            display_id: {
                "runway": {"thresholds": thresholds},
                "corridor": {
                    "half_width_m": runway.half_width_m,
                    "extension_m": EXTENSION_M,
                    "axis_tolerance_deg": AXIS_TOLERANCE_DEG,
                    "ground_half_width_m": runway.ground_half_width_m,
                },
            }
        },
    }


def km_to_nm(radius_km: int) -> float:
    """Zone radius in nautical miles for a whole-kilometre radius.

    Rounded to two decimals so equal inputs share one zone key; the allowed
    2 to 28 km therefore span 1.08 to 15.12 NM.
    """
    return round(radius_km / KM_PER_NM, 2)


def round_coordinate(value: float) -> float:
    """Two-decimal coordinate with negative zero normalised to zero."""
    return round(value, 2) + 0.0


def inside_france(lat: float, lon: float) -> bool:
    """Whether the rounded coordinate lies in the coarse France box."""
    return (
        FRANCE_LAT_MIN <= round_coordinate(lat) <= FRANCE_LAT_MAX
        and FRANCE_LON_MIN <= round_coordinate(lon) <= FRANCE_LON_MAX
    )


def _is_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def validate_position(lat: Any, lon: Any, radius_km: Any) -> tuple[float, float, int]:
    """Rounded (lat, lon) and the radius, or ValueError.

    The error's first argument is a stable code: "radius", "location" (not a
    finite coordinate) or "outside_france".
    """
    if isinstance(radius_km, bool) or not isinstance(radius_km, int):
        raise ValueError("radius")
    if not RADIUS_KM_MIN <= radius_km <= RADIUS_KM_MAX:
        raise ValueError("radius")
    if not _is_number(lat) or not _is_number(lon):
        raise ValueError("location")
    if not inside_france(lat, lon):
        raise ValueError("outside_france")
    return round_coordinate(lat), round_coordinate(lon), radius_km


def position_zone(lat: float, lon: float, radius_km: int) -> fleet_zones.Zone:
    """The zone for a device position: the single place one is constructed.

    Rounds before the Zone exists, so the unrounded coordinate cannot reach
    a provider request.
    """
    return fleet_zones.Zone(round_coordinate(lat), round_coordinate(lon), km_to_nm(radius_km))


def position_display_id(radius_km: int) -> str:
    return "%s%d" % (POSITION_ID_PREFIX, radius_km)


def _position_km(display_id: str) -> int | None:
    if not display_id.startswith(POSITION_ID_PREFIX):
        return None
    text = display_id[len(POSITION_ID_PREFIX):]
    return int(text) if text.isdigit() else None


def _position_doc(zone: fleet_zones.Zone) -> dict[str, Any]:
    radius_m = zone.radius_nm * 1852.0
    dlat = radius_m / detect._M_PER_DEG_LAT
    dlon = radius_m / (detect._M_PER_DEG_LAT * math.cos(math.radians(zone.lat)))
    return {
        "detection_mode": POSITION_MODE,
        "center": {"lat": zone.lat, "lon": zone.lon},
        "radius_nm": zone.radius_nm,
        "bbox": {
            "lat_min": round(zone.lat - dlat, 6),
            "lat_max": round(zone.lat + dlat, 6),
            "lon_min": round(zone.lon - dlon, 6),
            "lon_max": round(zone.lon + dlon, 6),
        },
        "alt_ceiling_ft": None,
    }


def no_location_spec() -> DetectionSpec:
    """Spec of a position-mode device that has no usable location."""
    return DetectionSpec(
        mode=POSITION_MODE,
        display_id=NO_LOCATION_DISPLAY_ID,
        zone=_NO_LOCATION_ZONE,
        geofence={},
        tag_text=NO_LOCATION_TAG_TEXT,
        empty_heading=NO_LOCATION_HEADING,
        no_location=True,
    )


def _position_spec(detection: Mapping[str, Any], location: Any) -> DetectionSpec | None:
    if detection.get("mode") != POSITION_MODE:
        return None
    # A bad radius is a corrupt setting and keeps the legacy fail-safe; a
    # missing, cleared or non-French location is a usable setting with
    # nowhere to look.
    try:
        validate_radius_km(detection.get("radius_km"))
    except ValueError:
        return None
    try:
        lat, lon = location
        lat, lon, radius_km = validate_position(lat, lon, detection.get("radius_km"))
    except (TypeError, ValueError):
        return no_location_spec()
    zone = position_zone(lat, lon, radius_km)
    display_id = position_display_id(radius_km)
    return DetectionSpec(
        mode=POSITION_MODE,
        display_id=display_id,
        zone=zone,
        geofence=_position_doc(zone),
        tag_text=tag_text(display_id),
        empty_heading=empty_heading(display_id),
    )


def _split_display_id(display_id: str) -> tuple[airports.Airport, airports.Runway] | None:
    icao, sep, designator = display_id.partition(":")
    if not sep:
        return None
    airport = airports.find_airport(icao)
    runway = airports.find_runway(icao, designator)
    if airport is None or runway is None:
        return None
    return airport, runway


def tag_text(display_id: str) -> str:
    """Image tag for a runway display id; unknown ids use the default runway."""
    if display_id == NO_LOCATION_DISPLAY_ID:
        return NO_LOCATION_TAG_TEXT
    if display_id in device_config.RUNWAYS:
        return str(device_config.RUNWAYS[display_id]["tag_text"])
    km = _position_km(display_id)
    if km is not None:
        return "NEARBY · %d KM" % km
    found = _split_display_id(display_id)
    if found is None:
        return str(device_config.RUNWAYS[_FALLBACK_ID]["tag_text"])
    airport, runway = found
    return "%s · %s" % (airport.iata or airport.icao, runway.designator)


def empty_heading(display_id: str) -> str:
    """Heading of the empty screen for a runway display id."""
    if display_id == NO_LOCATION_DISPLAY_ID:
        return NO_LOCATION_HEADING
    if display_id in device_config.RUNWAYS:
        return str(device_config.RUNWAYS[display_id]["empty_heading"])
    km = _position_km(display_id)
    if km is not None:
        return "Watching Within %d km" % km
    found = _split_display_id(display_id)
    if found is None:
        return str(device_config.RUNWAYS[_FALLBACK_ID]["empty_heading"])
    return "Watching Runway %s" % found[1].designator


def _spec_from_doc(display_id: str, doc: dict[str, Any]) -> DetectionSpec:
    return DetectionSpec(
        mode=RUNWAY_MODE,
        display_id=display_id,
        zone=fleet_zones.zone_from_geofence(doc),
        geofence=doc,
        tag_text=tag_text(display_id),
        empty_heading=empty_heading(display_id),
    )


def legacy_orly_spec(
    geofence_path: str | None = None, display_id: str = _FALLBACK_ID
) -> DetectionSpec:
    """Spec backed by the hand-tuned geofence file (the kill-switch path).

    Raises OSError or ValueError when the file is unreadable.
    """
    doc = detect.load_geofence(geofence_path)
    return _spec_from_doc(display_id, doc)


def _legacy_spec(display_id: str, geofence_path: str | None) -> DetectionSpec:
    use_file = LEGACY_ORLY_DEFAULT_TO_FILE or os.environ.get(LEGACY_GEOFENCE_ENV) == "1"
    if use_file:
        return legacy_orly_spec(geofence_path, display_id)
    icao, designator = LEGACY_RUNWAY_MAP[display_id]
    airport = airports.find_airport(icao)
    runway = airports.find_runway(icao, designator)
    if airport is None or runway is None:
        raise ValueError("catalogue is missing the legacy runway")
    doc = runway_geofence_doc(airport, runway, display_id, legacy=True)
    return _spec_from_doc(display_id, doc)


def _catalogue_spec(
    detection: Mapping[str, Any], geofence_path: str | None
) -> DetectionSpec | None:
    if detection.get("mode") != RUNWAY_MODE:
        return None
    icao = detection.get("airport")
    designator = detection.get("runway")
    airport = airports.find_airport(icao)
    runway = airports.find_runway(icao, designator)
    if airport is None or runway is None:
        return None
    if not isinstance(icao, str) or not isinstance(designator, str):
        return None
    legacy_id = _LEGACY_BY_RUNWAY.get((icao, designator))
    if legacy_id is not None:
        return _legacy_spec(legacy_id, geofence_path)
    display_id = runway_display_id(icao, designator)
    return _spec_from_doc(display_id, runway_geofence_doc(airport, runway, display_id))


def spec_for(
    device_cfg: Mapping[str, Any],
    location: Any = None,
    legacy_geofence_path: str | None = None,
) -> DetectionSpec:
    """The detection spec for one device.

    Never raises on bad configuration: anything malformed or unknown yields
    the default Orly runway, except a position-mode
    device without a usable location, which yields `no_location_spec()`. Only an OSError from
    reading the legacy geofence file (kill switch on) can escape.
    """
    detection = device_cfg.get("detection") if isinstance(device_cfg, Mapping) else None
    if detection is None:
        tracked = device_cfg.get("tracked_runway") if isinstance(device_cfg, Mapping) else None
        if isinstance(tracked, str) and tracked in LEGACY_RUNWAY_MAP:
            return _legacy_spec(tracked, legacy_geofence_path)
        return _legacy_spec(_FALLBACK_ID, legacy_geofence_path)
    if isinstance(detection, Mapping):
        spec = _position_spec(detection, location)
        if spec is None:
            spec = _catalogue_spec(detection, legacy_geofence_path)
        if spec is not None:
            return spec
    return _legacy_spec(_FALLBACK_ID, legacy_geofence_path)


def validate_runway_selection(icao: Any, designator: Any) -> tuple[str, str]:
    """The (airport, runway) pair when the catalogue has it, else ValueError.

    The error's first argument is a stable code the page maps to its
    messages: "airport" (unknown or malformed identifier) or "runway" (the
    airport exists but has no runway with exactly this designator).
    """
    if airports.find_airport(icao) is None:
        raise ValueError("airport")
    if airports.find_runway(icao, designator) is None:
        raise ValueError("runway")
    if not isinstance(icao, str) or not isinstance(designator, str):
        raise ValueError("airport")
    return icao, designator


def validate_radius_km(radius_km: Any) -> int:
    """The radius when it is a whole number inside the supported bounds."""
    if isinstance(radius_km, bool) or not isinstance(radius_km, int):
        raise ValueError("radius")
    if not RADIUS_KM_MIN <= radius_km <= RADIUS_KM_MAX:
        raise ValueError("radius")
    return radius_km


def apply_runway_selection(state_dir: str, icao: Any, designator: Any) -> None:
    """Store a runway choice for the device whose state lives in `state_dir`.

    The three Orly runways keep the legacy `tracked_runway` id and drop any
    detection object: the live frame's config bytes stay what they were and
    the previous release keeps reading the id it understands. Every other
    runway stores one detection object and leaves `tracked_runway` alone,
    so the previous release still runs on its last Orly runway. Nothing is
    written when validation fails.
    """
    icao, designator = validate_runway_selection(icao, designator)
    legacy_id = _LEGACY_BY_RUNWAY.get((icao, designator))
    if legacy_id is not None:
        device_config.save_device_config(
            state_dir,
            tracked_runway=legacy_id,
            detection=device_config.CLEAR_DETECTION,
        )
        return
    device_config.save_device_config(
        state_dir,
        detection={"mode": RUNWAY_MODE, "airport": icao, "runway": designator},
    )


def apply_position_selection(state_dir: str, radius_km: Any) -> None:
    """Store a position-radius choice. The centre is the device's location
    row, never part of the config file; nothing is written on a bad radius.
    """
    radius = validate_radius_km(radius_km)
    device_config.save_device_config(
        state_dir, detection={"mode": POSITION_MODE, "radius_km": radius}
    )


def _legacy_selection(runway_id: str) -> dict[str, Any]:
    icao, designator = LEGACY_RUNWAY_MAP[runway_id]
    return {"mode": RUNWAY_MODE, "airport": icao, "runway": designator}


def current_selection(device_cfg: Any) -> dict[str, Any]:
    """The saved setting as the page shows it: a record with `mode`, plus
    `airport` and `runway` for runway mode or `radius_km` for position mode.
    Legacy runway ids map to their catalogue designators; anything
    malformed or unknown reads as the default Orly runway.
    """
    if not isinstance(device_cfg, Mapping):
        return _legacy_selection(_FALLBACK_ID)
    detection = device_config.normalise_detection(device_cfg.get("detection"))
    if detection is not None:
        if detection["mode"] == POSITION_MODE:
            try:
                return {"mode": POSITION_MODE, "radius_km": validate_radius_km(detection["radius_km"])}
            except ValueError:
                return _legacy_selection(_FALLBACK_ID)
        if airports.find_runway(detection["airport"], detection["runway"]) is not None:
            return dict(detection)
        return _legacy_selection(_FALLBACK_ID)
    tracked = device_cfg.get("tracked_runway")
    if isinstance(tracked, str) and tracked in LEGACY_RUNWAY_MAP:
        return _legacy_selection(tracked)
    return _legacy_selection(_FALLBACK_ID)
