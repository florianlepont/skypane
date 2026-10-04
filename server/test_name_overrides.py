#!/usr/bin/env python3
"""Contract tests for server/plane/name_overrides.py - the owner's airline
name overrides. Every fixture is `tmp_path`."""
import json

import server.plane.manual_resolutions as manual_resolutions
import server.plane.name_overrides as no


def test_missing_or_malformed_file_loads_empty(tmp_path):
    """a missing file, invalid JSON, a non-dict top level and a falsy state
    dir all load as an empty registry"""
    assert no.load_name_overrides(str(tmp_path)) == {}
    assert no.load_name_overrides("") == {}
    path = no.name_overrides_path(str(tmp_path))
    for body in ("not json", "[1]"):
        with open(path, "w") as fh:
            fh.write(body)
        assert no.load_name_overrides(str(tmp_path)) == {}


def test_set_names_writes_every_prefix_atomically_and_reads_back(tmp_path):
    """one call stores the name for all of the airline's prefixes, and
    re-setting replaces rather than duplicates"""
    state = str(tmp_path)
    assert no.set_names(state, ["TVF", "TVJ"], "  Transavia ", now="t1") == no.SET_OK
    registry = no.load_name_overrides(state)
    assert registry == {
        "TVF": {"airline_name": "Transavia", "created_at": "t1"},
        "TVJ": {"airline_name": "Transavia", "created_at": "t1"},
    }
    assert no.set_names(state, ["TVF"], "Transavia FR", now="t2") == no.SET_OK
    assert no.name_for_prefix("TVF", no.load_name_overrides(state)) == "Transavia FR"
    assert no.name_for_prefix("TVJ", no.load_name_overrides(state)) == "Transavia"


def test_set_names_rejections_write_nothing(tmp_path):
    """empty, too long, reserved, unusable names and bad prefixes are all
    refused with the shared reason codes and leave no file behind"""
    state = str(tmp_path)
    cases = [
        (["AFR"], "", manual_resolutions.ADD_REJECTED_NAME_EMPTY),
        (["AFR"], "   ", manual_resolutions.ADD_REJECTED_NAME_EMPTY),
        (["AFR"], "x" * 101, manual_resolutions.ADD_REJECTED_NAME_TOO_LONG),
        (["AFR"], "Generic Fallback", manual_resolutions.ADD_REJECTED_NAME_RESERVED),
        (["AFR"], "../../etc/passwd", manual_resolutions.ADD_REJECTED_NAME_EMPTY),
        (["AFR"], "!!!", manual_resolutions.ADD_REJECTED_NAME_EMPTY),
        ([], "Name", manual_resolutions.ADD_REJECTED_PREFIX),
        (["A1"], "Name", manual_resolutions.ADD_REJECTED_PREFIX),
    ]
    for prefixes, name, expected in cases:
        assert no.set_names(state, prefixes, name) == expected, (prefixes, name)
    assert no.load_name_overrides(state) == {}


def test_set_names_refuses_past_the_cap_but_allows_replacing(tmp_path, monkeypatch):
    """at the registry cap a new prefix is refused (no eviction) while an
    existing prefix can still be renamed"""
    state = str(tmp_path)
    monkeypatch.setattr(manual_resolutions, "MANUAL_RESOLUTION_MAX_ENTRIES", 2)
    assert no.set_names(state, ["AAA", "BBB"], "One") == no.SET_OK
    assert no.set_names(state, ["CCC"], "Two") == manual_resolutions.ADD_REJECTED_FULL
    assert no.set_names(state, ["BBB"], "Three") == no.SET_OK
    assert no.name_for_prefix("BBB", no.load_name_overrides(state)) == "Three"


def test_set_names_reports_a_write_failure(tmp_path):
    """an unwritable state dir yields ADD_FAILED, never an exception"""
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert no.set_names(str(blocker / "sub"), ["AFR"], "Name") == manual_resolutions.ADD_FAILED


def test_clear_names_removes_only_the_named_prefixes_and_is_idempotent(tmp_path):
    """clearing returns the registry to the other prefixes and tolerates a
    prefix that was never set"""
    state = str(tmp_path)
    no.set_names(state, ["AFR", "TVF"], "Name")
    assert no.clear_names(state, ["AFR", "ZZZ"]) is True
    assert list(no.load_name_overrides(state)) == ["TVF"]
    assert no.clear_names(state, ["AFR"]) is True
    assert no.clear_names(state, ["TVF"]) is True
    with open(no.name_overrides_path(state)) as fh:
        assert json.load(fh) == {}


def test_a_hand_edited_unsafe_name_is_dropped_on_load(tmp_path):
    """the loader re-applies the manual-resolution allowlist, so a
    path-shaped name in the file never reaches enrichment"""
    path = no.name_overrides_path(str(tmp_path))
    with open(path, "w") as fh:
        json.dump({"AFR": {"airline_name": "../x", "created_at": "t"},
                   "TVF": {"airline_name": "Fine", "created_at": "t"}}, fh)
    assert list(no.load_name_overrides(str(tmp_path))) == ["TVF"]


def _seed(tmp_path, rows):
    from server import history_db
    with history_db.open_db(str(tmp_path)) as conn:
        for ts, callsign, airline in rows:
            history_db.record_runway_event(
                conn, ts=ts, hex="abc", callsign=callsign, aircraft_type="A320",
                confirmed_state="departing", corroborated=True, route_source="fresh_hit",
                airline=airline, origin="ORY", destination="NCE", tracked_runway="3")


def test_stored_flights_read_under_the_override_and_reset_restores_them(tmp_path):
    """rows of a renamed prefix read back under the owner's name without being rewritten;
    other prefixes are untouched; removing the override returns every row's original name"""
    from server import history_db
    _seed(tmp_path, [
        ("2026-01-01T10:00:00+00:00", "TVF16VB", "Transavia France"),
        ("2026-01-01T10:01:00+00:00", "AFR123", "Air France"),
        ("2026-01-01T10:02:00+00:00", "tvf99", "Transavia (adsbdb)"),
        ("2026-01-01T10:03:00+00:00", None, "No Callsign Air"),
    ])
    state = str(tmp_path)
    no.set_names(state, ["TVF", "TFV"], "Transavia")
    names = no.names_by_prefix(no.load_name_overrides(state))
    with history_db.open_db(state) as conn:
        renamed = {r["callsign"]: r["airline"] for r in history_db.recent_runway_events(conn, airline_names=names)}
        raw = {r["callsign"]: r["airline"] for r in history_db.recent_runway_events(conn)}
    assert renamed["TVF16VB"] == "Transavia" and renamed["tvf99"] == "Transavia"
    assert renamed["AFR123"] == "Air France" and renamed[None] == "No Callsign Air"
    assert raw["TVF16VB"] == "Transavia France" and raw["tvf99"] == "Transavia (adsbdb)"
    no.clear_names(state, ["TVF", "TFV"])
    with history_db.open_db(state) as conn:
        again = {r["callsign"]: r["airline"] for r in history_db.recent_runway_events(
            conn, airline_names=no.names_by_prefix(no.load_name_overrides(state)))}
    assert again == raw


def test_reading_with_overrides_on_an_empty_history_is_empty(tmp_path):
    """no rows, no overrides and a non-registry value all read without error"""
    from server import history_db
    with history_db.open_db(str(tmp_path)) as conn:
        assert history_db.recent_runway_events(conn, airline_names={"AFR": "X"}) == []
    assert no.names_by_prefix(None) == {} and no.names_by_prefix({"AFR": 3}) == {}
