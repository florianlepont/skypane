"""The generated detection documents reproduce the hand-tuned Orly geofence.

Every comparison is strict equality: candidate sets, tagged geometry and
normalised selections (all keys but seen_pos) must be identical between the
legacy geofence file and the generic path, for committed fixtures and for a
deterministic sweep with dense bands at every gate edge.
"""

import glob
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import detection_sweep  # noqa: E402
from server import airports, detection  # noqa: E402
from server.plane import detect  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
LEGACY_IDS = ("3", "06-24", "02-20")
RUNWAY_FILE = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")


@pytest.fixture(autouse=True)
def _no_kill_switch(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)


@pytest.fixture(scope="module")
def legacy_doc():
    return detect.load_geofence()


def _generic_doc(runway_id):
    return detection.spec_for({"tracked_runway": runway_id}).geofence


def _fixture_records():
    """(name, records) for every record list in the committed fixtures."""
    groups = []
    for path in sorted(glob.glob(os.path.join(FIXTURES_DIR, "geofence_*.json"))):
        with open(path) as handle:
            data = json.load(handle)
        name = os.path.basename(path)
        if "adsbfi" in data:
            groups.append((name + ":adsbfi", data["adsbfi"]["aircraft"]))
            groups.append((name + ":adsblol", data["adsblol"]["ac"]))
            continue
        records = data.get("ac", data.get("aircraft"))
        groups.append((name, records))
    with open(os.path.join(FIXTURES_DIR, "track_arrival_440cb1.json")) as handle:
        groups.append(("track_arrival_440cb1.json", json.load(handle)))
    return groups


def _strip(selection):
    return None if selection is None else {k: v for k, v in selection.items() if k != "seen_pos"}


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_replay_fixtures_candidates_and_selection_identical(legacy_doc, runway_id):
    generic = _generic_doc(runway_id)
    groups = _fixture_records()
    assert sum(len(records) for _, records in groups) >= 14
    for name, records in groups:
        assert detect.runway_candidates(records, legacy_doc, runway_id) == (
            detect.runway_candidates(records, generic, runway_id)
        ), name
        for results in ([("a", records)],):
            assert _strip(detect.select_from_provider_results(results, legacy_doc, runway_id)) == (
                _strip(detect.select_from_provider_results(results, generic, runway_id))
            ), name


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_replay_two_provider_pavement_pair_both_orders(legacy_doc, runway_id):
    generic = _generic_doc(runway_id)
    with open(os.path.join(FIXTURES_DIR, "geofence_pavement_pair.json")) as handle:
        pair = json.load(handle)
    first = ("adsbfi", pair["adsbfi"]["aircraft"])
    second = ("adsblol", pair["adsblol"]["ac"])
    for results in ([first, second], [second, first]):
        old = detect.select_from_provider_results(results, legacy_doc, runway_id)
        new = detect.select_from_provider_results(results, generic, runway_id)
        assert _strip(old) == _strip(new)
        if runway_id == "3":
            assert old is not None and old["corroborated"] is True


def _swept(runway_id, legacy_doc):
    generic = _generic_doc(runway_id)
    return generic, list(detection_sweep.sweep_cells(generic, runway_id))


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_sweep_decisions_identical_on_every_cell(legacy_doc, runway_id):
    generic, cells = _swept(runway_id, legacy_doc)
    assert len(cells) >= 100_000
    assert detection_sweep.compare(legacy_doc, generic, runway_id, cells) == []
    assert detection_sweep.compare_selections(legacy_doc, generic, runway_id, cells) == []
    candidates = detect.runway_candidates(cells, legacy_doc, runway_id)
    assert candidates, "the sweep must contain accepted cells or it proves nothing"
    assert len(candidates) < len(cells)


def test_sweep_includes_the_gate_edge_bands(legacy_doc):
    generic, cells = _swept("3", legacy_doc)
    axis = detect.runway_axis(generic, runway_id="3")
    seen = set()
    for ac in cells:
        _, cross = detect.along_cross_track_m(ac["lat"], ac["lon"], generic, axis=axis)
        for edge in (499.0, 500.0, 501.0):
            if abs(abs(cross) - edge) < 1e-6:
                seen.add(edge)
    assert seen == {499.0, 500.0, 501.0}
    alongs = {
        round(detect.along_cross_track_m(ac["lat"], ac["lon"], generic, axis=axis)[0], 3)
        for ac in cells
    }
    assert {-2500.0, -2499.0} <= alongs


def test_sweep_is_deterministic(legacy_doc):
    generic = _generic_doc("06-24")
    first = list(detection_sweep.sweep_cells(generic, "06-24"))
    second = list(detection_sweep.sweep_cells(generic, "06-24"))
    assert first == second


def test_evidence_generic_bbox_differs(legacy_doc):
    airport = airports.find_airport("LFPO")
    runway = airports.find_runway("LFPO", "07/25")
    unclipped = detection.runway_geofence_doc(airport, runway, "3", legacy=False)
    assert unclipped["bbox"] != legacy_doc["bbox"]
    cells = list(
        detection_sweep.sweep_cells(unclipped, "3", bbox_edges=dict(detection.LEGACY_ORLY_BBOX))
    )
    different = detection_sweep.compare(legacy_doc, unclipped, "3", cells)
    assert different, "the generic bbox must change a decision, which is why the override exists"


def test_drift_frozen_override_equals_runway_file(legacy_doc):
    assert detection.LEGACY_ORLY_BBOX == {
        key: legacy_doc["bbox"][key] for key in ("lat_min", "lat_max", "lon_min", "lon_max")
    }
    assert detection.LEGACY_ORLY_CENTER == (legacy_doc["center"]["lat"], legacy_doc["center"]["lon"])
    assert detection.LEGACY_ORLY_RADIUS_NM == legacy_doc["radius_nm"]
    assert detection.LEGACY_ORLY_ALT_CEILING_FT == legacy_doc["alt_ceiling_ft"]


def test_drift_catalogue_thresholds_equal_runway_file(legacy_doc):
    for runway_id, (icao, designator) in detection.LEGACY_RUNWAY_MAP.items():
        runway = airports.find_runway(icao, designator)
        assert runway is not None
        file_thresholds = [
            (t["lat"], t["lon"]) for t in legacy_doc["runways"][runway_id]["runway"]["thresholds"]
        ]
        assert list(runway.thresholds) == file_thresholds
        assert runway.half_width_m == 500.0
        assert runway.ground_half_width_m == 75.0


@pytest.mark.parametrize("runway_id", LEGACY_IDS)
def test_zone_key_equals_legacy_resolver_key(legacy_doc, runway_id):
    from server import fleet_zones

    legacy_key = fleet_zones.zone_from_geofence(detect.load_geofence()).key
    assert detection.spec_for({"tracked_runway": runway_id}).zone.key == legacy_key
    assert legacy_key == "48.7233|2.3794|5.0"


def test_kill_switch_replay_still_identical_and_serves_file(monkeypatch, legacy_doc):
    monkeypatch.setenv(detection.LEGACY_GEOFENCE_ENV, "1")
    for runway_id in LEGACY_IDS:
        spec = detection.spec_for({"tracked_runway": runway_id})
        assert spec.geofence == legacy_doc
        for name, records in _fixture_records():
            assert detect.runway_candidates(records, legacy_doc, runway_id) == (
                detect.runway_candidates(records, spec.geofence, runway_id)
            ), name
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV)
    assert detection.spec_for({"tracked_runway": "3"}).geofence != legacy_doc


def test_kill_switch_default_constant_is_off():
    assert detection.LEGACY_ORLY_DEFAULT_TO_FILE is False


def _on_axis(doc, display_id, along, cross=0.0):
    axis = detect.runway_axis(doc, runway_id=display_id)
    lat, lon = detection_sweep._position(axis, along, cross)
    return {"hex": "abc123", "flight": "TST1 ", "lat": lat, "lon": lon, "alt_baro": 500,
            "track": axis["bearing_deg"]}


def _doc_for(icao, designator):
    return detection.spec_for(
        {"detection": {"mode": "runway", "airport": icao, "runway": designator}}
    )


@pytest.mark.parametrize(
    "icao,first,second",
    [
        ("LFPG", "08L/26R", "08R/26L"),
        ("LFPG", "09L/27R", "09R/27L"),
        ("LFMN", "04L/22R", "04R/22L"),
        ("LFBO", "14L/32R", "14R/32L"),
    ],
)
def test_parallel_runways_are_gated_only_by_their_own_runway(icao, first, second):
    spec_a = _doc_for(icao, first)
    spec_b = _doc_for(icao, second)
    assert spec_a.zone.key == spec_b.zone.key
    for mine, other in ((spec_a, spec_b), (spec_b, spec_a)):
        axis = detect.runway_axis(mine.geofence, runway_id=mine.display_id)
        for along in (-1000.0, axis["length_m"] / 2.0, axis["length_m"] + 1000.0):
            record = _on_axis(mine.geofence, mine.display_id, along)
            assert detect.runway_candidates([record], mine.geofence, mine.display_id)
            assert not detect.runway_candidates([record], other.geofence, other.display_id)


def test_parallel_lone_runway_keeps_a_wide_corridor():
    spec = _doc_for("LFPO", "07/25")
    assert spec.display_id == "3"
    record = _on_axis(spec.geofence, "3", 1500.0, cross=200.0)
    assert detect.runway_candidates([record], spec.geofence, "3")


def test_two_devices_share_one_zone_and_select_their_own_runway():
    spec_a = _doc_for("LFPG", "08L/26R")
    spec_b = _doc_for("LFPG", "08R/26L")
    assert spec_a.zone.key == spec_b.zone.key
    zone_records = [
        _on_axis(spec_a.geofence, spec_a.display_id, 1500.0) | {"hex": "aaaaaa"},
        _on_axis(spec_b.geofence, spec_b.display_id, 1500.0) | {"hex": "bbbbbb"},
    ]
    results = [("adsbfi", zone_records), ("adsblol", zone_records)]
    pick_a = detect.select_from_provider_results(results, spec_a.geofence, spec_a.display_id)
    pick_b = detect.select_from_provider_results(results, spec_b.geofence, spec_b.display_id)
    assert pick_a is not None and pick_b is not None
    assert pick_a["hex"] == "aaaaaa" and pick_b["hex"] == "bbbbbb"
    assert pick_a["selected_runway"] == "LFPG:08L/26R"
    assert pick_b["selected_runway"] == "LFPG:08R/26L"
