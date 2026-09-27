#!/usr/bin/env python3
"""Contract tests for one SQLite connection and one transaction per poll
cycle.

Covers `server/poll_cycle.py`'s `run_once()` (now wrapping `_run_once_locked()`
in a `history_db.connection_scope(state_dir)`, nested inside
`poll_cycle_lock()`) and `_record_history()` (now grouping every write in one
`history_db.write_batch(conn)`), across:

  * the research's seven poll-cycle branches (the same sequence
    `scripts/measure_efficiency.py`'s `build_poll_cycle_table()` runs), each
    opening exactly one connection and committing exactly once
  * `init_schema()` running at most once across that whole sequence
  * the injected-`snapshot=` path (no live ADS-B query) also opening exactly
    one connection
  * a cycle whose frame-silent notification fires: no write transaction is
    open on the cycle's own connection while the fake `notify.send_notification`
    runs, and the batch's own row is already visible from a second,
    independently-opened connection
  * a mid-batch history-write failure: contained by `_record_history()`'s
    existing handler, and the whole batch (not just the failing write) rolls
    back
  * `run_once()` called from inside an already-active `connection_scope()`
    on the same thread (the companion's POST /poll-now shape) opening no
    additional connection

No test here asserts wall-clock timing - only counts
(`efficiency_probe.count_db()`) and durable state, per this phase's own
research-instrument convention.
"""
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

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
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.wake as wake  # noqa: E402

pytestmark = pytest.mark.slow

_NOTIFY_TOPIC_URL = "https://ntfy.sh/skypane-test-topic"

# Same shape and values as scripts/measure_efficiency.py's own FLIGHT_RECORD:
# a raw aggregator-shaped record positioned inside adsb-test/runway3.json's
# bbox/altitude ceiling, climbing well past runway_config.CLIMB_THRESHOLD_FPM
# (200) so it resolves to a confirmed "departing" state on its very first
# cycle.
_FLIGHT_RECORD = {
    "hex": "39a1b2", "flight": "AFR123  ", "lat": 48.7233, "lon": 2.3794,
    "alt_baro": 450, "gs": 137.1, "baro_rate": 1500, "seen_pos": 1.0,
}

_SEVEN_BRANCH_LABELS = (
    "empty sky (first)",
    "empty sky (repeat)",
    "flight detected",
    "same flight again",
    "nothing new, flight on screen",
)


def _empty_snapshot():
    """No aircraft detected this cycle."""
    return {"ac": []}


def _flight_snapshot():
    return {"ac": [_FLIGHT_RECORD]}


def _iso(epoch):
    """`epoch` (seconds) as the same timezone-aware UTC ISO-8601-at-
    seconds-precision string `history_db.utc_now_iso()` produces.
    """
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


@pytest.fixture(autouse=True)
def _stub_adsbdb(monkeypatch):
    """Every cycle in this module stubs the adsbdb route-lookup transport -
    none of these tests needs a real route, and the ADS-B provider seam
    itself is stubbed separately per test (`fake_providers` or a direct
    `snapshot=` injection, neither of which reaches the network either).
    """
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


def _run_seven_branches(state_dir):
    """The research's seven branches, in order, against one state dir -
    each entry a `(label, efficiency_probe.cycle_probe() result)` pair.
    """
    empty_records = {}
    flight_records = {"adsbfi": [_FLIGHT_RECORD], "adsblol": [_FLIGHT_RECORD]}
    records_by_label = {
        "empty sky (first)": empty_records,
        "empty sky (repeat)": empty_records,
        "flight detected": flight_records,
        "same flight again": flight_records,
        "nothing new, flight on screen": empty_records,
    }

    results = []
    for label in _SEVEN_BRANCH_LABELS:
        result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=records_by_label[label])
        results.append((label, result))

    device_config.save_device_config(state_dir, display_enabled=False)
    for label in ("display_off hold entry", "display_off hold repeat"):
        result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)
        results.append((label, result))
    device_config.save_device_config(state_dir, display_enabled=True)

    return results


# --- The research's seven branches -----------------------------------------


def test_seven_research_branches_open_one_connection_and_commit_once(tmp_path, fake_providers):
    """Every one of the research's seven poll-cycle branches, run in
    sequence against the same state dir (as
    `scripts/measure_efficiency.py`'s `build_poll_cycle_table()` does),
    opens exactly one SQLite connection and commits exactly once -
    including a hold-repeat cycle with nothing new to write, which still
    advances `META_LAST_PIPELINE_RUN`.
    """
    state_dir = str(tmp_path / "cycles")
    results = _run_seven_branches(state_dir)

    for label, result in results:
        if result["connections"] != 1:
            pytest.fail("%s: expected 1 connection, got %d" % (label, result["connections"]))
        if result["commits"] != 1:
            pytest.fail("%s: expected 1 commit, got %d" % (label, result["commits"]))


def test_init_schema_runs_at_most_once_across_the_seven_branch_sequence(tmp_path, fake_providers):
    """All seven branches share the same `history.db` file identity - the
    schema-once guard from plan 03 must not re-run it once per cycle.
    """
    state_dir = str(tmp_path / "cycles-schema")
    results = _run_seven_branches(state_dir)

    total_init_schema = sum(result["init_schema"] for _label, result in results)
    if total_init_schema > 1:
        pytest.fail("expected init_schema at most once across all seven branches, got %d" % total_init_schema)


# --- Injected-snapshot path --------------------------------------------------


def test_injected_snapshot_path_also_opens_exactly_one_connection(tmp_path):
    """`run_once(snapshot=...)` never queries a live ADS-B provider, but
    still opens exactly one connection for the cycle.
    """
    state_dir = str(tmp_path / "snapshot")
    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, snapshot=_empty_snapshot())

    if result["connections"] != 1:
        pytest.fail("snapshot-injected cycle opened %d connections, expected 1" % result["connections"])


# --- No write transaction open during the ntfy send -------------------------


def test_no_write_transaction_open_during_notify_send_and_batch_already_visible(tmp_path, monkeypatch):
    """A cycle whose frame-silent notification fires: the cycle's own
    connection (captured through a `sqlite3.connect` wrapper) has no
    pending write transaction when the fake `notify.send_notification`
    runs, and the batch's own meta row is already visible from a second,
    independently-opened connection at that point - proof the batch
    committed before the HTTP call, not after or during it.
    """
    state_dir = str(tmp_path / "notify")
    device_config.save_device_config(
        state_dir, display_enabled=True,
        notifications={
            "topic_url": _NOTIFY_TOPIC_URL, "battery_low": False,
            "frame_silent": True, "lang": "en",
        },
    )

    device_cfg = device_config.load_device_config(state_dir)
    warn_s, _error_s = wake.device_staleness_thresholds(
        wake.effective_wake_interval_s(device_cfg, battery_critical=False)
    )
    stale_iso = _iso(time.time() - warn_s - 3600)
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, stale_iso, battery_mv=3700)

    captured_conns = []
    real_connect = sqlite3.connect

    def capturing_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        captured_conns.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", capturing_connect)

    probe = {}

    def fake_send(topic_url, title, body, timeout=5, transport=None):
        # Captured BEFORE opening the second connection below: this is the
        # count of connections the cycle itself opened, not including the
        # one this fake sender is about to open of its own.
        probe["cycle_connections"] = len(captured_conns)
        probe["in_transaction"] = captured_conns[-1].in_transaction
        second_conn = history_db.connect(state_dir)
        try:
            probe["meta_from_second_conn"] = history_db.get_meta(
                second_conn, history_db.META_LAST_PIPELINE_RUN)
        finally:
            second_conn.close()
        return True

    monkeypatch.setattr(poll_cycle.notify, "send_notification", fake_send)

    poll_cycle.run_once(snapshot=_empty_snapshot(), state_dir=state_dir, geofence=GEOFENCE_PATH)

    if "in_transaction" not in probe:
        pytest.fail("the fake notify.send_notification was never called - expected the silence transition to fire")
    if probe["cycle_connections"] != 1:
        pytest.fail("expected exactly one connection opened by the cycle itself, got %d" % probe["cycle_connections"])
    if probe["in_transaction"] is not False:
        pytest.fail("expected no open write transaction during the notify send, got %r" % (probe["in_transaction"],))
    if probe["meta_from_second_conn"] is None:
        pytest.fail("expected the batch's meta row already visible from a second connection, got %r" % (probe["meta_from_second_conn"],))


# --- A mid-batch history-write failure ---------------------------------------


def test_history_write_failure_is_contained_and_the_whole_batch_rolls_back(tmp_path, monkeypatch):
    """A `history_db.set_meta()` failure inside `_record_history()`'s batch
    is caught and logged by the existing handler - the cycle still returns
    its normal result dict, the panel is still written, and the WHOLE
    batch rolls back: this cycle's own flight detection would otherwise
    have written a `runway_events` row too, and that row must not survive
    either.
    """
    state_dir = str(tmp_path / "failure")

    def _boom(*args, **kwargs):
        raise sqlite3.OperationalError("meta write exploded")

    monkeypatch.setattr(poll_cycle.history_db, "set_meta", _boom)

    result = poll_cycle.run_once(
        snapshot=_flight_snapshot(), state_dir=state_dir, geofence=GEOFENCE_PATH)

    if result is None or "panel_changed" not in result:
        pytest.fail("run_once() did not return its normal result dict: %r" % (result,))
    if not os.path.exists(os.path.join(state_dir, "panel.bin")):
        pytest.fail("the panel was left unwritten by a failing history write")

    with history_db.open_db(state_dir) as conn:
        rows = history_db.recent_runway_events(conn, limit=10)
    if rows != []:
        pytest.fail("expected no runway_events row persisted from the rolled-back batch, got %r" % (rows,))


# --- run_once() nested inside an already-active connection_scope() ----------


def test_run_once_nested_inside_an_active_connection_scope_opens_no_additional_connection(tmp_path):
    """POST /poll-now's shape: a caller (e.g. the companion's request
    dispatch) already inside `history_db.connection_scope(state_dir)` on
    this thread, calling `run_once()`, reuses that same scope - re-entrant
    per plan 03 - rather than opening a second connection.
    """
    state_dir = str(tmp_path / "nested")

    with efficiency_probe.count_db() as counts:
        with history_db.connection_scope(state_dir):
            poll_cycle.run_once(snapshot=_empty_snapshot(), state_dir=state_dir, geofence=GEOFENCE_PATH)

    if counts.connections != 1:
        pytest.fail("run_once() nested inside an active connection_scope() opened %d connections, expected 1" % counts.connections)
