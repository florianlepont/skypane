#!/usr/bin/env python3
"""Tests for fleet.db schema 5: the sessions table only accepts the 'user'
principal, rebuilt atomically with a row-count check, and the report shows
the step as pending on a v4 file."""
import hashlib
import os
import sqlite3

import pytest

import server.fleet_db as fleet_db
import server.fleet_sessions as fs
import server.sqlite_migrations as sqlite_migrations
from server import hardware

T0 = 1_800_000_000
DAY = 86400
SESSION_COLUMNS = ("id_hash", "user_id", "principal", "created_at",
                   "last_seen_at", "expires_at")


def _h(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _v4_file(tmp_path, *, user_sessions=3, legacy_rows=0):
    """A v4 fleet.db with `user_sessions` user rows (all timestamps differ)
    and `legacy_rows` planted legacy-admin rows. Returns (path, expected
    user rows as tuples)."""
    path = fleet_db.fleet_db_path(str(tmp_path))
    raw = sqlite3.connect(path, isolation_level=None)
    raw.row_factory = sqlite3.Row
    fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:4])
    assert fleet_db.schema_version(raw) == 4
    raw.execute("PRAGMA foreign_keys=ON")
    uid = fleet_db.add_user(raw, "a@example.com", "admin")
    other = fleet_db.add_user(raw, "b@example.com", "user")
    fleet_db.add_device(raw, "aa:bb:cc:dd:ee:01", "a" * 64, hardware.LEGACY_KEY,
                        other, state_path="auto")
    rows = []
    for i in range(user_sessions):
        rows.append((_h("u%d" % i), (uid, other)[i % 2], "user",
                     T0 + i, T0 + 100 + 7 * i, T0 + 30 * DAY + 11 * i))
    raw.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)", rows)
    for i in range(legacy_rows):
        raw.execute("INSERT INTO sessions VALUES (?, NULL, 'legacy-admin', ?, ?, ?)",
                    (_h("l%d" % i), T0 - 40 * DAY, T0 - 40 * DAY, T0 - 10 * DAY))
    raw.close()
    return path, rows


def _read(path, sql="SELECT * FROM sessions ORDER BY id_hash"):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def _version(path):
    return _read(path, "PRAGMA user_version")[0][0]


def _sessions_sql(path):
    return _read(path, "SELECT sql FROM sqlite_master WHERE name = 'sessions'")[0][0]


def test_step_list_ends_with_the_sessions_rebuild():
    assert fleet_db.SCHEMA_VERSION == len(fleet_db.MIGRATIONS) == 5
    assert [s.version for s in fleet_db.FLEET_STEPS] == [1, 2, 3, 4, 5]
    assert fleet_db.FLEET_STEPS[-1].name == "sessions-user-principal-only"


def test_v4_user_rows_survive_byte_equal_in_every_column(tmp_path):
    path, rows = _v4_file(tmp_path, user_sessions=5)
    before = _read(path)
    fleet_db.connect(str(tmp_path)).close()
    assert _version(path) == 5
    after = _read(path)
    assert after == before == sorted(rows)
    assert {tuple(type(v).__name__ for v in r) for r in after} == {
        ("str", "int", "str", "int", "int", "int")}
    conn = sqlite3.connect(path)
    try:
        assert [c[1] for c in conn.execute("PRAGMA table_info(sessions)")] == list(
            SESSION_COLUMNS)
    finally:
        conn.close()


def test_indexes_are_recreated_exactly(tmp_path):
    path, _rows = _v4_file(tmp_path)
    shapes = {}
    for label in ("before", "after"):
        conn = sqlite3.connect(path)
        try:
            shapes[label] = {
                r[0]: r[1] for r in conn.execute(
                    "SELECT name, sql FROM sqlite_master "
                    "WHERE type = 'index' AND tbl_name = 'sessions' AND sql IS NOT NULL")
            }
        finally:
            conn.close()
        fleet_db.connect(str(tmp_path)).close()
    assert shapes["before"] == shapes["after"]
    assert set(shapes["after"]) == {"sessions_user", "sessions_expires"}


def test_zero_sessions_migrates_to_an_empty_table(tmp_path):
    path, _rows = _v4_file(tmp_path, user_sessions=0)
    fleet_db.connect(str(tmp_path)).close()
    assert _version(path) == 5
    assert _read(path) == []
    assert "'legacy-admin'" not in _sessions_sql(path)


def test_planted_legacy_admin_rows_are_removed_counted_and_reported(tmp_path, capsys):
    path, rows = _v4_file(tmp_path, user_sessions=3, legacy_rows=2)
    assert len(_read(path)) == 5
    fleet_db.connect(str(tmp_path)).close()
    assert _read(path) == sorted(rows)
    out = capsys.readouterr().out
    assert "removed 2 legacy-admin session row(s)" in out
    assert _h("l0") not in out


def test_no_report_line_when_no_legacy_admin_row_exists(tmp_path, capsys):
    _v4_file(tmp_path)
    fleet_db.connect(str(tmp_path)).close()
    assert "legacy-admin" not in capsys.readouterr().out


def test_foreign_keys_stay_on_and_nothing_references_sessions(tmp_path):
    path, _rows = _v4_file(tmp_path, legacy_rows=1)
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sessions VALUES (?, 9999, 'user', 1, 1, 2)",
                         (_h("orphan"),))
        referencing = conn.execute(
            "SELECT name FROM sqlite_master WHERE sql LIKE '%REFERENCES sessions%'"
        ).fetchall()
        assert referencing == []
    finally:
        conn.close()
    assert _version(path) == 5


def test_check_rejects_a_legacy_admin_row_and_a_missing_user(tmp_path):
    _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        insert = "INSERT INTO sessions VALUES (?, ?, ?, 1, 1, 2)"
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("h1", None, "legacy-admin"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("h2", uid, "legacy-admin"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(insert, ("h3", None, "user"))
        conn.execute(insert, ("h4", uid, "user"))
    finally:
        conn.close()


def test_session_store_refuses_to_create_a_legacy_admin_session(tmp_path):
    _v4_file(tmp_path)
    conn = fleet_db.connect(str(tmp_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            fs.create_session(conn, _h("x"), user_id=None, principal="legacy-admin",
                              now=T0)
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 3
        assert not conn.in_transaction
    finally:
        conn.close()


def test_second_open_is_a_no_op_byte_for_byte(tmp_path):
    path, _rows = _v4_file(tmp_path, legacy_rows=1)
    fleet_db.connect(str(tmp_path)).close()
    first = _bytes(path)
    fleet_db.connect(str(tmp_path)).close()
    assert _bytes(path) == first
    assert _version(path) == 5


def test_a_fresh_file_is_created_at_schema_5_with_the_narrow_check(tmp_path):
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert fleet_db.schema_version(conn) == 5
        assert "legacy-admin" not in _sessions_sql(fleet_db.fleet_db_path(str(tmp_path)))
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    finally:
        conn.close()


def test_a_file_at_schema_6_is_refused_without_a_write(tmp_path):
    path, _rows = _v4_file(tmp_path)
    fleet_db.connect(str(tmp_path)).close()
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = 6")
    raw.commit()
    raw.close()
    before = _bytes(path)
    with pytest.raises(fleet_db.FleetDbTooNew) as excinfo:
        fleet_db.connect(str(tmp_path))
    assert str(excinfo.value) == "fleet.db schema 6 is newer than supported 5"
    assert _bytes(path) == before


def test_a_runner_with_four_steps_refuses_a_v5_file(tmp_path):
    path, _rows = _v4_file(tmp_path)
    fleet_db.connect(str(tmp_path)).close()
    before = _bytes(path)
    raw = sqlite3.connect(path, isolation_level=None)
    try:
        with pytest.raises(fleet_db.FleetDbTooNew) as excinfo:
            fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:4])
    finally:
        raw.close()
    assert str(excinfo.value) == "fleet.db schema 5 is newer than supported 4"
    assert _bytes(path) == before


def test_failure_after_the_rebuild_leaves_the_v4_file_unchanged(tmp_path):
    path, _rows = _v4_file(tmp_path, user_sessions=4, legacy_rows=2)
    before = _bytes(path)

    def rebuild_then_fail(conn):
        fleet_db.MIGRATIONS[4](conn)
        raise RuntimeError("injected failure after the rebuild")

    raw = sqlite3.connect(path, isolation_level=None)
    try:
        with pytest.raises(RuntimeError):
            fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:4] + (rebuild_then_fail,))
        assert not raw.in_transaction
    finally:
        raw.close()
    assert _version(path) == 4
    assert _bytes(path) == before
    assert len(_read(path)) == 6
    assert "'legacy-admin'" in _sessions_sql(path)
    fleet_db.connect(str(tmp_path)).close()
    assert _version(path) == 5 and len(_read(path)) == 4


def _content(path):
    """Every schema object and every row of the file, so two snapshots are
    equal exactly when the stored data is."""
    conn = sqlite3.connect(path)
    try:
        return list(conn.iterdump()), conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


def test_a_row_count_mismatch_rolls_back_and_the_file_stays_v4(tmp_path, monkeypatch):
    path, _rows = _v4_file(tmp_path, user_sessions=4, legacy_rows=1)
    before = _content(path)
    real_copy = fleet_db._copy_user_sessions

    def lossy_copy(conn):
        real_copy(conn)
        conn.execute("DELETE FROM sessions_new WHERE rowid = (SELECT min(rowid) FROM sessions_new)")

    monkeypatch.setattr(fleet_db, "_copy_user_sessions", lossy_copy)
    with pytest.raises(fleet_db.FleetDbError, match="row count"):
        fleet_db.connect(str(tmp_path))
    assert _content(path) == before
    assert _version(path) == 4
    assert len(_read(path)) == 5
    assert "sessions_new" not in "".join(before[0]) and not _read(
        path, "SELECT name FROM sqlite_master WHERE name = 'sessions_new'")
    monkeypatch.undo()
    fleet_db.connect(str(tmp_path)).close()
    assert _version(path) == 5 and len(_read(path)) == 4


def test_the_step_runs_inside_the_immediate_transaction(tmp_path):
    path, _rows = _v4_file(tmp_path)
    seen = []
    real = fleet_db._copy_user_sessions

    def spy(conn):
        seen.append(conn.in_transaction)
        other = sqlite3.connect(path, isolation_level=None, timeout=0)
        try:
            other.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            seen.append(str(exc))
        finally:
            other.close()
        real(conn)

    fleet_db._copy_user_sessions = spy
    try:
        fleet_db.connect(str(tmp_path)).close()
    finally:
        fleet_db._copy_user_sessions = real
    assert seen == [True, "database is locked"]


def test_report_shows_step_5_pending_on_a_v4_file(tmp_path):
    _v4_file(tmp_path, user_sessions=3, legacy_rows=2)
    lines, code = sqlite_migrations.report(str(tmp_path))
    assert code == sqlite_migrations.EXIT_PENDING
    assert lines[0] == (
        "fleet.db pending current=4 target=5 pending=1 "
        "step=5:sessions-user-principal-only:rebuilds-table:sessions,"
        "removes-legacy-admin-rows:2")


def test_report_on_a_v4_file_without_legacy_rows_counts_zero(tmp_path):
    _v4_file(tmp_path)
    lines, _code = sqlite_migrations.report(str(tmp_path))
    assert lines[0].endswith("removes-legacy-admin-rows:0")


def test_report_on_an_old_file_without_a_sessions_table_counts_zero(tmp_path):
    raw = sqlite3.connect(fleet_db.fleet_db_path(str(tmp_path)), isolation_level=None)
    fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:1])
    raw.close()
    lines, code = sqlite_migrations.report(str(tmp_path))
    assert code == sqlite_migrations.EXIT_PENDING
    assert lines[0].endswith("step=5:sessions-user-principal-only:"
                             "rebuilds-table:sessions,removes-legacy-admin-rows:0")


def test_report_is_ok_on_a_v5_file_and_writes_nothing(tmp_path):
    path, _rows = _v4_file(tmp_path)
    fleet_db.connect(str(tmp_path)).close()
    before = _bytes(path)
    names = sorted(os.listdir(tmp_path))
    lines, code = sqlite_migrations.report(str(tmp_path))
    assert code == sqlite_migrations.EXIT_CURRENT
    assert lines[0] == "fleet.db ok current=5 target=5 pending=0"
    assert _bytes(path) == before
    assert sorted(os.listdir(tmp_path)) == names
