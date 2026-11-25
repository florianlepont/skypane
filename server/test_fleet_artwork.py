"""The per-frame to fleet artwork merge: conflict rule, archive, idempotence,
rollback safety (per-frame files never touched), caps and hostile input."""
import hashlib
import io
import itertools
import json
import os

import pytest
from PIL import Image

from server import device_dirs
from server.plane import fleet_artwork as fa
from server.plane import illustrations

A, B, C = "d_0000000a", "d_0000000b", "d_0000000c"
DIRNAME = illustrations.ILLUSTRATION_OVERRIDE_DIRNAME
NOW = "2026-06-01T00:00:00+00:00"
T1, T2, T3 = 1_700_000_000, 1_710_000_000, 1_720_000_000


def _png(shade=0, width=None, height=400):
    buffer = io.BytesIO()
    Image.new("RGBA", (width or illustrations.ILLUSTRATION_MIN_WIDTH, height),
              (shade % 256, 30, 30, 128)).save(buffer, format="PNG")
    return buffer.getvalue()


def _frame(root, device_id):
    return device_dirs.provision_device_dir(str(root), device_id, 800, 480)


def _put(directory, name, data, mtime=None):
    folder = os.path.join(str(directory), DIRNAME)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "wb") as fh:
        fh.write(data)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _tree(root):
    """Relative path -> (sha256, mtime_ns) for every file under `root`."""
    out = {}
    for base, _dirs, files in os.walk(str(root)):
        for name in files:
            path = os.path.join(base, name)
            with open(path, "rb") as fh:
                out[os.path.relpath(path, str(root))] = (
                    hashlib.sha256(fh.read()).hexdigest(), os.stat(path).st_mtime_ns)
    return out


def _devices_tree(root):
    return {k: v for k, v in _tree(root).items() if k.startswith("devices")}


def _merge(root):
    plan = fa.plan_merge(str(root))
    return plan, fa.apply_merge(str(root), plan, now=NOW)


def _read(root, *parts):
    with open(os.path.join(str(root), *parts), "rb") as fh:
        return fh.read()


def _fleet(root, name):
    return os.path.join(str(root), DIRNAME, name)


def test_merge_without_conflict_keeps_bytes_and_times_and_touches_no_frame_file(tmp_path):
    root = tmp_path
    a, b = _frame(root, A), _frame(root, B)
    _put(a, "ocn.png", _png(1), T1)
    _put(a, "ocn-a320.png", _png(2), T2)
    _put(b, "zzz.png", _png(3), T3)
    _put(root, "ryr.png", _png(4), T1)
    frames_before = _devices_tree(root)

    _plan, lines = _merge(root)

    assert sorted(os.listdir(os.path.join(str(root), DIRNAME))) == [
        "ocn-a320.png", "ocn.png", "ryr.png", "zzz.png"]
    for name, shade, mtime in (("ocn.png", 1, T1), ("ocn-a320.png", 2, T2), ("zzz.png", 3, T3)):
        assert _read(root, DIRNAME, name) == _png(shade)
        assert os.stat(_fleet(root, name)).st_mtime == mtime
    assert _devices_tree(root) == frames_before
    marker = json.loads(_read(root, fa.MARKER_FILENAME))
    assert marker["merged"] == {
        "%s/ocn.png" % A: hashlib.sha256(_png(1)).hexdigest(),
        "%s/ocn-a320.png" % A: hashlib.sha256(_png(2)).hexdigest(),
        "%s/zzz.png" % B: hashlib.sha256(_png(3)).hexdigest()}
    assert not os.path.exists(os.path.join(str(root), fa.CONFLICTS_DIRNAME))
    assert any("merged 3 picture(s)" in line for line in lines)


def test_the_latest_file_time_wins_and_every_loser_is_archived(tmp_path):
    root = tmp_path
    a, b = _frame(root, A), _frame(root, B)
    _put(root, "ocn.png", _png(1), T2)
    _put(a, "ocn.png", _png(2), T3)
    _put(b, "ocn.png", _png(3), T1)

    _plan, lines = _merge(root)

    assert _read(root, DIRNAME, "ocn.png") == _png(2)
    assert os.stat(_fleet(root, "ocn.png")).st_mtime == T3
    archived = {
        folder: _read(root, fa.CONFLICTS_DIRNAME, folder, "ocn.png")
        for folder in ("live", B)}
    assert archived == {"live": _png(1), B: _png(3)}
    assert os.stat(os.path.join(str(root), fa.CONFLICTS_DIRNAME, "live", "ocn.png")).st_mtime == T2
    assert os.stat(os.path.join(str(root), fa.CONFLICTS_DIRNAME, B, "ocn.png")).st_mtime == T1
    conflict_lines = [line for line in lines if "conflict ocn.png" in line]
    assert len(conflict_lines) == 2
    assert all("keep [frame %s," % A in line for line in conflict_lines)
    marker = json.loads(_read(root, fa.MARKER_FILENAME))
    assert len(marker["conflicts"]) == 2


@pytest.mark.parametrize("order", list(itertools.permutations([A, B, C])))
def test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order(tmp_path, order):
    root = tmp_path
    frames = {device_id: _frame(root, device_id) for device_id in order}
    for shade, device_id in enumerate(order, start=1):
        _put(frames[device_id], "ocn.png", _png(shade * 10), T2)
    expected = _png((order.index(A) + 1) * 10)
    _merge(root)
    assert _read(root, DIRNAME, "ocn.png") == expected


def test_a_tie_with_the_fleet_file_keeps_the_fleet_file(tmp_path):
    root = tmp_path
    _put(root, "ocn.png", _png(1), T2)
    _put(_frame(root, A), "ocn.png", _png(2), T2)
    _merge(root)
    assert _read(root, DIRNAME, "ocn.png") == _png(1)
    assert _read(root, fa.CONFLICTS_DIRNAME, A, "ocn.png") == _png(2)


def test_a_second_archived_version_gets_a_numeric_suffix_and_never_overwrites(tmp_path):
    root = tmp_path
    a = _frame(root, A)
    _put(root, "ocn.png", _png(1), T3)
    _put(a, "ocn.png", _png(2), T1)
    _merge(root)
    _put(a, "ocn.png", _png(5), T2)
    _merge(root)
    folder = os.path.join(str(root), fa.CONFLICTS_DIRNAME, A)
    assert sorted(os.listdir(folder)) == ["ocn.1.png", "ocn.png"]
    assert _read(root, fa.CONFLICTS_DIRNAME, A, "ocn.png") == _png(2)
    assert _read(root, fa.CONFLICTS_DIRNAME, A, "ocn.1.png") == _png(5)


def test_identical_bytes_are_neither_a_conflict_nor_copied_nor_archived(tmp_path):
    root = tmp_path
    _put(root, "ocn.png", _png(1), T1)
    _put(_frame(root, A), "ocn.png", _png(1), T3)
    _put(_frame(root, B), "ocn.png", _png(1), T2)
    plan, lines = _merge(root)
    assert plan.conflicts == 0 and plan.new == 0 and plan.replaced == 0
    assert os.stat(_fleet(root, "ocn.png")).st_mtime == T1
    assert not os.path.exists(os.path.join(str(root), fa.CONFLICTS_DIRNAME))
    assert not any("conflict" in line.split("fleet directory:")[-1] and "keep" in line for line in lines)


def test_a_second_run_changes_nothing_and_a_removed_picture_stays_removed(tmp_path):
    root = tmp_path
    a = _frame(root, A)
    _put(a, "ocn.png", _png(1), T1)
    _put(a, "zzz.png", _png(2), T2)
    _put(_frame(root, B), "zzz.png", _png(3), T3)
    _merge(root)
    first = _tree(root)

    _plan, lines = _merge(root)
    assert _tree(root) == first
    assert lines == ["artwork: nothing to do"]

    os.unlink(_fleet(root, "ocn.png"))
    _merge(root)
    assert not os.path.exists(_fleet(root, "ocn.png"))

    _put(a, "zzz.png", _png(9), T3 + 5)
    plan, _lines = _merge(root)
    assert plan.pending == 1
    assert _read(root, DIRNAME, "zzz.png") == _png(9)
    assert not os.path.exists(_fleet(root, "ocn.png"))


def test_a_dry_run_plan_writes_nothing(tmp_path):
    root = tmp_path
    _put(_frame(root, A), "ocn.png", _png(1), T1)
    _put(root, "ocn.png", _png(2), T2)
    before = _tree(root)
    plan = fa.plan_merge(str(root))
    lines = fa.report_lines(plan, dry_run=True)
    assert _tree(root) == before
    assert not os.path.exists(os.path.join(str(root), fa.MARKER_FILENAME))
    assert lines[0].startswith("artwork: would merge 1 picture(s)")


def test_hostile_or_invalid_candidates_are_skipped_reported_and_never_deleted(tmp_path):
    root = tmp_path
    a = _frame(root, A)
    _put(a, "good.png", _png(1), T1)
    folder = os.path.join(a, DIRNAME)
    outside = tmp_path / "outside.png"
    outside.write_bytes(_png(7))
    os.symlink(str(outside), os.path.join(folder, "linked.png"))
    for bad in ("a b.png", "UP.png", "x.jpg", "..x.png", "-lead.png"):
        _put(a, bad, _png(2))
    _put(a, ".hidden.png", _png(2))
    _put(a, "leftover.png.upload.1.tmp", _png(2))
    _put(a, "big.png", b"\x00" * (fa.MAX_UPLOAD_BYTES + 1))
    _put(a, "text.png", b"not a png at all")
    _put(a, "bomb.png", _png(3, width=illustrations.ILLUSTRATION_MAX_PIXELS // 400 + 50))
    _put(a, "cut.png", _png(4)[:200])
    # A symlinked image directory on frame B and a symlinked device directory.
    b = _frame(root, B)
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "sneaky.png").write_bytes(_png(5))
    os.symlink(str(target), os.path.join(b, DIRNAME))
    c_target = tmp_path / "c-target"
    (c_target / DIRNAME).mkdir(parents=True)
    (c_target / DIRNAME / "viaC.png").write_bytes(_png(6))
    os.symlink(str(c_target), os.path.join(str(root), "devices", C))
    os.makedirs(os.path.join(str(root), "devices", "not-a-device", DIRNAME))
    _put(os.path.join(str(root), "devices", "not-a-device"), "evil.png", _png(8))
    before = _tree(root)
    before_outside = (outside.read_bytes(), sorted(os.listdir(str(target))))

    plan, lines = _merge(root)

    assert sorted(os.listdir(os.path.join(str(root), DIRNAME))) == ["good.png"]
    text = "\n".join(lines)
    for fragment in ("linked.png of frame %s: symlink" % A, "a b.png", "UP.png", "x.jpg",
                     "big.png of frame %s: over the" % A, "text.png", "bomb.png", "cut.png",
                     "%s of frame %s: symlink" % (DIRNAME, B), ".hidden.png", "leftover.png.upload.1.tmp"):
        assert fragment in text, fragment
    assert "sneaky" not in text and "viaC" not in text and "evil" not in text
    after = _tree(root)
    for path, value in before.items():
        assert after[path] == value, path
    assert (outside.read_bytes(), sorted(os.listdir(str(target)))) == before_outside
    assert plan.new == 1


def test_the_live_frames_own_directory_is_never_a_device_source(tmp_path):
    root = tmp_path
    _put(root, "ocn.png", _png(1), T1)
    plan, lines = _merge(root)
    assert plan.seen == 0 and lines == []
    assert not os.path.exists(os.path.join(str(root), fa.MARKER_FILENAME))


def test_a_symlinked_fleet_directory_is_not_written_through(tmp_path):
    root = tmp_path / "state"
    root.mkdir()
    _put(_frame(root, A), "ocn.png", _png(1), T1)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    os.symlink(str(elsewhere), str(root / DIRNAME))
    _plan, lines = _merge(root)
    assert os.listdir(str(elsewhere)) == []
    assert any("fleet directory is a symlink" in line for line in lines)


def test_the_file_cap_merges_the_latest_first_and_leaves_the_rest_pending(tmp_path, monkeypatch):
    root = tmp_path
    a = _frame(root, A)
    for index in range(5):
        _put(a, "k%d.png" % index, _png(index), T1 + index)
    monkeypatch.setattr(fa, "MAX_MERGED_FILES", 3)
    plan, lines = _merge(root)
    assert sorted(os.listdir(os.path.join(str(root), DIRNAME))) == ["k2.png", "k3.png", "k4.png"]
    assert any("2 file(s) beyond the per-run cap" in line for line in lines)
    assert sorted(os.listdir(os.path.join(a, DIRNAME))) == ["k%d.png" % i for i in range(5)]
    marker = json.loads(_read(root, fa.MARKER_FILENAME))
    assert sorted(marker["merged"]) == ["%s/k%d.png" % (A, i) for i in (2, 3, 4)]
    monkeypatch.setattr(fa, "MAX_MERGED_FILES", 1000)
    _merge(root)
    assert len(os.listdir(os.path.join(str(root), DIRNAME))) == 5
    assert plan.pending == 3


def test_the_byte_cap_merges_the_latest_first(tmp_path, monkeypatch):
    root = tmp_path
    a = _frame(root, A)
    newest, older = _png(1), _png(2)
    _put(a, "new.png", newest, T2)
    _put(a, "old.png", older, T1)
    monkeypatch.setattr(fa, "MAX_MERGED_BYTES", len(newest) + len(older) - 1)
    _merge(root)
    assert os.listdir(os.path.join(str(root), DIRNAME)) == ["new.png"]


def test_the_upload_cap_equals_the_companion_upload_cap():
    from companion import upload_form
    assert fa.MAX_UPLOAD_BYTES == upload_form.MAX_UPLOAD_BYTES


def test_a_write_failure_raises_and_writes_no_marker(tmp_path, monkeypatch):
    root = tmp_path
    _put(_frame(root, A), "ocn.png", _png(1), T1)
    monkeypatch.setattr(fa.atomic_io, "atomic_write",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    plan = fa.plan_merge(str(root))
    with pytest.raises(OSError):
        fa.apply_merge(str(root), plan, now=NOW)
    assert not os.path.exists(os.path.join(str(root), fa.MARKER_FILENAME))
