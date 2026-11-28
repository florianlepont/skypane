#!/usr/bin/env python3
"""Pins the `PRAGMA user_version` outcomes of fleet.db and history.db.

Both databases are migrated by the shared mechanism in
`server/sqlite_migrations.py` under two policies. These tests exercise only
public entry points and assert outcomes (versions, tables, columns, file
bytes), so they hold for any implementation behind them.
"""
import hashlib
import os
import sqlite3
import subprocess
import sys
import textwrap
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.fleet_db as fleet_db  # noqa: E402
import server.history_db as history_db  # noqa: E402
import server.sqlite_migrations as sqlite_migrations  # noqa: E402

FLEET_TABLES = {
    "users", "locations", "devices", "meta", "sessions", "pending_devices",
    "audit_log", "device_co_managers",
}
HISTORY_TABLES = {
    "runway_events", "device_health", "meta", "wake_epochs", "poll_cycles",
    "route_lookups",
}


def _digest(path):
    """Hash of the main file plus any WAL/SHM sidecar bytes."""
    h = hashlib.sha256()
    for suffix in ("", "-wal"):
        p = path + suffix
        if os.path.exists(p):
            with open(p, "rb") as handle:
                h.update(handle.read())
    return h.hexdigest()


def _tables(conn):
    return {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")
    }


def _columns(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)}


def _version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _indexes(conn):
    return {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_%'")
    }


def _triggers(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'")}


def _fleet_at(state_dir, upto):
    path = fleet_db.fleet_db_path(state_dir)
    raw = sqlite3.connect(path, isolation_level=None)
    fleet_db.migrate_schema(raw, fleet_db.MIGRATIONS[:upto])
    assert _version(raw) == upto
    raw.close()
    return path


# --- fleet.db ---------------------------------------------------------------


def test_fleet_target_version_is_four():
    assert fleet_db.SCHEMA_VERSION == 4
    assert len(fleet_db.MIGRATIONS) == 4


def test_fleet_fresh_file_ends_at_current_with_all_tables(tmp_path):
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert _version(conn) == 4
        assert _tables(conn) == FLEET_TABLES
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_fleet_fresh_file_is_created_mode_0600(tmp_path):
    fleet_db.connect(str(tmp_path)).close()
    mode = os.stat(fleet_db.fleet_db_path(str(tmp_path))).st_mode & 0o777
    assert mode == 0o600


@pytest.mark.parametrize("start", [1, 2, 3])
def test_fleet_older_versions_end_at_current(tmp_path, start):
    _fleet_at(str(tmp_path), start)
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert _version(conn) == 4
        assert _tables(conn) == FLEET_TABLES
    finally:
        conn.close()


def test_fleet_v2_gains_the_v3_and_v4_changes(tmp_path):
    path = _fleet_at(str(tmp_path), 2)
    raw = sqlite3.connect(path)
    before_tables = _tables(raw)
    before_triggers = _triggers(raw)
    raw.close()
    assert "device_co_managers" not in before_tables
    assert "device_co_managers_not_owner" not in before_triggers

    conn = fleet_db.connect(str(tmp_path))
    try:
        assert "device_co_managers" in _tables(conn)
        assert {
            "device_co_managers_not_owner", "devices_owner_not_co_manager",
        } <= _triggers(conn)
        assert "device_co_managers_user" in _indexes(conn)
    finally:
        conn.close()


def test_fleet_upgrade_keeps_existing_rows(tmp_path):
    path = _fleet_at(str(tmp_path), 2)
    raw = sqlite3.connect(path, isolation_level=None)
    raw.execute("INSERT INTO meta (key, value) VALUES ('probe', 'kept')")
    raw.close()
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert fleet_db.meta_get(conn, "probe") == "kept"
    finally:
        conn.close()


def test_fleet_current_file_reopen_changes_no_byte(tmp_path):
    fleet_db.connect(str(tmp_path)).close()
    path = fleet_db.fleet_db_path(str(tmp_path))
    first = _digest(path)
    again = fleet_db.connect(str(tmp_path))
    assert _version(again) == 4
    again.close()
    assert _digest(path) == first


def test_fleet_newer_file_is_refused_before_any_write(tmp_path):
    path = fleet_db.fleet_db_path(str(tmp_path))
    raw = sqlite3.connect(path)
    raw.execute("CREATE TABLE marker (x INTEGER)")
    raw.execute("PRAGMA user_version = 5")
    raw.commit()
    raw.close()
    before = _digest(path)
    mode_before = os.stat(path).st_mode

    with pytest.raises(fleet_db.FleetDbTooNew) as excinfo:
        fleet_db.connect(str(tmp_path))
    assert str(excinfo.value) == "fleet.db schema 5 is newer than supported 4"

    assert _digest(path) == before
    assert os.stat(path).st_mode == mode_before
    assert not os.path.exists(path + "-wal")
    check = sqlite3.connect(path)
    assert check.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert _version(check) == 5
    assert _tables(check) == {"marker"}
    check.close()


def test_fleet_migrate_schema_refuses_newer_with_same_error(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)
    conn.execute("PRAGMA user_version = 9")
    with pytest.raises(fleet_db.FleetDbTooNew) as excinfo:
        fleet_db.migrate_schema(conn)
    assert str(excinfo.value) == "fleet.db schema 9 is newer than supported 4"
    assert _version(conn) == 9
    assert _tables(conn) == set()
    conn.close()


def test_fleet_custom_step_tuple_is_the_target(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)
    conn.execute("PRAGMA user_version = 3")
    with pytest.raises(fleet_db.FleetDbTooNew) as excinfo:
        fleet_db.migrate_schema(conn, (lambda c: None, lambda c: None))
    assert str(excinfo.value) == "fleet.db schema 3 is newer than supported 2"
    conn.close()


def test_fleet_step_runs_inside_begin_immediate_with_version_bump(tmp_path):
    path = str(tmp_path / "x.db")
    conn = sqlite3.connect(path, isolation_level=None)
    other = sqlite3.connect(path, isolation_level=None, timeout=0)
    seen = []

    def step(c):
        seen.append(c.in_transaction)
        # A second writer cannot get the lock while the step runs.
        try:
            other.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            seen.append(str(exc))
        else:
            other.execute("ROLLBACK")
            seen.append("writer admitted")
        c.execute("CREATE TABLE t (x INTEGER)")
        # The bump is not yet visible from outside the open transaction.
        seen.append(_version(other))

    fleet_db.migrate_schema(conn, (step,))
    assert seen == [True, "database is locked", 0]
    assert not conn.in_transaction
    assert _version(other) == 1
    assert _tables(other) == {"t"}
    conn.close()
    other.close()


def test_fleet_failed_step_rolls_back_and_keeps_old_version(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)

    def ok(c):
        c.execute("CREATE TABLE a (x INTEGER)")

    def bad(c):
        c.execute("CREATE TABLE b (x INTEGER)")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        fleet_db.migrate_schema(conn, (ok, bad))
    assert _version(conn) == 1
    assert _tables(conn) == {"a"}
    assert not conn.in_transaction
    conn.close()


def test_fleet_step_applied_by_another_process_is_skipped(tmp_path):
    path = str(tmp_path / "x.db")
    conn = sqlite3.connect(path, isolation_level=None)
    calls = []

    def first(c):
        calls.append("first")
        # Simulates another process finishing step 2 while this one holds
        # no lock yet: the next iteration must re-read the version.

    def second(c):
        calls.append("second")

    # Pre-stamp as if a racing process had applied step 2 already.
    conn.execute("PRAGMA user_version = 1")
    fleet_db.migrate_schema(conn, (first, second))
    assert calls == ["second"]
    assert _version(conn) == 2
    conn.close()


def test_fleet_two_threads_migrating_one_fresh_file_both_succeed(tmp_path):
    path = str(tmp_path / "x.db")
    barrier = threading.Barrier(2)
    errors, versions = [], []

    def run():
        conn = sqlite3.connect(path, isolation_level=None, timeout=10)
        try:
            barrier.wait()
            fleet_db.migrate_schema(conn)
            versions.append(_version(conn))
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
    assert versions == [4, 4]
    check = sqlite3.connect(path)
    assert _tables(check) == FLEET_TABLES
    check.close()


def test_fleet_busy_timeout_is_5000_ms(tmp_path):
    conn = fleet_db.connect(str(tmp_path))
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        conn.close()


# --- history.db -------------------------------------------------------------


def _history_conn(state_dir):
    return history_db.connect(str(state_dir))


def _make_old_history(path):
    """History file from before the route-directory counters: user_version 0,
    no route_lookups table, no extra runway_events or device_health columns,
    one row in each."""
    raw = sqlite3.connect(path)
    raw.execute(
        "CREATE TABLE runway_events (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, "
        "hex TEXT, callsign TEXT, aircraft_type TEXT, confirmed_state TEXT, "
        "corroborated TEXT, route_source TEXT, airline TEXT, origin TEXT, "
        "destination TEXT, tracked_runway TEXT)")
    raw.execute(
        "CREATE TABLE device_health (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, "
        "battery_mv INTEGER, fw_version TEXT, boot_reason TEXT, rssi TEXT, "
        "UNIQUE(ts, battery_mv))")
    raw.execute(
        "INSERT INTO runway_events (ts, hex, callsign) "
        "VALUES ('2026-01-01T00:00:00', 'abc123', 'TST1')")
    raw.execute(
        "INSERT INTO device_health (ts, battery_mv) "
        "VALUES ('2026-01-01T00:00:00', 3900)")
    raw.commit()
    assert _version(raw) == 0
    raw.close()


def test_history_target_version_is_one():
    assert history_db.HISTORY_SCHEMA_VERSION == 1


def test_history_fresh_file_ends_at_one_with_all_tables(tmp_path):
    conn = _history_conn(tmp_path)
    try:
        assert _version(conn) == 1
        assert _tables(conn) == HISTORY_TABLES
        assert {"gallery_name", "route_directory"} <= _columns(conn, "runway_events")
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


def test_history_old_file_gains_route_lookups_and_columns_keeping_rows(tmp_path):
    path = history_db.history_db_path(str(tmp_path))
    _make_old_history(path)
    conn = _history_conn(tmp_path)
    try:
        assert _version(conn) == 1
        assert _tables(conn) == HISTORY_TABLES
        events = _columns(conn, "runway_events")
        assert {"gallery_name", "route_directory"} <= events
        assert set(history_db._WAKE_COLUMN_TYPES) <= _columns(conn, "device_health")
        row = conn.execute(
            "SELECT hex, callsign, gallery_name, route_directory "
            "FROM runway_events").fetchone()
        assert tuple(row) == ("abc123", "TST1", None, None)
        assert conn.execute("SELECT COUNT(*) FROM device_health").fetchone()[0] == 1
    finally:
        conn.close()


def test_history_current_file_reopen_in_new_process_state_changes_no_byte(tmp_path):
    _history_conn(tmp_path).close()
    path = history_db.history_db_path(str(tmp_path))
    first = _digest(path)
    history_db._SCHEMA_READY.clear()
    again = _history_conn(tmp_path)
    assert _version(again) == 1
    again.close()
    assert _digest(path) == first


def test_history_init_schema_twice_is_idempotent(tmp_path):
    conn = _history_conn(tmp_path)
    try:
        before = (_version(conn), _tables(conn), _indexes(conn))
        history_db.init_schema(conn)
        history_db.init_schema(conn)
        assert (_version(conn), _tables(conn), _indexes(conn)) == before
    finally:
        conn.close()


@pytest.mark.parametrize("stamp", [7, 2])
def test_history_newer_stamp_is_kept_and_not_refused(tmp_path, stamp):
    _history_conn(tmp_path).close()
    path = history_db.history_db_path(str(tmp_path))
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = %d" % stamp)
    raw.commit()
    raw.close()
    history_db._SCHEMA_READY.clear()
    conn = _history_conn(tmp_path)
    try:
        assert _version(conn) == stamp
        history_db.init_schema(conn)
        assert _version(conn) == stamp
        assert _tables(conn) == HISTORY_TABLES
    finally:
        conn.close()


def test_history_stamped_current_but_missing_table_is_repaired(tmp_path):
    _history_conn(tmp_path).close()
    path = history_db.history_db_path(str(tmp_path))
    raw = sqlite3.connect(path)
    raw.execute("DROP TABLE route_lookups")
    raw.commit()
    assert _version(raw) == 1
    raw.close()
    history_db._SCHEMA_READY.clear()
    conn = _history_conn(tmp_path)
    try:
        assert "route_lookups" in _tables(conn)
        assert _version(conn) == 1
    finally:
        conn.close()


def test_history_zero_size_file_is_rebuilt_even_when_marked_ready(tmp_path):
    conn = _history_conn(tmp_path)
    conn.close()
    path = history_db.history_db_path(str(tmp_path))
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    conn = _history_conn(tmp_path)
    try:
        assert _version(conn) == 1
        assert _tables(conn) == HISTORY_TABLES
    finally:
        conn.close()


def test_history_init_schema_on_unversioned_complete_file_stamps_one(tmp_path):
    conn = _history_conn(tmp_path)
    conn.execute("PRAGMA user_version = 0")
    history_db.init_schema(conn)
    try:
        assert _version(conn) == 1
    finally:
        conn.close()


def test_history_two_threads_opening_a_fresh_file_both_succeed(tmp_path):
    barrier = threading.Barrier(2)
    errors, versions = [], []

    def run():
        try:
            barrier.wait()
            conn = _history_conn(tmp_path)
            versions.append(_version(conn))
            conn.close()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert versions == [1, 1]
    check = _history_conn(tmp_path)
    assert _tables(check) == HISTORY_TABLES
    check.close()


def test_history_two_schema_runs_racing_on_separate_connections(tmp_path):
    path = history_db.history_db_path(str(tmp_path))
    _make_old_history(path)
    barrier = threading.Barrier(2)
    errors = []

    def run():
        conn = sqlite3.connect(path, timeout=10)
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            barrier.wait()
            history_db.init_schema(conn)
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
    check = sqlite3.connect(path)
    assert _version(check) == 1
    assert _tables(check) == HISTORY_TABLES
    assert {"gallery_name", "route_directory"} <= _columns(check, "runway_events")
    check.close()


def test_history_two_processes_completing_one_old_file_both_succeed(tmp_path):
    # The file already exists in WAL mode, as it does once any process has
    # opened it; the two processes race only on completing its schema. (The
    # very first journal-mode switch of a brand-new file across two processes
    # can lose with "database is locked" and is not part of this guarantee.)
    path = history_db.history_db_path(str(tmp_path))
    _make_old_history(path)
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA journal_mode=WAL")
    raw.close()
    script = textwrap.dedent(
        """
        import sys, time
        sys.path.insert(0, sys.argv[1])
        import server.history_db as history_db
        while time.time() < float(sys.argv[3]):
            pass
        conn = history_db.connect(sys.argv[2])
        print(conn.execute("PRAGMA user_version").fetchone()[0])
        conn.close()
        """
    )
    start = str(time.time() + 1.5)
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script, REPO_ROOT, str(tmp_path), start],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    results = [p.communicate(timeout=60) + (p.returncode,) for p in procs]
    assert [r[2] for r in results] == [0, 0], results
    assert [r[0].strip() for r in results] == ["1", "1"]
    check = _history_conn(tmp_path)
    assert _tables(check) == HISTORY_TABLES
    assert {"gallery_name", "route_directory"} <= _columns(check, "runway_events")
    check.close()


def test_history_busy_timeout_is_5000_ms(tmp_path):
    conn = _history_conn(tmp_path)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        conn.close()


# --- read-only report -------------------------------------------------------

FAKE_TOKEN = "tok_FAKESECRETVALUE0123456789"
FAKE_HASH = "f" * 64
DEVICE_ID = "d_0a1b2c3d"


def _tree_state(root):
    """Every path under `root` with its content hash: detects a changed byte
    and a created or removed file alike."""
    state = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith("-shm"):
                # The WAL index is shared memory every reader updates; it
                # holds no database content, but its presence is checked.
                state[name] = ""
                continue
            full = os.path.join(dirpath, name)
            with open(full, "rb") as handle:
                state[os.path.relpath(full, root)] = hashlib.sha256(
                    handle.read()).hexdigest()
    return state


def _seed_secret_rows(path):
    raw = sqlite3.connect(path, isolation_level=None)
    raw.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("note", FAKE_TOKEN))
    raw.execute("INSERT INTO users (email, role, created_at) VALUES (?, 'admin', 'now')",
                ("%s@example.org" % FAKE_TOKEN.lower(),))
    raw.execute(
        "INSERT INTO sessions (id_hash, user_id, principal, created_at, "
        "last_seen_at, expires_at) VALUES (?, 1, 'user', 1, 1, 2)", (FAKE_HASH,))
    raw.close()


def _report(state_dir, capsys):
    code = sqlite_migrations.main(["report", "--state-dir", str(state_dir)])
    return code, capsys.readouterr().out.splitlines()


def test_report_current_files_exit_zero_and_one_line_each(tmp_path, capsys):
    fleet_db.connect(str(tmp_path)).close()
    _history_conn(tmp_path).close()
    device_dir = tmp_path / "devices" / DEVICE_ID
    device_dir.mkdir(parents=True)
    history_db.connect(str(device_dir)).close()
    before = _tree_state(tmp_path)

    code, lines = _report(tmp_path, capsys)

    assert code == 0
    assert lines == [
        "fleet.db ok current=4 target=4 pending=0",
        "history.db ok current=1 target=1 pending=0",
        "devices/%s/history.db ok current=1 target=1 pending=0" % DEVICE_ID,
    ]
    assert _tree_state(tmp_path) == before


def test_report_older_fleet_lists_pending_steps_and_exits_three(tmp_path, capsys):
    path = _fleet_at(str(tmp_path), 2)
    _seed_secret_rows(path)
    before = _tree_state(tmp_path)

    code, lines = _report(tmp_path, capsys)

    assert code == 3
    assert len(lines) == 2  # fleet.db, plus the absent root history.db
    fields = lines[0].split(" ")
    assert fields[:5] == ["fleet.db", "pending", "current=2", "target=4", "pending=2"]
    assert fields[5].startswith("step=3:") and fields[6].startswith("step=4:")
    assert len(fields) == 7
    assert lines[1] == "history.db absent"
    assert _tree_state(tmp_path) == before


def test_report_never_prints_row_contents(tmp_path, capsys):
    fleet_db.connect(str(tmp_path)).close()
    _seed_secret_rows(fleet_db.fleet_db_path(str(tmp_path)))
    path = history_db.history_db_path(str(tmp_path))
    _make_old_history(path)
    raw = sqlite3.connect(path)
    raw.execute("INSERT INTO runway_events (ts, callsign) VALUES ('t', ?)",
                (FAKE_TOKEN,))
    raw.commit()
    raw.close()

    code, lines = _report(tmp_path, capsys)

    text = "\n".join(lines)
    assert code == 3
    assert FAKE_TOKEN not in text and FAKE_TOKEN.lower() not in text
    assert FAKE_HASH not in text
    # The old-shape fixture lacks four tables, the wake columns and two more.
    assert lines[1] == (
        "history.db pending current=0 target=1 pending=1 "
        "step=1:initial-schema:creates-tables:4,adds-columns:%d"
        % (len(history_db._WAKE_COLUMN_TYPES) + 2))


def test_report_newer_fleet_is_flagged_not_pending(tmp_path, capsys):
    path = fleet_db.fleet_db_path(str(tmp_path))
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = 5")
    raw.commit()
    raw.close()
    before = _tree_state(tmp_path)

    code, lines = _report(tmp_path, capsys)

    assert code == 0
    assert lines[0] == "fleet.db newer current=5 target=4 pending=0"
    assert _tree_state(tmp_path) == before


def test_report_unreadable_file_exits_two_without_content(tmp_path, capsys):
    (tmp_path / "fleet.db").write_bytes(b"this is not a database " * 200)
    before = _tree_state(tmp_path)

    code, lines = _report(tmp_path, capsys)

    assert code == 2
    assert lines[0] == "fleet.db unreadable"
    assert _tree_state(tmp_path) == before


def test_report_reads_a_live_wal_database_without_writing(tmp_path, capsys):
    holder = history_db.connect(str(tmp_path))
    holder.execute(
        "INSERT INTO runway_events (ts, callsign) VALUES ('t', ?)", (FAKE_TOKEN,))
    holder.commit()
    assert os.path.exists(history_db.history_db_path(str(tmp_path)) + "-wal")
    before = _tree_state(tmp_path)
    try:
        code, lines = _report(tmp_path, capsys)
        after = _tree_state(tmp_path)
    finally:
        holder.close()
    assert code == 0
    assert "history.db ok current=1 target=1 pending=0" in lines
    assert FAKE_TOKEN not in "\n".join(lines)
    assert after == before


def test_report_skips_linked_and_badly_named_device_directories(tmp_path, capsys):
    devices = tmp_path / "devices"
    devices.mkdir()
    (devices / "not-a-device").mkdir()
    history_db.connect(str(devices / "not-a-device")).close()
    (devices / DEVICE_ID).symlink_to(devices / "not-a-device")

    code, lines = _report(tmp_path, capsys)

    assert code == 0
    assert lines == ["fleet.db absent", "history.db absent"]


def test_report_command_runs_as_a_module_and_writes_nothing(tmp_path):
    _fleet_at(str(tmp_path), 3)
    before = _tree_state(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "server.sqlite_migrations", "report",
         "--state-dir", str(tmp_path)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 3, proc.stderr
    assert proc.stdout.splitlines()[0].startswith(
        "fleet.db pending current=3 target=4 pending=1 step=4:device-co-managers:")
    assert _tree_state(tmp_path) == before


def test_pending_steps_lists_only_steps_above_the_stamp(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"), isolation_level=None)
    conn.execute("PRAGMA user_version = 2")
    names = [s.name for s in sqlite_migrations.pending_steps(conn, fleet_db.FLEET_STEPS)]
    assert names == ["pending-devices-and-owned-locations", "device-co-managers"]
    assert _version(conn) == 2
    conn.close()


def test_idempotent_policy_never_lowers_a_newer_stamp(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"))
    conn.execute("PRAGMA user_version = 8")
    calls = []
    steps = (sqlite_migrations.Step(1, "one", lambda c: calls.append(1)),)
    sqlite_migrations.apply_steps(
        conn, steps, sqlite_migrations.Policy("idempotent", "keep"))
    assert _version(conn) == 8 and calls == [1]
    conn.close()


def test_add_column_if_missing_is_idempotent(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "x.db"))
    conn.execute("CREATE TABLE t (a INTEGER)")
    sqlite_migrations.add_column_if_missing(conn, "t", "b", "TEXT")
    sqlite_migrations.add_column_if_missing(conn, "t", "b", "TEXT")
    assert _columns(conn, "t") == {"a", "b"}
    conn.close()
