#!/usr/bin/env python3
"""Tests for the device_photos row helpers and the hooks that clear photo rows
when a frame is removed or retired or an account is deleted."""
import json
import sqlite3

import pytest

import server.fleet_db as fleet_db
from server import hardware

SECRET = "a" * 64
MAC = "aa:bb:cc:dd:ee:01"
MAC2 = "aa:bb:cc:dd:ee:02"


def pid(n):
    return "ph_%016x" % n


@pytest.fixture
def conn(tmp_path):
    c = fleet_db.connect(str(tmp_path))
    yield c
    c.close()


@pytest.fixture
def fleet(conn):
    owner = fleet_db.add_user(conn, "owner@example.com", "user")
    helper = fleet_db.add_user(conn, "helper@example.com", "user")
    other = fleet_db.add_user(conn, "other@example.com", "user")
    d1 = fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, owner, state_path="auto")
    d2 = fleet_db.add_device(conn, MAC2, SECRET, hardware.LEGACY_KEY, other, state_path="auto")
    return {"owner": owner, "helper": helper, "other": other, "d1": d1, "d2": d2}


def _count(conn, device_id=None):
    if device_id is None:
        return conn.execute("SELECT count(*) FROM device_photos").fetchone()[0]
    return conn.execute(
        "SELECT count(*) FROM device_photos WHERE device_id = ?", (device_id,)).fetchone()[0]


def _audit(conn):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM audit_log WHERE action = ?", (fleet_db.ACTION_PHOTO_PURGE,))]


# ---- helpers ---------------------------------------------------------


def test_insert_assigns_seq_per_device(conn, fleet):
    d1, d2, u = fleet["d1"], fleet["d2"], fleet["owner"]
    assert fleet_db.insert_photo(conn, pid(1), d1, 100, 10, 20, u, 1) == 1
    assert fleet_db.insert_photo(conn, pid(2), d1, 100, 10, 20, u, 2) == 2
    assert fleet_db.insert_photo(conn, pid(3), d2, 100, 10, 20, u, 3) == 1
    fleet_db.delete_photo_row(conn, d1, pid(2))
    assert fleet_db.insert_photo(conn, pid(4), d1, 100, 10, 20, u, 4) == 2
    assert not conn.in_transaction


def test_usage_and_listing(conn, fleet):
    d1, d2, u = fleet["d1"], fleet["d2"], fleet["owner"]
    assert fleet_db.photo_usage(conn, d1) == (0, 0)
    assert fleet_db.server_photo_bytes(conn) == 0
    fleet_db.insert_photo(conn, pid(1), d1, 300, 10, 20, u, 1)
    fleet_db.insert_photo(conn, pid(2), d1, 200, 10, 20, u, 2)
    fleet_db.insert_photo(conn, pid(3), d2, 500, 10, 20, u, 3)
    assert fleet_db.photo_usage(conn, d1) == (2, 500)
    assert fleet_db.photo_usage(conn, d2) == (1, 500)
    assert fleet_db.server_photo_bytes(conn) == 1000
    assert [r["id"] for r in fleet_db.list_photo_rows(conn, d1)] == [pid(1), pid(2)]
    assert sorted(fleet_db.all_photo_refs(conn)) == sorted(
        [(d1, pid(1)), (d1, pid(2)), (d2, pid(3))])


def test_get_and_delete_are_scoped_to_the_device(conn, fleet):
    d1, d2, u = fleet["d1"], fleet["d2"], fleet["owner"]
    fleet_db.insert_photo(conn, pid(1), d1, 300, 11, 22, u, 9)
    row = fleet_db.get_photo_row(conn, d1, pid(1))
    assert (row["size_bytes"], row["width"], row["height"], row["uploaded_by"],
            row["created_at"], row["seq"]) == (300, 11, 22, u, 9, 1)
    assert fleet_db.get_photo_row(conn, d2, pid(1)) is None
    assert fleet_db.delete_photo_row(conn, d2, pid(1)) is False
    assert fleet_db.delete_photo_row(conn, d1, pid(1)) is True
    assert fleet_db.delete_photo_row(conn, d1, pid(1)) is False


def test_is_user_active(conn, fleet):
    off = fleet_db.add_user(conn, "off@example.com", "user", disabled=True)
    assert fleet_db.is_user_active(conn, fleet["owner"])
    assert not fleet_db.is_user_active(conn, off)
    assert not fleet_db.is_user_active(conn, 9999)


# ---- hooks -----------------------------------------------------------


def test_remove_device_clears_photo_rows(conn, fleet):
    d1, d2, u = fleet["d1"], fleet["d2"], fleet["owner"]
    fleet_db.insert_photo(conn, pid(1), d1, 100, 1, 1, u, 1)
    fleet_db.insert_photo(conn, pid(2), d2, 100, 1, 1, u, 1)
    assert fleet_db.remove_device(conn, MAC) is True
    assert _count(conn, d1) == 0
    assert _count(conn, d2) == 1
    assert fleet_db.get_device_owner(conn, d1) is None


def test_park_retired_clears_photo_rows(conn, fleet):
    d1, u = fleet["d1"], fleet["owner"]
    fleet_db.insert_photo(conn, pid(1), d1, 100, 1, 1, u, 1)
    pending = fleet_db.park_retired(conn, d1, 5)
    assert pending is not None
    assert _count(conn, d1) == 0
    assert fleet_db.get_device_owner(conn, d1) is None


def test_delete_user_removes_their_uploads_on_any_frame_with_one_count_audit(conn, fleet):
    d1, d2 = fleet["d1"], fleet["d2"]
    owner, helper, other = fleet["owner"], fleet["helper"], fleet["other"]
    fleet_db.add_co_manager(conn, d1, helper, owner)
    fleet_db.add_co_manager(conn, d2, helper, other)
    fleet_db.insert_photo(conn, pid(1), d1, 100, 1, 1, helper, 1)
    fleet_db.insert_photo(conn, pid(2), d1, 100, 1, 1, helper, 2)
    fleet_db.insert_photo(conn, pid(3), d2, 100, 1, 1, helper, 3)
    fleet_db.insert_photo(conn, pid(4), d1, 100, 1, 1, owner, 4)
    assert fleet_db.delete_user_guarded(conn, owner, helper) is True
    assert [r["id"] for r in fleet_db.list_photo_rows(conn, d1)] == [pid(4)]
    assert _count(conn, d2) == 0
    rows = _audit(conn)
    assert len(rows) == 1
    detail = json.loads(rows[0]["detail"])
    assert detail == {"cause": "user_deleted", "count": 3}
    assert (rows[0]["target_type"], rows[0]["target_id"]) == ("user", str(helper))
    assert "ph_" not in rows[0]["detail"]


def test_delete_user_without_photos_writes_no_photo_audit(conn, fleet):
    assert fleet_db.delete_user_guarded(conn, fleet["owner"], fleet["helper"]) is True
    assert _audit(conn) == []


def test_owner_refusal_rolls_back_and_leaves_photos(conn, fleet):
    owner = fleet["owner"]
    fleet_db.insert_photo(conn, pid(1), fleet["d1"], 100, 1, 1, owner, 1)
    with pytest.raises(fleet_db.UserOwnsFrame):
        fleet_db.delete_user_guarded(conn, fleet["other"], owner)
    assert _count(conn) == 1
    assert _audit(conn) == []


def test_co_manager_removal_keeps_photos(conn, fleet):
    d1, owner, helper = fleet["d1"], fleet["owner"], fleet["helper"]
    fleet_db.add_co_manager(conn, d1, helper, owner)
    fleet_db.insert_photo(conn, pid(1), d1, 100, 1, 1, helper, 1)
    assert fleet_db.remove_co_manager(conn, d1, helper) is True
    assert _count(conn, d1) == 1
    fleet_db.add_co_manager(conn, d1, helper, owner)
    fleet_db.clear_co_managers(conn, d1)
    assert _count(conn, d1) == 1


def test_purge_helpers_return_refs_without_touching_other_rows(conn, fleet):
    d1, d2, u = fleet["d1"], fleet["d2"], fleet["owner"]
    fleet_db.insert_photo(conn, pid(1), d1, 100, 1, 1, u, 1)
    fleet_db.insert_photo(conn, pid(2), d2, 100, 1, 1, u, 1)
    assert sorted(fleet_db.photo_refs_uploaded_by(conn, u)) == sorted([(d1, pid(1)), (d2, pid(2))])
    assert fleet_db.delete_photo_rows(conn, d1) == [pid(1)]
    assert fleet_db.delete_photo_rows_uploaded_by(conn, u) == [(d2, pid(2))]
    assert _count(conn) == 0
    fleet_db.audit_photo_purge(
        conn, fleet_db.AuditActor(None, "system", None), "device", d1, 0, "x")
    assert _audit(conn) == []


def test_no_cascade_is_defined_on_the_photo_table(conn):
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'device_photos'").fetchone()[0]
    assert "CASCADE" not in sql.upper()
    fks = conn.execute("PRAGMA foreign_key_list(device_photos)").fetchall()
    assert [(r["table"], r["from"]) for r in fks] == [("devices", "device_id")]
    assert isinstance(conn, sqlite3.Connection)
