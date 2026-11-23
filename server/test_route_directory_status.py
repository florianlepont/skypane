"""Per-directory route lookup counters and the "answered by" mark.

Every assertion reads what the history database holds after a real poll
cycle (or what the enrichment seam returns), never source text. The
migration tests open databases laid out by the previous schema.
"""
import json
import os
import sqlite3
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.history_db as history_db  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402

GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")
CLOCK_BASE = 1_700_000_000.0
NOW_ISO = "2026-11-18T10:00:00+00:00"
LEG = ("arriving", frozenset({"ORY"}))


def _vrs_body(codes):
    return {
        "callsign": "X", "airline_code": "XXX",
        "_airport_codes_iata": "-".join(codes),
        "_airports": [
            {"name": c + " Airport", "iata": c, "icao": "X" + c, "location": c}
            for c in dict.fromkeys(codes)],
    }


def _adsbdb_body(callsign, origin, dest):
    def airport(iata):
        return {"iata_code": iata, "icao_code": "X" + iata, "municipality": iata, "name": iata}
    return {"response": {"flightroute": {
        "callsign": callsign, "callsign_icao": callsign, "callsign_iata": callsign,
        "airline": {"name": "easyJet Europe", "icao": callsign[:3], "iata": "XX", "country": "France"},
        "origin": airport(origin), "destination": airport(dest)}}}


def _transport(answer):
    """A fake transport: `answer` is a status, a `(status, body)` pair, or an
    exception to raise."""
    def call(_key, timeout=None):
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, tuple) else (answer, None)
    return call


def _resolve(cache, vrs, adsbdb, callsign="EJU1LIN"):
    report = enrich.LookupReport()
    route, source = enrich.resolve_route(
        callsign, cache, transport=_transport(adsbdb), vrs_transport=_transport(vrs),
        now=CLOCK_BASE, leg=LEG, report=report)
    return route, source, report


# --- the enrichment seam --------------------------------------------------


def test_each_request_is_reported_with_its_outcome_and_the_answering_directory():
    cache = {}
    _route, source, report = _resolve(cache, (200, _vrs_body(["LIN", "ORY"])), 404)
    assert (source, report.network, report.directory) == (
        "fresh_hit", [("vrs", "found")], "vrs")

    _route, source, report = _resolve({}, 404, (200, _adsbdb_body("EJU1LIN", "LIN", "ORY")))
    assert (source, report.network, report.directory) == (
        "fresh_hit", [("vrs", "none"), ("adsbdb", "found")], "adsbdb")


def test_a_definite_no_route_answer_is_counted_as_none_and_names_no_directory():
    _route, source, report = _resolve({}, 404, 404, callsign="ZZZ9999")
    assert source != "fresh_hit"
    assert report.network == [("vrs", "none"), ("adsbdb", "none")]
    assert report.directory is None


def test_a_failed_transient_lookup_is_counted_and_not_cached_as_a_miss():
    cache = {}
    _route, _source, report = _resolve(cache, OSError("down"), 503, callsign="EJU1LIN")
    assert report.network == [("vrs", "failed"), ("adsbdb", "failed")]
    assert cache == {}
    # The next call asks again, so a passing hiccup never becomes a miss.
    _route, _source, again = _resolve(cache, 429, 500, callsign="EJU1LIN")
    assert again.network == [("vrs", "failed"), ("adsbdb", "failed")]


def test_a_cached_answer_makes_no_request_and_still_names_its_directory():
    cache = {}
    _resolve(cache, (200, _vrs_body(["LIN", "ORY"])), 404)
    _route, source, report = _resolve(cache, OSError("down"), OSError("down"))
    assert (source, report.network, report.directory) == ("cache_hit", [], "vrs")


def test_reporting_does_not_change_what_resolve_route_returns():
    plain = enrich.resolve_route(
        "EJU1LIN", {}, transport=_transport(404), vrs_transport=_transport((200, _vrs_body(["LIN", "ORY"]))),
        now=CLOCK_BASE, leg=LEG)
    with_report = enrich.resolve_route(
        "EJU1LIN", {}, transport=_transport(404), vrs_transport=_transport((200, _vrs_body(["LIN", "ORY"]))),
        now=CLOCK_BASE, leg=LEG, report=enrich.LookupReport())
    assert plain == with_report


# --- the history database -------------------------------------------------


def test_counters_per_directory_and_the_last_answer_are_read_back(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_route_lookups(conn, "2026-11-18T08:00:00+00:00", [
            ("vrs", "found"), ("vrs", "none"), ("adsbdb", "found")])
        history_db.record_route_lookups(conn, "2026-11-18T09:00:00+00:00", [
            ("vrs", "failed"), ("adsbdb", "failed")])
        history_db.record_route_lookups(conn, "2026-11-18T09:30:00+00:00", [("bogus", "found"), ("vrs", "weird")])
        stats = history_db.route_directory_stats(conn, "2026-11-17T10:00:00+00:00")
    assert stats["vrs"] == {
        "lookups": 3, "found": 1, "failed": 1,
        "last_answer_ts": "2026-11-18T08:00:00+00:00", "reachable": False}
    assert stats["adsbdb"]["last_answer_ts"] == "2026-11-18T08:00:00+00:00"
    assert stats["adsbdb"]["reachable"] is False


def test_a_directory_never_asked_reads_as_unknown(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        stats = history_db.route_directory_stats(conn, "2026-11-17T10:00:00+00:00")
    assert stats["vrs"] == {
        "lookups": 0, "found": 0, "failed": 0, "last_answer_ts": None, "reachable": None}


def test_a_directory_whose_newest_request_was_answered_is_reachable(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_route_lookups(conn, "2026-11-18T08:00:00+00:00", [("vrs", "failed")])
        history_db.record_route_lookups(conn, "2026-11-18T08:05:00+00:00", [("vrs", "none")])
        stats = history_db.route_directory_stats(conn, "2026-11-17T10:00:00+00:00")
    assert stats["vrs"]["reachable"] is True
    assert stats["vrs"]["last_answer_ts"] == "2026-11-18T08:05:00+00:00"


def test_requests_older_than_the_window_are_not_counted_and_old_rows_are_pruned(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_route_lookups(conn, "2026-10-01T08:00:00+00:00", [("vrs", "found")])
        history_db.record_route_lookups(conn, "2026-11-18T08:00:00+00:00", [("vrs", "found")])
        stats = history_db.route_directory_stats(conn, "2026-11-17T10:00:00+00:00")
        deleted = history_db.prune_route_lookups(conn, NOW_ISO)
        left = conn.execute("SELECT COUNT(*) FROM route_lookups").fetchone()[0]
    assert stats["vrs"]["lookups"] == 1
    assert (deleted, left) == (1, 1)


def test_flights_are_counted_by_the_directory_that_answered(tmp_path):
    with history_db.open_db(str(tmp_path)) as conn:
        for directory in ("vrs", "vrs", "adsbdb", None):
            history_db.record_runway_event(conn, ts="2026-11-18T08:00:00+00:00", route_directory=directory)
        history_db.record_runway_event(conn, ts="2026-10-01T08:00:00+00:00", route_directory="vrs")
        counts = history_db.route_directory_counts(conn, "2026-11-11T10:00:00+00:00")
    assert counts == {"vrs": 2, "adsbdb": 1}


# --- migration of a database made by the previous schema ------------------

_OLD_SCHEMA = (
    "CREATE TABLE runway_events (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, hex TEXT, callsign TEXT, "
    "aircraft_type TEXT, confirmed_state TEXT, corroborated TEXT, route_source TEXT, airline TEXT, "
    "origin TEXT, destination TEXT, tracked_runway TEXT, gallery_name TEXT)",
    "CREATE TABLE device_health (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, battery_mv INTEGER, "
    "fw_version TEXT, boot_reason TEXT, rssi TEXT, UNIQUE(ts, battery_mv))",
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE wake_epochs (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, wake_interval_s INTEGER)",
)


def _previous_schema_database(state_dir):
    """A history.db as the previous release left it: user_version 0, no
    `route_lookups` table, no `runway_events.route_directory`, with rows."""
    os.makedirs(state_dir, exist_ok=True)
    path = history_db.history_db_path(state_dir)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    for statement in _OLD_SCHEMA:
        conn.execute(statement)
    conn.execute(
        "INSERT INTO runway_events (ts, hex, callsign, route_source, origin, destination, gallery_name) "
        "VALUES ('2026-11-01T08:00:00+00:00', 'abc123', 'AFR1000', 'cache_hit', 'LFMN', 'LFPO', 'g.png')")
    conn.execute("INSERT INTO device_health (ts, battery_mv) VALUES ('2026-11-01T08:00:00+00:00', 3900)")
    conn.execute("INSERT INTO meta VALUES ('k', 'v', '2026-11-01T08:00:00+00:00')")
    conn.commit()
    conn.close()
    return path


def _user_version(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


def test_a_database_of_the_previous_schema_is_migrated_without_losing_a_row(tmp_path):
    path = _previous_schema_database(str(tmp_path))
    assert _user_version(path) == 0
    with history_db.open_db(str(tmp_path)) as conn:
        row = conn.execute("SELECT callsign, origin, gallery_name, route_directory FROM runway_events").fetchone()
        health = conn.execute("SELECT battery_mv FROM device_health").fetchone()
        meta = conn.execute("SELECT value FROM meta WHERE key = 'k'").fetchone()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tuple(row) == ("AFR1000", "LFMN", "g.png", None)
    assert (health[0], meta[0]) == (3900, "v")
    assert "route_lookups" in tables
    assert _user_version(path) == history_db.HISTORY_SCHEMA_VERSION


def test_migrating_twice_changes_nothing(tmp_path):
    path = _previous_schema_database(str(tmp_path))
    conn = sqlite3.connect(path)
    history_db.init_schema(conn)
    before = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    history_db.init_schema(conn)
    after = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    rows = conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0]
    conn.close()
    assert before == after
    assert rows == 1
    assert _user_version(path) == history_db.HISTORY_SCHEMA_VERSION


def test_migration_runs_while_another_connection_reads_and_writes(tmp_path):
    """The poll oneshot may migrate while the companion holds a read
    transaction, and the companion may migrate right after the oneshot."""
    path = _previous_schema_database(str(tmp_path))
    reader = sqlite3.connect(path)
    reader.execute("BEGIN")
    reader.execute("SELECT COUNT(*) FROM runway_events").fetchone()
    try:
        with history_db.open_db(str(tmp_path)) as conn:
            history_db.record_route_lookups(conn, NOW_ISO, [("vrs", "found")])
    finally:
        reader.close()
    other = sqlite3.connect(path)
    history_db.init_schema(other)
    count = other.execute("SELECT COUNT(*) FROM route_lookups").fetchone()[0]
    other.close()
    assert count == 1


def test_a_snapshot_taken_before_the_migration_opens_and_migrates(tmp_path):
    """A restore from a backup made by the previous release."""
    source = _previous_schema_database(str(tmp_path / "live"))
    restored_dir = str(tmp_path / "restored")
    os.makedirs(restored_dir)
    snapshot = sqlite3.connect(os.path.join(restored_dir, history_db.HISTORY_DB_FILENAME))
    live = sqlite3.connect(source)
    live.backup(snapshot)
    live.close()
    snapshot.close()
    with history_db.open_db(restored_dir) as conn:
        count = conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0]
    assert count == 1
    assert _user_version(os.path.join(restored_dir, history_db.HISTORY_DB_FILENAME)) == history_db.HISTORY_SCHEMA_VERSION


def test_the_previous_release_can_still_write_to_a_migrated_database(tmp_path):
    """A rollback of the code leaves the migrated file usable: the old
    insert names its columns, so the new column and table stay out of it."""
    _previous_schema_database(str(tmp_path))
    with history_db.open_db(str(tmp_path)):
        pass
    conn = sqlite3.connect(history_db.history_db_path(str(tmp_path)))
    conn.execute(
        "INSERT INTO runway_events (ts, hex, callsign, aircraft_type, confirmed_state, corroborated, "
        "route_source, airline, origin, destination, tracked_runway, gallery_name) "
        "VALUES ('2026-11-02T08:00:00+00:00', 'x', 'Y', 'A320', 'arriving', 'True', 'miss', NULL, NULL, NULL, '3', '')")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0] == 2
    conn.close()


# --- the poll cycle -------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    fake = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_cycle, "now_s", lambda: fake["t"])
    return fake


@pytest.fixture
def directories(monkeypatch):
    """Both directories, each answering `status`/`(status, body)` or raising."""
    state = {"vrs": 404, "adsbdb": 404, "vrs_calls": 0, "adsbdb_calls": 0}

    def make(name):
        def call(_key, timeout=None):
            state[name + "_calls"] += 1
            answer = state[name]
            if isinstance(answer, Exception):
                raise answer
            return answer if isinstance(answer, tuple) else (answer, None)
        return call

    monkeypatch.setattr(enrich, "default_vrs_transport", make("vrs"))
    monkeypatch.setattr(enrich, "default_transport", make("adsbdb"))
    return state


def _snapshot(hex_code, callsign, baro_rate, alt=450):
    return {"ac": [{
        "hex": hex_code, "flight": callsign, "lat": 48.7233, "lon": 2.3794,
        "alt_baro": alt, "gs": 137.1, "baro_rate": baro_rate, "seen_pos": 1.0}]}


def _run(clock, state_dir, snapshot):
    clock["t"] += 100
    return poll_cycle.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)


def _lookups(state_dir):
    with history_db.open_db(state_dir) as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT directory, outcome FROM route_lookups ORDER BY id")]


def _events(state_dir):
    with history_db.open_db(state_dir) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM runway_events ORDER BY id")]


def _cache(state_dir):
    with open(os.path.join(state_dir, "poll_state.json")) as fh:
        return json.load(fh).get("enrichment_cache", {})


def test_a_cycle_counts_each_request_and_marks_the_flight_with_its_directory(tmp_path, clock, directories):
    directories["vrs"] = (200, _vrs_body(["LIN", "ORY"]))
    _run(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    assert _lookups(str(tmp_path)) == [("vrs", "found")]
    (event,) = _events(str(tmp_path))
    assert (event["route_source"], event["route_directory"]) == ("fresh_hit", "vrs")


def test_a_flight_answered_by_the_fallback_is_marked_adsbdb(tmp_path, clock, directories):
    directories["adsbdb"] = (200, _adsbdb_body("EJU1LIN", "LIN", "ORY"))
    _run(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    assert _lookups(str(tmp_path)) == [("vrs", "none"), ("adsbdb", "found")]
    assert _events(str(tmp_path))[0]["route_directory"] == "adsbdb"


def test_a_cached_route_makes_no_new_counter_row_but_keeps_its_mark(tmp_path, clock, directories):
    directories["vrs"] = (200, _vrs_body(["LIN", "ORY"]))
    _run(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    clock["t"] += 400
    _run(clock, str(tmp_path), _snapshot("bbbbbb", "EJU1LIN", -700))
    assert _lookups(str(tmp_path)) == [("vrs", "found")]
    assert [e["route_directory"] for e in _events(str(tmp_path))] == ["vrs", "vrs"]


def test_with_both_directories_failing_the_cycle_completes_and_nothing_is_cached(tmp_path, clock, directories):
    directories["vrs"] = OSError("down")
    directories["adsbdb"] = 503
    result = _run(clock, str(tmp_path), _snapshot("aaaaaa", "EJU1LIN", -700))
    assert result["flight"] is not None
    assert _lookups(str(tmp_path)) == [("vrs", "failed"), ("adsbdb", "failed")]
    assert _cache(str(tmp_path)) == {}
    (event,) = _events(str(tmp_path))
    assert event["route_directory"] is None
    # The next aircraft with that callsign asks again.
    _run(clock, str(tmp_path), _snapshot("bbbbbb", "EJU1LIN", -700))
    assert directories["vrs_calls"] == 2 and directories["adsbdb_calls"] == 2


def test_the_cycle_output_does_not_depend_on_the_counters(tmp_path, clock, directories):
    """Same inputs, one run with a counter table that cannot be written: the
    cycle returns the same result."""
    directories["vrs"] = (200, _vrs_body(["LIN", "ORY"]))
    first = _run(clock, str(tmp_path / "a"), _snapshot("aaaaaa", "EJU1LIN", -700))
    os.makedirs(str(tmp_path / "b"))
    with history_db.open_db(str(tmp_path / "b")) as db:
        db.execute("DROP TABLE route_lookups")
        db.execute("CREATE VIEW route_lookups AS SELECT 1 AS ts, 1 AS directory, 1 AS outcome")
    history_db._SCHEMA_READY.clear()
    clock["t"] = CLOCK_BASE
    second = _run(clock, str(tmp_path / "b"), _snapshot("aaaaaa", "EJU1LIN", -700))
    assert first == second
