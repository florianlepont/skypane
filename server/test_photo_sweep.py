"""The orphan sweep reconciles the photo tree with the device_photos table."""
import os

import pytest

import photo_samples
from photo_fleet import seed_photo_fleet
from server import fleet_db, photo_paths, photo_purge, photo_quota, photo_store

NOW = 1_700_000_000
GRACE = 900


@pytest.fixture(autouse=True)
def _no_disk_floor(monkeypatch):
    monkeypatch.setattr(photo_quota, "MIN_FREE_DISK_BYTES", 0)


@pytest.fixture
def env(tmp_path):
    state = str(tmp_path)
    fleet = seed_photo_fleet(state)
    conn = fleet_db.connect(state)
    mgr = photo_store.authorize_manager(conn, fleet.device_id, fleet.owner_id)
    yield state, conn, fleet, mgr
    conn.close()


def _add(env, count=1):
    state, conn, _f, mgr = env
    return [photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
            for _ in range(count)]


def _dir(state, device_id):
    return os.path.join(state, "photos", device_id)


def _write(path, age, now=NOW):
    with open(path, "wb") as fh:
        fh.write(b"x")
    stamp = now - age
    os.utime(path, (stamp, stamp))


def _sweep(env, now=NOW):
    state, conn, _f, _m = env
    return photo_purge.sweep(conn, state, now=now, grace_seconds=GRACE)


def test_clean_tree_sweeps_to_zeros(env):
    _add(env, 2)
    assert _sweep(env) == photo_purge.SweepCounts()


def test_no_photos_directory_returns_zeros_and_creates_nothing(env):
    state = env[0]
    assert _sweep(env) == photo_purge.SweepCounts()
    assert not os.path.exists(os.path.join(state, "photos"))


def test_directory_of_a_vanished_device_goes_without_grace(env):
    state = env[0]
    ghost = os.path.join(state, "photos", "d_0badf00d")
    os.makedirs(ghost)
    _write(os.path.join(ghost, "ph_" + "a" * 16 + ".jpg"), age=0)
    counts = _sweep(env)
    assert counts.orphan_dirs == 1
    assert not os.path.exists(ghost)


def test_directory_with_an_invalid_name_goes_and_link_target_survives(
        env, tmp_path_factory):
    state = env[0]
    outside = tmp_path_factory.mktemp("outside")
    (outside / "keep.txt").write_text("k")
    odd = os.path.join(state, "photos", "not a device")
    os.makedirs(odd)
    os.symlink(outside, os.path.join(odd, "inner"))
    counts = _sweep(env)
    assert counts.orphan_dirs == 1 and counts.links == 1
    assert not os.path.exists(odd)
    assert (outside / "keep.txt").read_text() == "k"


def test_unrowed_file_is_removed_only_after_the_grace_period(env):
    state, _conn, f, _m = env
    (pid,) = _add(env)
    directory = _dir(state, f.device_id)
    young = os.path.join(directory, "ph_" + "b" * 16 + ".jpg")
    old = os.path.join(directory, "ph_" + "c" * 16 + ".jpg")
    _write(young, age=GRACE - 60)
    _write(old, age=GRACE + 60)
    counts = _sweep(env)
    assert counts.orphan_files == 1
    assert os.path.exists(young) and not os.path.exists(old)
    assert os.path.exists(os.path.join(directory, pid + ".jpg"))
    assert _sweep(env, now=NOW + GRACE + 120).orphan_files == 1
    assert not os.path.exists(young)


def test_stale_temp_goes_and_in_flight_temp_stays(env):
    state, _conn, f, _m = env
    _add(env)
    directory = _dir(state, f.device_id)
    young = os.path.join(directory, photo_paths.TEMP_PREFIX + "young")
    old = os.path.join(directory, photo_paths.TEMP_PREFIX + "old")
    _write(young, age=10)
    _write(old, age=GRACE + 10)
    counts = _sweep(env)
    assert counts.stale_temps == 1
    assert os.path.exists(young) and not os.path.exists(old)


def test_row_without_a_file_is_deleted(env):
    state, conn, f, mgr = env
    a, b = _add(env, 2)
    os.unlink(os.path.join(_dir(state, f.device_id), a + ".jpg"))
    counts = _sweep(env)
    assert counts.missing_rows == 1
    assert [r["id"] for r in fleet_db.list_photo_rows(conn, f.device_id)] == [b]
    assert [p for p in photo_store.list_photos(mgr, conn)]


def test_symlinks_are_removed_as_links_never_followed(env, tmp_path_factory):
    state, conn, f, _m = env
    (pid,) = _add(env)
    outside = tmp_path_factory.mktemp("outside")
    secret = outside / "secret.jpg"
    secret.write_bytes(b"secret")
    directory = _dir(state, f.device_id)
    os.symlink(secret, os.path.join(directory, "ph_" + "d" * 16 + ".jpg"))
    os.symlink(outside, os.path.join(directory, "subdir"))
    final = os.path.join(directory, pid + ".jpg")
    os.unlink(final)
    os.symlink(secret, final)  # a link in place of the row's file
    counts = _sweep(env)
    assert counts.links == 3
    assert counts.missing_rows == 1
    assert secret.read_bytes() == b"secret"
    assert os.listdir(outside) == ["secret.jpg"]
    assert fleet_db.list_photo_rows(conn, f.device_id) == []


def test_symlinked_photos_directory_is_refused(env, tmp_path_factory):
    state, conn, f, _m = env
    outside = tmp_path_factory.mktemp("outside")
    ghost = outside / "d_0badf00d"
    ghost.mkdir()
    (ghost / "x.jpg").write_bytes(b"x")
    os.symlink(outside, os.path.join(state, "photos"))
    fleet_db.insert_photo(conn, "ph_" + "e" * 16, f.device_id, 10, 1, 1, None, NOW)
    counts = _sweep(env)
    assert counts.refused == 1
    assert counts == photo_purge.SweepCounts(refused=1)
    assert (ghost / "x.jpg").exists()
    assert len(fleet_db.list_photo_rows(conn, f.device_id)) == 1
    assert os.path.islink(os.path.join(state, "photos"))


def test_second_run_returns_zeros(env, tmp_path_factory):
    state, _conn, f, _m = env
    _add(env)
    os.makedirs(os.path.join(state, "photos", "d_0badf00d"))
    _write(os.path.join(_dir(state, f.device_id), photo_paths.TEMP_PREFIX + "o"),
           age=GRACE + 1)
    first = _sweep(env)
    assert sum(first) > 0
    assert _sweep(env) == photo_purge.SweepCounts()


def test_restore_without_photos_reconciles_the_table(env):
    import shutil

    state, conn, f, mgr = env
    _add(env, 3)
    shutil.rmtree(os.path.join(state, "photos"))
    counts = _sweep(env)
    assert counts.missing_rows == 3
    assert fleet_db.all_photo_refs(conn) == []
    assert photo_store.list_photos(mgr, conn) == []


def test_sweep_output_is_integers_and_silent(env, capsys, caplog):
    state = env[0]
    os.makedirs(os.path.join(state, "photos", "d_0badf00d"))
    with caplog.at_level("DEBUG"):
        counts = _sweep(env)
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    assert caplog.records == []
    assert all(type(v) is int for v in counts)
