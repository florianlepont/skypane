"""Photos disappear from disk and from the table when a frame is retired or
reassigned and when the account that uploaded them is deleted; removing or
disabling a co-manager keeps them."""
import json
import os
import time

import pytest

import fleet_console_support as fx
import photo_samples
from companion import prefs
from companion_app_server import InProcessAppServer
from photo_fleet import seed_photo_fleet
from server import device_dirs, fleet_db, fleet_ops, photo_purge, photo_quota, photo_store

NOW = 1_700_000_000
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")


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


def _upload(conn, state, device_id, user_id, count=1):
    mgr = photo_store.authorize_manager(conn, device_id, user_id)
    return [photo_store.add(mgr, conn, state, photo_samples.jpeg_bytes(), NOW)
            for _ in range(count)]


def _file(state, device_id, photo_id):
    return os.path.join(state, "photos", device_id, photo_id + ".jpg")


def _purge_audit(conn):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM audit_log WHERE action = 'device.photo_purge'")]


def _new_owner(conn):
    return fleet_db.add_user(conn, "new-owner@example.test", "user")


def test_retire_removes_files_rows_and_directory(env):
    state, conn, f = env
    ids = _upload(conn, state, f.device_id, f.owner_id, 3)
    fleet_ops.retire_frame(conn, state, f.device_id, ACTOR)
    assert not os.path.exists(os.path.join(state, "photos", f.device_id))
    assert conn.execute("SELECT COUNT(*) FROM device_photos").fetchone()[0] == 0
    rows = _purge_audit(conn)
    assert len(rows) == 1
    assert json.loads(rows[0]["detail"]) == {"count": 3, "cause": "retire"}
    assert not any(pid in rows[0]["detail"] for pid in ids)
    assert [r for r in conn.execute(
        "SELECT 1 FROM audit_log WHERE action = 'device.retire'")]


def test_retire_without_photos_writes_no_photo_audit_and_no_directory(env):
    state, conn, f = env
    fleet_ops.retire_frame(conn, state, f.device_id, ACTOR)
    assert _purge_audit(conn) == []
    assert not os.path.exists(os.path.join(state, "photos", f.device_id))


def test_refused_retire_of_the_live_frame_keeps_photos(env):
    state, conn, f = env
    conn.execute("UPDATE devices SET state_path = ? WHERE id = ?",
                 (device_dirs.LIVE_STATE_PATH, f.device_id))
    ids = _upload(conn, state, f.device_id, f.owner_id, 2)
    with pytest.raises(fleet_ops.LiveFrameProtected):
        fleet_ops.retire_frame(conn, state, f.device_id, ACTOR)
    assert all(os.path.isfile(_file(state, f.device_id, p)) for p in ids)
    assert len(fleet_db.list_photo_rows(conn, f.device_id)) == 2


@pytest.mark.parametrize("live", [False, True])
def test_reassign_leaves_the_new_owner_an_empty_frame(env, live):
    state, conn, f = env
    if live:
        conn.execute("UPDATE devices SET state_path = ? WHERE id = ?",
                     (device_dirs.LIVE_STATE_PATH, f.device_id))
    _upload(conn, state, f.device_id, f.owner_id, 2)
    _upload(conn, state, f.device_id, f.co_manager_id, 1)
    new_owner = _new_owner(conn)
    fleet_ops.reassign_frame(conn, state, f.device_id, new_owner, ACTOR)
    assert not os.path.exists(os.path.join(state, "photos", f.device_id))
    assert fleet_db.list_photo_rows(conn, f.device_id) == []
    mgr = photo_store.authorize_manager(conn, f.device_id, new_owner)
    assert photo_store.list_photos(mgr, conn) == []
    with pytest.raises(photo_store.PhotoAccessDenied):
        photo_store.authorize_manager(conn, f.device_id, f.owner_id)
    rows = _purge_audit(conn)
    assert len(rows) == 1
    assert json.loads(rows[0]["detail"]) == {"count": 3, "cause": "reassign"}


@pytest.mark.parametrize("operation", ["retire", "reassign"])
def test_an_unlink_failure_does_not_undo_the_operation_and_sweep_cleans(
        env, monkeypatch, operation):
    state, conn, f = env
    ids = _upload(conn, state, f.device_id, f.owner_id, 2)

    def broken(*_a, **_k):
        raise OSError("disk")

    monkeypatch.setattr(photo_purge, "remove_files", broken)
    if operation == "retire":
        fleet_ops.retire_frame(conn, state, f.device_id, ACTOR)
    else:
        fleet_ops.reassign_frame(conn, state, f.device_id, _new_owner(conn), ACTOR)
    assert fleet_db.list_photo_rows(conn, f.device_id) == []
    # The in-call sweep already cleaned vanished-device or unrowed files only
    # after the grace period, so run one with a clock past it.
    photo_purge.sweep(conn, state, now=time.time() + 10_000_000)
    assert not any(os.path.exists(_file(state, f.device_id, p)) for p in ids)


def test_removing_or_disabling_a_co_manager_keeps_every_photo(env):
    state, conn, f = env
    ids = _upload(conn, state, f.device_id, f.owner_id, 1)
    ids += _upload(conn, state, f.device_id, f.co_manager_id, 2)
    fleet_db.remove_co_manager(conn, f.device_id, f.co_manager_id)
    fleet_db.set_user_disabled(conn, "comanager@example.test", True)
    assert len(fleet_db.list_photo_rows(conn, f.device_id)) == 3
    assert all(os.path.isfile(_file(state, f.device_id, p)) for p in ids)
    assert _purge_audit(conn) == []


# ---- account deletion over the real route -----------------------------


@pytest.fixture
def rig(tmp_path):
    state = str(tmp_path / "state")
    prefs.set_request_prefs(lang="en")
    server = InProcessAppServer(state)
    seed = fx.seed_fleet(state)
    conn = fleet_db.connect(state)
    co = fleet_db.add_user(conn, "co@example.test", "user")
    fleet_db.add_co_manager(conn, seed.owned_id, co, None)
    yield server, seed, co, state, conn
    conn.close()
    server.stop()


def _delete(server, user_id):
    cookie = fx.admin_cookie(server.state_dir)
    status, _h, _b = fx.post(server, cookie, "/users/%s/delete" % user_id, {})
    assert status == 303


def test_deleting_an_account_removes_only_its_own_photos(rig):
    server, seed, co, state, conn = rig
    mine = _upload(conn, state, seed.owned_id, co, 2)
    theirs = _upload(conn, state, seed.owned_id, seed.owner_id, 1)
    _delete(server, co)
    assert not any(os.path.exists(_file(state, seed.owned_id, p)) for p in mine)
    assert os.path.isfile(_file(state, seed.owned_id, theirs[0]))
    assert [r["id"] for r in fleet_db.list_photo_rows(conn, seed.owned_id)] == theirs
    rows = _purge_audit(conn)
    assert len(rows) == 1
    assert json.loads(rows[0]["detail"]) == {"count": 2, "cause": "user_deleted"}


def test_a_refused_delete_removes_nothing(rig):
    server, seed, _co, state, conn = rig
    ids = _upload(conn, state, seed.owned_id, seed.owner_id, 1)
    _delete(server, seed.owner_id)
    assert os.path.isfile(_file(state, seed.owned_id, ids[0]))
    assert len(fleet_db.list_photo_rows(conn, seed.owned_id)) == 1
    assert _purge_audit(conn) == []


@pytest.mark.parametrize("language,label", [("en", "Photos purged"), ("fr", "Photos supprimées")])
def test_the_audit_page_labels_the_purge_without_ids(rig, language, label):
    server, seed, co, state, conn = rig
    ids = _upload(conn, state, seed.owned_id, co, 2)
    _delete(server, co)
    prefs.set_request_prefs(lang=language)
    status, _h, body = fx.get(
        server, fx.admin_cookie(state), "/audit",
        headers={"Accept-Language": language})
    assert status == 200
    assert label in body
    assert not any(pid in body for pid in ids)
    assert "Other action" not in body and "Autre action" not in body
