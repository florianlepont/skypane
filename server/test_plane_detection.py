#!/usr/bin/env python3
"""Contract harness for server/plane/detect.py's geofence filter, the
D-P2-01 multi-aircraft selection rule, and the runway-3 identification
gate added by the runway3-false-positive debug session (2026-08-27).

Checks 11-22 are that session's regression coverage. They are built on two
newly committed fixtures that are real live captures of the actual bug and
its correct counter-example (see server/fixtures/README.md), plus the real
published OurAirports coordinates of Orly's OTHER two runways, which the
gate must never accept as runway 3.

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

EXPECTED_CHECK_COUNT = 22


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

    # ---------------------------------------------------------------
    # runway3-false-positive (2026-08-27): runway-3 identification gate
    # ---------------------------------------------------------------

    def _wrong_runway_record():
        return load_fixture("geofence_wrong_runway_39de4a.json")["aircraft"]

    def _runway3_record():
        return load_fixture("geofence_runway3_arrival_347288.json")["aircraft"]

    # 11. The real false-positive record genuinely reproduces the bug's
    #     precondition: it IS inside the bbox and IS below the ceiling, so
    #     the pre-fix code (which gated on exactly those two things) had no
    #     reason to reject it. Without this check, check 12 could pass for
    #     the wrong reason - e.g. if the fixture were simply out of bbox.
    def _wrong_runway_fixture_reproduces_the_precondition():
        matched = detect.filter_in_geofence(_wrong_runway_record(), geofence)
        if len(matched) != 1 or matched[0]["hex"] != "39de4a":
            return False, "expected the real 39de4a record to be in-bbox, got %r" % (
                [m.get("hex") for m in matched],)
        if not matched[0].get("in_bbox") or not matched[0].get("below_ceiling"):
            return False, "expected in_bbox and below_ceiling True (the pre-fix accept condition), got %r" % (
                {k: matched[0].get(k) for k in ("in_bbox", "below_ceiling")},)
        return True, ""
    check("real wrong-runway record 39de4a is in-bbox and below-ceiling (the pre-fix accept condition)",
          _wrong_runway_fixture_reproduces_the_precondition)

    # 12. THE REGRESSION. hex 39de4a (TVF12ZW) was captured live on
    #     2026-08-27 being selected as "the aircraft using runway 3" while
    #     it was actually departing runway 20 - climbing +2304 ft/min on
    #     track 197.67, 750m off runway 3's centreline. It must now be
    #     rejected, leaving nothing selected for that snapshot.
    def _wrong_runway_is_rejected():
        winner = detect.select_runway3_aircraft(_wrong_runway_record(), geofence)
        if winner is not None:
            return False, "the real runway-20 departure 39de4a was still selected as runway 3: %r" % (winner,)
        return True, ""
    check("select_runway3_aircraft rejects the real runway-20 departure 39de4a (the reported false positive)",
          _wrong_runway_is_rejected)

    # 13. The counter-example: the gate must not have been tightened into
    #     rejecting genuine runway-3 traffic. hex 347288 (IBE05DP) was
    #     captured in the same live window on final to runway 25.
    def _real_runway3_arrival_is_still_selected():
        winner = detect.select_runway3_aircraft(_runway3_record(), geofence)
        if winner is None:
            return False, "the real runway-25 arrival 347288 is no longer selected"
        if winner["hex"] != "347288" or winner["callsign"] != "IBE05DP":
            return False, "expected 347288/IBE05DP, got %r/%r" % (winner["hex"], winner.get("callsign"))
        return True, ""
    check("select_runway3_aircraft still selects the real runway-25 arrival 347288 (no over-tightening)",
          _real_runway3_arrival_is_still_selected)

    # 14. Both real aircraft in one snapshot: the wrong-runway one must not
    #     even be a candidate, and the genuine one must win.
    def _wrong_runway_loses_to_real_one():
        combined = _wrong_runway_record() + _runway3_record()
        tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(combined, geofence)}
        if tagged["39de4a"].get("on_runway3"):
            return False, "39de4a was still tagged on_runway3"
        if not tagged["347288"].get("on_runway3"):
            return False, "347288 was not tagged on_runway3"
        winner = detect.select_runway3_aircraft(combined, geofence)
        if winner is None or winner["hex"] != "347288":
            return False, "expected 347288 to win, got %r" % (winner and winner["hex"],)
        return True, ""
    check("with both real aircraft present, only the genuine runway-3 arrival is a candidate",
          _wrong_runway_loses_to_real_one)

    # 15. The axis is derived from the runway's own published thresholds,
    #     not hardcoded: threshold 07 is the origin, threshold 25 sits one
    #     runway-length along it, and both are exactly on the centreline.
    def _axis_is_derived_from_published_thresholds():
        axis = detect.runway_axis(geofence)
        if axis is None:
            return False, "runway_axis() returned None for the project geofence"
        if not (74.0 <= axis["bearing_deg"] <= 75.0):
            return False, "expected a ~74.4 deg TRUE bearing, got %r" % (axis["bearing_deg"],)
        if not (3300.0 <= axis["length_m"] <= 3330.0):
            return False, "expected a ~3320m centreline, got %r" % (axis["length_m"],)
        runway = geofence["runway"]
        a0, c0 = detect.along_cross_track_m(
            runway["threshold_07"]["lat"], runway["threshold_07"]["lon"], geofence)
        a1, c1 = detect.along_cross_track_m(
            runway["threshold_25"]["lat"], runway["threshold_25"]["lon"], geofence)
        if abs(a0) > 1.0 or abs(c0) > 1.0:
            return False, "threshold 07 should be the axis origin, got along=%r cross=%r" % (a0, c0)
        if abs(a1 - axis["length_m"]) > 1.0 or abs(c1) > 1.0:
            return False, "threshold 25 should sit at (length, 0), got along=%r cross=%r" % (a1, c1)
        return True, ""
    check("runway_axis/along_cross_track_m are derived from the published thresholds",
          _axis_is_derived_from_published_thresholds)

    # 16. Alignment is measured against TRUE track and is direction-
    #     agnostic (runway 3 is used both ways). Bools are rejected before
    #     the numeric check - Python's bool is an int subclass, so an
    #     unguarded True would read as a 1-degree track.
    def _track_deviation_is_bidirectional_and_type_safe():
        cases = [
            (254.9, 1.0),    # the real IBE05DP arrival on final to 25
            (74.41, 0.2),    # the reciprocal - rolling out on 07
            (197.67, 57.5),  # the real runway-20 departure
        ]
        for track, ceiling in cases:
            dev = detect.track_axis_deviation_deg(track, geofence)
            if dev is None or dev > ceiling:
                return False, "track %r: expected deviation <= %r, got %r" % (track, ceiling, dev)
        if detect.track_axis_deviation_deg(197.67, geofence) < 55.0:
            return False, "the runway-20 track should be ~56 deg off runway 3's axis"
        for bad in (None, "254", True, False, [254]):
            if detect.track_axis_deviation_deg(bad, geofence) is not None:
                return False, "expected None for a non-numeric track %r" % (bad,)
        return True, ""
    check("track_axis_deviation_deg is bidirectional and rejects bools/non-numerics",
          _track_deviation_is_bidirectional_and_type_safe)

    # 17. Runway 06/24 is only ~12 deg off runway 3's heading, so the track
    #     gate CANNOT separate it - this asserts the corridor is what
    #     rejects it, i.e. that the corridor gate is load-bearing rather
    #     than redundant. Coordinates are the real published OurAirports
    #     LFPO thresholds carried in runway3.json.
    def _corridor_is_what_rejects_runway_06_24():
        neighbour = geofence["runway"]["neighbouring_runways"]["06/24"]
        for key, track in (("threshold_06", 62.0), ("threshold_24", 242.0)):
            point = neighbour[key]
            record = {"hex": "060024", "lat": point["lat"], "lon": point["lon"],
                      "alt_baro": "ground", "track": track}
            tagged = detect.filter_in_geofence([record], geofence)
            if not tagged:
                continue  # outside the coarse bbox is also a valid rejection
            if not tagged[0]["track_aligned"]:
                return False, ("%s: the track gate rejected it, so this check no longer proves the "
                               "corridor is load-bearing (06/24 is only ~12 deg off axis)" % key)
            if tagged[0]["in_corridor"]:
                return False, "%s: runway 06/24 was accepted into the runway-3 corridor" % key
            if tagged[0]["on_runway3"]:
                return False, "%s: runway 06/24 was tagged on_runway3" % key
        return True, ""
    check("runway 06/24's published thresholds are rejected by the corridor gate, not the track gate",
          _corridor_is_what_rejects_runway_06_24)

    # 18. The mirror image: runway 02/20 physically CROSSES runway 3's
    #     centreline, so the corridor gate cannot separate it - this
    #     asserts the track gate is what rejects it. The test point is the
    #     real crossing point of the two published centrelines.
    def _track_gate_is_what_rejects_runway_02_20():
        neighbour = geofence["runway"]["neighbouring_runways"]["02/20"]
        start, end = neighbour["threshold_02"], neighbour["threshold_20"]
        # Walk the real 02/20 centreline and take the point closest to
        # runway 3's centreline - the crossing the corridor cannot exclude.
        best = None
        for i in range(1001):
            f = i / 1000.0
            lat = start["lat"] + f * (end["lat"] - start["lat"])
            lon = start["lon"] + f * (end["lon"] - start["lon"])
            _, cross = detect.along_cross_track_m(lat, lon, geofence)
            if best is None or abs(cross) < abs(best[2]):
                best = (lat, lon, cross)
        lat, lon, cross = best
        if abs(cross) > 25.0:
            return False, ("expected runway 02/20 to cross runway 3's centreline (|cross| ~0), "
                           "got %r - the premise of this check no longer holds" % cross)
        record = {"hex": "020020", "lat": lat, "lon": lon, "alt_baro": "ground", "track": 198.0}
        tagged = detect.filter_in_geofence([record], geofence)
        if not tagged:
            return False, "the 02/20 crossing point fell outside the bbox; check premise broken"
        if not tagged[0]["in_corridor"]:
            return False, ("the corridor rejected the crossing point, so this check no longer proves "
                           "the track gate is load-bearing")
        if tagged[0]["track_aligned"]:
            return False, "a runway-20-aligned track (198 deg) was accepted as runway-3-aligned"
        if tagged[0]["on_runway3"]:
            return False, "an aircraft on runway 02/20's centreline was tagged on_runway3"
        return True, ""
    check("runway 02/20's centreline crossing is rejected by the track gate, not the corridor gate",
          _track_gate_is_what_rejects_runway_02_20)

    # 19. A record with no `track` is not disqualified - it still has to
    #     pass the corridor. This is the documented asymmetry with
    #     below_ceiling's "unknown never claims" rule, and it is what keeps
    #     the pre-existing real fixtures (which carry no track) selectable.
    def _missing_track_does_not_disqualify():
        fixture = load_fixture("geofence_on_ground.json")
        tagged = {ac["hex"]: ac for ac in detect.filter_in_geofence(fixture["ac"], geofence)}
        if tagged["3985a7"].get("track_deg") is not None:
            return False, "premise broken: fixture 3985a7 now carries a track"
        if not tagged["3985a7"].get("track_aligned"):
            return False, "a record with no track was treated as misaligned"
        if not tagged["3985a7"].get("on_runway3"):
            return False, "the real on-ground runway-3 record stopped qualifying"
        # ...but the corridor still applies to it: move it 900m off the
        # centreline (roughly where runway 06/24 sits) and it must fail.
        off_corridor = dict(next(ac for ac in fixture["ac"] if ac["hex"] == "3985a7"))
        off_corridor["lat"] = 48.7355   # real runway 24 threshold, no track field
        off_corridor["lon"] = 2.36068
        off_corridor.pop("track", None)
        moved = detect.filter_in_geofence([off_corridor], geofence)
        if moved and moved[0].get("on_runway3"):
            return False, "an untracked record 1600m off the centreline still qualified as runway 3"
        return True, ""
    check("a record with no track is corridor-gated rather than rejected outright",
          _missing_track_does_not_disqualify)

    # ---------------------------------------------------------------
    # Per-poll cross-source validation (fix 2)
    # ---------------------------------------------------------------

    def _with_stubbed_providers(responses, fn):
        """Run fn() with detect.query_provider replaced by a lookup into
        `responses` ({provider_name: aircraft_list_or_Exception}), and the
        inter-call sleep zeroed so the harness stays fast.
        """
        real_query, real_sleep = detect.query_provider, detect.MIN_SECONDS_BETWEEN_CALLS

        def fake_query(name, lat, lon, radius_nm, timeout=10.0):
            value = responses[name]
            if isinstance(value, Exception):
                raise value
            return value

        detect.query_provider = fake_query
        detect.MIN_SECONDS_BETWEEN_CALLS = 0
        try:
            return fn()
        finally:
            detect.query_provider = real_query
            detect.MIN_SECONDS_BETWEEN_CALLS = real_sleep

    # 20. Both providers independently select the same aircraft -> the
    #     selection is returned and marked corroborated by both.
    def _agreeing_providers_are_corroborated():
        both = {"airplaneslive": _runway3_record(), "adsbfi": _runway3_record()}
        result = _with_stubbed_providers(
            both, lambda: detect.poll_current_aircraft(geofence))
        if result is None:
            return False, "two agreeing providers produced no selection"
        if result["hex"] != "347288":
            return False, "expected 347288, got %r" % (result["hex"],)
        if result.get("corroborated") is not True:
            return False, "expected corroborated True, got %r" % (result.get("corroborated"),)
        if sorted(result.get("sources") or []) != ["adsbfi", "airplaneslive"]:
            return False, "expected both providers in sources, got %r" % (result.get("sources"),)
        return True, ""
    check("poll_current_aircraft: two agreeing providers yield corroborated=True",
          _agreeing_providers_are_corroborated)

    # 21. The providers name two different aircraft as "the one on runway
    #     3" - at most one can be right, so the poll selects nothing and
    #     D-04 leaves the panel alone. Built from the real arrival record
    #     plus a copy relocated to the other end of the real runway, so
    #     both are legitimately on runway 3 and the disagreement is about
    #     which aircraft, not about the gate.
    def _disagreeing_providers_yield_nothing():
        other = dict(_runway3_record()[0])
        other["hex"] = "3985a7"
        other["flight"] = "AFR56XX "
        other["lat"] = 48.719398   # real threshold 07, the far end of runway 3
        other["lon"] = 2.358590
        other["track"] = 74.41
        if detect.select_runway3_aircraft([other], geofence) is None:
            return False, "premise broken: the stand-in aircraft is not itself on runway 3"
        responses = {"airplaneslive": _runway3_record(), "adsbfi": [other]}
        result = _with_stubbed_providers(
            responses, lambda: detect.poll_current_aircraft(geofence))
        if result is not None:
            return False, "expected None on provider disagreement, got %r" % (result["hex"],)
        return True, ""
    check("poll_current_aircraft: disagreeing providers select nothing (doubt -> D-04 hold)",
          _disagreeing_providers_yield_nothing)

    # 22. One provider unreachable (the live 2026-08-27 reality:
    #     api.airplanes.live answers 403) must NOT be scored as
    #     disagreement - the reachable provider's selection is returned,
    #     flagged as uncorroborated rather than suppressed.
    def _single_reachable_provider_is_uncorroborated_not_suppressed():
        import requests
        responses = {
            "airplaneslive": requests.RequestException("403 Client Error: Forbidden"),
            "adsbfi": _runway3_record(),
        }
        result = _with_stubbed_providers(
            responses, lambda: detect.poll_current_aircraft(geofence))
        if result is None:
            return False, "a single reachable provider was suppressed as if it were a disagreement"
        if result["hex"] != "347288":
            return False, "expected 347288, got %r" % (result["hex"],)
        if result.get("corroborated") is not None:
            return False, "expected corroborated None (no corroboration available), got %r" % (
                result.get("corroborated"),)
        if result.get("sources") != ["adsbfi"]:
            return False, "expected sources ['adsbfi'], got %r" % (result.get("sources"),)
        return True, ""
    check("poll_current_aircraft: an unreachable provider is not scored as disagreement",
          _single_reachable_provider_is_uncorroborated_not_suppressed)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("plane-detection: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
