"""The per-frame to fleet airline registry merge: conflict rule, idempotence,
rollback safety (per-frame files never touched), caps and hostile input."""
import hashlib
import itertools
import json
import os

import pytest

from server import device_dirs
from server.plane import airline_default_types as adt
from server.plane import fleet_registries as fr
from server.plane import manual_resolutions as mr
from server.plane import name_overrides as no

A, B, C = "d_0000000a", "d_0000000b", "d_0000000c"
T1, T2, T3 = "2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00", "2026-03-01T00:00:00+00:00"


def _entry(name, stamp):
    return {"airline_name": name, "created_at": stamp}


def _put(directory, filename, data):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, filename), "w") as fh:
        json.dump(data, fh)


def _frame(root, device_id):
    return device_dirs.provision_device_dir(str(root), device_id, 800, 480)


def _manual(directory, data):
    _put(directory, mr.MANUAL_RESOLUTIONS_FILENAME, data)


def _tree_hashes(root):
    out = {}
    for base, _dirs, files in os.walk(str(root)):
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as fh:
                out[os.path.relpath(path, str(root))] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _merge(root, now="2026-06-01T00:00:00+00:00"):
    plan = fr.plan_merge(str(root))
    return plan, fr.apply_merge(str(root), plan, now=now)


def _root_manual(root):
    return mr.load_registry_file(os.path.join(str(root), mr.MANUAL_RESOLUTIONS_FILENAME))


def test_distinct_names_from_two_frames_all_reach_the_root_and_frame_files_are_untouched(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _manual(str(tmp_path), {"RYR": _entry("Ryan", T1)})
    _manual(a, {"OCN": _entry("Oceanic", T2)})
    _manual(b, {"ZZZ": _entry("Zed Air", T3)})
    frame_files = {k: v for k, v in _tree_hashes(tmp_path).items() if k.startswith("devices")}
    _merge(tmp_path)
    merged = _root_manual(tmp_path)
    assert merged == {"OCN": _entry("Oceanic", T2), "RYR": _entry("Ryan", T1), "ZZZ": _entry("Zed Air", T3)}
    assert {k: v for k, v in _tree_hashes(tmp_path).items() if k.startswith("devices")} == frame_files
    marker = json.load(open(os.path.join(str(tmp_path), fr.MARKER_FILENAME)))
    assert sorted(marker["merged"]) == [
        "devices/%s/manual_resolutions.json" % A, "devices/%s/manual_resolutions.json" % B]


def test_the_newest_stamp_wins_and_the_losers_are_logged_and_recorded(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _manual(str(tmp_path), {"OCN": _entry("Root Name", T1)})
    _manual(a, {"OCN": _entry("Name A", T2)})
    _manual(b, {"OCN": _entry("Name B", T3)})
    plan, lines = _merge(tmp_path)
    assert _root_manual(tmp_path)["OCN"] == _entry("Name B", T3)
    conflicts = [ln for ln in lines if "conflict manual_resolutions OCN" in ln]
    assert len(conflicts) == 2
    assert "'Name B' [frame %s, %s]" % (B, T3) in conflicts[0]
    marker = json.load(open(os.path.join(str(tmp_path), fr.MARKER_FILENAME)))
    assert {(x["lost"], x["lost_frame"]) for x in marker["losers"]} == {
        ("Root Name", "live"), ("Name A", A)}


def test_a_tie_goes_to_the_root_then_to_the_lowest_frame_id(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _manual(str(tmp_path), {"OCN": _entry("Root Name", T2)})
    _manual(a, {"OCN": _entry("Name A", T2), "ZZZ": _entry("Zed A", T2)})
    _manual(b, {"OCN": _entry("Name B", T2), "ZZZ": _entry("Zed B", T2)})
    _merge(tmp_path)
    merged = _root_manual(tmp_path)
    assert merged["OCN"]["airline_name"] == "Root Name"
    assert merged["ZZZ"]["airline_name"] == "Zed A"


def test_an_unparsable_stamp_loses_to_any_valid_one(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _manual(a, {"OCN": _entry("Name A", "not a date")})
    _manual(b, {"OCN": _entry("Name B", T1)})
    _merge(tmp_path)
    assert _root_manual(tmp_path)["OCN"]["airline_name"] == "Name B"


def test_the_result_does_not_depend_on_the_frame_listing_order(tmp_path, monkeypatch):
    frames = [_frame(tmp_path, d) for d in (A, B, C)]
    for index, directory in enumerate(frames):
        _manual(directory, {"OCN": _entry("Name %d" % index, T2), "ZZZ": _entry("Zed %d" % index, T2)})
    results = set()
    real = fr.frame_state_dirs
    for order in itertools.permutations(range(3)):
        monkeypatch.setattr(
            fr, "frame_state_dirs",
            lambda root, order=order: [real(root)[0]] + [real(root)[1:][i] for i in order])
        plan = fr.plan_merge(str(tmp_path))
        results.add(json.dumps(plan.merged, sort_keys=True))
    assert len(results) == 1


def test_a_second_run_changes_nothing_and_a_deleted_name_is_not_brought_back(tmp_path):
    a = _frame(tmp_path, A)
    _manual(a, {"OCN": _entry("Oceanic", T1), "ZZZ": _entry("Zed Air", T2)})
    _merge(tmp_path)
    assert mr.delete_entry(str(tmp_path), "ZZZ") is True
    before = _tree_hashes(tmp_path)
    plan, lines = _merge(tmp_path, now="2027-01-01T00:00:00+00:00")
    assert not plan.needs_write
    assert lines == ["airline names: nothing to do"]
    assert _tree_hashes(tmp_path) == before
    assert "ZZZ" not in _root_manual(tmp_path)


def test_a_frame_file_changed_since_is_merged_again_once(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _manual(a, {"OCN": _entry("Oceanic", T1)})
    _manual(b, {"ZZZ": _entry("Zed Air", T1)})
    _merge(tmp_path)
    mr.delete_entry(str(tmp_path), "ZZZ")
    mr.delete_entry(str(tmp_path), "OCN")
    _manual(a, {"OCN": _entry("Oceanic II", T3)})
    plan, _lines = _merge(tmp_path)
    assert plan.sources_pending == 1
    assert _root_manual(tmp_path) == {"OCN": _entry("Oceanic II", T3)}
    again, _ = _merge(tmp_path)
    assert not again.needs_write


def test_overrides_may_not_take_a_built_in_airlines_name_or_another_airlines_override(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _put(a, no.NAME_OVERRIDES_FILENAME, {
        "AFR": _entry("Transavia France", T1),
        "TVF": _entry("Skyline", T1),
    })
    _put(b, no.NAME_OVERRIDES_FILENAME, {
        "EZY": _entry("Skyline", T2),
        "TFV": _entry("skyline", T3),
    })
    _, lines = _merge(tmp_path)
    merged = no.load_name_overrides(str(tmp_path))
    assert "AFR" not in merged
    assert any("not merged name_overrides AFR" in ln and "built-in airline" in ln for ln in lines)
    # TVF and TFV are the same built-in airline: they keep one shared name; EZY (another carrier) loses it.
    assert set(merged) >= {"TVF", "TFV"} and "EZY" not in merged
    assert any("not merged name_overrides EZY" in ln for ln in lines)


def test_default_types_root_wins_then_lowest_frame_id(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    _put(str(tmp_path), adt.DEFAULT_TYPES_FILENAME, {"air-france": "A320"})
    _put(a, adt.DEFAULT_TYPES_FILENAME, {"air-france": "A350", "zed-air": "B738"})
    _put(b, adt.DEFAULT_TYPES_FILENAME, {"zed-air": "A321", "oceanic": "B77W"})
    _, lines = _merge(tmp_path)
    assert adt.load_default_types(str(tmp_path)) == {"air-france": "A320", "oceanic": "B77W", "zed-air": "B738"}
    assert sum("conflict default_types" in ln for ln in lines) == 2


def test_the_cap_merges_exactly_the_free_room_and_deletes_nothing(tmp_path):
    a = _frame(tmp_path, A)
    names = ["%s%s%s" % (x, y, z) for x in "ABCDEFGH" for y in "ABCDEFGHIJ" for z in "ABCDEFGHIJ"]
    root_entries = {n: _entry("Root %s" % n, T1) for n in names[:150]}
    device_entries = {n: _entry("Frame %s" % n, T2) for n in names[150:250]}
    _manual(str(tmp_path), root_entries)
    _manual(a, device_entries)
    before = _tree_hashes(tmp_path)
    _, lines = _merge(tmp_path)
    merged = _root_manual(tmp_path)
    assert len(merged) == mr.MANUAL_RESOLUTION_MAX_ENTRIES
    assert all(n in merged for n in names[:150])
    assert any("50 entries beyond the 200-entry cap" in ln for ln in lines)
    assert _tree_hashes(tmp_path)[os.path.join("devices", A, mr.MANUAL_RESOLUTIONS_FILENAME)] == before[
        os.path.join("devices", A, mr.MANUAL_RESOLUTIONS_FILENAME)]


def test_hostile_entries_never_reach_the_root_file(tmp_path):
    a = _frame(tmp_path, A)
    _manual(a, {
        "OKA": _entry("Fine Air", T1),
        "BAD": _entry("../../etc/passwd", T1),
        "bad!": _entry("Nope", T1),
        "XXX": "not a dict",
        "YYY": {"airline_name": ["x"], "created_at": T1},
        "ZZZ": _entry("generic-a320", T1),
    })
    _merge(tmp_path)
    assert _root_manual(tmp_path) == {"OKA": _entry("Fine Air", T1)}
    assert ".." not in open(os.path.join(str(tmp_path), mr.MANUAL_RESOLUTIONS_FILENAME)).read()


def test_a_symlinked_frame_directory_or_registry_file_and_bad_names_are_ignored(tmp_path):
    a = _frame(tmp_path, A)
    outside = tmp_path / "outside"
    outside.mkdir()
    _manual(str(outside), {"OUT": _entry("Outside Air", T1)})
    devices = os.path.join(str(tmp_path), "devices")
    os.symlink(str(outside), os.path.join(devices, B))
    os.makedirs(os.path.join(devices, "not-an-id"))
    _manual(os.path.join(devices, "not-an-id"), {"BAD": _entry("Bad Air", T1)})
    os.makedirs(os.path.join(devices, "d_0000000D"))
    _manual(os.path.join(devices, "d_0000000D"), {"UPP": _entry("Upper Air", T1)})
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"LNK": _entry("Linked Air", T1)}))
    os.symlink(str(target), os.path.join(a, mr.MANUAL_RESOLUTIONS_FILENAME))
    plan, lines = _merge(tmp_path)
    assert not os.path.exists(os.path.join(str(tmp_path), mr.MANUAL_RESOLUTIONS_FILENAME))
    assert any("symlink" in ln for ln in lines)
    assert [label for label, _d in fr.frame_state_dirs(str(tmp_path))] == [fr.LIVE_LABEL, A]


def test_an_invalid_or_oversized_frame_file_counts_as_no_entries_and_is_reported(tmp_path):
    a, b = _frame(tmp_path, A), _frame(tmp_path, B)
    with open(os.path.join(a, mr.MANUAL_RESOLUTIONS_FILENAME), "w") as fh:
        fh.write("{not json")
    with open(os.path.join(b, mr.MANUAL_RESOLUTIONS_FILENAME), "w") as fh:
        fh.write(" " * (fr.MAX_SOURCE_BYTES + 1))
    plan, lines = _merge(tmp_path)
    assert not plan.needs_write
    assert any("not valid JSON" in ln for ln in lines)
    assert any("over %d bytes" % fr.MAX_SOURCE_BYTES in ln for ln in lines)


def test_the_live_frames_own_files_are_never_a_source(tmp_path):
    _manual(str(tmp_path), {"RYR": _entry("Ryan", T1)})
    plan = fr.plan_merge(str(tmp_path))
    assert plan.sources_seen == 0 and not plan.needs_write
    assert fr.report_lines(plan, dry_run=True) == []


def test_a_write_failure_raises_and_leaves_no_marker(tmp_path, monkeypatch):
    a = _frame(tmp_path, A)
    _manual(a, {"OCN": _entry("Oceanic", T1)})
    plan = fr.plan_merge(str(tmp_path))

    def boom(path, data):
        raise OSError("disk full")
    monkeypatch.setattr(fr.atomic_io, "atomic_write", boom)
    with pytest.raises(OSError):
        fr.apply_merge(str(tmp_path), plan)
    assert not os.path.exists(os.path.join(str(tmp_path), fr.MARKER_FILENAME))
