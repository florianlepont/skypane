#!/usr/bin/env python3
"""Contract harness for server/poll_loop.py's two-deep flight history
(D-25, 03-CONTEXT.md decisions_addendum_2) - the engineering consequence of
the current+previous two-flight poster layout: a genuinely new detection
(different ICAO hex) must shift the old "current" flight down into
"previous" before being overwritten; re-detecting the same aircraft must
not shift anything.

Stdlib-only, plus the module under test (server.poll_loop, which
transitively imports Pillow via server.plane.render) - must be run under
server/.venv's interpreter. Exits 0 only when every check below passes.

Usage:
    server/.venv/bin/python3 server/test_poll_loop.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
GEOFENCE_PATH = os.path.join(REPO_ROOT, "adsb-test", "runway3.json")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 5


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

    tmpdir = tempfile.mkdtemp(prefix="ink-frame-poll-loop-history-")
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

            def _spy(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None):
                captured["previous_flight"] = previous_flight
                captured["previous_state"] = previous_state
                return original(flight, state, route=route, previous_flight=previous_flight, previous_route=previous_route, previous_state=previous_state)

            poll_loop.render.render_panel = _spy
            try:
                poll_loop.run_once(snapshot=_snapshot("dddddd", "FLIGHT4 ", CLIMB), state_dir=tmpdir, geofence=GEOFENCE_PATH)
            finally:
                poll_loop.render.render_panel = original

            if captured.get("previous_flight", {}).get("hex") != "cccccc":
                return False, "render_panel() was called with previous_flight=%r, expected hex=cccccc" % (captured.get("previous_flight"),)
            return True, ""
        check("render.render_panel() is actually called with the shifted previous_flight (not just recorded in poll_state.json)", _previous_flight_is_plumbed_into_render_panel)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("poll-loop: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
