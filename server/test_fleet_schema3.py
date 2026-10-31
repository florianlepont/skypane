#!/usr/bin/env python3
"""Tests for fleet.db schema 3: pending_devices, audit_log, location owners,
and the pending / location / user-guard API built on them."""
import sqlite3
import threading

import pytest

import server.fleet_db as fleet_db
from server import hardware

SECRET = "a" * 64
MAC = "aa:bb:cc:dd:ee:01"
MAC2 = "aa:bb:cc:dd:ee:02"
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")


@pytest.fixture
def state_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def conn(state_dir):
    c = fleet_db.connect(state_dir)
    yield c
    c.close()


def _objects(conn, kind):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type=?", (kind,))}


def _make_old(state_dir, upto):
    conn = sqlite3.connect(fleet_db.fleet_db_path(state_dir), isolation_level=None)
    fleet_db.migrate_schema(conn, fleet_db.MIGRATIONS[:upto])
    return conn


def test_fresh_database_is_at_schema_3_with_new_objects(conn):
    assert fleet_db.SCHEMA_VERSION == 3
    assert fleet_db.schema_version(conn) == 3
    assert {"pending_devices", "audit_log"} <= _objects(conn, "table")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(locations)")}
    assert "owner_user_id" in cols


@pytest.mark.parametrize("start", [1, 2])
def test_old_databases_upgrade_in_place_keeping_rows(state_dir, start):
    raw = _make_old(state_dir, start)
    raw.execute("PRAGMA foreign_keys=ON")
    raw.execute(
        "INSERT INTO users (email, role, created_at) VALUES ('a@x.fr', 'admin', 't')"
    )
    raw.execute(
        "INSERT INTO locations (name, latitude, longitude, timezone) "
        "VALUES ('Home', 48.0, 2.0, 'Europe/Paris')"
    )
    raw.execute(
        "INSERT INTO devices (id, mac, secret_sha256, hardware_type, owner_user_id, "
        "created_at) VALUES ('d_00000001', ?, ?, 'x', 1, 't')",
        (MAC, SECRET),
    )
    raw.close()
    conn = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 1
    loc = conn.execute("SELECT * FROM locations").fetchone()
    assert loc["name"] == "Home" and loc["owner_user_id"] is None
    before = fleet_db.dump_logical(conn)
    fleet_db.migrate_schema(conn)
    assert fleet_db.dump_logical(conn) == before
    conn.close()


def test_concurrent_upgraders_end_at_schema_3(state_dir):
    _make_old(state_dir, 2).close()
    path = fleet_db.fleet_db_path(state_dir)
    barrier = threading.Barrier(3)
    versions: list[int] = []
    errors: list[BaseException] = []

    def run():
        c = sqlite3.connect(path, isolation_level=None, timeout=10)
        try:
            barrier.wait()
            fleet_db.migrate_schema(c)
            versions.append(fleet_db.schema_version(c))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            c.close()

    threads = [threading.Thread(target=run) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert versions == [3, 3, 3]


def test_audit_log_is_append_only(conn):
    row_id = fleet_db.audit_append(conn, ACTOR, "frame.add", "device", "d_1", "ok", now=5)
    assert row_id == 1
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError), match="append-only"):
        conn.execute("UPDATE audit_log SET outcome = 'failed'")
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError), match="append-only"):
        conn.execute("DELETE FROM audit_log")
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 1


def test_audit_outcome_check_and_detail_bound(conn):
    with pytest.raises(ValueError):
        fleet_db.audit_append(conn, ACTOR, "frame.add", "device", None, "weird")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO audit_log (ts, actor_label, action, target_type, outcome) "
            "VALUES (1, 'x', 'a', 't', 'weird')"
        )
    fleet_db.audit_append(
        conn, ACTOR, "frame.add", "device", None, "ok", detail={"k": "v" * 5000}
    )
    detail = conn.execute("SELECT detail FROM audit_log").fetchone()[0]
    assert len(detail) == 1000


def test_audit_categories_and_ordering(conn):
    for i, (action, outcome) in enumerate([
        ("pairing.code_issued", "ok"),
        ("frame.rename", "ok"),
        ("device.remove", "ok"),
        ("user.disable", "ok"),
        ("location.add", "ok"),
        ("release.start", "ok"),
        ("pairing.code_failed", "denied"),
    ]):
        fleet_db.audit_append(conn, ACTOR, action, "t", None, outcome, now=100 + i)
    assert fleet_db.count_audit(conn, "all") == 7
    assert fleet_db.count_audit(conn, "pairing") == 2
    assert fleet_db.count_audit(conn, "frames") == 2
    assert fleet_db.count_audit(conn, "users") == 1
    assert fleet_db.count_audit(conn, "locations") == 1
    assert fleet_db.count_audit(conn, "releases") == 1
    assert fleet_db.count_audit(conn, "failed") == 1
    rows = fleet_db.list_audit(conn, "all", 3, 0)
    assert [r["action"] for r in rows][0] == "pairing.code_failed"
    assert len(rows) == 3
    assert len(fleet_db.list_audit(conn, "all", 10, 5)) == 2
    with pytest.raises(ValueError):
        fleet_db.list_audit(conn, "nope", 1, 0)


def test_pending_table_constraints(conn):
    ins = (
        "INSERT INTO pending_devices (id, mac, secret_sha256, hardware_type, "
        "status, created_at) VALUES (?, ?, ?, 'x', ?, 't')"
    )
    conn.execute(ins, ("p_0a1b2c3d", MAC, SECRET, "pending"))
    for bad_id in ("p_0A1B2C3D", "p_0a1b2c3", "d_0a1b2c3d", "p_0a1b2c3dd"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(ins, (bad_id, MAC2, SECRET, "pending"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("p_11111111", MAC, SECRET, "pending"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("p_22222222", MAC2, SECRET, "bogus"))


def test_schema_4_is_refused(state_dir):
    fleet_db.connect(state_dir).close()
    raw = sqlite3.connect(fleet_db.fleet_db_path(state_dir))
    raw.execute("PRAGMA user_version = 4")
    raw.commit()
    raw.close()
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.connect(state_dir)
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.connect_readonly(state_dir)


def test_existing_views_unchanged_and_list_devices_carries_owner(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, owner, token="tok")
    assert fleet_db.registry_view(conn) == {"devices": {MAC: {"secret_sha256": SECRET}}}
    assert fleet_db.tokens_by_mac(conn) == {MAC: "tok"}
    rows = fleet_db.list_devices(conn)
    assert rows[0]["owner_user_id"] == owner
    assert "token" not in rows[0].keys()


def test_add_device_refuses_a_pending_mac(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    conn.execute(
        "INSERT INTO pending_devices (id, mac, secret_sha256, hardware_type, created_at) "
        "VALUES ('p_0a1b2c3d', ?, ?, 'x', 't')",
        (MAC, SECRET),
    )
    with pytest.raises(ValueError):
        fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, owner)
