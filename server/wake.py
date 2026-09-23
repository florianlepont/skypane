"""server/wake.py — the effective wake interval and the derived
device-staleness thresholds shared across the SkyPane server and web
app (D-05/A-23, 19-05-PLAN.md; D-13/S-02, a later plan's own second
consumer; D-27, 20-02-PLAN.md — moved here from the web app's own
wake module this phase).

D-27 (20-CONTEXT.md): this module lives under `server/` — not the
web-app package — specifically so `server/poll_loop.py` can reuse the
identical thresholds the web app's Health page already displays,
without the server ever importing anything from that other package.
The web app's own wake module is now a thin re-export shim over this
module, kept so every existing call site and every pinned test
importing it keeps working unmodified.

Sits beside server/device_config.py in this same package — a shared,
leaf module. This module may import server.device_config for its
constants (WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S,
DISPLAY_OFF_SLEEP_S). It must never import anything from the web-app
package — that package's own wake module is expected to import THIS
module (the shim direction), so the reverse import would be circular.

19-12-PLAN.md Task 3 (D-13/S-02) added `next_wake_at_iso()`, this
module's second export and the one definition site of the "when will
the frame next wake up" arithmetic Home and Device both display.
Deliberately imports no view/formatting module, even though its
return value is only ever fed to a clock-text formatter by a caller:
this module stays free of any VIEW dependency, matching every other
function here — each page module formats the ISO string itself.

Stdlib-only (os, json, datetime), plus server.device_config.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from server import device_config

SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

# Quick task 260923-fr4 (battery-empty-screen-before-the-pack-die): the
# BATTERY EMPTY latch's key in poll_state.json. Lives here, in this leaf
# module the companion can already import (rather than in poll_loop.py,
# which the companion never imports), so both poll_loop.py (the single
# writer, via apply_battery_critical_hysteresis()) and every reader below -
# this module's own effective_wake_interval_s()/next_wake_status(), plus
# stub-server/byos_server.py's independent read_battery_critical() and the
# companion's own ctx builder - name the same key.
BATTERY_CRITICAL_STATE_KEY = "battery_critical_active"

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


def read_battery_critical(state_dir):
    """Quick task 260923-fr4: True only when
    `<state_dir>/poll_state.json`'s BATTERY_CRITICAL_STATE_KEY is
    literally `True` — every failure (missing file, malformed JSON, a
    non-dict payload, or a value under the key that is anything other
    than the literal boolean `True`) returns False and never raises,
    the identical fail-open shape stub-server/byos_server.py's own
    `read_display_enabled()` already uses for device_config.json.

    server/poll_loop.py is the single writer of poll_state.json — its
    own `apply_battery_critical_hysteresis()` computes the latch exactly
    once per cycle and stores it under this same key — so this is a
    read-only consumer, the same relationship device_config.json already
    has with the companion. Fail-open is safe here specifically because
    the only cost of a wrongly-returned False is a few extra wakes at the
    device's ordinary cadence, never a missed BATTERY EMPTY render, which
    poll_loop's own latch (not this reader) is solely responsible for.
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
    """The wake interval, in seconds, actually governing this device's
    cadence right now — or None when it cannot be determined.

    `device_cfg` is server.device_config.load_device_config()'s own
    dict shape, or None, or a partial/degraded dict — this function
    tolerates all three and never raises.

    Precedence:
      1. When `battery_critical` is True (quick task 260923-fr4: the
         BATTERY EMPTY hold is active), the parked cadence
         (`device_config.BATTERY_CRITICAL_SLEEP_S`) is pinned ahead of
         every other consideration — checked FIRST, before even
         `display_enabled=False` below, because a flat pack overrides
         even the operator's own toggle (poll_loop.py's hold-kind
         priority — battery_empty, then display_off, then quiet_hours —
         mirrors this exactly).
      2. Otherwise, when `device_cfg.get("display_enabled")` is
         explicitly `False`, the screen-off cadence
         (`device_config.DISPLAY_OFF_SLEEP_S`) is pinned independently
         of `wake_interval_s` (12-CONTEXT.md D-01) — checked next,
         before `wake_interval_s`, because the display-off cadence
         overrides whatever `wake_interval_s` happens to be configured
         to.
      3. Otherwise, `device_cfg.get("wake_interval_s")` when it is a
         positive int.
      4. Otherwise, `env_sleep_s()`.
      5. Otherwise, `None`.

    `battery_critical` defaults to `False` so every pre-existing call
    site — none of which know about the BATTERY EMPTY latch — keeps its
    original result exactly unchanged.

    Every test above is an explicit `isinstance()`/`is None` check,
    never `or` — this codebase's documented idiom for a value with a
    legitimate falsy state (0 is never a valid wake_interval_s, but the
    idiom is followed even so, so a stray 0 can never silently fall
    through to the next branch by merely looking falsy).
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


# 24-03-PLAN.md Task 2 (CFG-43): the verdict vocabulary for one OBSERVED
# interval between two consecutive device check-ins. Module constants, not
# bare string literals, for the same reason HOLD_QUIET_HOURS above is one.
#
# Every term here is observed, never claimed. There is deliberately no
# term asserting the device KEPT a wake, and none asserting it was on time
# as a matter of conduct rather than of record:
# 24-RESEARCH.md Risk 1 shows that a log rotation `history_db.
# ingest_caddy_battery_log()` missed leaves a hole in `device_health`
# indistinguishable from a device that did not wake, and that NO schema
# change recovers it. A verdict here is therefore a statement about the
# RECORD of check-ins, never about the device's conduct — and the name is
# the one every caption drawn from it will inherit.
CHECK_IN_ON_CADENCE = "on_cadence"
CHECK_IN_LATE = "late"
CHECK_IN_MISSING = "missing"
# The honest fourth state: `history_db.check_in_gaps()` reports `gap_s`
# as None for a span bounded by an undatable or out-of-order timestamp,
# and a span whose duration is not knowable must not be reported as one
# the device kept.
CHECK_IN_UNKNOWN = "unknown"


def classify_check_in_gap(gap_s, wake_interval_s):
    """Classify ONE observed interval between consecutive device check-ins
    (`history_db.check_in_gaps()`'s `gap_s`) as `CHECK_IN_ON_CADENCE`,
    `CHECK_IN_LATE`, `CHECK_IN_MISSING` or `CHECK_IN_UNKNOWN`.

    The thresholds come from `device_staleness_thresholds()` directly
    above — the same `(warn_s, error_s)` pair the Device/Frame tile's own
    `staleness_status()` consumes — so a grid drawn from these verdicts and
    that tile can never disagree about what "late" means. The multipliers
    (`MISSED_WAKES_WARN`/`MISSED_WAKES_ERROR`) and the floors are NOT
    re-typed here and must never be: one definition, reused.

    Boundaries, matching `staleness_status()`'s own discipline exactly:
    below `warn_s` is on-cadence, `warn_s` itself is already late, and
    `error_s` itself is already missing.

    `wake_interval_s` is an ARGUMENT, never read from `device_config` here.
    Two reasons. First, a caller drawing a grid has to be able to state
    WHICH cadence the grid was judged against, and it can only say that
    honestly if it passed it in. Second, the cadence actually in force at
    the time of a historical gap is unrecoverable (`device_config.json` is
    a current-state file with a pinned no-migration/no-rewrite contract,
    and `effective_wake_interval_s()` above switches to
    `DISPLAY_OFF_SLEEP_S` whenever the screen is off) — so the caller, not
    this function, owns that caveat.

    `wake_interval_s = None` degrades to the bare floors rather than
    refusing to classify, exactly as `device_staleness_thresholds()`
    already does for a deployment whose cadence cannot be determined.

    `gap_s` that is None, a bool, a non-number, negative, or NaN is
    `CHECK_IN_UNKNOWN` — never on-cadence. The `isinstance()`/explicit-test
    idiom, never `or`, is this codebase's documented handling for a value
    with a legitimate falsy state (a genuine 0-second gap is on-cadence and
    must not fall through to "unknown" merely by looking falsy).
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


# 22-02-PLAN.md Task 1 (D-03/CFG-26): the hold-reason vocabulary. A
# module constant, not a bare string literal, so every consumer (the
# strip, the tiles, companion/frame_state.py) compares against the same
# identity rather than each hand-typing "quiet_hours" and risking a typo
# that silently never matches. `None` is the other legal value, meaning
# "not held" — there is deliberately no second reason constant for a
# screen that is merely off, because that case is already fully absorbed
# into `effective_wake_interval_s()`'s own DISPLAY_OFF_SLEEP_S branch: a
# longer, but still perfectly ordinary, cadence. Only an active
# quiet-hours window changes the STATE a consumer should render (D-03's
# "held" state), so only it gets a reason.
HOLD_QUIET_HOURS = "quiet_hours"


def next_wake_status(last_checkin_ts, device_cfg, battery_critical=False):
    """The `(next_wake_iso, effective_interval_s, hold_reason)` triple
    every consumer of "when will the frame next wake" needs (D-03/
    CFG-26, 22-02-PLAN.md Task 1): the strip's headline, the Home/Health
    status tiles and every settings delay caption all read this ONE
    result instead of each re-deriving their own — that is what makes
    the disagreement X2 found ("Expected since 23:0x" beside "Checking
    in normally") impossible by construction.

    `battery_critical` (quick task 260923-fr4, default False so every
    pre-existing call site is unaffected) is threaded straight through to
    `effective_wake_interval_s()` below, which pins the parked
    `device_config.BATTERY_CRITICAL_SLEEP_S` cadence ahead of every other
    consideration when True — see that function's own docstring for the
    full precedence list. This is the same mirror
    `_notify_silence_transition()` and every companion frame-strip/flash
    call site read from `wake.read_battery_critical()`, so a parked frame
    never crosses its own staleness threshold on the SHORT cadence it was
    configured with before parking.

    Returns `(None, None, None)` — never raises — for every one of
    these cases, matching `next_wake_at_iso()`'s own pre-existing
    never-raise contract:
      - `last_checkin_ts` is falsy (no check-in recorded yet) or is not
        a string `datetime.fromisoformat()`-equivalent parsing accepts;
      - `effective_wake_interval_s(device_cfg)` itself returns `None`
        (no on-disk `wake_interval_s`, no `SKYPANE_SLEEP_S`, and the
        screen is not off) — with no known base cadence there is
        nothing for a quiet-hours extension to compose against.

    `last_checkin_ts` is parsed with the same naive-value-is-UTC
    convention this module has always used (see `next_wake_at_iso()`
    below): a timezone-naive result is stamped UTC before any
    arithmetic, never left ambiguous.

    Quiet-hours composition — reproduces `stub-server/byos_server.py`'s
    own `quiet_hours_sleep_s(display_off_sleep_s(base_sleep_s, ...),
    ...)`, i.e. `max(base_interval, seconds_remaining_in_the_window)`, by
    composing two already-tested primitives; no new window arithmetic is
    invented here (`device_config.quiet_hours_status()`'s own "never
    raise" contract already covers a hostile config or epoch).
    `effective_wake_interval_s(device_cfg)` supplies the base half
    (already screen-off aware); `device_config.quiet_hours_status()`
    supplies the quiet-hours half, called TWICE against the same
    `device_cfg`, both times against an epoch derived only from
    `last_checkin_ts` and the base interval — never against a
    render-time "now":

      1. At the check-in epoch itself (`parsed.timestamp()`), catching
         a window already active when the device last reported in — the
         device's own sleep_s at that moment already reflects the hold.
      2. At the check-in epoch PLUS the base interval — the base
         candidate wake, before any quiet-hours extension — catching a
         window that OPENS between the check-in and that candidate.
         This second call is necessary, not optional: a device polling
         every 15 minutes that last checked in two minutes before a
         23:00 quiet-hours window opens gets told, at THAT poll, to
         sleep the ordinary 900s (the window is not active yet at
         22:58); it is the poll landing inside the window a quarter
         hour later that actually receives the long hold. Reporting the
         naive 22:58 + 900s = 23:13 candidate as "the next wake" would
         be technically the device's literal next radio contact, but it
         would misrepresent what a household member cares about — the
         frame is, in every practical sense, held for the night — and
         is exactly the shape of X2's nightly false alarm this plan
         exists to remove. Both calls reuse the SAME tested primitive
         (`quiet_hours_status`) at a different, still check-in-derived
         epoch; no new window arithmetic is written here.

    Whichever call (or both) reports an active window sets
    `hold_reason` to `HOLD_QUIET_HOURS` and contributes its own
    check-in-relative seconds figure — the first call's remaining
    seconds are already measured from the check-in; the second call's
    are converted to the same frame of reference by adding the base
    interval that elapsed to reach it. `effective_interval_s` is the max
    of the base interval and every contributed figure, so quiet hours
    can only ever lengthen the wait, never shorten it, matching
    `quiet_hours_sleep_s()`'s own documented invariant.

    Inherits `seconds_until_quiet_hours_end()`'s own accepted PEP 495
    `fold=0` DST caveat rather than reopening it: a window boundary
    configured inside the 02:00-03:00 transition hour on the last Sunday
    of March or October can resolve up to an hour off for that one
    instant, twice a year — accepted there, accepted here for the same
    reason (D-01's "never shorter than the base sleep" rule bounds the
    worst case to one extra or one missing wake).
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
    """The next time the device is expected to wake, as an ISO-8601 UTC
    string, or `None` when it cannot be determined (D-13/S-02).

    A thin wrapper over `next_wake_status()` (D-03/CFG-26,
    22-02-PLAN.md Task 1) returning its ISO element only. Its name,
    signature, None-cases and never-raise contract are all unchanged by
    that extension, so `home_page.py:421` and `config_page.py:3109` keep
    compiling and keep returning the same values for every
    non-quiet-hours configuration; they migrate to the richer accessor
    in their own plan, not here. `battery_critical` (quick task
    260923-fr4, default False) is threaded straight through to
    `next_wake_status()` for the identical reason that function's own
    docstring gives.

    Returns a plain ISO string, not formatted text — deliberately not
    run through any formatter here, since this module has no view
    dependency (see the module docstring above): each caller formats
    the value itself for display.
    """
    return next_wake_status(last_checkin_ts, device_cfg, battery_critical=battery_critical)[0]
