#!/usr/bin/env python3
"""Round-trip, compact-format, persist-if-changed and fail-open tests for
server/state_store.py: the single owner of poll_state.json and the
read-only reader of byos's battery_state.json.

Every assertion here is a return value, a write count, or a byte-for-byte
file comparison - never source text.
"""
import json
import os

import pytest

import server.atomic_io as atomic_io
import server.device_policy as device_policy
import server.state_store as state_store


# --- load_poll_state: fail-open on every malformed shape --------------


def test_load_poll_state_missing_file_returns_empty_dict(tmp_path):
    got = state_store.load_poll_state(str(tmp_path))
    if got != {}:
        pytest.fail("load_poll_state() on a missing file returned %r, expected {}" % (got,))


def test_load_poll_state_invalid_json_returns_empty_dict(tmp_path):
    path = state_store.poll_state_path(str(tmp_path))
    with open(path, "w") as fh:
        fh.write("{not valid json")
    got = state_store.load_poll_state(str(tmp_path))
    if got != {}:
        pytest.fail("load_poll_state() on invalid JSON returned %r, expected {}" % (got,))


def test_load_poll_state_json_list_returns_empty_dict(tmp_path):
    path = state_store.poll_state_path(str(tmp_path))
    with open(path, "w") as fh:
        json.dump([1, 2, 3], fh)
    got = state_store.load_poll_state(str(tmp_path))
    if got != {}:
        pytest.fail("load_poll_state() on a JSON list returned %r, expected {}" % (got,))


def test_load_poll_state_directory_at_path_returns_empty_dict(tmp_path):
    path = state_store.poll_state_path(str(tmp_path))
    os.makedirs(path)
    got = state_store.load_poll_state(str(tmp_path))
    if got != {}:
        pytest.fail("load_poll_state() with a directory at the path returned %r, expected {}" % (got,))


def test_load_poll_state_returns_the_dict_otherwise(tmp_path):
    path = state_store.poll_state_path(str(tmp_path))
    with open(path, "w") as fh:
        json.dump({"pending_flights": [], "current": None}, fh)
    got = state_store.load_poll_state(str(tmp_path))
    if got != {"pending_flights": [], "current": None}:
        pytest.fail("load_poll_state() on a valid file returned %r" % (got,))


# --- serialize_poll_state: byte-identical to the historical compact format -


# Computed once against poll_loop's now-deleted _serialize_poll_state()
# copy and hard-coded here as a literal - the sole expectation, now that
# poll_loop itself has no copy left to compare against.
_REPRESENTATIVE_STATE = {
    "pending_flights": [],
    "battery_low_active": False,
    "current": {"hex": "39a1b2", "flight": "AFR123", "airline": "Aéroports de Paris"},
    "hold_state": None,
}
_REPRESENTATIVE_STATE_JSON = (
    '{"pending_flights":[],"battery_low_active":false,'
    '"current":{"hex":"39a1b2","flight":"AFR123","airline":"A\\u00e9roports de Paris"},'
    '"hold_state":null}'
)


def test_serialize_poll_state_matches_the_literal():
    got = state_store.serialize_poll_state(_REPRESENTATIVE_STATE)
    if got != _REPRESENTATIVE_STATE_JSON:
        pytest.fail("state_store.serialize_poll_state() returned %r, expected the literal %r" % (
            got, _REPRESENTATIVE_STATE_JSON))


# --- save_poll_state: round-trips, writes through atomic_io exactly once


def test_save_poll_state_round_trips_and_writes_through_atomic_io_once(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    state = {"a": 1, "b": [1, 2, 3]}

    calls = []
    real_atomic_write = atomic_io.atomic_write

    def spying_atomic_write(path, data, mode=None):
        calls.append(path)
        return real_atomic_write(path, data, mode=mode)

    monkeypatch.setattr(atomic_io, "atomic_write", spying_atomic_write)

    state_store.save_poll_state(state_dir, state)

    if len(calls) != 1:
        pytest.fail("save_poll_state() called atomic_io.atomic_write %d times, expected 1" % len(calls))
    got = state_store.load_poll_state(state_dir)
    if got != state:
        pytest.fail("save_poll_state() then load_poll_state() round-tripped to %r, expected %r" % (got, state))


# --- persist_poll_state_if_changed: 0 writes unchanged, 1 writes changed


def test_persist_poll_state_if_changed_writes_zero_when_unchanged(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    poll_state = {"a": 1}
    baseline = state_store.serialize_poll_state(poll_state)

    calls = []
    monkeypatch.setattr(atomic_io, "atomic_write", lambda *a, **k: calls.append(a))

    got = state_store.persist_poll_state_if_changed(state_dir, poll_state, baseline)

    if len(calls) != 0:
        pytest.fail("persist_poll_state_if_changed() on an unchanged state wrote %d times, expected 0" % len(calls))
    if got is not None:
        pytest.fail("persist_poll_state_if_changed() returned %r, expected None" % (got,))


def test_persist_poll_state_if_changed_writes_once_when_changed(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    baseline = state_store.serialize_poll_state({"a": 1})
    poll_state = {"a": 2}

    calls = []
    real_atomic_write = atomic_io.atomic_write

    def spying_atomic_write(path, data, mode=None):
        calls.append(path)
        return real_atomic_write(path, data, mode=mode)

    monkeypatch.setattr(atomic_io, "atomic_write", spying_atomic_write)

    got = state_store.persist_poll_state_if_changed(state_dir, poll_state, baseline)

    if len(calls) != 1:
        pytest.fail("persist_poll_state_if_changed() on a changed state wrote %d times, expected 1" % len(calls))
    if got is not None:
        pytest.fail("persist_poll_state_if_changed() returned %r, expected None" % (got,))
    on_disk = state_store.load_poll_state(state_dir)
    if on_disk != poll_state:
        pytest.fail("persist_poll_state_if_changed() left %r on disk, expected %r" % (on_disk, poll_state))


# --- hold_state ----------------------------------------------------------


def test_hold_state_reads_the_hold_state_key():
    if state_store.hold_state({"hold_state": "display_off"}) != "display_off":
        pytest.fail("hold_state({'hold_state': 'display_off'}) did not return 'display_off'")


def test_hold_state_unknown_kind_returns_none():
    if state_store.hold_state({"hold_state": "not-a-real-kind"}) is not None:
        pytest.fail("hold_state() with an unknown kind did not return None")


def test_hold_state_legacy_quiet_hours_active_without_hold_state():
    if state_store.hold_state({"quiet_hours_active": True}) != "quiet_hours":
        pytest.fail("hold_state({'quiet_hours_active': True}) did not return 'quiet_hours'")
    if state_store.hold_state({}) is not None:
        pytest.fail("hold_state({}) did not return None")


# --- load_battery_state ----------------------------------------------------


def test_load_battery_state_valid_int_returns_int(tmp_path):
    path = os.path.join(str(tmp_path), state_store.BATTERY_STATE_FILENAME)
    with open(path, "w") as fh:
        json.dump({"battery_mv": 3700}, fh)
    got = state_store.load_battery_state(str(tmp_path))
    if got != 3700:
        pytest.fail("load_battery_state() with battery_mv=3700 returned %r" % (got,))


def test_load_battery_state_rejects_hostile_shapes(tmp_path):
    cases = (
        {"battery_mv": True},
        {"battery_mv": 0},
        {"battery_mv": -5},
        {"battery_mv": "3700"},
        [1, 2, 3],
    )
    for i, payload in enumerate(cases):
        state_dir = str(tmp_path / ("case-%d" % i))
        os.makedirs(state_dir, exist_ok=True)
        path = os.path.join(state_dir, state_store.BATTERY_STATE_FILENAME)
        with open(path, "w") as fh:
            json.dump(payload, fh)
        got = state_store.load_battery_state(state_dir)
        if got is not None:
            pytest.fail("load_battery_state() with payload %r returned %r, expected None" % (payload, got))


def test_load_battery_state_missing_file_returns_none(tmp_path):
    got = state_store.load_battery_state(str(tmp_path))
    if got is not None:
        pytest.fail("load_battery_state() on a missing file returned %r, expected None" % (got,))


# --- read_battery_critical --------------------------------------------


def test_read_battery_critical_true_only_when_key_is_literally_true(tmp_path):
    path = state_store.poll_state_path(str(tmp_path))
    with open(path, "w") as fh:
        json.dump({device_policy.BATTERY_CRITICAL_STATE_KEY: True}, fh)
    if state_store.read_battery_critical(str(tmp_path)) is not True:
        pytest.fail("read_battery_critical() with the key literally True did not return True")


def test_read_battery_critical_fails_open_to_false(tmp_path):
    missing_dir = str(tmp_path / "missing")
    if state_store.read_battery_critical(missing_dir) is not False:
        pytest.fail("read_battery_critical() on a missing file did not return False")

    invalid_dir = str(tmp_path / "invalid")
    os.makedirs(invalid_dir, exist_ok=True)
    with open(state_store.poll_state_path(invalid_dir), "w") as fh:
        fh.write("{not valid json")
    if state_store.read_battery_critical(invalid_dir) is not False:
        pytest.fail("read_battery_critical() on invalid JSON did not return False")

    non_dict_dir = str(tmp_path / "non-dict")
    os.makedirs(non_dict_dir, exist_ok=True)
    with open(state_store.poll_state_path(non_dict_dir), "w") as fh:
        json.dump([1, 2, 3], fh)
    if state_store.read_battery_critical(non_dict_dir) is not False:
        pytest.fail("read_battery_critical() on a JSON list did not return False")

    string_true_dir = str(tmp_path / "string-true")
    os.makedirs(string_true_dir, exist_ok=True)
    with open(state_store.poll_state_path(string_true_dir), "w") as fh:
        json.dump({device_policy.BATTERY_CRITICAL_STATE_KEY: "true"}, fh)
    if state_store.read_battery_critical(string_true_dir) is not False:
        pytest.fail("read_battery_critical() with the key set to the string 'true' did not return False")


# --- DEFAULT_STATE_DIR -----------------------------------------------------


def test_default_state_dir_is_server_state():
    here = os.path.dirname(os.path.abspath(state_store.__file__))
    expected = os.path.join(here, "state")
    if state_store.DEFAULT_STATE_DIR != expected:
        pytest.fail("DEFAULT_STATE_DIR is %r, expected %r" % (state_store.DEFAULT_STATE_DIR, expected))
