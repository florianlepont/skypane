#!/usr/bin/env python3
"""Runway-configuration inference: is the aircraft using runway 3 right
now departing or arriving?

Inferred from the ADS-B vertical-rate field via a **deadband**, not a
zero crossing: >= +200 ft/min climbs ("departing"), <= -200 ft/min
descends ("arriving"), anything between - or a missing/non-numeric
reading - **holds the last confirmed state**.

Asymmetric evidence: `DESCEND_THRESHOLD_FPM` is backed by a real capture
(server/fixtures/track_arrival_440cb1.json), whose landing flare shows
+48 ft/min noise comfortably inside the deadband, so it never flips a
confirmed "arriving" state. `CLIMB_THRESHOLD_FPM` is **provisional**,
inferred by symmetry and never checked against a real climbing track -
hardware QA confirms it, not this module's test suite.

Heading-based inference is deliberately not implemented: vertical rate
alone cleanly separated every real sampled track, and an unvalidated
second signal would add a failure mode without adding evidence.

Mirrors adsb-test/query_aggregator.py's discipline: explicit
isinstance() checks, skip/hold rather than raise. Booleans are rejected
explicitly before the numeric comparison, since Python treats bool as an
int subclass.
"""

CLIMB_THRESHOLD_FPM = 200
DESCEND_THRESHOLD_FPM = -200

STATE_DEPARTING = "departing"
STATE_ARRIVING = "arriving"


def infer_runway_config(vertical_rate_fpm, last_confirmed_state):
    """Inferred runway configuration for a single vertical-rate reading,
    applying the deadband and hold-last-state rule. A non-numeric or
    boolean reading holds `last_confirmed_state` (never raises, never
    invents a state); `>= CLIMB_THRESHOLD_FPM` -> STATE_DEPARTING;
    `<= DESCEND_THRESHOLD_FPM` -> STATE_ARRIVING; otherwise
    `last_confirmed_state` unchanged (see module docstring for the
    asymmetric evidence behind each threshold).
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
    """Delegate to infer_runway_config() using `flight["vertical_rate_fpm"]`,
    so poll_loop never has to reach into raw aggregator fields itself.
    """
    vertical_rate_fpm = None
    if isinstance(flight, dict):
        vertical_rate_fpm = flight.get("vertical_rate_fpm")
    return infer_runway_config(vertical_rate_fpm, last_confirmed_state)
