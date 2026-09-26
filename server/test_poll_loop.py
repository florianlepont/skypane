#!/usr/bin/env python3
"""Contract tests for server/poll_loop.py's two-deep flight history - the
engineering consequence of the current+previous two-flight poster layout:
a genuinely new detection (different ICAO hex) must shift the old
"current" flight down into "previous" before being overwritten;
re-detecting the same aircraft must not shift anything.

Also covers cross-cycle persistence of the unresolved-ICAO-prefix
registry: that a registry entry survives the process boundary between
two separate `run_once()` invocations against the same state directory,
that a recognized-airline cycle leaves it untouched, and that the poll
line's `unknown_prefix=` field names the recorded prefix on a miss cycle
and reads `None` on a covered cycle.

It also covers the BOUNDED-AGE PENDING QUEUE (mechanism-C mitigation) that
paces how fast the "current" slot advances: the server re-renders every
30s but the frame physically cannot redraw faster than ~90s, so distinct
detections are queued rather than overwriting each other, promoted
oldest-first, and discarded once they would be more than `MAX_STALENESS_S`
stale.

WHAT THE TESTS ARE FOR - three distinct roles, kept explicit so a later
reader cannot mistake one for another and quietly relax it:

  * REGRESSION tests assert the FIXED behaviour and fail against a
    restored pre-fix implementation. The single seam that restores the
    pre-fix behaviour is `poll_loop.advance_is_due` forced to True: with
    the pacing gate always open, every distinct detection is enqueued and
    popped in the same cycle, the queue never accumulates, and the
    "current" slot advances on every distinct detection - exactly what
    the code did before this pass.
  * PRECONDITION tests assert the BUG is genuinely reproducible, so they
    MUST hold against the pre-fix implementation - that is their whole
    point (test_prefix_burst_loses_an_aircraft_entirely_pre_fix below).
  * GUARD tests must hold in BOTH directions. If a guard flips, the fix
    has broken something it was supposed to leave alone, or has abandoned
    a bound it exists to enforce.

TIME IS INJECTED, NEVER SLEPT. `poll_loop.now_s()` is a module-level seam
precisely because every pacing and staleness decision is arithmetic over
timestamps persisted in poll_state.json (this script is a systemd oneshot
with no in-process memory, D-P2-02). The `clock` fixture below replaces it
with a dictionary-backed fake clock, stepped explicitly, so a 150-second
staleness window costs no wall-clock time and the outcome is
deterministic.

Every run_once() cycle in this module stubs enrich.default_transport (the
`_stub_adsbdb` autouse fixture) - no test reaches the real network; a
test needing a specific adsbdb response overrides the stub locally via
`monkeypatch`.
"""
import contextlib
import hashlib
import io
import json
import os
import platform
import shutil
import sqlite3
import subprocess
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
# `pytest` invocation; the legacy-runner bridge below executes this file
# directly instead, so the same directory is added here too.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import server.poll_loop as poll_loop  # noqa: E402
import server.device_config as device_config  # noqa: E402
import server.plane.detect as detect  # noqa: E402
import server.plane.render as render  # noqa: E402
import server.plane.calendar_rules as calendar_rules  # noqa: E402
import server.plane.colour_rules as colour_rules  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402
import server.plane.manual_resolutions as manual_resolutions  # noqa: E402
from server import history_db  # noqa: E402
from skypane_test_support import requires_non_root  # noqa: E402

pytestmark = pytest.mark.slow

# Pins the default-config panel.bin digest produced against the FLIGHT1
# fixture (test_default_config_byte_identity's own _snapshot("aaaaaa",
# "FLIGHT1 ") fixture) - Linux/CI-authoritative (_digest_verdict() below
# degrades a mismatch to an informational NOTE off Linux, since Pillow/
# FreeType text rasterization genuinely differs by platform for
# byte-identical code). Always re-pin this value from a real CI FAIL log,
# never from a local computation, containerized or not - this project has
# repeatedly confirmed macOS, a generic Linux container and the real CI
# runner each produce a different digest for identical code.
_DEFAULT_CONFIG_DIGEST = "f8cb1f8d358d45e6977ccd56639e1f42eb76d394f4a7cf1b03217d314f4ba2d3"

# A fixed, arbitrary epoch base so every timestamp in this harness is a plain
# offset from zero and no assertion depends on the real wall clock.
CLOCK_BASE = 1_700_000_000.0

# A strong, unambiguous +2400 ft/min climb - clears the D-P2-04 deadband on
# the very first cycle, so confirmed_state is never None in a fixture built
# from this constant (irrelevant to what any single test below exercises).
CLIMB = 2400

# The battery/silence notification-transition tests below call
# poll_loop._notify_battery_transition()/_notify_silence_transition()
# directly with an injected _FakeSender - the private helpers both
# call sites in run_once() invoke - never a real POST.
_NOTIFY_TOPIC_URL = "https://ntfy.sh/skypane-test-topic"


def _notify_device_cfg(topic_url=_NOTIFY_TOPIC_URL, battery_low=True, frame_silent=True, lang="en", wake_interval_s=None):
    notifications = {
        "topic_url": topic_url, "battery_low": battery_low,
        "frame_silent": frame_silent, "lang": lang,
    }
    cfg = {"notifications": notifications}
    if wake_interval_s is not None:
        cfg["wake_interval_s"] = wake_interval_s
    return cfg


def _tick(clock, seconds):
    """Step a `clock` fixture's fake time forward by `seconds`."""
    clock["t"] += float(seconds)


def _wake_epoch_rows(state_dir):
    """The wake_epochs table's own (ts, wake_interval_s) rows, oldest
    first - the history-write path pins that a row is written only on a
    genuine interval CHANGE, never once per cycle.
    """
    with poll_loop.history_db.open_db(state_dir) as conn:
        return [
            (row["ts"], row["wake_interval_s"])
            for row in conn.execute(
                "SELECT ts, wake_interval_s FROM wake_epochs ORDER BY id ASC"
            ).fetchall()
        ]


def _mkdir(base, name):
    """A fresh subdirectory under `tmp_path`, standing in for the old
    hand-rolled temp-dir-factory calls this harness used before migration -
    pytest owns `tmp_path`'s lifecycle, so no matching rmtree/cleanup call
    is required here (any `shutil.rmtree()` still present below is a
    harmless no-op belt for code that already assumed it owned the
    directory's teardown).
    """
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@pytest.fixture
def clock(monkeypatch):
    """A fresh fake clock per test (dict-backed, starting at CLOCK_BASE),
    installed in place of `poll_loop.now_s()` - deterministic pacing/
    staleness arithmetic with no dependency on test execution order or
    wall-clock time (monkeypatch, never manual save/restore).
    """
    fake_clock = {"t": CLOCK_BASE}
    monkeypatch.setattr(poll_loop, "now_s", lambda: fake_clock["t"])
    return fake_clock


@pytest.fixture(autouse=True)
def _stub_adsbdb(monkeypatch, fake_providers):
    """Every run_once() cycle in this module stubs BOTH network seams a
    live cycle can reach: `fake_providers` (repo-root conftest.py) patches
    `requests.get` itself, which is what `detect.query_provider()` uses -
    so a test that calls run_once() with no injected snapshot (and so
    takes the LIVE detect.poll_current_aircraft() path, e.g. a
    battery-state test that only cares about the hold/park branches) still
    never reaches the real network; and `enrich.default_transport` is
    additionally monkeypatched straight to a hard miss, mirroring every
    locally-scoped override below (which shadows this default when a test
    needs a specific adsbdb response, e.g. a manual-resolution "fresh_hit"
    scenario). No test in this module may reach the real network.
    """
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (404, None))
    return fake_providers


def _snapshot(hex_code, callsign, baro_rate):
    """A single-aircraft airplanes.live-shaped snapshot, positioned well
    inside adsb-test/runway3.json's bbox/altitude ceiling (mirrors the real
    TVF23WV entry in server/fixtures/geofence_multi_aircraft.json).
    """
    return {
        "ac": [
            {
                "hex": hex_code,
                "flight": callsign,
                "lat": 48.7233,
                "lon": 2.3794,
                "alt_baro": 450,
                "gs": 137.1,
                "baro_rate": baro_rate,
                "seen_pos": 1.0,
            }
        ]
    }


def _empty_snapshot():
    """No aircraft detected this cycle - exercises the hold branch
    (`elif last_flight is not None:`) when a flight is already on screen.
    """
    return {"ac": []}


def _write_battery_state(state_dir, mv):
    """Hand-write battery_state.json the way stub-server/byos_server.py's
    save_battery_state() would (this harness never runs that process - it
    only needs the file server/poll_loop.py's load_battery_state() reads).
    """
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": mv, "received_at": 1.0}, fh)


# The transition-hook tests below never perform a real POST - every one
# injects this fake in place of server.notify.send_notification,
# recording each call's (topic_url, title, body) rather than reaching a
# network.
class _FakeSender:
    def __init__(self, result=True, raises=None):
        self.calls = []
        self.result = result
        self.raises = raises

    def __call__(self, topic_url, title, body, timeout=5, transport=None):
        self.calls.append((topic_url, title, body))
        if self.raises is not None:
            raise self.raises
        return self.result


def _iso(epoch):
    """`epoch` (fake-clock seconds) as the same timezone-aware UTC
    ISO-8601-at-seconds-precision string `history_db.utc_now_iso()`
    produces, so a seeded `device_health` row parses through
    `poll_loop._parse_iso_epoch()` exactly like a real one would.
    """
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


def _seed_device_health(poll_loop, state_dir, ts_iso, battery_mv=None):
    """Insert one `device_health` row directly via `history_db`, the way
    `history_db.ingest_caddy_battery_log()` would from a real Caddy log
    line - this harness seeds the row itself so the frame-silent checks
    below never depend on a real Caddy log file. `poll_loop` is passed in
    explicitly, mirroring `_seed_calendar_cache()`'s own established
    pattern in this file.
    """
    with poll_loop.history_db.open_db(state_dir) as conn:
        poll_loop.history_db.record_device_health(conn, ts_iso, battery_mv=battery_mv)


# A real airline/far-end pair the calendar tests reuse across every
# scenario below - TVF/TO (Transavia France) is the exact ICAO/IATA pair
# calendar_rules.py's own docstring already cites, and
# enrich._ICAO_AIRLINE_PREFIXES already maps "TVF" to "Transavia France"
# (the airline_only/prefix-fallback path one test below exercises), so
# nothing here invents a fictitious carrier.
_CAL_ICAO_PREFIX = "TVF"
_CAL_AIRLINE_IATA = "TO"
_CAL_ORIGIN_IATA = "ORY"
_CAL_DESTINATION_IATA = "NCE"


def _seed_calendar_cache(poll_loop, state_dir, callsign, origin_iata=_CAL_ORIGIN_IATA, destination_iata=_CAL_DESTINATION_IATA):
    """Pre-seed poll_state.json's enrichment_cache with a resolved
    "cache_hit"-shaped route for `callsign`, so a test can exercise
    `origin_iata`/`destination_iata`/`callsign_iata` being present without
    ever reaching a real adsbdb network call - the same
    `enrich.lookup_route()` cache-hit shape `_route_from_entry()` produces.
    `poll_loop` is passed in explicitly, mirroring every other module-level
    fixture helper in this file (`_write_battery_state` above needs no
    such parameter only because it never touches poll_loop.py's own
    persistence helpers).
    """
    poll_loop.save_poll_state(state_dir, {
        "enrichment_cache": {
            callsign: {
                "found": True,
                "airline_name": "Transavia France",
                "origin_iata": origin_iata,
                "origin_city": "Paris",
                "destination_iata": destination_iata,
                "destination_city": "Nice",
                "callsign_iata": _CAL_AIRLINE_IATA + "1234",
            }
        }
    })


def _calendar_entry(reference_time, origin_iata=_CAL_ORIGIN_IATA, destination_iata=_CAL_DESTINATION_IATA, duration_s=5400.0):
    """One calendar registry entry, matching `reference_time`
    for a DEPARTING detection (`_seed_calendar_cache()`'s route departs
    `origin_iata` for `destination_iata`, so `start_at` - not `end_at` -
    is the reference `match_calendar_theme()` compares against).
    """
    return {
        "airline_iata": _CAL_AIRLINE_IATA,
        "origin_iata": origin_iata,
        "destination_iata": destination_iata,
        "start_at": float(reference_time),
        "end_at": float(reference_time) + duration_s,
    }


def _digest_verdict(digest, expected):
    """Judge a computed panel.bin digest against the pinned expected value,
    platform-gated: Linux (CI + the production VPS) is authoritative, so a
    mismatch there is a hard failure. Everywhere else (macOS dev machines)
    a mismatch is expected and informational only.

    Returns the same (ok, reason) two-tuple test_default_config_byte_identity
    below asserts on.
    """
    if digest == expected:
        return True, ""
    detail = "panel.bin digest %s != pinned %s" % (digest, expected)
    system = platform.system()
    if system == "Linux":
        return False, detail
    print(
        "NOTE %s (platform.system()=%r) - expected on non-Linux: a "
        "Pillow/FreeType text-rasterization difference, not a regression; "
        "the pin is Linux/CI-authoritative, see _DEFAULT_CONFIG_DIGEST's "
        "own comment history" % (detail, system)
    )
    return True, ""


def test_two_deep_flight_history_sequence(tmp_path, monkeypatch, clock):
    """A genuinely sequential scenario: each cycle's outcome depends
    on the same state_dir's accumulated state from the previous cycle, so
    the five old checks below stay one pytest node id.

    - the first-ever detection sets last_flight and leaves previous_flight
      as None
    - re-detecting the same hex across consecutive cycles does not shift
      anything into previous_flight
    - a genuinely new aircraft (different hex) shifts the old current
      flight into previous_flight/previous_confirmed_state
    - a third distinct detection shifts again - previous_flight tracks
      only the immediately-preceding detection (two-deep)
    - render.build_canvas() is actually called with the shifted
      previous_flight (not just recorded in poll_state.json)
    """
    state_dir = str(tmp_path)

    def _run(hex_code, callsign):
        clock["t"] += poll_loop.MIN_ADVANCE_INTERVAL_S + 30
        poll_loop.run_once(snapshot=_snapshot(hex_code, callsign, 2400), state_dir=state_dir, geofence=GEOFENCE_PATH)
        return poll_loop.load_poll_state(state_dir)

    # 1. First-ever detection: no previous_flight yet.
    state1 = _run("aaaaaa", "FLIGHT1 ")
    assert state1.get("last_flight", {}).get("hex") == "aaaaaa", (
        "last_flight after the first detection is %r, expected hex=aaaaaa" % (state1.get("last_flight"),))
    assert state1.get("previous_flight") is None, (
        "previous_flight after the very first detection is %r, expected None" % (state1.get("previous_flight"),))

    # 2. Re-detecting the SAME aircraft (same hex) across consecutive
    # cycles must NOT shift anything into previous_flight.
    state2 = _run("aaaaaa", "FLIGHT1 ")
    assert state2.get("previous_flight") is None, (
        "previous_flight after re-detecting the SAME hex is %r, expected still None (D-25: same aircraft, "
        "not a new one)" % (state2.get("previous_flight"),))
    assert state2.get("last_flight", {}).get("hex") == "aaaaaa", (
        "last_flight after re-detection is %r, expected hex=aaaaaa" % (state2.get("last_flight"),))

    # 3. A genuinely NEW aircraft (different hex) shifts the old current
    # flight down into previous_flight.
    state3 = _run("bbbbbb", "FLIGHT2 ")
    assert state3.get("last_flight", {}).get("hex") == "bbbbbb", (
        "last_flight after a new-hex detection is %r, expected hex=bbbbbb" % (state3.get("last_flight"),))
    assert state3.get("previous_flight", {}).get("hex") == "aaaaaa", (
        "previous_flight after a new-hex detection is %r, expected hex=aaaaaa (the old current flight)"
        % (state3.get("previous_flight"),))
    assert state3.get("previous_confirmed_state") == "departing", (
        "previous_confirmed_state is %r, expected 'departing' (aaaaaa's confirmed state before the shift)"
        % (state3.get("previous_confirmed_state"),))

    # 4. A third, distinct aircraft shifts again - previous_flight tracks
    # the immediately-preceding detection only (two-deep, not a full
    # history).
    state4 = _run("cccccc", "FLIGHT3 ")
    assert state4.get("last_flight", {}).get("hex") == "cccccc", (
        "last_flight after a third distinct detection is %r, expected hex=cccccc" % (state4.get("last_flight"),))
    assert state4.get("previous_flight", {}).get("hex") == "bbbbbb", (
        "previous_flight after a third distinct detection is %r, expected hex=bbbbbb (immediately preceding, "
        "not aaaaaa)" % (state4.get("previous_flight"),))

    # 5. render.build_canvas() was actually called with the shifted
    # previous_flight/previous_route/previous_state (not just recorded in
    # poll_state.json but plumbed through to the render call) - spy on
    # render.build_canvas via the module poll_loop already imported.
    captured = {}
    original = render.build_canvas

    def _spy(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None, **kwargs):
        captured["previous_flight"] = previous_flight
        captured["previous_state"] = previous_state
        return original(flight, state, route=route, previous_flight=previous_flight, previous_route=previous_route,
                         previous_state=previous_state, **kwargs)

    monkeypatch.setattr(poll_loop.render, "build_canvas", _spy)
    clock["t"] += poll_loop.MIN_ADVANCE_INTERVAL_S + 30
    poll_loop.run_once(snapshot=_snapshot("dddddd", "FLIGHT4 ", 2400), state_dir=state_dir, geofence=GEOFENCE_PATH)
    assert captured.get("previous_flight", {}).get("hex") == "cccccc", (
        "build_canvas() was called with previous_flight=%r, expected hex=cccccc" % (captured.get("previous_flight"),))


def test_unresolved_prefix_registry_accumulates_across_cycles(tmp_path, clock):
    """the unresolved-prefix registry accumulates across two separate run_once() cycles against the same state directory, read back from poll_state.json on disk between cycles"""
    oz9_dir = _mkdir(tmp_path, "oz9")
    try:
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        state_after_1 = poll_loop.load_poll_state(oz9_dir)
        reg1 = state_after_1.get("unresolved_prefixes")
        if not isinstance(reg1, dict) or reg1.get("ZZQ", {}).get("count") != 1:
            pytest.fail("after cycle 1, unresolved_prefixes = %r, expected ZZQ at count 1" % (reg1,))

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("222222", "ZZQ5678", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        state_after_2 = poll_loop.load_poll_state(oz9_dir)
        reg2 = state_after_2.get("unresolved_prefixes")
        if list(reg2) != ["ZZQ"] or reg2["ZZQ"].get("count") != 2:
            pytest.fail("after cycle 2, unresolved_prefixes = %r, expected one entry ZZQ at count 2" % (reg2,))
        if reg2["ZZQ"].get("first_seen") != reg1["ZZQ"].get("first_seen"):
            pytest.fail("first_seen moved between cycles: %r -> %r" % (reg1["ZZQ"].get("first_seen"), reg2["ZZQ"].get("first_seen")))
        if reg2["ZZQ"].get("example_callsign") != "ZZQ5678":
            pytest.fail("example_callsign after cycle 2 = %r, expected 'ZZQ5678'" % (reg2["ZZQ"].get("example_callsign"),))
        return
    finally:
        shutil.rmtree(oz9_dir, ignore_errors=True)


def test_recognized_airline_leaves_registry_untouched(tmp_path, clock):
    """a cycle detecting a callsign whose prefix IS in _ICAO_AIRLINE_PREFIXES leaves unresolved_prefixes byte-identical - the registry is a list of gaps, not a log of every adsbdb miss"""
    oz9_dir = _mkdir(tmp_path, "oz9")
    try:
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        reg_before = poll_loop.load_poll_state(oz9_dir).get("unresolved_prefixes")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("333333", "AFR1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        reg_after = poll_loop.load_poll_state(oz9_dir).get("unresolved_prefixes")

        if reg_after != reg_before:
            pytest.fail("a recognized airline (AFR) changed the registry: %r -> %r" % (reg_before, reg_after))
        return
    finally:
        shutil.rmtree(oz9_dir, ignore_errors=True)


def test_journal_line_names_unknown_prefix(tmp_path, clock):
    """the poll_loop: line's unknown_prefix= field names the recorded prefix on a miss cycle, reads None on a covered cycle, and every pre-existing field is still present"""
    oz9_dir = _mkdir(tmp_path, "oz9")
    try:
        buf = io.StringIO()
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        miss_line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
        if "unknown_prefix=ZZQ" not in miss_line:
            pytest.fail("the poll line never names the recorded prefix: %s" % (miss_line,))

        buf = io.StringIO()
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=_snapshot("333333", "AFR1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
        covered_line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
        if "unknown_prefix=None" not in covered_line:
            pytest.fail("a covered prefix was named in the log field: %s" % (covered_line,))

        for field in ("hex=", "callsign=", "aircraft_type=", "corroborated=", "route_source=", "panel_changed="):
            for line in (miss_line, covered_line):
                if field not in line:
                    pytest.fail("existing log field %s was lost: %s" % (field, line))
        return
    finally:
        shutil.rmtree(oz9_dir, ignore_errors=True)


# --- mechanism-C mitigation: the bounded-age pending queue ---------------
#
# Everything below drives run_once() over a scripted timeline of fake
# seconds. `_drive()` models BOTH cadences that matter and that the bug
# lives between:
#   * the SERVER's 30s systemd-timer poll (POLL_INTERVAL_S), and
#   * the DEVICE's ~90s physical redraw floor (MIN_ADVANCE_INTERVAL_S), at
#     which it samples the two display slots - which is the only thing a
#     human ever actually sees.
# An aircraft that occupies the "current" slot only between two device
# samples was never on the glass. That, and not anything about
# poll_state.json's internals, is the user-visible symptom the tests below
# are written against.


def _drive(clock, state_dir, detections, until_s, poll_interval_s=None, draw_interval_s=None):
    """Run one poll every `poll_interval_s` of fake time from t=0 to
    `until_s`, feeding `detections.get(t)` as that poll's selection.

    Returns (cycles, frames) where `cycles` is one dict per poll (t,
    detected, shown, pending, dropped, line) and `frames` is the (current,
    previous) pair the device would have fetched at each of its own redraw
    opportunities.
    """
    poll_interval_s = poll_interval_s or poll_loop.POLL_INTERVAL_S
    draw_interval_s = draw_interval_s or poll_loop.MIN_ADVANCE_INTERVAL_S
    cycles = []
    frames = []
    for t in range(0, until_s + 1, poll_interval_s):
        clock["t"] = CLOCK_BASE + t
        detected = detections.get(t)
        snapshot = _snapshot(detected, "ZZQ%04d" % (abs(hash(detected)) % 10000), 2400) if detected else {"ac": []}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=snapshot, state_dir=state_dir, geofence=GEOFENCE_PATH)
        line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
        st = poll_loop.load_poll_state(state_dir)
        shown = (st.get("last_flight") or {}).get("hex")
        prev = (st.get("previous_flight") or {}).get("hex")
        pending = [e["flight"].get("hex") for e in poll_loop.normalise_pending(st.get("pending_flights"))]
        dropped_field = line.split("dropped=")[1].split(" ")[0]
        cycles.append({
            "t": t, "detected": detected, "shown": shown, "previous": prev,
            "pending": pending, "line": line,
            "dropped": [] if dropped_field == "None" else dropped_field.split(","),
        })
        if t % draw_interval_s == 0:
            frames.append((t, shown, prev))
    return cycles, frames


def _ever_on_glass(frames):
    seen = set()
    for _, cur, prev in frames:
        seen.update(h for h in (cur, prev) if h)
    return seen


def _promotions(cycles):
    """[(t, hex)] - each moment the "current" slot changed."""
    out = []
    last = None
    for c in cycles:
        if c["shown"] != last:
            out.append((c["t"], c["shown"]))
            last = c["shown"]
    return out


# The bug's own shape, from the diagnosis pass: four distinct aircraft
# selected on four consecutive 30s polls - i.e. more aircraft than the
# device can physically draw in that window - then an empty sky. The empty
# tail matters: a burst followed by silence is the common real shape, and
# a queue that only drained on detection cycles would strand everything in
# it.
BURST = {0: "a1a1a1", 30: "b2b2b2", 60: "c3c3c3", 90: "d4d4d4"}
BURST_UNTIL = 600

# A sustained burst: one distinct aircraft per poll for twelve consecutive
# polls, far faster than the device can consume them and far past the
# queue's depth cap. This is the pathological case the depth cap exists
# for.
SUSTAINED = {i * 30: "h%05d" % i for i in range(12)}
SUSTAINED_UNTIL = 1200


def test_prefix_burst_loses_an_aircraft_entirely_pre_fix(tmp_path, monkeypatch, clock):
    """PRECONDITION: with pacing disabled (pre-fix), a 4-aircraft burst inside one device redraw window leaves at least one aircraft that NEVER appears on any frame the device could fetch (mechanism C)"""
    # `advance_is_due` forced True is a faithful restoration of the
    # pre-fix implementation, not an approximation: with the gate always
    # open a distinct detection is enqueued and popped within the same
    # cycle, so the queue never accumulates, `pending_flights` stays
    # empty, and the "current" slot advances on every distinct detection -
    # exactly the pre-2026-08-28 behaviour, which is what let mechanism C
    # overwrite flights before the device could fetch them.
    monkeypatch.setattr(poll_loop, "advance_is_due", lambda *args, **kwargs: True)
    _, frames = _drive(clock, str(tmp_path), BURST, BURST_UNTIL)
    on_glass = _ever_on_glass(frames)
    missing = set(BURST.values()) - on_glass
    assert missing, (
        "with pacing disabled (the pre-fix behaviour) every aircraft still reached the glass - "
        "mechanism C is not reproducible by this timeline, so the regression tests below would prove "
        "nothing. frames=%r" % (frames,))


def test_paced_burst_shows_every_undropped_aircraft(tmp_path, clock):
    """REGRESSION (a): a burst of 4 distinct detections inside one ~90s device window puts every non-discarded aircraft on the glass, in first-detected (FIFO) order"""
    cycles, frames = _drive(clock, str(tmp_path), BURST, BURST_UNTIL)
    on_glass = _ever_on_glass(frames)
    discarded = {h for c in cycles for h in c["dropped"]}
    expected = set(BURST.values()) - discarded
    missing = expected - on_glass
    assert not missing, "aircraft never reached the glass despite never being discarded: %r (frames=%r)" % (
        sorted(missing), frames)
    # FIFO: the order aircraft reach the "current" slot must be the order
    # they were first detected.
    order = [h for _, h in _promotions(cycles) if h in BURST.values()]
    detection_order = [BURST[t] for t in sorted(BURST)]
    expected_order = [h for h in detection_order if h in order]
    assert order == expected_order, "promotion order %r is not the detection (FIFO) order %r" % (order, expected_order)
    assert len(on_glass & set(BURST.values())) >= 3, (
        "only %d of the burst's aircraft ever reached the glass, expected at least 3" % len(on_glass & set(BURST.values())))


def test_no_promotion_exceeds_the_staleness_bound(tmp_path, clock):
    """GUARD: no aircraft ever reaches the current display slot more than MAX_STALENESS_S (150s) after it was first detected - the bound that keeps this a real-time board rather than a backlog"""
    # Must hold in BOTH directions: pre-fix every promotion is instant
    # (age 0), so this passing pre-fix is expected and correct. It fails
    # only if the bound is ever abandoned - which is the failure mode an
    # unbounded "never drop a flight" queue would have had.
    cycles, _ = _drive(clock, str(tmp_path), BURST, BURST_UNTIL)
    first_detected = {h: t for t, h in sorted(BURST.items(), reverse=True)}
    for t, hex_code in _promotions(cycles):
        if hex_code not in first_detected:
            continue
        age = t - first_detected[hex_code]
        assert age <= poll_loop.MAX_STALENESS_S, (
            "%s reached the current slot %ds after it was first detected, bound is %ds" % (
                hex_code, age, poll_loop.MAX_STALENESS_S))


def test_expired_entries_are_skipped_not_stalled_behind(tmp_path, clock):
    """REGRESSION: a queued aircraft past MAX_STALENESS_S when its turn comes is discarded, named in the log line's dropped= field, and skipped PAST - a fresher entry behind it is promoted in the same cycle"""
    cycles, _ = _drive(clock, str(tmp_path), SUSTAINED, SUSTAINED_UNTIL)
    dropping = [c for c in cycles if c["dropped"]]
    assert dropping, "no cycle discarded anything - the staleness bound was never exercised"
    for hexes in (c["dropped"] for c in dropping):
        for h in hexes:
            assert h in SUSTAINED.values(), "dropped= named %r, which is not one of the detected aircraft" % (h,)
    # The skip-don't-stall property: at least one cycle must both discard
    # an expired entry AND still promote a fresher one.
    shown_before = None
    skipped = False
    for c in cycles:
        if c["dropped"] and c["shown"] != shown_before and c["shown"] is not None:
            skipped = True
        shown_before = c["shown"]
    assert skipped, (
        "every discard cycle left the current slot unchanged - an expired head entry is stalling "
        "the queue instead of being skipped past. cycles=%r" % ([(c["t"], c["shown"], c["dropped"]) for c in cycles],))
    # Nothing discarded may ever also have been displayed.
    discarded = {h for c in cycles for h in c["dropped"]}
    displayed = {h for _, h in _promotions(cycles)}
    both = discarded & displayed
    assert not both, "aircraft both discarded and displayed: %r" % (sorted(both),)


def test_sustained_burst_caps_the_queue_and_drops_oldest_first(tmp_path, clock):
    """REGRESSION (b): a sustained 12-aircraft burst never grows the pending queue past MAX_PENDING_FLIGHTS and never raises - it saturates at the cap and discards the OLDEST entries first"""
    cycles, _ = _drive(clock, str(tmp_path), SUSTAINED, SUSTAINED_UNTIL)
    for c in cycles:
        assert len(c["pending"]) <= poll_loop.MAX_PENDING_FLIGHTS, (
            "pending queue reached depth %d at t=%d, cap is %d (queue is growing unboundedly)" % (
                len(c["pending"]), c["t"], poll_loop.MAX_PENDING_FLIGHTS))
    burst_end = [c for c in cycles if c["t"] == max(SUSTAINED)][0]
    assert len(burst_end["pending"]) == poll_loop.MAX_PENDING_FLIGHTS, (
        "at the end of a 12-aircraft burst the queue holds %d entries, expected it saturated at %d: %r" % (
            len(burst_end["pending"]), poll_loop.MAX_PENDING_FLIGHTS, burst_end["pending"]))

    # Oldest-first, asserted PER CYCLE. Comparing the whole run's discards
    # against the final queue would be wrong: two different mechanisms
    # discard here (the depth cap during the burst, then the staleness
    # bound long after it), so a hex dropped late is naturally newer than
    # one still queued earlier. The real invariant is local - whatever a
    # cycle dropped came off the HEAD, so it must be older than everything
    # that cycle left behind.
    detected_at = {h: t for t, h in SUSTAINED.items()}
    for c in cycles:
        if not c["dropped"] or not c["pending"]:
            continue
        newest_dropped = max(detected_at[h] for h in c["dropped"])
        oldest_kept = min(detected_at[h] for h in c["pending"])
        assert newest_dropped <= oldest_kept, (
            "at t=%d the queue dropped %r (newest first detected t=%d) while keeping %r "
            "(oldest first detected t=%d) - eviction is not oldest-first"
            % (c["t"], c["dropped"], newest_dropped, c["pending"], oldest_kept))

    # ...and prove the DEPTH CAP itself fired, not just the staleness
    # bound: a discard while the queue was saturated and no entry could
    # yet have expired.
    cap_evictions = [
        c for c in cycles
        if c["dropped"] and c["t"] <= max(SUSTAINED)
        and all(c["t"] - detected_at[h] <= poll_loop.MAX_STALENESS_S for h in c["dropped"])
    ]
    assert cap_evictions, (
        "no discard happened while every dropped entry was still within the staleness bound - the "
        "depth cap never fired, so this test is only exercising the TTL. cycles=%r"
        % ([(c["t"], c["pending"], c["dropped"]) for c in cycles if c["dropped"]],))


def test_light_traffic_is_identical_to_pre_fix(tmp_path, clock):
    """GUARD (c): light traffic - one distinct aircraft every 120s - never queues, never discards, and shifts current->previous on the very same cycle it is detected (byte-identical to pre-fix behaviour)"""
    # Must hold in BOTH directions: if this ever fails post-fix, the
    # mitigation has started delaying the common case it was never
    # supposed to touch.
    #
    # One distinct aircraft every 120s - comfortably beyond the 90s floor
    # - each re-detected once 30s later, which is the real shape of a
    # runway-3 movement (58-110s corridor dwell against a 30s poll).
    light = {}
    for i, hex_code in enumerate(["e5e5e5", "f6f6f6", "070707", "181818"]):
        light[i * 120] = hex_code
        light[i * 120 + 30] = hex_code
    cycles, _ = _drive(clock, str(tmp_path), light, 600)
    for c in cycles:
        assert not c["pending"], (
            "light traffic queued something at t=%d: %r (the common case must never be delayed)" % (c["t"], c["pending"]))
        assert not c["dropped"], "light traffic discarded something at t=%d: %r" % (c["t"], c["dropped"])
        if c["detected"] is not None:
            assert c["shown"] == c["detected"], (
                "at t=%d the poll detected %s but the current slot holds %s - a well-spaced detection was "
                "delayed" % (c["t"], c["detected"], c["shown"]))
    # ...and the two-deep shift still happens on the same cycle.
    at_120 = [c for c in cycles if c["t"] == 120][0]
    assert at_120["previous"] == "e5e5e5", (
        "the outgoing current aircraft did not shift into previous on the same cycle: %r" % (at_120,))


def test_queue_survives_the_process_boundary(tmp_path, clock):
    """REGRESSION: a deferred detection and its last_advance_at timestamp are written to poll_state.json and read back from disk by the next run_once() - the queue survives the systemd oneshot boundary (D-P2-02)"""
    persist_dir = str(tmp_path)
    clock["t"] = CLOCK_BASE
    poll_loop.run_once(snapshot=_snapshot("aa11aa", "ZZQ0001", 2400), state_dir=persist_dir, geofence=GEOFENCE_PATH)
    clock["t"] = CLOCK_BASE + 30
    poll_loop.run_once(snapshot=_snapshot("bb22bb", "ZZQ0002", 2400), state_dir=persist_dir, geofence=GEOFENCE_PATH)

    # Read back from DISK - the only assertion in this test that proves
    # the queue crosses the oneshot's boundary.
    on_disk = poll_loop.load_poll_state(persist_dir)
    queued = poll_loop.normalise_pending(on_disk.get("pending_flights"))
    assert [e["flight"].get("hex") for e in queued] == ["bb22bb"], (
        "pending_flights on disk is %r, expected the deferred bb22bb" % (on_disk.get("pending_flights"),))
    assert poll_loop._as_timestamp(on_disk.get("last_advance_at")) == CLOCK_BASE, (
        "last_advance_at on disk is %r, expected the first cycle's timestamp" % (on_disk.get("last_advance_at"),))
    assert on_disk.get("last_flight", {}).get("hex") == "aa11aa", (
        "the deferred aircraft was displayed anyway: %r" % (on_disk.get("last_flight"),))


def test_malformed_queue_state_degrades_instead_of_raising(tmp_path, clock):
    """GUARD: a malformed pending_flights / last_advance_at in poll_state.json degrades to an empty queue and completes the cycle, never raising (load_poll_state()'s never-a-crash discipline, D-P2-02)"""
    persist_dir = str(tmp_path)
    clock["t"] = CLOCK_BASE
    poll_loop.run_once(snapshot=_snapshot("aa11aa", "ZZQ0001", 2400), state_dir=persist_dir, geofence=GEOFENCE_PATH)
    on_disk = poll_loop.load_poll_state(persist_dir)
    # Hand-corrupt every field the queue reads - non-list, non-dict
    # entries, a missing flight, an unusable first_seen, a non-numeric
    # timestamp.
    on_disk["pending_flights"] = [{"nope": 1}, "garbage", {"flight": {"hex": "x"}, "first_seen": "soon"}, 7]
    on_disk["last_advance_at"] = "half past four"
    poll_loop.save_poll_state(persist_dir, on_disk)

    clock["t"] = CLOCK_BASE + 60
    poll_loop.run_once(snapshot=_snapshot("cc33cc", "ZZQ0003", 2400), state_dir=persist_dir, geofence=GEOFENCE_PATH)
    recovered = poll_loop.load_poll_state(persist_dir)
    assert not poll_loop.normalise_pending(recovered.get("pending_flights")), (
        "malformed entries survived normalisation: %r" % (recovered.get("pending_flights"),))
    assert recovered.get("last_flight", {}).get("hex") in ("aa11aa", "cc33cc"), (
        "the cycle after a corrupt state file left an unexpected display slot: %r" % (recovered.get("last_flight"),))
    assert poll_loop.normalise_pending("not even a list") == [] and poll_loop._as_timestamp(True) is None, (
        "normalise_pending()/_as_timestamp() do not degrade on hostile input")


def test_log_line_contract_is_intact(tmp_path, clock):
    """GUARD: every poll line still carries all eleven pre-existing fields and additionally shown=, pending= and dropped= - on every cycle, not only on interesting ones"""
    cycles, _ = _drive(clock, str(tmp_path), BURST, 200)
    for c in cycles:
        for field in ("hex=", "callsign=", "aircraft_type=", "corroborated=", "altitude_ft=",
                      "confirmed_state=", "render_state=", "state_source=", "route_source=",
                      "unknown_prefix=", "shown=", "pending=", "dropped=", "panel_changed="):
            assert field in c["line"], "log field %s missing at t=%d: %s" % (field, c["t"], c["line"])


def test_a_deferred_cycle_is_distinguishable_in_the_log(tmp_path, clock):
    """REGRESSION: a cycle that defers a detection is legible in the log - hex= names the detection, shown= names the different aircraft on the panel, pending= is non-zero, and panel_changed=False"""
    # Deliberately independent of the "the fields exist" GUARD above -
    # lumping "the fields exist" together with "a deferral is
    # distinguishable" would blur a guard with a regression.
    cycles, _ = _drive(clock, str(tmp_path), BURST, 200)
    deferring = [c for c in cycles if c["detected"] and c["shown"] != c["detected"]]
    assert deferring, "no cycle in the burst deferred a detection - a distinct new aircraft was displayed immediately"
    c = deferring[0]
    assert "hex=%s" % c["detected"] in c["line"], (
        "hex= no longer names THIS CYCLE'S DETECTION (%s): %s" % (c["detected"], c["line"]))
    assert "shown=%s" % c["shown"] in c["line"], (
        "shown= does not name the aircraft in the current slot (%s): %s" % (c["shown"], c["line"]))
    assert ("pending=%d" % len(c["pending"]) in c["line"]) and ("pending=0" not in c["line"]), (
        "pending= does not name the real queue depth (%d): %s" % (len(c["pending"]), c["line"]))
    assert "panel_changed=False" in c["line"], (
        "a deferred cycle rewrote the panel - the whole point is that it must not: %s" % (c["line"],))


def test_hysteresis_truth_table():
    """apply_battery_hysteresis()'s truth table: threshold-inclusive disarm (<=3500 sets True), clear-inclusive re-arm (>=3600 clears True) - a reading strictly between the two constants holds the previous decision in both directions (Pitfall 5)"""
    f = poll_loop.apply_battery_hysteresis
    cases = [
        # (battery_mv, was_active, expected)
        (3499, False, True), (3500, False, True), (3501, False, False),
        (3599, False, False), (3600, False, False),
        (3400, True, True), (3500, True, True), (3550, True, True),
        (3599, True, True), (3600, True, False), (3700, True, False),
    ]
    for mv, was_active, expected in cases:
        result = f(mv, was_active)
        if result != expected:
            pytest.fail("apply_battery_hysteresis(%r, was_active=%r) = %r, expected %r" % (mv, was_active, result, expected))


def test_never_reported_reading_holds():
    """apply_battery_hysteresis(None, was_active) holds was_active unchanged - a device that has never reported must not spuriously show the icon, and an unreadable file must not spuriously clear a real warning"""
    if poll_loop.apply_battery_hysteresis(None, False) is not False:
        pytest.fail("apply_battery_hysteresis(None, False) is not False")
    if poll_loop.apply_battery_hysteresis(None, True) is not True:
        pytest.fail("apply_battery_hysteresis(None, True) is not True")


def test_load_battery_state_degrades_never_raises(tmp_path):
    """load_battery_state() returns None for a missing file, invalid JSON, a JSON list, a dict with no battery_mv key, and a battery_mv that is a string/bool/float/negative/zero - and the int for a well-formed state"""
    d = _mkdir(tmp_path, "battery-state")
    try:
        path = os.path.join(d, "battery_state.json")

        def _write_raw(text):
            with open(path, "w") as fh:
                fh.write(text)

        def _write_json(obj):
            with open(path, "w") as fh:
                json.dump(obj, fh)

        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("missing file: expected None")
        _write_raw("{not valid json")
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("invalid JSON: expected None")
        _write_json([1, 2, 3])
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a JSON list (non-dict payload): expected None")
        _write_json({"other": 1})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a dict with no battery_mv key: expected None")
        _write_json({"battery_mv": "3400"})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a string battery_mv: expected None")
        _write_json({"battery_mv": True})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a bool battery_mv: expected None")
        _write_json({"battery_mv": 3400.5})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a float battery_mv: expected None")
        _write_json({"battery_mv": -1})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("a negative int battery_mv: expected None")
        _write_json({"battery_mv": 0})
        if poll_loop.load_battery_state(d) is not None:
            pytest.fail("battery_mv=0: expected None")
        _write_json({"battery_mv": 3400, "received_at": 1.0})
        if poll_loop.load_battery_state(d) != 3400:
            pytest.fail("a well-formed state: expected 3400, got %r" % (poll_loop.load_battery_state(d),))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_cross_cycle_persistence_and_hold_branch_rerender(tmp_path):
    """the battery decision survives run_once()'s process boundary in poll_state.json, and the hold branch re-renders panel.bin exactly when the battery decision genuinely flips (not on every hold cycle, and even with no aircraft detected at all)"""
    d = _mkdir(tmp_path, "battery-d")
    try:
        panel_path = os.path.join(d, "panel.bin")

        # (1) A detection cycle with a low reading already on
        # disk: battery_low_active flips True and the log line
        # says so.
        _write_battery_state(d, 3400)
        poll_loop.run_once(snapshot=_snapshot("eeeeee", "FLIGHT5 ", CLIMB), state_dir=d, geofence=GEOFENCE_PATH)
        state1 = poll_loop.load_poll_state(d)
        if state1.get("battery_low_active") is not True:
            pytest.fail("after a detection cycle with battery_mv=3400, battery_low_active = %r, expected True" % (state1.get("battery_low_active"),))
        with open(panel_path, "rb") as fh:
            panel_after_detection = fh.read()

        # (2) A hold cycle (empty snapshot, a flight already on
        # screen) with the reading flipped to a clearing value:
        # panel_changed is True, panel.bin's bytes changed, and
        # battery_low_active flips False - the warning can clear
        # on a cycle with no detection at all.
        _write_battery_state(d, 3700)
        result2 = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=d, geofence=GEOFENCE_PATH)
        state2 = poll_loop.load_poll_state(d)
        if state2.get("battery_low_active") is not False:
            pytest.fail("after a battery flip to 3700 on a hold cycle, battery_low_active = %r, expected False" % (state2.get("battery_low_active"),))
        if result2.get("panel_changed") is not True:
            pytest.fail("hold-cycle re-render on a genuine battery flip: panel_changed = %r, expected True" % (result2.get("panel_changed"),))
        with open(panel_path, "rb") as fh:
            panel_after_flip = fh.read()
        if panel_after_flip == panel_after_detection:
            pytest.fail("panel.bin bytes did not change after the battery-flip hold-cycle re-render")

        # (3) Another hold cycle, same 3700 reading (no flip):
        # panel_changed is False and panel.bin is byte-identical
        # - the re-render fires only on a genuine flip, not
        # every hold cycle.
        result3 = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=d, geofence=GEOFENCE_PATH)
        if result3.get("panel_changed") is not False:
            pytest.fail("hold-cycle with an unchanged battery reading: panel_changed = %r, expected False" % (result3.get("panel_changed"),))
        with open(panel_path, "rb") as fh:
            panel_after_repeat = fh.read()
        if panel_after_repeat != panel_after_flip:
            pytest.fail("panel.bin changed on a hold-cycle with no genuine battery flip")
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_runway_ids_agree_across_device_config_and_geofence():
    """device_config.RUNWAYS and the geofence file's own runway id set agree exactly"""
    geofence = detect.load_geofence(GEOFENCE_PATH)
    geofence_ids = set(geofence.get("runways") or {})
    config_ids = set(device_config.RUNWAYS)
    if config_ids != geofence_ids:
        pytest.fail("device_config.RUNWAYS=%r does not match adsb-test/runway3.json's runways=%r - "
            "the two runway-id sets must agree" % (sorted(config_ids), sorted(geofence_ids)))


def test_default_config_byte_identity(tmp_path):
    """a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest"""
    # Linux (CI + the production VPS) is authoritative here, so a
    # mismatch fails there; elsewhere it degrades to an
    # informational note - see _digest_verdict().
    digest_dir = _mkdir(tmp_path, "digest")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=digest_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(digest_dir, "panel.bin"), "rb") as fh:
            data = fh.read()
        digest = hashlib.sha256(data).hexdigest()
        ok, reason = _digest_verdict(digest, _DEFAULT_CONFIG_DIGEST)
        assert ok, reason
    finally:
        shutil.rmtree(digest_dir, ignore_errors=True)


def test_non_default_runway_reaches_select_aircraft_for_runway(tmp_path, monkeypatch):
    """a saved non-default tracked runway reaches detect.select_aircraft_for_runway on the injected-snapshot branch"""
    runway_dir = _mkdir(tmp_path, "runway")
    try:
        device_config.save_device_config(runway_dir, tracked_runway="06-24")
        captured = {}
        original = detect.select_aircraft_for_runway

        def _spy(aircraft, geofence, runway_id=device_config.DEFAULT_RUNWAY_ID):
            captured["runway_id"] = runway_id
            return original(aircraft, geofence, runway_id=runway_id)

        monkeypatch.setattr(poll_loop.detect, "select_aircraft_for_runway", _spy)
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=runway_dir, geofence=GEOFENCE_PATH)
        if captured.get("runway_id") != "06-24":
            pytest.fail("select_aircraft_for_runway received runway_id=%r, expected '06-24'" % (captured.get("runway_id"),))
        return
    finally:
        shutil.rmtree(runway_dir, ignore_errors=True)


def test_non_default_runway_reaches_poll_current_aircraft(tmp_path, monkeypatch):
    """a saved non-default tracked runway reaches detect.poll_current_aircraft on the live branch"""
    runway_dir = _mkdir(tmp_path, "runway-live")
    try:
        device_config.save_device_config(runway_dir, tracked_runway="02-20")
        captured = {}

        def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
            captured["runway_id"] = runway_id
            if diagnostics is not None:
                diagnostics.update({"queried": [], "failed": [], "selected": [], "disagreement": False, "runway_id": runway_id})
            return None

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        poll_loop.run_once(state_dir=runway_dir, geofence=GEOFENCE_PATH)
        if captured.get("runway_id") != "02-20":
            pytest.fail("poll_current_aircraft received runway_id=%r, expected '02-20'" % (captured.get("runway_id"),))
        return
    finally:
        shutil.rmtree(runway_dir, ignore_errors=True)


def test_all_failed_diagnostics_yields_true_fault_flag(tmp_path, monkeypatch):
    """an all-providers-failed diagnostics report yields a true source_fault flag passed to render.build_canvas"""
    fault_dir = _mkdir(tmp_path, "fault")
    try:
        def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
            if diagnostics is not None:
                diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": ["adsbfi", "adsblol"], "selected": [], "disagreement": False, "runway_id": runway_id})
            return None

        captured = {}
        original_build = poll_loop.render.build_canvas

        def _spy_build(flight, state, **kwargs):
            captured["source_fault"] = kwargs.get("source_fault")
            return original_build(flight, state, **kwargs)

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        monkeypatch.setattr(poll_loop.render, "build_canvas", _spy_build)
        result = poll_loop.run_once(state_dir=fault_dir, geofence=GEOFENCE_PATH)
        if result.get("source_fault") is not True:
            pytest.fail("run_once() result source_fault=%r, expected True" % (result.get("source_fault"),))
        if captured.get("source_fault") is not True:
            pytest.fail("render.build_canvas() received source_fault=%r, expected True" % (captured.get("source_fault"),))
        return
    finally:
        shutil.rmtree(fault_dir, ignore_errors=True)


def test_successful_query_no_selection_yields_false_fault_flag(tmp_path, monkeypatch):
    """providers queried successfully with nothing selected leaves the source_fault flag false"""
    fault_dir = _mkdir(tmp_path, "nofault")
    try:
        def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
            if diagnostics is not None:
                diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": [], "selected": [], "disagreement": False, "runway_id": runway_id})
            return None

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        result = poll_loop.run_once(state_dir=fault_dir, geofence=GEOFENCE_PATH)
        if result.get("source_fault") is not False:
            pytest.fail("run_once() result source_fault=%r, expected False" % (result.get("source_fault"),))
        return
    finally:
        shutil.rmtree(fault_dir, ignore_errors=True)


def test_injected_snapshot_branch_never_sets_fault(tmp_path):
    """the injected-snapshot branch never sets the source_fault flag, regardless of a previously-persisted true value"""
    snap_dir = _mkdir(tmp_path, "snapfault")
    try:
        with history_db.open_db(snap_dir) as conn:
            history_db.set_meta(conn, history_db.META_SOURCE_FAULT, "True")
        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=snap_dir, geofence=GEOFENCE_PATH)
        if result.get("source_fault") is not False:
            pytest.fail("injected-snapshot branch returned source_fault=%r, expected False" % (result.get("source_fault"),))
        return
    finally:
        shutil.rmtree(snap_dir, ignore_errors=True)


def test_fault_transition_gated_not_value(tmp_path, monkeypatch):
    """two consecutive cycles with an unchanged true fault flag and no new detection write panel.bin exactly once, not twice"""
    trans_dir = _mkdir(tmp_path, "transition")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=trans_dir, geofence=GEOFENCE_PATH)

        def _fake_poll_all_failed(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
            if diagnostics is not None:
                diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": ["adsbfi", "adsblol"], "selected": [], "disagreement": False, "runway_id": runway_id})
            return None

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll_all_failed)
        r1 = poll_loop.run_once(state_dir=trans_dir, geofence=GEOFENCE_PATH)
        r2 = poll_loop.run_once(state_dir=trans_dir, geofence=GEOFENCE_PATH)
        writes = sum(1 for r in (r1, r2) if r.get("panel_changed"))
        if writes != 1:
            pytest.fail("two consecutive cycles with an unchanged true fault flag wrote panel.bin %d times, expected exactly 1" % (writes,))
        return
    finally:
        shutil.rmtree(trans_dir, ignore_errors=True)


def test_log_line_gains_theme_runway_fault_fields(tmp_path):
    """the poll_loop: log line gains theme=/tracked_runway=/source_fault= fields and stays a single print() per cycle"""
    log_dir = _mkdir(tmp_path, "logfields")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=log_dir, geofence=GEOFENCE_PATH)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: hex=")]
        if len(lines) != 1:
            pytest.fail("expected exactly one 'poll_loop: hex=' line, found %d" % (len(lines),))
        line = lines[0]
        for field in ("theme=", "tracked_runway=", "source_fault="):
            if field not in line:
                pytest.fail("log line missing new field %s: %s" % (field, line))
        return
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_history_row_written_only_on_hex_transition(tmp_path):
    """detecting a new aircraft writes exactly one runway_events row; re-detecting it unchanged writes no further row"""
    hist_dir = _mkdir(tmp_path, "hist-hex")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(hist_dir) as conn:
            count1 = len(history_db.recent_runway_events(conn, limit=100))
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(hist_dir) as conn:
            count2 = len(history_db.recent_runway_events(conn, limit=100))
        if count1 != 1:
            pytest.fail("first-ever detection produced %d runway_events rows, expected exactly 1" % (count1,))
        if count2 != 1:
            pytest.fail("re-detecting the same hex with an unchanged state produced %d total rows, expected still 1" % (count2,))
        return
    finally:
        shutil.rmtree(hist_dir, ignore_errors=True)


def test_history_row_written_on_confirmed_state_flip(tmp_path):
    """a confirmed_state flip on the same hex writes a new runway_events row"""
    hist_dir = _mkdir(tmp_path, "hist-state")
    try:
        DESCEND = -2400
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", DESCEND), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(hist_dir) as conn:
            rows = history_db.recent_runway_events(conn, limit=100)
        if len(rows) != 2:
            pytest.fail("a confirmed_state flip on the same hex produced %d total rows, expected 2" % (len(rows),))
        states = sorted(r["confirmed_state"] for r in rows)
        if states != ["arriving", "departing"]:
            pytest.fail("expected one departing and one arriving row, got %r" % (states,))
        return
    finally:
        shutil.rmtree(hist_dir, ignore_errors=True)


def test_history_row_written_on_corroboration_flip(tmp_path, monkeypatch):
    """a corroboration flip on the same hex/confirmed_state writes a new runway_events row"""
    hist_dir = _mkdir(tmp_path, "hist-corrob")
    try:
        base_flight = {
            "hex": "aaaaaa", "callsign": "FLIGHT1", "aircraft_type": None,
            "altitude_ft": 450.0, "on_ground": False, "vertical_rate_fpm": CLIMB,
            "lat": 48.7233, "lon": 2.3794, "gs": 137.1, "seen_pos": 1.0,
            "along_track_m": 0.0, "cross_track_m": 0.0, "track_deg": None,
            "track_deviation_deg": None, "selected_runway": "3",
        }
        calls = {"n": 0}

        def _spy(aircraft, geofence, runway_id=device_config.DEFAULT_RUNWAY_ID):
            calls["n"] += 1
            flight = dict(base_flight)
            flight["corroborated"] = True if calls["n"] == 1 else False
            return flight

        monkeypatch.setattr(poll_loop.detect, "select_aircraft_for_runway", _spy)
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(hist_dir) as conn:
            rows = history_db.recent_runway_events(conn, limit=100)
        if len(rows) != 2:
            pytest.fail("a corroboration flip on the same hex/state produced %d total rows, expected 2" % (len(rows),))
        corroborated_values = sorted(r["corroborated"] for r in rows)
        if corroborated_values != ["False", "True"]:
            pytest.fail("expected one True and one False corroborated row, got %r" % (corroborated_values,))
        return
    finally:
        shutil.rmtree(hist_dir, ignore_errors=True)


def test_pipeline_run_meta_updated_every_cycle(tmp_path):
    """the pipeline-run meta timestamp updates on every cycle, including one that writes no runway_events row"""
    meta_dir = _mkdir(tmp_path, "meta")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=meta_dir, geofence=GEOFENCE_PATH)
        # A known sentinel in between makes the second (no-new-
        # row) cycle's write provable without depending on
        # wall-clock time actually advancing between two fast
        # consecutive calls (meta timestamps are second-precision).
        with history_db.open_db(meta_dir) as conn:
            history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, "SENTINEL")
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=meta_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(meta_dir) as conn:
            ts_after = history_db.get_meta(conn, history_db.META_LAST_PIPELINE_RUN)
            rows = history_db.recent_runway_events(conn, limit=100)
        if len(rows) != 1:
            pytest.fail("expected the second (unchanged) cycle to write no new row, found %d total" % (len(rows),))
        if ts_after == "SENTINEL" or not ts_after:
            pytest.fail("pipeline-run meta timestamp was not rewritten on a no-new-row cycle: %r" % (ts_after,))
        return
    finally:
        shutil.rmtree(meta_dir, ignore_errors=True)


def test_gallery_archives_only_changed_panels(tmp_path):
    """a panel write with changed bytes saves one image into the gallery; an unchanged-bytes cycle saves none"""
    gal_dir = _mkdir(tmp_path, "gallery-changed")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=gal_dir, geofence=GEOFENCE_PATH)
        entries_after_1 = os.listdir(os.path.join(gal_dir, "gallery"))
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=gal_dir, geofence=GEOFENCE_PATH)
        entries_after_2 = os.listdir(os.path.join(gal_dir, "gallery"))
        if len(entries_after_1) != 1:
            pytest.fail("a changed-bytes cycle produced %d gallery entries, expected 1" % (len(entries_after_1),))
        if len(entries_after_2) != len(entries_after_1):
            pytest.fail("an unchanged-bytes cycle changed the gallery entry count: %d -> %d" % (len(entries_after_1), len(entries_after_2)))
        return
    finally:
        shutil.rmtree(gal_dir, ignore_errors=True)


def test_gallery_prunes_to_max_entries(tmp_path):
    """the gallery never holds more than GALLERY_MAX_ENTRIES; the oldest entries are removed first"""
    cap_dir = _mkdir(tmp_path, "gallery-cap")
    try:
        gallery_dir = os.path.join(cap_dir, "gallery")
        os.makedirs(gallery_dir)
        for i in range(30):
            with open(os.path.join(gallery_dir, "2020-01-01T00-00-%02d+00-00.png" % i), "wb") as fh:
                fh.write(b"x")
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=cap_dir, geofence=GEOFENCE_PATH)
        entries = sorted(os.listdir(gallery_dir))
        if len(entries) != poll_loop.GALLERY_MAX_ENTRIES:
            pytest.fail("gallery holds %d entries after a changed cycle, expected exactly GALLERY_MAX_ENTRIES=%d" % (len(entries), poll_loop.GALLERY_MAX_ENTRIES))
        if "2020-01-01T00-00-00+00-00.png" in entries:
            pytest.fail("the oldest seeded entry was not pruned: %r" % (entries,))
        return
    finally:
        shutil.rmtree(cap_dir, ignore_errors=True)


@requires_non_root
def test_readonly_gallery_dir_does_not_fail_cycle(tmp_path):
    """a read-only gallery directory does not fail the cycle - run_once() still returns and panel.bin is still written"""
    ro_dir = _mkdir(tmp_path, "gallery-ro")
    try:
        gallery_dir = os.path.join(ro_dir, "gallery")
        os.makedirs(gallery_dir)
        os.chmod(gallery_dir, 0o500)
        try:
            result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=ro_dir, geofence=GEOFENCE_PATH)
        finally:
            os.chmod(gallery_dir, 0o700)
        if not result.get("panel_changed"):
            pytest.fail("run_once() reported panel_changed=%r, expected True" % (result.get("panel_changed"),))
        if not os.path.exists(os.path.join(ro_dir, "panel.bin")):
            pytest.fail("panel.bin was not written when the gallery directory was read-only")
        return
    finally:
        shutil.rmtree(ro_dir, ignore_errors=True)


def test_history_write_failure_does_not_fail_cycle(tmp_path, monkeypatch):
    """a history.db failure (open_db raising) is caught and logged without failing the cycle or leaving panel.bin unwritten"""
    hist_fail_dir = _mkdir(tmp_path, "histfail")
    try:
        def _boom(*args, **kwargs):
            raise sqlite3.OperationalError("simulated lock")

        monkeypatch.setattr(poll_loop.history_db, "open_db", _boom)
        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_fail_dir, geofence=GEOFENCE_PATH)
        if not result.get("panel_changed"):
            pytest.fail("run_once() reported panel_changed=%r, expected True" % (result.get("panel_changed"),))
        if not os.path.exists(os.path.join(hist_fail_dir, "panel.bin")):
            pytest.fail("panel.bin was not written when history_db.open_db raised")
        return
    finally:
        shutil.rmtree(hist_fail_dir, ignore_errors=True)


def test_poll_loop_never_writes_device_config(tmp_path):
    """device_config.json is byte-identical before and after a poll cycle - poll_loop.py reads it and never writes it"""
    cfg_dir = _mkdir(tmp_path, "cfgwrite")
    try:
        device_config.save_device_config(cfg_dir, theme="black", tracked_runway="3")
        path = device_config.device_config_path(cfg_dir)
        with open(path, "rb") as fh:
            before = fh.read()
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=cfg_dir, geofence=GEOFENCE_PATH)
        with open(path, "rb") as fh:
            after = fh.read()
        if before != after:
            pytest.fail("device_config.json changed after a poll cycle - poll_loop.py must only ever read it")
        return
    finally:
        shutil.rmtree(cfg_dir, ignore_errors=True)


def test_corrupted_device_config_falls_back_to_defaults(tmp_path):
    """a corrupted device_config.json (invalid JSON) still yields a completed cycle using the documented defaults"""
    bad_dir = _mkdir(tmp_path, "badcfg")
    try:
        os.makedirs(bad_dir, exist_ok=True)
        with open(device_config.device_config_path(bad_dir), "w") as fh:
            fh.write("{not valid json")
        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=bad_dir, geofence=GEOFENCE_PATH)
        if result.get("theme") != device_config.DEFAULT_THEME_ID:
            pytest.fail("corrupted device_config.json yielded theme=%r, expected the default %r" % (result.get("theme"), device_config.DEFAULT_THEME_ID))
        if result.get("tracked_runway") != device_config.DEFAULT_RUNWAY_ID:
            pytest.fail("corrupted device_config.json yielded tracked_runway=%r, expected the default %r" % (result.get("tracked_runway"), device_config.DEFAULT_RUNWAY_ID))
        return
    finally:
        shutil.rmtree(bad_dir, ignore_errors=True)


def test_caddy_log_ingestion_wired_into_poll_cycle(tmp_path):
    """a run_once() cycle given --caddy-log ingests a real access-log line into device_health"""
    log_dir = _mkdir(tmp_path, "caddylog")
    try:
        log_path = os.path.join(log_dir, "caddy-access.log")
        with open(log_path, "w") as fh:
            fh.write(json.dumps({
                "ts": 1_700_000_000.0,
                "request": {
                    "uri": "/device/v1/display",
                    "headers": {"X-Battery-Mv": ["4090"]},
                },
            }) + "\n")
        poll_loop.run_once(
            snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB),
            state_dir=log_dir, geofence=GEOFENCE_PATH, caddy_log=log_path,
        )
        with history_db.open_db(log_dir) as conn:
            rows = history_db.recent_device_health(conn, limit=5)
        if not any(r.get("battery_mv") == 4090 for r in rows):
            pytest.fail("expected a device_health row with battery_mv=4090, got %r" % (rows,))
        return
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)


def test_caddy_log_omitted_is_noop(tmp_path):
    """omitting --caddy-log (the default) ingests nothing and raises nothing"""
    none_dir = _mkdir(tmp_path, "nocaddylog")
    try:
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=none_dir, geofence=GEOFENCE_PATH)
        with history_db.open_db(none_dir) as conn:
            rows = history_db.recent_device_health(conn, limit=5)
        if rows:
            pytest.fail("expected zero device_health rows with caddy_log omitted, got %r" % (rows,))
        return
    finally:
        shutil.rmtree(none_dir, ignore_errors=True)


def test_digest_verdict_is_linux_strict_and_non_linux_informational(monkeypatch):
    """the pinned-digest verdict is Linux-strict and non-Linux-informational - both branches proven by forcing platform.system()"""
    # A pure/hermetic proof: _digest_verdict() is pure, so this needs no
    # run_once(), no temp dir and no render - just two deliberately-
    # different 64-char hex stand-ins. Never mutates _DEFAULT_CONFIG_DIGEST,
    # never touches disk. `platform.system` is monkeypatched (not manually
    # saved/restored) to prove both branches of the REAL _digest_verdict()
    # (not a copy of it) by forcing platform.system() at call time.
    sample = "a" * 64
    bogus = "b" * 64

    # (b) the strict branch is genuinely preserved: forced "Linux", the
    # identical arguments must return (False, reason) naming both digests,
    # and print nothing. Checked FIRST (ahead of (a)) because this is the
    # exact assertion an inverted condition breaks.
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    buf_b = io.StringIO()
    with contextlib.redirect_stdout(buf_b):
        ok_b, reason_b = _digest_verdict(sample, bogus)
    out_b = buf_b.getvalue()
    assert ok_b is False, "(b) forced Linux mismatch returned ok=%r, expected False" % (ok_b,)
    assert sample in reason_b and bogus in reason_b, (
        "(b) forced Linux mismatch reason %r does not name both %r and %r" % (reason_b, sample, bogus))
    assert not out_b, "(b) forced Linux mismatch printed %r, expected nothing" % (out_b,)

    # (a) the softened branch is real: forced "Darwin", a mismatch must
    # still return (True, "") AND must print a line starting with "NOTE "
    # - returning true silently would hide the mismatch from the
    # developer entirely.
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    buf_a = io.StringIO()
    with contextlib.redirect_stdout(buf_a):
        result_a = _digest_verdict(sample, bogus)
    out_a = buf_a.getvalue()
    assert result_a == (True, ""), "(a) forced Darwin mismatch returned %r, expected (True, '')" % (result_a,)
    assert any(ln.startswith("NOTE ") for ln in out_a.splitlines()), (
        "(a) forced Darwin mismatch printed %r, expected a line starting with 'NOTE '" % (out_a,))

    # (c) the helper is not degenerate: a matching digest never emits a
    # note and never fails, under EITHER forced platform.
    for forced in ("Darwin", "Linux"):
        monkeypatch.setattr(platform, "system", lambda forced=forced: forced)
        buf_c = io.StringIO()
        with contextlib.redirect_stdout(buf_c):
            result_c = _digest_verdict(sample, sample)
        out_c = buf_c.getvalue()
        assert result_c == (True, ""), (
            "(c) matching digest under forced %s returned %r, expected (True, '')" % (forced, result_c))
        assert not out_c, "(c) matching digest under forced %s printed %r, expected nothing" % (forced, out_c)


def test_quiet_hours_entry_renders_once_and_persists_flag(tmp_path, clock):
    """window entry renders the QUIET HOURS canvas exactly once and persists hold_state='quiet_hours'"""
    qh_dir = _mkdir(tmp_path, "quiet-entry")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "quiet_hours":
            pytest.fail("entry cycle returned state=%r, expected 'quiet_hours'" % (result.get("state"),))
        if not result.get("panel_changed"):
            pytest.fail("entry cycle returned panel_changed=%r, expected True" % (result.get("panel_changed"),))
        on_disk = poll_loop.load_poll_state(qh_dir)
        if on_disk.get("hold_state") != "quiet_hours":
            pytest.fail("poll_state.json's hold_state is %r, expected 'quiet_hours'" % (on_disk.get("hold_state"),))
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_hold_is_noop(tmp_path, clock):
    """a second in-window cycle is a no-op - panel_changed is False and panel.bin's bytes are unchanged"""
    qh_dir = _mkdir(tmp_path, "quiet-hold")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(qh_dir, "panel.bin"), "rb") as fh:
            first_bytes = fh.read()
        clock["t"] = CLOCK_BASE + 60  # still inside the window
        result = poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "quiet_hours":
            pytest.fail("hold cycle returned state=%r, expected 'quiet_hours'" % (result.get("state"),))
        if result.get("panel_changed"):
            pytest.fail("hold cycle returned panel_changed=True, expected False - a mid-window cycle must not re-render")
        with open(os.path.join(qh_dir, "panel.bin"), "rb") as fh:
            second_bytes = fh.read()
        if second_bytes != first_bytes:
            pytest.fail("panel.bin's bytes changed on a hold cycle, expected them unchanged")
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_panel_matches_expected_canvas(tmp_path, clock):
    """the rendered panel is exactly render.build_canvas(None, 'quiet_hours', quiet_hours_until='07:00')"""
    qh_dir = _mkdir(tmp_path, "quiet-canvas")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(qh_dir, "panel.bin"), "rb") as fh:
            actual = fh.read()
        expected = poll_loop.panel_format.pack_panel(
            poll_loop.render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00")
        )
        if actual != expected:
            pytest.fail("panel.bin does not equal panel_format.pack_panel(render.build_canvas(None, 'quiet_hours', quiet_hours_until='07:00'))")
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_skips_ads_b_detection(tmp_path, monkeypatch, clock):
    """an in-window cycle on the live path never calls detect.poll_current_aircraft or detect.load_geofence"""
    qh_dir = _mkdir(tmp_path, "quiet-skip")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        called = {"poll": False, "geofence": False}

        def _fake_poll(*args, **kwargs):
            called["poll"] = True
            return None

        def _fake_geofence(*args, **kwargs):
            called["geofence"] = True
            return {}

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        monkeypatch.setattr(poll_loop.detect, "load_geofence", _fake_geofence)
        poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if called["poll"] or called["geofence"]:
            pytest.fail("detect.poll_current_aircraft/load_geofence were called during an active quiet-hours window: %r" % (called,))
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_exit_from_held_branch_repaints(tmp_path, clock):
    """REGRESSION GUARD: the first cycle after window exit repaints the held live board and clears hold_state"""
    qh_dir = _mkdir(tmp_path, "quiet-exit")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE - 3600  # 22:13:20 Paris - before the window
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=qh_dir, geofence=GEOFENCE_PATH)
        clock["t"] = CLOCK_BASE  # 23:13:20 - inside the window: entry render
        poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(qh_dir, "panel.bin"), "rb") as fh:
            quiet_bytes = fh.read()
        clock["t"] = CLOCK_BASE + 28800  # 07:13:20 - just outside the window
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if not result.get("panel_changed"):
            pytest.fail("the first cycle after window exit returned panel_changed=False, expected True (must force one repaint)")
        with open(os.path.join(qh_dir, "panel.bin"), "rb") as fh:
            after_bytes = fh.read()
        if after_bytes == quiet_bytes:
            pytest.fail("panel.bin is still the QUIET HOURS bytes after the window ended - the stale-image bug this plan exists to prevent")
        on_disk = poll_loop.load_poll_state(qh_dir)
        if on_disk.get("hold_state") is not None:
            pytest.fail("poll_state.json's hold_state is %r after window exit, expected None" % (on_disk.get("hold_state"),))
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_exit_writes_no_transition_screen(tmp_path, clock):
    """the exit cycle's returned state is the ordinary held value, never 'quiet_hours' and never a new third state"""
    qh_dir = _mkdir(tmp_path, "quiet-notrans")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE - 3600
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=qh_dir, geofence=GEOFENCE_PATH)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=qh_dir, geofence=GEOFENCE_PATH)
        clock["t"] = CLOCK_BASE + 28800
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if result.get("state") == "quiet_hours":
            pytest.fail("the exit cycle's returned state is still 'quiet_hours', expected the ordinary held value")
        if result.get("state") != "departing":
            pytest.fail("the exit cycle's returned state is %r, expected 'departing' (the held FLIGHT1 confirmed state)" % (result.get("state"),))
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_quiet_hours_disabled_is_inert(tmp_path, clock):
    """quiet_hours_enabled=False takes the ordinary detection path regardless of stored start/end times"""
    qh_dir = _mkdir(tmp_path, "quiet-disabled")
    try:
        device_config.save_device_config(
            qh_dir, quiet_hours_enabled=False,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=qh_dir, geofence=GEOFENCE_PATH)
        if result.get("state") == "quiet_hours":
            pytest.fail("a disabled quiet_hours_enabled flag still entered the quiet-hours branch")
        return
    finally:
        shutil.rmtree(qh_dir, ignore_errors=True)


def test_display_off_entry_renders_once_and_matches_canvas(tmp_path, clock):
    """toggle-off entry renders the DISPLAY OFF canvas exactly once, byte-identical to render.build_canvas(None, 'display_off')"""
    off_dir = _mkdir(tmp_path, "off-entry")
    try:
        device_config.save_device_config(off_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(state_dir=off_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("entry cycle returned state=%r, expected 'display_off'" % (result.get("state"),))
        if not result.get("panel_changed"):
            pytest.fail("entry cycle returned panel_changed=%r, expected True" % (result.get("panel_changed"),))
        on_disk = poll_loop.load_poll_state(off_dir)
        if on_disk.get("hold_state") != "display_off":
            pytest.fail("poll_state.json's hold_state is %r, expected 'display_off'" % (on_disk.get("hold_state"),))
        with open(os.path.join(off_dir, "panel.bin"), "rb") as fh:
            actual = fh.read()
        expected = poll_loop.panel_format.pack_panel(
            poll_loop.render.build_canvas(None, "display_off")
        )
        if actual != expected:
            pytest.fail("panel.bin does not equal panel_format.pack_panel(render.build_canvas(None, 'display_off'))")
        return
    finally:
        shutil.rmtree(off_dir, ignore_errors=True)


def test_display_off_hold_is_noop_across_battery_transition(tmp_path, clock):
    """toggle-off hold is a no-op - panel.bin unchanged and no gallery entry added, even across a battery hysteresis transition"""
    off_dir = _mkdir(tmp_path, "off-hold")
    try:
        device_config.save_device_config(off_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=off_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(off_dir, "panel.bin"), "rb") as fh:
            first_bytes = fh.read()
        gallery_dir = os.path.join(off_dir, "gallery")
        before_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0
        # A battery-low transition mid-hold must not force a
        # repaint (unlike the held branch below, where a
        # transition DOES force one) - nothing rendered mid-hold
        # can ever reach the glass.
        # 3400: below BATTERY_LOW_THRESHOLD_MV
        # (3500) and above BATTERY_CRITICAL_MV (3300) - still a
        # badge-only transition, never a park.
        _write_battery_state(off_dir, 3400)
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(state_dir=off_dir, geofence=GEOFENCE_PATH)
        if result.get("panel_changed"):
            pytest.fail("hold cycle across a battery transition returned panel_changed=True, expected False")
        with open(os.path.join(off_dir, "panel.bin"), "rb") as fh:
            second_bytes = fh.read()
        if second_bytes != first_bytes:
            pytest.fail("panel.bin's bytes changed on a hold cycle, expected them unchanged")
        after_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0
        if after_count != before_count:
            pytest.fail("a hold cycle added a gallery entry (%d -> %d), expected none" % (before_count, after_count))
        return
    finally:
        shutil.rmtree(off_dir, ignore_errors=True)


def test_display_off_skips_ads_b_detection(tmp_path, monkeypatch, clock):
    """a toggle-off cycle on the live path never calls detect.poll_current_aircraft or detect.load_geofence - an off period is unbounded, so a query-and-discard loop would run against the free-tier aggregators indefinitely"""
    off_dir = _mkdir(tmp_path, "off-skip")
    try:
        device_config.save_device_config(off_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE
        called = {"poll": False, "geofence": False}

        def _fake_poll(*args, **kwargs):
            called["poll"] = True
            return None

        def _fake_geofence(*args, **kwargs):
            called["geofence"] = True
            return {}

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        monkeypatch.setattr(poll_loop.detect, "load_geofence", _fake_geofence)
        poll_loop.run_once(state_dir=off_dir, geofence=GEOFENCE_PATH)
        if called["poll"] or called["geofence"]:
            pytest.fail("detect.poll_current_aircraft/load_geofence were called during an active display-off hold: %r" % (called,))
        return
    finally:
        shutil.rmtree(off_dir, ignore_errors=True)


def test_display_off_wins_over_active_quiet_hours_window(tmp_path, clock):
    """the overlap: toggle off AND an active quiet-hours window renders DISPLAY OFF, not QUIET HOURS"""
    overlap_dir = _mkdir(tmp_path, "overlap")
    try:
        device_config.save_device_config(
            overlap_dir, display_enabled=False, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE  # inside the window too
        result = poll_loop.run_once(state_dir=overlap_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("toggle-off with an active window returned state=%r, expected 'display_off' (D-05: the toggle wins on what the panel shows)" % (result.get("state"),))
        on_disk = poll_loop.load_poll_state(overlap_dir)
        if on_disk.get("hold_state") != "display_off":
            pytest.fail("poll_state.json's hold_state is %r, expected 'display_off'" % (on_disk.get("hold_state"),))
        with open(os.path.join(overlap_dir, "panel.bin"), "rb") as fh:
            actual = fh.read()
        expected = poll_loop.panel_format.pack_panel(
            poll_loop.render.build_canvas(None, "display_off")
        )
        if actual != expected:
            pytest.fail("panel.bin does not equal the DISPLAY OFF canvas while toggle-off overlaps an active quiet-hours window")
        return
    finally:
        shutil.rmtree(overlap_dir, ignore_errors=True)


def test_toggle_off_mid_window_produces_no_refresh(tmp_path, clock):
    """hold-to-hold, direction one: switching the toggle off mid-window costs no e-ink refresh - the quiet screen stays up and the latch silently updates to 'display_off'"""
    transit_dir = _mkdir(tmp_path, "hold-to-hold-a")
    try:
        device_config.save_device_config(
            transit_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE  # window entry - quiet screen renders
        poll_loop.run_once(state_dir=transit_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(transit_dir, "panel.bin"), "rb") as fh:
            quiet_bytes = fh.read()
        gallery_dir = os.path.join(transit_dir, "gallery")
        before_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0

        device_config.save_device_config(transit_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE + 60  # still inside the window
        result = poll_loop.run_once(state_dir=transit_dir, geofence=GEOFENCE_PATH)
        if result.get("panel_changed"):
            pytest.fail("switching the toggle off mid-window returned panel_changed=True, expected False - moving between two hold states must not cost a refresh")
        with open(os.path.join(transit_dir, "panel.bin"), "rb") as fh:
            after_bytes = fh.read()
        if after_bytes != quiet_bytes:
            pytest.fail("panel.bin changed when the toggle was switched off mid-window - the quiet screen must stay on the glass until the transition is silent")
        after_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0
        if after_count != before_count:
            pytest.fail("switching the toggle off mid-window added a gallery entry (%d -> %d), expected none" % (before_count, after_count))
        on_disk = poll_loop.load_poll_state(transit_dir)
        if on_disk.get("hold_state") != "display_off":
            pytest.fail("poll_state.json's hold_state is %r after switching off mid-window, expected 'display_off'" % (on_disk.get("hold_state"),))
        return
    finally:
        shutil.rmtree(transit_dir, ignore_errors=True)


def test_toggle_back_on_during_window_produces_no_refresh(tmp_path, clock):
    """hold-to-hold, direction two: switching the toggle back on while a quiet-hours window is already active costs no e-ink refresh - the off screen stays up and the latch silently updates to 'quiet_hours'"""
    transit_dir = _mkdir(tmp_path, "hold-to-hold-b")
    try:
        device_config.save_device_config(transit_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE  # toggle-off entry render, no window yet
        poll_loop.run_once(state_dir=transit_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(transit_dir, "panel.bin"), "rb") as fh:
            off_bytes = fh.read()
        gallery_dir = os.path.join(transit_dir, "gallery")
        before_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0

        # Switch the toggle back on AND bring a window into effect
        # in the same save, so the very next cycle sees BOTH
        # display_enabled=True and an active window at once -
        # hold_kind flips straight from "display_off" to
        # "quiet_hours" on a single cycle, with no None step
        # between them.
        device_config.save_device_config(
            transit_dir, display_enabled=True, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE + 60  # still inside the window
        result = poll_loop.run_once(state_dir=transit_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "quiet_hours":
            pytest.fail("toggling back on during an active window returned state=%r, expected 'quiet_hours'" % (result.get("state"),))
        if result.get("panel_changed"):
            pytest.fail("toggling back on during an active window returned panel_changed=True, expected False - moving between two hold states must not cost a refresh")
        with open(os.path.join(transit_dir, "panel.bin"), "rb") as fh:
            after_bytes = fh.read()
        if after_bytes != off_bytes:
            pytest.fail("panel.bin changed when the toggle was switched back on during an active window - the off screen must stay on the glass until the transition is silent")
        after_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0
        if after_count != before_count:
            pytest.fail("toggling back on during an active window added a gallery entry (%d -> %d), expected none" % (before_count, after_count))
        on_disk = poll_loop.load_poll_state(transit_dir)
        if on_disk.get("hold_state") != "quiet_hours":
            pytest.fail("poll_state.json's hold_state is %r after toggling back on during an active window, expected 'quiet_hours'" % (on_disk.get("hold_state"),))
        return
    finally:
        shutil.rmtree(transit_dir, ignore_errors=True)


def test_display_off_exit_repaints_once_with_no_transition_screen(tmp_path, clock):
    """the first cycle after the toggle is switched back on repaints the held live board once, with no intermediate transition screen, and clears hold_state"""
    exit_dir = _mkdir(tmp_path, "off-exit")
    try:
        device_config.save_device_config(exit_dir)
        clock["t"] = CLOCK_BASE - 3600
        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=exit_dir, geofence=GEOFENCE_PATH)

        device_config.save_device_config(exit_dir, display_enabled=False)
        clock["t"] = CLOCK_BASE  # toggle-off entry render
        poll_loop.run_once(state_dir=exit_dir, geofence=GEOFENCE_PATH)
        with open(os.path.join(exit_dir, "panel.bin"), "rb") as fh:
            off_bytes = fh.read()

        device_config.save_device_config(exit_dir, display_enabled=True)
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=exit_dir, geofence=GEOFENCE_PATH)
        if not result.get("panel_changed"):
            pytest.fail("the first cycle after the toggle is switched back on returned panel_changed=False, expected True (must force one repaint)")
        if result.get("state") == "display_off":
            pytest.fail("the exit cycle's returned state is still 'display_off', expected the ordinary held value")
        if result.get("state") != "departing":
            pytest.fail("the exit cycle's returned state is %r, expected 'departing' (the held FLIGHT1 confirmed state)" % (result.get("state"),))
        with open(os.path.join(exit_dir, "panel.bin"), "rb") as fh:
            after_bytes = fh.read()
        if after_bytes == off_bytes:
            pytest.fail("panel.bin is still the DISPLAY OFF bytes after the toggle was switched back on - a stale-image bug")
        on_disk = poll_loop.load_poll_state(exit_dir)
        if on_disk.get("hold_state") is not None:
            pytest.fail("poll_state.json's hold_state is %r after the toggle exit, expected None" % (on_disk.get("hold_state"),))
        return
    finally:
        shutil.rmtree(exit_dir, ignore_errors=True)


def test_legacy_poll_state_migrates_without_spurious_repaint(tmp_path, clock):
    """a Phase-10-shaped poll_state.json (legacy quiet_hours_active=True, no hold_state) migrates without a spurious repaint and loses its stale key on disk"""
    mig_dir = _mkdir(tmp_path, "migration")
    try:
        device_config.save_device_config(
            mig_dir, quiet_hours_enabled=True,
            quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        clock["t"] = CLOCK_BASE
        # Seed a Phase-10-shaped poll_state.json directly, bypassing
        # run_once() entirely so this genuinely models a file the
        # OLD code wrote and left behind before this upgrade -
        # panel.bin is seeded to match what that old code would
        # have rendered for the same window, so a spurious repaint
        # is detectable as a byte change.
        legacy_canvas = poll_loop.render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00")
        legacy_bytes = poll_loop.panel_format.pack_panel(legacy_canvas)
        with open(os.path.join(mig_dir, "panel.bin"), "wb") as fh:
            fh.write(legacy_bytes)
        poll_loop.save_poll_state(mig_dir, {"quiet_hours_active": True})

        result = poll_loop.run_once(state_dir=mig_dir, geofence=GEOFENCE_PATH)
        if result.get("panel_changed"):
            pytest.fail("the first post-upgrade cycle returned panel_changed=True, expected False (no spurious repaint on upgrade)")
        with open(os.path.join(mig_dir, "panel.bin"), "rb") as fh:
            after_bytes = fh.read()
        if after_bytes != legacy_bytes:
            pytest.fail("panel.bin changed on the first post-upgrade cycle, expected it byte-identical to the legacy-written image")
        with open(poll_loop._poll_state_path(mig_dir)) as fh:
            on_disk_raw = json.load(fh)
        if on_disk_raw.get("hold_state") != "quiet_hours":
            pytest.fail("the on-disk poll_state.json's hold_state is %r, expected 'quiet_hours'" % (on_disk_raw.get("hold_state"),))
        if "quiet_hours_active" in on_disk_raw:
            pytest.fail("the on-disk poll_state.json still has the legacy quiet_hours_active key: %r, expected it removed" % (on_disk_raw,))
        return
    finally:
        shutil.rmtree(mig_dir, ignore_errors=True)


def test_display_enabled_is_inert(tmp_path, clock):
    """display_enabled=True takes the ordinary detection path - the display-off machinery costs nothing when unused"""
    inert_dir = _mkdir(tmp_path, "off-inert")
    try:
        device_config.save_device_config(inert_dir, display_enabled=True)
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=inert_dir, geofence=GEOFENCE_PATH)
        if result.get("state") == "display_off":
            pytest.fail("display_enabled=True still entered the display-off branch")
        if result.get("state") != "departing":
            pytest.fail("display_enabled=True returned state=%r, expected the ordinary 'departing' detection outcome" % (result.get("state"),))
        return
    finally:
        shutil.rmtree(inert_dir, ignore_errors=True)


def test_manual_registry_loaded_once_per_cycle_from_its_own_state_dir(tmp_path, clock):
    """run_once() configures the manual-resolution registry from THIS cycle's own state_dir every cycle - a seeded prefix resolves after a cycle against its state dir, and a later cycle against a different, registry-less state dir leaves it unresolved again"""
    seeded_dir = _mkdir(tmp_path, "manual-a")
    empty_dir = _mkdir(tmp_path, "manual-b")
    try:
        manual_resolutions.add_entry(seeded_dir, "ZZZ", "Zephyr Air")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("777777", "AAA1234", CLIMB), state_dir=seeded_dir, geofence=GEOFENCE_PATH)
        if enrich.airline_from_callsign("ZZZ1234") != "Zephyr Air":
            pytest.fail("after a cycle against a state dir seeded with ZZZ -> 'Zephyr Air', "
                "enrich.airline_from_callsign('ZZZ1234') = %r, expected 'Zephyr Air'"
                % (enrich.airline_from_callsign("ZZZ1234"),))

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("888888", "BBB1234", CLIMB), state_dir=empty_dir, geofence=GEOFENCE_PATH)
        if enrich.airline_from_callsign("ZZZ1234") is not None:
            pytest.fail("after a cycle against a DIFFERENT state dir with no manual_resolutions.json, "
                "enrich.airline_from_callsign('ZZZ1234') = %r, expected None (today's exact "
                "behaviour - the registry must be reloaded from THIS cycle's own state_dir, "
                "not left over from the previous cycle's)" % (enrich.airline_from_callsign("ZZZ1234"),))
        return
    finally:
        manual_resolutions.set_manual_registry_state_dir(None)
        shutil.rmtree(seeded_dir, ignore_errors=True)
        shutil.rmtree(empty_dir, ignore_errors=True)


def test_manual_resolution_reaches_route_source_end_to_end(tmp_path, clock):
    """a detected flight whose callsign carries a manually-registered prefix, with adsbdb returning nothing, is recorded with route_source == 'manual' and a route carrying the operator's airline name, end to end through a real run_once() cycle"""
    manual_dir = _mkdir(tmp_path, "manual-e2e")
    try:
        manual_resolutions.add_entry(manual_dir, "MRZ", "Meridian Air")
        buf = io.StringIO()
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=_snapshot("999999", "MRZ1234", CLIMB), state_dir=manual_dir, geofence=GEOFENCE_PATH)
        line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
        if "route_source=manual" not in line:
            pytest.fail("a manually-resolved-only callsign did not log route_source=manual: %s" % (line,))
        route = poll_loop.load_poll_state(manual_dir).get("last_route")
        if not isinstance(route, dict) or route.get("airline_name") != "Meridian Air":
            pytest.fail("the persisted last_route = %r, expected airline_name='Meridian Air'" % (route,))
        return
    finally:
        manual_resolutions.set_manual_registry_state_dir(None)
        shutil.rmtree(manual_dir, ignore_errors=True)


def test_clear_resolved_unresolved_prefix_removes_resolvable_entry(tmp_path, clock):
    """a cycle detecting a flight whose prefix is now resolvable via the manual registry removes that prefix's entry from unresolved_prefixes and persists the removal, leaving a still-unresolvable prefix's entry byte-identical"""
    d14a_dir = _mkdir(tmp_path, "d14-clear")
    try:
        seeded_still_unresolved = {
            "count": 1,
            "first_seen": "2026-01-02T00:00:00+00:00",
            "last_seen": "2026-01-02T00:00:00+00:00",
            "example_callsign": "PPP5555",
        }
        poll_loop.save_poll_state(d14a_dir, {
            "unresolved_prefixes": {
                "NNN": {
                    "count": 3,
                    "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:10:00+00:00",
                    "example_callsign": "NNN4444",
                },
                "PPP": dict(seeded_still_unresolved),
            },
        })
        manual_resolutions.add_entry(d14a_dir, "NNN", "Novus Air")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("666666", "NNN7777", CLIMB), state_dir=d14a_dir, geofence=GEOFENCE_PATH)

        unresolved_after = poll_loop.load_poll_state(d14a_dir).get("unresolved_prefixes")
        if not isinstance(unresolved_after, dict) or "NNN" in unresolved_after:
            pytest.fail("NNN is still present after being resolved via the manual registry: %r" % (unresolved_after,))
        if unresolved_after.get("PPP") != seeded_still_unresolved:
            pytest.fail("the still-unresolvable PPP entry was not left byte-identical: %r" % (unresolved_after.get("PPP"),))
        return
    finally:
        manual_resolutions.set_manual_registry_state_dir(None)
        shutil.rmtree(d14a_dir, ignore_errors=True)


def test_clear_resolved_unresolved_prefix_is_independent_of_route_source(tmp_path, monkeypatch, clock):
    """the resolved-prefix cleanup removes a prefix's entry even when this cycle's own route_source is 'fresh_hit' (adsbdb answered) - a route_source-gated implementation would fail exactly this check and no other"""
    monkeypatch.setattr(enrich, "default_transport", lambda callsign, timeout=None: (200, {
            "response": {
                "flightroute": {
                    "airline": {"name": "Full Route Air"},
                    "origin": {"iata_code": "ORY", "municipality": "Paris"},
                    "destination": {"iata_code": "JFK", "municipality": "New York"},
                }
            }
        }))
    d14b_dir = _mkdir(tmp_path, "d14-fresh")
    try:
        seeded_still_unresolved = {
            "count": 1,
            "first_seen": "2026-01-03T00:00:00+00:00",
            "last_seen": "2026-01-03T00:00:00+00:00",
            "example_callsign": "TUV2222",
        }
        poll_loop.save_poll_state(d14b_dir, {
            "unresolved_prefixes": {
                "QRS": {
                    "count": 2,
                    "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:05:00+00:00",
                    "example_callsign": "QRS1111",
                },
                "TUV": dict(seeded_still_unresolved),
            },
        })
        manual_resolutions.add_entry(d14b_dir, "QRS", "Quorum Air")

        buf = io.StringIO()
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        with contextlib.redirect_stdout(buf):
            poll_loop.run_once(snapshot=_snapshot("555555", "QRS3333", CLIMB), state_dir=d14b_dir, geofence=GEOFENCE_PATH)
        line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
        if "route_source=fresh_hit" not in line:
            pytest.fail("test setup did not produce route_source=fresh_hit as required: %s" % (line,))

        unresolved_after = poll_loop.load_poll_state(d14b_dir).get("unresolved_prefixes")
        if not isinstance(unresolved_after, dict) or "QRS" in unresolved_after:
            pytest.fail("QRS is still present after a fresh_hit cycle - the cleanup must not be gated on "
                "route_source: %r" % (unresolved_after,))
        if unresolved_after.get("TUV") != seeded_still_unresolved:
            pytest.fail("the still-unresolvable TUV entry was not left byte-identical: %r" % (unresolved_after.get("TUV"),))
        return
    finally:
        manual_resolutions.set_manual_registry_state_dir(None)
        shutil.rmtree(d14b_dir, ignore_errors=True)


def test_battery_transition_never_flips_effective_theme_for_the_same_flight(tmp_path, monkeypatch, clock):
    """a battery-icon repaint of the same flight (the held/re-render branch) reports the identical effective_theme the flight-detected branch already reported, and both are the matching rule's theme rather than the base theme - proving a battery-icon repaint can never flip the panel's colour"""
    import server.plane.render as render

    d13_dir = _mkdir(tmp_path, "d13-both")
    try:
        colour_rules.add_rule(d13_dir, colour_rules.RULE_KIND_CALLSIGN, "BLK7777", "black")

        # Spy on render.build_canvas itself (check 5's own pattern)
        # so this check asserts on the theme_id ACTUALLY PASSED TO
        # THE RENDER CALL, not merely on run_once()'s reported
        # effective_theme metadata - a call site that silently
        # diverges from its own resolved effective_theme_id (e.g.
        # a stray theme_id=theme_id at the build_canvas() call
        # while the resolver call above it is left in place) would
        # still report the correct metadata but paint the wrong
        # colour, and only a spy on the real call site catches
        # that.
        captured_theme_ids = []
        original = render.build_canvas

        def _spy(flight, state, **kwargs):
            captured_theme_ids.append(kwargs.get("theme_id"))
            return original(flight, state, **kwargs)

        monkeypatch.setattr(poll_loop.render, "build_canvas", _spy)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result1 = poll_loop.run_once(snapshot=_snapshot("d13001", "BLK7777", CLIMB), state_dir=d13_dir, geofence=GEOFENCE_PATH)

        # Change ONLY the battery state - crossing
        # BATTERY_LOW_THRESHOLD_MV forces the held branch's
        # guarded re-render of the SAME flight from
        # current_route, with nothing about the flight itself
        # changing. 3400: below the
        # 3500 badge threshold, above BATTERY_CRITICAL_MV
        # (3300) - a badge-only transition, never a park.
        _write_battery_state(d13_dir, 3400)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result2 = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=d13_dir, geofence=GEOFENCE_PATH)

        if len(captured_theme_ids) != 2:
            pytest.fail("expected exactly 2 render.build_canvas() calls across the two cycles (one per "
                "branch), captured %r" % (captured_theme_ids,))
        rendered_theme_1, rendered_theme_2 = captured_theme_ids

        for label, result, rendered_theme in (
            ("the flight-detected branch", result1, rendered_theme_1),
            ("the held/re-render branch", result2, rendered_theme_2),
        ):
            if result.get("effective_theme") != rendered_theme:
                pytest.fail("%s reported effective_theme=%r but actually called render.build_canvas() with "
                    "theme_id=%r - the reported metadata and the real render call must never "
                    "diverge" % (label, result.get("effective_theme"), rendered_theme))

        if rendered_theme_2 != rendered_theme_1:
            pytest.fail("a battery-icon repaint of the SAME flight (BLK7777) changed the theme_id actually "
                "passed to render.build_canvas() from %r to %r - the held/re-render branch must "
                "render with the IDENTICAL theme the flight-detected branch already used (D-13)"
                % (rendered_theme_1, rendered_theme_2))
        if rendered_theme_1 != "black":
            pytest.fail("render.build_canvas() was called with theme_id=%r on both cycles, expected the "
                "matching rule's theme 'black' - not the base theme, so both branches must "
                "genuinely consult the same rule" % (rendered_theme_1,))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(d13_dir, ignore_errors=True)


def test_nothing_ever_detected_ignores_rule_and_override(tmp_path, clock):
    """the nothing-ever-detected empty-state call site reports effective_theme == the base theme, never consulting a configured rule or the arrivals override"""
    b1_dir = _mkdir(tmp_path, "d13-flightless-a")
    try:
        colour_rules.add_rule(b1_dir, colour_rules.RULE_KIND_CALLSIGN, "SNK4444", "black")
        device_config.save_device_config(b1_dir, theme_arriving="yellow")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=b1_dir, geofence=GEOFENCE_PATH)
        if result.get("effective_theme") != "white":
            pytest.fail("a cycle that has never detected anything reported effective_theme=%r, expected the "
                "base theme 'white' even with a rule and an arrivals override configured (D-09)"
                % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(b1_dir, ignore_errors=True)


def test_held_branch_with_no_confirmed_state_ignores_rule_and_override(tmp_path, clock):
    """the held branch's own empty-state call site (a persisted flight whose confirmed_state never resolved) reports effective_theme == the base theme, even though a rule configured to match that flight's own callsign is present"""
    b2_dir = _mkdir(tmp_path, "d13-flightless-b")
    try:
        colour_rules.add_rule(b2_dir, colour_rules.RULE_KIND_CALLSIGN, "SNK5555", "black")
        device_config.save_device_config(b2_dir, theme_arriving="yellow")

        # First cycle: baro_rate=0 sits inside runway_config's
        # deadband, so confirmed_state stays None - render_state
        # is "empty" and last_confirmed_state persists as None,
        # but last_flight IS persisted.
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("d13005", "SNK5555", 0), state_dir=b2_dir, geofence=GEOFENCE_PATH)
        state_after_1 = poll_loop.load_poll_state(b2_dir)
        if state_after_1.get("last_confirmed_state") is not None:
            pytest.fail("test setup did not produce an unconfirmed first detection: last_confirmed_state=%r"
                % (state_after_1.get("last_confirmed_state"),))

        # Second cycle: nothing detected. Force the held branch's
        # transition gate open via a battery change, exactly as
        # the both-branches invariant does, so its empty-state
        # call site actually runs this cycle. 3400: below the 3500
        # badge threshold, above BATTERY_CRITICAL_MV (3300) - a
        # badge-only transition, never a park.
        _write_battery_state(b2_dir, 3400)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=b2_dir, geofence=GEOFENCE_PATH)
        if result.get("effective_theme") != "white":
            pytest.fail("the held branch's empty-state call site (unconfirmed flight, battery transition) "
                "reported effective_theme=%r, expected the base theme 'white' - a rule matching the "
                "persisted flight's own callsign must never leak onto this call site (D-09)"
                % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(b2_dir, ignore_errors=True)


def test_hold_early_return_ignores_rule_and_override(tmp_path, clock):
    """the hold early-return's result dict reports effective_theme == the base theme under display-off, even with a matching rule, an arrivals override, and a pre-hold flight persisted in poll_state.json"""
    b3_dir = _mkdir(tmp_path, "d13-flightless-c")
    try:
        colour_rules.add_rule(b3_dir, colour_rules.RULE_KIND_CALLSIGN, "SNK6666", "black")
        device_config.save_device_config(b3_dir, theme_arriving="yellow", display_enabled=False)
        poll_loop.save_poll_state(b3_dir, {
            "last_flight": {"hex": "d13006", "callsign": "SNK6666"},
            "last_confirmed_state": "departing",
        })

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=b3_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("test setup did not enter the display-off hold: state=%r" % (result.get("state"),))
        if result.get("effective_theme") != "white":
            pytest.fail("the hold early-return's result dict reported effective_theme=%r, expected the base "
                "theme 'white' - a rule matching the pre-hold flight's own callsign must never leak "
                "onto a hold screen (D-09)" % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(b3_dir, ignore_errors=True)


def test_direction_sensitivity_through_the_real_loop(tmp_path, clock):
    """with no rule but an arrivals override configured, run_once() reports the override as effective_theme for a detected arriving flight and the base theme for a detected departing flight, proved end to end through the real poll loop"""
    c_dir_arr = _mkdir(tmp_path, "d13-direction-arr")
    c_dir_dep = _mkdir(tmp_path, "d13-direction-dep")
    try:
        device_config.save_device_config(c_dir_arr, theme_arriving="yellow")
        device_config.save_device_config(c_dir_dep, theme_arriving="yellow")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        arriving_result = poll_loop.run_once(snapshot=_snapshot("d13007", "ARR8888", -CLIMB), state_dir=c_dir_arr, geofence=GEOFENCE_PATH)
        if arriving_result.get("state") != "arriving":
            pytest.fail("test setup did not produce an arriving detection: state=%r" % (arriving_result.get("state"),))
        if arriving_result.get("effective_theme") != "yellow":
            pytest.fail("a detected ARRIVING flight with an arrivals override configured reported "
                "effective_theme=%r, expected the override 'yellow' (D-04)" % (arriving_result.get("effective_theme"),))

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        departing_result = poll_loop.run_once(snapshot=_snapshot("d13008", "DEP9999", CLIMB), state_dir=c_dir_dep, geofence=GEOFENCE_PATH)
        if departing_result.get("state") != "departing":
            pytest.fail("test setup did not produce a departing detection: state=%r" % (departing_result.get("state"),))
        if departing_result.get("effective_theme") != "white":
            pytest.fail("a detected DEPARTING flight with an arrivals override configured reported "
                "effective_theme=%r, expected the base theme 'white' - the override applies only to "
                "arriving (D-04)" % (departing_result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(c_dir_arr, ignore_errors=True)
        shutil.rmtree(c_dir_dep, ignore_errors=True)


def test_colour_rules_registry_reloaded_every_cycle_from_its_own_state_dir(tmp_path, clock):
    """a colour rule added to the state dir AFTER one run_once() cycle is picked up by the very next cycle - proving the registry is primed every cycle, not cached once per process"""
    d_dir = _mkdir(tmp_path, "d13-priming")
    try:
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        before = poll_loop.run_once(snapshot=_snapshot("d13009", "PRM1111", CLIMB), state_dir=d_dir, geofence=GEOFENCE_PATH)
        if before.get("effective_theme") != "white":
            pytest.fail("before any rule exists, effective_theme=%r, expected the base theme 'white'" % (before.get("effective_theme"),))

        colour_rules.add_rule(d_dir, colour_rules.RULE_KIND_CALLSIGN, "PRM1111", "black")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        after = poll_loop.run_once(snapshot=_snapshot("d13009", "PRM1111", CLIMB), state_dir=d_dir, geofence=GEOFENCE_PATH)
        if after.get("effective_theme") != "black":
            pytest.fail("a rule added between two run_once() cycles was not picked up by the NEXT cycle: "
                "effective_theme=%r, expected 'black' - the registry must be reloaded from THIS "
                "cycle's own state_dir every cycle, not cached once per process"
                % (after.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(d_dir, ignore_errors=True)


def test_calendar_match_survives_a_battery_repaint_past_its_own_window(tmp_path, monkeypatch, clock):
    """a battery-icon repaint of a calendar-matched flight, hours after the calendar entry's own time window has closed, reports the identical effective_theme the flight-detected branch already reported - the calendar theme, not the base theme - proving the held branch reuses the persisted match rather than recomputing one against the moved clock"""
    import server.plane.render as render

    cal1_dir = _mkdir(tmp_path, "cal-both")
    try:
        device_config.save_device_config(cal1_dir, calendar_theme_id="green")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal1_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        _seed_calendar_cache(poll_loop, cal1_dir, "TVF7061")

        captured_theme_ids = []
        original = render.build_canvas

        def _spy(flight, state, **kwargs):
            captured_theme_ids.append(kwargs.get("theme_id"))
            return original(flight, state, **kwargs)

        monkeypatch.setattr(poll_loop.render, "build_canvas", _spy)
        result1 = poll_loop.run_once(snapshot=_snapshot("cal0001", "TVF7061", CLIMB), state_dir=cal1_dir, geofence=GEOFENCE_PATH)

        # Change ONLY the battery state, and advance the
        # clock WELL PAST the calendar entry's own match
        # tolerance - the whole point of the check: a
        # version that recomputed the match in the held
        # branch would find no candidate this far out and
        # silently fall back to the base theme, passing a
        # same-minute test and failing only this one. 3400
        #: below the 3500 badge
        # threshold, above BATTERY_CRITICAL_MV (3300) - a
        # badge-only transition, never a park.
        _write_battery_state(cal1_dir, 3400)
        _tick(clock, calendar_rules.CALENDAR_MATCH_TOLERANCE_S + 3600)
        result2 = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal1_dir, geofence=GEOFENCE_PATH)

        if len(captured_theme_ids) != 2:
            pytest.fail("expected exactly 2 render.build_canvas() calls across the two cycles (one per "
                "branch), captured %r" % (captured_theme_ids,))
        rendered_theme_1, rendered_theme_2 = captured_theme_ids

        for label, result, rendered_theme in (
            ("the flight-detected branch", result1, rendered_theme_1),
            ("the held/re-render branch", result2, rendered_theme_2),
        ):
            if result.get("effective_theme") != rendered_theme:
                pytest.fail("%s reported effective_theme=%r but actually called render.build_canvas() with "
                    "theme_id=%r - the reported metadata and the real render call must never "
                    "diverge" % (label, result.get("effective_theme"), rendered_theme))

        if rendered_theme_2 != rendered_theme_1:
            pytest.fail("a battery-icon repaint of the SAME flight, hours after the calendar entry's own "
                "matching window closed, changed the theme_id actually passed to "
                "render.build_canvas() from %r to %r - the held/repaint branch must reuse the "
                "PERSISTED match rather than recompute one against the moved clock (D-13, "
                "T-16-BRANCH)" % (rendered_theme_1, rendered_theme_2))
        if rendered_theme_1 != "green":
            pytest.fail("render.build_canvas() was called with theme_id=%r on both cycles, expected the "
                "operator's calendar theme 'green' - not the base theme - so the check would still "
                "fail if both branches were wrong in the same direction" % (rendered_theme_1,))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal1_dir, ignore_errors=True)


def test_calendar_match_beats_an_exact_callsign_rule(tmp_path, clock):
    """a calendar match beats a matching exact-callsign rule end to end through the real loop - the calendar's designated theme, not the rule's"""
    cal2_dir = _mkdir(tmp_path, "cal-precedence")
    try:
        device_config.save_device_config(cal2_dir, calendar_theme_id="green")
        colour_rules.add_rule(cal2_dir, colour_rules.RULE_KIND_CALLSIGN, "TVF7062", "black")

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal2_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        _seed_calendar_cache(poll_loop, cal2_dir, "TVF7062")

        result = poll_loop.run_once(snapshot=_snapshot("cal0002", "TVF7062", CLIMB), state_dir=cal2_dir, geofence=GEOFENCE_PATH)
        if result.get("effective_theme") != "green":
            pytest.fail("a flight matching BOTH a calendar entry and its own exact-callsign rule reported "
                "effective_theme=%r, expected the calendar theme 'green' to win over the rule's "
                "'black' (D-02)" % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal2_dir, ignore_errors=True)


def test_nothing_ever_detected_ignores_calendar_match(tmp_path, clock):
    """the nothing-ever-detected empty-state call site reports effective_theme == the base theme with a calendar theme configured - a calendar match must never reach an empty state"""
    cal3_dir = _mkdir(tmp_path, "cal-flightless-a")
    try:
        device_config.save_device_config(cal3_dir, calendar_theme_id="green")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal3_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)

        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal3_dir, geofence=GEOFENCE_PATH)
        if result.get("effective_theme") != "white":
            pytest.fail("a cycle that has never detected anything reported effective_theme=%r, expected the "
                "base theme 'white' even with a calendar theme configured - a calendar match must "
                "never reach an empty state" % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal3_dir, ignore_errors=True)


def test_held_branch_with_no_confirmed_state_ignores_calendar_match(tmp_path, clock):
    """the held branch's own empty-state call site (a persisted flight whose confirmed_state never resolved) reports effective_theme == the base theme, even though a calendar entry matching that flight's own route is present"""
    cal4_dir = _mkdir(tmp_path, "cal-flightless-b")
    try:
        device_config.save_device_config(cal4_dir, calendar_theme_id="green")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal4_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        _seed_calendar_cache(poll_loop, cal4_dir, "TVF7065")

        # First cycle: baro_rate=0 sits inside runway_config's
        # deadband, so confirmed_state stays None - render_state
        # is "empty" and last_confirmed_state persists as None,
        # but last_flight IS persisted (check 53's own template).
        poll_loop.run_once(snapshot=_snapshot("cal0011", "TVF7065", 0), state_dir=cal4_dir, geofence=GEOFENCE_PATH)
        state_after_1 = poll_loop.load_poll_state(cal4_dir)
        if state_after_1.get("last_confirmed_state") is not None:
            pytest.fail("test setup did not produce an unconfirmed first detection: last_confirmed_state=%r"
                % (state_after_1.get("last_confirmed_state"),))

        # Second cycle: nothing detected. Force the held
        # branch's transition gate open via a battery change so
        # its empty-state call site actually runs this cycle.
        # 3400: below the 3500 badge
        # threshold, above BATTERY_CRITICAL_MV (3300) - a
        # badge-only transition, never a park.
        _write_battery_state(cal4_dir, 3400)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal4_dir, geofence=GEOFENCE_PATH)
        if result.get("effective_theme") != "white":
            pytest.fail("the held branch's empty-state call site (unconfirmed flight, battery transition) "
                "reported effective_theme=%r, expected the base theme 'white' - a calendar entry "
                "matching the persisted flight's own route must never leak onto this call site"
                % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal4_dir, ignore_errors=True)


def test_hold_early_return_ignores_calendar_match(tmp_path, clock):
    """the hold early-return's result dict reports effective_theme == the base theme under display-off, even with a calendar theme configured, a matching entry present, and a pre-hold flight's own last_calendar_theme_id already persisted"""
    cal5_dir = _mkdir(tmp_path, "cal-flightless-c")
    try:
        device_config.save_device_config(cal5_dir, calendar_theme_id="green", display_enabled=False)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal5_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        poll_loop.save_poll_state(cal5_dir, {
            "last_flight": {"hex": "cal0012", "callsign": "TVF7066"},
            "last_confirmed_state": "departing",
            "last_calendar_theme_id": "green",
        })

        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal5_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("test setup did not enter the display-off hold: state=%r" % (result.get("state"),))
        if result.get("effective_theme") != "white":
            pytest.fail("the hold early-return's result dict reported effective_theme=%r under display-off, "
                "expected the base theme 'white' - a persisted calendar match must never leak onto "
                "a hold screen" % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal5_dir, ignore_errors=True)


def test_airline_only_route_never_matches_the_calendar(tmp_path, clock):
    """an airline-only enrichment (no cached route, resolved only via the static ICAO-prefix table) never lets a calendar match fire, even with an entry that would otherwise match on airline and time - proving the narrowing end to end through the real loop (CORRECTION 1)"""
    cal6_dir = _mkdir(tmp_path, "cal-narrowing")
    try:
        device_config.save_device_config(cal6_dir, calendar_theme_id="green")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal6_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        # Deliberately NOT seeded via _seed_calendar_cache(): no
        # enrichment_cache entry exists for this callsign, and
        # enrich.default_transport (stubbed to a 404 miss for
        # this whole section) never resolves it either - so the
        # only route this cycle can produce is the static-table
        # airline-only fallback for the TVF prefix, which
        # carries no origin_iata/destination_iata/callsign_iata.
        result = poll_loop.run_once(snapshot=_snapshot("cal0013", "TVF9999", CLIMB), state_dir=cal6_dir, geofence=GEOFENCE_PATH)

        state_after = poll_loop.load_poll_state(cal6_dir)
        route_after = state_after.get("last_route")
        if not isinstance(route_after, dict) or route_after.get("origin_iata") is not None:
            pytest.fail("test setup did not produce an airline-only route: last_route=%r" % (route_after,))
        if result.get("effective_theme") != "white":
            pytest.fail("an airline-only-enriched detection, with a calendar entry that would otherwise "
                "match on airline and time, reported effective_theme=%r, expected the base theme "
                "'white' - a match must require origin_iata/destination_iata/callsign_iata to be "
                "present (CORRECTION 1)" % (result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal6_dir, ignore_errors=True)


def test_tampered_last_calendar_theme_id_falls_back_to_base_theme(tmp_path, clock):
    """a hand-edited poll_state.json whose stored last_calendar_theme_id is not a registered theme falls back to the base theme on the held branch's repaint, never reaching the panel (T-16-TAMPER)"""
    cal7_dir = _mkdir(tmp_path, "cal-tamper")
    try:
        device_config.save_device_config(cal7_dir, calendar_theme_id="green")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        match_time = clock["t"]
        calendar_rules.write_calendar_registry(
            cal7_dir, [_calendar_entry(match_time)], match_time, None, now=match_time)
        _seed_calendar_cache(poll_loop, cal7_dir, "TVF7063")

        result1 = poll_loop.run_once(snapshot=_snapshot("cal0006", "TVF7063", CLIMB), state_dir=cal7_dir, geofence=GEOFENCE_PATH)
        if result1.get("effective_theme") != "green":
            pytest.fail("test setup did not produce a calendar-matched cycle: effective_theme=%r"
                % (result1.get("effective_theme"),))

        tampered = poll_loop.load_poll_state(cal7_dir)
        if tampered.get("last_calendar_theme_id") != "green":
            pytest.fail("the flight-detected branch did not persist last_calendar_theme_id: %r"
                % (tampered.get("last_calendar_theme_id"),))
        tampered["last_calendar_theme_id"] = "not_a_registered_theme"
        poll_loop.save_poll_state(cal7_dir, tampered)

        # 3400: below the 3500 badge
        # threshold, above BATTERY_CRITICAL_MV (3300) - a
        # badge-only transition, never a park.
        _write_battery_state(cal7_dir, 3400)
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        result2 = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal7_dir, geofence=GEOFENCE_PATH)
        if result2.get("effective_theme") == "not_a_registered_theme":
            pytest.fail("a hand-edited poll_state.json's last_calendar_theme_id reached the panel "
                "unchanged: effective_theme=%r" % (result2.get("effective_theme"),))
        if result2.get("effective_theme") != "white":
            pytest.fail("a tampered last_calendar_theme_id fell back to effective_theme=%r, expected the "
                "base theme 'white' (no manual rule configured in this scenario)"
                % (result2.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal7_dir, ignore_errors=True)


def test_unconfigured_cycle_never_creates_the_registry_file(tmp_path, clock):
    """with no calendar secret file present, a full run_once() cycle completes normally and never creates calendar_rules.json"""
    cal8_dir = _mkdir(tmp_path, "cal-unconfigured")
    try:
        # No secret file is written - a fresh state dir is
        # "unconfigured" by construction, with nothing to arrange or
        # restore.
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        poll_loop.run_once(snapshot=_snapshot("cal0014", "TVF7064", CLIMB), state_dir=cal8_dir, geofence=GEOFENCE_PATH)
        if os.path.exists(calendar_rules.calendar_rules_path(cal8_dir)):
            pytest.fail("calendar_rules.json was created for a cycle with the calendar feature unconfigured")
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal8_dir, ignore_errors=True)


def test_throttled_cycles_never_rewrite_the_registry_file(tmp_path, clock):
    """with a calendar secret file present and a fresh last_attempt_at already on disk, ten consecutive cycles inside the throttle interval leave calendar_rules.json's modification time and contents byte-identical - the throttled path performs no write (T-16-DOS)"""
    cal9_dir = _mkdir(tmp_path, "cal-throttle")
    try:
        assert calendar_rules.save_calendar_url(cal9_dir, "https://example.invalid/calendar.ics") is True
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        calendar_rules.write_calendar_registry(cal9_dir, [], clock["t"], None, now=clock["t"])
        path = calendar_rules.calendar_rules_path(cal9_dir)
        before_mtime = os.path.getmtime(path)
        with open(path, "rb") as fh:
            before_bytes = fh.read()

        for _ in range(10):
            _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
            poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal9_dir, geofence=GEOFENCE_PATH)

        after_mtime = os.path.getmtime(path)
        with open(path, "rb") as fh:
            after_bytes = fh.read()
        if after_mtime != before_mtime or after_bytes != before_bytes:
            pytest.fail("calendar_rules.json changed across 10 throttled cycles: mtime %r -> %r, bytes "
                "changed=%s" % (before_mtime, after_mtime, after_bytes != before_bytes))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal9_dir, ignore_errors=True)


def test_feature_off_leaves_every_pre_phase_behaviour_unchanged(tmp_path, clock):
    """with no calendar configured, a matching-rule cycle, an arrivals-override cycle and a plain base-theme cycle all report exactly what they reported before this phase - an explicit regression fence"""
    off_rule_dir = _mkdir(tmp_path, "cal-off-rule")
    off_arr_dir = _mkdir(tmp_path, "cal-off-arr")
    off_base_dir = _mkdir(tmp_path, "cal-off-base")
    try:
        colour_rules.add_rule(off_rule_dir, colour_rules.RULE_KIND_CALLSIGN, "OFF1111", "black")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        rule_result = poll_loop.run_once(snapshot=_snapshot("cal0015", "OFF1111", CLIMB), state_dir=off_rule_dir, geofence=GEOFENCE_PATH)
        if rule_result.get("effective_theme") != "black":
            pytest.fail("with no calendar configured, a matching-rule cycle reported effective_theme=%r, "
                "expected the rule's own theme 'black' unchanged from Phase 15"
                % (rule_result.get("effective_theme"),))

        device_config.save_device_config(off_arr_dir, theme_arriving="yellow")
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        arr_result = poll_loop.run_once(snapshot=_snapshot("cal0016", "OFF2222", -CLIMB), state_dir=off_arr_dir, geofence=GEOFENCE_PATH)
        if arr_result.get("effective_theme") != "yellow":
            pytest.fail("with no calendar configured, a detected arriving flight with an arrivals override "
                "reported effective_theme=%r, expected the override 'yellow' unchanged from Phase "
                "15" % (arr_result.get("effective_theme"),))

        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        base_result = poll_loop.run_once(snapshot=_snapshot("cal0017", "OFF3333", CLIMB), state_dir=off_base_dir, geofence=GEOFENCE_PATH)
        if base_result.get("effective_theme") != "white":
            pytest.fail("with no calendar configured and no rule, a plain detection reported "
                "effective_theme=%r, expected the base theme 'white' unchanged from Phase 15"
                % (base_result.get("effective_theme"),))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(off_rule_dir, ignore_errors=True)
        shutil.rmtree(off_arr_dir, ignore_errors=True)
        shutil.rmtree(off_base_dir, ignore_errors=True)


def test_default_min_interval_s_preserves_poll_loops_pacing(tmp_path, clock):
    """poll_loop.py's own run_once() call site, which passes no min_interval_s argument, still skips the calendar fetch 60 seconds after a recorded attempt - pinning refresh_calendar_registry()'s parameter to default to None so today's pacing is unchanged"""
    cal10_dir = _mkdir(tmp_path, "cal-default-interval")
    try:
        assert calendar_rules.save_calendar_url(cal10_dir, "https://example.invalid/calendar.ics") is True
        _tick(clock, poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
        seed_now = clock["t"]
        calendar_rules.write_calendar_registry(cal10_dir, [], seed_now, None, now=seed_now)
        path = calendar_rules.calendar_rules_path(cal10_dir)
        before_mtime = os.path.getmtime(path)
        with open(path, "rb") as fh:
            before_bytes = fh.read()

        _tick(clock, 60)
        poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=cal10_dir, geofence=GEOFENCE_PATH)

        after_mtime = os.path.getmtime(path)
        with open(path, "rb") as fh:
            after_bytes = fh.read()
        if after_mtime != before_mtime or after_bytes != before_bytes:
            pytest.fail("calendar_rules.json changed after a single cycle 60 seconds inside the "
                "standard interval - refresh_calendar_registry()'s min_interval_s default may "
                "no longer be None: mtime %r -> %r, bytes changed=%s"
                % (before_mtime, after_mtime, after_bytes != before_bytes))
        return
    finally:
        colour_rules.set_colour_rules_state_dir(None)
        shutil.rmtree(cal10_dir, ignore_errors=True)


def test_battery_low_transition_sends_once_with_mv():
    """a first cycle crossing into battery-low sends exactly one push whose body carries the millivolt reading and the discharge-curve percentage '(≈ 9%)', and records last_battery_sent=True"""
    poll_state = {}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(), sender=sender,
    )
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send, got %d" % len(sender.calls))
    _, title, body = sender.calls[0]
    # Real transition pushes carry notify.ALERT_TITLE, not
    # TEST_NOTIFICATION_TITLE - the latter is reserved for the "Send a
    # test" button alone.
    if title != poll_loop.notify.ALERT_TITLE:
        pytest.fail("expected the project's short-name title, got %r" % (title,))
    if "3400" not in body:
        pytest.fail("expected the millivolt figure 3400 in body %r" % (body,))
    if "(≈ 9%)" not in body:
        pytest.fail("expected the SEED-006 curve percentage '(≈ 9%%)' in body %r" % (body,))
    if poll_loop._battery_percent_estimate(3400) != 9:
        pytest.fail("expected poll_loop._battery_percent_estimate(3400) == 9, got %r"
            % (poll_loop._battery_percent_estimate(3400),))
    if poll_state.get("notifications", {}).get("last_battery_sent") is not True:
        pytest.fail("expected last_battery_sent=True recorded, got %r" % (poll_state,))


def test_battery_low_second_cycle_sends_nothing():
    """a second cycle still battery-low (last_battery_sent already True) sends nothing"""
    poll_state = {"notifications": {"last_battery_sent": True, "last_silent_sent": False}}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(), sender=sender,
    )
    if sender.calls:
        pytest.fail("expected no send on an unchanged battery-low state, got %r" % (sender.calls,))


def test_battery_recovery_transition_sends_once():
    """a cycle crossing back to normal sends exactly one recovery push (no interpolated arguments) and records last_battery_sent=False"""
    poll_state = {"notifications": {"last_battery_sent": True, "last_silent_sent": False}}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, False, 3700, _notify_device_cfg(), sender=sender,
    )
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one recovery send, got %d" % len(sender.calls))
    if sender.calls[0][2] != poll_loop.notify.BATTERY_OK_BODY:
        pytest.fail("expected the fixed recovery body, got %r" % (sender.calls[0][2],))
    if poll_state["notifications"]["last_battery_sent"] is not False:
        pytest.fail("expected last_battery_sent=False recorded, got %r" % (poll_state,))


def test_battery_config_disabled_sends_nothing():
    """a notifications group with battery_low: False sends nothing on a transition and records nothing"""
    poll_state = {}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(battery_low=False), sender=sender,
    )
    if sender.calls:
        pytest.fail("expected no send with battery_low: False, got %r" % (sender.calls,))
    if "notifications" in poll_state:
        pytest.fail("expected nothing recorded with battery_low: False, got %r" % (poll_state,))


def test_battery_no_topic_url_sends_nothing():
    """a notifications group with no topic_url configured sends nothing"""
    poll_state = {}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(topic_url=None), sender=sender,
    )
    if sender.calls:
        pytest.fail("expected no send with topic_url=None, got %r" % (sender.calls,))


def test_battery_sender_returning_false_still_flips_state():
    """a sender returning False still flips the recorded state, so a persistently-failing endpoint does not repeat the push every cycle"""
    poll_state = {}
    sender = _FakeSender(result=False)
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(), sender=sender,
    )
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one attempted send, got %d" % len(sender.calls))
    if poll_state.get("notifications", {}).get("last_battery_sent") is not True:
        pytest.fail("expected last_battery_sent=True recorded even on a False return, got %r" % (poll_state,))
    sender2 = _FakeSender(result=False)
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(), sender=sender2,
    )
    if sender2.calls:
        pytest.fail("expected no repeat send on the next cycle despite the False return, got %r" % (sender2.calls,))


def test_battery_raising_sender_does_not_propagate_through_run_once(tmp_path, monkeypatch):
    """a raising send_notification() does not propagate out of the real run_once() battery-transition call site"""
    raise_dir = _mkdir(tmp_path, "notify-raise")
    try:
        device_config.save_device_config(
            raise_dir,
            notifications={
                "topic_url": _NOTIFY_TOPIC_URL, "battery_low": True,
                "frame_silent": True, "lang": "en",
            },
        )
        _write_battery_state(raise_dir, 3400)

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated transport failure")

        monkeypatch.setattr(poll_loop.notify, "send_notification", _boom)
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=raise_dir, geofence=GEOFENCE_PATH)
        if result is None or result.get("panel_changed") is None:
            pytest.fail("run_once() did not return its normal result dict: %r" % (result,))
        return
    finally:
        shutil.rmtree(raise_dir, ignore_errors=True)


def test_battery_french_lang_produces_french_body():
    """notifications.lang == "fr" produces the French battery-low body"""
    poll_state = {}
    sender = _FakeSender()
    poll_loop._notify_battery_transition(
        "unused", poll_state, True, 3400, _notify_device_cfg(lang="fr"), sender=sender,
    )
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send, got %d" % len(sender.calls))
    body = sender.calls[0][2]
    if "Batterie faible" not in body:
        pytest.fail("expected the French battery-low body, got %r" % (body,))


def test_silence_transition_sends_once_past_warn_threshold(tmp_path):
    """a seeded device_health check-in older than the shared warn threshold sends exactly one frame-silent push and records last_silent_sent=True"""
    d = _mkdir(tmp_path, "silence-past")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=500)
        warn_s, _error_s = poll_loop.wake.device_staleness_thresholds(
            poll_loop.wake.effective_wake_interval_s(device_cfg)
        )
        now_epoch = poll_loop.now_s()
        _seed_device_health(poll_loop, d, _iso(now_epoch - warn_s - 60))
        poll_state = {}
        sender = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender)
        if len(sender.calls) != 1:
            pytest.fail("expected exactly one silent push, got %d" % len(sender.calls))
        if poll_state.get("notifications", {}).get("last_silent_sent") is not True:
            pytest.fail("expected last_silent_sent=True recorded, got %r" % (poll_state,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_second_cycle_sends_nothing(tmp_path):
    """a second cycle reading the same stale device_health row sends nothing"""
    d = _mkdir(tmp_path, "silence-repeat")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=500)
        warn_s, _error_s = poll_loop.wake.device_staleness_thresholds(
            poll_loop.wake.effective_wake_interval_s(device_cfg)
        )
        now_epoch = poll_loop.now_s()
        _seed_device_health(poll_loop, d, _iso(now_epoch - warn_s - 60))
        poll_state = {}
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=_FakeSender())
        sender2 = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender2)
        if sender2.calls:
            pytest.fail("expected no repeat send on an unchanged stale row, got %r" % (sender2.calls,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_recovery_sends_once(tmp_path):
    """a fresh device_health check-in after a reported silence sends exactly one recovery push"""
    d = _mkdir(tmp_path, "silence-recover")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=500)
        warn_s, _error_s = poll_loop.wake.device_staleness_thresholds(
            poll_loop.wake.effective_wake_interval_s(device_cfg)
        )
        now_epoch = poll_loop.now_s()
        _seed_device_health(poll_loop, d, _iso(now_epoch - warn_s - 60))
        poll_state = {}
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=_FakeSender())
        _seed_device_health(poll_loop, d, _iso(now_epoch))
        sender2 = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender2)
        if len(sender2.calls) != 1:
            pytest.fail("expected exactly one recovery push, got %d" % len(sender2.calls))
        if sender2.calls[0][2] != poll_loop.notify.FRAME_RECOVERED_BODY:
            pytest.fail("expected the fixed recovery body, got %r" % (sender2.calls[0][2],))
        if poll_state["notifications"]["last_silent_sent"] is not False:
            pytest.fail("expected last_silent_sent=False recorded, got %r" % (poll_state,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_inside_threshold_sends_nothing(tmp_path):
    """a seeded device_health check-in just inside the shared warn threshold sends nothing"""
    d = _mkdir(tmp_path, "silence-inside")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=500)
        warn_s, _error_s = poll_loop.wake.device_staleness_thresholds(
            poll_loop.wake.effective_wake_interval_s(device_cfg)
        )
        now_epoch = poll_loop.now_s()
        _seed_device_health(poll_loop, d, _iso(now_epoch - (warn_s - 10)))
        poll_state = {}
        sender = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender)
        if sender.calls:
            pytest.fail("expected no send for a check-in still inside the warn threshold, got %r" % (sender.calls,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_no_rows_sends_and_records_nothing(tmp_path):
    """no device_health rows at all sends nothing and records nothing (a first-install state, not a silence transition)"""
    d = _mkdir(tmp_path, "silence-norows")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=500)
        poll_state = {}
        sender = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender)
        if sender.calls:
            pytest.fail("expected no send with no device_health rows at all, got %r" % (sender.calls,))
        if "notifications" in poll_state:
            pytest.fail("expected nothing recorded with no device_health rows at all, got %r" % (poll_state,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_config_disabled_sends_nothing(tmp_path):
    """a notifications group with frame_silent: False sends nothing even for a very stale check-in"""
    d = _mkdir(tmp_path, "silence-disabled")
    try:
        device_cfg = _notify_device_cfg(frame_silent=False, wake_interval_s=500)
        now_epoch = poll_loop.now_s()
        _seed_device_health(poll_loop, d, _iso(now_epoch - 100000))
        poll_state = {}
        sender = _FakeSender()
        with poll_loop.history_db.open_db(d) as conn:
            poll_loop._notify_silence_transition(d, poll_state, conn, device_cfg, sender=sender)
        if sender.calls:
            pytest.fail("expected no send with frame_silent: False, got %r" % (sender.calls,))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_threshold_matches_shared_wake_thresholds_for_nondefault_interval(tmp_path):
    """the silent threshold the helper actually used equals wake.device_staleness_thresholds(wake.effective_wake_interval_s(cfg))[0] for a non-default wake_interval_s (777s), not a phase-local re-tuning"""
    device_cfg = _notify_device_cfg(wake_interval_s=777)
    warn_s, _error_s = poll_loop.wake.device_staleness_thresholds(
        poll_loop.wake.effective_wake_interval_s(device_cfg)
    )
    now_epoch = poll_loop.now_s()
    d_inside = _mkdir(tmp_path, "silence-boundary-in")
    d_outside = _mkdir(tmp_path, "silence-boundary-out")
    try:
        _seed_device_health(poll_loop, d_inside, _iso(now_epoch - (warn_s - 5)))
        sender_inside = _FakeSender()
        with poll_loop.history_db.open_db(d_inside) as conn:
            poll_loop._notify_silence_transition(d_inside, {}, conn, device_cfg, sender=sender_inside)
        if sender_inside.calls:
            pytest.fail("age 5s inside warn_s=%r unexpectedly reported silent" % (warn_s,))

        _seed_device_health(poll_loop, d_outside, _iso(now_epoch - (warn_s + 5)))
        sender_outside = _FakeSender()
        with poll_loop.history_db.open_db(d_outside) as conn:
            poll_loop._notify_silence_transition(d_outside, {}, conn, device_cfg, sender=sender_outside)
        if len(sender_outside.calls) != 1:
            pytest.fail("age 5s past warn_s=%r did not report silent" % (warn_s,))
        return
    finally:
        shutil.rmtree(d_inside, ignore_errors=True)
        shutil.rmtree(d_outside, ignore_errors=True)


def test_silence_transition_fires_during_display_off_hold(tmp_path, monkeypatch, clock):
    """a display_off hold with a stale device_health check-in still raises exactly one frame_silent push from the early-return hold branch, and persists last_silent_sent=True"""
    hold_dir = _mkdir(tmp_path, "silence-hold")
    try:
        device_config.save_device_config(
            hold_dir, display_enabled=False,
            notifications={
                "topic_url": _NOTIFY_TOPIC_URL, "battery_low": True,
                "frame_silent": True, "lang": "en",
            },
        )
        clock["t"] = CLOCK_BASE
        _seed_device_health(poll_loop, hold_dir, _iso(CLOCK_BASE - 100000))
        sender = _FakeSender()
        monkeypatch.setattr(poll_loop.notify, "send_notification", sender)
        result = poll_loop.run_once(state_dir=hold_dir, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("expected a display_off hold cycle, got state=%r" % (result.get("state"),))
        if len(sender.calls) != 1:
            pytest.fail("expected exactly one frame-silent push from the hold branch, got %d: %r" % (len(sender.calls), sender.calls))
        on_disk = poll_loop.load_poll_state(hold_dir)
        if on_disk.get("notifications", {}).get("last_silent_sent") is not True:
            pytest.fail("expected last_silent_sent=True persisted after a hold cycle, got %r" % (on_disk,))
        return
    finally:
        shutil.rmtree(hold_dir, ignore_errors=True)


def test_wake_epochs_accrue_only_when_the_effective_interval_changes(tmp_path, clock):
    """three consecutive poll cycles at an unchanged effective wake interval write exactly one wake_epochs row, and a fourth at a changed interval writes a second"""
    epoch_dir = _mkdir(tmp_path, "wake-epochs")
    try:
        device_config.save_device_config(epoch_dir, wake_interval_s=600)
        clock["t"] = CLOCK_BASE
        for _ in range(3):
            poll_loop.run_once(
                snapshot=_empty_snapshot(), state_dir=epoch_dir, geofence=GEOFENCE_PATH,
            )
            clock["t"] += 30
        after_three = _wake_epoch_rows(epoch_dir)
        if len(after_three) != 1:
            pytest.fail("three cycles at an unchanged 600 s cadence wrote %d wake_epochs rows, "
                "expected exactly 1: %r" % (len(after_three), after_three))
        if after_three[0][1] != 600:
            pytest.fail("the first epoch recorded %r, expected 600" % (after_three[0],))

        device_config.save_device_config(epoch_dir, wake_interval_s=900)
        poll_loop.run_once(
            snapshot=_empty_snapshot(), state_dir=epoch_dir, geofence=GEOFENCE_PATH,
        )
        after_change = _wake_epoch_rows(epoch_dir)
        if [value for _ts, value in after_change] != [600, 900]:
            pytest.fail("a fourth cycle at a CHANGED cadence must add exactly one row, got %r"
                % (after_change,))
        return
    finally:
        shutil.rmtree(epoch_dir, ignore_errors=True)


def test_a_raising_epoch_write_cannot_break_a_poll_cycle(tmp_path, monkeypatch, clock):
    """a wake_epochs write raising sqlite3.Error is contained by _record_history()'s existing handler - the poll cycle completes and the panel is still written"""
    raise_dir = _mkdir(tmp_path, "wake-epochs-raise")
    try:
        device_config.save_device_config(raise_dir, wake_interval_s=600)
        clock["t"] = CLOCK_BASE

        def _boom(*args, **kwargs):
            raise sqlite3.Error("wake_epochs write exploded")

        monkeypatch.setattr(poll_loop.history_db, "record_wake_epoch", _boom)
        result = poll_loop.run_once(
            snapshot=_empty_snapshot(), state_dir=raise_dir, geofence=GEOFENCE_PATH,
        )
        if result is None or result.get("panel_changed") is None:
            pytest.fail("run_once() did not return its normal result dict: %r" % (result,))
        if not os.path.exists(os.path.join(raise_dir, "panel.bin")):
            pytest.fail("the panel was left unwritten by a failing history write")
        if _wake_epoch_rows(raise_dir) != []:
            pytest.fail("the failing write left a row behind: %r" % (_wake_epoch_rows(raise_dir),))
        return
    finally:
        shutil.rmtree(raise_dir, ignore_errors=True)


def test_apply_battery_critical_hysteresis_boundaries():
    """apply_battery_critical_hysteresis(battery_mv, was_active) holds every pinned boundary: (None, False)->False, (None, True)->True, (3300, False)->True, (3301, False)->False, (3699, True)->True, (3700, True)->False"""
    cases = [
        ((None, False), False),
        ((None, True), True),
        ((3300, False), True),
        ((3301, False), False),
        ((3699, True), True),
        ((3700, True), False),
    ]
    for (mv, was_active), expected in cases:
        got = poll_loop.apply_battery_critical_hysteresis(mv, was_active)
        if got != expected:
            pytest.fail("apply_battery_critical_hysteresis(%r, %r) = %r, expected %r"
                % (mv, was_active, got, expected))


def test_battery_empty_entry_from_live_board_renders_and_skips_detection(tmp_path, monkeypatch, clock):
    """a 3290 mV reading on the live board enters BATTERY EMPTY: state, panel_changed, the persisted hold_state/battery_critical_active latch, byte-identical panel.bin, and detection skipped entirely (detect.poll_current_aircraft/load_geofence never called)"""
    be_dir = _mkdir(tmp_path, "be-entry")
    try:
        _write_battery_state(be_dir, 3290)
        called = {"poll": False, "geofence": False}

        def _fake_poll(*args, **kwargs):
            called["poll"] = True
            return None

        def _fake_geofence(*args, **kwargs):
            called["geofence"] = True
            return {}

        monkeypatch.setattr(poll_loop.detect, "poll_current_aircraft", _fake_poll)
        monkeypatch.setattr(poll_loop.detect, "load_geofence", _fake_geofence)
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(state_dir=be_dir, geofence=GEOFENCE_PATH)
        if called["poll"] or called["geofence"]:
            pytest.fail("detection was called on BATTERY EMPTY entry: %r" % (called,))
        if result.get("state") != "battery_empty":
            pytest.fail("entry cycle returned state=%r, expected 'battery_empty'" % (result.get("state"),))
        if not result.get("panel_changed"):
            pytest.fail("entry cycle returned panel_changed=%r, expected True" % (result.get("panel_changed"),))
        on_disk = poll_loop.load_poll_state(be_dir)
        if on_disk.get("hold_state") != "battery_empty":
            pytest.fail("poll_state.json's hold_state is %r, expected 'battery_empty'" % (on_disk.get("hold_state"),))
        if on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY) is not True:
            pytest.fail("poll_state.json's battery_critical_active is %r, expected True"
                % (on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY),))
        with open(os.path.join(be_dir, "panel.bin"), "rb") as fh:
            actual = fh.read()
        expected = poll_loop.panel_format.pack_panel(poll_loop.render.build_canvas(None, "battery_empty"))
        if actual != expected:
            pytest.fail("panel.bin does not equal panel_format.pack_panel(render.build_canvas(None, 'battery_empty'))")
        return
    finally:
        shutil.rmtree(be_dir, ignore_errors=True)


def test_battery_empty_outranks_display_off(tmp_path, clock):
    """display_enabled=False plus a 3290 mV reading yields battery_empty, not display_off - the battery axis outranks the operator's own toggle"""
    d = _mkdir(tmp_path, "be-vs-off")
    try:
        device_config.save_device_config(d, display_enabled=False)
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "battery_empty":
            pytest.fail("display_enabled=False plus 3290 mV returned state=%r, expected 'battery_empty'"
                % (result.get("state"),))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_outranks_quiet_hours(tmp_path, clock):
    """an active quiet-hours window plus a 3290 mV reading yields battery_empty, not quiet_hours - a flat pack cannot honour either standing condition"""
    d = _mkdir(tmp_path, "be-vs-qh")
    try:
        device_config.save_device_config(
            d, quiet_hours_enabled=True, quiet_hours_start="23:00", quiet_hours_end="07:00",
        )
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE  # inside the window
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "battery_empty":
            pytest.fail("an active quiet-hours window plus 3290 mV returned state=%r, expected 'battery_empty'"
                % (result.get("state"),))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_entry_from_existing_display_off_hold_repaints(tmp_path, clock):
    """entering BATTERY EMPTY from an existing DISPLAY OFF hold repaints, producing the byte-identical BATTERY EMPTY canvas"""
    d = _mkdir(tmp_path, "be-from-off")
    try:
        device_config.save_device_config(d, display_enabled=False)
        _write_battery_state(d, 4000)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        with open(os.path.join(d, "panel.bin"), "rb") as fh:
            off_bytes = fh.read()
        on_disk = poll_loop.load_poll_state(d)
        if on_disk.get("hold_state") != "display_off":
            pytest.fail("setup did not enter display_off first: hold_state=%r" % (on_disk.get("hold_state"),))

        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "battery_empty":
            pytest.fail("expected state='battery_empty' after crossing into it from an active display_off "
                "hold, got %r" % (result.get("state"),))
        if not result.get("panel_changed"):
            pytest.fail("crossing from display_off into battery_empty returned panel_changed=False, expected True")
        with open(os.path.join(d, "panel.bin"), "rb") as fh:
            be_bytes = fh.read()
        if be_bytes == off_bytes:
            pytest.fail("panel.bin did not change when crossing from display_off into battery_empty")
        expected = poll_loop.panel_format.pack_panel(poll_loop.render.build_canvas(None, "battery_empty"))
        if be_bytes != expected:
            pytest.fail("panel.bin does not equal render.build_canvas(None, 'battery_empty') after the crossing")
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_parked_is_noop_across_readings_and_config_edits(tmp_path, clock):
    """parked cycles at 3290/3400/3600/3699 mV, plus a display toggle and a theme change while still parked, are all no-ops - panel.bin unchanged and no gallery entry added"""
    d = _mkdir(tmp_path, "be-parked")
    try:
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        with open(os.path.join(d, "panel.bin"), "rb") as fh:
            first_bytes = fh.read()
        gallery_dir = os.path.join(d, "gallery")
        before_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0

        t = CLOCK_BASE
        for mv in (3290, 3400, 3600, 3699):
            _write_battery_state(d, mv)
            t += 60
            clock["t"] = t
            result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
            if result.get("panel_changed"):
                pytest.fail("parked cycle at %d mV returned panel_changed=True, expected False" % (mv,))

        device_config.save_device_config(d, display_enabled=False)
        t += 60
        clock["t"] = t
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("panel_changed"):
            pytest.fail("a display toggle while parked returned panel_changed=True, expected False")

        device_config.save_device_config(d, theme="black")
        t += 60
        clock["t"] = t
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("panel_changed"):
            pytest.fail("a theme change while parked returned panel_changed=True, expected False")

        with open(os.path.join(d, "panel.bin"), "rb") as fh:
            last_bytes = fh.read()
        if last_bytes != first_bytes:
            pytest.fail("panel.bin's bytes changed across the parked episode, expected them unchanged")
        after_count = len(os.listdir(gallery_dir)) if os.path.isdir(gallery_dir) else 0
        if after_count != before_count:
            pytest.fail("a parked cycle added a gallery entry (%d -> %d), expected none" % (before_count, after_count))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_missing_or_corrupt_reading_never_parks_and_never_clears(tmp_path, clock):
    """a missing or corrupt battery_state.json can never enter BATTERY EMPTY, and deleting the file while already parked never clears the park - the persisted latch, not the file's presence, is authoritative"""
    d = _mkdir(tmp_path, "be-missing")
    try:
        # No battery_state.json at all.
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") == "battery_empty":
            pytest.fail("a missing battery_state.json entered battery_empty")

        # A corrupt one.
        with open(os.path.join(d, "battery_state.json"), "w") as fh:
            fh.write("{not valid json")
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") == "battery_empty":
            pytest.fail("a corrupt battery_state.json entered battery_empty")

        # Now genuinely park it.
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE + 120
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "battery_empty":
            pytest.fail("setup failed to park: state=%r" % (result.get("state"),))

        # Delete the file while parked - the park must hold.
        os.remove(os.path.join(d, "battery_state.json"))
        clock["t"] = CLOCK_BASE + 180
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "battery_empty":
            pytest.fail("deleting battery_state.json while parked cleared the park: state=%r"
                % (result.get("state"),))
        if result.get("panel_changed"):
            pytest.fail("deleting battery_state.json while parked triggered a repaint, expected none")
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_recovery_repaints_live_board(tmp_path, clock):
    """a 3700 mV reading clears the BATTERY EMPTY hold, repaints the live board (panel_changed=True), and the persisted battery_critical_active latch returns to False"""
    d = _mkdir(tmp_path, "be-recover")
    try:
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)

        _write_battery_state(d, 3700)
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(snapshot=_empty_snapshot(), state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") == "battery_empty":
            pytest.fail("a 3700 mV reading did not clear the BATTERY EMPTY hold")
        if not result.get("panel_changed"):
            pytest.fail("recovery did not repaint the live board: panel_changed=%r" % (result.get("panel_changed"),))
        on_disk = poll_loop.load_poll_state(d)
        if on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY) is not False:
            pytest.fail("poll_state.json's battery_critical_active is %r after recovery, expected False"
                % (on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY),))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_battery_empty_recovery_with_display_off_repaints_display_off(tmp_path, clock):
    """recovering while display_enabled=False repaints DISPLAY OFF, not the live board - the next hold in priority order"""
    d = _mkdir(tmp_path, "be-recover-off")
    try:
        device_config.save_device_config(d, display_enabled=False)
        _write_battery_state(d, 3290)
        clock["t"] = CLOCK_BASE
        poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)

        _write_battery_state(d, 3700)
        clock["t"] = CLOCK_BASE + 60
        result = poll_loop.run_once(state_dir=d, geofence=GEOFENCE_PATH)
        if result.get("state") != "display_off":
            pytest.fail("recovery with display_enabled=False returned state=%r, expected 'display_off'"
                % (result.get("state"),))
        if not result.get("panel_changed"):
            pytest.fail("recovery into display_off did not repaint: panel_changed=%r" % (result.get("panel_changed"),))
        expected = poll_loop.panel_format.pack_panel(poll_loop.render.build_canvas(None, "display_off"))
        with open(os.path.join(d, "panel.bin"), "rb") as fh:
            actual = fh.read()
        if actual != expected:
            pytest.fail("panel.bin does not equal render.build_canvas(None, 'display_off') after recovering "
                "with the toggle still off")
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_badge_threshold_reading_sets_badge_without_parking(tmp_path, clock):
    """3400 mV sets the battery-low badge (battery_low_active=True) without parking the frame (battery_critical_active stays False) - the two axes are independent"""
    d = _mkdir(tmp_path, "badge-only")
    try:
        _write_battery_state(d, 3400)
        clock["t"] = CLOCK_BASE
        result = poll_loop.run_once(
            snapshot=_snapshot("cccccc", "FLIGHT9 ", CLIMB), state_dir=d, geofence=GEOFENCE_PATH
        )
        if result.get("state") == "battery_empty":
            pytest.fail("3400 mV entered battery_empty, expected the badge only")
        on_disk = poll_loop.load_poll_state(d)
        if on_disk.get("battery_low_active") is not True:
            pytest.fail("3400 mV did not set battery_low_active: %r" % (on_disk.get("battery_low_active"),))
        if on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY) is not False:
            pytest.fail("3400 mV set battery_critical_active: %r, expected False"
                % (on_disk.get(poll_loop.wake.BATTERY_CRITICAL_STATE_KEY),))
        return
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_silence_transition_parked_suppresses_false_alert(tmp_path):
    """parked with wake_interval_s=300 and a 20-minute-old check-in, no frame_silent push is sent - the identical setup without the park sends exactly one (issue 1's fix)"""
    unparked_dir = _mkdir(tmp_path, "silence-unparked")
    parked_dir = _mkdir(tmp_path, "silence-parked")
    try:
        device_cfg = _notify_device_cfg(wake_interval_s=300)
        now_epoch = poll_loop.now_s()
        checkin_iso = _iso(now_epoch - 1200)  # 20 minutes ago

        # Control: NOT parked - a 20-minute-old check-in at a
        # 300s cadence is past the (unparked) 900s warn
        # threshold and sends exactly one silent push.
        _seed_device_health(poll_loop, unparked_dir, checkin_iso)
        control_state = {}
        control_sender = _FakeSender()
        with poll_loop.history_db.open_db(unparked_dir) as conn:
            poll_loop._notify_silence_transition(unparked_dir, control_state, conn, device_cfg, sender=control_sender)
        if len(control_sender.calls) != 1:
            pytest.fail("control (not parked): expected exactly one silent push, got %d" % len(control_sender.calls))

        # Parked: the identical 20-minute-old check-in now sits
        # well inside the 3600s BATTERY_CRITICAL_SLEEP_S-derived
        # warn window and must raise nothing.
        _seed_device_health(poll_loop, parked_dir, checkin_iso)
        poll_loop.save_poll_state(parked_dir, {poll_loop.wake.BATTERY_CRITICAL_STATE_KEY: True})
        parked_state = poll_loop.load_poll_state(parked_dir)
        parked_sender = _FakeSender()
        with poll_loop.history_db.open_db(parked_dir) as conn:
            poll_loop._notify_silence_transition(parked_dir, parked_state, conn, device_cfg, sender=parked_sender)
        if parked_sender.calls:
            pytest.fail("parked: expected no frame_silent push, got %r" % (parked_sender.calls,))
        return
    finally:
        shutil.rmtree(unparked_dir, ignore_errors=True)
        shutil.rmtree(parked_dir, ignore_errors=True)



# ==========================================================================
# run_once()'s cross-process poll_cycle_lock(), from the caller side -
# server/test_poll_lock.py owns the two-process x 200 reproduction itself;
# these tests cover run_once()'s lock_timeout_s parameter and main()'s
# PollBusy handling.
# ==========================================================================

_POLL_LOCK_HOLDER_TEMPLATE = """
import os
import sys
sys.path.insert(0, {repo_root!r})
from server import atomic_io

lock_path = os.path.join(sys.argv[1], "poll.lock")
with atomic_io.exclusive_lock(lock_path, 5):
    print("locked", flush=True)
    sys.stdin.read()  # blocks until the parent closes stdin, releasing the lock
"""

_POLL_LOCK_TIMED_HOLDER_TEMPLATE = """
import os
import sys
import time
sys.path.insert(0, {repo_root!r})
from server import atomic_io

lock_path = os.path.join(sys.argv[1], "poll.lock")
hold_s = float(sys.argv[2])
with atomic_io.exclusive_lock(lock_path, 5):
    print("locked", flush=True)
    time.sleep(hold_s)
"""


def _spawn_poll_lock_holder(state_dir, script_name, template, extra_args=()):
    """Start a child process holding <state_dir>/poll.lock, confirmed via
    its own "locked" stdout line before returning - so the parent never
    races the child's own lock acquisition.
    """
    os.makedirs(state_dir, exist_ok=True)
    script_path = os.path.join(state_dir, script_name)
    with open(script_path, "w") as fh:
        fh.write(template.format(repo_root=REPO_ROOT))
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    child = subprocess.Popen(
        [sys.executable, script_path, state_dir] + list(extra_args),
        cwd=REPO_ROOT, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    line = child.stdout.readline()
    assert line.strip() == "locked", (
        "expected the lock-holder child to report itself locked, got %r" % (line,))
    return child


def test_run_once_busy_lock_raises_promptly_and_writes_nothing(tmp_path):
    """with a child process holding poll.lock, run_once(lock_timeout_s=0) raises PollBusy
    within 0.5s and creates neither poll_state.json nor panel.bin"""
    state_dir = str(tmp_path)
    holder = _spawn_poll_lock_holder(state_dir, "_holder.py", _POLL_LOCK_HOLDER_TEMPLATE)
    try:
        start = time.monotonic()
        with pytest.raises(poll_loop.PollBusy):
            poll_loop.run_once(
                snapshot=_snapshot("aaaaaa", "FLIGHT1 ", 2400), state_dir=state_dir,
                geofence=GEOFENCE_PATH, lock_timeout_s=0)
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, (
            "expected run_once(lock_timeout_s=0) to raise promptly, took %.3fs" % elapsed)
    finally:
        holder.stdin.close()
        assert holder.wait(timeout=5) == 0

    assert not os.path.exists(os.path.join(state_dir, "poll_state.json")), (
        "a busy run_once() must never have started writing poll_state.json")
    assert not os.path.exists(os.path.join(state_dir, "panel.bin")), (
        "a busy run_once() must never have started writing panel.bin")


def test_run_once_waits_for_a_held_lock_then_completes(tmp_path):
    """a child holds poll.lock for 0.5s; run_once(lock_timeout_s=5) waits, then completes
    normally"""
    state_dir = str(tmp_path)
    holder = _spawn_poll_lock_holder(
        state_dir, "_timed_holder.py", _POLL_LOCK_TIMED_HOLDER_TEMPLATE, extra_args=("0.5",))
    try:
        result = poll_loop.run_once(
            snapshot=_snapshot("aaaaaa", "FLIGHT1 ", 2400), state_dir=state_dir,
            geofence=GEOFENCE_PATH, lock_timeout_s=5)
        assert result["flight"]["hex"] == "aaaaaa", (
            "expected run_once() to complete normally once the lock freed, got %r" % (result,))
    finally:
        assert holder.wait(timeout=5) == 0
    assert os.path.exists(os.path.join(state_dir, "poll_state.json")), (
        "expected a completed cycle to have written poll_state.json"
    )


def test_main_busy_lock_prints_the_lock_path_and_exits_1(tmp_path, monkeypatch, capsys):
    """with the lock held elsewhere and POLL_LOCK_WAIT_S monkeypatched to 0.2,
    main(["--state-dir", sd]) returns 1 and stdout names the busy lock"""
    state_dir = str(tmp_path)
    monkeypatch.setattr(poll_loop, "POLL_LOCK_WAIT_S", 0.2)
    holder = _spawn_poll_lock_holder(state_dir, "_holder.py", _POLL_LOCK_HOLDER_TEMPLATE)
    try:
        exit_code = poll_loop.main(["--state-dir", state_dir, "--geofence", GEOFENCE_PATH])
        assert exit_code == 1, "expected main() to return 1 on a busy lock, got %r" % (exit_code,)
        captured = capsys.readouterr()
        lock_path = os.path.join(state_dir, poll_loop.POLL_LOCK_FILENAME)
        assert lock_path in captured.out, (
            "expected stdout to name the busy lock path %r, got %r" % (lock_path, captured.out))
    finally:
        holder.stdin.close()
        assert holder.wait(timeout=5) == 0


# ==========================================================================
# Remaining atomic writes (panel.bin, the gallery PNG), main()'s traceback,
# a queued detection updating META_LAST_DETECTION, and now_s() reaching
# enrich.resolve_route()'s cache TTL.
# ==========================================================================


def test_panel_and_gallery_written_with_no_leftover_temp(tmp_path, clock):
    """after a cycle that changes the panel: panel.bin holds packed bytes, the gallery holds a
    PNG PIL can open, and no '*.tmp' exists in state_dir or gallery/"""
    from PIL import Image

    state_dir = str(tmp_path)
    result = poll_loop.run_once(
        snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)
    assert result["panel_changed"] is True, "expected the first-ever detection to change the panel"

    panel_path = os.path.join(state_dir, "panel.bin")
    assert os.path.isfile(panel_path), "expected panel.bin to exist"

    gallery_dir = os.path.join(state_dir, poll_loop.GALLERY_DIRNAME)
    pngs = [name for name in os.listdir(gallery_dir) if name.endswith(".png")]
    assert len(pngs) == 1, "expected exactly one gallery PNG, got %r" % (pngs,)
    with Image.open(os.path.join(gallery_dir, pngs[0])) as img:
        img.load()  # raises if the PNG is malformed/truncated

    leftovers = [name for name in os.listdir(state_dir) if name.endswith(".tmp")]
    leftovers += [name for name in os.listdir(gallery_dir) if name.endswith(".tmp")]
    assert leftovers == [], "expected no leftover .tmp file, found %r" % (leftovers,)


def test_gallery_archive_failure_is_contained_and_leaves_no_temp(tmp_path, clock, monkeypatch):
    """atomic_io.atomic_write forced to raise inside _save_to_gallery: the cycle still
    completes (existing containment) and no '*.tmp' remains"""
    state_dir = str(tmp_path)
    gallery_dir = os.path.join(state_dir, poll_loop.GALLERY_DIRNAME)
    calls = []
    real_atomic_write = poll_loop.atomic_io.atomic_write

    def spy_atomic_write(path, data, mode=None):
        calls.append(path)
        if gallery_dir in path:
            raise OSError("disk full (injected)")
        return real_atomic_write(path, data, mode=mode)

    monkeypatch.setattr(poll_loop.atomic_io, "atomic_write", spy_atomic_write)

    result = poll_loop.run_once(
        snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)

    assert any(gallery_dir in path for path in calls), (
        "expected _save_to_gallery() to archive the panel through atomic_io.atomic_write(), got "
        "no call under %r; calls=%r" % (gallery_dir, calls))
    assert result["panel_changed"] is True, (
        "expected the gallery archive failure to be contained, not to fail the whole cycle")
    assert os.path.isfile(os.path.join(state_dir, "panel.bin")), (
        "expected panel.bin to have been written despite the gallery archive failure")

    leftovers = []
    if os.path.isdir(gallery_dir):
        leftovers = [name for name in os.listdir(gallery_dir) if name.endswith(".tmp")]
    assert leftovers == [], "expected no leftover .tmp file in the gallery dir, found %r" % (leftovers,)


def test_main_generic_failure_prints_traceback_to_stdout(tmp_path, monkeypatch, capsys):
    """main() with run_once monkeypatched to raise ValueError("boom"): returns 1, and captured
    stdout contains "Traceback (most recent call last)" and "ValueError: boom" """
    def _raise(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(poll_loop, "run_once", _raise)
    exit_code = poll_loop.main(["--state-dir", str(tmp_path), "--geofence", GEOFENCE_PATH])
    assert exit_code == 1, "expected main() to return 1 on a generic failure, got %r" % (exit_code,)
    captured = capsys.readouterr()
    assert "Traceback (most recent call last)" in captured.out, (
        "expected a full traceback in stdout, got %r" % (captured.out,))
    assert "ValueError: boom" in captured.out, (
        "expected the exception's own message in stdout, got %r" % (captured.out,))


def test_queued_detection_updates_last_detection_meta(tmp_path, monkeypatch):
    """cycle 1 detects A (displayed); cycle 2 within MIN_ADVANCE_INTERVAL_S detects B, which is
    queued (held branch); with history_db.utc_now_iso monkeypatched to return distinct values per
    cycle, META_LAST_DETECTION equals cycle 2's value"""
    state_dir = str(tmp_path)
    # A mutable holder, not an iterator: history_db.set_meta() calls
    # utc_now_iso() again for its own row timestamp, so every call within
    # one cycle must see that SAME cycle's value.
    fake_iso = {"value": "2026-01-01T00:00:00+00:00"}
    monkeypatch.setattr(poll_loop.history_db, "utc_now_iso", lambda: fake_iso["value"])

    poll_loop.run_once(
        snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)
    fake_iso["value"] = "2026-01-01T00:00:05+00:00"
    # A distinct aircraft, detected well within MIN_ADVANCE_INTERVAL_S of
    # cycle 1 (no clock fixture here - real wall-clock, but two
    # back-to-back calls are microseconds apart) - queued, not promoted.
    poll_loop.run_once(
        snapshot=_snapshot("bbbbbb", "FLIGHT2 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)

    with poll_loop.history_db.open_db(state_dir) as conn:
        last_detection = poll_loop.history_db.get_meta(conn, poll_loop.history_db.META_LAST_DETECTION)
    assert last_detection == "2026-01-01T00:00:05+00:00", (
        "expected META_LAST_DETECTION to record the SECOND cycle's timestamp (a queued "
        "detection still counts as a detection), got %r" % (last_detection,))


def test_held_cycle_with_no_detection_leaves_last_detection_unchanged(tmp_path, monkeypatch):
    """a held cycle with no detection leaves META_LAST_DETECTION unchanged"""
    state_dir = str(tmp_path)
    fake_iso = {"value": "2026-01-01T00:00:00+00:00"}
    monkeypatch.setattr(poll_loop.history_db, "utc_now_iso", lambda: fake_iso["value"])

    poll_loop.run_once(
        snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)
    fake_iso["value"] = "2026-01-01T00:00:05+00:00"
    poll_loop.run_once(
        snapshot=_empty_snapshot(), state_dir=state_dir, geofence=GEOFENCE_PATH)

    with poll_loop.history_db.open_db(state_dir) as conn:
        last_detection = poll_loop.history_db.get_meta(conn, poll_loop.history_db.META_LAST_DETECTION)
    assert last_detection == "2026-01-01T00:00:00+00:00", (
        "expected META_LAST_DETECTION to stay at cycle 1's timestamp when cycle 2 detects "
        "nothing, got %r" % (last_detection,))


def test_now_s_clock_reaches_adsbdb_cache_stamp(tmp_path, clock):
    """with the clock fixture at T, a cycle that enriches a callsign stores cached_at == T in
    poll_state's enrichment_cache (proves now_s() reaches enrich.resolve_route())"""
    state_dir = str(tmp_path)
    clock["t"] = CLOCK_BASE + 12345

    poll_loop.run_once(
        snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=state_dir, geofence=GEOFENCE_PATH)

    on_disk = poll_loop.load_poll_state(state_dir)
    cache = on_disk.get("enrichment_cache", {})
    entry = cache.get("FLIGHT1")
    assert entry is not None, (
        "expected an enrichment_cache entry for the normalised callsign 'FLIGHT1', got keys %r"
        % (list(cache.keys()),))
    assert entry.get("cached_at") == clock["t"], (
        "expected cached_at to equal the injected clock's time (poll_loop.now_s() must reach "
        "enrich.resolve_route()), got %r" % (entry.get("cached_at"),))
