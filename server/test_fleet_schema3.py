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


# ---- pending devices -------------------------------------------------


def _admin(conn, email="a@example.com"):
    return fleet_db.add_user(conn, email, "admin")


def test_register_pending_inserts_and_rejects_duplicates(conn):
    owner = _admin(conn)
    pid = fleet_db.register_pending(conn, MAC, SECRET, hardware.LEGACY_KEY, owner)
    assert fleet_db.PENDING_ID_RE.match(pid)
    row = fleet_db.get_pending(conn, pid)
    assert row["status"] == fleet_db.PENDING_STATUS_PENDING and row["mac"] == MAC
    assert "secret_sha256" not in row.keys() and "token" not in row.keys()
    with pytest.raises(ValueError):
        fleet_db.register_pending(conn, MAC, SECRET, hardware.LEGACY_KEY, owner)
    fleet_db.add_device(conn, MAC2, SECRET, hardware.LEGACY_KEY, owner)
    with pytest.raises(ValueError):
        fleet_db.register_pending(conn, MAC2, SECRET, hardware.LEGACY_KEY, owner)
    for bad in ("A" * 64, "a" * 63, "plain-secret"):
        with pytest.raises(ValueError):
            fleet_db.register_pending(
                conn, "aa:bb:cc:dd:ee:03", bad, hardware.LEGACY_KEY, owner
            )
    assert fleet_db.get_pending_by_mac(conn, MAC)["id"] == pid


def test_pending_views_mirror_registry_shapes_and_leave_registry_alone(conn):
    owner = _admin(conn)
    fleet_db.add_device(conn, MAC2, SECRET, hardware.LEGACY_KEY, owner, token="dev")
    pid = fleet_db.register_pending(conn, MAC, "b" * 64, hardware.LEGACY_KEY, owner)
    assert fleet_db.set_pending_token(conn, MAC, "pt")
    assert fleet_db.pending_registry_view(conn) == {
        "devices": {MAC: {"secret_sha256": "b" * 64}}
    }
    assert fleet_db.pending_tokens_by_mac(conn) == {MAC: "pt"}
    assert fleet_db.registry_view(conn) == {"devices": {MAC2: {"secret_sha256": SECRET}}}
    assert fleet_db.tokens_by_mac(conn) == {MAC2: "dev"}
    assert [r["id"] for r in fleet_db.list_pending(conn)] == [pid]


def test_pending_code_touch_and_delete(conn):
    owner = _admin(conn)
    pid = fleet_db.register_pending(conn, MAC, SECRET, hardware.LEGACY_KEY, owner)
    assert fleet_db.issue_pending_code(conn, pid, "salt", "hash", 999)
    row = fleet_db.get_pending(conn, pid)
    assert (row["code_salt"], row["code_hash"], row["code_expires_at"]) == ("salt", "hash", 999)
    assert fleet_db.list_pending(conn)[0]["has_code"] == 1
    assert "code_hash" not in fleet_db.list_pending(conn)[0].keys()
    assert fleet_db.touch_pending(conn, pid, 50, 3900, "1.2.3")
    row = fleet_db.get_pending(conn, pid)
    assert (row["last_seen_at"], row["battery_mv"], row["fw_version"]) == (50, 3900, "1.2.3")
    assert fleet_db.clear_pending_code(conn, pid)
    assert fleet_db.get_pending(conn, pid)["code_hash"] is None
    assert fleet_db.delete_pending(conn, pid)
    assert not fleet_db.delete_pending(conn, pid)


def test_park_retired_moves_a_device_and_reactivate_resets_it(conn):
    owner = _admin(conn)
    did = fleet_db.add_device(
        conn, MAC, SECRET, hardware.LEGACY_KEY, owner, name="Hall",
        token="tok", state_path="auto",
    )
    state_path = fleet_db.get_device(conn, did)["state_path"]
    with fleet_db.transaction(conn):
        pid = fleet_db.park_retired(conn, did, 777)
    assert pid is not None
    assert fleet_db.get_device(conn, did) is None
    row = fleet_db.get_pending(conn, pid)
    assert row["status"] == fleet_db.PENDING_STATUS_RETIRED
    assert (row["previous_owner_user_id"], row["previous_device_id"]) == (owner, did)
    assert (row["previous_state_path"], row["previous_name"], row["retired_at"]) == (
        state_path, "Hall", 777)
    assert fleet_db.pending_registry_view(conn)["devices"][MAC]["secret_sha256"] == SECRET
    assert fleet_db.pending_tokens_by_mac(conn) == {MAC: "tok"}
    assert fleet_db.park_retired(conn, did, 1) is None
    fleet_db.issue_pending_code(conn, pid, "s", "h", 5)
    assert fleet_db.reactivate_pending(conn, pid)
    row = fleet_db.get_pending(conn, pid)
    assert row["status"] == fleet_db.PENDING_STATUS_PENDING and row["code_hash"] is None


def test_get_device_has_no_secret_columns(conn):
    owner = _admin(conn)
    did = fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, owner, token="t")
    keys = set(fleet_db.get_device(conn, did).keys())
    assert {"mac", "state_path", "owner_user_id", "hardware_type", "name",
            "location_id"} <= keys
    assert not keys & {"secret_sha256", "token"}


# ---- user guards -----------------------------------------------------


def test_last_admin_and_self_actions_are_refused(conn):
    a = _admin(conn)
    u = fleet_db.add_user(conn, "u@example.com", "user")
    with pytest.raises(fleet_db.LastAdminError):
        fleet_db.set_user_role_guarded(conn, u, a, "user")
    with pytest.raises(fleet_db.LastAdminError):
        fleet_db.set_user_disabled_guarded(conn, u, a, True)
    with pytest.raises(fleet_db.SelfActionError):
        fleet_db.set_user_role_guarded(conn, a, a, "user")
    with pytest.raises(fleet_db.SelfActionError):
        fleet_db.set_user_disabled_guarded(conn, u, u, True)
    assert fleet_db.count_active_admins(conn) == 1
    b = fleet_db.add_user(conn, "b@example.com", "admin")
    assert fleet_db.set_user_role_guarded(conn, a, b, "user")
    with pytest.raises(fleet_db.LastAdminError):
        fleet_db.set_user_role_guarded(conn, None, a, "user")
    assert not fleet_db.set_user_role_guarded(conn, a, 999, "user")
    with pytest.raises(ValueError):
        fleet_db.set_user_role_guarded(conn, a, u, "root")


def test_disable_deletes_sessions_and_leaves_no_email_in_errors(conn):
    a = _admin(conn)
    u = fleet_db.add_user(conn, "victim@example.com", "user")
    conn.execute(
        "INSERT INTO sessions (id_hash, user_id, principal, created_at, last_seen_at, "
        "expires_at) VALUES ('h1', ?, 'user', 1, 40, 99)", (u,))
    rows = {r["id"]: r for r in fleet_db.list_users_with_frame_counts(conn)}
    assert rows[u]["last_seen_at"] == 40 and rows[a]["last_seen_at"] is None
    assert rows[u]["has_identity"] == 0
    assert fleet_db.set_user_disabled_guarded(conn, a, u, True)
    assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert conn.execute("SELECT disabled FROM users WHERE id = ?", (u,)).fetchone()[0] == 1
    assert fleet_db.set_user_disabled_guarded(conn, a, u, False)
    with pytest.raises(fleet_db.SelfActionError) as exc:
        fleet_db.set_user_disabled_guarded(conn, a, a, True)
    assert "example.com" not in str(exc.value)


def test_user_listing_counts_frames_and_identity(conn):
    a = _admin(conn)
    u = fleet_db.add_user(conn, "u@example.com", "user", iss="https://i", sub="s")
    fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, u, state_path="auto")
    rows = {r["id"]: r for r in fleet_db.list_users_with_frame_counts(conn)}
    assert rows[u]["frame_count"] == 1 and rows[a]["frame_count"] == 0
    assert rows[u]["has_identity"] == 1 and rows[a]["has_identity"] == 0
    assert "iss" not in rows[u].keys() and "sub" not in rows[u].keys()


def test_concurrent_mutual_demotion_keeps_an_admin(state_dir):
    setup = fleet_db.connect(state_dir)
    a = _admin(setup, "a@example.com")
    b = _admin(setup, "b@example.com")
    setup.close()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def run(actor, target):
        c = fleet_db.connect(state_dir)
        try:
            barrier.wait()
            try:
                with fleet_db.transaction(c):
                    fleet_db.set_user_role_guarded(c, actor, target, "user")
                outcomes.append("ok")
            except fleet_db.FleetDbError as exc:
                outcomes.append(type(exc).__name__)
        finally:
            c.close()

    threads = [threading.Thread(target=run, args=(a, b)),
               threading.Thread(target=run, args=(b, a))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    check = fleet_db.connect(state_dir)
    try:
        assert fleet_db.count_active_admins(check) >= 1
    finally:
        check.close()
    assert sorted(outcomes) == ["LastAdminError", "ok"]


# ---- locations -------------------------------------------------------


def test_location_visibility_by_owner(conn):
    a = _admin(conn)
    u1 = fleet_db.add_user(conn, "u1@example.com", "user")
    u2 = fleet_db.add_user(conn, "u2@example.com", "user")
    legacy = fleet_db.add_location(conn, "Legacy", 48.0, 2.0, "Europe/Paris")
    mine = fleet_db.add_location(conn, "Mine", 48.1, 2.1, "Europe/Paris", u1)
    theirs = fleet_db.add_location(conn, "Theirs", 48.2, 2.2, "Europe/Paris", u2)
    assert {r["id"] for r in fleet_db.list_locations_for(conn, a, True)} == {legacy, mine, theirs}
    assert [r["id"] for r in fleet_db.list_locations_for(conn, u1, False)] == [mine]
    assert fleet_db.count_locations_owned(conn, u1) == 1
    assert fleet_db.get_location(conn, legacy)["owner_user_id"] is None
    assert fleet_db.get_location(conn, 999) is None


def test_update_and_delete_location(conn):
    a = _admin(conn)
    loc = fleet_db.add_location(conn, "Old", 48.0, 2.0, "Europe/Paris", a)
    assert fleet_db.update_location(conn, loc, "New", 43.0, 5.0, "Europe/Paris")
    assert fleet_db.get_location(conn, loc)["name"] == "New"
    with pytest.raises(ValueError):
        fleet_db.update_location(conn, loc, "", 43.0, 5.0, "Europe/Paris")
    assert not fleet_db.update_location(conn, 999, "x", 1.0, 1.0, "Europe/Paris")
    did = fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, a, location_id=loc)
    assert fleet_db.location_usage_counts(conn) == {loc: 1}
    with pytest.raises(fleet_db.LocationInUse):
        fleet_db.delete_location_if_unused(conn, loc)
    assert fleet_db.get_location(conn, loc) is not None
    assert fleet_db.set_device_location_checked(conn, did, None, a, True)
    assert fleet_db.delete_location_if_unused(conn, loc)
    assert not fleet_db.delete_location_if_unused(conn, loc)


def test_set_device_location_checked_enforces_owners(conn):
    a = _admin(conn)
    u1 = fleet_db.add_user(conn, "u1@example.com", "user")
    u2 = fleet_db.add_user(conn, "u2@example.com", "user")
    d1 = fleet_db.add_device(conn, MAC, SECRET, hardware.LEGACY_KEY, u1, state_path="auto")
    mine = fleet_db.add_location(conn, "Mine", 48.0, 2.0, "Europe/Paris", u1)
    theirs = fleet_db.add_location(conn, "Theirs", 48.0, 2.0, "Europe/Paris", u2)
    legacy = fleet_db.add_location(conn, "Legacy", 48.0, 2.0, "Europe/Paris")
    assert fleet_db.set_device_location_checked(conn, d1, mine, u1, False)
    for forbidden in (theirs, legacy, 999):
        with pytest.raises(PermissionError):
            fleet_db.set_device_location_checked(conn, d1, forbidden, u1, False)
    with pytest.raises(PermissionError):
        fleet_db.set_device_location_checked(conn, d1, mine, u2, False)
    assert fleet_db.get_device(conn, d1)["location_id"] == mine
    assert fleet_db.set_device_location_checked(conn, d1, legacy, a, True)
    assert fleet_db.get_device(conn, d1)["location_id"] == legacy
    assert not fleet_db.set_device_location_checked(conn, "d_00000000", mine, a, True)
    with pytest.raises(ValueError):
        fleet_db.set_device_location_checked(conn, d1, 999, a, True)
