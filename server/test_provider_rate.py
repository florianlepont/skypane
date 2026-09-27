#!/usr/bin/env python3
"""Behaviour tests for keeping each ADS-B provider's own rate limit across
back-to-back poll cycles (and processes), now that the old fixed
inter-provider sleep is gone.

Covers `server/history_db.py`'s `META_PROVIDER_LAST_CALL_PREFIX` and
`server/poll_cycle.py`'s `_load_provider_last_calls()`/`_record_history()`
wiring:

  * two cycles run back to back never call the same provider twice within
    its own `MIN_SECONDS_BETWEEN_CALLS`
  * the per-provider last-call times persist in `history.db` meta as float
    epoch strings, read back and honoured by a later, otherwise unrelated
    cycle - no in-process structure is carried between the two calls
  * a cycle with no prior meta sleeps zero times, and still opens exactly
    one connection and commits exactly once
  * an unparsable stored value is treated as no previous call - no
    exception, no sleep
  * a hold cycle and an injected-snapshot cycle neither read nor write the
    provider meta keys
  * a history-write failure (the existing catch in `_record_history()`)
    still does not raise out of the cycle with provider last-call times
    present

Every spacing assertion compares two recorded `time.time()` timestamps
(`efficiency_probe.fake_provider_latency()`'s own call log) against each
other, never against a fixed wall-clock duration of the test itself.
"""
import os
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# `pytest` invocation; inserted here too so this file also works under the
# legacy direct-execution bridge other server/test_*.py modules support.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import efficiency_probe  # noqa: E402

import server.device_config as device_config  # noqa: E402
import server.history_db as history_db  # noqa: E402
import server.plane.detect as detect  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402

pytestmark = pytest.mark.slow


def _empty_snapshot():
    """No aircraft detected this cycle - the injected-snapshot path."""
    return {"ac": []}


def _meta_value(state_dir, key):
    with history_db.open_db(state_dir) as conn:
        return history_db.get_meta(conn, key)


@pytest.fixture(autouse=True)
def _stub_adsbdb(monkeypatch):
    """No test in this module needs a real adsbdb route lookup - every
    cycle here sees an empty sky (no candidate ever reaches
    enrich.resolve_route)."""
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


@pytest.fixture(autouse=True)
def _zero_provider_spacing(monkeypatch):
    """Same convention as the repo's `fake_providers` fixture
    (conftest.py): most tests here don't exercise the spacing wait itself
    and should run fast. The tests that do exercise it set this back to a
    small positive value with their own `monkeypatch.setattr`.
    """
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0)


# --- Back-to-back spacing ---------------------------------------------------


def test_back_to_back_cycles_never_call_the_same_provider_twice_within_its_spacing(tmp_path, monkeypatch):
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0.3)
    state_dir = str(tmp_path / "spacing")

    with efficiency_probe.fake_provider_latency(0) as calls:
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    by_provider = {}
    for name, start, _end, _thread in calls:
        by_provider.setdefault(name, []).append(start)

    for name in detect.DEFAULT_PROVIDER_ORDER:
        starts = sorted(by_provider.get(name, []))
        if len(starts) != 2:
            pytest.fail(
                "expected exactly 2 calls to %s across 2 back-to-back cycles, got %d"
                % (name, len(starts))
            )
        gap = starts[1] - starts[0]
        if gap < 0.3 - 0.01:
            pytest.fail(
                "%s: second cycle's call started only %.3fs after the first, expected >= ~0.29s"
                % (name, gap)
            )


# --- Cross-cycle persistence in meta ----------------------------------------


def test_provider_last_call_times_persist_in_meta_and_a_later_cycle_still_waits(tmp_path, monkeypatch):
    """After one cycle, meta holds a parsable float epoch string per
    provider; a second, independent `run_once()` call - no in-process
    structure carried over, since `_load_provider_last_calls()` rebuilds
    its dict from meta every time - still honours that recorded spacing.
    """
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 0.3)
    state_dir = str(tmp_path / "cross-cycle")

    with efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    stored = {}
    for name in detect.DEFAULT_PROVIDER_ORDER:
        raw = _meta_value(state_dir, history_db.META_PROVIDER_LAST_CALL_PREFIX + name)
        if raw is None:
            pytest.fail("expected a provider_last_call meta row for %s after the first cycle" % name)
        try:
            stored[name] = float(raw)
        except (TypeError, ValueError):
            pytest.fail("meta value for %s is not a parsable float: %r" % (name, raw))

    with efficiency_probe.fake_provider_latency(0) as calls:
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    seen = set()
    for name, start, _end, _thread in calls:
        seen.add(name)
        gap = start - stored[name]
        if gap < 0.3 - 0.01:
            pytest.fail(
                "%s: second cycle's call started only %.3fs after the meta-recorded call, expected >= ~0.29s"
                % (name, gap)
            )
    if seen != set(detect.DEFAULT_PROVIDER_ORDER):
        pytest.fail("expected the second cycle to call every default provider, got %r" % (seen,))


# --- No prior meta -----------------------------------------------------------


def test_a_cycle_with_no_prior_meta_sleeps_zero_times_and_makes_one_connection_and_commit(tmp_path):
    state_dir = str(tmp_path / "first")

    with efficiency_probe.count_sleeps() as sleeps, \
            efficiency_probe.count_db() as counts, \
            efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if sleeps:
        pytest.fail("expected no sleep on a cycle with no prior provider_last_call meta, got %r" % (sleeps,))
    if counts.connections != 1:
        pytest.fail("expected exactly 1 connection, got %d" % counts.connections)
    if counts.commits != 1:
        pytest.fail("expected exactly 1 commit, got %d" % counts.commits)


# --- An unchanged live repeat leaves poll_state.json alone -------------------


def test_an_unchanged_live_repeat_writes_poll_state_zero_times(tmp_path):
    state_dir = str(tmp_path / "repeat")

    with efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)  # warm-up

    with efficiency_probe.count_poll_state_writes() as writes, \
            efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if writes:
        pytest.fail(
            "expected zero poll_state.json writes on an unchanged empty-sky repeat, got %r" % (writes,)
        )


# --- Corrupt stored value ----------------------------------------------------


def test_an_unparsable_stored_last_call_value_is_treated_as_no_previous_call(tmp_path, monkeypatch):
    """A large spacing value, restored here from the autouse zeroing
    fixture, would force a real wait IF the corrupt string were somehow
    parsed as a recent call - proving this test actually exercises the
    "treat as no previous call" branch rather than passing by
    coincidence.
    """
    monkeypatch.setattr(detect, "MIN_SECONDS_BETWEEN_CALLS", 1.1)
    state_dir = str(tmp_path / "corrupt")

    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(conn, history_db.META_PROVIDER_LAST_CALL_PREFIX + "adsbfi", "abc")

    with efficiency_probe.count_sleeps() as sleeps, efficiency_probe.fake_provider_latency(0):
        result = poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if result is None or "panel_changed" not in result:
        pytest.fail("run_once() did not return its normal result dict against a corrupt meta value: %r" % (result,))
    if sleeps:
        pytest.fail("expected no sleep against an unparsable stored value, got %r" % (sleeps,))


# --- Hold and injected-snapshot cycles never touch the provider keys --------


def test_a_hold_cycle_and_an_injected_snapshot_cycle_never_touch_the_provider_meta_keys(tmp_path):
    state_dir = str(tmp_path / "untouched")

    # One real live cycle first, so there is something in meta that a
    # later cycle could (but must not) disturb.
    with efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    before = {
        name: _meta_value(state_dir, history_db.META_PROVIDER_LAST_CALL_PREFIX + name)
        for name in detect.DEFAULT_PROVIDER_ORDER
    }
    if any(value is None for value in before.values()):
        pytest.fail("expected every default provider's meta row to exist after the warm-up cycle: %r" % (before,))

    # A hold cycle: display_enabled=False takes the early return before
    # detect.load_geofence()/poll_current_aircraft() is ever reached.
    device_config.save_device_config(state_dir, display_enabled=False)
    poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)
    device_config.save_device_config(state_dir, display_enabled=True)

    # An injected-snapshot cycle: no live provider is ever queried.
    poll_cycle.run_once(snapshot=_empty_snapshot(), state_dir=state_dir, geofence=GEOFENCE_PATH)

    after = {
        name: _meta_value(state_dir, history_db.META_PROVIDER_LAST_CALL_PREFIX + name)
        for name in detect.DEFAULT_PROVIDER_ORDER
    }
    if before != after:
        pytest.fail(
            "provider_last_call meta changed across a hold cycle and an injected-snapshot cycle: %r -> %r"
            % (before, after)
        )


# --- A history-write failure is still contained ------------------------------


def test_a_history_write_failure_does_not_raise_out_of_the_cycle_with_provider_last_calls_present(tmp_path, monkeypatch):
    state_dir = str(tmp_path / "write-failure")

    def _boom(*args, **kwargs):
        raise sqlite3.OperationalError("meta write exploded")

    monkeypatch.setattr(poll_cycle.history_db, "set_meta", _boom)

    with efficiency_probe.fake_provider_latency(0):
        result = poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if result is None or "panel_changed" not in result:
        pytest.fail("run_once() did not return its normal result dict after a history write failure: %r" % (result,))
