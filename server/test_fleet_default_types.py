"""The one-time clearing of default aircraft types that have no picture: plan and
apply, the archive, the marker and the report lines."""
import json
import os

from server.plane import airline_default_types as adt
from server.plane import fleet_default_types as fdt
from server.plane import illustrations

NOW = "2026-06-01T00:00:00+00:00"


def _stored(root, entries):
    with open(adt.default_types_path(root), "w") as fh:
        json.dump(entries, fh)


def _upload(root, key, code):
    path = illustrations.override_path_for_key(illustrations.type_artwork_keys(key, code)[0], root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"png")


def _seed(root):
    _stored(root, {
        "air-france": "B738",          # no picture: cleared
        "transavia-france": "A320",    # built-in picture: kept
        "zephyr-air": "B738",          # fleet override exists: kept
        "xqz-wings": "A330",           # no picture: cleared
    })
    _upload(str(root), "zephyr-air", "B738")


def test_the_plan_lists_only_defaults_without_a_picture(tmp_path):
    _seed(str(tmp_path))
    plan = fdt.plan_clear(str(tmp_path))
    assert plan.to_clear == [("air-france", "B738"), ("xqz-wings", "A330")]
    assert fdt.report_lines(plan, dry_run=True) == [
        "airline default types: would clear 2",
        "airline default types: would clear air-france: B738",
        "airline default types: would clear xqz-wings: A330"]


def test_a_dry_run_writes_nothing(tmp_path):
    root = str(tmp_path)
    _seed(root)
    before = sorted(os.listdir(root))
    content = open(adt.default_types_path(root)).read()
    fdt.report_lines(fdt.plan_clear(root), dry_run=True)
    assert sorted(os.listdir(root)) == before
    assert open(adt.default_types_path(root)).read() == content


def test_apply_archives_clears_marks_and_leaves_the_others(tmp_path):
    root = str(tmp_path)
    _seed(root)
    lines = fdt.apply_clear(root, fdt.plan_clear(root), now=NOW)
    assert lines[0] == "airline default types: cleared 2"
    assert adt.load_default_types(root) == {"transavia-france": "A320", "zephyr-air": "B738"}
    archive = json.load(open(os.path.join(root, fdt.ARCHIVE_FILENAME)))
    assert archive == [
        {"airline_key": "air-france", "type": "B738", "source": "fleet", "cleared_at": NOW},
        {"airline_key": "xqz-wings", "type": "A330", "source": "fleet", "cleared_at": NOW}]
    assert json.load(open(os.path.join(root, fdt.MARKER_FILENAME)))["cleared"] == 2


def test_a_second_run_is_a_no_op_even_for_a_default_stored_later(tmp_path):
    root = str(tmp_path)
    _seed(root)
    fdt.apply_clear(root, fdt.plan_clear(root), now=NOW)
    _stored(root, {"late-air": "A320"})
    snapshot = {n: open(os.path.join(root, n)).read() for n in os.listdir(root) if os.path.isfile(os.path.join(root, n))}
    plan = fdt.plan_clear(root)
    assert plan.done and not plan.needs_write
    assert fdt.apply_clear(root, plan) == ["airline default types: nothing to do"]
    assert {n: open(os.path.join(root, n)).read() for n in os.listdir(root) if os.path.isfile(os.path.join(root, n))} == snapshot


def test_nothing_to_clear_writes_nothing(tmp_path):
    root = str(tmp_path)
    _stored(root, {"transavia-france": "A320"})
    assert fdt.apply_clear(root, fdt.plan_clear(root)) == ["airline default types: nothing to do"]
    assert not os.path.exists(os.path.join(root, fdt.MARKER_FILENAME))
    assert not os.path.exists(os.path.join(root, fdt.ARCHIVE_FILENAME))


def test_an_earlier_archive_is_extended_not_replaced(tmp_path):
    root = str(tmp_path)
    _stored(root, {"air-france": "B738"})
    with open(os.path.join(root, fdt.ARCHIVE_FILENAME), "w") as fh:
        json.dump([{"airline_key": "old", "type": "A320", "source": "fleet", "cleared_at": "x"}], fh)
    fdt.apply_clear(root, fdt.plan_clear(root), now=NOW)
    assert [r["airline_key"] for r in json.load(open(os.path.join(root, fdt.ARCHIVE_FILENAME)))] == [
        "old", "air-france"]


def test_per_frame_files_are_never_touched(tmp_path):
    from server import device_dirs
    root = str(tmp_path)
    frame = device_dirs.provision_device_dir(root, "d_0123abcd", 800, 480)
    frozen = os.path.join(frame, adt.DEFAULT_TYPES_FILENAME)
    with open(frozen, "w") as fh:
        json.dump({"air-france": "B738"}, fh)
    _stored(root, {"air-france": "B738"})
    fdt.apply_clear(root, fdt.plan_clear(root), now=NOW)
    assert json.load(open(frozen)) == {"air-france": "B738"}
