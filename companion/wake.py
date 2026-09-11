"""companion/wake.py — the effective wake interval and the derived
device-staleness thresholds shared across the companion service
(D-05/A-23, 19-05-PLAN.md; D-13/S-02, a later plan's own second
consumer).

Sits beside auth.py, battery.py, layout.py and screens.py in this same
package — a shared, page-independent module, never living inside the
per-tab pages package itself (that package's own header states the
rule: no page module imports another page module). This module may
import server.device_config for its constants (WAKE_INTERVAL_MIN_S,
WAKE_INTERVAL_MAX_S, DISPLAY_OFF_SLEEP_S) — a module in this package
reaching into server/ for read-only constants is already precedented
elsewhere in this codebase, not a new boundary crossing. It must never
import anything from the pages package, and it must never import the
top-level HTTP handler module (app.py) — app.py is expected to import
this module in a later plan, so the reverse import would be circular.

19-12-PLAN.md Task 3 (D-13/S-02) adds `next_wake_at_iso()`, this
module's second export and the one definition site of the "when will
the frame next wake up" arithmetic Home and Device both display.
Deliberately imports no view/formatting module, even though its
return value is only ever fed to a clock-text formatter by a caller:
this module stays free of any VIEW dependency, matching every other
function here — each page module formats the ISO string itself.

Stdlib-only (os, datetime), plus server.device_config.
"""
import os
from datetime import datetime, timedelta, timezone

from server import device_config

SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

# D-05 (19-CONTEXT.md): warn after this many missed wakes, error after
# this many, each multiplier applied to the device's own effective wake
# interval and then floored (see device_staleness_thresholds() below).
MISSED_WAKES_WARN = 3
MISSED_WAKES_ERROR = 12

# D-05: the floors a very short cadence must never warn/error below — a
# 30s cadence would otherwise warn after 90 seconds (3 * 30), which one
# dropped Wi-Fi association would trip constantly. Fixed at 5/20 minutes
# regardless of how short the configured cadence is.
STALE_WARN_FLOOR_S = 300
STALE_ERROR_FLOOR_S = 1200


def env_sleep_s():
    """The deployed SKYPANE_SLEEP_S as a positive int, or None when
    unset, empty, non-numeric, or not strictly positive. Read via
    `os.environ.get(SLEEP_ENV_VAR)` on every call, never captured at
    import time — matching `auth.configured_password()`'s own per-call
    shape, so a redeployed env file takes effect on the next service
    restart with nothing cached in between.

    Deliberately does NOT apply device_config's own
    [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] clamp the way app.py's
    env_wake_interval_default() does. That clamp exists there for a
    narrow, unrelated reason: a value below WAKE_INTERVAL_MIN_S (60)
    cannot be rendered as a Settings form's own min="60" numeric input
    value without failing HTML5 constraint validation and blocking the
    whole form's submission — a UI-rendering constraint, not a
    statement about what the device's real cadence is. This function
    feeds a staleness *threshold* instead, where the shipped
    SKYPANE_SLEEP_S=30 — below that same 60s floor — IS the device's
    real wake cadence and must be read as such, unclamped, or every
    staleness threshold derived from it would be measured against a
    number the device was never actually configured to use.
    """
    raw = os.environ.get(SLEEP_ENV_VAR)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value


def effective_wake_interval_s(device_cfg):
    """The wake interval, in seconds, actually governing this device's
    cadence right now — or None when it cannot be determined.

    `device_cfg` is server.device_config.load_device_config()'s own
    dict shape, or None, or a partial/degraded dict — this function
    tolerates all three and never raises.

    Precedence:
      1. When `device_cfg.get("display_enabled")` is explicitly
         `False`, the screen-off cadence
         (`device_config.DISPLAY_OFF_SLEEP_S`) is pinned independently
         of `wake_interval_s` (12-CONTEXT.md D-01) — checked first,
         before `wake_interval_s`, because the display-off cadence
         overrides whatever `wake_interval_s` happens to be configured
         to.
      2. Otherwise, `device_cfg.get("wake_interval_s")` when it is a
         positive int.
      3. Otherwise, `env_sleep_s()`.
      4. Otherwise, `None`.

    Every test above is an explicit `isinstance()`/`is None` check,
    never `or` — this codebase's documented idiom for a value with a
    legitimate falsy state (0 is never a valid wake_interval_s, but the
    idiom is followed even so, so a stray 0 can never silently fall
    through to the next branch by merely looking falsy).
    """
    if device_cfg is None:
        device_cfg = {}
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
    """The `(warn_s, error_s)` pair `staleness_status()` consumes for
    the Device tile, derived from the device's own wake cadence
    (D-05/A-23): warn after `MISSED_WAKES_WARN` missed wakes, error
    after `MISSED_WAKES_ERROR`, each floored at
    `STALE_WARN_FLOOR_S`/`STALE_ERROR_FLOOR_S`.

    The floors exist because a 30s cadence would otherwise warn after
    90 seconds (3 * 30) — one dropped Wi-Fi association would trip that
    constantly — so D-05 fixes the floor at 5/20 minutes regardless of
    how short the configured cadence is.

    `wake_interval_s` must be a positive int to use the multiplier
    path; `None` or any non-positive/non-int input degrades to the bare
    floors (`STALE_WARN_FLOOR_S`, `STALE_ERROR_FLOOR_S`) — the same
    thresholds a freshly-provisioned deployment with no
    `wake_interval_s` set at all, and no `SKYPANE_SLEEP_S` deployed
    either, gets today.

    `warn_s < error_s` is guaranteed for every input: `MISSED_WAKES_ERROR`
    is always greater than `MISSED_WAKES_WARN` for any shared positive
    multiplier, and `STALE_WARN_FLOOR_S < STALE_ERROR_FLOOR_S`, so
    neither the multiplier path nor the floor path can ever invert the
    pair.
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


def next_wake_at_iso(last_checkin_ts, device_cfg):
    """The next time the device is expected to wake, as an ISO-8601 UTC
    string — `last_checkin_ts + effective_wake_interval_s(device_cfg)` —
    or `None` when it cannot be determined (D-13/S-02).

    `None` is returned, never raised, for every one of these cases:
      - `last_checkin_ts` is falsy (no check-in recorded yet) or is not
        a string `datetime.fromisoformat()`-equivalent parsing accepts;
      - `effective_wake_interval_s(device_cfg)` itself returns `None`
        (no on-disk `wake_interval_s`, no `SKYPANE_SLEEP_S`, and the
        screen is not off).

    `last_checkin_ts` is parsed with the same naive-value-is-UTC
    convention this codebase's own clock-text formatter documents (it
    matches `history_db.utc_now_iso()`'s own timezone-aware output, but
    a hand-written or legacy naive value must not raise or silently
    misread as local time): a timezone-naive result is stamped UTC
    before the addition, never left ambiguous.

    Returns a plain ISO string, not formatted text — deliberately not
    run through any formatter here, since this module has no view
    dependency (see the module docstring above); each caller formats
    the value itself for display.
    """
    if not last_checkin_ts:
        return None
    try:
        parsed = datetime.fromisoformat(last_checkin_ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    interval_s = effective_wake_interval_s(device_cfg)
    if interval_s is None:
        return None
    return (parsed + timedelta(seconds=interval_s)).isoformat()
