"""Thin re-export shim over server/wake.py.

The real arithmetic lives in server/wake.py so server/poll_loop.py can
import it without ever importing anything under companion/ ("the
server never imports the companion"). Every `companion.wake.*` call
site (home_page.py, health_page.py, config_page.py) goes through this
shim rather than a second, companion-local `import server.wake`: two
import paths to one module is how a later reader comes to believe
there are two definitions of "late".
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
