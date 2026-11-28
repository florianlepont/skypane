#!/usr/bin/env python3
"""Pinned outcomes of the fleet.db session store across a schema step.

A fleet.db file at schema 4 holding user sessions must hand back every
session row unchanged, with the same indexes and the same session
behaviour (create, read, revoke, expiry), and leave the audit and other
tables untouched, whichever later schema step it passes through when it is
opened by the current code.
"""
import hashlib
import sqlite3

import pytest

import server.fleet_db as fleet_db
import server.fleet_sessions as fs
from server import hardware

T0 = 1_800_000_000
DAY = 86400
ACTOR = fleet_db.AuditActor(None, "test", "127.0.0.1")
SESSION_COLUMNS = ("id_hash", "user_id", "principal", "created_at",
                   "last_seen_at", "expires_at")


def _h(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _v4_file(tmp_path):
    """A fleet.db at schema 4 with users, a frame, an audit row and sessions
    whose three timestamps all differ."""
    path = fleet_db.fleet_db_path(str(tmp_path))
    raw = sqlite3.connect(path, isolation_level=None)
    raw.row_factory = sqlite3.Row
    fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:4])
    assert fleet_db.schema_version(raw) == 4
    raw.execute("PRAGMA foreign_keys=ON")
    first = fleet_db.add_user(raw, "first@example.com", "admin")
    second = fleet_db.add_user(raw, "second@example.com", "user")
    fleet_db.add_device(
        raw, "aa:bb:cc:dd:ee:01", "a" * 64, hardware.LEGACY_KEY, second,
        state_path="auto")
    with fleet_db.transaction(raw):
        fleet_db.audit_append(raw, ACTOR, "probe", "user", "1", "ok", now=T0)
    sessions = [
        (_h("s1"), first, "user", T0, T0 + 10, T0 + 30 * DAY),
        (_h("s2"), second, "user", T0 + 5, T0 + 600, T0 + 5 + 30 * DAY),
        (_h("s3"), second, "user", T0 + 7, T0 + 7, T0 + 7 + 30 * DAY),
        (_h("s4"), first, "user", T0 - DAY, T0 - 3600, T0 - 1),
    ]
    raw.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)", sessions)
    raw.close()
    return path, first, second, sessions


def _rows(path, table, order):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    finally:
        conn.close()


def _index_shapes(conn):
    out = {}
    for row in conn.execute("PRAGMA index_list(sessions)"):
        name = row[1]
        if name.startswith("sqlite_autoindex"):
            continue
        out[name] = [c[2] for c in conn.execute(f"PRAGMA index_info({name})")]
    return out


def test_user_session_rows_survive_opening_every_column_equal(tmp_path):
    path, _first, _second, sessions = _v4_file(tmp_path)
    before = _rows(path, "sessions", "id_hash")
    assert sorted(before) == sorted(tuple(s) for s in sessions)
    fleet_db.connect(str(tmp_path)).close()
    after = _rows(path, "sessions", "id_hash")
    assert after == before
    # Types as well as values: integers stay integers, text stays text.
    kinds = [tuple(type(v).__name__ for v in row) for row in after]
    assert set(kinds) == {("str", "int", "str", "int", "int", "int")}


def test_session_columns_and_indexes_keep_their_shape(tmp_path):
    _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        columns = [(r[1], r[2]) for r in conn.execute("PRAGMA table_info(sessions)")]
        assert columns == [
            ("id_hash", "TEXT"), ("user_id", "INTEGER"), ("principal", "TEXT"),
            ("created_at", "INTEGER"), ("last_seen_at", "INTEGER"),
            ("expires_at", "INTEGER")]
        assert _index_shapes(conn) == {
            "sessions_user": ["user_id"], "sessions_expires": ["expires_at"]}
        pk = [r[1] for r in conn.execute("PRAGMA table_info(sessions)") if r[5]]
        assert pk == ["id_hash"]
    finally:
        conn.close()


def test_other_tables_and_audit_trail_are_untouched(tmp_path):
    path, _first, _second, _sessions = _v4_file(tmp_path)
    tables = ("users", "devices", "locations", "pending_devices",
              "device_co_managers", "audit_log", "meta")
    order = {"devices": "id", "meta": "key", "pending_devices": "id",
             "device_co_managers": "device_id, user_id"}
    before = {t: _rows(path, t, order.get(t, "id")) for t in tables}
    assert len(before["audit_log"]) == 1
    conn = fleet_db.connect(str(tmp_path))
    try:
        triggers = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        assert {"audit_log_no_update", "audit_log_no_delete",
                "device_co_managers_not_owner",
                "devices_owner_not_co_manager"} <= triggers
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM audit_log")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    assert {t: _rows(path, t, order.get(t, "id")) for t in tables} == before


def test_foreign_key_still_rejects_a_session_for_a_missing_user(tmp_path):
    _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sessions VALUES (?, ?, 'user', 1, 1, 2)",
                (_h("orphan"), 9999))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sessions VALUES (?, NULL, 'user', 1, 1, 2)", (_h("n"),))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO sessions VALUES (?, 1, 'other', 1, 1, 2)", (_h("o"),))
    finally:
        conn.close()


def test_migrated_sessions_authenticate_expire_and_revoke_as_before(tmp_path):
    _path, first, second, _sessions = _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        rec = fs.lookup_session(conn, _h("s1"), T0 + 20)
        assert rec is not None
        assert (rec.user_id, rec.principal, rec.email, rec.role) == (
            first, "user", "first@example.com", "admin")
        assert rec.created_at == T0 and rec.expires_at == T0 + 30 * DAY
        # An expired row never authenticates and is removed by the lookup.
        assert fs.lookup_session(conn, _h("s4"), T0) is None
        assert conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE id_hash = ?", (_h("s4"),)
        ).fetchone()[0] == 0
        # Revocation of one session and of every session of a user.
        fs.delete_session(conn, _h("s2"))
        assert fs.lookup_session(conn, _h("s2"), T0 + 20) is None
        assert fs.lookup_session(conn, _h("s3"), T0 + 20) is not None
        assert fs.delete_sessions_for_user(conn, second) == 1
        assert fs.lookup_session(conn, _h("s3"), T0 + 20) is None
        assert fs.lookup_session(conn, _h("s1"), T0 + 20) is not None
        # Creation and rotation.
        fs.create_session(conn, _h("new"), user_id=second, principal="user", now=T0)
        fs.create_session(
            conn, _h("rot"), user_id=second, principal="user", now=T0,
            replace_hash=_h("new"))
        assert fs.lookup_session(conn, _h("new"), T0 + 1) is None
        rec = fs.lookup_session(conn, _h("rot"), T0 + 1)
        assert rec is not None and rec.expires_at == T0 + fs.ABSOLUTE_LIFETIME_S
    finally:
        conn.close()


def test_a_disabled_user_session_is_not_returned_and_keeps_its_row(tmp_path):
    _path, _first, second, _sessions = _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (second,))
        assert fs.lookup_session(conn, _h("s2"), T0 + 20) is None
        assert conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (second,)
        ).fetchone()[0] == 2
    finally:
        conn.close()
