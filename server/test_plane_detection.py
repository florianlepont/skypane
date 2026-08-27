#!/usr/bin/env python3
"""Contract harness for server/plane/detect.py's geofence filter and the
D-P2-01 multi-aircraft selection rule.

Stdlib-only, plus the module under test (server.plane.detect). Exits 0 only
when every check below passes; any failure (or exception - none is ever
swallowed into a pass) exits 1.

Usage:
    server/.venv/bin/python3 server/test_plane_detection.py
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 10


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


def load_geofence():
    # stdlib-only file I/O - no extra dependency needed just to read a
    # committed fixture or the geofence config.
    with open(GEOFENCE_PATH) as fh:
        return json.load(fh)


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.plane.detect as detect
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before
        # server/plane/detect.py exists. It must fail - Task 2 turns it green.
        print("FAIL import server.plane.detect - %r" % (exc,))
        print("plane-detection: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    geofence = load_geofence()

    # 1. filter_in_geofence drops the out-of-bbox and position-less synthetic
    #    records while keeping both real in-bbox hexes.
    def _filters_out_of_bbox_and_positionless():
        fixture = load_fixture("geofence_multi_aircraft.json")
        matched = detect.filter_in_geofence(fixture["ac"], geofence)
        matched_hexes = {ac["hex"] for ac in matched}
        if "000001" in matched_hexes:
            return False, "out-of-bbox synthetic hex 000001 was not dropped"
        if "000002" in matched_hexes:
            return False, "position-less synthetic hex 000002 was not dropped"
        if not {"39d300", "39dd01"} <= matched_hexes:
            return False, "real in-bbox hexes missing from filtered result: %r" % matched_hexes
        return True, ""
    check("filter_in_geofence drops out-of-bbox and position-less records", _filters_out_of_bbox_and_positionless)

    # 2. D-P2-01: lowest effective altitude wins (450ft beats 800ft).
    def _selects_lowest_altitude():
        fixture = load_fixture("geofence_multi_aircraft.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is None:
            return False, "expected a winner, got None"
        if winner["hex"] != "39d300":
            return False, "expected hex 39d300 (450ft), got %r" % (winner["hex"],)
        return True, ""
    check("select_runway3_aircraft picks 39d300 (450ft beats 800ft)", _selects_lowest_altitude)

    # 3. D-P2-01: on-ground (effective altitude 0) beats an 800ft airborne aircraft.
    def _on_ground_beats_airborne():
        fixture = load_fixture("geofence_on_ground.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is None:
            return False, "expected a winner, got None"
        if winner["hex"] != "3985a7":
            return False, "expected hex 3985a7 (on-ground), got %r" % (winner["hex"],)
        return True, ""
    check("select_runway3_aircraft: on-ground beats 800ft airborne", _on_ground_beats_airborne)

    # 4. D-04: an empty geofence snapshot selects nothing.
    def _empty_returns_none():
        fixture = load_fixture("geofence_empty.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is not None:
            return False, "expected None for an empty geofence snapshot, got %r" % (winner,)
        return True, ""
    check("select_runway3_aircraft returns None for an empty snapshot", _empty_returns_none)

    # 5. The winning record's callsign is stripped of the aggregator's trailing padding.
    def _callsign_is_stripped():
        fixture = load_fixture("geofence_multi_aircraft.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is None:
            return False, "expected a winner"
        if winner.get("callsign") != "TVF23WV":
            return False, "expected stripped callsign 'TVF23WV', got %r" % (winner.get("callsign"),)
        return True, ""
    check("selected record's callsign is stripped of trailing padding", _callsign_is_stripped)

    # 6. D-P2-01's tie-breaks make the pick independent of input array ordering.
    def _deterministic_under_shuffle():
        fixture = load_fixture("geofence_multi_aircraft.json")
        aircraft = list(fixture["ac"])
        first = detect.select_runway3_aircraft(aircraft, geofence)
        shuffled = list(aircraft)
        random.Random(1234).shuffle(shuffled)
        second = detect.select_runway3_aircraft(shuffled, geofence)
        if first is None or second is None:
            return False, "expected both selections to return a winner"
        if first["hex"] != second["hex"]:
            return False, "selection changed under shuffled input ordering: %r vs %r" % (
                first["hex"], second["hex"])
        return True, ""
    check("select_runway3_aircraft is deterministic under input reordering", _deterministic_under_shuffle)

    # 7. PLANE-01/02: the multi-aircraft fixture winner's aircraft_type is
    #    extracted from its fixture-carried `t` field (03.1-02).
    def _multi_aircraft_winner_has_aircraft_type():
        fixture = load_fixture("geofence_multi_aircraft.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is None:
            return False, "expected a winner"
        if winner.get("aircraft_type") != "B738":
            return False, "expected aircraft_type 'B738', got %r" % (winner.get("aircraft_type"),)
        return True, ""
    check("select_runway3_aircraft: multi-aircraft winner's aircraft_type is B738", _multi_aircraft_winner_has_aircraft_type)

    # 8. PLANE-01/02: the on-ground fixture winner's aircraft_type is
    #    extracted from its fixture-carried `t` field (03.1-02).
    def _on_ground_winner_has_aircraft_type():
        fixture = load_fixture("geofence_on_ground.json")
        winner = detect.select_runway3_aircraft(fixture["ac"], geofence)
        if winner is None:
            return False, "expected a winner"
        if winner.get("aircraft_type") != "A320":
            return False, "expected aircraft_type 'A320', got %r" % (winner.get("aircraft_type"),)
        return True, ""
    check("select_runway3_aircraft: on-ground winner's aircraft_type is A320", _on_ground_winner_has_aircraft_type)

    # 9. A record with no `t` key at all still selects successfully and
    #    yields aircraft_type is None - built inline from the multi-aircraft
    #    fixture's own winner coordinates rather than a third fixture file.
    def _no_type_key_yields_none():
        fixture = load_fixture("geofence_multi_aircraft.json")
        winner_record = next(ac for ac in fixture["ac"] if ac["hex"] == "39d300")
        no_type_record = dict(winner_record)
        no_type_record.pop("t", None)
        winner = detect.select_runway3_aircraft([no_type_record], geofence)
        if winner is None:
            return False, "expected a winner"
        if winner.get("aircraft_type") is not None:
            return False, "expected aircraft_type None for a record with no t key, got %r" % (winner.get("aircraft_type"),)
        return True, ""
    check("select_runway3_aircraft: a record with no t key yields aircraft_type None", _no_type_key_yields_none)

    # 10. T-03.1-02-01 / ASVS V5: a battery of malformed type values all
    #     degrade to aircraft_type None and none raises.
    def _malformed_type_values_never_raise():
        fixture = load_fixture("geofence_multi_aircraft.json")
        winner_record = next(ac for ac in fixture["ac"] if ac["hex"] == "39d300")
        malformed_values = ["", "   ", 738, ["A320"], "../../etc/passwd"]
        for bad_value in malformed_values:
            record = dict(winner_record)
            record["t"] = bad_value
            winner = detect.select_runway3_aircraft([record], geofence)
            if winner is None:
                return False, "expected a winner for malformed t=%r" % (bad_value,)
            if winner.get("aircraft_type") is not None:
                return False, "expected aircraft_type None for malformed t=%r, got %r" % (
                    bad_value, winner.get("aircraft_type"))
        return True, ""
    check("select_runway3_aircraft: malformed type values all yield aircraft_type None without raising", _malformed_type_values_never_raise)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("plane-detection: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
