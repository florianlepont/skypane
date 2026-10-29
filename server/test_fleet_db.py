#!/usr/bin/env python3
"""Tests for server/fleet_db.py: schema constraints, atomic migrations,
file modes, read-only access and the change-only status file."""
import os
import sqlite3
import stat

import pytest

import server.fleet_db as fleet_db


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


def _tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {r[0] for r in rows}


def test_connect_creates_mode_0600_migrated_wal_db(state_dir):
    old = os.umask(0o022)
    try:
        conn = fleet_db.connect(state_dir)
    finally:
        os.umask(old)
    path = fleet_db.fleet_db_path(state_dir)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert {"users", "locations", "devices", "meta"} <= _tables(conn)
    conn.close()


def test_connect_is_idempotent(state_dir):
    fleet_db.connect(state_dir).close()
    conn = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    conn.close()


def test_failed_migration_step_is_atomic():
    def bad(conn):
        conn.execute("CREATE TABLE half (x INTEGER)")
        raise RuntimeError("boom")

    conn = sqlite3.connect(":memory:", isolation_level=None)
    with pytest.raises(RuntimeError):
        fleet_db.migrate_schema(conn, (bad,))
    assert fleet_db.schema_version(conn) == 0
    assert "half" not in _tables(conn)


def test_too_new_database_is_refused_and_untouched(state_dir):
    path = fleet_db.fleet_db_path(state_dir)
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = 99")
    raw.commit()
    raw.close()
    with open(path, "rb") as fh:
        before = fh.read()
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.connect(state_dir)
    with open(path, "rb") as fh:
        assert fh.read() == before


def test_readonly_absent_does_not_create(state_dir):
    with pytest.raises(fleet_db.FleetDbAbsent):
        fleet_db.connect_readonly(state_dir)
    assert not os.path.exists(fleet_db.fleet_db_path(state_dir))


def test_connect_without_create_raises_absent(state_dir):
    with pytest.raises(fleet_db.FleetDbAbsent):
        fleet_db.connect(state_dir, create=False)


def test_readonly_cannot_write(state_dir):
    fleet_db.connect(state_dir).close()
    ro = fleet_db.connect_readonly(state_dir)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO meta (key, value) VALUES ('a', 'b')")
    ro.close()


def test_readonly_refuses_too_new(state_dir):
    path = fleet_db.fleet_db_path(state_dir)
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = 99")
    raw.commit()
    raw.close()
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.connect_readonly(state_dir)


def test_connect_memory_is_migrated():
    conn = fleet_db.connect_memory()
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert "devices" in _tables(conn)


def test_transaction_commits_and_rolls_back():
    conn = fleet_db.connect_memory()
    with fleet_db.transaction(conn):
        fleet_db.meta_set(conn, "k", "v1")
    assert fleet_db.meta_get(conn, "k") == "v1"
    with pytest.raises(ValueError):
        with fleet_db.transaction(conn):
            fleet_db.meta_set(conn, "k", "v2")
            raise ValueError("stop")
    assert fleet_db.meta_get(conn, "k") == "v1"
    assert fleet_db.meta_get(conn, "missing") is None


def test_status_roundtrip_and_write_on_change_only(state_dir):
    assert fleet_db.read_status(state_dir) is None
    fleet_db.write_status(state_dir, fleet_db.STATUS_OK, "fine")
    doc = fleet_db.read_status(state_dir)
    assert doc is not None
    assert doc["state"] == "ok" and doc["detail"] == "fine" and doc["updated_at"]
    path = os.path.join(state_dir, fleet_db.FLEET_STATUS_FILENAME)
    before = os.stat(path).st_mtime_ns
    fleet_db.write_status(state_dir, fleet_db.STATUS_OK, "fine")
    assert os.stat(path).st_mtime_ns == before
    fleet_db.write_status(state_dir, fleet_db.STATUS_FAULT, "bad")
    changed = fleet_db.read_status(state_dir)
    assert changed is not None and changed["state"] == "fault"


def test_status_malformed_is_none(state_dir):
    path = os.path.join(state_dir, fleet_db.FLEET_STATUS_FILENAME)
    with open(path, "w") as fh:
        fh.write("[1, 2")
    assert fleet_db.read_status(state_dir) is None
    with open(path, "w") as fh:
        fh.write('{"state": 1}')
    assert fleet_db.read_status(state_dir) is None
