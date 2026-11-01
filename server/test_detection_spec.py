"""Behaviour of the runway-mode detection spec against the real catalogue."""

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import airports, detection, device_config, fleet_zones  # noqa: E402
from server.plane import detect  # noqa: E402

LEGACY_IDS = ("3", "06-24", "02-20")


@pytest.fixture(autouse=True)
def _no_kill_switch(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)


def _all_runways():
    for airport in airports.load_catalogue().values():
        for runway in airport.runways:
            yield airport, runway


def test_legacy_runway_spec_keeps_zone_key_and_text():
    spec = detection.spec_for({"tracked_runway": "3", "detection": None})
    assert spec.mode == "runway"
    assert spec.display_id == "3"
    assert spec.zone.key == "48.7233|2.3794|5.0"
    assert spec.zone == fleet_zones.Zone(48.7233, 2.3794, 5.0)
    assert spec.tag_text == "ORY · RWY 3"
    assert spec.empty_heading == "Watching Runway 3"


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_legacy_text_equals_device_config_registry(runway_id):
    spec = detection.spec_for({"tracked_runway": runway_id})
    assert spec.display_id == runway_id
    assert spec.tag_text == device_config.RUNWAYS[runway_id]["tag_text"]
    assert spec.empty_heading == device_config.RUNWAYS[runway_id]["empty_heading"]
    assert detection.tag_text(runway_id) == spec.tag_text
    assert detection.empty_heading(runway_id) == spec.empty_heading


def test_catalogue_runway_spec_text_uses_iata():
    spec = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}}
    )
    assert spec.display_id == "LFPG:08L/26R"
    assert spec.tag_text == "CDG · 08L/26R"
    assert spec.empty_heading == "Watching Runway 08L/26R"


def test_airport_without_iata_uses_icao_in_tag():
    airport = next(a for a in airports.load_catalogue().values() if not a.iata)
    runway = airport.runways[0]
    display_id = detection.runway_display_id(airport.icao, runway.designator)
    assert detection.tag_text(display_id) == "%s · %s" % (airport.icao, runway.designator)


@pytest.mark.parametrize(
    "bad",
    [
        {"mode": "runway", "airport": "ZZZZ", "runway": "08L/26R"},
        {"mode": "runway", "airport": "LFPG", "runway": "01/19"},
        {"mode": "runway", "airport": "LFPG"},
        {"mode": "runway", "airport": 5, "runway": ["x"]},
        {"mode": "bogus", "airport": "LFPG", "runway": "08L/26R"},
        {"mode": "position", "radius_nm": 5},
        {},
        "LFPG:08L/26R",
        42,
        ["runway"],
    ],
)
def test_bad_detection_object_falls_back_to_legacy_runway(bad):
    spec = detection.spec_for({"tracked_runway": "06-24", "detection": bad})
    assert spec.display_id == "3"
    assert spec.zone.key == "48.7233|2.3794|5.0"


def test_non_mapping_config_never_raises():
    spec = detection.spec_for(None)  # type: ignore[arg-type]
    assert spec.display_id == "3"


def test_every_catalogue_runway_document_is_self_consistent():
    count = 0
    for airport, runway in _all_runways():
        display_id = detection.runway_display_id(airport.icao, runway.designator)
        doc = detection.runway_geofence_doc(airport, runway, display_id)
        count += 1
        block = doc["runways"][display_id]
        assert detect._effective_runway_id(doc, display_id) == display_id
        assert [(t["lat"], t["lon"]) for t in block["runway"]["thresholds"]] == list(
            runway.thresholds
        )
        assert block["corridor"] == {
            "half_width_m": runway.half_width_m,
            "extension_m": 2500,
            "axis_tolerance_deg": 30,
            "ground_half_width_m": runway.ground_half_width_m,
        }
        assert doc["radius_nm"] == 5.0
        assert doc["alt_ceiling_ft"] == 3000
        assert doc["center"] == {"lat": round(airport.lat, 4), "lon": round(airport.lon, 4)}
    assert count > 300


def test_bbox_contains_all_four_corridor_corners_and_is_tight():
    airport = airports.find_airport("LFPG")
    runway = airports.find_runway("LFPG", "08L/26R")
    display_id = "LFPG:08L/26R"
    doc = detection.runway_geofence_doc(airport, runway, display_id)
    axis = detect.runway_axis(doc, runway_id=display_id)
    bbox = doc["bbox"]
    hw = runway.half_width_m
    for along in (-2500, axis["length_m"] + 2500):
        for cross in (-hw, hw):
            x = along * axis["ux"] - cross * axis["uy"]
            y = along * axis["uy"] + cross * axis["ux"]
            lat = axis["lat0"] + y / detect._M_PER_DEG_LAT
            lon = axis["lon0"] + x / axis["lon_scale"]
            assert bbox["lat_min"] <= lat <= bbox["lat_max"]
            assert bbox["lon_min"] <= lon <= bbox["lon_max"]
    # Tight to within a few metres of the corners (1e-5 degrees is about 1 m).
    assert bbox["lat_max"] - bbox["lat_min"] < 0.1
    corner_lats = []
    for along in (-2500, axis["length_m"] + 2500):
        for cross in (-hw, hw):
            y = along * axis["uy"] + cross * axis["ux"]
            corner_lats.append(axis["lat0"] + y / detect._M_PER_DEG_LAT)
    assert abs(bbox["lat_min"] - min(corner_lats)) < 2e-6
    assert abs(bbox["lat_max"] - max(corner_lats)) < 2e-6


def test_runways_of_one_airport_share_a_zone_but_not_a_runway():
    first = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}}
    )
    second = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPG", "runway": "09L/27R"}}
    )
    assert first.zone.key == second.zone.key
    assert first.display_id != second.display_id
    assert set(first.geofence["runways"]) == {"LFPG:08L/26R"}


def test_catalogue_selection_of_orly_runway_resolves_to_legacy_id():
    spec = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPO", "runway": "07/25"}}
    )
    assert spec.display_id == "3"
    assert spec.zone.key == "48.7233|2.3794|5.0"


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_legacy_documents_carry_frozen_values(runway_id):
    spec = detection.spec_for({"tracked_runway": runway_id})
    doc = spec.geofence
    assert doc["bbox"] == dict(detection.LEGACY_ORLY_BBOX)
    assert doc["center"] == {"lat": 48.7233, "lon": 2.3794}
    assert doc["radius_nm"] == 5.0
    assert doc["alt_ceiling_ft"] == 3000
    assert detect._effective_runway_id(doc, runway_id) == runway_id
    assert doc["runways"][runway_id]["corridor"]["half_width_m"] == 500.0


def test_kill_switch_loads_the_geofence_file(monkeypatch):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    spec = detection.spec_for({"tracked_runway": "06-24"})
    with open(detect.DEFAULT_GEOFENCE) as handle:
        assert spec.geofence == json.load(handle)
    assert spec.display_id == "06-24"
    assert spec.zone.key == "48.7233|2.3794|5.0"
    assert spec.tag_text == "ORY · RWY 06/24"


def test_kill_switch_uses_the_given_path_and_ignores_other_ids(monkeypatch, tmp_path):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    custom = tmp_path / "geofence.json"
    with open(detect.DEFAULT_GEOFENCE) as handle:
        doc = json.load(handle)
    doc["alt_ceiling_ft"] = 1234
    custom.write_text(json.dumps(doc))
    legacy = detection.spec_for({"tracked_runway": "3"}, legacy_geofence_path=str(custom))
    assert legacy.geofence["alt_ceiling_ft"] == 1234
    other = detection.spec_for(
        {"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}},
        legacy_geofence_path=str(custom),
    )
    assert other.geofence["alt_ceiling_ft"] == 3000


def test_kill_switch_off_gives_generated_document():
    spec = detection.spec_for({"tracked_runway": "3"})
    assert list(spec.geofence["runways"]) == ["3"]
    assert "center" in spec.geofence and "source" not in spec.geofence["center"]


# ---------------------------------------------------------------
# Position mode
# ---------------------------------------------------------------

_POSITION_CFG = {"detection": {"mode": "position", "radius_km": 9}}


@pytest.mark.parametrize("km,nm", [(9, 4.86), (4, 2.16), (28, 15.12)])
def test_bounds_km_to_nm(km, nm):
    assert detection.km_to_nm(km) == nm


@pytest.mark.parametrize("radius", [1, 29, True, 9.5, "9", None, 9.0])
def test_bounds_radius_rejected(radius):
    with pytest.raises(ValueError) as err:
        detection.validate_position(48.86, 2.35, radius)
    assert err.value.args[0] == "radius"


@pytest.mark.parametrize("radius", [2, 3, 28, 9])
def test_bounds_radius_accepted(radius):
    assert detection.validate_position(48.86, 2.35, radius)[2] == radius


@pytest.mark.parametrize(
    "lat,lon",
    [(41.29, 2.0), (51.16, 2.0), (48.0, -5.21), (48.0, 9.61), (0.0, 0.0)],
)
def test_bounds_outside_france(lat, lon):
    with pytest.raises(ValueError) as err:
        detection.validate_position(lat, lon, 9)
    assert err.value.args[0] == "outside_france"


@pytest.mark.parametrize(
    "lat,lon", [(41.30, -5.20), (51.15, 9.60), (41.296, -5.196), (51.149, 9.601)]
)
def test_bounds_france_box_inclusive_on_rounded_values(lat, lon):
    assert detection.validate_position(lat, lon, 9)[:2] == (
        detection.round_coordinate(lat),
        detection.round_coordinate(lon),
    )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "48.8", None, True])
def test_bounds_non_finite_location_rejected(bad):
    with pytest.raises(ValueError) as err:
        detection.validate_position(bad, 2.35, 9)
    assert err.value.args[0] == "location"


def test_round_negative_zero_normalised():
    value = detection.round_coordinate(-0.001)
    assert value == 0.0
    assert str(value) == "0.0"


def test_position_zone_rounds_and_converts():
    zone = detection.position_zone(48.85661, 2.35222, 9)
    assert zone == fleet_zones.Zone(48.86, 2.35, 4.86)


def test_position_zone_key_has_no_negative_zero():
    assert detection.position_zone(48.8566, -0.001, 9).key == "48.86|0.0|4.86"


def test_position_spec_fields():
    spec = detection.spec_for(_POSITION_CFG, location=(48.85661, 2.35222))
    assert spec.mode == "position"
    assert spec.display_id == "position:9"
    assert spec.zone == fleet_zones.Zone(48.86, 2.35, 4.86)
    assert spec.tag_text == "NEARBY · 9 KM"
    assert spec.empty_heading == "Watching Within 9 km"
    doc = spec.geofence
    assert doc["detection_mode"] == "position"
    assert doc["center"] == {"lat": 48.86, "lon": 2.35}
    assert doc["radius_nm"] == 4.86
    assert doc["alt_ceiling_ft"] is None
    assert "runways" not in doc


def test_position_spec_keeps_no_unrounded_coordinate():
    spec = detection.spec_for(_POSITION_CFG, location=(48.85661, 2.35222))
    text = repr(spec) + json.dumps(spec.geofence)
    assert "48.85661" not in text
    assert "2.35222" not in text


def test_position_spec_zone_matches_zone_from_document():
    spec = detection.spec_for(_POSITION_CFG, location=(48.85661, 2.35222))
    assert fleet_zones.zone_from_geofence(spec.geofence) == spec.zone


@pytest.mark.parametrize(
    "cfg,location",
    [
        ({"detection": {"mode": "position", "radius_km": 99}}, (48.8, 2.3)),
        ({"detection": {"mode": "position", "radius_km": 9.5}}, (48.8, 2.3)),
        ({"detection": {"mode": "position", "radius_km": True}}, (48.8, 2.3)),
        ({"detection": {"mode": "position"}}, (48.8, 2.3)),
    ],
)
def test_position_spec_bad_input_falls_back(cfg, location):
    spec = detection.spec_for(cfg, location=location)
    assert spec.mode == "runway"
    assert spec.display_id == "3"


@pytest.mark.parametrize(
    "location",
    [None, (40.0, 2.0), (48.8, "x"), "48.8,2.3", (float("nan"), 2.3), (48.8,)],
)
def test_position_without_usable_location_is_a_no_location_spec(location):
    spec = detection.spec_for(_POSITION_CFG, location=location)
    assert spec.no_location is True
    assert spec.display_id == detection.NO_LOCATION_DISPLAY_ID
    assert spec.tag_text == "SET A LOCATION"
    assert spec.empty_heading == "Set a location"
    assert detection.tag_text(spec.display_id) == spec.tag_text
    assert detection.empty_heading(spec.display_id) == spec.empty_heading


def test_usable_location_and_other_modes_are_not_no_location():
    assert detection.spec_for(_POSITION_CFG, location=(48.8, 2.3)).no_location is False
    assert detection.spec_for({"tracked_runway": "3"}).no_location is False
    assert detection.spec_for({"tracked_runway": "3"}, location=None).display_id == "3"
    bad_radius = detection.spec_for(
        {"detection": {"mode": "position", "radius_km": 99}}, location=None)
    assert bad_radius.no_location is False
    assert bad_radius.display_id == "3"


def test_shared_zone_for_nearby_locations():
    first = detection.spec_for(_POSITION_CFG, location=(48.8566, 2.3522))
    second = detection.spec_for(_POSITION_CFG, location=(48.8601, 2.3500))
    other = detection.spec_for(
        {"detection": {"mode": "position", "radius_km": 10}}, location=(48.8566, 2.3522)
    )
    assert first.zone.key == second.zone.key
    assert first.zone.key != other.zone.key


def test_km_to_nm_minimum_radius():
    assert detection.km_to_nm(2) == 1.08
