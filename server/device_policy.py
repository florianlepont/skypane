#!/usr/bin/env python3
"""The single shared home of battery and quiet-hours policy: the battery-low
and BATTERY EMPTY hysteresis pair, the battery discharge curve, the
wake/sleep constants and the quiet-hours window arithmetic, used by the
poll cycle (server/), the always-on device endpoint (stub-server/) and the
companion.

This module imports only the standard library. That is not incidental: it
is the reason the module exists rather than living in server/poll_loop.py
or server/device_config.py. stub-server/byos_server.py is deliberately
dependency-free (no PIL, no requests, nothing from server/'s render/detect
stack) so the always-on device endpoint keeps the smallest possible attack
and failure surface; importing this module must never change that. The
companion imports it too, so its battery gauge and its quiet-hours preview
share one set of numbers with the device-facing code instead of a second,
independently maintained copy.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# --- Battery-low hysteresis ---------------------------------------------
#
# Raw millivolts, never a derived percentage, since no real discharge curve
# existed when these were first set. THRESHOLD_MV=3500 sits with margin
# above hardware/logtools.py's --cutoff-mv 3400; CLEAR_MV=3600 is a 100 mV
# re-arm buffer against flapping.
BATTERY_LOW_THRESHOLD_MV = 3500
BATTERY_LOW_CLEAR_MV = 3600

# BATTERY EMPTY hysteresis, raw millivolts, sourced from a measured
# discharge run (~3500 mV at ~43h remaining, 2960 mV ~17 min before the
# panel froze). CRITICAL_MV=3300 sits below the 3500 mV badge and above
# the 2960 mV failure point; RECOVER_MV=3700 is a wider 400 mV re-arm
# buffer than the badge's, since a false recovery risks dying mid-refresh.
BATTERY_CRITICAL_MV = 3300
BATTERY_CRITICAL_RECOVER_MV = 3700

# The BATTERY EMPTY latch's key in poll_state.json - lives here so every
# writer (this module's own apply_battery_critical_hysteresis(), called
# from server/poll_cycle.py's load_cycle_context()) and every reader
# (server/state_store.py, stub-server/byos_server.py) shares one literal.
BATTERY_CRITICAL_STATE_KEY = "battery_critical_active"


def apply_battery_hysteresis(battery_mv: int | None, was_active: bool) -> bool:
    """Pure function: the battery-low decision, hysteresis between
    BATTERY_LOW_THRESHOLD_MV (3500) and BATTERY_LOW_CLEAR_MV (3600).
    `battery_mv=None` returns `was_active` unchanged. A reading strictly
    between the two constants holds the previous decision either way.
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV


def apply_battery_critical_hysteresis(battery_mv: int | None, was_active: bool) -> bool:
    """Pure function: the BATTERY EMPTY latch decision - the identical
    shape as `apply_battery_hysteresis()` above, applied to the park/hold
    decision, with hysteresis between BATTERY_CRITICAL_MV (3300) and
    BATTERY_CRITICAL_RECOVER_MV (3700).
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_CRITICAL_RECOVER_MV
    return battery_mv <= BATTERY_CRITICAL_MV


def battery_critical_pin_applies(latched: bool, fresh_mv: int | None) -> bool:
    """True when the BATTERY EMPTY sleep pin still applies: the latch is
    set and this poll's own fresh battery reading (`fresh_mv`, e.g. a
    request's X-Battery-Mv) does not already show recovery at or above
    BATTERY_CRITICAL_RECOVER_MV. The latch itself clears up to one cycle
    after the recovering check-in this reading represents, so a plain
    latch read alone would still see the stale `True`; a fresh, already-
    recovered reading anticipates that instead, without writing anything.
    `latched=False` always returns False regardless of `fresh_mv`.
    """
    if not latched:
        return False
    return not (fresh_mv is not None and fresh_mv >= BATTERY_CRITICAL_RECOVER_MV)


# --- Battery discharge curve ---------------------------------------------
#
# A 14-knot piecewise millivolt-to-percent lookup (source:
# hardware/BATTERY-RUN.md's 12.34-day discharge run), replacing a linear
# 4.2V/3.3V estimate that overstated charge. Deliberately not linear
# between the endpoints: flat near the top, a cliff near the bottom - a
# straight line misreads 3500 mV as ~48% when ~15% remained.
BATTERY_DISCHARGE_CURVE: tuple[tuple[int, int], ...] = (
    (2946, 0),
    (3364, 7),
    (3500, 15),
    (3556, 22),
    (3652, 29),
    (3734, 36),
    (3784, 43),
    (3814, 50),
    (3836, 57),
    (3892, 65),
    (3922, 72),
    (3982, 79),
    (4000, 90),
    (4112, 100),
)

# The end knots, indexed rather than typed, so a change to the table above
# can never drift out of sync with the clamp endpoints below.
BATTERY_FULL_MV = BATTERY_DISCHARGE_CURVE[-1][0]
BATTERY_EMPTY_MV = BATTERY_DISCHARGE_CURVE[0][0]


def battery_fraction(mv: object) -> float | None:
    """The clamped 0.0-1.0 state-of-charge fraction for `mv`, read off
    BATTERY_DISCHARGE_CURVE, or None for a non-numeric, non-positive or
    NaN reading (0 or -1 mV is a broken sensor, not a flat battery).
    Never raises. THE computation: `battery_percent()` is just this value
    rounded, so a gauge and its printed percentage can never disagree.
    Exactly 0.0 at/below BATTERY_EMPTY_MV, exactly 1.0 at/above
    BATTERY_FULL_MV, linear between knots otherwise.
    """
    try:
        value = float(mv)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN is the one float that compares unequal to itself.
        return None
    if value <= 0:
        return None
    if value <= BATTERY_EMPTY_MV:
        return 0.0
    if value >= BATTERY_FULL_MV:
        return 1.0
    for (lower_mv, lower_pct), (upper_mv, upper_pct) in zip(
            BATTERY_DISCHARGE_CURVE, BATTERY_DISCHARGE_CURVE[1:]):
        if upper_mv >= value:
            percent = lower_pct + (value - lower_mv) * (upper_pct - lower_pct) / float(
                upper_mv - lower_mv)
            return percent / 100.0
    return 1.0  # unreachable: value < BATTERY_FULL_MV already returned above.


def battery_percent(mv: object) -> int | None:
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric,
    non-positive or NaN reading. Never raises.

    The arithmetic lives in `battery_fraction()` above; this function is
    just its rounding, `int(round(fraction * 100))`.
    """
    fraction = battery_fraction(mv)
    if fraction is None:
        return None
    return int(round(fraction * 100))


# --- Wake / sleep constants -----------------------------------------------
#
# Bounds for the stored wake_interval_s field. 60 mirrors firmware's
# FP_MIN_REFRESH_SPACING_S default (a conservative margin against needless
# redraws, not a vendor minimum - GDEP133C02 specifies none). 3600 is the
# developer-confirmed ceiling.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600

# Fixed off-state check-in cadence while display_enabled is False,
# independent of wake_interval_s.
DISPLAY_OFF_SLEEP_S = 300

# Fixed check-in cadence while BATTERY EMPTY is active - one hour, since
# detection is skipped entirely while parked.
BATTERY_CRITICAL_SLEEP_S = 3600


# --- Quiet hours -----------------------------------------------------------
#
# Anchored with `\Z`, not `$`: `$` also matches before a trailing newline,
# which would let a dirty "07:00\n" reach the panel's body text
# unvalidated.
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")

# Fixed physical location, so the timezone is hardcoded, not
# per-installation.
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

DEFAULT_QUIET_HOURS_START = "23:00"  # One daily recurring window, never per-weekday.
DEFAULT_QUIET_HOURS_END = "07:00"  # One daily recurring window, never per-weekday.


def normalise_quiet_hours_time(value: object, default: str) -> str:
    """`value` unchanged if it matches the `HHMM_RE` shape gate, else
    `default`. Shared by both start/end fields so they can't drift apart
    on validation strictness.
    """
    if isinstance(value, str) and HHMM_RE.match(value):
        return value
    return default


def seconds_until_quiet_hours_end(now_utc: datetime, start_hm: str, end_hm: str) -> int | None:
    """Seconds remaining until the daily [start_hm, end_hm) Europe/Paris
    window's end, or None when `now_utc` falls outside it. Wraps midnight
    when `end_hm <= start_hm`; a zero-width window (`start_hm == end_hm`)
    is never active.

    Arithmetic core only, no validation: `now_utc` must be timezone-aware;
    `start_hm`/`end_hm` must already match `HHMM_RE`.

    Two DST-safety properties: (a) the final subtraction converts to UTC
    first (`end_dt.astimezone(timezone.utc) - now_utc`), since two aware
    datetimes sharing a `tzinfo` subtract by wall-clock numerals only,
    which is wrong by an hour across a DST transition; (b) a boundary
    configured inside the 02:00-03:00 transition hour can resolve up to
    an hour off (PEP 495 `fold=0`, accepted, not engineered around).
    """
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
    start_h, start_m = (int(x) for x in start_hm.split(":"))
    end_h, end_m = (int(x) for x in end_hm.split(":"))
    start_today = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_today = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if (start_h, start_m) <= (end_h, end_m):
        if not (start_today <= local_now < end_today):
            return None
        end_dt = end_today
    else:
        if local_now >= start_today:
            end_dt = end_today + timedelta(days=1)
        elif local_now < end_today:
            end_dt = end_today
        else:
            return None
    return max(0, int((end_dt.astimezone(timezone.utc) - now_utc).total_seconds()))


def quiet_hours_window(config: object) -> tuple[str, str] | None:
    """The effective `(start_hm, end_hm)` quiet-hours window for `config`,
    or None when quiet hours are not enabled (`config` is not a dict, or
    `quiet_hours_enabled` is anything other than the literal `True` - a
    truthy-but-not-bool value like "yes" does not enable it).

    Fallback rule: an invalid stored bound (wrong shape, wrong type, or
    missing) falls back to its own default (DEFAULT_QUIET_HOURS_START /
    DEFAULT_QUIET_HOURS_END), independently for each bound - so a
    corrupted or partially-written config keeps the frame on its usual
    23:00-07:00 night schedule rather than silently disabling quiet hours
    altogether.
    """
    if not isinstance(config, dict) or config.get("quiet_hours_enabled") is not True:
        return None
    start_hm = normalise_quiet_hours_time(config.get("quiet_hours_start"), DEFAULT_QUIET_HOURS_START)
    end_hm = normalise_quiet_hours_time(config.get("quiet_hours_end"), DEFAULT_QUIET_HOURS_END)
    return start_hm, end_hm


def quiet_hours_status(config: object, now_epoch: object) -> tuple[int, str] | tuple[None, None]:
    """`(seconds_remaining, end_hm)`, or `(None, None)` when quiet hours
    aren't enabled or `seconds_until_quiet_hours_end()` returns None.
    `now_epoch` is epoch seconds (float); never raises, even for a
    hostile value.
    """
    try:
        window = quiet_hours_window(config)
        if window is None:
            return None, None
        start_hm, end_hm = window
        now_utc = datetime.fromtimestamp(float(now_epoch), timezone.utc)  # type: ignore[arg-type]
        remaining = seconds_until_quiet_hours_end(now_utc, start_hm, end_hm)
        if remaining is None:
            return None, None
        return remaining, end_hm
    except (TypeError, ValueError, OverflowError, OSError):
        return None, None
