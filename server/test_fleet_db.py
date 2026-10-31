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


# ---- users, locations, devices ----------------------------------------

import inspect
import threading

import server.hardware as hardware

SECRET = "a" * 64
MAC = "aa:bb:cc:dd:ee:01"
MAC2 = "aa:bb:cc:dd:ee:02"
SIM_ON = {hardware.SIM_ENV_VAR: "1"}


@pytest.fixture
def conn():
    c = fleet_db.connect_memory()
    yield c
    c.close()


def _dev(conn, owner, mac=MAC, **kw):
    return fleet_db.add_device(conn, mac, SECRET, hardware.LEGACY_KEY, owner, **kw)


def test_add_user_normalises_and_rejects_duplicates(conn):
    uid = fleet_db.add_user(conn, "  Flo@Example.COM ", "admin")
    assert fleet_db.get_user_by_email(conn, "flo@example.com")["id"] == uid
    with pytest.raises(sqlite3.IntegrityError):
        fleet_db.add_user(conn, "FLO@example.com", "user")


@pytest.mark.parametrize("bad", ["", "nope", "a@b@c", "a b@c.d", "@x.y", "x@"])
def test_bad_emails_rejected(conn, bad):
    with pytest.raises(ValueError):
        fleet_db.add_user(conn, bad, "user")


def test_bad_role_rejected(conn):
    with pytest.raises(ValueError):
        fleet_db.add_user(conn, "a@b.c", "root")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (email, role, created_at) VALUES ('x@y.z', 'root', 't')"
        )


def test_null_iss_sub_coexist_and_pair_is_unique(conn):
    fleet_db.add_user(conn, "a@b.c", "user")
    fleet_db.add_user(conn, "d@e.f", "user")
    fleet_db.add_user(conn, "g@h.i", "user", iss="https://idp", sub="1")
    with pytest.raises(sqlite3.IntegrityError):
        fleet_db.add_user(conn, "j@k.l", "user", iss="https://idp", sub="1")


def test_get_user_role_and_signature(conn):
    uid = fleet_db.add_user(conn, "a@b.c", "admin")
    assert fleet_db.get_user_role(conn, uid) == "admin"
    assert fleet_db.get_user_role(conn, uid + 100) is None
    params = list(inspect.signature(fleet_db.get_user_role).parameters)
    assert params == ["conn", "user_id"]


def test_device_requires_existing_owner(conn):
    with pytest.raises(sqlite3.IntegrityError):
        _dev(conn, None)
    with pytest.raises(sqlite3.IntegrityError):
        _dev(conn, 4242)


def test_single_owner_column_and_reassignment(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    b = fleet_db.add_user(conn, "d@e.f", "user")
    _dev(conn, a)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(devices)")]
    assert [c for c in cols if "owner" in c] == ["owner_user_id"]
    assert fleet_db.assign_owner(conn, MAC, b) is True
    assert fleet_db.get_device_by_mac(conn, MAC)["owner_user_id"] == b
    with pytest.raises(sqlite3.IntegrityError):
        fleet_db.assign_owner(conn, MAC, 4242)
    assert fleet_db.assign_owner(conn, "aa:bb:cc:dd:ee:99", a) is False


def test_disabling_owner_keeps_device(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    _dev(conn, a)
    assert fleet_db.set_user_disabled(conn, "A@b.c", True) is True
    assert fleet_db.get_user_by_email(conn, "a@b.c")["disabled"] == 1
    assert fleet_db.get_device_by_mac(conn, MAC)["owner_user_id"] == a
    assert fleet_db.set_user_disabled(conn, "no@one.x", True) is False


def test_device_id_is_opaque_and_not_the_mac(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    device_id = _dev(conn, a)
    assert device_id.startswith("d_") and len(device_id) == 10
    assert "aabbccddee" not in device_id


@pytest.mark.parametrize("mac", ["AA:BB:CC:DD:EE:01", "aa-bb-cc-dd-ee-01", "aa:bb:cc", ""])
def test_bad_mac_rejected(conn, mac):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    with pytest.raises(ValueError):
        _dev(conn, a, mac=mac)


@pytest.mark.parametrize("secret", ["A" * 64, "a" * 63, "g" * 64, ""])
def test_bad_secret_rejected(conn, secret):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    with pytest.raises(ValueError):
        fleet_db.add_device(conn, MAC, secret, hardware.LEGACY_KEY, a)


def test_location_validation_and_link(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    with pytest.raises(ValueError):
        fleet_db.add_location(conn, "x", 91.0, 2.0, "Europe/Paris")
    with pytest.raises(ValueError):
        fleet_db.add_location(conn, "x", 48.0, 181.0, "Europe/Paris")
    with pytest.raises(ValueError):
        fleet_db.add_location(conn, "x", 48.0, 2.0, "Mars/Olympus")
    loc = fleet_db.add_location(conn, "Orly", 48.72, 2.38, "Europe/Paris")
    assert [r["name"] for r in fleet_db.list_locations(conn)] == ["Orly"]
    _dev(conn, a, location_id=loc)
    assert fleet_db.list_devices(conn)[0]["location_name"] == "Orly"
    assert fleet_db.set_device_location(conn, MAC, None) is True
    assert fleet_db.list_devices(conn)[0]["location_name"] is None


def test_sim_hardware_needs_gate_to_add(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    with pytest.raises(hardware.UnknownHardwareType):
        fleet_db.add_device(conn, MAC, SECRET, "sim-ee02-clone", a, environ={})
    with pytest.raises(hardware.UnknownHardwareType):
        fleet_db.add_device(conn, MAC, SECRET, "no-such-type", a)
    device_id = fleet_db.add_device(
        conn, MAC, SECRET, "sim-ee02-clone", a, environ=SIM_ON
    )
    assert device_id.startswith("d_")


def test_gated_rows_remain_readable_with_gate_off(conn, monkeypatch):
    monkeypatch.delenv(hardware.SIM_ENV_VAR, raising=False)
    a = fleet_db.add_user(conn, "a@b.c", "user")
    conn.execute(
        "INSERT INTO devices (id, mac, secret_sha256, token, hardware_type, "
        "owner_user_id, created_at) VALUES ('d_00000001', ?, ?, 'tok', "
        "'sim-ee02-clone', ?, 't')",
        (MAC, SECRET, a),
    )
    assert fleet_db.get_device_by_mac(conn, MAC)["hardware_type"] == "sim-ee02-clone"
    assert fleet_db.tokens_by_mac(conn) == {MAC: "tok"}
    assert fleet_db.registry_view(conn) == {"devices": {MAC: {"secret_sha256": SECRET}}}


def test_tokens_registry_and_removal(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    _dev(conn, a, token="t1")
    _dev(conn, a, mac=MAC2, state_path="auto")
    assert fleet_db.tokens_by_mac(conn) == {MAC: "t1"}
    assert set(fleet_db.registry_view(conn)["devices"]) == {MAC, MAC2}
    assert fleet_db.set_device_token(conn, MAC, None) is True
    assert fleet_db.tokens_by_mac(conn) == {}
    assert fleet_db.set_device_secret(conn, MAC, "b" * 64) is True
    assert fleet_db.registry_view(conn)["devices"][MAC]["secret_sha256"] == "b" * 64
    assert fleet_db.remove_device(conn, MAC) is True
    assert fleet_db.remove_device(conn, MAC) is False
    assert any("devices" in line for line in fleet_db.dump_logical(conn))


def test_list_devices_hides_token_and_full_hash(conn):
    a = fleet_db.add_user(conn, "a@b.c", "user")
    _dev(conn, a, token="secret-token")
    row = fleet_db.list_devices(conn)[0]
    assert "token" not in row.keys()
    assert "secret_sha256" not in row.keys()
    assert row["secret_prefix"] == SECRET[:12]
    assert row["owner_email"] == "a@b.c"


def test_concurrent_readers_and_writer(state_dir):
    setup = fleet_db.connect(state_dir)
    owner = fleet_db.add_user(setup, "a@b.c", "user")
    _dev(setup, owner, token="t0")
    errors = []
    stop = threading.Event()

    def reader():
        c = fleet_db.connect(state_dir)
        try:
            while not stop.is_set():
                fleet_db.tokens_by_mac(c)
        except Exception as exc:  # noqa: BLE001 - collected for the assertion
            errors.append(exc)
        finally:
            c.close()

    threads = [threading.Thread(target=reader) for _ in range(8)]
    for t in threads:
        t.start()
    try:
        for i in range(50):
            with fleet_db.transaction(setup):
                fleet_db.set_device_token(setup, MAC, f"t{i}")
    finally:
        stop.set()
        for t in threads:
            t.join()
    setup.close()
    assert errors == []


def test_add_device_auto_state_path_uses_generated_id(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    device_id = _dev(conn, owner, state_path="auto")
    row = conn.execute("SELECT state_path FROM devices WHERE id = ?", (device_id,)).fetchone()
    assert row["state_path"] == "devices/" + device_id


def test_add_device_default_state_path_is_live(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    device_id = _dev(conn, owner)
    row = conn.execute("SELECT state_path FROM devices WHERE id = ?", (device_id,)).fetchone()
    assert row["state_path"] == "."


def test_add_device_rejects_a_second_live_state_path(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    _dev(conn, owner)
    with pytest.raises(ValueError, match="already uses the live state path"):
        _dev(conn, owner, mac="aa:bb:cc:dd:ee:02")
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == 1


def test_add_device_auto_rows_never_conflict_with_the_live_row(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    _dev(conn, owner)
    first = _dev(conn, owner, mac="aa:bb:cc:dd:ee:02", state_path="auto")
    second = _dev(conn, owner, mac="aa:bb:cc:dd:ee:03", state_path="auto")
    assert first != second
    assert conn.execute(
        "SELECT count(*) FROM devices WHERE state_path = '.'").fetchone()[0] == 1


def test_add_device_legacy_import_may_share_the_live_path(conn):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    _dev(conn, owner)
    _dev(conn, owner, mac="aa:bb:cc:dd:ee:02", allow_shared_live=True)
    assert conn.execute(
        "SELECT count(*) FROM devices WHERE state_path = '.'").fetchone()[0] == 2


@pytest.mark.parametrize("bad", ["../x", "devices/d_deadbeef", "/abs", "", "devices"])
def test_add_device_rejects_unsafe_state_path_and_inserts_nothing(conn, bad):
    owner = fleet_db.add_user(conn, "o@example.com", "admin")
    before = conn.execute("SELECT count(*) FROM devices").fetchone()[0]
    with pytest.raises(ValueError):
        _dev(conn, owner, state_path=bad)
    assert conn.execute("SELECT count(*) FROM devices").fetchone()[0] == before


def _make_v1(state_dir):
    path = fleet_db.fleet_db_path(state_dir)
    conn = sqlite3.connect(path, isolation_level=None)
    fleet_db.migrate_schema(conn, fleet_db.MIGRATIONS[:1])
    assert fleet_db.schema_version(conn) == 1
    conn.close()


def test_v1_database_upgrades_in_place_to_current(state_dir):
    _make_v1(state_dir)
    conn = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"sessions_user", "sessions_expires"} <= names
    conn.close()
    again = fleet_db.connect(state_dir)
    assert fleet_db.schema_version(again) == fleet_db.SCHEMA_VERSION
    again.close()


def test_concurrent_upgrades_both_end_at_current(state_dir):
    import threading

    _make_v1(state_dir)
    path = fleet_db.fleet_db_path(state_dir)
    barrier = threading.Barrier(2)
    errors = []
    versions = []

    def run():
        conn = sqlite3.connect(path, isolation_level=None, timeout=10)
        try:
            barrier.wait()
            fleet_db.migrate_schema(conn)
            versions.append(fleet_db.schema_version(conn))
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert versions == [fleet_db.SCHEMA_VERSION] * 2


def test_readonly_opens_current_and_still_refuses_newer(state_dir):
    fleet_db.connect(state_dir).close()
    fleet_db.connect_readonly(state_dir).close()
    raw = sqlite3.connect(fleet_db.fleet_db_path(state_dir))
    raw.execute("PRAGMA user_version = %d" % (fleet_db.SCHEMA_VERSION + 1))
    raw.commit()
    raw.close()
    with pytest.raises(fleet_db.FleetDbTooNew):
        fleet_db.connect_readonly(state_dir)


def test_sessions_principal_user_id_check():
    conn = fleet_db.connect_memory()
    uid = fleet_db.add_user(conn, "a@example.com", "admin")
    insert = "INSERT INTO sessions VALUES (?, ?, ?, 1, 1, 2)"
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("h1", None, "user"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, ("h2", uid, "legacy-admin"))
    conn.execute(insert, ("h3", uid, "user"))
    conn.execute(insert, ("h4", None, "legacy-admin"))


def test_get_device_owner():
    conn = fleet_db.connect_memory()
    uid = fleet_db.add_user(conn, "a@example.com", "admin")
    device_id = fleet_db.add_device(
        conn, "aa:bb:cc:dd:ee:ff", "0" * 64, hardware.LEGACY_KEY, uid
    )
    owner = fleet_db.get_device_owner(conn, device_id)
    assert owner == uid and isinstance(owner, int)
    assert fleet_db.get_device_owner(conn, "d_unknown0") is None
    assert fleet_db.get_device_owner(conn, "'; --") is None
