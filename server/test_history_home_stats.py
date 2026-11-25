#!/usr/bin/env python3
"""Behaviour checks for the read-only aggregates behind Home's statistics card:
the per-hour timeline of one local day, the seven daily totals, and the most
seen and new airlines; zero-filled, in the frame's own time zone, scoped to the
one frame's database, and never writing."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.history_db as history_db  # noqa: E402

PARIS = "Europe/Paris"
# 14:30 in Paris (UTC+2 in September).
NOW = "2026-09-03T12:30:00+00:00"


def _seed(state_dir, rows):
    with history_db.open_db(state_dir) as conn:
        for index, (ts, state, airline) in enumerate(rows):
            history_db.record_runway_event(
                conn, ts=ts, hex="4b%04x" % index, callsign="AFR%d" % (100 + index),
                airline=airline, origin="ORY", destination="TLS",
                confirmed_state=state, corroborated=True)


def _read(state_dir, fn, *args, **kwargs):
    with history_db.open_db(state_dir) as conn:
        return fn(conn, *args, **kwargs)


def test_hourly_timeline_has_all_24_hours_in_the_frame_zone(tmp_path):
    """arrivals and departures are bucketed by the frame's local hour (22:30 UTC the day
    before is 00:30 in Paris), every hour of the day is present with zero when quiet, and
    a flight of another day is left out"""
    _seed(tmp_path, [
        ("2026-09-02T22:30:00+00:00", "departing", "Air France"),
        ("2026-09-03T05:10:00+00:00", "arriving", "Air France"),
        ("2026-09-03T05:50:00+00:00", "arriving", "Transavia"),
        ("2026-09-03T10:00:00+00:00", "departing", "Air France"),
        ("2026-09-02T21:00:00+00:00", "arriving", "Air France"),
    ])
    timeline = _read(tmp_path, history_db.home_day_timeline, PARIS, NOW)
    assert timeline["day"] == "2026-09-03"
    assert [h["hour"] for h in timeline["hours"]] == list(range(24))
    by_hour = {h["hour"]: (h["arriving"], h["departing"]) for h in timeline["hours"]}
    assert by_hour[0] == (0, 1)
    assert by_hour[7] == (2, 0)
    assert by_hour[12] == (0, 1)
    assert by_hour[3] == (0, 0)
    assert (timeline["arriving"], timeline["departing"]) == (2, 2)
    assert [round(t["at"], 2) for t in timeline["ticks"]] == [0.5, 7.17, 7.83, 12.0]


def test_a_pass_stored_twice_counts_once_and_other_states_are_left_out(tmp_path):
    """the same aircraft stored twice 30 s apart is one flight; an overhead row is neither
    an arrival nor a departure"""
    with history_db.open_db(tmp_path) as conn:
        for ts in ("2026-09-03T08:00:00+00:00", "2026-09-03T08:00:30+00:00"):
            history_db.record_runway_event(
                conn, ts=ts, hex="4b0001", callsign="AFR1", airline="Air France",
                origin="ORY", destination="TLS", confirmed_state="departing")
        history_db.record_runway_event(
            conn, ts="2026-09-03T09:00:00+00:00", hex="4b0002", callsign="AFR2",
            confirmed_state="overhead")
    timeline = _read(tmp_path, history_db.home_day_timeline, PARIS, NOW)
    assert (timeline["arriving"], timeline["departing"]) == (0, 1)


def test_week_totals_are_seven_zero_filled_days_ending_today(tmp_path):
    """exactly seven daily totals, oldest first, the last one today; days with no flight
    are zero and the arrival and departure split adds up"""
    _seed(tmp_path, [
        ("2026-09-03T08:00:00+00:00", "departing", "Air France"),
        ("2026-09-03T09:00:00+00:00", "arriving", "Air France"),
        ("2026-09-01T09:00:00+00:00", "arriving", "Air France"),
        ("2026-08-28T09:00:00+00:00", "arriving", "Air France"),
        ("2026-08-27T09:00:00+00:00", "arriving", "Air France"),
    ])
    week = _read(tmp_path, history_db.home_week_totals, PARIS, NOW)
    assert [d["day"] for d in week] == [
        "2026-08-28", "2026-08-29", "2026-08-30", "2026-08-31",
        "2026-09-01", "2026-09-02", "2026-09-03"]
    assert [d["total"] for d in week] == [1, 0, 0, 0, 1, 0, 2]
    assert (week[-1]["arriving"], week[-1]["departing"]) == (1, 1)


def test_empty_history_gives_zero_filled_results_not_errors(tmp_path):
    timeline = _read(tmp_path, history_db.home_day_timeline, PARIS, NOW)
    week = _read(tmp_path, history_db.home_week_totals, PARIS, NOW)
    highlights = _read(tmp_path, history_db.home_airline_highlights, PARIS, NOW)
    assert timeline["arriving"] == timeline["departing"] == 0 and timeline["ticks"] == []
    assert len(timeline["hours"]) == 24 and len(week) == 7
    assert highlights == {"most_seen": None, "new_airlines": []}


def test_most_seen_airline_breaks_ties_alphabetically_and_lists_new_ones(tmp_path):
    """the airline with the most flights wins, a tie goes to the alphabetically first name,
    and an airline with no row before the window is new"""
    _seed(tmp_path, [
        ("2026-08-01T09:00:00+00:00", "arriving", "Air France"),
        ("2026-09-02T09:00:00+00:00", "arriving", "Zeta Air"),
        ("2026-09-02T10:00:00+00:00", "departing", "Zeta Air"),
        ("2026-09-03T08:00:00+00:00", "departing", "Air France"),
        ("2026-09-03T09:00:00+00:00", "arriving", "Air France"),
        ("2026-09-03T10:00:00+00:00", "arriving", "Beta Jet"),
        ("2026-09-03T11:00:00+00:00", "arriving", None),
    ])
    result = _read(tmp_path, history_db.home_airline_highlights, PARIS, NOW)
    assert result["most_seen"] == {"airline": "Air France", "count": 2}
    assert result["new_airlines"] == ["Beta Jet", "Zeta Air"]


def test_owner_airline_names_apply_to_the_counts(tmp_path):
    _seed(tmp_path, [("2026-09-03T08:00:00+00:00", "departing", "Air France")])
    result = _read(
        tmp_path, history_db.home_airline_highlights, PARIS, NOW,
        airline_names={"AFR": "Ma compagnie"})
    assert result["most_seen"]["airline"] == "Ma compagnie"


def test_each_frame_reads_only_its_own_database(tmp_path):
    """the aggregates read the one history database they are given: another frame's
    state directory never leaks into the totals"""
    mine, other = tmp_path / "mine", tmp_path / "other"
    mine.mkdir()
    other.mkdir()
    _seed(str(mine), [("2026-09-03T08:00:00+00:00", "departing", "Air France")])
    _seed(str(other), [
        ("2026-09-03T08:00:00+00:00", "arriving", "Zeta Air"),
        ("2026-09-03T09:00:00+00:00", "arriving", "Zeta Air")])
    assert _read(str(mine), history_db.home_week_totals, PARIS, NOW)[-1]["total"] == 1
    assert _read(str(other), history_db.home_week_totals, PARIS, NOW)[-1]["total"] == 2


def test_the_aggregates_write_nothing(tmp_path):
    _seed(tmp_path, [("2026-09-03T08:00:00+00:00", "departing", "Air France")])
    with history_db.open_db(tmp_path) as conn:
        before = conn.total_changes
        history_db.home_day_timeline(conn, PARIS, NOW)
        history_db.home_week_totals(conn, PARIS, NOW)
        history_db.home_airline_highlights(conn, PARIS, NOW)
        assert conn.total_changes == before

