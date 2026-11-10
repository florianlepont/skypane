"""The photo store's privacy wall: capability-only access, no role knob,
no cross-frame reads, no symlink following."""
import inspect
import os

import pytest

import photo_samples
from photo_fleet import seed_photo_fleet
from server import fleet_db, hardware, photo_paths, photo_quota, photo_store

NOW = 1_700_000_000
# Public functions that are not user-facing store operations. Later work
# that adds a system-only function must name it here on purpose.
SYSTEM_ONLY = frozenset({"authorize_manager"})
FORBIDDEN_PARAMS = {"role", "admin", "is_admin"}


@pytest.fixture(autouse=True)
def _no_disk_floor(monkeypatch):
    monkeypatch.setattr(photo_quota, "MIN_FREE_DISK_BYTES", 0)


@pytest.fixture
def env(tmp_path):
    state = str(tmp_path)
    fleet = seed_photo_fleet(state)
    conn = fleet_db.connect(state)
    yield state, conn, fleet
    conn.close()


def _public_functions():
    return {
        name: fn for name, fn in inspect.getmembers(photo_store, inspect.isfunction)
        if not name.startswith("_") and fn.__module__ == photo_store.__name__
    }


def test_user_facing_functions_take_the_capability_first_and_no_role():
    funcs = _public_functions()
    assert {"add", "list_photos", "read_photo", "delete_photo"} <= set(funcs)
    for name, fn in funcs.items():
        params = list(inspect.signature(fn).parameters.values())
        assert not FORBIDDEN_PARAMS & {p.name for p in params}, name
        if name in SYSTEM_ONLY:
            continue
        assert params[0].name == "manager", name
        assert params[0].annotation in (photo_store.FrameManager, "FrameManager"), name


def test_authorize_matrix(env):
    state, conn, f = env
    fleet_db.add_co_manager(conn, f.device_id, f.other_id, f.owner_id)
    fleet_db.remove_co_manager(conn, f.device_id, f.other_id)  # removed co-manager
    allowed = {f.owner_id, f.co_manager_id}
    principals = {
        "owner": f.owner_id, "co-manager": f.co_manager_id, "other": f.other_id,
        "anonymous": None, "admin": f.admin_id, "disabled": f.disabled_id,
        "removed co-manager": f.other_id, "missing user": 98765,
    }
    denials = set()
    for label, user in principals.items():
        if user in allowed:
            cap = photo_store.authorize_manager(conn, f.device_id, user)
            assert (cap.device_id, cap.user_id) == (f.device_id, user), label
            continue
        with pytest.raises(photo_store.PhotoAccessDenied) as exc:
            photo_store.authorize_manager(conn, f.device_id, user)
        denials.add((type(exc.value), str(exc.value)))
    for device in ("d_00000000", "../x", "d_zzzzzzzz", "", "d_0123abcd\n", None):
        with pytest.raises(photo_store.PhotoAccessDenied) as exc:
            photo_store.authorize_manager(conn, device, f.owner_id)
        denials.add((type(exc.value), str(exc.value)))
    assert len(denials) == 1


def test_admin_and_disabled_owner_are_refused(env):
    state, conn, f = env
    # The admin role is never consulted: an admin who is neither owner nor
    # co-manager is refused, and so is a disabled owner.
    with pytest.raises(photo_store.PhotoAccessDenied):
        photo_store.authorize_manager(conn, f.device_id, f.admin_id)
    conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (f.owner_id,))
    with pytest.raises(photo_store.PhotoAccessDenied):
        photo_store.authorize_manager(conn, f.device_id, f.owner_id)


def _second_frame(conn, f):
    other = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:77", "e" * 64, hardware.LEGACY_KEY, f.other_id,
        state_path="auto")
    return photo_store.authorize_manager(conn, other, f.other_id)


def test_photo_of_frame_a_never_resolves_through_frame_b(env):
    state, conn, f = env
    mgr_a = photo_store.authorize_manager(conn, f.device_id, f.owner_id)
    mgr_b = _second_frame(conn, f)
    pid = photo_store.add(mgr_a, conn, state, photo_samples.jpeg_bytes(), NOW)
    with pytest.raises(photo_store.PhotoNotFound):
        photo_store.read_photo(mgr_b, conn, state, pid)
    with pytest.raises(photo_store.PhotoNotFound):
        photo_store.delete_photo(mgr_b, conn, state, pid)
    assert photo_store.list_photos(mgr_b, conn) == []
    assert os.path.isfile(os.path.join(state, "photos", f.device_id, pid + ".jpg"))
    assert photo_store.read_photo(mgr_a, conn, state, pid)


def test_planted_symlink_is_never_read_or_removed(env, tmp_path_factory):
    state, conn, f = env
    mgr = photo_store.authorize_manager(conn, f.device_id, f.owner_id)
    outside = tmp_path_factory.mktemp("outside") / "secret.jpg"
    outside.write_bytes(b"outside-secret")
    pid = photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
    final = os.path.join(state, "photos", f.device_id, pid + ".jpg")
    os.unlink(final)
    os.symlink(outside, final)
    with pytest.raises(photo_store.PhotoNotFound):
        photo_store.read_photo(mgr, conn, state, pid)
    photo_store.delete_photo(mgr, conn, state, pid)
    assert outside.read_bytes() == b"outside-secret"


def test_symlinked_device_directory_blocks_add(env, tmp_path_factory):
    state, conn, f = env
    mgr = photo_store.authorize_manager(conn, f.device_id, f.owner_id)
    outside = tmp_path_factory.mktemp("outside")
    os.makedirs(os.path.join(state, photo_paths.PHOTOS_DIRNAME))
    os.symlink(outside, os.path.join(state, "photos", f.device_id))
    with pytest.raises(ValueError):
        photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
    assert list(outside.iterdir()) == []
    assert fleet_db.list_photo_rows(conn, f.device_id) == []
