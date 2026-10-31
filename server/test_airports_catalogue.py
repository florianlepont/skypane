"""France runway catalogue: offline build rules, data checks and loader."""

import importlib.util
import json
import math
import re
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUILD_PATH = os.path.join(os.path.dirname(_HERE), "scripts", "build_airports.py")

_spec = importlib.util.spec_from_file_location("build_airports_under_test", _BUILD_PATH)
assert _spec is not None and _spec.loader is not None
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

AIRPORT_COLUMNS = [
    "id", "ident", "type", "name", "latitude_deg", "longitude_deg", "elevation_ft",
    "continent", "iso_country", "iso_region", "municipality", "scheduled_service",
    "icao_code", "iata_code", "gps_code", "local_code", "home_link",
    "wikipedia_link", "keywords",
]
RUNWAY_COLUMNS = [
    "id", "airport_ref", "airport_ident", "length_ft", "width_ft", "surface",
    "lighted", "closed", "le_ident", "le_latitude_deg", "le_longitude_deg",
    "le_elevation_ft", "le_heading_degT", "le_displaced_threshold_ft", "he_ident",
    "he_latitude_deg", "he_longitude_deg", "he_elevation_ft", "he_heading_degT",
    "he_displaced_threshold_ft",
]
SNAPSHOT = {"date": "2026-01-01", "airports_sha256": "a", "runways_sha256": "b"}
M_PER_DEG = 111320.0

_row_ids = iter(range(1, 10_000))


def airport(ident, kind="small_airport", lat=48.0, lon=2.0, iata=""):
    row = dict.fromkeys(AIRPORT_COLUMNS, "")
    row.update(
        id=str(next(_row_ids)), ident=ident, type=kind, name="Airport " + ident,
        latitude_deg=str(lat), longitude_deg=str(lon), iso_country="FR",
        municipality="Town", iata_code=iata,
    )
    return row


def east_west(lat, lon0=2.0, length_m=2000.0):
    """Thresholds of an east-west runway, 6-decimal degrees."""
    lon1 = lon0 + length_m / (M_PER_DEG * math.cos(math.radians(lat)))
    return (lat, lon0), (lat, round(lon1, 6))


def runway(ident, le, he, thresholds, **extra):
    row = dict.fromkeys(RUNWAY_COLUMNS, "")
    (lat0, lon0), (lat1, lon1) = thresholds
    row.update(
        id=str(next(_row_ids)), airport_ident=ident, surface="ASP", closed="0",
        le_ident=le, he_ident=he, le_latitude_deg=str(lat0), le_longitude_deg=str(lon0),
        he_latitude_deg=str(lat1), he_longitude_deg=str(lon1),
    )
    row.update(extra)
    return row


def run(airports, runways):
    return build.build_catalogue(airports, runways, SNAPSHOT)


def reasons(exclusions):
    return {e["ident"]: e["reason"] for e in exclusions}


def test_filter_traps_yield_only_valid_rows_and_one_exclusion_each():
    good = east_west(48.0)
    airports = [airport("LFAA")] + [
        airport(ident, kind)
        for ident, kind in [
            ("LFAB", "small_airport"), ("LFAC", "small_airport"), ("LFAD", "closed"),
            ("LFAE", "heliport"), ("FR-0001", "small_airport"), ("LFAF", "small_airport"),
            ("LFAG", "small_airport"), ("LFAH", "small_airport"), ("LFAI", "small_airport"),
            ("LFAJ", "small_airport"), ("LFAK", "small_airport"),
        ]
    ]
    short = east_west(48.0, length_m=50.0)
    bearing_50 = ((48.0, 2.0), (48.0 + 1300 / M_PER_DEG, 2.0 + 1500 / (M_PER_DEG * 0.669)))
    runways = [
        runway("LFAA", "09", "27", good),
        runway("LFAB", "09", "27", good, he_latitude_deg="", he_longitude_deg=""),
        runway("LFAC", "09", "27", good, closed="1"),
        runway("LFAD", "09", "27", good),
        runway("LFAE", "09", "27", good),
        runway("FR-0001", "09", "27", good),
        runway("LFAF", "16G", "34G", good),
        runway("LFAG", "08H", "26H", good),
        runway("LFAH", "09", "27", good, surface="WATER"),
        runway("LFAI", "09", "27", bearing_50),
        runway("LFAJ", "09", "27", short),
        runway("LFAK", "09", "27", good, he_latitude_deg="abc"),
    ]
    catalogue, exclusions = run(airports, runways)
    assert [a["icao"] for a in catalogue["airports"]] == ["LFAA"]
    assert reasons(exclusions) == {
        "LFAB": "missing_threshold", "LFAC": "closed", "LFAD": "airport_type",
        "LFAE": "airport_type", "FR-0001": "bad_ident", "LFAF": "designator",
        "LFAG": "designator", "LFAH": "water", "LFAI": "bearing_mismatch",
        "LFAJ": "too_short", "LFAK": "bad_number",
    }
    assert len(exclusions) == 11


def test_validation_rejects_non_reciprocal_pair_and_duplicates():
    good = east_west(48.0)
    with pytest.raises(ValueError, match="reciprocal"):
        run([airport("LFAA")], [runway("LFAA", "09", "20", good)])
    twice = [runway("LFAA", "09", "27", good), runway("LFAA", "09", "27", good)]
    with pytest.raises(ValueError, match="duplicate"):
        run([airport("LFAA")], twice)


def test_validation_rejects_oversized_csv(tmp_path):
    path = tmp_path / "big.csv"
    path.write_text("a\n")
    original = build.MAX_CSV_BYTES
    build.MAX_CSV_BYTES = 1
    try:
        with pytest.raises(ValueError, match="larger"):
            build.read_csv(str(path))
    finally:
        build.MAX_CSV_BYTES = original


def test_rounding_float32_noise_is_rounded_before_use():
    noisy = (("48.719398498535156", "2.358590030670166"), ("48.727401733398438", "2.4020700454711914"))
    row = runway("LFPO", "07", "25", noisy)
    catalogue, _ = run([airport("LFPO", lat=48.729499, lon=2.358963)], [row])
    thresholds = catalogue["airports"][0]["runways"][0]["thresholds"]
    assert thresholds == [{"lat": 48.719398, "lon": 2.35859}, {"lat": 48.727402, "lon": 2.40207}]
    assert build.parse_coord("48.719398498535156", 90.0) == 48.719398


def test_swap_lower_runway_number_comes_first_with_its_thresholds():
    west, east = east_west(48.0)
    row = runway("LFDH", "27", "09", (east, west))
    catalogue, exclusions = run([airport("LFDH")], [row])
    record = catalogue["airports"][0]["runways"][0]
    assert exclusions == []
    assert (record["designator"], record["le"], record["he"]) == ("09/27", "09", "27")
    assert record["thresholds"][0] == {"lat": west[0], "lon": west[1]}
    assert record["bearing_deg"] == pytest.approx(90.0, abs=0.1)


def two_runways(lat_offset_deg, second=("09C", "27C")):
    first = east_west(48.0)
    other = east_west(48.0 + lat_offset_deg)
    return [runway("LFAA", "09", "27", first), runway("LFAA", second[0], second[1], other)]


def widths(runways):
    catalogue, _ = run([airport("LFAA")], runways)
    return {r["designator"]: r for r in catalogue["airports"][0]["runways"]}


def test_half_width_parallel_neighbours_use_half_the_gap():
    result = widths(two_runways(0.003467))
    assert result["09/27"]["half_width_m"] == pytest.approx(193.0, abs=0.1)
    assert result["09C/27C"]["half_width_m"] == pytest.approx(193.0, abs=0.1)
    assert result["09/27"]["ground_half_width_m"] == 75.0


def test_half_width_without_neighbour_is_exactly_the_default():
    catalogue, _ = run([airport("LFAA")], [runway("LFAA", "09", "27", east_west(48.0))])
    only = catalogue["airports"][0]["runways"][0]
    assert only["half_width_m"] == 500.0
    assert only["ground_half_width_m"] == 75.0


def test_half_width_collinear_duplicates_hit_the_floor_not_zero():
    result = widths(two_runways(0.0))
    for record in result.values():
        assert record["half_width_m"] == 50.0
        assert record["ground_half_width_m"] == 50.0


def test_half_width_far_apart_parallel_runways_keep_the_default():
    result = widths(two_runways(0.02))
    assert {r["half_width_m"] for r in result.values()} == {500.0}


def test_half_width_ignores_a_neighbour_beyond_the_parallel_limit():
    lat0, lon0 = 48.0, 2.0
    bearing = math.radians(102.6)
    dx, dy = 2000.0 * math.sin(bearing), 2000.0 * math.cos(bearing)
    start = (round(lat0 + 300 / M_PER_DEG, 6), lon0)
    end = (
        round(start[0] + dy / M_PER_DEG, 6),
        round(lon0 + dx / (M_PER_DEG * math.cos(math.radians(lat0))), 6),
    )
    rows = [runway("LFAA", "09", "27", east_west(lat0)), runway("LFAA", "10", "28", (start, end))]
    result = widths(rows)
    assert result["09/27"]["half_width_m"] == 500.0
    assert result["10/28"]["half_width_m"] == 500.0
    assert build.PARALLEL_AXIS_DEG < 12.6


def test_half_width_stored_values_are_never_non_positive():
    for offset in (0.0, 0.0002, 0.001, 0.003467, 0.02):
        for record in widths(two_runways(offset)).values():
            assert record["half_width_m"] >= build.MIN_HALF_WIDTH_M
            assert record["ground_half_width_m"] == min(75.0, record["half_width_m"])


def test_filter_known_bad_row_is_listed_with_its_reason():
    bad_row = runway("TFFA", "09", "27", east_west(16.3, lon0=-61.3))
    catalogue, exclusions = run([airport("TFFA", lat=16.3, lon=-61.3)], [bad_row])
    assert catalogue["airports"] == []
    assert exclusions[0]["reason"] == "known_bad_survey"


def test_filter_declination_sized_deviation_is_kept():
    start = (-20.88, 55.4)
    end = (round(start[0] - 0.0108, 6), round(start[1] + 0.0229, 6))
    catalogue, exclusions = run(
        [airport("FMEE", lat=-20.88, lon=55.4)], [runway("FMEE", "14", "32", (start, end))]
    )
    assert exclusions == [] and len(catalogue["airports"][0]["runways"]) == 1


# ---- committed data -------------------------------------------------------

_ROOT = os.path.dirname(_HERE)
_DATA = os.path.join(_ROOT, "scripts", "data")
_CATALOGUE = os.path.join(_HERE, "data", "airports_fr.json")


def load_committed():
    with open(_CATALOGUE, encoding="utf-8") as handle:
        return json.load(handle)


def by_icao():
    return {a["icao"]: a for a in load_committed()["airports"]}


def runway_map(icao):
    return {r["designator"]: r for r in by_icao()[icao]["runways"]}


def test_reproducible_build_matches_committed(tmp_path):
    catalogue = tmp_path / "airports_fr.json"
    exclusions = tmp_path / "exclusions.json"
    build.build(_DATA, str(catalogue), str(exclusions))
    with open(_CATALOGUE, "rb") as handle:
        assert catalogue.read_bytes() == handle.read()
    with open(os.path.join(_DATA, "ourairports-exclusions.json"), "rb") as handle:
        assert exclusions.read_bytes() == handle.read()
    with open(os.path.join(_DATA, "ourairports-source.json"), encoding="utf-8") as handle:
        source = json.load(handle)
    assert source["snapshot_date"] == "2026-10-31"
    for name, key in (("ourairports-fr-airports.csv", "airports"), ("ourairports-fr-runways.csv", "runways")):
        with open(os.path.join(_DATA, name), "rb") as handle:
            assert build.sha256_bytes(handle.read()) == source["subset"][key]["sha256"]
    assert len(source["full"]["airports"]["sha256"]) == 64
    assert len(source["full"]["runways"]["sha256"]) == 64


def test_absent_rows():
    data = load_committed()
    pairs = {(a["icao"], r["designator"]) for a in data["airports"] for r in a["runways"]}
    assert ("NTGY", "18/36") not in pairs and ("TFFA", "09/27") not in pairs
    for icao, designator in pairs:
        assert not re.match(r"^[A-Z]{2}-\d{4}$", icao)
        assert not re.search(r"[GH]/", designator)
    for airport_record in data["airports"]:
        assert airport_record["runways"]
        for record in airport_record["runways"]:
            assert len(record["thresholds"]) == 2


def test_designators_real():
    assert set(runway_map("LFPG")) == {"08L/26R", "08R/26L", "09L/27R", "09R/27L"}
    assert set(runway_map("LFDH")) == {"18/36"}


def test_lfpo():
    runways = runway_map("LFPO")
    assert set(runways) == {"02/20", "06/24", "07/25"}
    with open(os.path.join(_ROOT, "adsb-test", "runway3.json"), encoding="utf-8") as handle:
        legacy = json.load(handle)["runways"]["3"]["runway"]["thresholds"]
    assert runways["07/25"]["thresholds"] == legacy
    assert all(r["half_width_m"] == 500.0 for r in runways.values())
    deviation = abs(runways["07/25"]["bearing_deg"] - runways["06/24"]["bearing_deg"])
    assert build.PARALLEL_AXIS_DEG < deviation


def test_parallel_lfpg():
    for designator in ("08L/26R", "08R/26L"):
        assert runway_map("LFPG")[designator]["half_width_m"] == pytest.approx(193, abs=1)
    for designator in ("09L/27R", "09R/27L"):
        assert runway_map("LFPG")[designator]["half_width_m"] == pytest.approx(192, abs=1)


def test_parallel_other_airports():
    for record in by_icao()["LFMN"]["runways"]:
        assert record["half_width_m"] == pytest.approx(150, abs=5)
    for record in by_icao()["LFBO"]["runways"]:
        assert record["half_width_m"] == pytest.approx(144.7, abs=0.5)
    assert {r["half_width_m"] for r in by_icao()["LFMT"]["runways"]} == {500.0}


def test_floor_cases():
    assert all(r["half_width_m"] >= 50 for r in by_icao()["LFPK"]["runways"])
    assert all(r["half_width_m"] >= 50 for r in by_icao()["LFGI"]["runways"])
    assert runway_map("LFGI")["02/20"]["half_width_m"] == 50.0


def test_counts():
    data = load_committed()
    airports = data["airports"]
    assert 265 <= len(airports) <= 280
    assert 330 <= sum(len(a["runways"]) for a in airports) <= 350
    iatas = [a["iata"] for a in airports if a["iata"]]
    assert len(iatas) == len(set(iatas))
    for record in airports:
        assert re.match(r"^[A-Z]{2}[A-Z0-9]{2}$", record["icao"])
        for rw in record["runways"]:
            assert rw["half_width_m"] > 0
            assert rw["ground_half_width_m"] == min(75, rw["half_width_m"])


def test_corridor_inside_zone():
    for record in load_committed()["airports"]:
        arp = (record["lat"], record["lon"])
        for rw in record["runways"]:
            pair = {"thresholds": [(t["lat"], t["lon"]) for t in rw["thresholds"]]}
            assert build.corners_within_zone(pair, rw["half_width_m"], arp), record["icao"]
