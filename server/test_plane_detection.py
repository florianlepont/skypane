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

EXPECTED_CHECK_COUNT = 8


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

    # 7. Default poll (no providers argument - exactly how
    #    server/poll_loop.py:165 calls it in production) queries adsb.fi
    #    only. Pins the 2026-08-27 default-provider demotion so this
    #    regression cannot silently reopen.
    def _default_poll_queries_adsbfi_only():
        recorded = []

        def recording_query_provider(name, lat, lon, radius_nm, timeout=10.0):
            recorded.append(name)
            return []

        original_query_provider = detect.query_provider
        detect.query_provider = recording_query_provider
        try:
            detect.poll_current_aircraft(geofence)
        finally:
            detect.query_provider = original_query_provider

        if recorded != ["adsbfi"]:
            return False, "expected default poll to query exactly ['adsbfi'], got %r" % (recorded,)
        return True, ""
    check("default poll (no providers arg) queries adsb.fi only", _default_poll_queries_adsbfi_only)

    # 8. The airplanes.live opt-in path survives the demotion: still
    #    selectable via --provider, but no longer in the default order.
    def _airplaneslive_still_opt_in():
        if "airplaneslive" not in detect.PROVIDERS:
            return False, "airplaneslive was removed from PROVIDERS - the opt-in path must be retained"
        if "airplaneslive" in detect.DEFAULT_PROVIDER_ORDER:
            return False, "airplaneslive is still in DEFAULT_PROVIDER_ORDER - it must be opt-in only"
        return True, ""
    check("airplaneslive remains a selectable opt-in, absent from the default order", _airplaneslive_still_opt_in)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("plane-detection: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
