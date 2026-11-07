"""The owner's default aircraft type per airline: the file contract (never-raising load,
validate-before-write, the cap) and the round trip."""
import json
import os

from server.plane import airline_default_types as adt


def test_a_default_type_round_trips_and_is_normalised(tmp_path):
    state = str(tmp_path)
    assert adt.load_default_types(state) == {}
    assert adt.set_default_type(state, "air-france", " a321 ") == adt.SET_OK
    assert adt.set_default_type(state, "transavia-france", "B738") == adt.SET_OK
    assert adt.load_default_types(state) == {"air-france": "A321", "transavia-france": "B738"}


def test_an_empty_type_clears_the_entry(tmp_path):
    state = str(tmp_path)
    adt.set_default_type(state, "air-france", "A320")
    assert adt.set_default_type(state, "air-france", "") == adt.SET_OK
    assert adt.load_default_types(state) == {}
    assert adt.set_default_type(state, "never-set", None) == adt.SET_OK


def test_unsafe_keys_and_codes_are_refused_and_write_nothing(tmp_path):
    state = str(tmp_path)
    for key, code in (("../etc", "A320"), ("Air France", "A320"), ("", "A320"), (None, "A320"),
                      ("air-france", "a320; drop"), ("air-france", "A"), ("air-france", "x" * 20)):
        assert adt.set_default_type(state, key, code) == adt.SET_REJECTED, (key, code)
    assert not os.path.exists(adt.default_types_path(state))


def test_a_hand_edited_file_is_validated_on_read(tmp_path):
    state = str(tmp_path)
    with open(adt.default_types_path(state), "w") as fh:
        json.dump({"ok-key": "a320", "../bad": "A320", "bad-code": "no way!", "n": 3}, fh)
    assert adt.load_default_types(state) == {"ok-key": "A320"}
    with open(adt.default_types_path(state), "w") as fh:
        fh.write("not json")
    assert adt.load_default_types(state) == {}
    assert adt.load_default_types("") == {}


def test_the_registry_is_capped(tmp_path):
    state = str(tmp_path)
    with open(adt.default_types_path(state), "w") as fh:
        json.dump({"k%d" % n: "A320" for n in range(adt.MAX_ENTRIES)}, fh)
    assert adt.set_default_type(state, "one-more", "A320") == adt.SET_FULL
    assert adt.set_default_type(state, "k1", "B738") == adt.SET_OK
