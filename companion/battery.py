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

Deliberately NOT added here: a "battery life remaining" estimate. Phase
25's D18 wants one and it needs a discharge model this project has no
data to justify; inventing one now would be this estimator disagreeing
with itself across two phases.
"""

# A rough state-of-charge estimate for a single-cell LiPo: 4.2V full,
# 3.3V empty, linear in between. It is an estimate, and labelled as one
# ("≈") — the frame's own low-battery warning still uses the exact
# millivolt thresholds in server/poll_loop.py.
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300

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
#   is DERIVED from the estimate above rather than typed: it is exactly
#   the millivolt level at which `battery_percent()` reads
#   LOW_BATTERY_DISPLAY_PERCENT, so the line a chart draws and the "≈ N%"
#   printed beside it can never tell two different stories. At 20% of the
#   3300-4200 span that is 3480 mV.
#
# Unifying the two is a decision nobody has taken, and it is not this
# phase's to take. What IS worth knowing about the relationship: the
# device's 3500 sits just ABOVE this line, so by the time a plotted
# series crosses the companion's mark the frame has already been warning.
#
# The value is also constrained from below by the chart it is drawn on:
# health_page.py's SPARKLINE_Y_MIN_MV is 3000, the fixed floor of the
# plotted range. A threshold below that would draw off-canvas and a
# threshold equal to it would land ON the axis and read as chrome; 3480
# is strictly above it by 480 mV, comfortably inside the canvas.
LOW_BATTERY_DISPLAY_PERCENT = 20
LOW_BATTERY_DISPLAY_MV = BATTERY_EMPTY_MV + int(round(
    LOW_BATTERY_DISPLAY_PERCENT / 100.0 * (BATTERY_FULL_MV - BATTERY_EMPTY_MV)))


def battery_fraction(mv):
    """The clamped 0.0-1.0 state-of-charge fraction for `mv`, or None for
    a non-numeric or non-positive reading. Never raises.

    This is THE computation: `battery_percent()` below is this value
    rounded to an integer percent and nothing else, so a gauge drawn from
    the fraction and a percentage printed beside it are one number in two
    renderings rather than two numbers that happen to agree today.

    The domain it refuses is deliberately identical to
    `battery_percent()`'s — non-numeric OR non-positive — rather than the
    narrower "non-numeric only": a reading of 0 or -1 mV is a broken
    sensor, not a flat battery, and a gauge that drew it as an honest
    empty ring while the text beside it printed nothing would be the two
    disagreeing again.

    Returns exactly 0.0 at BATTERY_EMPTY_MV and exactly 1.0 at
    BATTERY_FULL_MV — both boundaries are asserted, at the boundary.
    """
    try:
        value = float(mv)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    ratio = (value - BATTERY_EMPTY_MV) / float(BATTERY_FULL_MV - BATTERY_EMPTY_MV)
    return max(0.0, min(1.0, ratio))


def battery_percent(mv):
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric or
    non-positive reading. Never raises.

    24-01-PLAN.md Task 1: the arithmetic moved into `battery_fraction()`
    above and this function became its rounding. Every input this
    function already handled returns byte-identically — the twelve-value
    table in 24-01-SUMMARY.md records the before/after — because the
    clamp, the span and the rounding step are the same operations in the
    same order, just split across two names.
    """
    ratio = battery_fraction(mv)
    if ratio is None:
        return None
    return int(round(ratio * 100))
