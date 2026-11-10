"""Photo id shape, path refusal and quota precedence."""
import os
import stat

import pytest

from photo_fleet import seed_photo_fleet
from server import fleet_db, hardware, photo_paths, photo_quota

GOOD_FREE = 10_000_000_000


# ---- ids and paths -------------------------------------------------------

def test_new_photo_id_has_the_expected_shape():
    pid = photo_paths.new_photo_id()
    assert photo_paths.is_valid_photo_id(pid)
    assert pid != photo_paths.new_photo_id()


@pytest.mark.parametrize("bad", [
    "ph_../x", "ph_0123456789abcdef\n", "ph_0123456789ABCDEF", "ph_0123",
    "ph_0123456789abcdef0", "", "x_0123456789abcdef", None, 5, b"ph_0123456789abcdef",
])
def test_bad_photo_ids_are_refused(bad):
    assert not photo_paths.is_valid_photo_id(bad)


def test_paths_refuse_invalid_ids(tmp_path):
    root = str(tmp_path)
    for dev in ("../x", "d_zzzzzzzz", "", "d_0123abcd\n"):
        with pytest.raises(ValueError):
            photo_paths.photo_dir(root, dev)
    with pytest.raises(ValueError):
        photo_paths.photo_file(root, "d_0123abcd", "ph_../x")


def test_ensure_photo_dir_modes_ignore_umask(tmp_path):
    old = os.umask(0)
    try:
        directory = photo_paths.ensure_photo_dir(str(tmp_path), "d_0123abcd")
    finally:
        os.umask(old)
    assert directory == str(tmp_path / "photos" / "d_0123abcd")
    for path in (tmp_path / "photos", tmp_path / "photos" / "d_0123abcd"):
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o700


def test_symlinked_photos_directory_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    os.symlink(outside, state / "photos")
    with pytest.raises(ValueError):
        photo_paths.photo_dir(str(state), "d_0123abcd")
    with pytest.raises(ValueError):
        photo_paths.ensure_photo_dir(str(state), "d_0123abcd")
    assert list(outside.iterdir()) == []


def test_symlinked_device_directory_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    state = tmp_path / "state"
    (state / "photos").mkdir(parents=True)
    os.symlink(outside, state / "photos" / "d_0123abcd")
    with pytest.raises(ValueError):
        photo_paths.ensure_photo_dir(str(state), "d_0123abcd")
    assert list(outside.iterdir()) == []


def test_symlinked_file_is_refused(tmp_path):
    target = tmp_path / "secret.txt"
    target.write_bytes(b"keep")
    directory = photo_paths.ensure_photo_dir(str(tmp_path), "d_0123abcd")
    pid = photo_paths.new_photo_id()
    os.symlink(target, os.path.join(directory, pid + ".jpg"))
    with pytest.raises(ValueError):
        photo_paths.photo_file(str(tmp_path), "d_0123abcd", pid)
    assert target.read_bytes() == b"keep"


# ---- quota ---------------------------------------------------------------

@pytest.fixture
def fleet(tmp_path):
    state = str(tmp_path)
    seeded = seed_photo_fleet(state)
    conn = fleet_db.connect(state)
    yield conn, seeded
    conn.close()


def _fill(conn, device_id, count, each=1000, start=0):
    for i in range(count):
        fleet_db.insert_photo(
            conn, "ph_%016x" % (start + i), device_id, each, 400, 300, None, 1)


def test_accepts_exactly_on_every_limit(fleet):
    conn, f = fleet
    _fill(conn, f.device_id, photo_quota.MAX_PHOTOS_PER_FRAME - 1, each=1)
    photo_quota.check(conn, f.device_id, 1, GOOD_FREE)


def test_frame_count_refuses_the_21st(fleet):
    conn, f = fleet
    _fill(conn, f.device_id, photo_quota.MAX_PHOTOS_PER_FRAME)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 1, GOOD_FREE)
    assert exc.value.code == "frame_count"


def test_frame_bytes_boundary(fleet):
    conn, f = fleet
    _fill(conn, f.device_id, 19, each=1_000_000)
    photo_quota.check(conn, f.device_id, 1_000_000, GOOD_FREE)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 1_000_001, GOOD_FREE)
    assert exc.value.code == "frame_bytes"


def test_server_bytes_counts_other_frames(fleet, monkeypatch):
    conn, f = fleet
    other = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:11", "d" * 64, hardware.LEGACY_KEY, f.owner_id, state_path="auto")
    monkeypatch.setattr(photo_quota, "MAX_BYTES_SERVER", 10_000)
    _fill(conn, other, 9, each=1_000)
    photo_quota.check(conn, f.device_id, 1_000, GOOD_FREE)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 1_001, GOOD_FREE)
    assert exc.value.code == "server_bytes"


def test_server_bytes_code_when_frame_has_room(fleet, monkeypatch):
    conn, f = fleet
    monkeypatch.setattr(photo_quota, "MAX_BYTES_SERVER", 5000)
    _fill(conn, f.device_id, 1, each=4000)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 1001, GOOD_FREE)
    assert exc.value.code == "server_bytes"
    photo_quota.check(conn, f.device_id, 1000, GOOD_FREE)


def test_disk_low_boundary_and_precedence(fleet):
    conn, f = fleet
    photo_quota.check(conn, f.device_id, 1000, photo_quota.MIN_FREE_DISK_BYTES + 1000)
    _fill(conn, f.device_id, photo_quota.MAX_PHOTOS_PER_FRAME)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 1000, photo_quota.MIN_FREE_DISK_BYTES + 999)
    assert exc.value.code == "disk_low"


def test_frame_count_wins_over_bytes_and_server(fleet, monkeypatch):
    conn, f = fleet
    monkeypatch.setattr(photo_quota, "MAX_BYTES_SERVER", 10)
    _fill(conn, f.device_id, photo_quota.MAX_PHOTOS_PER_FRAME, each=1_000_000)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_quota.check(conn, f.device_id, 5, GOOD_FREE)
    assert exc.value.code == "frame_count"


def test_free_disk_bytes_is_a_positive_int(tmp_path):
    assert photo_quota.free_disk_bytes(str(tmp_path)) > 0
