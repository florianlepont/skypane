"""Self-tests for efficiency_probe.py: prove the PROBE MECHANICS work -
each counter counts what it says it counts and restores what it patches
- never today's inefficiency numbers. A later plan in this phase changes
those numbers; these tests must stay green before and after every one of
them.
"""
import os
import sqlite3
import threading
import time

import companion_app_server
import efficiency_probe

import server.atomic_io as atomic_io
import server.history_db as history_db
import server.plane.detect as detect


# --- count_db --------------------------------------------------------------


def test_count_db_counts_connection_init_schema_and_commit(tmp_path):
    with efficiency_probe.count_db() as counts:
        with history_db.open_db(str(tmp_path)) as conn:
            history_db.set_meta(conn, "probe-key", "probe-value")

    assert counts.connections == 1
    assert counts.init_schema >= 1
    assert counts.commits >= 1


def test_count_db_includes_a_second_thread(tmp_path):
    def worker():
        with history_db.open_db(str(tmp_path)) as conn:
            history_db.set_meta(conn, "worker-key", "worker-value")

    with efficiency_probe.count_db() as counts:
        with history_db.open_db(str(tmp_path)) as conn:
            history_db.set_meta(conn, "main-key", "main-value")
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

    assert counts.connections == 2
    assert len(counts.by_thread) == 2
    assert sum(counts.by_thread.values()) == 2


def test_count_db_restores_patched_attributes(tmp_path):
    original_connect = sqlite3.connect
    original_init_schema = history_db.init_schema

    with efficiency_probe.count_db():
        with history_db.open_db(str(tmp_path)) as conn:
            history_db.set_meta(conn, "k", "v")

    assert sqlite3.connect is original_connect
    assert history_db.init_schema is original_init_schema


# --- count_sleeps -----------------------------------------------------------


def test_count_sleeps_records_inside_and_not_outside():
    with efficiency_probe.count_sleeps() as calls:
        time.sleep(0)

    assert calls == [0]

    time.sleep(0)  # outside the block: must not be recorded

    assert calls == [0]


# --- count_poll_state_writes ------------------------------------------------


def test_count_poll_state_writes_counts_only_poll_state_json(tmp_path):
    import server.poll_loop as poll_loop

    with efficiency_probe.count_poll_state_writes() as writes:
        poll_loop.save_poll_state(str(tmp_path), {"a": 1})
        atomic_io.atomic_write(os.path.join(str(tmp_path), "other.json"), "{}")

    assert len(writes) == 1
    assert writes[0] > 0


# --- fake_provider_latency --------------------------------------------------


def test_fake_provider_latency_returns_records_and_logs():
    records = {"adsbfi": [{"hex": "abc123"}]}

    with efficiency_probe.fake_provider_latency(0.0, records) as calls:
        result = detect.query_provider("adsbfi", 48.72, 2.37, 5)

    assert result == [{"hex": "abc123"}]
    assert len(calls) == 1
    name, start, end, thread_name = calls[0]
    assert name == "adsbfi"
    assert end >= start
    assert thread_name == threading.current_thread().name


def test_fake_provider_latency_restores_query_provider():
    original = detect.query_provider

    with efficiency_probe.fake_provider_latency(0.0, {}):
        pass

    assert detect.query_provider is original


# --- route_weight ------------------------------------------------------


def test_route_weight_over_seeded_state(tmp_path):
    state_dir = str(tmp_path / "state")
    server = companion_app_server.InProcessAppServer(state_dir)
    try:
        cookie = companion_app_server.login(server)
        efficiency_probe.seed_history(state_dir, n=5)

        result = efficiency_probe.route_weight(server, "/", cookie=cookie, repeats=2)

        assert result["status"] == 200
        assert result["identity_bytes"] > result["gzip_bytes"] > 0
        assert result["script_srcs"]
        assert result["ms"] >= 0
    finally:
        server.stop()


# --- cycle_probe -------------------------------------------------------


def test_cycle_probe_returns_expected_keys(tmp_path, monkeypatch):
    # The one seam this task's convention allows monkeypatch for: without
    # it, an unpatched two-provider cycle would really sleep 1.1s here.
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)
    state_dir = str(tmp_path / "state")

    result = efficiency_probe.cycle_probe(state_dir, latency_s=0)

    assert set(result) == {
        "wall_s", "sleeps", "connections", "init_schema", "commits",
        "poll_state_writes", "poll_state_bytes", "state",
    }
    assert result["wall_s"] >= 0
    assert isinstance(result["sleeps"], list)
    assert isinstance(result["connections"], int)
