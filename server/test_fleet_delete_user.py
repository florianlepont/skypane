#!/usr/bin/env python3
"""Deleting a user record: the guards, the child rows, atomicity, and the
owner-checked retire used when an owner removes their own frame."""
import pytest

import server.fleet_db as fleet_db
from server import fleet_ops, hardware

SECRET = "ab" * 32
HW = hardware.LEGACY_KEY
ACTOR = fleet_db.AuditActor(None, "admin-test", "127.0.0.1")


@pytest.fixture
def conn(tmp_path):
    c = fleet_db.connect(str(tmp_path))
    yield c
    c.close()


def _user(conn, name, role="user"):
    return fleet_db.add_user(conn, "%s@example.test" % name, role)


def _count(conn, table, where="1", args=()):
    return conn.execute("SELECT COUNT(*) FROM %s WHERE %s" % (table, where), args).fetchone()[0]


def test_deleting_an_unknown_user_returns_false(conn):
    _user(conn, "admin", "admin")
    assert fleet_db.delete_user_guarded(conn, None, 999) is False


def test_a_user_who_owns_a_frame_is_refused_with_its_name_and_nothing_changes(conn):
    owner = _user(conn, "owner")
    fleet_db.add_device(conn, "aa:bb:cc:00:00:01", SECRET, HW, owner, name="Kitchen",
                        state_path="auto")
    with pytest.raises(fleet_db.UserOwnsFrame) as refused:
        fleet_db.delete_user_guarded(conn, None, owner)
    assert refused.value.frame_name == "Kitchen"
    assert _count(conn, "users", "id = ?", (owner,)) == 1


def test_the_actor_and_the_last_active_admin_are_refused(conn):
    admin = _user(conn, "admin", "admin")
    with pytest.raises(fleet_db.SelfActionError):
        fleet_db.delete_user_guarded(conn, admin, admin)
    with pytest.raises(fleet_db.LastAdminError):
        fleet_db.delete_user_guarded(conn, None, admin)
    other = _user(conn, "other", "admin")
    assert fleet_db.delete_user_guarded(conn, other, admin) is True


def test_a_delete_removes_children_in_one_transaction_and_keeps_audit_rows(conn):
    admin = _user(conn, "admin", "admin")
    owner = _user(conn, "owner")
    person = _user(conn, "person")
    device = fleet_db.add_device(conn, "aa:bb:cc:00:00:01", SECRET, HW, owner,
                                 state_path="auto")
    fleet_db.add_co_manager(conn, device, person, owner)
    location = fleet_db.add_location(conn, "Home", 48.7, 2.4, "Europe/Paris", person)
    conn.execute(
        "INSERT INTO sessions (id_hash, user_id, principal, created_at, last_seen_at, "
        "expires_at) VALUES ('h', ?, 'user', 1, 1, 9999999999)", (person,))
    fleet_db.audit_append(conn, fleet_db.AuditActor(person, "person", None),
                          "location.add", "location", "1", "ok")
    conn.commit()
    assert fleet_db.delete_user_guarded(conn, admin, person, ACTOR) is True
    conn.commit()
    assert _count(conn, "users", "id = ?", (person,)) == 0
    assert _count(conn, "sessions") == 0 and _count(conn, "device_co_managers") == 0
    assert conn.execute("SELECT owner_user_id FROM locations WHERE id = ?",
                        (location,)).fetchone()[0] is None
    assert _count(conn, "audit_log", "actor_user_id = ?", (person,)) == 1
    assert _count(conn, "audit_log", "action = 'device.co_manager_remove'") == 1


def test_retire_with_an_owner_check_refuses_a_frame_that_changed_hands(conn, tmp_path):
    owner = _user(conn, "owner")
    new_owner = _user(conn, "new")
    device = fleet_db.add_device(conn, "aa:bb:cc:00:00:01", SECRET, HW, owner,
                                 state_path="auto")
    conn.execute("UPDATE devices SET owner_user_id = ? WHERE id = ?", (new_owner, device))
    conn.commit()
    with pytest.raises(fleet_ops.NotFound):
        fleet_ops.retire_frame(conn, str(tmp_path), device, ACTOR, owner_user_id=owner)
    assert _count(conn, "devices", "id = ?", (device,)) == 1
    fleet_ops.retire_frame(conn, str(tmp_path), device, ACTOR, owner_user_id=new_owner)
    assert _count(conn, "devices", "id = ?", (device,)) == 0
