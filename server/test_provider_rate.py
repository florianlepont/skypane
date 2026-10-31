#!/usr/bin/env python3
"""Behaviour tests for keeping the ADS-B request budget across back-to-back
poll cycles (and processes): a standalone cycle fetches only through the
persisted request ledger in the state root.

  * two cycles run back to back never start provider requests closer
    together than the ledger spacing
  * the ledger lives in the state root, never in a per-device directory
  * a cycle with a fresh ledger sleeps zero times, and still opens exactly
    one connection and commits exactly once
  * an unusable ledger file does not break the cycle
  * a hold cycle and an injected-snapshot cycle make no provider request,
    create no ledger and write no `provider_last_call:*` meta row
  * a history-write failure still does not raise out of the cycle

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
import server.request_budget as request_budget  # noqa: E402

pytestmark = pytest.mark.slow


def _empty_snapshot():
    """No aircraft detected this cycle - the injected-snapshot path."""
    return {"ac": []}


@pytest.fixture(autouse=True)
def _stub_adsbdb(monkeypatch):
    """No test in this module needs a real adsbdb route lookup - every
    cycle here sees an empty sky (no candidate ever reaches
    enrich.resolve_route)."""
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


def _set_ledger_spacing(monkeypatch, seconds):
    """The ledger constructor's default spacing is bound at definition
    time, so the defaults themselves are replaced for the test."""
    monkeypatch.setattr(request_budget.RequestLedger.__init__, "__defaults__", (None, None, seconds))


def _meta_provider_rows(state_dir):
    with history_db.open_db(state_dir) as conn:
        return [
            name for name in detect.DEFAULT_PROVIDER_ORDER
            if history_db.get_meta(conn, history_db.META_PROVIDER_LAST_CALL_PREFIX + name) is not None
        ]


@pytest.fixture(autouse=True)
def _zero_ledger_spacing(monkeypatch):
    """Most tests here do not exercise the spacing wait and should run
    fast; the spacing tests set a small positive value themselves."""
    _set_ledger_spacing(monkeypatch, 0.0)


# --- Back-to-back spacing ---------------------------------------------------


def test_back_to_back_cycles_never_start_provider_requests_within_the_ledger_spacing(tmp_path, monkeypatch):
    _set_ledger_spacing(monkeypatch, 0.3)
    state_dir = str(tmp_path / "spacing")

    with efficiency_probe.fake_provider_latency(0) as calls:
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    starts = sorted(start for _name, start, _end, _thread in calls)
    expected = 2 * len(detect.DEFAULT_PROVIDER_ORDER)
    if len(starts) != expected:
        pytest.fail("expected %d provider requests across 2 cycles, got %d" % (expected, len(starts)))
    for earlier, later in zip(starts, starts[1:]):
        if later - earlier < 0.3 - 0.01:
            pytest.fail("two provider requests started only %.3fs apart, expected >= ~0.29s" % (later - earlier))


def test_a_per_device_directory_spends_the_ledger_in_the_state_root(tmp_path):
    root = tmp_path / "root"
    device_dir = root / "devices" / "frame-1"

    with efficiency_probe.fake_provider_latency(0) as calls:
        poll_cycle.run_once(state_dir=str(device_dir), geofence=GEOFENCE_PATH, reconcile_firmware=False)

    if not calls:
        pytest.fail("expected the standalone cycle to query the providers")
    if not (root / request_budget.LEDGER_FILENAME).is_file():
        pytest.fail("expected the request ledger in the state root")
    if (device_dir / request_budget.LEDGER_FILENAME).exists():
        pytest.fail("a per-device directory must never hold a request ledger")


def test_an_explicit_ledger_root_wins(tmp_path):
    state_dir = tmp_path / "state"
    ledger_root = tmp_path / "elsewhere"
    ledger_root.mkdir()

    with efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=str(state_dir), geofence=GEOFENCE_PATH, ledger_root=str(ledger_root))

    if not (ledger_root / request_budget.LEDGER_FILENAME).is_file():
        pytest.fail("expected the ledger under the explicit ledger_root")
    if (state_dir / request_budget.LEDGER_FILENAME).exists():
        pytest.fail("the state directory must not hold a ledger when ledger_root is given")


# --- Fresh ledger ------------------------------------------------------------


def test_a_cycle_with_a_fresh_ledger_sleeps_zero_times_and_makes_one_connection_and_commit(tmp_path):
    state_dir = str(tmp_path / "first")

    with efficiency_probe.count_sleeps() as sleeps, \
            efficiency_probe.count_db() as counts, \
            efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if sleeps:
        pytest.fail("expected no sleep on a cycle with a fresh ledger, got %r" % (sleeps,))
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


# --- Unusable ledger ---------------------------------------------------------


def test_an_unusable_ledger_file_does_not_break_the_cycle(tmp_path):
    state_dir = tmp_path / "corrupt"
    state_dir.mkdir()
    (state_dir / request_budget.LEDGER_FILENAME).write_text("not json {{{", encoding="utf-8")

    with efficiency_probe.fake_provider_latency(0):
        result = poll_cycle.run_once(state_dir=str(state_dir), geofence=GEOFENCE_PATH)

    if result is None or "panel_changed" not in result:
        pytest.fail("run_once() did not return its normal result dict against a corrupt ledger: %r" % (result,))


def test_an_unwritable_budget_degrades_to_a_source_fault_without_a_request(tmp_path, monkeypatch):
    def _unavailable(self, provider):
        raise request_budget.BudgetUnavailable("busy")

    monkeypatch.setattr(request_budget.RequestLedger, "acquire", _unavailable)

    with efficiency_probe.fake_provider_latency(0) as calls:
        result = poll_cycle.run_once(state_dir=str(tmp_path / "busy"), geofence=GEOFENCE_PATH)

    if calls:
        pytest.fail("no provider request may be made without budget, got %r" % (calls,))
    if result.get("source_fault") is not True:
        pytest.fail("expected a source fault when no provider could be queried, got %r" % (result,))


# --- Hold and injected-snapshot cycles spend nothing -------------------------


def test_a_hold_cycle_and_an_injected_snapshot_cycle_make_no_request_and_create_no_ledger(tmp_path):
    state_dir = tmp_path / "untouched"
    device_config.save_device_config(str(state_dir), display_enabled=False)

    with efficiency_probe.fake_provider_latency(0) as calls:
        poll_cycle.run_once(state_dir=str(state_dir), geofence=GEOFENCE_PATH)
        device_config.save_device_config(str(state_dir), display_enabled=True)
        poll_cycle.run_once(snapshot=_empty_snapshot(), state_dir=str(state_dir), geofence=GEOFENCE_PATH)

    if calls:
        pytest.fail("hold and snapshot cycles must not query a provider, got %r" % (calls,))
    if (state_dir / request_budget.LEDGER_FILENAME).exists():
        pytest.fail("hold and snapshot cycles must not create a request ledger")
    if _meta_provider_rows(str(state_dir)):
        pytest.fail("no provider_last_call meta row may be written")


def test_a_live_cycle_writes_no_provider_last_call_meta_row(tmp_path):
    state_dir = str(tmp_path / "live")

    with efficiency_probe.fake_provider_latency(0):
        poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if _meta_provider_rows(state_dir):
        pytest.fail("a live cycle must not write provider_last_call meta rows")


# --- A history-write failure is still contained ------------------------------


def test_a_history_write_failure_does_not_raise_out_of_the_cycle(tmp_path, monkeypatch):
    state_dir = str(tmp_path / "write-failure")

    def _boom(*args, **kwargs):
        raise sqlite3.OperationalError("meta write exploded")

    monkeypatch.setattr(poll_cycle.history_db, "set_meta", _boom)

    with efficiency_probe.fake_provider_latency(0):
        result = poll_cycle.run_once(state_dir=state_dir, geofence=GEOFENCE_PATH)

    if result is None or "panel_changed" not in result:
        pytest.fail("run_once() did not return its normal result dict after a history write failure: %r" % (result,))
