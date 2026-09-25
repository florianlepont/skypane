"""The effective wake interval and derived device-staleness thresholds,
shared across the server and companion app.

Leaf module under `server/`: may import server.device_config, never
companion/ (whose own wake module re-exports this one instead).
"""
import json
import os
from datetime import datetime, timedelta, timezone

from server import device_config

SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

# The BATTERY EMPTY latch's key in poll_state.json - lives in this leaf
# module so every writer and reader across the codebase can share it
# without importing poll_loop.py itself.
BATTERY_CRITICAL_STATE_KEY = "battery_critical_active"

# Warn after this many missed wakes, error after this many, each
# multiplier applied to the wake interval and then floored below.
MISSED_WAKES_WARN = 3
MISSED_WAKES_ERROR = 12

# Floors so a very short cadence doesn't warn/error too fast - a 30s
# cadence would otherwise warn after 90s, which one dropped Wi-Fi
# association would trip constantly.
STALE_WARN_FLOOR_S = 300
STALE_ERROR_FLOOR_S = 1200


def env_sleep_s():
    """The deployed SKYPANE_SLEEP_S as a positive int, or None if unset/
    invalid. Read fresh on every call, never cached. Deliberately
    unclamped by device_config's [WAKE_INTERVAL_MIN_S,
    WAKE_INTERVAL_MAX_S]: the shipped SKYPANE_SLEEP_S=30 is genuinely
    below that floor and is the device's real cadence.
    """
    raw = os.environ.get(SLEEP_ENV_VAR)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def read_battery_critical(state_dir):
    """True only when poll_state.json's BATTERY_CRITICAL_STATE_KEY is
    literally `True`; any failure degrades to False, never raises -
    fail-open, since a wrongly-returned False costs a few extra wakes,
    never a missed BATTERY EMPTY render.
    """
    try:
        with open(os.path.join(state_dir, "poll_state.json")) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return data.get(BATTERY_CRITICAL_STATE_KEY) is True


def effective_wake_interval_s(device_cfg, battery_critical=False):
    """The wake interval in seconds actually governing this device now, or
    None when undetermined. `device_cfg` may be None or a partial dict;
    never raises.

    Precedence: `battery_critical` (parked cadence, overrides even the
    operator's own display toggle) > `display_enabled=False` (screen-off
    cadence) > `device_cfg["wake_interval_s"]` (positive int) >
    `env_sleep_s()` > None. `battery_critical` defaults False so
    pre-existing callers are unaffected.
    """
    if device_cfg is None:
        device_cfg = {}
    if battery_critical is True:
        return device_config.BATTERY_CRITICAL_SLEEP_S
    if device_cfg.get("display_enabled") is False:
        return device_config.DISPLAY_OFF_SLEEP_S
    wake_interval_s = device_cfg.get("wake_interval_s")
    if (
        isinstance(wake_interval_s, int)
        and not isinstance(wake_interval_s, bool)
        and wake_interval_s > 0
    ):
        return wake_interval_s
    return env_sleep_s()


def device_staleness_thresholds(wake_interval_s):
    """The `(warn_s, error_s)` pair for the Device tile: warn after
    MISSED_WAKES_WARN missed wakes, error after MISSED_WAKES_ERROR, each
    floored at STALE_WARN_FLOOR_S/STALE_ERROR_FLOOR_S. A non-positive or
    non-int `wake_interval_s` (including None) degrades to the bare
    floors.
    """
    if (
        not isinstance(wake_interval_s, int)
        or isinstance(wake_interval_s, bool)
        or wake_interval_s <= 0
    ):
        return (STALE_WARN_FLOOR_S, STALE_ERROR_FLOOR_S)
    warn_s = max(MISSED_WAKES_WARN * wake_interval_s, STALE_WARN_FLOOR_S)
    error_s = max(MISSED_WAKES_ERROR * wake_interval_s, STALE_ERROR_FLOOR_S)
    return (warn_s, error_s)


# Verdict vocabulary for one observed check-in gap - a statement about the
# check-in record, never a claim about device conduct: a missed log
# rotation looks identical to a missed wake (history_db.check_in_gaps()).
CHECK_IN_ON_CADENCE = "on_cadence"
CHECK_IN_LATE = "late"
CHECK_IN_MISSING = "missing"
CHECK_IN_UNKNOWN = "unknown"  # gap_s is None: span not datable


def classify_check_in_gap(gap_s, wake_interval_s):
    """Classify one observed check-in gap as CHECK_IN_ON_CADENCE/_LATE/
    _MISSING/_UNKNOWN, via device_staleness_thresholds() so a grid drawn
    from these verdicts can never disagree with the Device tile. Boundary:
    below `warn_s` is on-cadence, `warn_s` itself is late, `error_s`
    itself is missing.

    `wake_interval_s` is a caller-supplied argument, not read from
    device_config, since the cadence in force at a historical gap is
    unrecoverable. `gap_s` that is None, a bool, non-numeric, negative, or
    NaN is CHECK_IN_UNKNOWN.
    """
    warn_s, error_s = device_staleness_thresholds(wake_interval_s)
    if (
        not isinstance(gap_s, (int, float))
        or isinstance(gap_s, bool)
        or gap_s != gap_s  # NaN is the only value unequal to itself
        or gap_s < 0
    ):
        return CHECK_IN_UNKNOWN
    if gap_s >= error_s:
        return CHECK_IN_MISSING
    if gap_s >= warn_s:
        return CHECK_IN_LATE
    return CHECK_IN_ON_CADENCE


# Hold-reason vocabulary; `None` means not held. No separate constant for
# a merely-off screen - that's absorbed into DISPLAY_OFF_SLEEP_S as an
# ordinary (if longer) cadence.
HOLD_QUIET_HOURS = "quiet_hours"


def next_wake_status(last_checkin_ts, device_cfg, battery_critical=False):
    """The `(next_wake_iso, effective_interval_s, hold_reason)` triple
    every "when will the frame next wake" consumer reads, so callers can
    never disagree. Returns (None, None, None) when `last_checkin_ts` is
    falsy/unparsable or `effective_wake_interval_s()` returns None.

    Composes two tested primitives rather than new window arithmetic:
    `device_config.quiet_hours_status()` called twice - at check-in, and
    at check-in + base interval - to catch a window already open or
    opening before the next candidate wake. Either hit sets `hold_reason`
    and can only lengthen `effective_interval_s`, never shorten it.
    """
    if not last_checkin_ts:
        return None, None, None
    try:
        parsed = datetime.fromisoformat(last_checkin_ts)
    except (TypeError, ValueError):
        return None, None, None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    interval_s = effective_wake_interval_s(device_cfg, battery_critical=battery_critical)
    if interval_s is None:
        return None, None, None

    checkin_epoch = parsed.timestamp()
    remaining_at_checkin, _end_hm = device_config.quiet_hours_status(
        device_cfg, checkin_epoch)
    remaining_at_candidate, _end_hm2 = device_config.quiet_hours_status(
        device_cfg, checkin_epoch + interval_s)

    hold_reason = None
    effective_interval_s = interval_s
    if remaining_at_checkin is not None:
        hold_reason = HOLD_QUIET_HOURS
        effective_interval_s = max(effective_interval_s, remaining_at_checkin)
    if remaining_at_candidate is not None:
        hold_reason = HOLD_QUIET_HOURS
        effective_interval_s = max(
            effective_interval_s, interval_s + remaining_at_candidate)

    next_wake_iso = (parsed + timedelta(seconds=effective_interval_s)).isoformat()
    return next_wake_iso, effective_interval_s, hold_reason


def next_wake_at_iso(last_checkin_ts, device_cfg, battery_critical=False):
    """The next wake time as an ISO-8601 UTC string, or None. A thin
    wrapper over `next_wake_status()`'s first element - never formatted,
    since this module has no view dependency; callers format for display.
    """
    return next_wake_status(last_checkin_ts, device_cfg, battery_critical=battery_critical)[0]
