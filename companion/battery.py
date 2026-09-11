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
"""

# A rough state-of-charge estimate for a single-cell LiPo: 4.2V full,
# 3.3V empty, linear in between. It is an estimate, and labelled as one
# ("≈") — the frame's own low-battery warning still uses the exact
# millivolt thresholds in server/poll_loop.py.
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300


def battery_percent(mv):
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric or
    non-positive reading. Never raises."""
    try:
        value = float(mv)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    ratio = (value - BATTERY_EMPTY_MV) / float(BATTERY_FULL_MV - BATTERY_EMPTY_MV)
    return int(round(max(0.0, min(1.0, ratio)) * 100))
