"""The shared battery-percentage estimate for the SkyPane companion
service. Page-independent, stdlib-only, so home_page.py and
health_page.py can share one estimate without importing each other.

The 14-knot discharge curve, its endpoints and the two percentage
functions are the server's shared battery policy
(`server/device_policy.py`), re-exported here rather than redefined:
one curve for the percentage shown on the frame and the percentage
this page prints, so the two can never round to different stories.
`LOW_BATTERY_DISPLAY_MV` and the life-estimate code below are this
module's own, companion-only additions on top of that shared curve.
"""

import datetime

from server.device_policy import (  # noqa: F401
    BATTERY_DISCHARGE_CURVE, BATTERY_FULL_MV, BATTERY_EMPTY_MV,
    battery_fraction, battery_percent,
)


def _curve_mv_at_percent(percent):
    """The millivolt value where BATTERY_DISCHARGE_CURVE reads `percent`,
    by inverting the table `battery_fraction()` walks below.

    Raises ValueError outside 0..100 — an import-time programming error,
    since the only caller is LOW_BATTERY_DISPLAY_MV, evaluated at module
    load, never user input.
    """
    if percent < 0 or percent > 100:
        raise ValueError("percent out of range 0..100: %r" % (percent,))
    for (lower_mv, lower_pct), (upper_mv, upper_pct) in zip(
            BATTERY_DISCHARGE_CURVE, BATTERY_DISCHARGE_CURVE[1:]):
        if upper_pct >= percent:
            mv = lower_mv + (percent - lower_pct) * (upper_mv - lower_mv) / float(
                upper_pct - lower_pct)
            return int(round(mv))
    return BATTERY_DISCHARGE_CURVE[-1][0]


# The COMPANION's own low-battery chart mark — distinct from
# server/device_policy.py's device-side BATTERY_LOW_THRESHOLD_MV (3500,
# raw millivolts, not an estimate). Derived from the curve above via
# `_curve_mv_at_percent()`, so the chart line and the printed "≈ N%"
# can never tell two different stories: 3540 mV at 20%.
LOW_BATTERY_DISPLAY_PERCENT = 20
LOW_BATTERY_DISPLAY_MV = _curve_mv_at_percent(LOW_BATTERY_DISPLAY_PERCENT)


# Named states, not an overloaded None: "no reading at all" must read
# differently from "a reading but no trend yet" or "charged"/"flat".
LIFE_TREND_NO_READING = "no-reading"
LIFE_TREND_NOT_ENOUGH_HISTORY = "not-enough-history"
LIFE_TREND_RISING = "rising"
LIFE_TREND_FLAT = "flat"
LIFE_TREND_FALLING = "falling"

# SPAN_DAYS=2: a LiPo's terminal voltage moves with temperature/load
# independently of charge, so a one-day delta is noise; two days is the
# floor of a claim, not a target. DROP_MV=10: below this a 1 mV/3-day
# drop would divide out to a five-year "lifetime" — a false promise.
LIFE_MIN_OBSERVED_SPAN_DAYS = 2
LIFE_MIN_OBSERVED_DROP_MV = 10


def _life_day_or_none(ts):
    """The calendar day of a row's `ts` as a `date`, or None. Accepts
    both the `"YYYY-MM-DD"` day key and a full timestamp, interchangeably.
    `ts` is unvalidated upstream (a Caddy log field can reach it), so an
    unparseable row forms no point at all rather than a phantom one.
    """
    if not isinstance(ts, str):
        return None
    try:
        return datetime.date.fromisoformat(ts[:10])
    except ValueError:
        return None


def _life_usable_points(rows):
    """`(day, millivolts)` for every row that carries both, newest last.

    Sorted here rather than trusted: `daily_battery_averages()` returns
    newest-first, `recent_device_health()` does not necessarily, and a
    slope computed from a series in the wrong order has the wrong SIGN —
    which would turn a draining battery into a charging one, silently.
    """
    points = []
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        day = _life_day_or_none(row.get("ts"))
        if day is None:
            continue
        mv = row.get("battery_mv")
        if isinstance(mv, bool) or not isinstance(mv, (int, float)):
            continue
        if mv <= 0:
            continue
        points.append((day, float(mv)))
    points.sort(key=lambda point: point[0])
    return points


def _life_cadence_or_none(seconds):
    """A usable wake interval in seconds, or None.

    Explicit `isinstance` checks and an explicit bool exclusion, this
    codebase's standing idiom: `isinstance(True, int)` is true in
    Python, and a cadence of `True` would otherwise become one second.
    A non-finite float is refused too — it reaches a division below.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        return None
    value = float(seconds)
    if value <= 0 or value != value or value in (float("inf"), float("-inf")):
        return None
    # Guarded against a value so large that the ratio below overflows to
    # infinity. The real band this app configures is 60..3600 seconds
    # (server/device_config.py's own bounds, deliberately NOT imported
    # here - see this module's docstring), so anything past a year is
    # not a cadence, it is a typo or an attack.
    if value > 366 * 24 * 3600:
        return None
    return value


def battery_life_estimate(rows, current_wake_interval_s=None,
                          proposed_wake_interval_s=None):
    """What can honestly be said about how long this battery has left.
    `rows` is a daily-average series (`server/history_db.py`'s row
    shape); order doesn't matter. `current_wake_interval_s` is the
    caller-resolved cadence (this module may not import server/wake.py).

    Returns a dict: `trend` (a LIFE_TREND_* name), `latest_mv`,
    `observed_span_days`, `mv_per_day`, `days_remaining` (an int only
    when history supports one), `relative_factor` (proposed/current
    cadence, available even with no history at all — a wake-count
    ratio, never a lifetime multiplier).

    Never assumes a per-wake energy cost (the source discharge run left
    that split unresolved) and never turns a RISING series into a
    number (a charged battery has no honest "days until empty").
    """
    current_s = _life_cadence_or_none(current_wake_interval_s)
    proposed_s = _life_cadence_or_none(proposed_wake_interval_s)
    relative_factor = None
    if current_s is not None and proposed_s is not None:
        relative_factor = proposed_s / current_s

    result = {
        "trend": LIFE_TREND_NO_READING,
        "latest_mv": None,
        "observed_span_days": None,
        "mv_per_day": None,
        "days_remaining": None,
        "relative_factor": relative_factor,
    }

    points = _life_usable_points(rows)
    if not points:
        return result

    newest_day, newest_mv = points[-1]
    result["latest_mv"] = int(round(newest_mv))

    oldest_day, oldest_mv = points[0]
    span_days = (newest_day - oldest_day).days
    result["observed_span_days"] = span_days
    if span_days < LIFE_MIN_OBSERVED_SPAN_DAYS:
        result["trend"] = LIFE_TREND_NOT_ENOUGH_HISTORY
        return result

    mv_per_day = (newest_mv - oldest_mv) / float(span_days)
    result["mv_per_day"] = mv_per_day

    if mv_per_day > 0:
        result["trend"] = LIFE_TREND_RISING
        return result

    drop_mv = oldest_mv - newest_mv
    if drop_mv < LIFE_MIN_OBSERVED_DROP_MV:
        result["trend"] = LIFE_TREND_FLAT
        return result

    result["trend"] = LIFE_TREND_FALLING
    # Projected in state-of-charge space, not by straight-line millivolt
    # extrapolation: charge falls roughly linearly in time even though
    # millivolts do not. Validated against the discharge run: this
    # projection landed at 6.0 days for a window where 6.2 actually
    # elapsed; millivolt extrapolation was off by 2-3x on the same window.
    newest_fraction = battery_fraction(newest_mv)
    oldest_fraction = battery_fraction(oldest_mv)
    if newest_fraction == 0.0:
        result["days_remaining"] = 0
    elif (oldest_fraction - newest_fraction) <= 0:
        # Both readings sit at or above the curve's top knot: no
        # measurable state-of-charge drop to project from, even though
        # millivolts fell. The trend stays FALLING and days_remaining
        # stays None; config_page already renders the unknown sentence
        # for that combination.
        result["days_remaining"] = None
    else:
        soc_drop_per_day = (oldest_fraction - newest_fraction) / span_days
        result["days_remaining"] = int(round(newest_fraction / soc_drop_per_day))
    return result


# --- Estimated "probably charging" ------------------------------------
#
# The frame reports only a battery voltage at each wake: the EE02 board's
# charger drives a status LED and nothing readable by the firmware, so
# "charging" can only be INFERRED from the voltage trend. This is an
# estimate, never a measurement, and every caller must word it that way.
#
# The rule looks at the latest readings counted in WAKES, not seconds, so
# it reads the same at a 60 s and a 3600 s cadence, and fires on any of:
#   plateau  the last 3 readings are all at or above CHARGE_PLATEAU_MV;
#   step     the median of the last 3 readings sits at least
#            CHARGE_STEP_RISE_MV above the median of the 3 before them
#            (the level shift of plugging in);
#   ramp     over the last 12 readings, three blocks of 4 whose medians
#            each rise by CHARGE_RAMP_BLOCK_RISE_MV and together by
#            CHARGE_RAMP_TOTAL_RISE_MV (a constant-current charge).
# step and ramp additionally need the latest reading to be within
# CHARGE_LATEST_TOLERANCE_MV of the highest of the last 3, so an unplug
# (a step DOWN) ends the estimate on the first reading after it.
# Medians, not endpoints: the panel refresh load makes single readings sag
# and recover by up to ~100 mV, which as an endpoint looks like a rise.
#
# Calibration data: one battery, one discharge run (3248 discharge
# readings at about 342 s spacing, hardware/logs/battery-run-server.log)
# and one real unplug (4122 mV on USB, 4038 mV on the first wake after).
# Over every discharge window the plateau rule never fires (highest
# discharge reading 4040 mV against the 4112-4126 mV seen on USB), the
# largest 3-vs-3 median rise is 60 mV (against 75), and the ramp rule
# fires 0 times (the closest windows reach 50 mV total, against 60). Only
# that one real charge/unplug transition exists: the thresholds are
# calibrated on discharge noise plus that documented USB plateau, and the
# charging ramp itself is synthetic. Treat them as an estimate.
CHARGE_LIKELY = "charging-likely"
CHARGE_NOT_CHARGING = "not-charging"
CHARGE_UNKNOWN = "unknown"

CHARGE_MIN_READINGS = 3
CHARGE_PLATEAU_MV = 4090
CHARGE_STEP_WINDOW_WAKES = 6
CHARGE_STEP_RISE_MV = 75
CHARGE_RAMP_WINDOW_WAKES = 12
CHARGE_RAMP_BLOCK_RISE_MV = 8
CHARGE_RAMP_TOTAL_RISE_MV = 60
CHARGE_LATEST_TOLERANCE_MV = 20
# One missed wake is tolerated; a "now" claim older than that shows nothing.
CHARGE_FRESH_WAKES = 2
CHARGE_FRESH_SLACK_S = 60


def _charge_instant_or_none(value):
    """A timezone-aware UTC datetime for an ISO string or a datetime (a
    naive one is taken as UTC, as `history_db.instant_or_none()` does),
    or None. `ts` is unvalidated upstream, so nothing here may raise."""
    if isinstance(value, datetime.datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def _charge_readings(rows):
    """Chronological `(instant, millivolts)` pairs for every usable row.
    Sorted here rather than trusted: `recent_device_health()` returns
    newest-first, and a trend read in the wrong order has the wrong sign,
    which would turn a draining battery into a charging one."""
    readings = []
    for row in rows or ():
        if not isinstance(row, dict):
            continue
        instant = _charge_instant_or_none(row.get("ts"))
        if instant is None:
            continue
        mv = row.get("battery_mv")
        if isinstance(mv, bool) or not isinstance(mv, (int, float)):
            continue
        mv = float(mv)
        if mv != mv or mv in (float("inf"), float("-inf")) or mv <= 0:
            continue
        readings.append((instant, mv))
    readings.sort(key=lambda reading: reading[0])
    return readings


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _charge_trend_says_charging(mvs):
    """Whether chronological millivolt readings `mvs` (at least
    CHARGE_MIN_READINGS) read as a charge, by the rule above."""
    latest = mvs[-3:]
    if min(latest) >= CHARGE_PLATEAU_MV:
        return True
    if mvs[-1] < max(latest) - CHARGE_LATEST_TOLERANCE_MV:
        return False
    if len(mvs) >= CHARGE_STEP_WINDOW_WAKES:
        window = mvs[-CHARGE_STEP_WINDOW_WAKES:]
        if _median(window[3:]) - _median(window[:3]) >= CHARGE_STEP_RISE_MV:
            return True
    if len(mvs) >= CHARGE_RAMP_WINDOW_WAKES:
        window = mvs[-CHARGE_RAMP_WINDOW_WAKES:]
        block = CHARGE_RAMP_WINDOW_WAKES // 3
        first = _median(window[:block])
        middle = _median(window[block:2 * block])
        last = _median(window[2 * block:])
        if (middle - first >= CHARGE_RAMP_BLOCK_RISE_MV
                and last - middle >= CHARGE_RAMP_BLOCK_RISE_MV
                and last - first >= CHARGE_RAMP_TOTAL_RISE_MV):
            return True
    return False


def charging_estimate(rows, now, wake_interval_s):
    """CHARGE_LIKELY, CHARGE_NOT_CHARGING or CHARGE_UNKNOWN for the
    per-wake `device_health` `rows` (`ts` and `battery_mv`, any order).

    `now` is an ISO string or a datetime; `wake_interval_s` is the
    caller-resolved effective cadence (this module may not import
    server/wake.py). UNKNOWN, which callers render as nothing, covers
    every case where no honest claim exists: fewer than
    CHARGE_MIN_READINGS usable rows, a bad `now` or cadence, and a latest
    reading older than 2 x the cadence + 60 s (or stamped in the future),
    so a stale "charging" can never show.
    """
    interval_s = _life_cadence_or_none(wake_interval_s)
    now_instant = _charge_instant_or_none(now)
    if interval_s is None or now_instant is None:
        return CHARGE_UNKNOWN
    readings = _charge_readings(rows)
    if len(readings) < CHARGE_MIN_READINGS:
        return CHARGE_UNKNOWN
    age_s = (now_instant - readings[-1][0]).total_seconds()
    if age_s < -CHARGE_FRESH_SLACK_S or age_s > (
            CHARGE_FRESH_WAKES * interval_s + CHARGE_FRESH_SLACK_S):
        return CHARGE_UNKNOWN
    mvs = [mv for _instant, mv in readings[-CHARGE_RAMP_WINDOW_WAKES:]]
    if _charge_trend_says_charging(mvs):
        return CHARGE_LIKELY
    return CHARGE_NOT_CHARGING
