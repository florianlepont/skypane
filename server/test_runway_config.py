#!/usr/bin/env python3
"""Contract tests for server/plane/runway_config.py's runway inference
with its deadband and hold-last-state behaviour.

Real-data grounding: the arrival/deadband checks below replay
server/fixtures/track_arrival_440cb1.json, the real recorded EJU84YF flare
sequence (-640 then two +48 readings on an aircraft that is unambiguously
landing) - not an inline literal. Every climb-side ("departing") case is
explicitly labelled SYNTHETIC in its assertion message: no real runway-3
departure has ever been observed, so a green climb-side check proves the
deadband arithmetic, not real-world departure validation.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.device_config as device_config  # noqa: E402
import server.plane.runway_config as runway_config  # noqa: E402

infer = runway_config.infer_runway_config


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def track():
    return load_fixture("track_arrival_440cb1.json")


def test_real_track_first_observation_arriving(track):
    """real fixture track_arrival_440cb1: -640 seeded with no prior state -> arriving."""
    rate = track[0]["baro_rate"]
    assert rate == -640, "fixture's first baro_rate changed unexpectedly: %r" % (rate,)
    state = infer(rate, None)
    assert state == "arriving", "real EJU84YF -640 reading did not classify as arriving: got %r" % (state,)


def test_real_track_first_flare_holds(track):
    """real fixture track_arrival_440cb1: first +48 flare reading holds arriving (real landing, not a bug)."""
    rate = track[1]["baro_rate"]
    assert rate == 48, "fixture's second baro_rate changed unexpectedly: %r" % (rate,)
    state = infer(rate, "arriving")
    assert state == "arriving", (
        "real EJU84YF flare artefact (+48 ft/min) flipped the state away from "
        "arriving on an aircraft that is unambiguously landing - the deadband broke: got %r" % (state,)
    )


def test_real_track_second_flare_holds(track):
    """real fixture track_arrival_440cb1: second +48 flare reading still holds arriving (real landing, not a bug)."""
    rate = track[2]["baro_rate"]
    assert rate == 48, "fixture's third baro_rate changed unexpectedly: %r" % (rate,)
    state = infer(rate, "arriving")
    assert state == "arriving", (
        "real EJU84YF second flare reading (+48 ft/min) flipped the state away from "
        "arriving on an aircraft that is unambiguously landing - the deadband broke: got %r" % (state,)
    )


def test_no_prior_state_inside_deadband_returns_none():
    """+48 seeded with no prior confirmed state returns None (nothing to hold)."""
    state = infer(48, None)
    assert state is None, "expected None (nothing to hold, none invented), got %r" % (state,)


def test_synthetic_climb_threshold_departs():
    """SYNTHETIC (A-02-02-01, no real departure observed): +200 seeded None -> departing (inclusive boundary)."""
    state = infer(200, None)
    assert state == "departing", "SYNTHETIC boundary case: +200 did not classify as departing: got %r" % (state,)


def test_synthetic_just_below_climb_threshold_holds():
    """SYNTHETIC (A-02-02-01, no real departure observed): +199 holds last confirmed state (just inside deadband)."""
    state = infer(199, "arriving")
    assert state == "arriving", "SYNTHETIC boundary case: +199 did not hold the prior confirmed state: got %r" % (state,)


def test_descend_threshold_arrives():
    """real-data-backed boundary: -200 seeded None -> arriving (inclusive boundary)."""
    state = infer(-200, None)
    assert state == "arriving", "boundary case: -200 did not classify as arriving: got %r" % (state,)


def test_just_above_descend_threshold_holds():
    """real-data-backed boundary: -199 holds last confirmed state (just inside deadband)."""
    state = infer(-199, "departing")
    assert state == "departing", "boundary case: -199 did not hold the prior confirmed state: got %r" % (state,)


def test_none_vertical_rate_holds_last_confirmed_state_and_never_raises():
    state = infer(None, "arriving")
    assert state == "arriving", "None vertical_rate did not hold the prior confirmed state: got %r" % (state,)


def test_string_vertical_rate_holds_last_confirmed_state_and_never_raises():
    """'ground' string vertical_rate holds last confirmed state and never raises."""
    state = infer("ground", "departing")
    assert state == "departing", "string vertical_rate did not hold the prior confirmed state: got %r" % (state,)


def test_bool_vertical_rate_holds_last_confirmed_state_not_read_as_int_1():
    """True (bool) vertical_rate holds last confirmed state, not read as int 1."""
    # Python treats bool as an int subclass - True/False must be explicitly
    # rejected, not silently read as 1/0.
    state = infer(True, "arriving")
    assert state == "arriving", (
        "bool vertical_rate was not rejected before the numeric comparison "
        "(Python treats bool as an int subclass - True must not be read as 1): got %r" % (state,)
    )


def test_dict_vertical_rate_holds_last_confirmed_state_and_never_raises():
    state = infer({"unexpected": "shape"}, "departing")
    assert state == "departing", "dict vertical_rate did not hold the prior confirmed state: got %r" % (state,)


def test_synthetic_large_climb_departs():
    """SYNTHETIC (A-02-02-01, no real departure observed): +2400 large climb -> departing."""
    state = infer(2400, None)
    assert state == "departing", "SYNTHETIC case: +2400 large climb did not classify as departing: got %r" % (state,)


def test_infer_from_flight_delegates_on_the_flight_dicts_vertical_rate_fpm_key():
    assert hasattr(runway_config, "infer_from_flight"), "server.plane.runway_config has no infer_from_flight()"
    flight = {"hex": "440cb1", "callsign": "EJU84YF", "vertical_rate_fpm": -640}
    state = runway_config.infer_from_flight(flight, None)
    assert state == "arriving", "infer_from_flight did not read vertical_rate_fpm correctly: got %r" % (state,)


def test_runway_labels_are_english_with_no_piste_vocabulary():
    """device_config.runway_label() returns an English label containing 'Runway ' and no 'Piste' for every RUNWAY_IDS member."""
    # No other check in this file pins a runway LABEL literally (this
    # module tests server/plane/runway_config.py's inference state
    # machine, not server/device_config.py's registry) - added here so
    # the French "Piste" vocabulary can never come back unnoticed.
    for runway_id in device_config.RUNWAY_IDS:
        label = device_config.runway_label(runway_id)
        assert "Runway " in label, "runway_label(%r) = %r does not contain 'Runway '" % (runway_id, label)
        assert "Piste" not in label, "runway_label(%r) = %r still carries French 'Piste' vocabulary" % (runway_id, label)

