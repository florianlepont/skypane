#!/usr/bin/env python3
"""Contract tests for server/history_db.py's connection scope, schema-once
file identity, and write batching -- the machinery that lets a whole
companion request or poll cycle share one connection and one COMMIT,
without changing any existing open_db()/connect() caller's signature or
behaviour outside a scope/batch.
"""
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
