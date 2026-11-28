# SPDX-License-Identifier: AGPL-3.0-only
"""The one-time choice of a default aircraft type for every airline that has pictures and none:
the rules a/b/c/d, the dry run, the archive, the marker and the report lines."""
import json
import os

from server import history_db
from server.plane import airline_default_types as adt
from server.plane import fleet_set_defaults as fsd
from server.plane import illustrations as ill
from server.test_illustrations import _make_fixture_png

NOW = "2026-06-01T00:00:00+00:00"


def _upload(root, key):
    directory = os.path.join(root, ill.ILLUSTRATION_OVERRIDE_DIRNAME)
    os.makedirs(directory, exist_ok=True)
    _make_fixture_png(os.path.join(directory, key + ".png"))


def _stored(root, entries):
    with open(adt.default_types_path(root), "w") as fh:
        json.dump(entries, fh)


def _sight(directory, airline, code, times):
    os.makedirs(directory, exist_ok=True)
    with history_db.open_db(directory) as conn:
        for index in range(times):
            history_db.record_runway_event(
                conn, ts="2026-05-%02dT10:00:00+00:00" % (index + 1), hex="h%03d" % index,
                callsign="ZZZ%03d" % index, aircraft_type=code, confirmed_state="departing",
                airline=airline)


def _plan(root):
    return fsd.plan_set(str(root))


def _rules(plan):
    return {key: (code, rule) for key, code, rule in plan.to_set}


def test_rule_a_a_legacy_picture_with_a_known_airframe_gives_that_type(tmp_path):
    rules = _rules(_plan(tmp_path))
    assert rules["air-france"] == ("A320", "a")
    assert rules["tap-portugal"] == ("A321", "a")
    # Transavia has a legacy B737 picture and a typed A320 one: the legacy rule comes first.
    assert rules["transavia-france"] == ("B737", "a")


def test_rule_a_a_hand_named_airline_with_a_stored_default_is_left_alone(tmp_path):
    _upload(str(tmp_path), "acme-air")
    _stored(str(tmp_path), {"acme-air": "A321"})
    plan = _plan(tmp_path)
    assert "acme-air" not in _rules(plan)
    assert all(key != "acme-air" for key, _reason in plan.unresolved)


def test_rule_b_one_typed_picture_is_the_default(tmp_path):
    _upload(str(tmp_path), "acme-air-b737")
    assert _rules(_plan(tmp_path))["acme-air"] == ("B737", "b")


def test_rule_b_several_typed_pictures_take_the_most_seen_type(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-a320")
    _upload(root, "acme-air-b737")
    _sight(root, "Acme Air", "A320", 1)
    _sight(os.path.join(root, "devices", "d_0123abcd"), "Acme Air", "B738", 3)
    assert _rules(_plan(tmp_path))["acme-air"] == ("B737", "b")


def test_rule_b_a_tie_or_no_sighting_takes_the_first_type_code_alphabetically(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-b737")
    _upload(root, "acme-air-a320")
    assert _rules(_plan(tmp_path))["acme-air"] == ("A320", "b")
    _sight(root, "Acme Air", "A320", 2)
    _sight(root, "Acme Air", "B738", 2)
    assert _rules(_plan(tmp_path))["acme-air"] == ("A320", "b")


def test_rule_b_a_flight_of_a_type_without_a_picture_counts_for_its_slot(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-a320")
    _upload(root, "acme-air-b737")
    _sight(root, "Acme Air", "A20N", 1)
    _sight(root, "Acme Air", "B739", 4)
    assert _rules(_plan(tmp_path))["acme-air"] == ("B737", "b")


def test_rule_c_a_legacy_picture_of_an_unknown_airframe_takes_the_most_seen_typed_picture(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air")
    _upload(root, "acme-air-a320")
    _upload(root, "acme-air-b737")
    _sight(root, "Acme Air", "B738", 2)
    plan = _plan(tmp_path)
    assert _rules(plan)["acme-air"] == ("B737", "c")


def test_rule_c_without_a_seen_typed_picture_the_airline_is_unresolved_and_nothing_is_invented(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air")
    _upload(root, "acme-air-a320")
    plan = _plan(tmp_path)
    assert "acme-air" not in _rules(plan)
    assert [key for key, _reason in plan.unresolved] == ["acme-air"]
    _upload(root, "solo-air")
    assert "solo-air" in [key for key, _reason in _plan(tmp_path).unresolved]


def test_rule_d_an_airline_with_no_picture_gets_nothing(tmp_path):
    plan = _plan(tmp_path)
    assert "finnair" not in _rules(plan)
    assert all(key != "finnair" for key, _reason in plan.unresolved)


def test_a_stored_default_is_never_changed(tmp_path):
    _stored(str(tmp_path), {"air-france": "A320"})
    assert "air-france" not in _rules(_plan(tmp_path))


def test_report_lines_and_a_dry_run_that_writes_nothing(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-b737")
    _upload(root, "solo-air")
    _upload(root, "solo-air-a320")
    before = sorted(os.listdir(root))
    lines = fsd.report_lines(_plan(tmp_path), dry_run=True)
    assert lines[0].startswith("airline default types: would set ")
    assert "airline default types: would set acme-air: B737 (rule b)" in lines
    assert "airline default types: would set air-france: A320 (rule a)" in lines
    assert "airline default types: unresolved 1" in lines
    assert any(line.startswith("airline default types: unresolved solo-air: ") for line in lines)
    assert sorted(os.listdir(root)) == before
    assert not os.path.exists(adt.default_types_path(root))


def test_apply_sets_archives_marks_and_a_second_run_does_nothing(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-b737")
    plan = _plan(tmp_path)
    lines = fsd.apply_set(root, plan, now=NOW)
    assert lines[0] == "airline default types: set %d" % len(plan.to_set)
    stored = adt.load_default_types(root)
    assert stored["acme-air"] == "B737" and stored["air-france"] == "A320"
    archive = json.load(open(os.path.join(root, fsd.ARCHIVE_FILENAME)))
    assert {"airline_key": "acme-air", "type": "B737", "rule": "b", "set_at": NOW} in archive
    assert len(archive) == len(plan.to_set)
    marker = json.load(open(os.path.join(root, fsd.MARKER_FILENAME)))
    assert marker["set"] == len(plan.to_set)
    snapshot = {n: open(os.path.join(root, n)).read() for n in os.listdir(root)
                if os.path.isfile(os.path.join(root, n))}
    again = fsd.plan_set(root)
    assert again.done and not again.needs_write
    assert fsd.apply_set(root, again) == ["airline default types: nothing to do"]
    assert {n: open(os.path.join(root, n)).read() for n in os.listdir(root)
            if os.path.isfile(os.path.join(root, n))} == snapshot


def test_a_default_the_owner_clears_later_is_not_set_again(tmp_path):
    root = str(tmp_path)
    fsd.apply_set(root, _plan(tmp_path), now=NOW)
    adt.set_default_type(root, "air-france", "")
    assert fsd.apply_set(root, fsd.plan_set(root)) == ["airline default types: nothing to do"]
    assert "air-france" not in adt.load_default_types(root)


def test_a_dry_run_judges_defaults_about_to_be_cleared_as_gone(tmp_path):
    root = str(tmp_path)
    _stored(root, {"air-france": "B738"})
    assert "air-france" not in _rules(fsd.plan_set(root))
    assert _rules(fsd.plan_set(root, cleared={"air-france"}))["air-france"] == ("A320", "a")


def test_an_unreadable_history_counts_as_no_sighting(tmp_path):
    root = str(tmp_path)
    _upload(root, "acme-air-b737")
    _upload(root, "acme-air-a320")
    with open(history_db.history_db_path(root), "wb") as fh:
        fh.write(b"not a database")
    assert _rules(_plan(tmp_path))["acme-air"] == ("A320", "b")
