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

Position mode (aircraft around a location) is the one place the deadband
is surfaced as its own state: `display_state()` reports STATE_OVERHEAD for
a level aircraft. The held state that is persisted never holds it.

Heading-based inference is deliberately not implemented: vertical rate
alone cleanly separated every real sampled track, and an unvalidated
second signal would add a failure mode without adding evidence.

Mirrors adsb-test/query_aggregator.py's discipline: explicit
isinstance() checks, skip/hold rather than raise. Booleans are rejected
explicitly before the numeric comparison, since Python treats bool as an
int subclass.
"""
from __future__ import annotations

CLIMB_THRESHOLD_FPM = 200
DESCEND_THRESHOLD_FPM = -200

STATE_DEPARTING = "departing"
STATE_ARRIVING = "arriving"
STATE_OVERHEAD = "overhead"


def infer_runway_config(vertical_rate_fpm: object, last_confirmed_state: object) -> object:
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


def infer_from_flight(flight: object, last_confirmed_state: object) -> object:
    """Delegate to infer_runway_config() using `flight["vertical_rate_fpm"]`,
    so poll_loop never has to reach into raw aggregator fields itself.
    """
    vertical_rate_fpm = None
    if isinstance(flight, dict):
        vertical_rate_fpm = flight.get("vertical_rate_fpm")
    return infer_runway_config(vertical_rate_fpm, last_confirmed_state)


def display_state(flight: object, held_state: object, position_mode: bool) -> object:
    """The state to draw: STATE_OVERHEAD for a level aircraft in position
    mode, otherwise `held_state` unchanged.

    Level means a numeric (non-bool) vertical rate strictly inside the
    deadband. A missing, boolean or non-numeric rate, and NaN, hold
    `held_state`. Never raises.
    """
    if not position_mode or not isinstance(flight, dict):
        return held_state
    rate = flight.get("vertical_rate_fpm")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        return held_state
    if DESCEND_THRESHOLD_FPM < rate < CLIMB_THRESHOLD_FPM:
        return STATE_OVERHEAD
    return held_state
