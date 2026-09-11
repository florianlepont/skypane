"""companion/wake.py — thin re-export shim over server/wake.py (D-27,
20-02-PLAN.md).

Moved here in an earlier phase (19-05-PLAN.md); relocated to
server/wake.py this phase so server/poll_loop.py can import the same
arithmetic without ever importing anything under companion/ (D-27's own
"the server never imports the companion" constraint). Every existing
`companion.wake.*` call site (home_page.py, health_page.py,
config_page.py) and every existing pinned test importing
`companion.wake` keeps working unmodified against this shim.
"""
from server.wake import (  # noqa: F401
    env_sleep_s, effective_wake_interval_s, device_staleness_thresholds,
    next_wake_at_iso, MISSED_WAKES_WARN, MISSED_WAKES_ERROR,
    STALE_WARN_FLOOR_S, STALE_ERROR_FLOOR_S, SLEEP_ENV_VAR,
)
