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
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 8


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

        # 5. render.render_panel() was actually called with the shifted
        # previous_flight/previous_route/previous_state (not just recorded
        # in poll_state.json but plumbed through to the render call) - spy
        # on render.render_panel via the module poll_loop already imported.
        def _previous_flight_is_plumbed_into_render_panel():
            import server.plane.render as render

            captured = {}
            original = render.render_panel

            def _spy(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None, **kwargs):
                # **kwargs (plan 06-10): forward-compatible with run_once()'s
                # new theme_id/runway_id/source_fault keyword arguments -
                # this check only cares about previous_flight/previous_state,
                # so it passes anything else straight through unexamined.
                captured["previous_flight"] = previous_flight
                captured["previous_state"] = previous_state
                return original(flight, state, route=route, previous_flight=previous_flight, previous_route=previous_route, previous_state=previous_state, **kwargs)

            poll_loop.render.render_panel = _spy
            try:
                poll_loop.run_once(snapshot=_snapshot("dddddd", "FLIGHT4 ", CLIMB), state_dir=tmpdir, geofence=GEOFENCE_PATH)
            finally:
                poll_loop.render.render_panel = original

            if captured.get("previous_flight", {}).get("hex") != "cccccc":
                return False, "render_panel() was called with previous_flight=%r, expected hex=cccccc" % (captured.get("previous_flight"),)
            return True, ""
        check("render.render_panel() is actually called with the shifted previous_flight (not just recorded in poll_state.json)", _previous_flight_is_plumbed_into_render_panel)

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

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("poll-loop: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
