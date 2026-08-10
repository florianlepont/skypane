#!/usr/bin/env python3
"""Contract harness for server/plane/runway_config.py's D-03 inference with
D-P2-04's deadband and hold-last-state behaviour.

Stdlib-only, plus the module under test (server.plane.runway_config). Exits
0 only when every check below passes; any failure (or exception - none is
ever swallowed into a pass) exits 1.

Real-data grounding (A-02-02-01): the arrival/deadband checks below replay
server/fixtures/track_arrival_440cb1.json, the real recorded EJU84YF flare
sequence (-640 then two +48 readings on an aircraft that is unambiguously
landing) - not an inline literal. Every climb-side ("departing") case is
explicitly labelled SYNTHETIC in its assertion message: no real runway-3
departure has ever been observed (02-RESEARCH.md Open Question 2), so a
green climb-side check proves the deadband arithmetic, not real-world
departure validation - see A-02-02-01 in 02-02-PLAN.md.

Usage:
    server/.venv/bin/python3 server/test_runway_config.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 14


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
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
        import server.plane.runway_config as runway_config
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before
        # server/plane/runway_config.py exists. It must fail - Task 2 turns
        # it green.
        print("FAIL import server.plane.runway_config - %r" % (exc,))
        print("runway-config: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    infer = runway_config.infer_runway_config
    track = load_fixture("track_arrival_440cb1.json")

    # 1-3. Replay the real recorded EJU84YF flare sequence in order, seeded
    #      with no prior confirmed state. -640 -> arriving; both subsequent
    #      +48 readings (the real quantisation/flare artefact, not noise)
    #      must NOT flip the state away from arriving.
    def _real_track_first_observation_arriving():
        rate = track[0]["baro_rate"]
        if rate != -640:
            return False, "fixture's first baro_rate changed unexpectedly: %r" % (rate,)
        state = infer(rate, None)
        if state != "arriving":
            return False, "real EJU84YF -640 reading did not classify as arriving: got %r" % (state,)
        return True, ""
    check(
        "real fixture track_arrival_440cb1: -640 seeded with no prior state -> arriving",
        _real_track_first_observation_arriving,
    )

    def _real_track_first_flare_holds():
        rate = track[1]["baro_rate"]
        if rate != 48:
            return False, "fixture's second baro_rate changed unexpectedly: %r" % (rate,)
        state = infer(rate, "arriving")
        if state != "arriving":
            return False, (
                "real EJU84YF flare artefact (+48 ft/min) flipped the state away from "
                "arriving on an aircraft that is unambiguously landing - the deadband broke: got %r" % (state,)
            )
        return True, ""
    check(
        "real fixture track_arrival_440cb1: first +48 flare reading holds arriving (real landing, not a bug)",
        _real_track_first_flare_holds,
    )

    def _real_track_second_flare_holds():
        rate = track[2]["baro_rate"]
        if rate != 48:
            return False, "fixture's third baro_rate changed unexpectedly: %r" % (rate,)
        state = infer(rate, "arriving")
        if state != "arriving":
            return False, (
                "real EJU84YF second flare reading (+48 ft/min) flipped the state away from "
                "arriving on an aircraft that is unambiguously landing - the deadband broke: got %r" % (state,)
            )
        return True, ""
    check(
        "real fixture track_arrival_440cb1: second +48 flare reading still holds arriving (real landing, not a bug)",
        _real_track_second_flare_holds,
    )

    # 4. Inside the deadband with nothing to hold - must not invent a state.
    def _no_prior_state_inside_deadband_returns_none():
        state = infer(48, None)
        if state is not None:
            return False, "expected None (nothing to hold, none invented), got %r" % (state,)
        return True, ""
    check("+48 seeded with no prior confirmed state returns None (nothing to hold)", _no_prior_state_inside_deadband_returns_none)

    # 5-6. Departure-side boundary (SYNTHETIC per A-02-02-01 - see module
    #      docstring note above).
    def _climb_threshold_departs():
        state = infer(200, None)
        if state != "departing":
            return False, "SYNTHETIC boundary case: +200 did not classify as departing: got %r" % (state,)
        return True, ""
    check(
        "SYNTHETIC (A-02-02-01, no real departure observed): +200 seeded None -> departing (inclusive boundary)",
        _climb_threshold_departs,
    )

    def _just_below_climb_threshold_holds():
        state = infer(199, "arriving")
        if state != "arriving":
            return False, "SYNTHETIC boundary case: +199 did not hold the prior confirmed state: got %r" % (state,)
        return True, ""
    check(
        "SYNTHETIC (A-02-02-01, no real departure observed): +199 holds last confirmed state (just inside deadband)",
        _just_below_climb_threshold_holds,
    )

    # 7-8. Descent-side boundary (real-data-backed per A-02-02-01/D-P2-04).
    def _descend_threshold_arrives():
        state = infer(-200, None)
        if state != "arriving":
            return False, "boundary case: -200 did not classify as arriving: got %r" % (state,)
        return True, ""
    check("real-data-backed boundary: -200 seeded None -> arriving (inclusive boundary)", _descend_threshold_arrives)

    def _just_above_descend_threshold_holds():
        state = infer(-199, "departing")
        if state != "departing":
            return False, "boundary case: -199 did not hold the prior confirmed state: got %r" % (state,)
        return True, ""
    check("real-data-backed boundary: -199 holds last confirmed state (just inside deadband)", _just_above_descend_threshold_holds)

    # 9-12. Non-numeric inputs hold the last confirmed state and never raise.
    #       Python treats bool as an int subclass - True/False must be
    #       explicitly rejected, not silently read as 1/0.
    def _none_input_holds():
        state = infer(None, "arriving")
        if state != "arriving":
            return False, "None vertical_rate did not hold the prior confirmed state: got %r" % (state,)
        return True, ""
    check("None vertical_rate holds last confirmed state and never raises", _none_input_holds)

    def _string_input_holds():
        state = infer("ground", "departing")
        if state != "departing":
            return False, "string vertical_rate did not hold the prior confirmed state: got %r" % (state,)
        return True, ""
    check("'ground' string vertical_rate holds last confirmed state and never raises", _string_input_holds)

    def _bool_input_holds():
        state = infer(True, "arriving")
        if state != "arriving":
            return False, (
                "bool vertical_rate was not rejected before the numeric comparison "
                "(Python treats bool as an int subclass - True must not be read as 1): got %r" % (state,)
            )
        return True, ""
    check("True (bool) vertical_rate holds last confirmed state, not read as int 1", _bool_input_holds)

    def _dict_input_holds():
        state = infer({"unexpected": "shape"}, "departing")
        if state != "departing":
            return False, "dict vertical_rate did not hold the prior confirmed state: got %r" % (state,)
        return True, ""
    check("dict vertical_rate holds last confirmed state and never raises", _dict_input_holds)

    # 13. A large climb value - SYNTHETIC per A-02-02-01.
    def _large_climb_departs():
        state = infer(2400, None)
        if state != "departing":
            return False, "SYNTHETIC case: +2400 large climb did not classify as departing: got %r" % (state,)
        return True, ""
    check(
        "SYNTHETIC (A-02-02-01, no real departure observed): +2400 large climb -> departing",
        _large_climb_departs,
    )

    # 14. infer_from_flight delegates to the flight dict's vertical_rate_fpm
    #     key, so poll_loop never reaches into raw aggregator fields itself.
    def _infer_from_flight_delegates():
        if not hasattr(runway_config, "infer_from_flight"):
            return False, "server.plane.runway_config has no infer_from_flight()"
        flight = {"hex": "440cb1", "callsign": "EJU84YF", "vertical_rate_fpm": -640}
        state = runway_config.infer_from_flight(flight, None)
        if state != "arriving":
            return False, "infer_from_flight did not read vertical_rate_fpm correctly: got %r" % (state,)
        return True, ""
    check("infer_from_flight() delegates on the flight dict's vertical_rate_fpm key", _infer_from_flight_delegates)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("runway-config: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
