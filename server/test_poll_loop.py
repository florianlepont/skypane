#!/usr/bin/env python3
"""Contract harness for server/poll_loop.py's two-deep flight history
(D-25, 03-CONTEXT.md decisions_addendum_2) - the engineering consequence of
the current+previous two-flight poster layout: a genuinely new detection
(different ICAO hex) must shift the old "current" flight down into
"previous" before being overwritten; re-detecting the same aircraft must
not shift anything.

Also covers (quick task 260827-oz9) cross-cycle persistence of the
unresolved-ICAO-prefix registry: that a registry entry survives the
process boundary between two separate `run_once()` invocations against the
same state directory, that a recognized-airline cycle leaves it untouched,
and that the poll line's `unknown_prefix=` field names the recorded prefix
on a miss cycle and reads `None` on a covered cycle.

Stdlib-only, plus the module under test (server.poll_loop, which
transitively imports Pillow via server.plane.render) - must be run under
server/.venv's interpreter. Exits 0 only when every check below passes.

NOTE: `run_once()` calls `enrich.resolve_route()` with no injected
transport, so by default it reaches live adsbdb over the network for the
FLIGHT1-4 callsigns checks 1-5 use (this harness is not hermetic on that
axis today - a pre-existing condition, not introduced by this plan). Checks
6-8 below stub `enrich.default_transport` in a try/finally specifically so
their outcome does not depend on the network or on what adsbdb happens to
know today.

Usage:
    server/.venv/bin/python3 server/test_poll_loop.py
"""
import contextlib
import hashlib
import io
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 27

# Pins the default-config panel.bin digest produced against the FLIGHT1
# fixture (check 1's own _run("aaaaaa", "FLIGHT1 ") snapshot) - hand-
# verified byte-identical against the pre-06-10 implementation for an
# equivalent fixture before this plan's config/theme/runway/fault plumbing
# landed (06-10-SUMMARY.md records the exact comparison). Proves the
# default rendering path did not move.
_DEFAULT_CONFIG_DIGEST = "cc5cea2dca06416a6652f336f3fa7b6485409e7988d24b54af758d207cea19d8"


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


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.poll_loop as poll_loop
    except ImportError as exc:
        print("FAIL import server.poll_loop - %r" % (exc,))
        print("poll-loop: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    import server.device_config as device_config
    import server.plane.detect as detect
    from server import history_db

    tmpdir = tempfile.mkdtemp(prefix="skypane-poll-loop-history-")
    try:
        # A strong, unambiguous +2400 ft/min climb - clears the D-P2-04
        # deadband on the very first cycle, so confirmed_state is never
        # None here (irrelevant to what this harness tests).
        CLIMB = 2400

        def _run(hex_code, callsign):
            poll_loop.run_once(snapshot=_snapshot(hex_code, callsign, CLIMB), state_dir=tmpdir, geofence=GEOFENCE_PATH)
            return poll_loop.load_poll_state(tmpdir)

        # 1. First-ever detection: no previous_flight yet.
        state1 = _run("aaaaaa", "FLIGHT1 ")
        def _first_detection_has_no_previous():
            if state1.get("last_flight", {}).get("hex") != "aaaaaa":
                return False, "last_flight after the first detection is %r, expected hex=aaaaaa" % (state1.get("last_flight"),)
            if state1.get("previous_flight") is not None:
                return False, "previous_flight after the very first detection is %r, expected None" % (state1.get("previous_flight"),)
            return True, ""
        check("the first-ever detection sets last_flight and leaves previous_flight as None", _first_detection_has_no_previous)

        # 2. Re-detecting the SAME aircraft (same hex) across consecutive
        # cycles must NOT shift anything into previous_flight.
        state2 = _run("aaaaaa", "FLIGHT1 ")
        def _same_hex_redetection_does_not_shift():
            if state2.get("previous_flight") is not None:
                return False, "previous_flight after re-detecting the SAME hex is %r, expected still None (D-25: same aircraft, not a new one)" % (state2.get("previous_flight"),)
            if state2.get("last_flight", {}).get("hex") != "aaaaaa":
                return False, "last_flight after re-detection is %r, expected hex=aaaaaa" % (state2.get("last_flight"),)
            return True, ""
        check("re-detecting the same hex across consecutive cycles does not shift anything into previous_flight", _same_hex_redetection_does_not_shift)

        # 3. A genuinely NEW aircraft (different hex) shifts the old
        # current flight down into previous_flight.
        state3 = _run("bbbbbb", "FLIGHT2 ")
        def _new_hex_shifts_old_current_into_previous():
            if state3.get("last_flight", {}).get("hex") != "bbbbbb":
                return False, "last_flight after a new-hex detection is %r, expected hex=bbbbbb" % (state3.get("last_flight"),)
            if state3.get("previous_flight", {}).get("hex") != "aaaaaa":
                return False, "previous_flight after a new-hex detection is %r, expected hex=aaaaaa (the old current flight)" % (state3.get("previous_flight"),)
            if state3.get("previous_confirmed_state") != "departing":
                return False, "previous_confirmed_state is %r, expected 'departing' (aaaaaa's confirmed state before the shift)" % (state3.get("previous_confirmed_state"),)
            return True, ""
        check("a genuinely new aircraft (different hex) shifts the old current flight into previous_flight/previous_confirmed_state", _new_hex_shifts_old_current_into_previous)

        # 4. A third, distinct aircraft shifts again - previous_flight
        # tracks the immediately-preceding detection only (two-deep, not a
        # full history).
        state4 = _run("cccccc", "FLIGHT3 ")
        def _third_detection_shifts_again_two_deep_only():
            if state4.get("last_flight", {}).get("hex") != "cccccc":
                return False, "last_flight after a third distinct detection is %r, expected hex=cccccc" % (state4.get("last_flight"),)
            if state4.get("previous_flight", {}).get("hex") != "bbbbbb":
                return False, "previous_flight after a third distinct detection is %r, expected hex=bbbbbb (immediately preceding, not aaaaaa)" % (state4.get("previous_flight"),)
            return True, ""
        check("a third distinct detection shifts again - previous_flight tracks only the immediately-preceding detection (two-deep)", _third_detection_shifts_again_two_deep_only)

        # 5. render.build_canvas() was actually called with the shifted
        # previous_flight/previous_route/previous_state (not just recorded
        # in poll_state.json but plumbed through to the render call) - spy
        # on render.build_canvas via the module poll_loop already imported.
        # (plan 06-10 Task 2 restructured poll_loop.py's render call sites
        # from render.render_panel() to render.build_canvas() +
        # panel_format.pack_panel(), so the gallery hook can archive the
        # pre-pack canvas without a second render pass - this check follows
        # that restructuring rather than testing a call site that no longer
        # exists.)
        def _previous_flight_is_plumbed_into_render_panel():
            import server.plane.render as render

            captured = {}
            original = render.build_canvas

            def _spy(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None, **kwargs):
                # **kwargs (plan 06-10): forward-compatible with run_once()'s
                # new theme_id/runway_id/source_fault keyword arguments -
                # this check only cares about previous_flight/previous_state,
                # so it passes anything else straight through unexamined.
                captured["previous_flight"] = previous_flight
                captured["previous_state"] = previous_state
                return original(flight, state, route=route, previous_flight=previous_flight, previous_route=previous_route, previous_state=previous_state, **kwargs)

            poll_loop.render.build_canvas = _spy
            try:
                poll_loop.run_once(snapshot=_snapshot("dddddd", "FLIGHT4 ", CLIMB), state_dir=tmpdir, geofence=GEOFENCE_PATH)
            finally:
                poll_loop.render.build_canvas = original

            if captured.get("previous_flight", {}).get("hex") != "cccccc":
                return False, "build_canvas() was called with previous_flight=%r, expected hex=cccccc" % (captured.get("previous_flight"),)
            return True, ""
        check("render.build_canvas() is actually called with the shifted previous_flight (not just recorded in poll_state.json)", _previous_flight_is_plumbed_into_render_panel)

        # NOTE: checks 1-5 above already populate poll_state.json's
        # unresolved_prefixes registry as a harmless side effect - FLIGHT1
        # through FLIGHT4 are shape-valid callsigns whose prefix ("FLI") is
        # absent from _ICAO_AIRLINE_PREFIXES, so they are genuine misses
        # that the recorder is *supposed* to record. That is the feature
        # working, not test leakage (ground-truth item 2) - do not "fix"
        # it by renaming those callsigns or adding an opt-out to
        # run_once().

        # --- quick task 260827-oz9: cross-cycle persistence of the
        # unresolved-ICAO-prefix registry --------------------------------

        import server.plane.enrich as enrich

        # 6. The registry accumulates across separate poll cycles, read
        #    back from disk between cycles - the only assertion in this
        #    suite that proves the record survives the process boundary
        #    the systemd oneshot actually crosses.
        def _unresolved_prefix_registry_accumulates_across_cycles():
            original_transport = enrich.default_transport
            enrich.default_transport = lambda callsign, timeout=None: (404, None)
            try:
                oz9_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-oz9-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    state_after_1 = poll_loop.load_poll_state(oz9_dir)
                    reg1 = state_after_1.get("unresolved_prefixes")
                    if not isinstance(reg1, dict) or reg1.get("ZZQ", {}).get("count") != 1:
                        return False, "after cycle 1, unresolved_prefixes = %r, expected ZZQ at count 1" % (reg1,)

                    poll_loop.run_once(snapshot=_snapshot("222222", "ZZQ5678", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    state_after_2 = poll_loop.load_poll_state(oz9_dir)
                    reg2 = state_after_2.get("unresolved_prefixes")
                    if list(reg2) != ["ZZQ"] or reg2["ZZQ"].get("count") != 2:
                        return False, "after cycle 2, unresolved_prefixes = %r, expected one entry ZZQ at count 2" % (reg2,)
                    if reg2["ZZQ"].get("first_seen") != reg1["ZZQ"].get("first_seen"):
                        return False, "first_seen moved between cycles: %r -> %r" % (reg1["ZZQ"].get("first_seen"), reg2["ZZQ"].get("first_seen"))
                    if reg2["ZZQ"].get("example_callsign") != "ZZQ5678":
                        return False, "example_callsign after cycle 2 = %r, expected 'ZZQ5678'" % (reg2["ZZQ"].get("example_callsign"),)
                    return True, ""
                finally:
                    shutil.rmtree(oz9_dir, ignore_errors=True)
            finally:
                enrich.default_transport = original_transport
        check(
            "the unresolved-prefix registry accumulates across two separate run_once() cycles against the same "
            "state directory, read back from poll_state.json on disk between cycles (260827-oz9)",
            _unresolved_prefix_registry_accumulates_across_cycles,
        )

        # 7. A recognized airline records nothing - the zero-noise
        #    guarantee.
        def _recognized_airline_leaves_registry_untouched():
            original_transport = enrich.default_transport
            enrich.default_transport = lambda callsign, timeout=None: (404, None)
            try:
                oz9_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-oz9-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    reg_before = poll_loop.load_poll_state(oz9_dir).get("unresolved_prefixes")

                    poll_loop.run_once(snapshot=_snapshot("333333", "AFR1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    reg_after = poll_loop.load_poll_state(oz9_dir).get("unresolved_prefixes")

                    if reg_after != reg_before:
                        return False, "a recognized airline (AFR) changed the registry: %r -> %r" % (reg_before, reg_after)
                    return True, ""
                finally:
                    shutil.rmtree(oz9_dir, ignore_errors=True)
            finally:
                enrich.default_transport = original_transport
        check(
            "a cycle detecting a callsign whose prefix IS in _ICAO_AIRLINE_PREFIXES leaves unresolved_prefixes "
            "byte-identical - the registry is a list of gaps, not a log of every adsbdb miss (260827-oz9)",
            _recognized_airline_leaves_registry_untouched,
        )

        # 8. The journal line names the prefix on a miss cycle and reads
        #    None on a covered cycle; every pre-existing field is still
        #    present.
        def _journal_line_names_unknown_prefix():
            original_transport = enrich.default_transport
            enrich.default_transport = lambda callsign, timeout=None: (404, None)
            try:
                oz9_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-oz9-")
                try:
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    miss_line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
                    if "unknown_prefix=ZZQ" not in miss_line:
                        return False, "the poll line never names the recorded prefix: %s" % (miss_line,)

                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        poll_loop.run_once(snapshot=_snapshot("333333", "AFR1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    covered_line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
                    if "unknown_prefix=None" not in covered_line:
                        return False, "a covered prefix was named in the log field: %s" % (covered_line,)

                    for field in ("hex=", "callsign=", "aircraft_type=", "corroborated=", "route_source=", "panel_changed="):
                        for line in (miss_line, covered_line):
                            if field not in line:
                                return False, "existing log field %s was lost: %s" % (field, line)
                    return True, ""
                finally:
                    shutil.rmtree(oz9_dir, ignore_errors=True)
            finally:
                enrich.default_transport = original_transport
        check(
            "the poll_loop: line's unknown_prefix= field names the recorded prefix on a miss cycle, reads None on "
            "a covered cycle, and every pre-existing field is still present (260827-oz9)",
            _journal_line_names_unknown_prefix,
        )

        # --- plan 06-10: config/theme/runway threading, CFG-05 fault
        # classification and its transition gate, history write gating,
        # gallery retention/pruning, failure containment of both hooks, the
        # default-path byte identity, and the cross-module runway-id
        # agreement. Every check below stubs enrich.default_transport (no
        # live network call) and uses its own fresh temp state directory,
        # never the shared `tmpdir` checks 1-8 already populated. ---------

        original_transport = enrich.default_transport
        enrich.default_transport = lambda callsign, timeout=None: (404, None)
        try:

            # 9. The cross-module consistency check this phase has been
            # deferring: device_config.RUNWAYS and the geofence file's own
            # runway id set must agree exactly - plans 06-01/06-02 each
            # defined one of those key sets independently so they could be
            # built in parallel.
            def _runway_ids_agree_across_device_config_and_geofence():
                geofence = detect.load_geofence(GEOFENCE_PATH)
                geofence_ids = set(geofence.get("runways") or {})
                config_ids = set(device_config.RUNWAYS)
                if config_ids != geofence_ids:
                    return False, (
                        "device_config.RUNWAYS=%r does not match adsb-test/runway3.json's runways=%r - "
                        "the two runway-id sets must agree" % (sorted(config_ids), sorted(geofence_ids))
                    )
                return True, ""
            check(
                "device_config.RUNWAYS and the geofence file's own runway id set agree exactly",
                _runway_ids_agree_across_device_config_and_geofence,
            )

            # 10. Byte-identity regression gate against the pinned pre-06-10
            # digest (default config, FLIGHT1 fixture).
            def _default_config_byte_identity():
                digest_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-digest-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=digest_dir, geofence=GEOFENCE_PATH)
                    with open(os.path.join(digest_dir, "panel.bin"), "rb") as fh:
                        data = fh.read()
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != _DEFAULT_CONFIG_DIGEST:
                        return False, "panel.bin digest %s != pinned %s" % (digest, _DEFAULT_CONFIG_DIGEST)
                    return True, ""
                finally:
                    shutil.rmtree(digest_dir, ignore_errors=True)
            check(
                "a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest",
                _default_config_byte_identity,
            )

            # 11. A saved non-default runway reaches
            # detect.select_aircraft_for_runway on the injected-snapshot
            # branch.
            def _non_default_runway_reaches_select_aircraft_for_runway():
                runway_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-runway-")
                try:
                    device_config.save_device_config(runway_dir, tracked_runway="06-24")
                    captured = {}
                    original = detect.select_aircraft_for_runway

                    def _spy(aircraft, geofence, runway_id=device_config.DEFAULT_RUNWAY_ID):
                        captured["runway_id"] = runway_id
                        return original(aircraft, geofence, runway_id=runway_id)

                    poll_loop.detect.select_aircraft_for_runway = _spy
                    try:
                        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=runway_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.select_aircraft_for_runway = original
                    if captured.get("runway_id") != "06-24":
                        return False, "select_aircraft_for_runway received runway_id=%r, expected '06-24'" % (captured.get("runway_id"),)
                    return True, ""
                finally:
                    shutil.rmtree(runway_dir, ignore_errors=True)
            check(
                "a saved non-default tracked runway reaches detect.select_aircraft_for_runway on the injected-snapshot branch",
                _non_default_runway_reaches_select_aircraft_for_runway,
            )

            # 12. A saved non-default runway reaches
            # detect.poll_current_aircraft on the live branch (hermetic:
            # poll_current_aircraft itself is monkeypatched, no network).
            def _non_default_runway_reaches_poll_current_aircraft():
                runway_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-runway-live-")
                try:
                    device_config.save_device_config(runway_dir, tracked_runway="02-20")
                    captured = {}

                    def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
                        captured["runway_id"] = runway_id
                        if diagnostics is not None:
                            diagnostics.update({"queried": [], "failed": [], "selected": [], "disagreement": False, "runway_id": runway_id})
                        return None

                    original = poll_loop.detect.poll_current_aircraft
                    poll_loop.detect.poll_current_aircraft = _fake_poll
                    try:
                        poll_loop.run_once(state_dir=runway_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.poll_current_aircraft = original
                    if captured.get("runway_id") != "02-20":
                        return False, "poll_current_aircraft received runway_id=%r, expected '02-20'" % (captured.get("runway_id"),)
                    return True, ""
                finally:
                    shutil.rmtree(runway_dir, ignore_errors=True)
            check(
                "a saved non-default tracked runway reaches detect.poll_current_aircraft on the live branch",
                _non_default_runway_reaches_poll_current_aircraft,
            )

            # 13. An all-providers-failed diagnostics report yields a true
            # source_fault flag, reaching render.build_canvas.
            def _all_failed_diagnostics_yields_true_fault_flag():
                fault_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-fault-")
                try:
                    def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
                        if diagnostics is not None:
                            diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": ["adsbfi", "adsblol"], "selected": [], "disagreement": False, "runway_id": runway_id})
                        return None

                    captured = {}
                    original_poll = poll_loop.detect.poll_current_aircraft
                    original_build = poll_loop.render.build_canvas

                    def _spy_build(flight, state, **kwargs):
                        captured["source_fault"] = kwargs.get("source_fault")
                        return original_build(flight, state, **kwargs)

                    poll_loop.detect.poll_current_aircraft = _fake_poll
                    poll_loop.render.build_canvas = _spy_build
                    try:
                        result = poll_loop.run_once(state_dir=fault_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.poll_current_aircraft = original_poll
                        poll_loop.render.build_canvas = original_build
                    if result.get("source_fault") is not True:
                        return False, "run_once() result source_fault=%r, expected True" % (result.get("source_fault"),)
                    if captured.get("source_fault") is not True:
                        return False, "render.build_canvas() received source_fault=%r, expected True" % (captured.get("source_fault"),)
                    return True, ""
                finally:
                    shutil.rmtree(fault_dir, ignore_errors=True)
            check(
                "an all-providers-failed diagnostics report yields a true source_fault flag passed to render.build_canvas",
                _all_failed_diagnostics_yields_true_fault_flag,
            )

            # 14. Providers queried successfully with nothing selected
            # leaves the fault flag false - the opposing case to check 13.
            def _successful_query_no_selection_yields_false_fault_flag():
                fault_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-nofault-")
                try:
                    def _fake_poll(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
                        if diagnostics is not None:
                            diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": [], "selected": [], "disagreement": False, "runway_id": runway_id})
                        return None

                    original = poll_loop.detect.poll_current_aircraft
                    poll_loop.detect.poll_current_aircraft = _fake_poll
                    try:
                        result = poll_loop.run_once(state_dir=fault_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.poll_current_aircraft = original
                    if result.get("source_fault") is not False:
                        return False, "run_once() result source_fault=%r, expected False" % (result.get("source_fault"),)
                    return True, ""
                finally:
                    shutil.rmtree(fault_dir, ignore_errors=True)
            check(
                "providers queried successfully with nothing selected leaves the source_fault flag false",
                _successful_query_no_selection_yields_false_fault_flag,
            )

            # 15. The injected-snapshot branch never sets the fault flag,
            # even against a previously-persisted true value.
            def _injected_snapshot_branch_never_sets_fault():
                snap_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-snapfault-")
                try:
                    with history_db.open_db(snap_dir) as conn:
                        history_db.set_meta(conn, history_db.META_SOURCE_FAULT, "True")
                    result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=snap_dir, geofence=GEOFENCE_PATH)
                    if result.get("source_fault") is not False:
                        return False, "injected-snapshot branch returned source_fault=%r, expected False" % (result.get("source_fault"),)
                    return True, ""
                finally:
                    shutil.rmtree(snap_dir, ignore_errors=True)
            check(
                "the injected-snapshot branch never sets the source_fault flag, regardless of a previously-persisted true value",
                _injected_snapshot_branch_never_sets_fault,
            )

            # 16. T-06-10-04: two consecutive cycles with an unchanged true
            # fault flag and no new detection write panel.bin exactly once.
            def _fault_transition_gated_not_value():
                trans_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-transition-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=trans_dir, geofence=GEOFENCE_PATH)

                    def _fake_poll_all_failed(geofence, timeout=10.0, providers=None, runway_id=device_config.DEFAULT_RUNWAY_ID, diagnostics=None):
                        if diagnostics is not None:
                            diagnostics.update({"queried": ["adsbfi", "adsblol"], "failed": ["adsbfi", "adsblol"], "selected": [], "disagreement": False, "runway_id": runway_id})
                        return None

                    original = poll_loop.detect.poll_current_aircraft
                    poll_loop.detect.poll_current_aircraft = _fake_poll_all_failed
                    try:
                        r1 = poll_loop.run_once(state_dir=trans_dir, geofence=GEOFENCE_PATH)
                        r2 = poll_loop.run_once(state_dir=trans_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.poll_current_aircraft = original
                    writes = sum(1 for r in (r1, r2) if r.get("panel_changed"))
                    if writes != 1:
                        return False, "two consecutive cycles with an unchanged true fault flag wrote panel.bin %d times, expected exactly 1" % (writes,)
                    return True, ""
                finally:
                    shutil.rmtree(trans_dir, ignore_errors=True)
            check(
                "two consecutive cycles with an unchanged true fault flag and no new detection write panel.bin exactly once, not twice",
                _fault_transition_gated_not_value,
            )

            # 17. The log line gains theme=/tracked_runway=/source_fault=
            # fields and stays a single print() per cycle.
            def _log_line_gains_theme_runway_fault_fields():
                log_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-logfields-")
                try:
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=log_dir, geofence=GEOFENCE_PATH)
                    lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: hex=")]
                    if len(lines) != 1:
                        return False, "expected exactly one 'poll_loop: hex=' line, found %d" % (len(lines),)
                    line = lines[0]
                    for field in ("theme=", "tracked_runway=", "source_fault="):
                        if field not in line:
                            return False, "log line missing new field %s: %s" % (field, line)
                    return True, ""
                finally:
                    shutil.rmtree(log_dir, ignore_errors=True)
            check(
                "the poll_loop: log line gains theme=/tracked_runway=/source_fault= fields and stays a single print() per cycle",
                _log_line_gains_theme_runway_fault_fields,
            )

            # 18. Detecting a new aircraft writes exactly one runway_events
            # row; re-detecting it unchanged writes no further row.
            def _history_row_written_only_on_hex_transition():
                hist_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-hist-hex-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                    with history_db.open_db(hist_dir) as conn:
                        count1 = len(history_db.recent_runway_events(conn, limit=100))
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                    with history_db.open_db(hist_dir) as conn:
                        count2 = len(history_db.recent_runway_events(conn, limit=100))
                    if count1 != 1:
                        return False, "first-ever detection produced %d runway_events rows, expected exactly 1" % (count1,)
                    if count2 != 1:
                        return False, "re-detecting the same hex with an unchanged state produced %d total rows, expected still 1" % (count2,)
                    return True, ""
                finally:
                    shutil.rmtree(hist_dir, ignore_errors=True)
            check(
                "detecting a new aircraft writes exactly one runway_events row; re-detecting it unchanged writes no further row",
                _history_row_written_only_on_hex_transition,
            )

            # 19. A confirmed_state flip on the same hex writes a new row.
            def _history_row_written_on_confirmed_state_flip():
                hist_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-hist-state-")
                try:
                    DESCEND = -2400
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", DESCEND), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                    with history_db.open_db(hist_dir) as conn:
                        rows = history_db.recent_runway_events(conn, limit=100)
                    if len(rows) != 2:
                        return False, "a confirmed_state flip on the same hex produced %d total rows, expected 2" % (len(rows),)
                    states = sorted(r["confirmed_state"] for r in rows)
                    if states != ["arriving", "departing"]:
                        return False, "expected one departing and one arriving row, got %r" % (states,)
                    return True, ""
                finally:
                    shutil.rmtree(hist_dir, ignore_errors=True)
            check(
                "a confirmed_state flip on the same hex writes a new runway_events row",
                _history_row_written_on_confirmed_state_flip,
            )

            # 20. A corroboration flip on the same hex/state writes a new
            # row - detect.select_aircraft_for_runway is monkeypatched
            # (the injected-snapshot branch never sets "corroborated"
            # itself) so this stays hermetic and independent of live
            # cross-source agreement.
            def _history_row_written_on_corroboration_flip():
                hist_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-hist-corrob-")
                try:
                    base_flight = {
                        "hex": "aaaaaa", "callsign": "FLIGHT1", "aircraft_type": None,
                        "altitude_ft": 450.0, "on_ground": False, "vertical_rate_fpm": CLIMB,
                        "lat": 48.7233, "lon": 2.3794, "gs": 137.1, "seen_pos": 1.0,
                        "along_track_m": 0.0, "cross_track_m": 0.0, "track_deg": None,
                        "track_deviation_deg": None, "selected_runway": "3",
                    }
                    calls = {"n": 0}
                    original = poll_loop.detect.select_aircraft_for_runway

                    def _spy(aircraft, geofence, runway_id=device_config.DEFAULT_RUNWAY_ID):
                        calls["n"] += 1
                        flight = dict(base_flight)
                        flight["corroborated"] = True if calls["n"] == 1 else False
                        return flight

                    poll_loop.detect.select_aircraft_for_runway = _spy
                    try:
                        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                        poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.detect.select_aircraft_for_runway = original
                    with history_db.open_db(hist_dir) as conn:
                        rows = history_db.recent_runway_events(conn, limit=100)
                    if len(rows) != 2:
                        return False, "a corroboration flip on the same hex/state produced %d total rows, expected 2" % (len(rows),)
                    corroborated_values = sorted(r["corroborated"] for r in rows)
                    if corroborated_values != ["False", "True"]:
                        return False, "expected one True and one False corroborated row, got %r" % (corroborated_values,)
                    return True, ""
                finally:
                    shutil.rmtree(hist_dir, ignore_errors=True)
            check(
                "a corroboration flip on the same hex/confirmed_state writes a new runway_events row",
                _history_row_written_on_corroboration_flip,
            )

            # 21. The pipeline-run meta timestamp is rewritten on every
            # cycle, including one that writes no runway_events row.
            def _pipeline_run_meta_updated_every_cycle():
                meta_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-meta-")
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
                        return False, "expected the second (unchanged) cycle to write no new row, found %d total" % (len(rows),)
                    if ts_after == "SENTINEL" or not ts_after:
                        return False, "pipeline-run meta timestamp was not rewritten on a no-new-row cycle: %r" % (ts_after,)
                    return True, ""
                finally:
                    shutil.rmtree(meta_dir, ignore_errors=True)
            check(
                "the pipeline-run meta timestamp updates on every cycle, including one that writes no runway_events row",
                _pipeline_run_meta_updated_every_cycle,
            )

            # 22. A changed panel saves one gallery image; an unchanged
            # cycle saves none.
            def _gallery_archives_only_changed_panels():
                gal_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-gallery-changed-")
                try:
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=gal_dir, geofence=GEOFENCE_PATH)
                    entries_after_1 = os.listdir(os.path.join(gal_dir, "gallery"))
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=gal_dir, geofence=GEOFENCE_PATH)
                    entries_after_2 = os.listdir(os.path.join(gal_dir, "gallery"))
                    if len(entries_after_1) != 1:
                        return False, "a changed-bytes cycle produced %d gallery entries, expected 1" % (len(entries_after_1),)
                    if len(entries_after_2) != len(entries_after_1):
                        return False, "an unchanged-bytes cycle changed the gallery entry count: %d -> %d" % (len(entries_after_1), len(entries_after_2))
                    return True, ""
                finally:
                    shutil.rmtree(gal_dir, ignore_errors=True)
            check(
                "a panel write with changed bytes saves one image into the gallery; an unchanged-bytes cycle saves none",
                _gallery_archives_only_changed_panels,
            )

            # 23. The gallery never holds more than GALLERY_MAX_ENTRIES;
            # the oldest entries are removed first.
            def _gallery_prunes_to_max_entries():
                cap_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-gallery-cap-")
                try:
                    gallery_dir = os.path.join(cap_dir, "gallery")
                    os.makedirs(gallery_dir)
                    for i in range(30):
                        with open(os.path.join(gallery_dir, "2020-01-01T00-00-%02d+00-00.png" % i), "wb") as fh:
                            fh.write(b"x")
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=cap_dir, geofence=GEOFENCE_PATH)
                    entries = sorted(os.listdir(gallery_dir))
                    if len(entries) != poll_loop.GALLERY_MAX_ENTRIES:
                        return False, "gallery holds %d entries after a changed cycle, expected exactly GALLERY_MAX_ENTRIES=%d" % (len(entries), poll_loop.GALLERY_MAX_ENTRIES)
                    if "2020-01-01T00-00-00+00-00.png" in entries:
                        return False, "the oldest seeded entry was not pruned: %r" % (entries,)
                    return True, ""
                finally:
                    shutil.rmtree(cap_dir, ignore_errors=True)
            check(
                "the gallery never holds more than GALLERY_MAX_ENTRIES; the oldest entries are removed first",
                _gallery_prunes_to_max_entries,
            )

            # 24. A read-only gallery directory does not fail the cycle.
            def _readonly_gallery_dir_does_not_fail_cycle():
                ro_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-gallery-ro-")
                try:
                    gallery_dir = os.path.join(ro_dir, "gallery")
                    os.makedirs(gallery_dir)
                    os.chmod(gallery_dir, 0o500)
                    try:
                        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=ro_dir, geofence=GEOFENCE_PATH)
                    finally:
                        os.chmod(gallery_dir, 0o700)
                    if not result.get("panel_changed"):
                        return False, "run_once() reported panel_changed=%r, expected True" % (result.get("panel_changed"),)
                    if not os.path.exists(os.path.join(ro_dir, "panel.bin")):
                        return False, "panel.bin was not written when the gallery directory was read-only"
                    return True, ""
                finally:
                    shutil.rmtree(ro_dir, ignore_errors=True)
            check(
                "a read-only gallery directory does not fail the cycle - run_once() still returns and panel.bin is still written",
                _readonly_gallery_dir_does_not_fail_cycle,
            )

            # 25. A history.db failure (open_db raising) is caught and
            # logged without failing the cycle or leaving panel.bin
            # unwritten.
            def _history_write_failure_does_not_fail_cycle():
                hist_fail_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-histfail-")
                try:
                    def _boom(*args, **kwargs):
                        raise sqlite3.OperationalError("simulated lock")

                    original_open_db = poll_loop.history_db.open_db
                    poll_loop.history_db.open_db = _boom
                    try:
                        result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=hist_fail_dir, geofence=GEOFENCE_PATH)
                    finally:
                        poll_loop.history_db.open_db = original_open_db
                    if not result.get("panel_changed"):
                        return False, "run_once() reported panel_changed=%r, expected True" % (result.get("panel_changed"),)
                    if not os.path.exists(os.path.join(hist_fail_dir, "panel.bin")):
                        return False, "panel.bin was not written when history_db.open_db raised"
                    return True, ""
                finally:
                    shutil.rmtree(hist_fail_dir, ignore_errors=True)
            check(
                "a history.db failure (open_db raising) is caught and logged without failing the cycle or leaving panel.bin unwritten",
                _history_write_failure_does_not_fail_cycle,
            )

            # 26. device_config.json is byte-identical before and after a
            # poll cycle - poll_loop.py reads it and never writes it.
            def _poll_loop_never_writes_device_config():
                cfg_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-cfgwrite-")
                try:
                    device_config.save_device_config(cfg_dir, theme="sky", tracked_runway="3")
                    path = device_config.device_config_path(cfg_dir)
                    with open(path, "rb") as fh:
                        before = fh.read()
                    poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=cfg_dir, geofence=GEOFENCE_PATH)
                    with open(path, "rb") as fh:
                        after = fh.read()
                    if before != after:
                        return False, "device_config.json changed after a poll cycle - poll_loop.py must only ever read it"
                    return True, ""
                finally:
                    shutil.rmtree(cfg_dir, ignore_errors=True)
            check(
                "device_config.json is byte-identical before and after a poll cycle - poll_loop.py reads it and never writes it",
                _poll_loop_never_writes_device_config,
            )

            # 27. A corrupted device_config.json (invalid JSON) still
            # yields a completed cycle using the documented defaults -
            # load_device_config() is documented never to raise.
            def _corrupted_device_config_falls_back_to_defaults():
                bad_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-badcfg-")
                try:
                    os.makedirs(bad_dir, exist_ok=True)
                    with open(device_config.device_config_path(bad_dir), "w") as fh:
                        fh.write("{not valid json")
                    result = poll_loop.run_once(snapshot=_snapshot("aaaaaa", "FLIGHT1 ", CLIMB), state_dir=bad_dir, geofence=GEOFENCE_PATH)
                    if result.get("theme") != device_config.DEFAULT_THEME_ID:
                        return False, "corrupted device_config.json yielded theme=%r, expected the default %r" % (result.get("theme"), device_config.DEFAULT_THEME_ID)
                    if result.get("tracked_runway") != device_config.DEFAULT_RUNWAY_ID:
                        return False, "corrupted device_config.json yielded tracked_runway=%r, expected the default %r" % (result.get("tracked_runway"), device_config.DEFAULT_RUNWAY_ID)
                    return True, ""
                finally:
                    shutil.rmtree(bad_dir, ignore_errors=True)
            check(
                "a corrupted device_config.json (invalid JSON) still yields a completed cycle using the documented defaults",
                _corrupted_device_config_falls_back_to_defaults,
            )

        finally:
            enrich.default_transport = original_transport

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("poll-loop: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
