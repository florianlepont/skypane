"""companion/wake.py — thin re-export shim over server/wake.py (D-27,
20-02-PLAN.md).

Moved here in an earlier phase (19-05-PLAN.md); relocated to
server/wake.py this phase so server/poll_loop.py can import the same
arithmetic without ever importing anything under companion/ (D-27's own
"the server never imports the companion" constraint). Every existing
`companion.wake.*` call site (home_page.py, health_page.py,
config_page.py) and every existing pinned test importing
`companion.wake` keeps working unmodified against this shim.

24-03-PLAN.md Task 2 (CFG-43) added `classify_check_in_gap()` and the
`CHECK_IN_*` vocabulary to server/wake.py — deliberately there rather
than in server/history_db.py, whose own docstring declares it a
stdlib-only leaf that must not import `device_config` (which `wake`
does). They join the re-export list below so the web app reaches the
SAME classifier the Frame tile's own thresholds come from, rather than
importing `server.wake` at one call site and this shim at every other:
two import paths to one module is how a later reader comes to believe
there are two definitions of "late".

Quick task 260923-fr4 (battery-empty-screen-before-the-pack-die) adds
`read_battery_critical()` and `BATTERY_CRITICAL_STATE_KEY` to the
re-export list below, for the identical reason: the companion's ctx
builder reads the same BATTERY EMPTY latch `effective_wake_interval_s()`/
`next_wake_status()` now accept as a `battery_critical` keyword, and it
must reach that latch through this one shim rather than a second,
companion-local `import server.wake`.
"""
from server.wake import (  # noqa: F401
    env_sleep_s, effective_wake_interval_s, device_staleness_thresholds,
    next_wake_at_iso, next_wake_status, HOLD_QUIET_HOURS,
    MISSED_WAKES_WARN, MISSED_WAKES_ERROR,
    STALE_WARN_FLOOR_S, STALE_ERROR_FLOOR_S, SLEEP_ENV_VAR,
    classify_check_in_gap,
    CHECK_IN_ON_CADENCE, CHECK_IN_LATE, CHECK_IN_MISSING, CHECK_IN_UNKNOWN,
    read_battery_critical, BATTERY_CRITICAL_STATE_KEY,
)
