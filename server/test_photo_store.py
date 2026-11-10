"""Photo store behaviour on a temporary state directory."""
import contextlib
import logging
import os
import stat
import threading

import pytest

import photo_samples
from photo_fleet import seed_photo_fleet
from server import fleet_db, photo_paths, photo_quota, photo_store
from server.photo.normalize import PhotoRejected

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


def _tree(state):
    out = []
    for base, dirs, files in os.walk(os.path.join(state, "photos")):
        out.extend(os.path.join(base, n) for n in dirs + files)
    return sorted(out)


def _rows(conn, device_id):
    return len(fleet_db.list_photo_rows(conn, device_id))


def _jpeg(seed=1):
    return photo_samples.noise_jpeg_bytes(400, 300, seed=seed)


# ---- authorize_manager ---------------------------------------------------

def test_owner_and_co_manager_are_authorized(env):
    state, conn, f, mgr = env
    assert mgr.device_id == f.device_id and mgr.user_id == f.owner_id
    co = photo_store.authorize_manager(conn, f.device_id, f.co_manager_id)
    assert co.user_id == f.co_manager_id


def test_everyone_else_gets_the_same_denial(env):
    state, conn, f, mgr = env
    fleet_db.remove_co_manager(conn, f.device_id, f.co_manager_id)
    messages = set()
    for dev, user in (
        (f.device_id, f.other_id), (f.device_id, f.admin_id),
        (f.device_id, f.disabled_id), (f.device_id, f.co_manager_id),
        (f.device_id, None), ("d_00000000", f.owner_id), ("../x", f.owner_id),
        ("", f.owner_id), (f.device_id, 99999),
    ):
        with pytest.raises(photo_store.PhotoAccessDenied) as exc:
            photo_store.authorize_manager(conn, dev, user)
        messages.add(str(exc.value))
    assert len(messages) == 1


def test_a_hand_built_capability_is_refused(env):
    state, conn, f, mgr = env
    forged = photo_store.FrameManager(f.device_id, f.other_id)
    with pytest.raises(photo_store.PhotoAccessDenied):
        photo_store.list_photos(forged, conn)
    with pytest.raises(photo_store.PhotoAccessDenied):
        photo_store.add(forged, conn, state, _jpeg(), NOW)
    assert not os.path.exists(os.path.join(state, "photos"))


# ---- add / list / read / delete -----------------------------------------

def test_add_list_read_delete_roundtrip(env):
    state, conn, f, mgr = env
    pid = photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert photo_paths.is_valid_photo_id(pid)
    final = os.path.join(state, "photos", f.device_id, pid + ".jpg")
    assert os.path.isfile(final)
    assert stat.S_IMODE(os.stat(final).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(os.path.dirname(final)).st_mode) == 0o700
    listed = photo_store.list_photos(mgr, conn)
    assert [p.id for p in listed] == [pid]
    assert listed[0].created_at == NOW and listed[0].size_bytes == os.path.getsize(final)
    data = photo_store.read_photo(mgr, conn, state, pid)
    assert data == open(final, "rb").read() and data[:2] == b"\xff\xd8"
    photo_store.delete_photo(mgr, conn, state, pid)
    assert _tree(state) == [os.path.dirname(final)]
    assert photo_store.list_photos(mgr, conn) == []
    with pytest.raises(photo_store.PhotoNotFound):
        photo_store.read_photo(mgr, conn, state, pid)


def test_list_keeps_upload_order(env):
    state, conn, f, mgr = env
    ids = [photo_store.add(mgr, conn, state, _jpeg(i), NOW + i) for i in range(3)]
    assert [p.id for p in photo_store.list_photos(mgr, conn)] == ids


def test_co_manager_can_add_and_owner_can_read_it(env):
    state, conn, f, mgr = env
    co = photo_store.authorize_manager(conn, f.device_id, f.co_manager_id)
    pid = photo_store.add(co, conn, state, _jpeg(), NOW)
    assert photo_store.read_photo(mgr, conn, state, pid)


def test_original_upload_bytes_are_not_stored(env):
    state, conn, f, mgr = env
    raw = photo_samples.png_bytes(900, 700)
    pid = photo_store.add(mgr, conn, state, raw, NOW)
    stored = photo_store.read_photo(mgr, conn, state, pid)
    assert stored != raw and stored[:2] == b"\xff\xd8"
    assert len(_tree(state)) == 2  # device directory + one file


def test_rejected_upload_stores_nothing(env):
    state, conn, f, mgr = env
    with pytest.raises(PhotoRejected):
        photo_store.add(mgr, conn, state, photo_samples.HTML_BYTES, NOW)
    assert _tree(state) == [] and _rows(conn, f.device_id) == 0


def test_delete_missing_file_is_fine_and_unknown_id_is_not_found(env):
    state, conn, f, mgr = env
    pid = photo_store.add(mgr, conn, state, _jpeg(), NOW)
    os.unlink(os.path.join(state, "photos", f.device_id, pid + ".jpg"))
    photo_store.delete_photo(mgr, conn, state, pid)
    for bad in (pid, "ph_0000000000000000", "../x", "", None):
        with pytest.raises(photo_store.PhotoNotFound):
            photo_store.delete_photo(mgr, conn, state, bad)
        with pytest.raises(photo_store.PhotoNotFound):
            photo_store.read_photo(mgr, conn, state, bad)


# ---- quota refusals store nothing ----------------------------------------

def test_refusals_leave_directory_and_rows_unchanged(env, monkeypatch):
    state, conn, f, mgr = env
    monkeypatch.setattr(photo_quota, "MAX_PHOTOS_PER_FRAME", 1)
    photo_store.add(mgr, conn, state, _jpeg(1), NOW)
    before = _tree(state)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_store.add(mgr, conn, state, _jpeg(2), NOW)
    assert exc.value.code == "frame_count"
    assert _tree(state) == before and _rows(conn, f.device_id) == 1


@pytest.mark.parametrize("name,value,code", [
    ("MAX_BYTES_PER_FRAME", 10, "frame_bytes"),
    ("MAX_BYTES_SERVER", 10, "server_bytes"),
    ("MIN_FREE_DISK_BYTES", 1 << 62, "disk_low"),
])
def test_each_quota_code_stores_nothing(env, monkeypatch, name, value, code):
    state, conn, f, mgr = env
    monkeypatch.setattr(photo_quota, name, value)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert exc.value.code == code
    assert _tree(state) == [os.path.join(state, "photos", f.device_id)]
    assert _rows(conn, f.device_id) == 0


def test_twenty_one_photos_hit_the_default_limit(env):
    state, conn, f, mgr = env
    for i in range(photo_quota.MAX_PHOTOS_PER_FRAME):
        fleet_db.insert_photo(conn, "ph_%016x" % i, f.device_id, 10, 400, 300, None, NOW)
    with pytest.raises(photo_quota.QuotaExceeded) as exc:
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert exc.value.code == "frame_count"


# ---- failure injection ---------------------------------------------------

def test_failure_after_temp_write_leaves_nothing(env, monkeypatch):
    state, conn, f, mgr = env

    def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(photo_quota, "check", boom)
    with pytest.raises(RuntimeError):
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert _tree(state) == [os.path.join(state, "photos", f.device_id)]
    assert _rows(conn, f.device_id) == 0


def test_failure_after_row_insert_leaves_nothing(env, monkeypatch):
    state, conn, f, mgr = env
    real = fleet_db.insert_photo

    def insert_then_fail(*a, **k):
        real(*a, **k)
        raise RuntimeError("injected")

    monkeypatch.setattr(fleet_db, "insert_photo", insert_then_fail)
    with pytest.raises(RuntimeError):
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert _tree(state) == [os.path.join(state, "photos", f.device_id)]
    assert _rows(conn, f.device_id) == 0


def test_commit_failure_after_publish_unlinks_the_file(env, monkeypatch):
    state, conn, f, mgr = env
    real = fleet_db.transaction

    @contextlib.contextmanager
    def failing_commit(c):
        with real(c):
            yield c
            raise RuntimeError("injected commit failure")

    monkeypatch.setattr(fleet_db, "transaction", failing_commit)
    with pytest.raises(RuntimeError):
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    assert _tree(state) == [os.path.join(state, "photos", f.device_id)]
    assert _rows(conn, f.device_id) == 0


# ---- concurrency ---------------------------------------------------------

def test_concurrent_uploads_end_at_exactly_the_limit(env, monkeypatch):
    state, conn, f, mgr = env
    monkeypatch.setattr(photo_quota, "MAX_PHOTOS_PER_FRAME", 3)
    raws = [_jpeg(i) for i in range(8)]
    results = []
    lock = threading.Lock()

    def worker(raw):
        c = fleet_db.connect(state)
        try:
            m = photo_store.authorize_manager(c, f.device_id, f.owner_id)
            try:
                outcome = photo_store.add(m, c, state, raw, NOW)
            except photo_quota.QuotaExceeded as exc:
                outcome = exc.code
        except BaseException as exc:  # surfaced by the assertions below
            outcome = repr(exc)
        finally:
            c.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(r,)) for r in raws]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r for r in results if r == "frame_count") == ["frame_count"] * 5
    assert _rows(conn, f.device_id) == 3
    files = os.listdir(os.path.join(state, "photos", f.device_id))
    assert len(files) == 3 and all(n.endswith(".jpg") for n in files)


# ---- no leakage ----------------------------------------------------------

def test_errors_and_logs_carry_no_path_or_bytes(env, monkeypatch, caplog):
    state, conn, f, mgr = env
    monkeypatch.setattr(photo_quota, "MAX_PHOTOS_PER_FRAME", 0)
    caplog.set_level(logging.DEBUG)
    with pytest.raises(photo_quota.QuotaExceeded) as full:
        photo_store.add(mgr, conn, state, _jpeg(), NOW)
    with pytest.raises(photo_store.PhotoNotFound) as missing:
        photo_store.read_photo(mgr, conn, state, "ph_0000000000000000")
    with pytest.raises(photo_store.PhotoAccessDenied) as denied:
        photo_store.authorize_manager(conn, f.device_id, f.other_id)
    for exc in (full.value, missing.value, denied.value):
        text = str(exc) + repr(exc)
        assert state not in text and f.device_id not in text and "/" not in text
    assert state not in caplog.text
