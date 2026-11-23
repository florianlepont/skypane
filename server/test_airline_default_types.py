"""The owner's default aircraft type per airline: the file contract (never-raising load,
validate-before-write, the cap) and the round trip."""
import json
import os

from server.plane import airline_default_types as adt
from server.plane import illustrations


def _picture(state, key, code):
    """An uploaded picture for the airline's type `code`."""
    path = illustrations.override_path_for_key(
        illustrations.type_artwork_keys(key, code)[0], state)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"png")


def test_a_default_type_round_trips_and_is_normalised(tmp_path):
    state = str(tmp_path)
    assert adt.load_default_types(state) == {}
    _picture(state, "air-france", "A321")
    _picture(state, "transavia-france", "B738")
    assert adt.set_default_type(state, "air-france", " a321 ") == adt.SET_OK
    assert adt.set_default_type(state, "transavia-france", "B738") == adt.SET_OK
    assert adt.load_default_types(state) == {"air-france": "A321", "transavia-france": "B738"}


def test_an_empty_type_clears_the_entry(tmp_path):
    state = str(tmp_path)
    _picture(state, "air-france", "A320")
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
    _picture(state, "one-more", "A320")
    _picture(state, "k1", "B738")
    assert adt.set_default_type(state, "one-more", "A320") == adt.SET_FULL
    assert adt.set_default_type(state, "k1", "B738") == adt.SET_OK


def test_default_types_are_one_fleet_file_and_the_file_loader_is_path_based(tmp_path):
    from server import device_dirs
    frame_a = device_dirs.provision_device_dir(str(tmp_path), "d_0123abcd", 800, 480)
    frame_b = device_dirs.provision_device_dir(str(tmp_path), "d_4567cdef", 800, 480)
    _picture(str(tmp_path), "air-france", "A321")
    assert adt.set_default_type(frame_a, "air-france", "A321") == adt.SET_OK
    assert not os.path.exists(os.path.join(frame_a, adt.DEFAULT_TYPES_FILENAME))
    assert adt.load_default_types(frame_b) == {"air-france": "A321"}
    own = os.path.join(frame_b, adt.DEFAULT_TYPES_FILENAME)
    with open(own, "w") as fh:
        json.dump({"zz-air": "b738", "../x": "A320"}, fh)
    assert adt.load_default_types_file(own) == {"zz-air": "B738"}
    assert adt.load_default_types(frame_b) == {"air-france": "A321"}


def test_a_type_without_a_picture_is_refused_and_writes_nothing(tmp_path):
    state = str(tmp_path)
    assert adt.set_default_type(state, "air-france", "A320") == adt.SET_REJECTED
    assert not os.path.exists(adt.default_types_path(state))


def test_a_built_in_picture_is_a_livery(tmp_path):
    state = str(tmp_path)
    assert adt.set_default_type(state, "transavia-france", "A320") == adt.SET_OK


def test_a_picture_stored_in_the_same_request_counts_through_livery_key(tmp_path):
    state = str(tmp_path)
    assert adt.set_default_type(state, "air-france", "B738", livery_key="air-france") == adt.SET_OK
    assert adt.set_default_type(state, "xqz-wings", "B738", livery_key="xqz-wings") == adt.SET_REJECTED
    assert adt.load_default_types(state) == {"air-france": "B738"}
