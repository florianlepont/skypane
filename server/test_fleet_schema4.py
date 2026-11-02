#!/usr/bin/env python3
"""Tests for fleet.db schema 4: the device_co_managers table, its triggers and
the co-manager API."""
import sqlite3
import threading

import pytest

import server.fleet_db as fleet_db
from server import hardware

SECRET = "a" * 64
MAC = "aa:bb:cc:dd:ee:01"
MAC2 = "aa:bb:cc:dd:ee:02"


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


def _dump(conn, tables):
    return [
        line for line in conn.iterdump()
        if any(f'"{t}"' in line for t in tables) and line.startswith("INSERT")
    ]


def test_fresh_database_is_at_schema_4_with_new_objects(conn):
    assert fleet_db.SCHEMA_VERSION == len(fleet_db.MIGRATIONS) == 4
    assert fleet_db.schema_version(conn) == 4
    assert "device_co_managers" in _objects(conn, "table")
    assert "device_co_managers_user" in _objects(conn, "index")
    assert {"device_co_managers_not_owner", "devices_owner_not_co_manager"} <= _objects(
        conn, "trigger")


@pytest.mark.parametrize("start", [1, 2, 3])
def test_older_databases_upgrade_without_touching_rows(state_dir, start):
    raw = _make_old(state_dir, start)
    raw.execute("PRAGMA foreign_keys=ON")
    raw.execute("INSERT INTO users (email, role, created_at) VALUES ('a@x.fr', 'admin', 't')")
    raw.execute(
        "INSERT INTO locations (name, latitude, longitude, timezone) "
        "VALUES ('Home', 48.0, 2.0, 'Europe/Paris')"
    )
    raw.execute(
        "INSERT INTO devices (id, mac, secret_sha256, hardware_type, owner_user_id, "
        "created_at) VALUES ('d_00000001', ?, ?, 'x', 1, 't')",
        (MAC, SECRET),
    )
    # Upgrading from schema 1 or 2 also runs the schema 3 column addition,
    # which legitimately widens locations rows; from 3 only v4 runs.
    tables = ("devices", "users", "locations") if start == 3 else ("devices", "users")
    before = _dump(raw, tables)
    assert len(before) == len(tables)
    raw.close()
    conn = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(conn) == 4
    assert _dump(conn, tables) == before
    assert conn.execute("SELECT count(*) FROM device_co_managers").fetchone()[0] == 0
    conn.close()


def test_migrating_again_is_a_noop_and_concurrent_upgraders_agree(state_dir):
    _make_old(state_dir, 3).close()
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
    assert versions == [4, 4, 4]
    c = fleet_db.connect(state_dir)
    before = fleet_db.dump_logical(c)
    fleet_db.migrate_schema(c)
    assert fleet_db.dump_logical(c) == before
    c.close()


def test_table_constraints_hold_in_the_database(conn, frame):
    did, owner = frame
    other = fleet_db.add_user(conn, "other@example.com", "user")
    ins = "INSERT INTO device_co_managers (device_id, user_id, added_at) VALUES (?, ?, 1)"
    conn.execute(ins, (did, other))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, (did, other))
    with pytest.raises(sqlite3.IntegrityError, match="owner"):
        conn.execute(ins, (did, owner))
    with pytest.raises(sqlite3.IntegrityError, match="co-manager"):
        conn.execute("UPDATE devices SET owner_user_id = ? WHERE id = ?", (other, did))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("d_99999999", other))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, (did, 999))


def test_add_co_manager_accepts_eligible_users(conn, frame):
    did, owner = frame
    admin = fleet_db.add_user(conn, "admin@example.com", "admin")
    never = fleet_db.add_user(conn, "never@example.com", "user")
    fleet_db.add_co_manager(conn, did, admin, owner, now=500)
    fleet_db.add_co_manager(conn, did, never, admin)
    row = conn.execute(
        "SELECT added_by, added_at FROM device_co_managers WHERE user_id = ?", (admin,)
    ).fetchone()
    assert (row["added_by"], row["added_at"]) == (owner, 500)
    assert conn.execute(
        "SELECT added_at FROM device_co_managers WHERE user_id = ?", (never,)
    ).fetchone()["added_at"] > 0
    assert not conn.in_transaction


def test_add_co_manager_refusals(conn, frame):
    did, owner = frame
    off = fleet_db.add_user(conn, "off@example.com", "user", disabled=True)
    ok = fleet_db.add_user(conn, "ok@example.com", "user")
    for bad in (off, 999, owner):
        with pytest.raises(fleet_db.IneligibleUser):
            fleet_db.add_co_manager(conn, did, bad, owner)
    fleet_db.add_co_manager(conn, did, ok, owner)
    with pytest.raises(fleet_db.AlreadyCoManager):
        fleet_db.add_co_manager(conn, did, ok, owner)
    with pytest.raises(fleet_db.UnknownDevice):
        fleet_db.add_co_manager(conn, "d_99999999", ok, owner)
    assert not conn.in_transaction


def test_eligibility_is_rechecked_inside_the_transaction(conn, frame):
    did, owner = frame
    user = fleet_db.add_user(conn, "late@example.com", "user")
    listed = [r["id"] for r in fleet_db.eligible_co_manager_candidates(conn, did)]
    assert user in listed
    fleet_db.set_user_disabled(conn, "late@example.com", True)
    with pytest.raises(fleet_db.IneligibleUser):
        fleet_db.add_co_manager(conn, did, user, owner)
    assert fleet_db.list_co_managers(conn, did) == []


def test_candidates_and_find_eligible(conn, frame):
    did, owner = frame
    member = fleet_db.add_user(conn, "member@example.com", "user")
    fleet_db.add_user(conn, "off@example.com", "user", disabled=True)
    fleet_db.add_user(conn, "Zed@example.com", "user")
    fleet_db.add_user(conn, "adm@example.com", "admin")
    fleet_db.add_co_manager(conn, did, member, owner)
    rows = fleet_db.eligible_co_manager_candidates(conn, did)
    assert [r["email"] for r in rows] == ["adm@example.com", "zed@example.com"]
    assert fleet_db.find_eligible_co_manager(conn, did, "  ZED@Example.com ") == rows[1]["id"]
    for bad in ("nobody@example.com", "off@example.com", "owner@example.com",
                "member@example.com", "not-an-email", ""):
        assert fleet_db.find_eligible_co_manager(conn, did, bad) is None
    assert fleet_db.find_eligible_co_manager(conn, "d_99999999", "zed@example.com") is None


def test_list_remove_and_clear(conn, frame):
    did, owner = frame
    did2 = fleet_db.add_device(conn, MAC2, SECRET, hardware.LEGACY_KEY, owner, state_path="auto")
    b = fleet_db.add_user(conn, "B@example.com", "user")
    a = fleet_db.add_user(conn, "a@example.com", "user")
    for d in (did, did2):
        fleet_db.add_co_manager(conn, d, b, owner)
    fleet_db.add_co_manager(conn, did, a, owner)
    fleet_db.set_user_disabled(conn, "a@example.com", True)
    rows = fleet_db.list_co_managers(conn, did)
    assert [(r["email"], r["disabled"]) for r in rows] == [
        ("a@example.com", 1), ("b@example.com", 0)]
    assert {"user_id", "added_at"} <= set(rows[0].keys())
    assert fleet_db.co_managed_device_ids(conn, b) == {did, did2}
    assert fleet_db.co_managed_device_ids(conn, a) == {did}
    assert fleet_db.remove_co_manager(conn, did, a) is True
    assert fleet_db.remove_co_manager(conn, did, a) is False
    assert fleet_db.clear_co_managers(conn, did) == [b]
    assert fleet_db.clear_co_managers(conn, did) == []
    assert fleet_db.co_managed_device_ids(conn, b) == {did2}
    assert fleet_db.is_co_manager(conn, did2, b)
    assert not fleet_db.is_co_manager(conn, did, b)


def test_helpers_never_change_the_owner_row(conn, frame):
    did, owner = frame
    user = fleet_db.add_user(conn, "u@example.com", "user")
    before = _dump(conn, ("devices",))
    fleet_db.add_co_manager(conn, did, user, owner)
    assert _dump(conn, ("devices",)) == before
    fleet_db.remove_co_manager(conn, did, user)
    fleet_db.add_co_manager(conn, did, user, owner)
    fleet_db.clear_co_managers(conn, did)
    assert _dump(conn, ("devices",)) == before
    assert fleet_db.get_device_owner(conn, did) == owner
