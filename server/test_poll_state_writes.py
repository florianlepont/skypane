#!/usr/bin/env python3
"""Behaviour tests for server/poll_cycle.py's write-once-only-if-changed,
compact poll_state.json save.

Covers `state_store.serialize_poll_state()`/`state_store.persist_poll_state_if_changed()`
(the end-of-cycle save `_run_once_locked()` calls from its two exits instead of the
former mid-branch/unconditional-final saves) and `state_store.save_poll_state()`'s
still-unconditional, now-compact seam:

  * the research's seven poll-cycle branches each write poll_state.json
    at most once
  * the two unchanged-repeat branches (empty sky, a held hold) write it
    zero times, leaving the file byte-for-byte and mtime unchanged
  * a flight-detected cycle writes exactly once, strictly after panel.bin
  * a frame-silent notification transition on an otherwise unchanged cycle
    still writes exactly once (the notifications mutation is persisted)
  * the written file is compact JSON that round-trips through json.loads
    and is never longer than the equivalent indent=1 encoding
  * save_poll_state() itself keeps writing unconditionally (the seed seam
    the rest of the suite uses), now compact
  * a pre-existing indent=1 file is rewritten once, compact, on the first
    cycle that actually changes a value, then a following unchanged
    repeat writes zero

Every assertion is a write count, a byte-for-byte file comparison, or a
decoded value - never source text.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# `pytest` invocation; inserted here too so this file also works under the
# legacy direct-execution bridge other server/test_*.py modules support.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import efficiency_probe  # noqa: E402

import server.atomic_io as atomic_io  # noqa: E402
import server.device_config as device_config  # noqa: E402
import server.history_db as history_db  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.state_store as state_store  # noqa: E402
import server.wake as wake  # noqa: E402

pytestmark = pytest.mark.slow

_NOTIFY_TOPIC_URL = "https://ntfy.sh/skypane-test-topic"

# Same shape as scripts/measure_efficiency.py's own FLIGHT_RECORD: a raw
# aggregator-shaped record inside adsb-test/runway3.json's bbox/altitude
# ceiling, climbing well past runway_config.CLIMB_THRESHOLD_FPM (200), so
# it resolves to a confirmed "departing" state on its very first cycle.
_FLIGHT_RECORD = {
    "hex": "39a1b2", "flight": "AFR123  ", "lat": 48.7233, "lon": 2.3794,
    "alt_baro": 450, "gs": 137.1, "baro_rate": 1500, "seen_pos": 1.0,
}


def _poll_state_path(state_dir):
    return os.path.join(state_dir, "poll_state.json")


def _iso(epoch):
    """`epoch` (seconds) as the same timezone-aware UTC ISO-8601-at-
    seconds-precision string `history_db.utc_now_iso()` produces.
    """
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


@pytest.fixture(autouse=True)
def _stub_adsbdb(monkeypatch):
    """No test in this module needs a real adsbdb route lookup - the
    ADS-B provider seam itself is stubbed separately per test (the
    `fake_providers` fixture, or a bare empty-sky `records={}`)."""
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))


def _run_seven_branches(state_dir):
    """The research's seven branches, in order, against one state dir -
    each entry a `(label, efficiency_probe.cycle_probe() result)` pair.
    Mirrors server/test_poll_efficiency.py's own helper.
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
    for label in (
        "empty sky (first)", "empty sky (repeat)", "flight detected",
        "same flight again", "nothing new, flight on screen",
    ):
        result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=records_by_label[label])
        results.append((label, result))

    device_config.save_device_config(state_dir, display_enabled=False)
    for label in ("display_off hold entry", "display_off hold repeat"):
        result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)
        results.append((label, result))
    device_config.save_device_config(state_dir, display_enabled=True)

    return results


# --- The research's seven branches -----------------------------------------


def test_seven_research_branches_write_poll_state_at_most_once_per_cycle(tmp_path, fake_providers):
    """Every one of the research's seven poll-cycle branches writes
    poll_state.json at most once - never the old shape's 1-2 saves.
    """
    state_dir = str(tmp_path / "cycles")
    results = _run_seven_branches(state_dir)

    for label, result in results:
        if result["poll_state_writes"] > 1:
            pytest.fail("%s: expected at most 1 poll_state.json write, got %d" % (label, result["poll_state_writes"]))


# --- Unchanged repeats write zero, byte-for-byte unchanged ------------------


def test_empty_sky_repeat_writes_zero_and_leaves_the_file_byte_identical(tmp_path, fake_providers):
    state_dir = str(tmp_path / "empty-repeat")
    empty_records = {}
    path = _poll_state_path(state_dir)

    efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)  # bootstrap: writes once
    before_bytes = open(path, "rb").read()
    before_mtime_ns = os.stat(path).st_mtime_ns

    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)

    after_bytes = open(path, "rb").read()
    after_mtime_ns = os.stat(path).st_mtime_ns

    if result["poll_state_writes"] != 0:
        pytest.fail("empty-sky repeat: expected 0 poll_state.json writes, got %d" % result["poll_state_writes"])
    if after_bytes != before_bytes:
        pytest.fail("empty-sky repeat: poll_state.json bytes changed on an unchanged repeat")
    if after_mtime_ns != before_mtime_ns:
        pytest.fail("empty-sky repeat: poll_state.json mtime changed on an unchanged repeat")


def test_held_hold_repeat_writes_zero_and_leaves_the_file_byte_identical(tmp_path, fake_providers):
    state_dir = str(tmp_path / "hold-repeat")
    empty_records = {}
    path = _poll_state_path(state_dir)

    device_config.save_device_config(state_dir, display_enabled=False)
    efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)  # hold entry: writes once

    before_bytes = open(path, "rb").read()
    before_mtime_ns = os.stat(path).st_mtime_ns

    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)  # hold repeat

    after_bytes = open(path, "rb").read()
    after_mtime_ns = os.stat(path).st_mtime_ns

    if result["poll_state_writes"] != 0:
        pytest.fail("held-hold repeat: expected 0 poll_state.json writes, got %d" % result["poll_state_writes"])
    if after_bytes != before_bytes:
        pytest.fail("held-hold repeat: poll_state.json bytes changed on an unchanged repeat")
    if after_mtime_ns != before_mtime_ns:
        pytest.fail("held-hold repeat: poll_state.json mtime changed on an unchanged repeat")


# --- Flight detected: exactly 1 write, after panel.bin ----------------------


def test_flight_detected_writes_poll_state_exactly_once_after_panel_bin(tmp_path, fake_providers, monkeypatch):
    state_dir = str(tmp_path / "order")
    order = []
    real_atomic_write = atomic_io.atomic_write

    def logging_atomic_write(path, data, mode=None):
        order.append(os.path.basename(path))
        return real_atomic_write(path, data, mode=mode)

    monkeypatch.setattr(atomic_io, "atomic_write", logging_atomic_write)

    result = efficiency_probe.cycle_probe(
        state_dir, latency_s=0,
        records={"adsbfi": [_FLIGHT_RECORD], "adsblol": [_FLIGHT_RECORD]},
    )

    if result["poll_state_writes"] != 1:
        pytest.fail("flight detected: expected exactly 1 poll_state.json write, got %d" % result["poll_state_writes"])
    if "panel.bin" not in order:
        pytest.fail("expected panel.bin to have been written, got atomic_write order %r" % (order,))
    if "poll_state.json" not in order:
        pytest.fail("expected poll_state.json to have been written, got atomic_write order %r" % (order,))
    if order.index("panel.bin") > order.index("poll_state.json"):
        pytest.fail("panel.bin must be written before poll_state.json, got order %r" % (order,))


# --- A silence-notification transition on an otherwise unchanged cycle ------


def test_a_silence_transition_on_an_otherwise_unchanged_cycle_writes_exactly_once(tmp_path, fake_providers, monkeypatch):
    state_dir = str(tmp_path / "silence")
    empty_records = {}

    efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)  # bootstrap

    device_config.save_device_config(
        state_dir, notifications={
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

    monkeypatch.setattr(poll_cycle.notify, "send_notification", lambda *a, **k: True)

    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=empty_records)

    if result["poll_state_writes"] != 1:
        pytest.fail(
            "silence transition: expected exactly 1 poll_state.json write, got %d" % result["poll_state_writes"])

    on_disk = state_store.load_poll_state(state_dir)
    notifications = on_disk.get("notifications")
    if not isinstance(notifications, dict) or notifications.get("last_silent_sent") is not True:
        pytest.fail(
            "expected the notify hook's poll_state['notifications'] mutation to be persisted, got %r"
            % (notifications,))


# --- Compact format, round-trips, never longer than indent=1 ----------------


def test_the_written_file_is_compact_and_round_trips(tmp_path, fake_providers):
    state_dir = str(tmp_path / "compact")
    efficiency_probe.cycle_probe(state_dir, latency_s=0, records={})

    with open(_poll_state_path(state_dir), "rb") as fh:
        text = fh.read().decode("utf-8")

    if "\n" in text:
        pytest.fail("expected no newlines in the compact poll_state.json, found one")
    if ": " in text:
        pytest.fail("expected no space after a key's colon in the compact poll_state.json, found one")

    decoded = json.loads(text)
    if decoded != state_store.load_poll_state(state_dir):
        pytest.fail("json.loads(text) did not round-trip to the in-memory state")

    indented_len = len(json.dumps(decoded, indent=1))
    if len(text) > indented_len:
        pytest.fail(
            "expected the compact serialisation to be no longer than the indent=1 one, got %d > %d"
            % (len(text), indented_len))


# --- save_poll_state(): still always writes, now compact --------------------


def test_save_poll_state_always_writes_and_is_compact(tmp_path, monkeypatch):
    state_dir = str(tmp_path / "seed")
    os.makedirs(state_dir, exist_ok=True)
    state = {"a": 1, "b": [1, 2, 3]}

    calls = []
    real_atomic_write = atomic_io.atomic_write

    def counting_atomic_write(path, data, mode=None):
        calls.append(path)
        return real_atomic_write(path, data, mode=mode)

    monkeypatch.setattr(atomic_io, "atomic_write", counting_atomic_write)

    state_store.save_poll_state(state_dir, state)
    state_store.save_poll_state(state_dir, state)  # identical state - must still write

    if len(calls) != 2:
        pytest.fail(
            "save_poll_state() must always write, even given the identical state twice; got %d calls"
            % len(calls))

    with open(_poll_state_path(state_dir)) as fh:
        text = fh.read()
    if "\n" in text or ": " in text:
        pytest.fail("save_poll_state() did not write compact JSON")
    if json.loads(text) != state:
        pytest.fail("save_poll_state() did not round-trip the given state")


# --- Migration: an old indent=1 file rewrites once, compact, then zero ------


def test_an_old_indent1_file_is_rewritten_once_compact_then_a_repeat_writes_zero(tmp_path, fake_providers):
    state_dir = str(tmp_path / "migrate")
    os.makedirs(state_dir, exist_ok=True)
    path = _poll_state_path(state_dir)

    # A pre-existing file in the old indent=1 shape, missing the two keys
    # this cycle is about to add for the first time - the same shape a
    # real poll_state.json from before this change would have.
    atomic_io.atomic_write(path, json.dumps({"pending_flights": []}, indent=1))
    with open(path) as fh:
        seed_text = fh.read()
    if "\n" not in seed_text:
        pytest.fail("test setup did not actually seed an indent=1 (multi-line) file")

    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records={})
    if result["poll_state_writes"] != 1:
        pytest.fail(
            "expected the first cycle over an old indent=1 file to write exactly once, got %d"
            % result["poll_state_writes"])

    with open(path) as fh:
        rewritten_text = fh.read()
    if "\n" in rewritten_text or ": " in rewritten_text:
        pytest.fail("expected the rewritten file to be compact, found indentation")

    result2 = efficiency_probe.cycle_probe(state_dir, latency_s=0, records={})
    if result2["poll_state_writes"] != 0:
        pytest.fail(
            "expected the following unchanged repeat cycle to write zero times, got %d"
            % result2["poll_state_writes"])
