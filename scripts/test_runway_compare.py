"""Tests for scripts/runway_compare.py: one test per internal-consistency class.

Fixtures are small synthetic JSON Lines files written to tmp_path.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import runway_compare  # noqa: E402


def _event(ts, hex_, state, callsign="AAA1", origin="ORY", destination="NCE"):
    return {
        "ts": ts,
        "hex": hex_,
        "callsign": callsign,
        "confirmed_state": state,
        "origin": origin,
        "destination": destination,
    }


def _cycle(ts, hex_, state, rate, source="held", alt=1000.0):
    return {
        "ts": ts,
        "branch": source,
        "detected_hex": hex_,
        "detected_callsign": "CS" + str(hex_),
        "detected_altitude_ft": alt,
        "detected_rate_fpm": rate,
        "confirmed_state": state,
        "state_source": source,
    }


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _run(tmp_path, events, cycles):
    _write(tmp_path / "runway_events.jsonl", events)
    _write(tmp_path / "poll_cycles.jsonl", cycles)
    return runway_compare.analyse(str(tmp_path))


def test_held_carry_over(tmp_path):
    cycles = [
        _cycle("2026-11-15T12:00:00+00:00", "A", "arriving", -800.0, "inferred"),
        _cycle("2026-11-15T12:00:30+00:00", "B", "arriving", None, "held"),
    ]
    report = _run(tmp_path, [], cycles)
    rows = report["classes"]["held-carry-over"]["rows"]
    assert report["classes"]["held-carry-over"]["count"] == 1
    assert rows[0]["hex"] == "B"


def test_held_same_aircraft_is_not_carry_over(tmp_path):
    cycles = [
        _cycle("2026-11-15T12:00:00+00:00", "A", "arriving", -800.0, "inferred"),
        _cycle("2026-11-15T12:00:30+00:00", "A", "arriving", None, "held"),
    ]
    report = _run(tmp_path, [], cycles)
    assert report["classes"]["held-carry-over"]["count"] == 0


def test_state_contradiction(tmp_path):
    events = [
        _event("2026-11-15T12:00:10+00:00", "A", "departing"),
        _event("2026-11-15T12:05:10+00:00", "C", "arriving"),
        _event("2026-11-15T12:10:10+00:00", "D", "departing"),
    ]
    cycles = [
        _cycle("2026-11-15T12:00:00+00:00", "A", "departing", -900.0),
        _cycle("2026-11-15T12:05:00+00:00", "C", "arriving", 900.0),
        _cycle("2026-11-15T12:10:00+00:00", "D", "departing", 900.0),
    ]
    report = _run(tmp_path, events, cycles)
    found = report["classes"]["state-contradiction"]
    assert found["count"] == 2
    assert {row["hex"] for row in found["rows"]} == {"A", "C"}


def test_state_contradiction_not_testable_outside_coverage(tmp_path):
    events = [_event("2026-11-01T05:00:00+00:00", "A", "departing")]
    cycles = [_cycle("2026-11-15T12:00:00+00:00", "Z", "arriving", -800.0)]
    report = _run(tmp_path, events, cycles)
    found = report["classes"]["state-contradiction"]
    assert found["count"] == 0
    assert found["not_testable"] == 1
    assert report["coverage"]["poll_cycles"]["rows"] == 1
    assert report["coverage"]["poll_cycles"]["first"] == "2026-11-15T12:00:00+00:00"


def test_stateless(tmp_path):
    events = [
        _event("2026-11-02T05:00:00+00:00", "A", None),
        _event("2026-11-02T05:01:00+00:00", "B", "departing"),
    ]
    report = _run(tmp_path, events, [])
    assert report["classes"]["stateless"]["count"] == 1
    assert report["per_day"]["2026-11-02"] == {
        "departing": 1,
        "arriving": 0,
        "stateless": 1,
    }


def test_rotating_route(tmp_path):
    events = [
        _event("2026-11-02T05:00:00+00:00", "A", "departing", "XYZ1", "ORY", "NCE"),
        _event("2026-11-02T09:00:00+00:00", "B", "departing", "XYZ1", "ORY", "LYS"),
        _event("2026-11-03T05:00:00+00:00", "A", "departing", "STB1", "ORY", "NCE"),
        _event("2026-11-04T05:00:00+00:00", "A", "departing", "STB1", "ORY", "LYS"),
    ]
    report = _run(tmp_path, events, [])
    found = report["classes"]["rotating-route"]
    assert found["count"] == 1
    assert found["rows"][0]["callsign"] == "XYZ1"


def test_no_route(tmp_path):
    events = [
        _event("2026-11-%02dT05:00:00+00:00" % day, "A", "departing", "NOR1", "", "")
        for day in range(1, 5)
    ] + [
        _event("2026-11-01T05:00:00+00:00", "B", "departing", "OK1", "ORY", "NCE"),
    ]
    report = _run(tmp_path, events, [])
    found = report["classes"]["no-route"]
    assert found["not_testable"] is True
    report = runway_compare.analyse(str(tmp_path), no_route_min_days=3)
    found = report["classes"]["no-route"]
    assert found["not_testable"] is False
    assert found["count"] == 1
    assert found["rows"][0]["callsign"] == "NOR1"


def test_flip_flop(tmp_path):
    events = [
        _event("2026-11-02T05:00:00+00:00", "A", "departing"),
        _event("2026-11-02T05:05:00+00:00", "A", "arriving"),
        _event("2026-11-02T06:00:00+00:00", "B", "departing"),
        _event("2026-11-02T08:00:00+00:00", "B", "arriving"),
    ]
    report = _run(tmp_path, events, [])
    found = report["classes"]["flip-flop"]
    assert found["count"] == 1
    assert found["rows"][0]["hex"] == "A"


def test_thresholds_come_from_runway_config():
    from server.plane import runway_config

    assert runway_compare.CLIMB_THRESHOLD_FPM == runway_config.CLIMB_THRESHOLD_FPM
    assert runway_compare.DESCEND_THRESHOLD_FPM == runway_config.DESCEND_THRESHOLD_FPM


def test_route_direction_mismatch(tmp_path):
    events = [
        _event("2026-11-02T05:00:00+00:00", "A", "departing", "OK1", "ORY", "NCE"),
        _event("2026-11-02T06:00:00+00:00", "B", "departing", "BAD1", "DBV", "ORY"),
        _event("2026-11-02T07:00:00+00:00", "C", "arriving", "BAD2", "ORY", "NCE"),
        _event("2026-11-02T08:00:00+00:00", "D", "arriving", "OK2", "NCE", "ORY"),
        _event("2026-11-02T09:00:00+00:00", "E", "departing", "NOR", "", ""),
    ]
    report = _run(tmp_path, events, [])
    found = report["classes"]["route-direction-mismatch"]
    assert found["count"] == 2
    assert {row["callsign"] for row in found["rows"]} == {"BAD1", "BAD2"}


def test_pending_contradiction_is_reported_separately(tmp_path):
    cycles = [
        dict(_cycle("2026-11-15T12:00:00+00:00", "B", "departing", -900.0), shown_hex="A"),
        dict(_cycle("2026-11-15T12:00:30+00:00", "A", "departing", 900.0), shown_hex="A"),
    ]
    report = _run(tmp_path, [], cycles)
    assert report["supplementary"]["pending-rate-contradicts-shown-state"]["count"] == 1
