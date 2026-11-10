#!/usr/bin/env python3
"""Tests for fleet.db schema 5: the device_photos table and its constraints."""
import sqlite3

import pytest

import server.fleet_db as fleet_db
from server import hardware

SECRET = "a" * 64
MAC = "aa:bb:cc:dd:ee:01"
PHOTO = "ph_" + "0123456789abcdef"


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def conn(state_dir):
    c = fleet_db.connect(state_dir)
    yield c
    c.close()


@pytest.fixture
def frame(conn):
    owner = fleet_db.add_user(conn, "owner@example.com", "user")
    did = fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, owner, state_path="auto")
    return did, owner


def _objects(conn, kind):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type=?", (kind,))}


def _make_old(state_dir, upto):
    raw = sqlite3.connect(fleet_db.fleet_db_path(state_dir), isolation_level=None)
    fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:upto])
    return raw


def _inserts(conn):
    return [line for line in conn.iterdump() if line.startswith("INSERT")]


def _row(did, photo_id=PHOTO, size=1000, uploader=1):
    return (photo_id, did, size, 800, 600, uploader, 5, 1)


INSERT = (
    "INSERT INTO device_photos (id, device_id, size_bytes, width, height, "
    "uploaded_by, created_at, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)


def test_fresh_database_is_at_schema_5_with_an_empty_photo_table(conn):
    assert fleet_db.SCHEMA_VERSION == len(fleet_db.MIGRATIONS) >= 5
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert "device_photos" in _objects(conn, "table")
    assert "device_photos_device" in _objects(conn, "index")
    assert conn.execute("SELECT count(*) FROM device_photos").fetchone()[0] == 0


def test_v4_database_upgrades_without_touching_rows(state_dir):
    raw = _make_old(state_dir, 4)
    raw.execute("PRAGMA foreign_keys=ON")
    raw.execute("INSERT INTO users (email, role, created_at) VALUES ('a@x.fr', 'admin', 't')")
    raw.execute("INSERT INTO users (email, role, created_at) VALUES ('b@x.fr', 'user', 't')")
    raw.execute(
        "INSERT INTO devices (id, mac, secret_sha256, hardware_type, owner_user_id, "
        "created_at) VALUES ('d_00000001', ?, ?, 'x', 1, 't')",
        (MAC, SECRET),
    )
    raw.execute(
        "INSERT INTO device_co_managers (device_id, user_id, added_by, added_at) "
        "VALUES ('d_00000001', 2, 1, 7)"
    )
    before = _inserts(raw)
    assert len(before) >= 4
    raw.close()
    conn = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert _inserts(conn) == before
    assert conn.execute("SELECT count(*) FROM device_photos").fetchone()[0] == 0
    conn.close()


def test_id_shape_is_enforced_by_the_schema(conn, frame):
    did, owner = frame
    for bad in ("", "ph_0123", "ph_" + "0123456789ABCDEF", "xx_" + "0123456789abcdef",
                PHOTO + "0", "ph_" + "0123456789abcdeg"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, _row(did, bad, uploader=owner))
    conn.execute(INSERT, _row(did, uploader=owner))


def test_size_bounds_are_enforced_by_the_schema(conn, frame):
    did, owner = frame
    for bad in (0, -1, 1_000_001):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(INSERT, _row(did, size=bad, uploader=owner))
    conn.execute(INSERT, _row(did, size=1_000_000, uploader=owner))


def test_device_must_exist_but_uploader_need_not(conn, frame):
    did, _owner = frame
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(INSERT, _row("d_99999999"))
    conn.execute(INSERT, _row(did, uploader=424242))
    assert conn.execute("SELECT uploaded_by FROM device_photos").fetchone()[0] == 424242


def test_deleting_a_frame_row_directly_is_blocked_while_photos_exist(conn, frame):
    did, owner = frame
    conn.execute(INSERT, _row(did, uploader=owner))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM devices WHERE id = ?", (did,))


def test_a_build_with_four_migrations_refuses_a_v5_database(state_dir):
    fleet_db.connect(state_dir).close()
    raw = sqlite3.connect(fleet_db.fleet_db_path(state_dir), isolation_level=None)
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:4])
    raw.close()
