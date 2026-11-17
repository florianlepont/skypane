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


@pytest.mark.parametrize("rate", [0, 199.9, -199.9, 1, -1])
def test_display_state_level_in_position_mode_is_overhead(rate):
    flight = {"vertical_rate_fpm": rate}
    assert runway_config.display_state(flight, "arriving", True) == "overhead"
    assert runway_config.display_state(flight, None, True) == "overhead"


@pytest.mark.parametrize("rate", [200, -200, 900, -600])
def test_display_state_outside_the_deadband_holds(rate):
    assert runway_config.display_state({"vertical_rate_fpm": rate}, "arriving", True) == "arriving"


@pytest.mark.parametrize("rate", [None, "x", True, float("nan")])
def test_display_state_unreadable_rate_holds(rate):
    assert runway_config.display_state({"vertical_rate_fpm": rate}, "departing", True) == "departing"
    assert runway_config.display_state({}, "departing", True) == "departing"
    assert runway_config.display_state(None, None, True) is None


@pytest.mark.parametrize("rate", [0, 100, -100, 500, None])
def test_display_state_runway_mode_always_holds(rate):
    assert runway_config.display_state({"vertical_rate_fpm": rate}, "arriving", False) == "arriving"
    assert runway_config.display_state({"vertical_rate_fpm": rate}, None, False) is None


@pytest.mark.parametrize("flight", [
    {"vertical_rate_fpm": 0, "altitude_ft": 600.0, "altitude_ref_ft": 600.0},
    {"vertical_rate_fpm": 48, "altitude_ft": 575.0, "altitude_ref_ft": 625.0},
    {"altitude_ft": 0.0, "altitude_ref_ft": 0.0},
    {"vertical_rate_fpm": 0},
    {"vertical_rate_fpm": 0, "altitude_ft": 600.0, "altitude_ref_ft": True},
    {},
])
def test_aircraft_without_a_direction_awaits_a_state(flight):
    assert runway_config.awaits_state(flight, False) is True


@pytest.mark.parametrize("flight", [
    {"vertical_rate_fpm": 900},
    {"vertical_rate_fpm": -700},
    {"vertical_rate_fpm": 0, "altitude_ft": 500.0, "altitude_ref_ft": 700.0},
    {"altitude_ft": 900.0, "altitude_ref_ft": 700.0},
])
def test_aircraft_with_a_direction_does_not_await_a_state(flight):
    assert runway_config.awaits_state(flight, False) is False


def test_level_aircraft_in_position_mode_is_shown_as_overhead():
    assert runway_config.awaits_state({"vertical_rate_fpm": 0}, True) is False


@pytest.mark.parametrize("altitude, reference, expected", [
    (500.0, 700.0, "arriving"),
    (575.0, 675.0, "arriving"),
    (900.0, 700.0, "departing"),
    (675.0, 575.0, "departing"),
    (600.0, 650.0, None),
    (650.0, 600.0, None),
    (0.0, 0.0, None),
    (None, 600.0, None),
    (600.0, None, None),
    ("x", 600.0, None),
    (float("nan"), 600.0, None),
])
def test_altitude_trend_state(altitude, reference, expected):
    flight = {"altitude_ft": altitude, "altitude_ref_ft": reference}
    assert runway_config.altitude_trend_state(flight) == expected


@pytest.mark.parametrize("flight", [None, "x", 3, []])
def test_altitude_trend_state_ignores_non_flights(flight):
    assert runway_config.altitude_trend_state(flight) is None


def test_infer_from_flight_uses_the_trend_only_when_nothing_else_decides():
    falling = {"vertical_rate_fpm": 0, "altitude_ft": 500.0, "altitude_ref_ft": 700.0}
    assert runway_config.infer_from_flight(falling, None) == "arriving"
    assert runway_config.infer_from_flight(falling, "departing") == "departing"
    assert runway_config.infer_from_flight({**falling, "vertical_rate_fpm": 900}, None) == "departing"
    assert runway_config.infer_from_flight({**falling, "vertical_rate_fpm": None}, None) == "arriving"
    assert runway_config.infer_from_flight({"vertical_rate_fpm": 0}, None) is None


def _entry(hex_code, first_seen, on_ground=False):
    return {"flight": {"hex": hex_code, "on_ground": on_ground}, "first_seen": first_seen}


def test_pop_fresh_pending_takes_the_newest_and_skips_deferred_entries():
    import server.poll_cycle as poll_cycle
    pending = [_entry("g1", 0.0, True), _entry("a1", 1.0), _entry("a2", 2.0), _entry("g2", 3.0, True)]
    flight, dropped = poll_cycle.pop_fresh_pending(
        pending, 10.0, defer=lambda f: f["on_ground"])
    assert flight["hex"] == "a2"
    assert dropped == []
    assert [e["flight"]["hex"] for e in pending] == ["g1", "a1", "g2"]


def test_pop_fresh_pending_orders_by_last_seen_not_first_seen():
    import server.poll_cycle as poll_cycle
    older_but_refreshed = {"flight": {"hex": "r1"}, "first_seen": 0.0, "last_seen": 9.0}
    newer_first_sighting = {"flight": {"hex": "n1"}, "first_seen": 5.0, "last_seen": 5.0}
    pending = [older_but_refreshed, newer_first_sighting]
    flight, _dropped = poll_cycle.pop_fresh_pending(pending, 10.0)
    assert flight["hex"] == "r1"
    assert pending == [newer_first_sighting]


def test_pop_fresh_pending_reads_an_entry_saved_without_last_seen():
    import server.poll_cycle as poll_cycle
    pending = [{"flight": {"hex": "o1"}, "first_seen": 1.0}, {"flight": {"hex": "o2"}, "first_seen": 2.0}]
    flight, _dropped = poll_cycle.pop_fresh_pending(pending, 10.0)
    assert flight["hex"] == "o2"


def test_pop_fresh_pending_still_drops_deferred_entries_once_stale():
    import server.poll_cycle as poll_cycle
    pending = [_entry("g1", 0.0, True)]
    dropped_entries = []
    flight, dropped = poll_cycle.pop_fresh_pending(
        pending, 1000.0, defer=lambda f: f["on_ground"], dropped_entries=dropped_entries)
    assert flight is None
    assert dropped == ["g1"]
    assert [e["flight"]["hex"] for e in dropped_entries] == ["g1"]
    assert pending == []


def test_enqueue_refreshes_last_seen_and_keeps_first_seen():
    import server.poll_cycle as poll_cycle
    pending = []
    poll_cycle.enqueue_pending(pending, {"hex": "a1", "altitude_ft": 500}, 100.0)
    poll_cycle.enqueue_pending(pending, {"hex": "a1", "altitude_ft": 300}, 130.0)
    (entry,) = pending
    assert (entry["first_seen"], entry["last_seen"], entry["flight"]["altitude_ft"]) == (100.0, 130.0, 300)


def test_normalise_pending_fills_last_seen_from_first_seen():
    import server.poll_cycle as poll_cycle
    saved = [{"flight": {"hex": "a1"}, "first_seen": 5.0},
             {"flight": {"hex": "b2"}, "first_seen": 6.0, "last_seen": 8.5},
             {"flight": "bad", "first_seen": 1.0}]
    entries = poll_cycle.normalise_pending(saved)
    assert [(e["flight"]["hex"], e["first_seen"], e["last_seen"]) for e in entries] == [
        ("a1", 5.0, 5.0), ("b2", 6.0, 8.5)]


def test_roll_out_after_an_arrival_holds_arriving_whatever_the_vertical_rate():
    flight = {"on_ground": True, "vertical_rate_fpm": 320}
    assert runway_config.infer_from_flight(flight, runway_config.STATE_ARRIVING) == "arriving"


def test_on_the_ground_without_a_held_arrival_keeps_the_usual_inference():
    flight = {"on_ground": True, "vertical_rate_fpm": 320}
    assert runway_config.infer_from_flight(flight, None) == "departing"
    assert runway_config.infer_from_flight(flight, runway_config.STATE_DEPARTING) == "departing"


def test_airborne_climb_after_an_arrival_is_still_a_departure():
    flight = {"on_ground": False, "vertical_rate_fpm": 1800}
    assert runway_config.infer_from_flight(flight, runway_config.STATE_ARRIVING) == "departing"
