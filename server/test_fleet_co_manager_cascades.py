#!/usr/bin/env python3
"""Co-manager clean-up on reassign, retire and delete, and the location rule."""
import json
import sqlite3

import pytest
import skypane_live_state as live

import server.fleet_db as fleet_db
from server import fleet_ops, hardware, pairing_code

SECRET = "ab" * 32
MAC = "aa:bb:cc:dd:ee:01"
CODE = "ABCD2345"
ACTOR = fleet_db.AuditActor(None, "admin-test", "127.0.0.1")
HW = hardware.LEGACY_KEY


@pytest.fixture
def root(tmp_path):
    return str(tmp_path)


@pytest.fixture
def conn(root):
    c = fleet_db.connect(root)
    yield c
    c.close()


@pytest.fixture
def owner(conn):
    return fleet_db.add_user(conn, "owner@example.test", "user")


@pytest.fixture
def cm1(conn):
    return fleet_db.add_user(conn, "cm1@example.test", "user")


@pytest.fixture
def cm2(conn):
    return fleet_db.add_user(conn, "cm2@example.test", "user")


def _claimed(conn, root, owner):
    pid = fleet_ops.register_frame(conn, MAC, SECRET, HW, ACTOR)
    salt = pairing_code.new_salt()
    fleet_db.issue_pending_code(conn, pid, salt, pairing_code.hash_code(salt, CODE), 1600)
    res = fleet_ops.claim_pairing_code(conn, root, CODE, owner, ACTOR, now=1000)
    return res.device_id


def _audit(conn, action):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM audit_log WHERE action = ? ORDER BY id", (action,)
    )]


def _members(conn, did):
    return sorted(int(r["user_id"]) for r in fleet_db.list_co_managers(conn, did))


def _detail(row):
    return json.loads(row["detail"])


# ---- retire ------------------------------------------------------------


def test_retire_clears_and_audits_each_co_manager(conn, root, owner, cm1, cm2):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    fleet_db.add_co_manager(conn, did, cm2, owner)
    pid = fleet_ops.retire_frame(conn, root, did, ACTOR)
    pending = fleet_db.get_pending(conn, pid)
    assert pending["previous_owner_user_id"] == owner
    assert conn.execute("SELECT COUNT(*) FROM device_co_managers").fetchone()[0] == 0
    removals = _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)
    assert sorted(_detail(r)["co_manager_user_id"] for r in removals) == sorted([cm1, cm2])
    assert all(
        r["outcome"] == "ok" and r["target_id"] == did and _detail(r)["via"] == "retire"
        and r["actor_label"] == "admin-test"
        for r in removals
    )
    retire = _audit(conn, fleet_ops.ACTION_RETIRE)
    assert len(retire) == 1 and retire[0]["outcome"] == "ok"


def test_retire_rolls_back_membership_when_audit_fails(conn, root, owner, cm1, cm2, monkeypatch):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    fleet_db.add_co_manager(conn, did, cm2, owner)
    real = fleet_db.audit_append

    def failing(c, actor, action, *a, **k):
        if action == fleet_ops.ACTION_RETIRE:
            raise sqlite3.OperationalError("disk")
        return real(c, actor, action, *a, **k)

    monkeypatch.setattr(fleet_db, "audit_append", failing)
    with pytest.raises(sqlite3.OperationalError):
        fleet_ops.retire_frame(conn, root, did, ACTOR)
    assert fleet_db.get_device(conn, did) is not None
    assert _members(conn, did) == sorted([cm1, cm2])
    assert not _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)


# ---- reassign ----------------------------------------------------------


def test_reassign_to_a_co_manager_removes_only_that_row(conn, root, owner, cm1, cm2):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    fleet_db.add_co_manager(conn, did, cm2, owner)
    fleet_ops.reassign_frame(conn, root, did, cm1, ACTOR)
    dev = fleet_db.get_device(conn, did)
    assert dev["owner_user_id"] == cm1
    assert _members(conn, did) == [cm2]
    assert not fleet_db.is_co_manager(conn, did, owner)
    removals = _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)
    assert len(removals) == 1
    assert _detail(removals[0]) == {"co_manager_user_id": cm1, "via": "reassign"}
    assert removals[0]["actor_label"] == "admin-test"


def test_reassign_to_a_non_co_manager_changes_no_membership(conn, root, owner, cm1, cm2):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    fleet_ops.reassign_frame(conn, root, did, cm2, ACTOR)
    assert _members(conn, did) == [cm1]
    assert not _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)


def test_reassign_rollback_restores_the_co_manager_row(conn, root, owner, cm1, monkeypatch):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)

    def boom(*_a, **_k):
        raise OSError("disk")

    monkeypatch.setattr(fleet_ops, "_reset_directory", boom)
    with pytest.raises(OSError):
        fleet_ops.reassign_frame(conn, root, did, cm1, ACTOR)
    assert _members(conn, did) == [cm1]
    assert fleet_db.get_device(conn, did)["owner_user_id"] == owner
    assert not _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)


def test_reassign_live_frame_to_a_co_manager_touches_no_files(conn, root, owner, cm1):
    ns = live.seed_live_like_state(root)
    did = fleet_db.add_device(conn, ns.mac, SECRET, HW, owner, token="live-tok")
    fleet_db.add_co_manager(conn, did, cm1, owner)
    snap = {k: v for k, v in live.snapshot_dir(root).items() if not k.startswith("fleet.db")}
    fleet_ops.reassign_frame(conn, root, did, cm1, ACTOR)
    after = {k: v for k, v in live.snapshot_dir(root).items() if not k.startswith("fleet.db")}
    assert after == snap
    assert fleet_db.get_device(conn, did)["owner_user_id"] == cm1
    assert _members(conn, did) == []


def test_assign_owner_to_a_co_manager_fails_closed(conn, root, owner, cm1):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    with pytest.raises(sqlite3.IntegrityError):
        fleet_db.assign_owner(conn, MAC, cm1)
    assert fleet_db.get_device(conn, did)["owner_user_id"] == owner
    assert _members(conn, did) == [cm1]
    assert not _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)


# ---- hard delete -------------------------------------------------------


def test_remove_device_clears_and_audits_co_managers(conn, root, owner, cm1, cm2):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    fleet_db.add_co_manager(conn, did, cm2, owner)
    assert fleet_db.remove_device(conn, MAC) is True
    assert fleet_db.get_device(conn, did) is None
    assert conn.execute("SELECT COUNT(*) FROM device_co_managers").fetchone()[0] == 0
    removals = _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)
    assert sorted(_detail(r)["co_manager_user_id"] for r in removals) == sorted([cm1, cm2])
    assert all(_detail(r)["via"] == "delete" and r["actor_label"] == "system" for r in removals)


def test_remove_device_uses_the_given_actor(conn, root, owner, cm1):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    assert fleet_db.remove_device(conn, MAC, actor=ACTOR) is True
    assert _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)[0]["actor_label"] == "admin-test"


def test_remove_device_without_co_managers_is_unchanged(conn, root, owner):
    did = _claimed(conn, root, owner)
    assert fleet_db.remove_device(conn, MAC) is True
    assert fleet_db.get_device(conn, did) is None
    assert fleet_db.remove_device(conn, MAC) is False
    assert not _audit(conn, fleet_ops.ACTION_CO_MANAGER_REMOVE)
# ---- location rule -----------------------------------------------------


@pytest.fixture
def located(conn, root, owner, cm1):
    did = _claimed(conn, root, owner)
    fleet_db.add_co_manager(conn, did, cm1, owner)
    own = fleet_db.add_location(conn, "Owner", 48.7, 2.4, "Europe/Paris", owner_user_id=owner)
    return did, own


def _loc(conn, name, owner_id):
    return fleet_db.add_location(conn, name, 48.0, 2.0, "Europe/Paris", owner_user_id=owner_id)


def test_owner_assigns_and_clears_own_location(conn, owner, located):
    did, own = located
    assert fleet_db.set_device_location_checked(conn, did, own, owner, False) is True
    assert fleet_db.get_device(conn, did)["location_id"] == own
    assert fleet_db.set_device_location_checked(conn, did, None, owner, False) is True
    assert fleet_db.get_device(conn, did)["location_id"] is None


def test_co_manager_assigns_the_owners_location_and_clears(conn, cm1, located):
    did, own = located
    assert fleet_db.set_device_location_checked(conn, did, own, cm1, False) is True
    assert fleet_db.get_device(conn, did)["location_id"] == own
    assert fleet_db.set_device_location_checked(conn, did, None, cm1, False) is True
    assert fleet_db.get_device(conn, did)["location_id"] is None


def test_co_manager_is_refused_other_locations(conn, cm1, cm2, located):
    did, _own = located
    mine = _loc(conn, "Mine", cm1)
    third = _loc(conn, "Third", cm2)
    for loc in (mine, third, 99999):
        with pytest.raises(PermissionError):
            fleet_db.set_device_location_checked(conn, did, loc, cm1, False)
    assert fleet_db.get_device(conn, did)["location_id"] is None


def test_unrelated_user_is_refused_everything(conn, cm2, located):
    did, own = located
    for loc in (own, None):
        with pytest.raises(PermissionError):
            fleet_db.set_device_location_checked(conn, did, loc, cm2, False)


def test_admin_rules_are_unchanged(conn, owner, cm2, located):
    did, own = located
    free = fleet_db.add_location(conn, "Free", 48.0, 2.0, "Europe/Paris")
    assert fleet_db.set_device_location_checked(conn, did, free, None, True) is True
    assert fleet_db.set_device_location_checked(conn, did, own, None, True) is True
    other = _loc(conn, "Other", cm2)
    with pytest.raises(PermissionError):
        fleet_db.set_device_location_checked(conn, did, other, None, True)
    with pytest.raises(ValueError):
        fleet_db.set_device_location_checked(conn, did, 99999, None, True)
    for actor, admin in ((owner, False), (None, True), (cm2, False)):
        assert fleet_db.set_device_location_checked(conn, "nope", None, actor, admin) is False


def test_owner_is_still_refused_an_ownerless_location(conn, owner, located):
    did, _own = located
    free = fleet_db.add_location(conn, "Free", 48.0, 2.0, "Europe/Paris")
    with pytest.raises(PermissionError):
        fleet_db.set_device_location_checked(conn, did, free, owner, False)
    assert fleet_db.get_device(conn, did)["location_id"] is None
