#!/usr/bin/env python3
"""D-03 runway-configuration inference: is the aircraft using runway 3
right now departing or arriving?

This implements D-03 (02-CONTEXT.md/02-RESEARCH.md): departure vs. arrival
is inferred directly from the ADS-B vertical-rate field already collected -
no external NOTAM or runway-configuration feed. D-P2-04 (locked,
02-02-PLAN.md) resolves the exact thresholds as a **deadband**, not a zero
crossing: >= +200 ft/min is a climbing signal ("departing"), <= -200 ft/min
is a descending signal ("arriving"), and anything strictly between - or a
missing/non-numeric reading - **holds the last confirmed state** rather
than re-inferring from a single ambiguous sample.

Evidence and an explicit asymmetry warning (A-02-02-01, 02-02-PLAN.md):
`DESCEND_THRESHOLD_FPM` is backed by real captured runway-3 arrival data -
server/fixtures/track_arrival_440cb1.json (the real EJU84YF landing) shows
-640 ft/min followed by two consecutive +48 ft/min readings during the
flare, right before touchdown. Mode-S vertical-rate is quantised in 64
ft/min steps and genuinely goes near zero during a real landing's flare;
the +200 ft/min deadband sits comfortably above that observed +48 ft/min
noise floor and above 3x the quantisation step, so the real flare artefact
never flips the confirmed "arriving" state.

`CLIMB_THRESHOLD_FPM` is **provisional, inferred by symmetry with the
well-evidenced descent side, and has never been checked against a real
climbing runway-3 track** - every one of the 20 real tracked aircraft in
Phase 1's ~92-minute sample was a descending arrival, so runway 3 was
apparently in arrival configuration for the entire sampled window (see
02-RESEARCH.md's "Open Question 2" for the full analysis). Real-world
confirmation of the departure-side threshold happens in plan 02-05's
hardware QA checkpoint (observe at least one real runway-3 departure end to
end), not in this module or its test suite - a green
server/test_runway_config.py proves the deadband arithmetic is correct, not
that the departure threshold is real-world-validated.

Heading-based "toward/away" inference (also named in D-03's original
wording) is deliberately not implemented: vertical rate alone cleanly
separated every real track in Phase 1's sample data, and adding a second,
unvalidated signal would add a failure mode without adding evidence. If
real-world QA in 02-05 shows vertical rate alone is insufficient, heading
is the documented next lever.

Mirrors adsb-test/query_aggregator.py's filter_in_geofence discipline
(T-02-02-01): explicit isinstance() checks, skip/hold rather than raise on
anything unexpected. Booleans are rejected explicitly before the numeric
comparison - Python treats bool as an int subclass (isinstance(True, int)
is True), so an un-guarded bool would silently be read as 0/1 and could
mask a real caller-side type bug.
"""

CLIMB_THRESHOLD_FPM = 200
DESCEND_THRESHOLD_FPM = -200

STATE_DEPARTING = "departing"
STATE_ARRIVING = "arriving"


def infer_runway_config(vertical_rate_fpm, last_confirmed_state):
    """Return the inferred runway configuration for a single vertical-rate
    reading, applying D-P2-04's deadband and hold-last-state rule.

    - Bools are rejected explicitly before the numeric check (see module
      docstring) and hold `last_confirmed_state`.
    - Any other non-int/non-float value (None, a string, a dict, ...) also
      holds `last_confirmed_state` - a missing/malformed reading must never
      raise and must never invent a state.
    - `>= CLIMB_THRESHOLD_FPM` -> STATE_DEPARTING (SYNTHETIC per
      A-02-02-01 - see module docstring; symmetry-derived, not
      real-data-backed).
    - `<= DESCEND_THRESHOLD_FPM` -> STATE_ARRIVING (real-data-backed by
      server/fixtures/track_arrival_440cb1.json).
    - Otherwise (inside the deadband) -> `last_confirmed_state` unchanged,
      which may itself be None if nothing has ever been confirmed yet -
      this is the real EJU84YF flare artefact's case (+48 ft/min holds
      whatever "arriving" was already confirmed).
    """
    if isinstance(vertical_rate_fpm, bool):
        return last_confirmed_state
    if not isinstance(vertical_rate_fpm, (int, float)):
        return last_confirmed_state
    if vertical_rate_fpm >= CLIMB_THRESHOLD_FPM:
        return STATE_DEPARTING
    if vertical_rate_fpm <= DESCEND_THRESHOLD_FPM:
        return STATE_ARRIVING
    return last_confirmed_state


def infer_from_flight(flight, last_confirmed_state):
    """Delegate to infer_runway_config() using the normalised flight dict
    produced by detect.select_runway3_aircraft() (specifically its
    vertical_rate_fpm key), so poll_loop never has to reach into raw
    aggregator fields itself.
    """
    vertical_rate_fpm = None
    if isinstance(flight, dict):
        vertical_rate_fpm = flight.get("vertical_rate_fpm")
    return infer_runway_config(vertical_rate_fpm, last_confirmed_state)
