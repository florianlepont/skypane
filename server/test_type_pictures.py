# SPDX-License-Identifier: AGPL-3.0-only
"""An airline has no picture of its own: its pictures are those of its aircraft types.
`type_pictures` lists them by type code (built-in files, fleet-wide uploads and the legacy
`{airline}.png`, which counts as the picture of its airframe type); the runtime picks them in the
order exact type, effective default type, generic by shape, universal."""
import json
import os

from server.plane import airline_default_types as adt
from server.plane import illustrations as ill
from server.test_illustrations import _make_fixture_png


def _rig(tmp_path, monkeypatch, files):
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path / "art"))
    (tmp_path / "art").mkdir()
    (tmp_path / "state").mkdir()
    for name in files:
        _make_fixture_png(tmp_path / "art" / name)
    return str(tmp_path / "state")


def _store_default(state, entries):
    with open(os.path.join(state, adt.DEFAULT_TYPES_FILENAME), "w") as fh:
        json.dump(entries, fh)


def _upload(state, key):
    os.makedirs(os.path.join(state, ill.ILLUSTRATION_OVERRIDE_DIRNAME), exist_ok=True)
    _make_fixture_png(os.path.join(state, ill.ILLUSTRATION_OVERRIDE_DIRNAME, key + ".png"))


def test_a_built_in_airline_lists_its_legacy_picture_as_its_airframe_type(tmp_path):
    pictures = ill.type_pictures("air-france", str(tmp_path))
    assert list(pictures) == ["A320"]
    assert pictures["A320"].key == "air-france"
    assert os.path.basename(pictures["A320"].path) == "air-france.png"


def test_typed_files_and_the_legacy_picture_are_listed_side_by_side(tmp_path):
    pictures = ill.type_pictures("transavia-france", str(tmp_path))
    assert set(pictures) == {"B737", "A320"}
    assert pictures["A320"].key == "transavia-france-a320"
    assert pictures["B737"].key == "transavia-france"
    caraibes = ill.type_pictures("air-caraibes", str(tmp_path))
    assert set(caraibes) == {"A350", "A330", "A350-1000", "ATR72"}


def test_an_upload_wins_over_the_built_in_file_and_a_seen_type_finds_its_slot(tmp_path):
    state = str(tmp_path)
    _upload(state, "transavia-france-a320")
    assert ill.type_pictures("transavia-france", state)["A320"].path.startswith(state)
    _upload(state, "acme-air-embraer")
    assert ill.type_pictures("acme-air", state, codes=("E190",))["E190"].key == "acme-air-embraer"
    assert ill.type_pictures("acme-air", state) == {"EMBRAER": ill.TypePicture(
        "acme-air-embraer", os.path.join(state, "illustration_overrides", "acme-air-embraer.png"))}


def test_the_legacy_picture_of_a_hand_named_airline_has_the_type_chosen_at_upload(tmp_path):
    state = str(tmp_path)
    _upload(state, "acme-air")
    assert ill.type_pictures("acme-air", state) == {}
    _store_default(state, {"acme-air": "A321"})
    assert list(ill.type_pictures("acme-air", state)) == ["A321"]
    assert ill.has_type_livery("acme-air", "A321", state)
    assert not ill.has_type_livery("acme-air", "B738", state)
    assert ill.default_picture("acme-air", state).key == "acme-air"


def test_a_renamed_built_in_airline_keeps_the_airframe_of_its_original(tmp_path):
    from server.plane import name_overrides
    state = str(tmp_path)
    name_overrides.set_names(state, ["TAP"], "TAP Air Portugal", own_builtin_name="TAP Portugal")
    _upload(state, "tap-air-portugal")
    assert list(ill.type_pictures("tap-air-portugal", state)) == ["A321"]


def test_unsafe_or_empty_keys_list_nothing(tmp_path):
    for key in (None, "", "../x", "a/b"):
        assert ill.type_pictures(key, str(tmp_path)) == {}
        assert ill.default_picture(key, str(tmp_path)) is None
    assert not ill.has_type_livery("air-france", "", str(tmp_path))


def test_tier_order_exact_then_effective_default_then_generic_then_universal(tmp_path, monkeypatch):
    state = _rig(tmp_path, monkeypatch, [
        "acme-air-a320.png", "acme-air-b737.png", "generic-b737.png", ill.GENERIC_FALLBACK_FILENAME])
    _store_default(state, {"acme-air": "A320"})

    def pick(code):
        return os.path.basename(ill.select_illustration({"airline_name": "Acme Air"}, code, state))

    assert pick("B738") == "acme-air-b737.png"
    (tmp_path / "art" / "acme-air-b737.png").unlink()
    assert pick("B738") == "acme-air-a320.png"
    (tmp_path / "art" / "acme-air-a320.png").unlink()
    assert pick("B738") == "generic-b737.png"
    assert pick("ZZZZ") == ill.GENERIC_FALLBACK_FILENAME


def test_the_legacy_picture_acts_as_the_effective_default_without_a_stored_default(tmp_path, monkeypatch):
    state = _rig(tmp_path, monkeypatch, [
        "acme-air.png", "acme-air-a320.png", "generic-b737.png", ill.GENERIC_FALLBACK_FILENAME])
    route = {"airline_name": "Acme Air"}
    assert os.path.basename(ill.select_illustration(route, "B738", state)) == "acme-air.png"
    _store_default(state, {"acme-air": "A320"})
    assert os.path.basename(ill.select_illustration(route, "B738", state)) == "acme-air-a320.png"
    os.unlink(os.path.join(state, adt.DEFAULT_TYPES_FILENAME))
    assert os.path.basename(ill.select_illustration(route, "B738", state)) == "acme-air.png"


def test_a_stored_default_naming_the_legacy_airframe_serves_the_legacy_picture(tmp_path, monkeypatch):
    state = _rig(tmp_path, monkeypatch, ["acme-air.png", "generic-b737.png"])
    _store_default(state, {"acme-air": "A320"})
    assert os.path.basename(ill.select_illustration(
        {"airline_name": "Acme Air"}, "B738", state)) == "acme-air.png"


def test_two_designators_with_the_same_picture_slot_are_one_type():
    assert ill.same_type("B738", "B737") and ill.same_type("a320", "A321")
    assert not ill.same_type("B738", "A320") and not ill.same_type("A35K", "A359")
    assert not ill.same_type("ZZZZ", "YYYY") and ill.same_type("ZZZZ", "zzzz")
    assert not ill.same_type("", "")
    assert ill.type_slug("A35K") == "a350-1000" and ill.type_slug("B738") == "b737"


def test_a_seen_type_and_the_legacy_airframe_of_one_slot_are_one_picture(tmp_path):
    state = str(tmp_path)
    pictures = ill.type_pictures("transavia-france", state, codes=("B738", "A320"))
    # The legacy picture is the B737: the seen B738 is the same row, not a second one.
    assert set(pictures) == {"A320", "B738"}
    assert pictures["B738"].key == "transavia-france"
    assert ill.has_type_livery("transavia-france", "B738", state)
    assert ill.has_type_livery("transavia-france", "B737", state)
    assert not ill.has_type_livery("transavia-france", "A333", state)


def test_a_default_naming_a_seen_type_of_the_legacy_slot_serves_the_legacy_picture(tmp_path):
    state = str(tmp_path)
    assert adt.set_default_type(state, "transavia-france", "B738") == adt.SET_OK
    assert ill.default_picture("transavia-france", state).key == "transavia-france"
    assert ill.effective_default_type("transavia-france", state) == "B738"
