"""Per-device detection spec for runway mode.

`spec_for` turns a device's stored configuration into a zone to poll and a
geofence-shaped document that server.plane.detect consumes unchanged, so
every runway shares one set of gating functions and differs only in data.

The three legacy Orly ids ("3", "06-24", "02-20") resolve to the catalogue's
LFPO rows but keep a frozen bounding box, centre, radius and ceiling taken
from adsb-test/runway3.json. The generic corridor rectangle is not clipped
the way the hand-tuned box is, so deriving the box generically would change
decisions at the corridor tips; carrying the frozen values keeps the Orly
frame's behaviour and its zone key unchanged.

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


@dataclass(frozen=True)
class DetectionSpec:
    """What one device polls and how its aircraft are gated and labelled."""

    mode: str
    display_id: str
    zone: fleet_zones.Zone
    geofence: dict[str, Any]
    tag_text: str
    empty_heading: str
    fail_safe: bool


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
    if display_id in device_config.RUNWAYS:
        return str(device_config.RUNWAYS[display_id]["tag_text"])
    found = _split_display_id(display_id)
    if found is None:
        return str(device_config.RUNWAYS[_FALLBACK_ID]["tag_text"])
    airport, runway = found
    return "%s · %s" % (airport.iata or airport.icao, runway.designator)


def empty_heading(display_id: str) -> str:
    """Heading of the empty screen for a runway display id."""
    if display_id in device_config.RUNWAYS:
        return str(device_config.RUNWAYS[display_id]["empty_heading"])
    found = _split_display_id(display_id)
    if found is None:
        return str(device_config.RUNWAYS[_FALLBACK_ID]["empty_heading"])
    return "Watching Runway %s" % found[1].designator


def _spec_from_doc(display_id: str, doc: dict[str, Any], fail_safe: bool) -> DetectionSpec:
    return DetectionSpec(
        mode=RUNWAY_MODE,
        display_id=display_id,
        zone=fleet_zones.zone_from_geofence(doc),
        geofence=doc,
        tag_text=tag_text(display_id),
        empty_heading=empty_heading(display_id),
        fail_safe=fail_safe,
    )


def legacy_orly_spec(
    geofence_path: str | None = None, display_id: str = _FALLBACK_ID, fail_safe: bool = False
) -> DetectionSpec:
    """Spec backed by the hand-tuned geofence file (the kill-switch path).

    Raises OSError or ValueError when the file is unreadable.
    """
    doc = detect.load_geofence(geofence_path)
    return _spec_from_doc(display_id, doc, fail_safe)


def _legacy_spec(
    display_id: str, geofence_path: str | None, fail_safe: bool
) -> DetectionSpec:
    use_file = LEGACY_ORLY_DEFAULT_TO_FILE or os.environ.get(LEGACY_GEOFENCE_ENV) == "1"
    if use_file:
        return legacy_orly_spec(geofence_path, display_id, fail_safe)
    icao, designator = LEGACY_RUNWAY_MAP[display_id]
    airport = airports.find_airport(icao)
    runway = airports.find_runway(icao, designator)
    if airport is None or runway is None:
        raise ValueError("catalogue is missing the legacy runway")
    doc = runway_geofence_doc(airport, runway, display_id, legacy=True)
    return _spec_from_doc(display_id, doc, fail_safe)


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
    assert isinstance(icao, str) and isinstance(designator, str)
    legacy_id = _LEGACY_BY_RUNWAY.get((icao, designator))
    if legacy_id is not None:
        return _legacy_spec(legacy_id, geofence_path, False)
    display_id = runway_display_id(icao, designator)
    return _spec_from_doc(display_id, runway_geofence_doc(airport, runway, display_id), False)


def spec_for(
    device_cfg: Mapping[str, Any],
    location: Any = None,
    legacy_geofence_path: str | None = None,
) -> DetectionSpec:
    """The detection spec for one device.

    Never raises on bad configuration: anything malformed or unknown yields
    the default Orly runway with `fail_safe` True. Only an OSError from
    reading the legacy geofence file (kill switch on) can escape.
    """
    detection = device_cfg.get("detection") if isinstance(device_cfg, Mapping) else None
    if detection is None:
        tracked = device_cfg.get("tracked_runway") if isinstance(device_cfg, Mapping) else None
        if isinstance(tracked, str) and tracked in LEGACY_RUNWAY_MAP:
            return _legacy_spec(tracked, legacy_geofence_path, False)
        return _legacy_spec(_FALLBACK_ID, legacy_geofence_path, tracked is not None)
    if isinstance(detection, Mapping):
        spec = _catalogue_spec(detection, legacy_geofence_path)
        if spec is not None:
            return spec
    return _legacy_spec(_FALLBACK_ID, legacy_geofence_path, True)
