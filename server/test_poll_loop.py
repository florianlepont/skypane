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

Since 2026-08-28 (mechanism-C mitigation, see
.planning/debug/resolved/missed-flights-not-displayed.md) it also covers the
BOUNDED-AGE PENDING QUEUE that paces how fast the "current" slot advances:
the server re-renders every 30s but the frame physically cannot redraw
faster than ~90s, so distinct detections are queued rather than overwriting
each other, promoted oldest-first, and discarded once they would be more
than `MAX_STALENESS_S` stale.

WHAT THE CHECKS ARE FOR - three distinct roles, kept explicit so a later
reader cannot mistake one for another and quietly relax it (a distinction
this session's mechanism-B pass established and this pass keeps):

  * REGRESSION checks assert the FIXED behaviour and are proven to FAIL
    against a restored pre-fix implementation. The single seam that restores
    the pre-fix behaviour is `poll_loop.advance_is_due` forced to True:
    with the pacing gate always open, every distinct detection is enqueued
    and popped in the same cycle, the queue never accumulates, and the
    "current" slot advances on every distinct detection - which is exactly
    what the code did before this pass. Checks 10, 12, 13, 15, 18.
  * PRECONDITION checks assert the BUG is genuinely reproducible, so they
    MUST hold against the pre-fix implementation - that is their whole
    point. Check 9. (Same role checks 11/29/32 play in
    server/test_plane_detection.py.)
  * GUARD checks must hold in BOTH directions. If a guard flips, the fix has
    broken something it was supposed to leave alone (checks 1-8, 14, 16, 17)
    or has abandoned a bound it exists to enforce (check 11).

Checks 15/16 and 17/18 are each a deliberate SPLIT of one assertion that
mixed the two roles - persistence (regression) from malformed-input tolerance
(guard), and the field contract (guard) from deferral being legible
(regression). Lumping them together is exactly the blur the mechanism-B pass
split its own check 36/37 to avoid; a guard that also fails pre-fix teaches a
later reader nothing about which half broke.

TIME IS INJECTED, NEVER SLEPT. `poll_loop.now_s()` is a module-level seam
precisely because every pacing and staleness decision is arithmetic over
timestamps persisted in poll_state.json (this script is a systemd oneshot
with no in-process memory, D-P2-02). This harness replaces it with a
dictionary-backed fake clock and steps it explicitly, so a 150-second
staleness window costs no wall-clock time and the outcome is deterministic.

Stdlib-only, plus the module under test (server.poll_loop, which
transitively imports Pillow via server.plane.render) - must be run under
server/.venv's interpreter. Exits 0 only when every check below passes.

NOTE: `run_once()` calls `enrich.resolve_route()` with no injected
transport, so by default it reaches live adsbdb over the network for the
FLIGHT1-4 callsigns checks 1-5 use (this harness is not hermetic on that
axis today - a pre-existing condition, not introduced by this plan). Checks
6-18 below stub `enrich.default_transport` in a try/finally specifically so
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

EXPECTED_CHECK_COUNT = 18

# A fixed, arbitrary epoch base so every timestamp in this harness is a plain
# offset from zero and no assertion depends on the real wall clock.
CLOCK_BASE = 1_700_000_000.0
CLOCK = {"t": CLOCK_BASE}


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

    # Install the fake clock for the WHOLE harness (restored in the outer
    # finally). Checks 1-8 predate display pacing and are about the two-deep
    # history and the prefix registry, not about cadence - so every one of
    # their cycles steps the clock past MIN_ADVANCE_INTERVAL_S first, which
    # keeps their original meaning exactly: a well-spaced distinct detection
    # still shifts immediately. That they pass unchanged under the fix IS the
    # light-traffic no-regression guarantee (verification requirement (c)),
    # restated explicitly and in isolation by check 14.
    _real_now_s = poll_loop.now_s
    poll_loop.now_s = lambda: CLOCK["t"]

    tmpdir = tempfile.mkdtemp(prefix="skypane-poll-loop-history-")
    try:
        # A strong, unambiguous +2400 ft/min climb - clears the D-P2-04
        # deadband on the very first cycle, so confirmed_state is never
        # None here (irrelevant to what this harness tests).
        CLIMB = 2400

        def _tick(seconds):
            CLOCK["t"] += float(seconds)

        def _run(hex_code, callsign, state_dir=None, tick=None):
            """One paced cycle: step the clock past the pacing floor, then
            poll. `tick` defaults to comfortably more than
            MIN_ADVANCE_INTERVAL_S so these cycles model light traffic.
            """
            _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30 if tick is None else tick)
            target = tmpdir if state_dir is None else state_dir
            poll_loop.run_once(snapshot=_snapshot(hex_code, callsign, CLIMB), state_dir=target, geofence=GEOFENCE_PATH)
            return poll_loop.load_poll_state(target)

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
                _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
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
                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
                    poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    state_after_1 = poll_loop.load_poll_state(oz9_dir)
                    reg1 = state_after_1.get("unresolved_prefixes")
                    if not isinstance(reg1, dict) or reg1.get("ZZQ", {}).get("count") != 1:
                        return False, "after cycle 1, unresolved_prefixes = %r, expected ZZQ at count 1" % (reg1,)

                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
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
                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
                    poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    reg_before = poll_loop.load_poll_state(oz9_dir).get("unresolved_prefixes")

                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
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
                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
                    with contextlib.redirect_stdout(buf):
                        poll_loop.run_once(snapshot=_snapshot("111111", "ZZQ1234", CLIMB), state_dir=oz9_dir, geofence=GEOFENCE_PATH)
                    miss_line = [ln for ln in buf.getvalue().splitlines() if ln.startswith("poll_loop: ")][-1]
                    if "unknown_prefix=ZZQ" not in miss_line:
                        return False, "the poll line never names the recorded prefix: %s" % (miss_line,)

                    buf = io.StringIO()
                    _tick(poll_loop.MIN_ADVANCE_INTERVAL_S + 30)
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

        # --- mechanism-C mitigation: the bounded-age pending queue --------
        #
        # Everything below drives run_once() over a scripted timeline of fake
        # seconds. `_drive()` models BOTH cadences that matter and that the
        # bug lives between:
        #   * the SERVER's 30s systemd-timer poll (POLL_INTERVAL_S), and
        #   * the DEVICE's ~90s physical redraw floor
        #     (MIN_ADVANCE_INTERVAL_S), at which it samples the two display
        #     slots - which is the only thing a human ever actually sees.
        # An aircraft that occupies the "current" slot only between two
        # device samples was never on the glass. That, and not anything
        # about poll_state.json's internals, is the user-visible symptom
        # these checks are written against.

        def _drive(detections, until_s, state_dir=None, poll_interval_s=None, draw_interval_s=None):
            """Run one poll every `poll_interval_s` of fake time from t=0 to
            `until_s`, feeding `detections.get(t)` as that poll's selection.

            Returns (cycles, frames) where `cycles` is one dict per poll
            (t, detected, shown, pending, dropped, line) and `frames` is the
            (current, previous) pair the device would have fetched at each
            of its own redraw opportunities.
            """
            poll_interval_s = poll_interval_s or poll_loop.POLL_INTERVAL_S
            draw_interval_s = draw_interval_s or poll_loop.MIN_ADVANCE_INTERVAL_S
            owned = state_dir is None
            state_dir = state_dir or tempfile.mkdtemp(prefix="skypane-poll-loop-cadence-")
            cycles = []
            frames = []
            try:
                for t in range(0, until_s + 1, poll_interval_s):
                    CLOCK["t"] = CLOCK_BASE + t
                    detected = detections.get(t)
                    snapshot = _snapshot(detected, "ZZQ%04d" % (abs(hash(detected)) % 10000), CLIMB) if detected else {"ac": []}
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
            finally:
                if owned:
                    shutil.rmtree(state_dir, ignore_errors=True)

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

        # The bug's own shape, from the diagnosis pass: four distinct
        # aircraft selected on four consecutive 30s polls - i.e. more
        # aircraft than the device can physically draw in that window - then
        # an empty sky. The empty tail matters: a burst followed by silence
        # is the common real shape, and a queue that only drained on
        # detection cycles would strand everything in it.
        BURST = {0: "a1a1a1", 30: "b2b2b2", 60: "c3c3c3", 90: "d4d4d4"}
        BURST_UNTIL = 600

        def _hermetic(fn):
            """Run `fn` with adsbdb stubbed to a hard miss - these checks are
            about cadence, and must not depend on the network or on what
            adsbdb happens to know today.
            """
            original_transport = enrich.default_transport
            enrich.default_transport = lambda callsign, timeout=None: (404, None)
            try:
                return fn()
            finally:
                enrich.default_transport = original_transport

        def _unpaced(fn):
            """Restore the PRE-FIX implementation and run `fn`.

            `advance_is_due` forced True is a faithful restoration, not an
            approximation: with the gate always open a distinct detection is
            enqueued and popped within the same cycle, so the queue never
            accumulates, `pending_flights` stays empty, and the "current"
            slot advances on every distinct detection - exactly the
            pre-2026-08-28 behaviour, which is what let mechanism C overwrite
            flights before the device could fetch them.
            """
            original = poll_loop.advance_is_due
            poll_loop.advance_is_due = lambda *args, **kwargs: True
            try:
                return fn()
            finally:
                poll_loop.advance_is_due = original

        # 9. PRECONDITION - the bug is real and reproducible end to end.
        #    MUST hold against the pre-fix implementation; that is its job.
        def _prefix_burst_loses_an_aircraft_entirely():
            def _body():
                _, frames = _drive(BURST, BURST_UNTIL)
                on_glass = _ever_on_glass(frames)
                missing = set(BURST.values()) - on_glass
                if not missing:
                    return False, (
                        "with pacing disabled (the pre-fix behaviour) every aircraft still reached the glass - "
                        "mechanism C is not reproducible by this timeline, so checks 10+ would prove nothing. "
                        "frames=%r" % (frames,))
                return True, ""
            return _hermetic(lambda: _unpaced(_body))
        check(
            "PRECONDITION: with pacing disabled (pre-fix), a 4-aircraft burst inside one device redraw window "
            "leaves at least one aircraft that NEVER appears on any frame the device could fetch (mechanism C)",
            _prefix_burst_loses_an_aircraft_entirely,
        )

        # 10. REGRESSION (verification requirement (a)) - the same burst,
        #     paced: every aircraft the queue did not explicitly discard
        #     reaches the glass, and in FIFO order.
        def _paced_burst_shows_every_undropped_aircraft():
            def _body():
                cycles, frames = _drive(BURST, BURST_UNTIL)
                on_glass = _ever_on_glass(frames)
                discarded = {h for c in cycles for h in c["dropped"]}
                expected = set(BURST.values()) - discarded
                missing = expected - on_glass
                if missing:
                    return False, "aircraft never reached the glass despite never being discarded: %r (frames=%r)" % (sorted(missing), frames)
                # FIFO: the order aircraft reach the "current" slot must be
                # the order they were first detected.
                order = [h for _, h in _promotions(cycles) if h in BURST.values()]
                detection_order = [BURST[t] for t in sorted(BURST)]
                expected_order = [h for h in detection_order if h in order]
                if order != expected_order:
                    return False, "promotion order %r is not the detection (FIFO) order %r" % (order, expected_order)
                if len(on_glass & set(BURST.values())) < 3:
                    return False, "only %d of the burst's aircraft ever reached the glass, expected at least 3" % len(on_glass & set(BURST.values()))
                return True, ""
            return _hermetic(_body)
        check(
            "REGRESSION (a): a burst of 4 distinct detections inside one ~90s device window puts every "
            "non-discarded aircraft on the glass, in first-detected (FIFO) order",
            _paced_burst_shows_every_undropped_aircraft,
        )

        # 11. GUARD - the staleness bound itself. Must hold in BOTH
        #     directions: pre-fix every promotion is instant (age 0), so this
        #     passing pre-fix is expected and correct. It fails only if the
        #     bound is ever abandoned - which is the failure mode an
        #     unbounded "never drop a flight" queue would have had.
        def _no_promotion_exceeds_the_staleness_bound():
            def _body():
                cycles, _ = _drive(BURST, BURST_UNTIL)
                first_detected = {h: t for t, h in sorted(BURST.items(), reverse=True)}
                for t, hex_code in _promotions(cycles):
                    if hex_code not in first_detected:
                        continue
                    age = t - first_detected[hex_code]
                    if age > poll_loop.MAX_STALENESS_S:
                        return False, "%s reached the current slot %ds after it was first detected, bound is %ds" % (
                            hex_code, age, poll_loop.MAX_STALENESS_S)
                return True, ""
            return _hermetic(_body)
        check(
            "GUARD: no aircraft ever reaches the current display slot more than MAX_STALENESS_S (150s) after it "
            "was first detected - the bound that keeps this a real-time board rather than a backlog",
            _no_promotion_exceeds_the_staleness_bound,
        )

        # A sustained burst: one distinct aircraft per poll for twelve
        # consecutive polls, far faster than the device can consume them and
        # far past the queue's depth cap. This is the pathological case the
        # depth cap exists for.
        SUSTAINED = {i * 30: "h%05d" % i for i in range(12)}
        SUSTAINED_UNTIL = 1200

        # 12. REGRESSION - an entry that has passed the bound by the time its
        #     turn comes is DISCARDED and named on the log line, and the scan
        #     continues to the next still-fresh entry in the SAME cycle
        #     rather than stalling behind it.
        def _expired_entries_are_skipped_not_stalled_behind():
            def _body():
                cycles, _ = _drive(SUSTAINED, SUSTAINED_UNTIL)
                dropping = [c for c in cycles if c["dropped"]]
                if not dropping:
                    return False, "no cycle discarded anything - the staleness bound was never exercised"
                for hexes in (c["dropped"] for c in dropping):
                    for h in hexes:
                        if h not in SUSTAINED.values():
                            return False, "dropped= named %r, which is not one of the detected aircraft" % (h,)
                # The skip-don't-stall property: at least one cycle must both
                # discard an expired entry AND still promote a fresher one.
                shown_before = None
                skipped = False
                for c in cycles:
                    if c["dropped"] and c["shown"] != shown_before and c["shown"] is not None:
                        skipped = True
                    shown_before = c["shown"]
                if not skipped:
                    return False, (
                        "every discard cycle left the current slot unchanged - an expired head entry is stalling "
                        "the queue instead of being skipped past. cycles=%r" % ([(c["t"], c["shown"], c["dropped"]) for c in cycles],))
                # Nothing discarded may ever also have been displayed.
                discarded = {h for c in cycles for h in c["dropped"]}
                displayed = {h for _, h in _promotions(cycles)}
                both = discarded & displayed
                if both:
                    return False, "aircraft both discarded and displayed: %r" % (sorted(both),)
                return True, ""
            return _hermetic(_body)
        check(
            "REGRESSION: a queued aircraft past MAX_STALENESS_S when its turn comes is discarded, named in the "
            "log line's dropped= field, and skipped PAST - a fresher entry behind it is promoted in the same cycle",
            _expired_entries_are_skipped_not_stalled_behind,
        )

        # 13. REGRESSION (verification requirement (b)) - the depth cap.
        def _sustained_burst_caps_the_queue_and_drops_oldest_first():
            def _body():
                cycles, _ = _drive(SUSTAINED, SUSTAINED_UNTIL)
                for c in cycles:
                    if len(c["pending"]) > poll_loop.MAX_PENDING_FLIGHTS:
                        return False, "pending queue reached depth %d at t=%d, cap is %d (queue is growing unboundedly)" % (
                            len(c["pending"]), c["t"], poll_loop.MAX_PENDING_FLIGHTS)
                burst_end = [c for c in cycles if c["t"] == max(SUSTAINED)][0]
                if len(burst_end["pending"]) != poll_loop.MAX_PENDING_FLIGHTS:
                    return False, "at the end of a 12-aircraft burst the queue holds %d entries, expected it saturated at %d: %r" % (
                        len(burst_end["pending"]), poll_loop.MAX_PENDING_FLIGHTS, burst_end["pending"])

                # Oldest-first, asserted PER CYCLE. Comparing the whole run's
                # discards against the final queue would be wrong: two
                # different mechanisms discard here (the depth cap during the
                # burst, then the staleness bound long after it), so a hex
                # dropped late is naturally newer than one still queued
                # earlier. The real invariant is local - whatever a cycle
                # dropped came off the HEAD, so it must be older than
                # everything that cycle left behind.
                detected_at = {h: t for t, h in SUSTAINED.items()}
                for c in cycles:
                    if not c["dropped"] or not c["pending"]:
                        continue
                    newest_dropped = max(detected_at[h] for h in c["dropped"])
                    oldest_kept = min(detected_at[h] for h in c["pending"])
                    if newest_dropped > oldest_kept:
                        return False, (
                            "at t=%d the queue dropped %r (newest first detected t=%d) while keeping %r "
                            "(oldest first detected t=%d) - eviction is not oldest-first"
                            % (c["t"], c["dropped"], newest_dropped, c["pending"], oldest_kept))

                # ...and prove the DEPTH CAP itself fired, not just the
                # staleness bound: a discard while the queue was saturated and
                # no entry could yet have expired.
                cap_evictions = [
                    c for c in cycles
                    if c["dropped"] and c["t"] <= max(SUSTAINED)
                    and all(c["t"] - detected_at[h] <= poll_loop.MAX_STALENESS_S for h in c["dropped"])
                ]
                if not cap_evictions:
                    return False, (
                        "no discard happened while every dropped entry was still within the staleness bound - the "
                        "depth cap never fired, so this check is only exercising the TTL. cycles=%r"
                        % ([(c["t"], c["pending"], c["dropped"]) for c in cycles if c["dropped"]],))
                return True, ""
            return _hermetic(_body)
        check(
            "REGRESSION (b): a sustained 12-aircraft burst never grows the pending queue past MAX_PENDING_FLIGHTS "
            "and never raises - it saturates at the cap and discards the OLDEST entries first",
            _sustained_burst_caps_the_queue_and_drops_oldest_first,
        )

        # 14. GUARD (verification requirement (c)) - light traffic is
        #     untouched. Must hold in BOTH directions: if this ever fails
        #     post-fix, the mitigation has started delaying the common case
        #     it was never supposed to touch.
        def _light_traffic_is_identical_to_pre_fix():
            def _body():
                # One distinct aircraft every 120s - comfortably beyond the
                # 90s floor - each re-detected once 30s later, which is the
                # real shape of a runway-3 movement (58-110s corridor dwell
                # against a 30s poll).
                light = {}
                for i, hex_code in enumerate(["e5e5e5", "f6f6f6", "070707", "181818"]):
                    light[i * 120] = hex_code
                    light[i * 120 + 30] = hex_code
                cycles, _ = _drive(light, 600)
                for c in cycles:
                    if c["pending"]:
                        return False, "light traffic queued something at t=%d: %r (the common case must never be delayed)" % (c["t"], c["pending"])
                    if c["dropped"]:
                        return False, "light traffic discarded something at t=%d: %r" % (c["t"], c["dropped"])
                    if c["detected"] is not None and c["shown"] != c["detected"]:
                        return False, "at t=%d the poll detected %s but the current slot holds %s - a well-spaced detection was delayed" % (
                            c["t"], c["detected"], c["shown"])
                # ...and the two-deep shift still happens on the same cycle.
                at_120 = [c for c in cycles if c["t"] == 120][0]
                if at_120["previous"] != "e5e5e5":
                    return False, "the outgoing current aircraft did not shift into previous on the same cycle: %r" % (at_120,)
                return True, ""
            return _hermetic(_body)
        check(
            "GUARD (c): light traffic - one distinct aircraft every 120s - never queues, never discards, and "
            "shifts current->previous on the very same cycle it is detected (byte-identical to pre-fix behaviour)",
            _light_traffic_is_identical_to_pre_fix,
        )

        # 15. REGRESSION - the queue is only worth anything if it survives the
        #     process boundary this script actually crosses on EVERY cycle: it
        #     is a systemd oneshot with no in-process memory (D-P2-02), so an
        #     unpersisted enqueue would silently disable the whole mitigation
        #     while every unit test that stayed inside one process still
        #     passed.
        def _queue_survives_the_process_boundary():
            def _body():
                persist_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-persist-")
                try:
                    CLOCK["t"] = CLOCK_BASE
                    poll_loop.run_once(snapshot=_snapshot("aa11aa", "ZZQ0001", CLIMB), state_dir=persist_dir, geofence=GEOFENCE_PATH)
                    CLOCK["t"] = CLOCK_BASE + 30
                    poll_loop.run_once(snapshot=_snapshot("bb22bb", "ZZQ0002", CLIMB), state_dir=persist_dir, geofence=GEOFENCE_PATH)

                    # Read back from DISK - the only assertion in this harness
                    # that proves the queue crosses the oneshot's boundary.
                    on_disk = poll_loop.load_poll_state(persist_dir)
                    queued = poll_loop.normalise_pending(on_disk.get("pending_flights"))
                    if [e["flight"].get("hex") for e in queued] != ["bb22bb"]:
                        return False, "pending_flights on disk is %r, expected the deferred bb22bb" % (on_disk.get("pending_flights"),)
                    if poll_loop._as_timestamp(on_disk.get("last_advance_at")) != CLOCK_BASE:
                        return False, "last_advance_at on disk is %r, expected the first cycle's timestamp" % (on_disk.get("last_advance_at"),)
                    if on_disk.get("last_flight", {}).get("hex") != "aa11aa":
                        return False, "the deferred aircraft was displayed anyway: %r" % (on_disk.get("last_flight"),)
                    return True, ""
                finally:
                    shutil.rmtree(persist_dir, ignore_errors=True)
            return _hermetic(_body)
        check(
            "REGRESSION: a deferred detection and its last_advance_at timestamp are written to poll_state.json "
            "and read back from disk by the next run_once() - the queue survives the systemd oneshot boundary (D-P2-02)",
            _queue_survives_the_process_boundary,
        )

        # 16. GUARD - a malformed state file must degrade to an empty queue,
        #     never crash-loop the timer. Holds in BOTH directions: the
        #     normalisation runs before the pacing gate either way. This is
        #     load_poll_state()'s own "unreadable -> empty state, never a
        #     crash" discipline extended to the two new keys.
        def _malformed_queue_state_degrades_instead_of_raising():
            def _body():
                persist_dir = tempfile.mkdtemp(prefix="skypane-poll-loop-garbage-")
                try:
                    CLOCK["t"] = CLOCK_BASE
                    poll_loop.run_once(snapshot=_snapshot("aa11aa", "ZZQ0001", CLIMB), state_dir=persist_dir, geofence=GEOFENCE_PATH)
                    on_disk = poll_loop.load_poll_state(persist_dir)
                    # Hand-corrupt every field the queue reads - a non-list,
                    # non-dict entries, a missing flight, an unusable
                    # first_seen, a non-numeric timestamp.
                    on_disk["pending_flights"] = [{"nope": 1}, "garbage", {"flight": {"hex": "x"}, "first_seen": "soon"}, 7]
                    on_disk["last_advance_at"] = "half past four"
                    poll_loop.save_poll_state(persist_dir, on_disk)

                    CLOCK["t"] = CLOCK_BASE + 60
                    poll_loop.run_once(snapshot=_snapshot("cc33cc", "ZZQ0003", CLIMB), state_dir=persist_dir, geofence=GEOFENCE_PATH)
                    recovered = poll_loop.load_poll_state(persist_dir)
                    if poll_loop.normalise_pending(recovered.get("pending_flights")):
                        return False, "malformed entries survived normalisation: %r" % (recovered.get("pending_flights"),)
                    if recovered.get("last_flight", {}).get("hex") not in ("aa11aa", "cc33cc"):
                        return False, "the cycle after a corrupt state file left an unexpected display slot: %r" % (recovered.get("last_flight"),)
                    if poll_loop.normalise_pending("not even a list") != [] or poll_loop._as_timestamp(True) is not None:
                        return False, "normalise_pending()/_as_timestamp() do not degrade on hostile input"
                    return True, ""
                finally:
                    shutil.rmtree(persist_dir, ignore_errors=True)
            return _hermetic(_body)
        check(
            "GUARD: a malformed pending_flights / last_advance_at in poll_state.json degrades to an empty queue "
            "and completes the cycle, never raising (load_poll_state()'s never-a-crash discipline, D-P2-02)",
            _malformed_queue_state_degrades_instead_of_raising,
        )

        # 17. GUARD - the log-line contract. Every pre-existing field must
        #     still be there (the triage runbook greps them) and the three new
        #     pacing fields must be present on EVERY line, not only on
        #     interesting ones. Holds in both directions.
        def _log_line_contract_is_intact():
            def _body():
                cycles, _ = _drive(BURST, 200)
                for c in cycles:
                    for field in ("hex=", "callsign=", "aircraft_type=", "corroborated=", "altitude_ft=",
                                  "confirmed_state=", "render_state=", "state_source=", "route_source=",
                                  "unknown_prefix=", "shown=", "pending=", "dropped=", "panel_changed="):
                        if field not in c["line"]:
                            return False, "log field %s missing at t=%d: %s" % (field, c["t"], c["line"])
                return True, ""
            return _hermetic(_body)
        check(
            "GUARD: every poll line still carries all eleven pre-existing fields and additionally shown=, "
            "pending= and dropped= - on every cycle, not only on interesting ones",
            _log_line_contract_is_intact,
        )

        # 18. REGRESSION - the deferral is actually LEGIBLE. Mechanism C went
        #     undiagnosed as long as it did because it was invisible in this
        #     server's own logs (diagnosis pass, observability audit). `hex=`
        #     deliberately still means THIS CYCLE'S DETECTION so the existing
        #     triage recipes keep working; `shown=` is what names the display.
        #     Split out of check 17 on purpose - lumping "the fields exist"
        #     (a guard) together with "a deferral is distinguishable" (a
        #     regression) is exactly the blur the mechanism-B pass split
        #     check 36/37 to avoid.
        def _a_deferred_cycle_is_distinguishable_in_the_log():
            def _body():
                cycles, _ = _drive(BURST, 200)
                deferring = [c for c in cycles if c["detected"] and c["shown"] != c["detected"]]
                if not deferring:
                    return False, "no cycle in the burst deferred a detection - a distinct new aircraft was displayed immediately"
                c = deferring[0]
                if "hex=%s" % c["detected"] not in c["line"]:
                    return False, "hex= no longer names THIS CYCLE'S DETECTION (%s): %s" % (c["detected"], c["line"])
                if "shown=%s" % c["shown"] not in c["line"]:
                    return False, "shown= does not name the aircraft in the current slot (%s): %s" % (c["shown"], c["line"])
                if "pending=%d" % len(c["pending"]) not in c["line"] or "pending=0" in c["line"]:
                    return False, "pending= does not name the real queue depth (%d): %s" % (len(c["pending"]), c["line"])
                if "panel_changed=False" not in c["line"]:
                    return False, "a deferred cycle rewrote the panel - the whole point is that it must not: %s" % (c["line"],)
                return True, ""
            return _hermetic(_body)
        check(
            "REGRESSION: a cycle that defers a detection is legible in the log - hex= names the detection, shown= "
            "names the different aircraft on the panel, pending= is non-zero, and panel_changed=False",
            _a_deferred_cycle_is_distinguishable_in_the_log,
        )

    finally:
        poll_loop.now_s = _real_now_s
        shutil.rmtree(tmpdir, ignore_errors=True)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("poll-loop: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
