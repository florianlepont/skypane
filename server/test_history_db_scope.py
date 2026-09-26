#!/usr/bin/env python3
"""Contract tests for server/history_db.py's connection scope, schema-once
file identity, and write batching -- the machinery that lets a whole
companion request or poll cycle share one connection and one COMMIT,
without changing any existing open_db()/connect() caller's signature or
behaviour outside a scope/batch.
"""
import json
import os
import sqlite3
import sys
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import efficiency_probe  # noqa: E402
import server.history_db as history_db  # noqa: E402


# --- connection_scope / scoped open_db --------------------------------------


def test_two_open_db_blocks_in_one_scope_share_one_connection(tmp_path):
    """two open_db(tmp) blocks inside one connection_scope(tmp) yield the
    same connection object and open exactly one; the connection stays open
    after the first block closes, and is closed only once the scope itself
    exits"""
    state_dir = str(tmp_path)
    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            with history_db.open_db(state_dir) as conn1:
                history_db.set_meta(conn1, "k1", "v1")
            with history_db.open_db(state_dir) as conn2:
                assert conn1 is conn2
                conn2.execute("SELECT 1")  # still open after the first block
    assert counts.connections == 1

    with pytest.raises(sqlite3.ProgrammingError):
        conn1.execute("SELECT 1")  # closed once the scope has exited


def test_scope_that_never_opens_a_connection_opens_zero(tmp_path):
    state_dir = str(tmp_path)
    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            pass
    assert counts.connections == 0


def test_nested_scope_shares_one_connection_closed_at_outermost_exit(tmp_path):
    state_dir = str(tmp_path)
    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            with history_db.open_db(state_dir) as outer_conn:
                history_db.set_meta(outer_conn, "outer", "1")
                with history_db.connection_scope(state_dir):
                    with history_db.open_db(state_dir) as inner_conn:
                        assert inner_conn is outer_conn
                # the inner connection_scope exited; the connection is
                # still open because the outer scope has not exited yet.
                outer_conn.execute("SELECT 1")
    assert counts.connections == 1

    with pytest.raises(sqlite3.ProgrammingError):
        outer_conn.execute("SELECT 1")


def test_open_db_for_a_different_path_inside_a_scope_is_a_separate_passthrough(tmp_path):
    state_dir = str(tmp_path / "scoped")
    other_dir = str(tmp_path / "other")
    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            with history_db.open_db(state_dir) as scoped_conn:
                with history_db.open_db(other_dir) as other_conn:
                    assert other_conn is not scoped_conn
                # the other path's connection closes on its own block exit
                with pytest.raises(sqlite3.ProgrammingError):
                    other_conn.execute("SELECT 1")
                # the scoped connection is unaffected, still open
                scoped_conn.execute("SELECT 1")
    assert counts.connections == 2


def test_nested_scope_for_a_different_path_is_also_served_unscoped(tmp_path):
    """a connection_scope for a different path started while one is
    already active on this thread does not take over the slot - it is
    served exactly as if no scope were active at all, closing its own
    connection on its own exit while the outer scope's connection is
    untouched"""
    state_dir = str(tmp_path / "scoped")
    other_dir = str(tmp_path / "other")
    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            with history_db.open_db(state_dir) as scoped_conn:
                with history_db.connection_scope(other_dir):
                    with history_db.open_db(other_dir) as other_conn:
                        assert other_conn is not scoped_conn
                    with pytest.raises(sqlite3.ProgrammingError):
                        other_conn.execute("SELECT 1")
                scoped_conn.execute("SELECT 1")
    assert counts.connections == 2


def test_second_thread_opening_the_same_path_gets_its_own_connection(tmp_path):
    """a scope lives in threading.local(): another thread never sees it,
    and sqlite3's check_same_thread stays satisfied"""
    state_dir = str(tmp_path)
    other_conn_holder = {}
    ready = threading.Event()
    release = threading.Event()

    def worker():
        with history_db.open_db(state_dir) as conn:
            other_conn_holder["conn"] = conn
            history_db.set_meta(conn, "worker", "1")
            ready.set()
            release.wait(timeout=5)

    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            with history_db.open_db(state_dir) as main_conn:
                thread = threading.Thread(target=worker)
                thread.start()
                assert ready.wait(timeout=5)
                assert other_conn_holder["conn"] is not main_conn
                release.set()
                thread.join(timeout=5)
    assert counts.connections == 2
    assert counts.by_thread[threading.current_thread().name] == 1


def test_scoped_open_failure_is_remembered_and_not_retried(tmp_path, monkeypatch):
    """a scoped open_db failure is remembered for the rest of the scope:
    every later open_db in the scope re-raises the same exception class
    without calling sqlite3.connect again"""
    state_dir = str(tmp_path)
    calls = []
    real_connect = sqlite3.connect

    def failing_connect(*args, **kwargs):
        calls.append(1)
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(sqlite3, "connect", failing_connect)
    with history_db.connection_scope(state_dir):
        with pytest.raises(sqlite3.OperationalError):
            with history_db.open_db(state_dir):
                pass
        with pytest.raises(sqlite3.OperationalError):
            with history_db.open_db(state_dir):
                pass
    assert len(calls) == 1
    monkeypatch.setattr(sqlite3, "connect", real_connect)


def test_scope_exit_with_pending_transaction_rolls_it_back(tmp_path):
    state_dir = str(tmp_path)
    with history_db.connection_scope(state_dir):
        with history_db.open_db(state_dir) as conn:
            conn.execute(
                "INSERT INTO wake_epochs (ts, wake_interval_s) VALUES (?, ?)",
                ("2026-09-26T00:00:00Z", 60),
            )
            # deliberately not committed - the scope exit must roll it back

    with history_db.open_db(state_dir) as conn:
        row = conn.execute("SELECT COUNT(*) FROM wake_epochs").fetchone()
        assert row[0] == 0


def test_open_db_outside_a_scope_behaves_as_today(tmp_path):
    """test_backup-style: connect, write (writer commits), close, then a
    fresh open_db reads it back - exactly as before any scope existed"""
    state_dir = str(tmp_path)
    conn = history_db.connect(state_dir)
    history_db.record_device_health(conn, "2026-09-26T00:00:00Z", battery_mv=3700)
    conn.close()

    with history_db.open_db(state_dir) as conn2:
        row = conn2.execute("SELECT battery_mv FROM device_health").fetchone()
        assert row[0] == 3700


# --- schema once per database file identity ---------------------------------


def test_three_connects_run_init_schema_once_and_pragmas_every_time(tmp_path):
    state_dir = str(tmp_path)
    with efficiency_probe.count_db() as counts:
        conns = [history_db.connect(state_dir) for _ in range(3)]
    assert counts.init_schema == 1

    for conn in conns:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        conn.close()


def test_recreated_empty_file_at_same_path_reruns_schema(tmp_path):
    """covers inode reuse: a deleted-and-recreated history.db is always
    empty at connect time, so the schema always runs again there even if
    the OS happened to hand back a previously-seen (device, inode) pair"""
    state_dir = str(tmp_path)
    conn = history_db.connect(state_dir)
    conn.close()

    db_path = history_db.history_db_path(state_dir)
    os.remove(db_path)
    for suffix in ("-wal", "-shm"):
        candidate = db_path + suffix
        if os.path.exists(candidate):
            os.remove(candidate)

    with efficiency_probe.count_db() as counts:
        conn2 = history_db.connect(state_dir)
    assert counts.init_schema == 1
    row = conn2.execute("SELECT COUNT(*) FROM meta").fetchone()
    assert row[0] == 0
    conn2.close()


def test_two_different_state_dirs_run_init_schema_once_each(tmp_path):
    dir1 = str(tmp_path / "a")
    dir2 = str(tmp_path / "b")
    with efficiency_probe.count_db() as counts:
        conn1 = history_db.connect(dir1)
        conn2 = history_db.connect(dir2)
    assert counts.init_schema == 2
    conn1.close()
    conn2.close()


# --- write_batch: one transaction, deferred writer commits -----------------


def test_write_batch_commits_once_for_multiple_writers(tmp_path):
    state_dir = str(tmp_path)
    with efficiency_probe.count_db() as counts:
        with history_db.open_db(state_dir) as conn:
            with history_db.write_batch(conn):
                history_db.record_runway_event(
                    conn, hex="39a1b2", corroborated=True, confirmed_state="departure",
                )
                history_db.set_meta(conn, "batch-key", "batch-value")
                history_db.record_device_health(conn, "2026-09-26T00:00:00Z", battery_mv=3700)
    assert counts.commits == 1

    with history_db.open_db(state_dir) as conn2:
        assert conn2.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0] == 1
        assert conn2.execute("SELECT COUNT(*) FROM device_health").fetchone()[0] == 1
        assert history_db.get_meta(conn2, "batch-key") == "batch-value"


def test_write_batch_exception_rolls_back_and_reraises(tmp_path):
    class Boom(Exception):
        pass

    state_dir = str(tmp_path)
    with history_db.open_db(state_dir) as conn:
        with pytest.raises(Boom):
            with history_db.write_batch(conn):
                history_db.set_meta(conn, "rollback-key", "rollback-value")
                raise Boom("mid-batch failure")

    with history_db.open_db(state_dir) as conn2:
        assert history_db.get_meta(conn2, "rollback-key") is None


def test_set_meta_outside_batch_is_visible_from_a_second_connection_immediately(tmp_path):
    state_dir = str(tmp_path)
    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(conn, "immediate-key", "immediate-value")
        with history_db.open_db(state_dir) as conn2:
            assert history_db.get_meta(conn2, "immediate-key") == "immediate-value"


def _caddy_log_line(uri, ts, headers):
    """One Caddy JSON access-log line, matching
    server/test_caddy_tail.py's own helper of the same name."""
    entry = {
        "ts": ts,
        "logger": "http.log.access",
        "msg": "handled request",
        "request": {"method": "GET", "uri": uri, "headers": headers},
        "status": 200,
    }
    return json.dumps(entry)


def test_ingest_caddy_battery_log_inside_write_batch_commits_once(tmp_path):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    log_path = os.path.join(state_dir, "caddy-access.log")
    lines = [
        _caddy_log_line("/device/v1/display", "2026-09-26T00:00:00Z", {"X-Battery-Mv": ["3700"]}),
        _caddy_log_line("/device/v1/display", "2026-09-26T00:01:00Z", {"X-Battery-Mv": ["3690"]}),
    ]
    with open(log_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    with efficiency_probe.count_db() as counts:
        with history_db.open_db(state_dir) as conn:
            with history_db.write_batch(conn):
                inserted = history_db.ingest_caddy_battery_log(conn, log_path)
    assert inserted == 2
    assert counts.commits == 1


def test_write_batch_on_a_plain_connection_still_commits_once(tmp_path):
    """write_batch()'s _batch_depth bookkeeping is read via getattr with a
    0 default and written back in a try/except AttributeError, precisely
    so a bare sqlite3.Connection - never opened through this module's
    connect() and therefore missing the attribute entirely - still works
    as a single-level batch instead of raising"""
    db_path = os.path.join(str(tmp_path), "plain.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t (v TEXT)")
    conn.commit()

    with history_db.write_batch(conn):
        conn.execute("INSERT INTO t (v) VALUES ('a')")
        conn.execute("INSERT INTO t (v) VALUES ('b')")

    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 2

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with history_db.write_batch(conn):
            conn.execute("INSERT INTO t (v) VALUES ('c')")
            raise Boom("mid-batch failure")

    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 2
    conn.close()
