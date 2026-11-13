"""remove_files and purge_frame on a temporary state directory."""
import os

import pytest

import photo_samples
from photo_fleet import seed_photo_fleet
from server import fleet_db, photo_paths, photo_purge, photo_quota, photo_store

NOW = 1_700_000_000


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
    state, conn, fleet, mgr = env
    return [photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
            for _ in range(count)]


def _file(state, device_id, pid):
    return os.path.join(state, "photos", device_id, pid + ".jpg")


def test_remove_files_unlinks_files_of_deleted_rows(env):
    state, conn, f, _ = env
    a, b = _add(env, 2)
    fleet_db.delete_photo_row(conn, f.device_id, a)
    result = photo_purge.remove_files(
        conn, state, [(f.device_id, a), (f.device_id, b)])
    assert result == (1, 0)
    assert not os.path.exists(_file(state, f.device_id, a))
    assert os.path.exists(_file(state, f.device_id, b))  # row still exists


def test_remove_files_leaves_a_file_whose_row_survived(env):
    state, conn, f, _ = env
    (pid,) = _add(env)
    assert photo_purge.remove_files(conn, state, [(f.device_id, pid)]) == (0, 0)
    assert os.path.exists(_file(state, f.device_id, pid))


def test_remove_files_tolerates_missing_and_malformed_refs(env):
    state, conn, f, _ = env
    refs = [(f.device_id, "ph_" + "0" * 16), ("../x", "ph_" + "1" * 16),
            (f.device_id, "../../etc/passwd"), (f.device_id, None)]
    assert photo_purge.remove_files(conn, state, refs) == (0, 0)  # type: ignore[arg-type]


def test_remove_files_removes_an_emptied_directory(env):
    state, conn, f, _ = env
    (pid,) = _add(env)
    fleet_db.delete_photo_row(conn, f.device_id, pid)
    photo_purge.remove_files(conn, state, [(f.device_id, pid)])
    assert not os.path.exists(os.path.join(state, "photos", f.device_id))


def test_remove_files_keeps_a_directory_that_still_has_files(env):
    state, conn, f, _ = env
    a, b = _add(env, 2)
    fleet_db.delete_photo_row(conn, f.device_id, a)
    photo_purge.remove_files(conn, state, [(f.device_id, a)])
    assert os.path.isdir(os.path.join(state, "photos", f.device_id))


def test_remove_files_unlinks_a_planted_link_not_its_target(env, tmp_path_factory):
    state, conn, f, _ = env
    (pid,) = _add(env)
    outside = tmp_path_factory.mktemp("outside") / "keep.jpg"
    outside.write_bytes(b"keep")
    final = _file(state, f.device_id, pid)
    os.unlink(final)
    os.symlink(outside, final)
    fleet_db.delete_photo_row(conn, f.device_id, pid)
    assert photo_purge.remove_files(conn, state, [(f.device_id, pid)]) == (1, 0)
    assert not os.path.lexists(final)
    assert outside.read_bytes() == b"keep"


def test_unlink_failure_is_counted_and_others_continue(env, monkeypatch):
    state, conn, f, _ = env
    a, b = _add(env, 2)
    for pid in (a, b):
        fleet_db.delete_photo_row(conn, f.device_id, pid)
    real = os.unlink

    def flaky(path, *args, **kwargs):
        if str(path).endswith(a + ".jpg"):
            raise PermissionError(13, "denied: " + str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", flaky)
    result = photo_purge.remove_files(
        conn, state, [(f.device_id, a), (f.device_id, b)])
    assert result == (1, 1)
    assert not os.path.exists(_file(state, f.device_id, b))
    assert os.path.exists(_file(state, f.device_id, a))


def test_purge_frame_removes_rows_files_directory_and_temp(env):
    state, conn, f, _ = env
    ids = _add(env, 3)
    directory = os.path.join(state, "photos", f.device_id)
    with open(os.path.join(directory, photo_paths.TEMP_PREFIX + "abc"), "wb") as fh:
        fh.write(b"partial")
    assert photo_purge.purge_frame(conn, state, f.device_id) == (3, 0)
    assert fleet_db.list_photo_rows(conn, f.device_id) == []
    assert not os.path.exists(directory)
    assert all(not os.path.exists(_file(state, f.device_id, p)) for p in ids)
    assert photo_purge.purge_frame(conn, state, f.device_id) == (0, 0)


def test_purge_frame_does_not_touch_other_frames(env):
    state, conn, f, _ = env
    from server import hardware
    other = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:77", "e" * 64, hardware.LEGACY_KEY, f.other_id,
        state_path="auto")
    mgr_b = photo_store.authorize_manager(conn, other, f.other_id)
    pid_b = photo_store.add(mgr_b, conn, state, photo_samples.jpeg_bytes(), NOW)
    _add(env)
    photo_purge.purge_frame(conn, state, f.device_id)
    assert os.path.exists(_file(state, other, pid_b))
    assert len(fleet_db.list_photo_rows(conn, other)) == 1


def test_purge_frame_removes_links_inside_the_directory(env, tmp_path_factory):
    state, conn, f, _ = env
    _add(env)
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("s")
    directory = os.path.join(state, "photos", f.device_id)
    os.symlink(outside, os.path.join(directory, "link"))
    photo_purge.purge_frame(conn, state, f.device_id)
    assert (outside / "secret.txt").read_text() == "s"
    assert not os.path.exists(directory)


def test_purge_frame_unlinks_a_symlinked_device_directory(env, tmp_path_factory):
    state, conn, f, _ = env
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("s")
    os.makedirs(os.path.join(state, "photos"))
    os.symlink(outside, os.path.join(state, "photos", f.device_id))
    photo_purge.purge_frame(conn, state, f.device_id)
    assert (outside / "secret.txt").read_text() == "s"
    assert not os.path.lexists(os.path.join(state, "photos", f.device_id))


def test_purge_frame_rejects_a_malformed_device_id(env):
    state, conn, _f, _ = env
    for bad in ("../x", "", "d_zzzz", None):
        with pytest.raises(ValueError):
            photo_purge.purge_frame(conn, state, bad)  # type: ignore[arg-type]


def test_purge_frame_on_a_frame_without_photos_creates_nothing(env):
    state, conn, f, _ = env
    assert photo_purge.purge_frame(conn, state, f.device_id) == (0, 0)
    assert not os.path.exists(os.path.join(state, "photos"))
