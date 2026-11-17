"""The `poll_cycles` trace: which cycles are recorded, what a row holds, how
old rows are pruned, and how the read-only export copes with an older
database.

Every assertion reads history.db, never source text.
"""
import os
import sqlite3
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.history_db as history_db  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402

GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
CLOCK_BASE = 1_700_000_000.0
SINCE = "2000-01-01T00:00:00Z"


@pytest.fixture
def clock(monkeypatch):
    fake = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: fake["t"])
    return fake


def _snapshot(hex_code, callsign, baro_rate, alt=450):
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": 137.1, "baro_rate": baro_rate, "seen_pos": 1.0}]}


def _cycle(clock, state_dir, snapshot, advance_s=100):
    clock["t"] += advance_s
    poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)


def _rows(state_dir):
    columns = history_db.EXPORT_TABLES["poll_cycles"]
    return [dict(zip(columns, row))
            for row in history_db.export_table_rows(state_dir, "poll_cycles", SINCE, 1000)]


def test_a_cycle_that_saw_nothing_and_changed_nothing_is_not_recorded(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, {"ac": []})
    _cycle(clock, state_dir, {"ac": []})
    _cycle(clock, state_dir, {"ac": []})
    (first,) = _rows(state_dir)
    assert (first["branch"], first["render_state"], first["panel_changed"]) == ("empty", "empty", 1)


def test_a_detection_is_recorded_with_what_was_seen_and_what_was_drawn(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700, alt=450))
    (row,) = _rows(state_dir)
    assert (row["detected_hex"], row["detected_callsign"]) == ("aaaaaa", "EJU1LIN")
    assert (row["detected_altitude_ft"], row["detected_rate_fpm"]) == (450.0, -700.0)
    assert (row["shown_hex"], row["confirmed_state"], row["render_state"]) == (
        "aaaaaa", "arriving", "arriving")
    assert (row["branch"], row["panel_changed"], row["tracked_runway"]) == ("promoted", 1, "3")
    assert row["pending"] == 0 and row["dropped"] is None


def test_a_queued_aircraft_and_later_a_dropped_one_are_recorded(tmp_path, clock):
    state_dir = str(tmp_path)
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    _cycle(clock, state_dir, _snapshot("bbbbbb", "EJU2OPO", 1800, alt=900), advance_s=10)
    _cycle(clock, state_dir, {"ac": []}, advance_s=300)
    queued, dropped = _rows(state_dir)[1:]
    assert (queued["detected_hex"], queued["shown_hex"], queued["pending"]) == ("bbbbbb", "aaaaaa", 1)
    assert queued["pending_hexes"] == "bbbbbb"
    assert dropped["dropped"] == "bbbbbb" and dropped["detected_hex"] is None


def test_rows_older_than_the_retention_are_pruned_when_a_cycle_is_recorded(tmp_path, clock):
    state_dir = str(tmp_path)
    old = history_db.utc_now_iso()
    with history_db.open_db(state_dir) as conn:
        history_db.record_poll_cycle(conn, "2020-01-01T00:00:00+00:00", {"branch": "ancient"})
        history_db.record_poll_cycle(conn, old, {"branch": "fresh"})
    _cycle(clock, state_dir, _snapshot("aaaaaa", "EJU1LIN", -700))
    branches = [r["branch"] for r in _rows(state_dir)]
    assert "ancient" not in branches
    assert "fresh" in branches


def test_record_poll_cycle_ignores_unknown_keys_and_stores_booleans_as_numbers(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_poll_cycle(
            conn, "2026-11-15T10:00:00+00:00", {"branch": "held", "panel_changed": True, "bogus": 1})
        stored = [tuple(row) for row in conn.execute(
            "SELECT branch, panel_changed, redraw_blocked FROM poll_cycles")]
    assert stored == [("held", 1, None)]


def test_prune_leaves_everything_when_the_time_cannot_be_read(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_poll_cycle(conn, "2020-01-01T00:00:00+00:00", {"branch": "ancient"})
        assert history_db.prune_poll_cycles(conn, "not a time") == 0
        assert conn.execute("SELECT COUNT(*) FROM poll_cycles").fetchone()[0] == 1


def test_export_reads_a_database_from_before_the_trace_existed(tmp_path):
    path = history_db.history_db_path(str(tmp_path))
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE runway_events (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, hex TEXT, callsign TEXT)")
    conn.execute("INSERT INTO runway_events (ts, hex, callsign) VALUES ('2026-11-15T10:00:00+00:00', 'aaaaaa', 'X1')")
    conn.commit()
    conn.close()
    assert history_db.export_table_rows(str(tmp_path), "poll_cycles", SINCE, 10) == []
    (row,) = history_db.export_table_rows(str(tmp_path), "runway_events", SINCE, 10)
    columns = history_db.EXPORT_TABLES["runway_events"]
    stored = dict(zip(columns, row))
    assert (stored["hex"], stored["callsign"], stored["gallery_name"]) == ("aaaaaa", "X1", None)


def test_export_refuses_a_table_that_is_not_listed(tmp_path):
    history_db.connect(str(tmp_path)).close()
    with pytest.raises(KeyError):
        history_db.export_table_rows(str(tmp_path), "meta; DROP TABLE runway_events", SINCE, 10)


def test_export_refuses_to_truncate(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        for i in range(3):
            history_db.record_poll_cycle(conn, "2026-11-15T10:00:0%d+00:00" % i, {"branch": "held"})
    with pytest.raises(history_db.TooManyRows):
        history_db.export_table_rows(str(tmp_path), "poll_cycles", SINCE, 2)
