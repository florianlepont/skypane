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



# --- detection key -----------------------------------------------------------

_OLD_KEYS = (
    "theme", "theme_arriving", "calendar_theme_id", "tracked_runway", "led_enabled",
    "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end", "wake_interval_s",
    "display_enabled", "timezone",
)
_RUNWAY_OBJ = {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
_POSITION_OBJ = {"mode": "position", "radius_km": 9}


@pytest.mark.parametrize("value", [
    None, 5, "x", [], {}, {"mode": "other"},
    {"mode": "runway", "airport": "lfpg", "runway": "08L/26R"},
    {"mode": "runway", "airport": "LFPG", "runway": "8L/26R"},
    {"mode": "runway", "airport": "LFPG", "runway": "08L/26R\nx"},
    {"mode": "runway", "airport": "LFPG"},
    {"mode": "position", "radius_km": True},
    {"mode": "position", "radius_km": 9.0},
    {"mode": "position", "radius_km": "9"},
    {"mode": "position"},
])
def test_normalise_detection_rejects_bad_shapes(value):
    assert device_config.normalise_detection(value) is None


def test_normalise_detection_keeps_known_keys_only():
    assert device_config.normalise_detection(dict(_RUNWAY_OBJ, extra=[1] * 5)) == _RUNWAY_OBJ
    assert device_config.normalise_detection(dict(_POSITION_OBJ, extra="x")) == _POSITION_OBJ


def test_load_detection_is_none_when_absent_or_null(tmp_path):
    sd = str(tmp_path)
    assert device_config.load_device_config(sd)["detection"] is None
    with open(device_config.device_config_path(sd), "w") as fh:
        json.dump({"detection": None}, fh)
    assert device_config.load_device_config(sd)["detection"] is None
    with open(device_config.device_config_path(sd), "w") as fh:
        json.dump({"detection": {"mode": "runway", "airport": 4}}, fh)
    assert device_config.load_device_config(sd)["detection"] is None


def _read_bytes(sd):
    with open(device_config.device_config_path(sd), "rb") as fh:
        return fh.read()


def test_detection_carry_forward_clear_and_set(tmp_path):
    sd = str(tmp_path)
    device_config.save_device_config(sd, detection=_RUNWAY_OBJ)
    assert device_config.load_device_config(sd)["detection"] == _RUNWAY_OBJ
    device_config.save_device_config(sd, theme="black")
    assert device_config.load_device_config(sd)["detection"] == _RUNWAY_OBJ
    device_config.save_device_config(sd, detection=_POSITION_OBJ)
    assert device_config.load_device_config(sd)["detection"] == _POSITION_OBJ
    device_config.save_device_config(sd, detection=device_config.CLEAR_DETECTION)
    assert device_config.load_device_config(sd)["detection"] is None
    assert "detection" not in json.loads(_read_bytes(sd))


@pytest.mark.parametrize("bad", [5, {}, {"mode": "position", "radius_km": True}, "x"])
def test_invalid_detection_raises_and_writes_nothing(tmp_path, bad):
    sd = str(tmp_path)
    device_config.save_device_config(sd, theme="black")
    before = _read_bytes(sd)
    with pytest.raises(ValueError):
        device_config.save_device_config(sd, detection=bad)
    assert _read_bytes(sd) == before


def test_unrelated_save_is_byte_identical_to_the_legacy_layout(tmp_path):
    sd = str(tmp_path)
    device_config.save_device_config(sd, theme="black", tracked_runway="06-24")
    expected = json.dumps({
        "theme": "black", "theme_arriving": None, "calendar_theme_id": None,
        "tracked_runway": "06-24", "led_enabled": True, "quiet_hours_enabled": False,
        "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
        "wake_interval_s": None, "display_enabled": True,
    }, indent=1).encode()
    assert _read_bytes(sd) == expected
    assert "detection" not in json.loads(expected)


def test_previous_release_reader_still_sees_the_old_keys(tmp_path):
    sd = str(tmp_path)
    device_config.save_device_config(sd, theme="black", tracked_runway="02-20")
    with open(device_config.device_config_path(sd)) as fh:
        before = json.load(fh)
    device_config.save_device_config(sd, detection=_RUNWAY_OBJ)
    with open(device_config.device_config_path(sd)) as fh:
        after = json.load(fh)
    for key in _OLD_KEYS:
        assert after.get(key) == before.get(key), key
    assert after["tracked_runway"] == "02-20"


def test_tracked_runway_validation_is_unchanged(tmp_path):
    with pytest.raises(ValueError):
        device_config.save_device_config(str(tmp_path), tracked_runway="08L/26R")


def test_device_config_stays_a_leaf_module():
    with open(device_config.__file__) as fh:
        text = fh.read()
    assert "server.airports" not in text and "server.detection" not in text
