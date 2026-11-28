#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Runway-configuration inference: is the aircraft using runway 3 right
now departing or arriving?

Inferred from the ADS-B vertical-rate field via a **deadband**, not a
zero crossing: >= +200 ft/min climbs ("departing"), <= -200 ft/min
descends ("arriving"), anything between - or a missing/non-numeric
reading - **holds the last confirmed state**. An aircraft with no state to
hold falls back to its altitude trend (see `altitude_trend_state()`).

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

# Altitude change, between the first and the latest sighting of one aircraft,
# that reads as a climb or a descent when its vertical rate gives no direction.
# Reported altitudes step by 25 ft, so this is several steps clear of noise.
ALTITUDE_TREND_FT = 100

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


def _number(value: object) -> float | None:
    """`value` as a float when it is a real (non-bool) number, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def altitude_trend_state(flight: object) -> object:
    """STATE_ARRIVING or STATE_DEPARTING from how far the aircraft's altitude
    moved since it was first tracked (`altitude_ref_ft`), or None when it
    moved less than ALTITUDE_TREND_FT or either altitude is unreadable.
    """
    if not isinstance(flight, dict):
        return None
    altitude = _number(flight.get("altitude_ft"))
    reference = _number(flight.get("altitude_ref_ft"))
    if altitude is None or reference is None:
        return None
    change = altitude - reference
    if change >= ALTITUDE_TREND_FT:
        return STATE_DEPARTING
    if change <= -ALTITUDE_TREND_FT:
        return STATE_ARRIVING
    return None


def infer_from_flight(flight: object, last_confirmed_state: object) -> object:
    """Delegate to infer_runway_config() using `flight["vertical_rate_fpm"]`,
    so poll_loop never has to reach into raw aggregator fields itself.

    A vertical rate outside the deadband, or a held state, decides as before.
    Only when neither exists does the altitude trend (altitude_trend_state())
    give the direction, so an aircraft without a usable vertical rate is not
    left without a state.
    """
    vertical_rate_fpm = None
    if isinstance(flight, dict):
        vertical_rate_fpm = flight.get("vertical_rate_fpm")
        # An aircraft on the pavement that was just arriving is on its landing
        # roll-out: a small positive vertical rate there is noise, not a climb.
        if flight.get("on_ground") is True and last_confirmed_state == STATE_ARRIVING:
            return STATE_ARRIVING
    state = infer_runway_config(vertical_rate_fpm, last_confirmed_state)
    if state is not None:
        # A climb rate that would turn a held arrival into a departure is not
        # believed when the altitude since the first sighting says it is
        # still descending: a bad barometric rate sample near the ground
        # would otherwise turn a landing into a departure.
        if (last_confirmed_state == STATE_ARRIVING and state == STATE_DEPARTING
                and altitude_trend_state(flight) == STATE_ARRIVING):
            return STATE_ARRIVING
        return state
    return altitude_trend_state(flight)


def awaits_state(flight: object, position_mode: bool) -> bool:
    """True for an aircraft that has no direction to show yet.

    A different aircraft starts without a held state, and its vertical rate
    can sit inside the deadband (a landing roll-out, a take-off roll, the
    flare) or be missing. Until its altitude trend gives a direction there is
    nothing correct to draw: the previous aircraft's state would be wrong for
    one of the two, and the empty screen hides a detected aircraft.
    """
    return display_state(flight, infer_from_flight(flight, None), position_mode) is None


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
