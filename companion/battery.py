"""companion/battery.py — the shared battery-percentage estimate for the
SkyPane companion service (D-01/A-19, 19-01-PLAN.md).

Before this module existed, home_page.py (in the per-tab pages package
this companion service ships) owned `battery_percent()` outright, and
Health's audit finding (A-19) needed the same estimate without either
page module importing the other — the pages package's own documented
boundary is "no page module imports another page module." This module is
the fix: a shared, page-independent home for the estimate, sitting
beside companion/auth.py, companion/layout.py and companion/screens.py,
not inside the pages package itself.

This module is stdlib-only. It must never import from the pages package
and nothing from the server package — its whole purpose is to let
home_page.py and health_page.py share one estimate without either
importing the other, and pulling in a page module or a server module
here would defeat that.

24-01-PLAN.md Task 1 (CFG-39): this module is the phase's ONE home for
the battery estimate, and a source scan in companion/test_companion_app.py
now proves it — no other module under companion/ may define the millivolt
constants or a second percentage function. Phase 24 draws four new
pictures, one of them a battery ring gauge; every one of them takes its
number from here. The extensions this task adds are `battery_fraction()`
(the 0..1 a gauge needs) and `LOW_BATTERY_DISPLAY_MV` (where the chart
draws its low line), both derived from the SAME ratio `battery_percent()`
already returns, so a gauge and its own printed percentage can never
round to different stories.

25-01-PLAN.md Task 3 (CFG-49): the battery-LIFE estimate lands here, and
it lands here for the same reason the percentage did. Phase 24's version
of this paragraph said a life estimate was deliberately NOT added
because "it needs a discharge model this project has no data to
justify". That reasoning was right about the MODEL and wrong about the
conclusion: what it ruled out was an estimate built on an ASSUMED
per-wake energy cost, and `battery_life_estimate()` below is not that.
It reads a slope out of the observed daily-average series and reports a
figure only when that observed history supports one, with a named state
for every case where it does not. No per-wake cost is assumed anywhere
in this file. DEVICE-05's multi-day discharge run completed on
2026-09-14 (hardware/BATTERY-RUN.md) and is BATTERY_DISCHARGE_CURVE's
own source (SEED-006, quick 260923-gaf) — but it measured a single wake
cadence and left the per-wake versus standing-leakage split unresolved,
so this file still assumes no per-wake energy cost.

quick 260923-gaf (SEED-006, D-SEED006): the estimate itself changed from
a linear 4.2V-full/3.3V-empty span to the 14-knot piecewise curve below,
because the linear span measurably overstated charge across most of a
real discharge. See the comment above BATTERY_DISCHARGE_CURVE for the
data and the method.
"""

import datetime

# D-SEED006 (SEED-006, quick 260923-gaf): a 14-knot piecewise
# millivolt-to-percent lookup, replacing the old 4.2V-full/3.3V-empty
# linear estimate. Source: hardware/BATTERY-RUN.md's "## Discharge
# Trend" section, DEVICE-05's single-pack run from 2026-09-02 12:55 UTC
# to 2026-09-14 21:05 UTC (12.340 days) at a constant 300 s poll
# cadence. Percent is the share of that run's total runtime still ahead
# of a given reading — under the run's constant load, remaining runtime
# equals remaining charge, so that share is read straight off the
# timestamps.
#
# Two merges keep the table strictly increasing in millivolts. The
# 4000 mV plateau was logged at both 93% (09-03) and 86% (09-04); those
# collapse into one knot at their midpoint, 90% (rounded from 89.5), so
# the error at the plateau is at most about 4 points either way. The
# tail — 2960 mV at 0.10% and 2946 mV at 0.00%, the device's last-ever
# reading — collapses into the single bottom knot at 2946 mV / 0%. The
# 4122 mV on-charger plateau (BATTERY-RUN.md's Measured Inputs) is not a
# knot; it clamps to 100 along with every reading at or above 4112 mV.
#
# The endpoints were not simply moved to 4112/2946 and left linear in
# between (the rejected alternative, per the user's decision D-SEED006):
# a straight line between those two points reads 3500 mV as about 48%
# when this run shows about 15% remained, because this curve is flat
# near the top and falls off a cliff near the bottom rather than
# draining evenly.
#
# Caveats this table does not smooth over: one pack, one run, one
# ambient temperature, and single logged readings rather than averages.
# This is still an estimate, and every consumer labels it "≈" for that
# reason.
BATTERY_DISCHARGE_CURVE = (
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

# The end knots, indexed rather than typed, so a change to the table
# above can never drift out of sync with the clamp endpoints below.
BATTERY_FULL_MV = BATTERY_DISCHARGE_CURVE[-1][0]
BATTERY_EMPTY_MV = BATTERY_DISCHARGE_CURVE[0][0]


def _curve_mv_at_percent(percent):
    """The millivolt value where BATTERY_DISCHARGE_CURVE reads `percent`,
    by inverting the same table `battery_fraction()` walks below:
    finds the segment whose percent range contains `percent`,
    interpolates millivolts linearly within it, and rounds to the
    nearest millivolt.

    Raises ValueError outside 0..100. That is an import-time
    programming error — the only caller is LOW_BATTERY_DISPLAY_MV below,
    evaluated at module load — never user input reaching this function.
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


# The COMPANION's low-battery DISPLAY threshold — where this app draws a
# line on a chart, never when the frame decides to warn on glass. Those
# are two different numbers for two different jobs and this comment
# exists so nobody unifies them by accident:
#
#   server/poll_loop.py's BATTERY_LOW_THRESHOLD_MV = 3500 (with a
#   BATTERY_LOW_CLEAR_MV = 3600 re-arm) is the DEVICE-side hysteretic
#   decision (DEVICE-04, 05-02): it changes what the frame renders and
#   what a push notification says. It reasons in raw millivolts on
#   purpose (D-02) and it is not an estimate.
#
#   LOW_BATTERY_DISPLAY_MV below is the COMPANION's own charting mark. It
#   is DERIVED from the curve above rather than typed: it is exactly the
#   millivolt level at which `battery_percent()` reads
#   LOW_BATTERY_DISPLAY_PERCENT, computed by inverting
#   BATTERY_DISCHARGE_CURVE through `_curve_mv_at_percent()`, so the line
#   a chart draws and the "≈ N%" printed beside it can never tell two
#   different stories. At 20% of the DEVICE-05 curve that is 3540 mV.
#
# SEED-006 flipped the relationship to the device. The device's 3500 mV
# warning point now reads about 15% on the curve and sits BELOW this
# line, so a plotted series crosses the companion's display mark FIRST —
# about 40 mV earlier, roughly 15 hours at the late-run rate DEVICE-05
# observed (3556 → 3500 mV took about 21 h). Unifying the two thresholds
# is still a decision nobody has taken, and BATTERY_LOW_THRESHOLD_MV /
# BATTERY_LOW_CLEAR_MV are untouched by this file.
#
# The value is also constrained from below by the chart it is drawn on:
# health_page.py's SPARKLINE_Y_MIN_MV is 3000, the fixed floor of the
# plotted range. 3540 sits 540 mV above it, comfortably inside the
# canvas.
LOW_BATTERY_DISPLAY_PERCENT = 20
LOW_BATTERY_DISPLAY_MV = _curve_mv_at_percent(LOW_BATTERY_DISPLAY_PERCENT)


def battery_fraction(mv):
    """The clamped 0.0-1.0 state-of-charge fraction for `mv`, read off
    BATTERY_DISCHARGE_CURVE, or None for a non-numeric, non-positive or
    NaN reading. Never raises.

    This is THE computation: `battery_percent()` below is this value
    rounded to an integer percent and nothing else, so a gauge drawn from
    the fraction and a percentage printed beside it are one number in two
    renderings rather than two numbers that happen to agree today.

    The domain it refuses is deliberately identical to
    `battery_percent()`'s — non-numeric, non-positive OR NaN — rather
    than the narrower "non-numeric only": a reading of 0 or -1 mV is a
    broken sensor, not a flat battery, and NaN (a float that compares
    unequal to itself) is not a number either, whatever bit pattern
    produced it. A gauge that drew any of those as an honest empty ring
    while the text beside it printed nothing would be the two
    disagreeing again.

    Returns exactly 0.0 at or below BATTERY_EMPTY_MV and exactly 1.0 at
    or above BATTERY_FULL_MV — both boundaries are asserted, at the
    boundary. Every interior knot in BATTERY_DISCHARGE_CURVE returns its
    own percent exactly; between knots the fraction is linear in the
    segment whose upper millivolt value is at or above the reading.
    """
    try:
        value = float(mv)
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


def battery_percent(mv):
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric,
    non-positive or NaN reading. Never raises.

    24-01-PLAN.md Task 1: the arithmetic moved into `battery_fraction()`
    above and this function became its rounding. SEED-006 (quick
    260923-gaf) changed the underlying curve `battery_fraction()` reads;
    the rounding step here — `int(round(fraction * 100))` — is unchanged.
    """
    ratio = battery_fraction(mv)
    if ratio is None:
        return None
    return int(round(ratio * 100))


# 25-01-PLAN.md Task 3 (CFG-49) — THE BATTERY-LIFE ESTIMATE.
#
# The four named states a caller must handle, plus the one that carries
# a number. They are NAMES rather than an overloaded None on purpose: a
# caller that cannot tell "we have no battery reading at all" from "we
# have a reading but cannot see a trend yet" prints the wrong sentence,
# and both of those are different again from "the device was charged"
# and "nothing measurable has drained".
LIFE_TREND_NO_READING = "no-reading"
LIFE_TREND_NOT_ENOUGH_HISTORY = "not-enough-history"
LIFE_TREND_RISING = "rising"
LIFE_TREND_FLAT = "flat"
LIFE_TREND_FALLING = "falling"

# How much observed history is needed before a slope means anything.
#
# LIFE_MIN_OBSERVED_SPAN_DAYS = 2: a single day's difference between two
# daily averages is well inside the noise this series carries. The stored
# value is a mean of that day's readings, and a LiPo's terminal voltage
# moves with temperature and with load independently of state of charge,
# so a one-day delta can be several tens of millivolts in either
# direction on a battery that lost nothing at all. Two days is the
# shortest span where a consistent direction is worth reporting, and it
# is the FLOOR of a claim, not a target — more history is strictly
# better and the returned span says how much there actually was.
#
# LIFE_MIN_OBSERVED_DROP_MV = 10: below this the series is reported FLAT
# rather than falling. Without it, a 1 mV drop measured over three days
# divides out to a lifetime of roughly five years, which is a number a
# user would read as a promise. 10 mV is under 1% of the curve's
# 1166 mV span (BATTERY_FULL_MV - BATTERY_EMPTY_MV = 4112 - 2946).
LIFE_MIN_OBSERVED_SPAN_DAYS = 2
LIFE_MIN_OBSERVED_DROP_MV = 10


def _life_day_or_none(ts):
    """The calendar day of a row's `ts` as a `date`, or None.

    Accepts both row contracts this project already produces: the
    `"YYYY-MM-DD"` day key `server/history_db.py`'s
    `daily_battery_averages()` emits, and the full timestamp
    `recent_device_health()`'s rows carry — the two are deliberately
    interchangeable (that function's docstring says so, and it is why
    the key is named `ts` rather than `day`).

    A row whose `ts` does not parse forms no point at all rather than a
    phantom one, which is the same per-row degrade
    `daily_battery_averages()` itself applies. This matters beyond
    tidiness: `ts` in that table is not validated, and
    `tail_caddy_battery_log()` stores whatever string sits in a Caddy
    access-log entry's own `ts` field, so a hostile value can reach it.
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

    `rows` is a daily-average battery series in
    `server/history_db.py`'s own row shape (`ts`, `battery_mv`,
    `reading_count`); order does not matter and neither does whether
    every row carries a reading. `current_wake_interval_s` is the
    cadence in force — a FUNCTION of mutable config that switches when
    the screen is off, so the caller resolves it (through
    `server/wake.py`'s `effective_wake_interval_s()`) and passes it in;
    this module may not import that package.

    Returns a dict, always, for every input including nonsense:

        trend               one of the five LIFE_TREND_* names above
        latest_mv           the newest usable reading, or None
        observed_span_days  how many days the usable series covers,
                            or None
        mv_per_day          the observed slope, negative while
                            draining, or None
        days_remaining      an int, and ONLY when the observed history
                            supports one
        relative_factor     proposed cadence / current cadence, or None

    THREE THINGS THIS FUNCTION WILL NOT DO, each of which is the
    difference between an estimate and a fabrication:

    1. It never assumes a per-wake energy cost. DEVICE-05 has since run
       (hardware/BATTERY-RUN.md) and is the source of
       BATTERY_DISCHARGE_CURVE above, but it measured a single wake
       cadence and left the per-wake versus standing-leakage split
       unresolved, so no per-wake cost is assumed here either. That is
       why `days_remaining` is None in the four non-falling states, and
       in FALLING too whenever both readings sit above the curve's top
       knot with no measurable state-of-charge drop to project, rather
       than a best guess.
    2. It never turns a RISING series into a number. A charged device
       has a positive slope, and projecting the remaining state of
       charge against it yields a negative lifetime (or an infinite one
       at exactly zero). Both are numbers a user would act on. The
       honest answer to "how long until empty" for a battery that is
       filling is not a number.
    3. It never claims more precision than the span it measured. Below
       LIFE_MIN_OBSERVED_SPAN_DAYS the answer is
       LIFE_TREND_NOT_ENOUGH_HISTORY, which is a state the caller
       renders as its own sentence rather than a silent zero.

    `relative_factor` is deliberately separable from all of the above,
    and it is the reason a gauge can say something true on day one: it
    is the ratio of two cadences and nothing else, so it is available
    even when there is no history and no reading at all. Read it
    precisely — it is how many times less often the device will wake,
    NOT a multiplier on the lifetime. Those two would only be the same
    number if every joule this device spends went into waking, which is
    exactly the unmeasured assumption point 1 refuses.
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
    # SEED-006 (quick 260923-gaf): projected in STATE-OF-CHARGE space,
    # not by straight-line millivolt extrapolation to BATTERY_EMPTY_MV.
    # BATTERY_DISCHARGE_CURVE's percent is the share of DEVICE-05's run
    # runtime still ahead, so state of charge falls roughly LINEARLY in
    # time even though millivolts do not (flat top, cliff at the end).
    # Validated against DEVICE-05 itself: from the 3922 mV reading to
    # the 3814 mV reading (a 2.64-day window), this projection says 6.0
    # days remained and 6.2 actually did. Millivolt extrapolation to the
    # curve's bottom knot said about 21 days for the same window, and to
    # the old linear floor about 12.6 — both far outside the true 6.2.
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
