#!/usr/bin/env python3
"""The systemd-timer oneshot entrypoint: detect -> render -> atomic swap.

Poll cadence: 30 seconds, comfortably inside both aggregators' 1 req/s limit
given one call per cycle. This script has no in-process loop; a systemd
`.timer`/`.service` unit pair drives the cadence by invoking it repeatedly.

Cross-cycle state: this script has no in-process memory between invocations,
so the last detected flight, last chosen state, the pending display queue
(see "Display pacing" below), the unrecognized-ICAO-prefix registry, and the
hysteretic battery_low_active decision all live in
`<state_dir>/poll_state.json`, written with the same
tmp-write-then-os.replace() pattern stub-server/byos_server.py's
save_state() uses. An unreadable or malformed state file is treated as empty
state, never as a crash.
`<state_dir>/battery_state.json` is a second, read-only input this module
never writes - it is owned and written exclusively by
stub-server/byos_server.py's save_battery_state(): two processes
read-modify-writing one JSON file is a real lost-update race, and neither
unit takes a lock.

Display pacing: this server re-renders every 30s, but the frame physically
cannot redraw that fast, so handing it a new "current" aircraft on every
distinct detection silently overwrote flights the device never got a chance
to fetch. Distinct selections are therefore queued and the "current" slot
advances no faster than the device's own measured redraw floor. This is a
mitigation, not a cure: a burst severe enough to overflow the queue's
staleness bound or its depth cap still loses flights - deliberately, because
the alternative is an unbounded queue whose displayed information drifts
arbitrarily far behind reality, which would defeat the point of a real-time
departure board.

Usage:
    server/.venv/bin/python3 server/poll_loop.py --once
    server/.venv/bin/python3 server/poll_loop.py --once --state-dir /tmp/x
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

# Allow both `import server.poll_loop` (package import) and direct script
# execution (`python3 server/poll_loop.py`, where sys.path[0] is server/
# itself and the repo root must be added by hand before the absolute
# `server.plane.*` imports below can resolve).
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import server.device_config as device_config
import server.history_db as history_db
import server.notify as notify
import server.panel_format as panel_format
import server.plane.calendar_rules as calendar_rules
import server.plane.colour_rules as colour_rules
import server.plane.detect as detect
import server.plane.enrich as enrich
import server.plane.illustrations as illustrations
import server.plane.manual_resolutions as manual_resolutions
import server.plane.render as render
import server.plane.runway_config as runway_config
import server.wake as wake

DEFAULT_STATE_DIR = os.path.join(_HERE, "state")
POLL_INTERVAL_S = 30

# Each archived PNG is a full 1200x1600 panel image (a few hundred KB) -
# this cap bounds the gallery directory to single-digit megabytes of disk
# use regardless of how long the server has been running.
GALLERY_DIRNAME = "gallery"
GALLERY_MAX_ENTRIES = 25

# --- Display pacing constants -----------------------------------------------
#
# MIN_ADVANCE_INTERVAL_S is the device's own physical redraw floor, not a
# preference: the sum of two measured firmware numbers.
#
#   * CONFIG_FP_MIN_REFRESH_SPACING_S = 60s (firmware Kconfig default,
#     confirmed not overridden in sdkconfig.defaults). fp_panel_draw()
#     re-arms this guard after every successful blit, so it is a floor
#     between two DRAWN images, not between two wakes.
#   * ~31.5s for one full 13.3" Spectra 6 refresh, measured on real hardware.
#
# 60 + 31.5 = 91.5s, rounded down to 90 so the server paces slightly ahead of
# the device. Caveat: firmware/sdkconfig is generated at build time and not
# committed, so a menuconfig change on the flashed board is invisible here.
MIN_ADVANCE_INTERVAL_S = 90

# Hard staleness bound: a queued aircraft whose turn arrives more than this
# many seconds after it was first detected is discarded rather than shown -
# showing it would mislead the viewer about how current the board is. 150s
# (2m30s) trades off "never drop a flight" (an unbounded queue whose lag
# grows without limit) against "never show anything stale".
MAX_STALENESS_S = 150

# Defensive depth backstop, independent of MAX_STALENESS_S: expired entries
# are only skipped at advance time, so a pathological burst (a systemd
# catch-up storm, a clock jump) could otherwise pile up entries between two
# advances. A poll selects at most one aircraft every POLL_INTERVAL_S=30s, so
# at most 150/30 = 5 aircraft can legitimately be enqueued inside one
# staleness window; anything beyond is not real traffic. Written as a
# literal, not a division, so a cadence retune cannot silently inflate this.
MAX_PENDING_FLIGHTS = 5


def now_s():
    """Wall-clock epoch seconds, injectable so tests can drive cadence
    deterministically instead of sleeping through real 90s windows - every
    pacing/staleness decision is arithmetic over timestamps persisted in
    poll_state.json, not over in-process memory. Float epoch seconds, not an
    ISO-8601 string, because these values are arithmetic operands, not an
    audit record.
    """
    return time.time()


def _as_timestamp(value):
    """Coerce a persisted timestamp to a float, or None if missing or not a
    real number. Booleans are rejected explicitly (bool is an int subclass in
    Python). A hand-edited or older state file degrades to "no timestamp",
    never raises.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def normalise_pending(value):
    """Coerce poll_state.json's "pending_flights" into a list of well-shaped
    `{"flight": dict, "first_seen": float}` entries.

    Anything malformed - a non-list, a non-dict entry, a missing flight, an
    unusable first_seen - is dropped rather than raising. A state file
    written before this key existed yields an empty queue.
    """
    if not isinstance(value, list):
        return []
    entries = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        flight = entry.get("flight")
        first_seen = _as_timestamp(entry.get("first_seen"))
        if not isinstance(flight, dict) or first_seen is None:
            continue
        entries.append({"flight": flight, "first_seen": first_seen})
    return entries


def advance_is_due(last_advance_at, now, min_interval_s=None):
    """May the "current" display slot advance on this cycle?

    - No recorded advance yet (fresh state, or a migrated poll_state.json)
      -> due.
    - A negative elapsed time means the recorded stamp is in the future (an
      NTP step backwards, or a hand-edited file) - treated as due rather than
      a wait, since the alternative stalls the display for the whole jump.
    """
    if min_interval_s is None:
        min_interval_s = MIN_ADVANCE_INTERVAL_S
    if last_advance_at is None:
        return True
    elapsed = now - last_advance_at
    if elapsed < 0:
        return True
    return elapsed >= min_interval_s


def enqueue_pending(pending, flight, now, max_entries=None):
    """Append `flight` to the pending queue; return the hexes evicted by the
    depth cap (normally empty).

    Re-detecting an already-queued aircraft refreshes its stored record but
    leaves `first_seen` untouched - it answers "how long has this aircraft
    been waiting?", which MAX_STALENESS_S bounds; letting it move would let
    an aircraft loiter indefinitely by being re-detected.

    Eviction is oldest-first: the entry closest to expiring has least left
    to lose.
    """
    if max_entries is None:
        max_entries = MAX_PENDING_FLIGHTS
    hex_code = flight.get("hex")
    for entry in pending:
        if entry["flight"].get("hex") == hex_code:
            entry["flight"] = flight
            return []
    pending.append({"flight": flight, "first_seen": float(now)})
    evicted = []
    while len(pending) > max_entries:
        evicted.append(pending.pop(0)["flight"].get("hex"))
    return evicted


def pop_fresh_pending(pending, now, max_staleness_s=None):
    """Pop the oldest still-fresh entry off `pending` (FIFO), dropping any
    entry that has already exceeded `max_staleness_s` on the way.

    Returns `(flight_or_None, dropped_hexes)`; `pending` is mutated in place.

    An expired entry is dropped and the scan continues, so it never blocks a
    fresher one behind it. A negative age (first_seen stamped in the future
    by a clock step) reads as fresh - the safe direction, showing an aircraft
    rather than silently discarding it.
    """
    if max_staleness_s is None:
        max_staleness_s = MAX_STALENESS_S
    dropped = []
    while pending:
        entry = pending.pop(0)
        if (now - entry["first_seen"]) > max_staleness_s:
            dropped.append(entry["flight"].get("hex"))
            continue
        return entry["flight"], dropped
    return None, dropped


# Battery-low hysteresis thresholds, raw millivolts - never a derived
# percentage: no real discharge curve exists for this pack, so a percentage
# would be fabricated precision; raw mV matches how hardware/logtools.py's
# check-battery already reasons about it. BATTERY_LOW_THRESHOLD_MV = 3500
# sits with margin above hardware/logtools.py's --cutoff-mv 3400 "genuinely
# depleted" convention, so the warning fires with days of runway left.
# BATTERY_LOW_CLEAR_MV = 3600 is a 100 mV re-arm buffer against flapping.
BATTERY_LOW_THRESHOLD_MV = 3500
BATTERY_LOW_CLEAR_MV = 3600

# BATTERY EMPTY hysteresis thresholds, raw millivolts - same reasoning as the
# badge thresholds above: no state-of-charge curve exists, so this stays a
# raw-mV comparison. Sourced from a measured discharge run: ~3500 mV at ~43h
# remaining, ~3364 mV at ~21.5h, and a last reading of 2960 mV about 17
# minutes before the panel froze mid-transition. BATTERY_CRITICAL_MV = 3300
# sits with margin below the 3500 mV badge (so the badge always fires first)
# and above the 2960 mV failure point, parking the frame on a deliberate
# screen before a real pack would die. BATTERY_CRITICAL_RECOVER_MV = 3700 is
# a wider 400 mV re-arm buffer than the badge's, since a false recovery here
# means a device dying again mid-refresh. stub-server/byos_server.py keeps
# its own parity-checked copy of BATTERY_CRITICAL_RECOVER_MV to anticipate
# recovery one check-in early.
BATTERY_CRITICAL_MV = 3300
BATTERY_CRITICAL_RECOVER_MV = 3700


def _extract_aircraft(snapshot):
    """A raw aggregator response dict carries its aircraft array under a
    provider-specific key ("ac" for airplanes.live and adsb.lol, "aircraft"
    for adsb.fi). Never raises on an unexpected shape - an empty list is the
    safe default.
    """
    if not isinstance(snapshot, dict):
        return []
    for key in ("ac", "aircraft"):
        value = snapshot.get(key)
        if isinstance(value, list):
            return value
    return []


def _classify_state_source(vertical_rate_fpm):
    """Was this cycle's confirmed state newly inferred from a vertical-rate
    reading that crossed a threshold, or held over because the reading sat
    inside the deadband (or was missing/non-numeric)? Log-only classification
    mirroring runway_config.infer_runway_config()'s own branches without
    duplicating its threshold constants as literals.
    """
    if isinstance(vertical_rate_fpm, bool):
        return "held"
    if not isinstance(vertical_rate_fpm, (int, float)):
        return "held"
    if vertical_rate_fpm >= runway_config.CLIMB_THRESHOLD_FPM or vertical_rate_fpm <= runway_config.DESCEND_THRESHOLD_FPM:
        return "inferred"
    return "held"


def _poll_state_path(state_dir):
    return os.path.join(state_dir, "poll_state.json")


def load_poll_state(state_dir):
    """Missing, unreadable, or malformed -> empty state, never a crash."""
    try:
        with open(_poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


# The tri-valued hold-state latch. `None` means not holding; the other two
# name which screen is currently on the glass. A single key keeps "am I
# already holding?" the single test `was_hold is None`, correct for any
# number of hold mechanisms without a compound boolean test to extend.
# Without "battery_empty" as its own kind, a persisted park would read back
# as "not holding" on the next cycle and repaint every 30 seconds instead of
# staying parked.
_HOLD_KINDS = ("quiet_hours", "display_off", "battery_empty")


def _hold_state(poll_state):
    """Return the current hold kind (`"quiet_hours"` / `"display_off"` /
    `"battery_empty"`), or `None` when not holding.

    Migration: an older `poll_state.json` carries only the legacy
    `quiet_hours_active` boolean and no `hold_state` key. When `hold_state`
    is absent, this falls back to that boolean, returning `"quiet_hours"`
    when it is literally `True` (otherwise `None`) - without this, an
    upgrade landing mid-window would read "not holding" and force a needless
    full refresh of the screen already on the glass. The fallback fires for
    at most one cycle per upgraded install: the caller retires the legacy key
    on its first write after reading it here.

    Never raises: an unrecognised `hold_state` string degrades to `None`
    (not holding).
    """
    if "hold_state" in poll_state:
        kind = poll_state.get("hold_state")
        return kind if kind in _HOLD_KINDS else None
    return "quiet_hours" if poll_state.get("quiet_hours_active") is True else None


def load_battery_state(state_dir):
    """Read-only: `<state_dir>/battery_state.json` is owned and written
    exclusively by stub-server/byos_server.py's save_battery_state() - this
    function never writes it, since two processes read-modify-writing one
    JSON file would race.

    Returns the int `battery_mv` reading, or None on: a missing file,
    invalid JSON, a non-dict payload, a missing `battery_mv` key, or a
    `battery_mv` that is a bool, not an int, or not strictly positive.
    Degrades, never raises.
    """
    try:
        with open(os.path.join(state_dir, "battery_state.json")) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    mv = data.get("battery_mv")
    if isinstance(mv, bool) or not isinstance(mv, int) or mv <= 0:
        return None
    return mv


def apply_battery_hysteresis(battery_mv, was_active):
    """Pure function: the battery-low decision, with hysteresis between
    BATTERY_LOW_THRESHOLD_MV (3500) and BATTERY_LOW_CLEAR_MV (3600).

    `battery_mv=None` (never reported, or an unreadable/malformed file)
    returns `was_active` unchanged - a device that has never reported must
    not spuriously show the icon, and a temporarily unreadable file must not
    spuriously clear a real warning.

    Otherwise: when already active, it clears only once the reading is
    strictly below BATTERY_LOW_CLEAR_MV. When not active, it sets the
    warning at the threshold, inclusive. A reading strictly between the two
    constants deliberately holds the previous decision in both directions:
    it can neither newly arm nor newly clear the warning.
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV


def apply_battery_critical_hysteresis(battery_mv, was_active):
    """Pure function: the BATTERY EMPTY latch decision, the identical shape
    as `apply_battery_hysteresis()` above, applied to the park/hold decision
    rather than the badge, with hysteresis between BATTERY_CRITICAL_MV (3300)
    and BATTERY_CRITICAL_RECOVER_MV (3700).

    `battery_mv=None` returns `was_active` unchanged - a missing or rejected
    reading can neither newly park the frame nor clear an existing park; a
    rejected reading always arrives here as the last valid reading or as
    None, never as a fabricated zero.

    Otherwise: when already parked, it stays parked while the reading is
    strictly below BATTERY_CRITICAL_RECOVER_MV. When not parked, it parks at
    the threshold, inclusive. A reading strictly between the two constants
    holds the previous decision in both directions, exactly like the badge's
    own dead zone.
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_CRITICAL_RECOVER_MV
    return battery_mv <= BATTERY_CRITICAL_MV


# The shared "notifications" sub-dict of poll_state.json, and its two
# never-raising transition hooks. Each hook compares the freshly-computed
# boolean against what was last reported, sends at most one push per genuine
# transition, and records the newly-reported state whether or not the send
# actually succeeded - a flapping topic endpoint must not turn one
# transition into a push every cycle.

# A small knot table plus one clamped piecewise-linear lookup, duplicated
# (not imported) from companion/battery.py's identical
# BATTERY_DISCHARGE_CURVE/battery_percent() - this module must never import
# the companion package, and a private copy is cheaper than a third shared
# home. companion/test_companion_app.py enforces table equality and output
# parity between the two copies for every millivolt value from 2800 to 4400.
_NOTIFY_BATTERY_DISCHARGE_CURVE = (
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
_NOTIFY_BATTERY_FULL_MV = _NOTIFY_BATTERY_DISCHARGE_CURVE[-1][0]
_NOTIFY_BATTERY_EMPTY_MV = _NOTIFY_BATTERY_DISCHARGE_CURVE[0][0]


def _battery_percent_estimate(battery_mv):
    """A clamped 0-100 estimate for `battery_mv`, or None for a non-numeric,
    non-positive or NaN reading. Never raises. Performs the same operations,
    in the same order, as companion/battery.py's battery_fraction() followed
    by battery_percent().
    """
    try:
        value = float(battery_mv)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN is the one float that compares unequal to itself.
        return None
    if value <= 0:
        return None
    if value <= _NOTIFY_BATTERY_EMPTY_MV:
        fraction = 0.0
    elif value >= _NOTIFY_BATTERY_FULL_MV:
        fraction = 1.0
    else:
        fraction = None
        for (lower_mv, lower_pct), (upper_mv, upper_pct) in zip(
                _NOTIFY_BATTERY_DISCHARGE_CURVE, _NOTIFY_BATTERY_DISCHARGE_CURVE[1:]):
            if upper_mv >= value:
                percent = lower_pct + (value - lower_mv) * (upper_pct - lower_pct) / float(
                    upper_mv - lower_mv)
                fraction = percent / 100.0
                break
    return int(round(fraction * 100))


def _humanize_age_s(age_s):
    """A short "2 h"-shaped duration string for the frame-silent
    notification body, floored at 0 so a negative age (clock skew) never
    reads as "in the future". Deliberately not companion's own
    `relative_age_text()`, since this module must never import that package.
    """
    age_s = max(0, int(age_s))
    if age_s < 60:
        return "%ds" % age_s
    if age_s < 3600:
        return "%d min" % (age_s // 60)
    if age_s < 86400:
        return "%d h" % (age_s // 3600)
    return "%d d" % (age_s // 86400)


def _parse_iso_epoch(ts):
    """Parse an ISO-8601 string (`history_db.utc_now_iso()`'s own format) to
    epoch seconds, or None for anything unparsable - never raises. A
    timezone-naive value is stamped UTC before conversion, matching
    `server.wake.next_wake_at_iso()`'s convention.
    """
    try:
        parsed = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _notifications_group(device_cfg):
    """The `notifications` sub-dict off `device_cfg`, or None when
    `device_cfg` is not a dict or carries no well-formed group - never
    raises. Shared by both transition hooks below so neither repeats the
    same defensive `isinstance()` check.
    """
    if not isinstance(device_cfg, dict):
        return None
    notifications = device_cfg.get("notifications")
    return notifications if isinstance(notifications, dict) else None


def _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg, sender=None):
    """Push exactly one notification per genuine battery-low transition -
    never once per cycle, because
    `poll_state["notifications"]["last_battery_sent"]` remembers what was
    last reported. Called from both `battery_low_active` sites in
    `run_once()`, gated on the caller's own `battery_changed`.

    Returns immediately, sending and recording nothing, when the group has
    no `topic_url` configured or `battery_low` is off. The reported state is
    recorded whether or not the send actually succeeded, so a flapping topic
    endpoint cannot turn one transition into a push every cycle.

    Never raises: any exception - a malformed `device_cfg`, or a raising
    injected `sender` - is logged by type name and swallowed, since a poll
    cycle that dies on a notification is strictly worse than a missed one.
    `state_dir` is accepted (not used) to keep this hook's signature
    symmetric with `_notify_silence_transition()`'s own.
    """
    try:
        notifications = _notifications_group(device_cfg)
        if notifications is None:
            return
        topic_url = notifications.get("topic_url")
        if not topic_url or not notifications.get("battery_low"):
            return
        state = poll_state.setdefault(
            "notifications", {"last_battery_sent": False, "last_silent_sent": False}
        )
        if state.get("last_battery_sent") is battery_low:
            return
        lang = notifications.get("lang")
        if battery_low:
            pct = _battery_percent_estimate(battery_mv)
            body = notify.body_for_lang(notify.BATTERY_LOW_BODY, lang) % (
                battery_mv, pct if pct is not None else 0,
            )
        else:
            body = notify.body_for_lang(notify.BATTERY_OK_BODY, lang)
        send = sender or notify.send_notification
        # ALERT_TITLE, not TEST_NOTIFICATION_TITLE: this is a real
        # transition push, not the test button.
        send(topic_url, notify.ALERT_TITLE, body)
        state["last_battery_sent"] = battery_low
    except Exception as exc:
        print(
            "poll_loop: battery-transition notification hook failed: %s" % type(exc).__name__,
            file=sys.stderr,
        )


def _notify_silence_transition(state_dir, poll_state, conn, device_cfg, sender=None):
    """Push exactly one notification per genuine frame-silent transition, on
    the same shared staleness threshold the Health page displays
    (`wake.device_staleness_thresholds()`'s WARN value), reused rather than
    re-tuned, so this silent threshold can never drift below the Health
    page's own warn threshold.

    Returns immediately, sending and recording nothing, when the group has
    no `topic_url` configured, `frame_silent` is off, or
    `history_db.latest_device_health(conn)` has no row at all - a frame that
    has never checked in is a first-install state, not a silence transition.
    Records the reported state whether or not the send succeeded, exactly as
    its battery counterpart above does.

    Must be called only after this cycle's own `_record_history()` call has
    already committed (see both call sites in `run_once()`), so a frame that
    just checked in this cycle can never be reported silent for the one
    cycle before that fresh row becomes visible.

    Never raises: any exception is logged by type name and swallowed, for
    the identical reason its battery counterpart above documents.
    """
    try:
        notifications = _notifications_group(device_cfg)
        if notifications is None:
            return
        topic_url = notifications.get("topic_url")
        if not topic_url or not notifications.get("frame_silent"):
            return
        latest = history_db.latest_device_health(conn)
        if not latest:
            return
        checkin_epoch = _parse_iso_epoch(latest.get("ts"))
        if checkin_epoch is None:
            return
        age_s = now_s() - checkin_epoch
        # The same critical-aware mirror the top of run_once() feeds into
        # effective_wake_interval_s, read back from the persisted latch
        # rather than threaded as a parameter - without it, a parked frame
        # checking in hourly would cross the 3-missed-wakes warn threshold on
        # its configured (short) cadence and raise a false frame-silent push
        # every hour it stays parked.
        warn_s, _error_s = wake.device_staleness_thresholds(
            wake.effective_wake_interval_s(
                device_cfg, battery_critical=bool(poll_state.get(wake.BATTERY_CRITICAL_STATE_KEY) is True)
            )
        )
        silent = age_s >= warn_s
        state = poll_state.setdefault(
            "notifications", {"last_battery_sent": False, "last_silent_sent": False}
        )
        if state.get("last_silent_sent") is silent:
            return
        lang = notifications.get("lang")
        if silent:
            body = notify.body_for_lang(notify.FRAME_SILENT_BODY, lang) % _humanize_age_s(age_s)
        else:
            body = notify.body_for_lang(notify.FRAME_RECOVERED_BODY, lang)
        send = sender or notify.send_notification
        # ALERT_TITLE, not TEST_NOTIFICATION_TITLE: this is a real
        # transition push, not the test button.
        send(topic_url, notify.ALERT_TITLE, body)
        state["last_silent_sent"] = silent
    except Exception as exc:
        print(
            "poll_loop: _notify_silence_transition failed: %s" % type(exc).__name__,
            file=sys.stderr,
        )


def save_poll_state(state_dir, state):
    """Atomic tmp-write-then-os.replace(), matching
    stub-server/byos_server.py's save_state(). Never leaves a stray .tmp
    file behind, even if the write itself fails.
    """
    path = _poll_state_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def write_panel_atomic(state_dir, rendered):
    """Write `rendered` (packed panel bytes) to <state_dir>/panel.bin only if
    its SHA-256 differs from the currently-served bytes - tmp-write-then-
    os.replace(), so byos_server.py can never serve a half-written file.
    Returns True if the served panel actually changed.
    """
    panel_path = os.path.join(state_dir, "panel.bin")
    if os.path.exists(panel_path):
        with open(panel_path, "rb") as fh:
            existing = fh.read()
        if hashlib.sha256(existing).hexdigest() == hashlib.sha256(rendered).hexdigest():
            return False

    tmp = panel_path + ".tmp"
    try:
        with open(tmp, "wb") as fh:
            fh.write(rendered)
        os.replace(tmp, panel_path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    return True


def _classify_source_fault(diagnostics):
    """True only when every ADS-B provider this cycle actually queried
    failed outright - never merely because providers were queried
    successfully and found nothing on the tracked runway.

    Both cases return the same thing from `detect.poll_current_aircraft()` -
    a `None` selection - so this function is the only place that tells
    "every source is down" apart from "nothing is on the runway right now".
    Collapsing that distinction would fire the alert through every ordinary
    quiet period, training the user to ignore it.

    `diagnostics` is the dict `detect.poll_current_aircraft()` populates in
    place - `queried`/`failed`/`selected`/`disagreement`/`runway_id` - only
    when a live poll passes one in. The injected-snapshot test branch never
    queries a provider, so `diagnostics` stays `None`, which this function
    correctly classifies as "no fault", not "unknown".
    """
    if not isinstance(diagnostics, dict):
        return False
    queried = diagnostics.get("queried")
    failed = diagnostics.get("failed")
    if not isinstance(queried, list) or not queried:
        return False
    if not isinstance(failed, list):
        return False
    return set(failed) == set(queried)


def _last_source_fault(state_dir):
    """Best-effort read of the previously-persisted fault flag from
    `history.db`'s fixed-size meta table (`history_db.META_SOURCE_FAULT`) -
    the durable, cross-process comparison point the fault-transition
    re-render below needs. Not stored in `poll_state.json`: adding a second
    write path there would reopen the two-writer race this project avoids
    elsewhere. `history.db` has its own concurrency discipline (WAL +
    busy_timeout), so it is the correct home for a per-cycle signal.

    A missing database, a never-yet-set key, or any read failure all resolve
    to `False` (no known prior fault) rather than raising - a read failure
    here must never abort a poll cycle.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            value = history_db.get_meta(conn, history_db.META_SOURCE_FAULT)
    except (sqlite3.Error, OSError) as exc:
        print("poll_loop: could not read source_fault meta: %s: %s" % (type(exc).__name__, exc))
        return False
    return value == "True"


def _should_record_event(flight, confirmed_state, poll_state):
    """True only on a real transition - the detected hex differs from the
    last-recorded one, the confirmed state differs, or the corroboration
    flag differs - never on an unchanged repeat detection.

    The server polls every 30 seconds, roughly 2,880 cycles a day; writing a
    `runway_events` row on every cycle would produce on the order of a
    million rows a year. A transition is the only interesting event, so this
    is the gate for it.

    Compares against `poll_state["last_recorded_hex"]` /
    `["last_recorded_confirmed_state"]` / `["last_recorded_corroborated"]`,
    persisted via `run_once()`'s single `save_poll_state()` call so the
    comparison survives this oneshot's process boundary. `flight` is
    expected non-None; a non-dict `flight` degrades to "no hex/corroboration
    known" rather than raising.
    """
    last_hex = poll_state.get("last_recorded_hex")
    last_confirmed = poll_state.get("last_recorded_confirmed_state")
    last_corroborated = poll_state.get("last_recorded_corroborated")
    hex_ = flight.get("hex") if isinstance(flight, dict) else None
    corroborated = flight.get("corroborated") if isinstance(flight, dict) else None
    return hex_ != last_hex or confirmed_state != last_confirmed or corroborated != last_corroborated


# The "caller did not ask for an epoch to be recorded" sentinel. It cannot
# be None, because None is a legitimate effective wake interval meaning "the
# cadence cannot be determined" - an epoch worth recording in its own right.
# Defaulting to None would let a call site that forgot to pass the interval
# write a NULL epoch indistinguishable from a real transition to an unknown
# cadence.
_NO_WAKE_EPOCH = object()


def _record_history(state_dir, flight, confirmed_state, route_source, route, tracked_runway_id, source_fault, record_event, now_iso, caddy_log=None, wake_interval_s=_NO_WAKE_EPOCH):
    """Write this cycle's durable signals into `history.db`, in one
    connection, fully contained: a database or filesystem failure here is
    caught and logged, never allowed to fail the poll cycle or leave the
    panel unwritten - history is an accessory to the panel, not a
    dependency of it.

    `record_event` (from `_should_record_event()`) gates the one thing not
    written on every cycle: a `runway_events` row, inserted only on a real
    hex/confirmed_state/corroborated transition. Everything else here - the
    pipeline-run timestamp, the source-fault flag, and (when `flight` is not
    None) the last-detection timestamp - is written to the fixed-size `meta`
    table on every cycle, transition or not, so those per-cycle freshness
    signals never grow the database.

    `caddy_log`, when given a path, ingests any new `/device/v1/display`
    lines from the Caddy durable access log into `device_health` on every
    cycle - a missing/unreadable log file is a no-op (0 rows), the same
    catch-and-log containment as everything else here.

    `wake_interval_s`, when supplied, records a `wake_epochs` row only when
    this cycle's effective interval differs from the newest one stored, so
    an unchanged cadence writes nothing. The value is the one `run_once()`
    already resolved once per cycle from `device_cfg`, not a second
    resolution here: reading the config twice in one cycle is how a
    mid-cycle save lands half in one cadence and half in another. The call
    sits inside this function's single `try` so its failure mode matches
    every other history write here.
    """
    route = route if isinstance(route, dict) else {}
    try:
        with history_db.open_db(state_dir) as conn:
            if record_event and isinstance(flight, dict):
                history_db.record_runway_event(
                    conn,
                    ts=now_iso,
                    hex=flight.get("hex"),
                    callsign=flight.get("callsign"),
                    aircraft_type=flight.get("aircraft_type"),
                    confirmed_state=confirmed_state,
                    corroborated=flight.get("corroborated"),
                    route_source=route_source,
                    airline=route.get("airline_name"),
                    origin=route.get("origin_iata"),
                    destination=route.get("destination_iata"),
                    tracked_runway=tracked_runway_id,
                )
            history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, now_iso)
            history_db.set_meta(conn, history_db.META_SOURCE_FAULT, str(source_fault))
            if flight is not None:
                history_db.set_meta(conn, history_db.META_LAST_DETECTION, now_iso)
            if caddy_log:
                history_db.ingest_caddy_battery_log(conn, caddy_log)
            if wake_interval_s is not _NO_WAKE_EPOCH:
                history_db.record_wake_epoch(conn, now_iso, wake_interval_s)
    except (sqlite3.Error, OSError) as exc:
        print("poll_loop: history write failed: %s: %s" % (type(exc).__name__, exc))


def _gallery_dir(state_dir):
    return os.path.join(state_dir, GALLERY_DIRNAME)


def _prune_gallery(gallery_dir):
    """Remove the oldest PNGs beyond GALLERY_MAX_ENTRIES, oldest-first by
    lexical sort order - which is chronological order, thanks to
    `_save_to_gallery()`'s colon-sanitised ISO-8601 filenames. A missing or
    unreadable gallery directory, or a failed removal, is silently
    tolerated - never raises.
    """
    try:
        entries = sorted(
            name for name in os.listdir(gallery_dir) if name.endswith(".png")
        )
    except OSError:
        return
    while len(entries) > GALLERY_MAX_ENTRIES:
        stale = entries.pop(0)
        try:
            os.remove(os.path.join(gallery_dir, stale))
        except OSError:
            pass


def _save_to_gallery(state_dir, canvas, now_iso):
    """Archive `canvas` (the pre-pack render already produced for this
    cycle - never a second render pass) as a PNG into
    `<state_dir>/gallery/`, named from a filesystem-safe form of `now_iso`
    so lexical order is chronological, then prune down to
    GALLERY_MAX_ENTRIES.

    The filename is generated server-side from this process's own clock,
    never from any external input; the companion service additionally only
    ever serves a name matched against a fresh directory listing.

    Called only when `write_panel_atomic()` actually changed the served
    bytes - an unchanged cycle is not a new render, and archiving one would
    fill the gallery with visually-identical duplicates. Wrapped in the same
    catch-and-log containment as `_record_history()`: the gallery is an
    accessory, never allowed to fail a poll cycle - by the time this is
    called, `panel.bin` has already been written.
    """
    try:
        gallery_dir = _gallery_dir(state_dir)
        os.makedirs(gallery_dir, exist_ok=True)
        safe_name = now_iso.replace(":", "-") + ".png"
        canvas.convert("RGB").save(os.path.join(gallery_dir, safe_name))
        _prune_gallery(gallery_dir)
    except Exception as exc:
        print("poll_loop: gallery archive failed: %s: %s" % (type(exc).__name__, exc))


def run_once(snapshot=None, state_dir=None, geofence=None, caddy_log=None):
    """One poll cycle. `snapshot=None` polls the live aggregators
    (detect.poll_current_aircraft()); a non-None `snapshot` is a raw
    aggregator response dict injected by the test harness so
    test_pipeline_e2e.py is fully hermetic (no live network call).

    Returns a small result dict: {"flight": ..., "state": ...,
    "panel_changed": ..., "theme": ..., "effective_theme": ...,
    "tracked_runway": ..., "source_fault": ..., "event_recorded": ...}.
    `theme` is always the configured base theme id; `effective_theme` is
    what the panel actually rendered with - equal to `theme` on any cycle
    that displayed no flight, and equal to the colour_rules-resolved id on
    any cycle that displayed one. `flight` is what this cycle detected,
    which is not necessarily what it displayed - a distinct new aircraft
    may have been queued rather than shown; `state` and `panel_changed`
    describe the display. Read poll_state.json's "last_flight" for what is
    actually on the panel. Everything derived from the displayed aircraft -
    the render, the enrichment, and the history row - is keyed on that
    displayed aircraft (`current_flight`), never on this cycle's raw
    detection, so a paced cycle can never write a row whose hex and route
    describe two different aircraft.

    Never logs a bearer token or BYOS setup secret - this module has no
    access to either; only the selected hex/callsign/altitude/state and
    whether the panel changed are printed.

    Hold states: two independent mechanisms can each put the panel on hold
    - a scheduled quiet-hours window and the manual display-off toggle -
    both gated through one shared `poll_state["hold_state"]` latch
    (`_hold_state()`). When the once-per-cycle device-config read reports
    either mechanism active, this function takes an early return before any
    ADS-B call is made - a hold suppresses detection entirely for the
    cycle, not just its display; an off period has no scheduled end, so
    without this the aggregators would be queried indefinitely. The rule is
    "render once at entry, then hold": the held screen is drawn exactly
    once, on the first cycle `_hold_state(poll_state)` flips from `None` to
    a kind, and every subsequent held cycle - including a move from one
    hold kind to the other - is a deliberate no-op for the panel: an e-ink
    refresh costs energy and flashes visibly for no informational gain.
    `display_enabled=False` always wins on what the panel shows over a
    standing quiet-hours window - the toggle is the operator's explicit
    manual instruction; the opposite resolution (longest sleep wins)
    applies only to how long the device sleeps, and lives entirely in
    stub-server/byos_server.py, not here. The first cycle after all hold
    conditions clear resumes normal detection and forces one repaint of the
    live board from whichever branch below would otherwise have held it, so
    no stale held image survives.
    """
    state_dir = state_dir or DEFAULT_STATE_DIR
    os.makedirs(state_dir, exist_ok=True)

    # Configure the illustration override resolver and the manual-resolution
    # registry from THIS cycle's own state_dir, here rather than in main() -
    # run_once() is the single entry point both the systemd oneshot and
    # companion/app.py's POST /poll-now in-process trigger go through, so
    # setting both here covers both triggers without a second call site.
    # Idempotent, and both callers pass the same state_dir, so this
    # process-global assignment is safe under companion/app.py's
    # ThreadingHTTPServer.
    #
    # The manual registry is reloaded from disk here, once per cycle, for
    # the same reason the device_cfg read below is: a companion-side save
    # landing between two separate reads would otherwise split one cycle
    # across two registries. This is also the latency contract the operator
    # is told about - a manual resolution reaches the glass at the next
    # wake, never instantly.
    illustrations.set_override_state_dir(state_dir)
    manual_resolutions.set_manual_registry_state_dir(state_dir)
    # Prime the per-flight colour-rule registry cache from THIS cycle's own
    # state_dir, for the same reason as the priming calls above - a
    # companion-side rule save landing mid-cycle must never split one
    # rendered panel across two registry configurations. Only loads a small
    # JSON file into the process-wide cache; the resolver itself,
    # resolve_effective_theme_id(), is NOT called here - render_state and
    # current_flight are not settled yet at this point.
    colour_rules.set_colour_rules_state_dir(state_dir)

    # The calendar refresh is its own distinct step, not a fourth entry in
    # the priming block above: the calls above only read a small JSON file
    # into a process-wide cache, while this one may open a socket. It is
    # still safe to call unconditionally at the top of every cycle because
    # refresh_calendar_registry() makes three guarantees: no transport call
    # at all when the feature is unconfigured, none when the throttle
    # interval has not elapsed, and a single bounded call otherwise - and it
    # never raises, so it can never delay a render. now_s() is passed as the
    # clock, the same seam every other per-cycle timestamp decision in this
    # function uses, so the test harness's fake clock drives the calendar
    # throttle too.
    _, calendar_registry = calendar_rules.refresh_calendar_registry(state_dir, now_s())

    # Read the user's saved theme + tracked runway once per cycle, not once
    # per call site - a mid-cycle save landing between two separate reads is
    # exactly how a panel could end up rendered half in one theme/runway and
    # half in another. The loader never raises and always returns
    # registry-member values, so no validation is needed here.
    device_cfg = device_config.load_device_config(state_dir)
    theme_id = device_cfg["theme"]
    # poll_state.json and battery_state.json are each read once per cycle,
    # right here, and every branch below - both the hold branch and the main
    # path - reuses these same two objects rather than re-reading either
    # file a second time. poll_loop.py is the single writer of
    # poll_state.json (byos and the companion only ever read it), so an
    # earlier load is equivalent to a later one within the same cycle. One
    # battery read feeds three decisions: the badge (apply_battery_hysteresis,
    # computed further down from this same battery_mv), the BATTERY EMPTY
    # latch below, and - via that latch -
    # wake.effective_wake_interval_s()'s critical-aware pin one line down.
    poll_state = load_poll_state(state_dir)
    battery_mv = load_battery_state(state_dir)
    # BATTERY EMPTY hysteresis: the same None-holds-the-prior-decision shape
    # as apply_battery_hysteresis's own badge decision, applied to
    # poll_state's own persisted latch rather than a per-branch local. Stored
    # back into poll_state immediately, before wake.effective_wake_interval_s()
    # is called one line down, so the sleep-interval mirror sees this cycle's
    # own decision rather than last cycle's stale one.
    was_battery_critical = poll_state.get(wake.BATTERY_CRITICAL_STATE_KEY) is True
    battery_critical = apply_battery_critical_hysteresis(battery_mv, was_battery_critical)
    poll_state[wake.BATTERY_CRITICAL_STATE_KEY] = battery_critical
    # The cadence in force THIS cycle, resolved once here for the same
    # reason device_cfg itself is read once, and passed down to every
    # _record_history() call site rather than re-resolved inside it. None is
    # a legitimate value ("cannot be determined") and is recorded as such.
    # battery_critical pins this to device_config.BATTERY_CRITICAL_SLEEP_S
    # ahead of every other consideration - see
    # wake.effective_wake_interval_s()'s own docstring for the full
    # precedence list.
    effective_wake_interval_s = wake.effective_wake_interval_s(device_cfg, battery_critical=battery_critical)
    # A default assignment, not a resolution. Every branch below - including
    # the four that display no flight - references this name, defined before
    # any branching for the same UnboundLocalError reason `unknown_prefix`
    # and `event_recorded` further down are. Do NOT call the colour_rules
    # resolver here: `render_state` and `current_flight` are not settled at
    # this point - calling the resolver here would either raise (both are
    # undefined this early) or, worse if written defensively, silently
    # resolve against the previous cycle's stale values.
    #
    # The identical trap applies to the calendar match
    # (calendar_rules.match_calendar_theme) - render_state and current_flight
    # are just as unsettled here, and the match additionally needs the
    # enriched `route`, which does not exist until enrich.resolve_route()
    # runs much further down. The match is computed at the flight-detected
    # branch's resolver call site below, not here.
    effective_theme_id = theme_id
    tracked_runway_id = device_cfg["tracked_runway"]
    # The once-per-cycle quiet-hours decision, computed from the same
    # device_cfg read above - never a second load_device_config() call, for
    # the same reason given above. now_s() (not datetime.now()) is
    # deliberate: it is this module's own harness-replaceable clock seam, so
    # the poll-loop test harness's fake clock drives this arithmetic too.
    quiet_remaining, quiet_until = device_config.quiet_hours_status(device_cfg, now_s())
    # display_enabled, read from the same device_cfg read above. The toggle
    # is the operator's explicit manual instruction and wins over a standing
    # schedule on what the panel shows, so "off" is checked first: the off
    # screen renders whenever the toggle is off, regardless of any window.
    # This is ONLY the display axis - the sleep-duration axis resolves the
    # opposite way (the longest value wins) and lives entirely in
    # stub-server/byos_server.py, not here.
    display_enabled = device_cfg["display_enabled"]
    # Priority: battery_empty, then display_off, then quiet_hours. The
    # battery axis outranks the operator's own toggle and any standing
    # schedule because a flat pack cannot honour either - it does not matter
    # what the operator asked for if the device is about to lose power
    # mid-refresh.
    if battery_critical:
        hold_kind = "battery_empty"
    elif not display_enabled:
        hold_kind = "display_off"
    elif quiet_remaining is not None:
        hold_kind = "quiet_hours"
    else:
        hold_kind = None

    if hold_kind is not None:
        # This early return sits before detect.load_geofence()/
        # detect.poll_current_aircraft() below on purpose: inside a hold,
        # this cycle must not touch `detect` at all, or it would keep
        # querying the free-tier ADS-B aggregators every 30 seconds
        # throughout the hold and throw every result away. An off period has
        # no scheduled end, so querying the aggregators through it would be
        # unbounded rather than merely overnight.
        #
        # poll_state and battery_mv are already loaded, once, above - reused
        # here rather than re-read, so this branch's battery_low decision and
        # the top-level battery_critical decision can never observe two
        # different mV readings for what is, on the wire, a single device
        # check-in.
        was_hold = _hold_state(poll_state)
        legacy_present = "quiet_hours_active" in poll_state

        # The identical three-line battery decision the main path computes
        # below - the held screen carries the same battery-low icon.
        was_battery_low = bool(poll_state.get("battery_low_active", False))
        battery_low = apply_battery_hysteresis(battery_mv, was_battery_low)
        battery_changed = battery_low != was_battery_low
        poll_state["battery_low_active"] = battery_low
        if battery_changed:
            _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg)

        # No provider was queried this cycle, so there is no new observation
        # to classify - carry the previously-persisted fault flag forward
        # rather than inventing a fault or silently clearing a real ongoing
        # one.
        source_fault = _last_source_fault(state_dir)
        poll_state["hold_state"] = hold_kind
        if legacy_present:
            del poll_state["quiet_hours_active"]
        now_iso = history_db.utc_now_iso()

        # Render on entry into a hold from the live board (`was_hold is
        # None`), never merely on `was_hold != hold_kind` - except for the
        # one boundary case: crossing into or out of BATTERY EMPTY. A full
        # e-ink refresh measures ~31.5s on this panel, and the device is
        # deep-asleep and cannot fetch anything mid-hold anyway, so
        # re-rendering for zero new information burns the panel for
        # nothing - every later cycle inside a hold is a deliberate no-op,
        # even across a battery-low badge transition. A move between QUIET
        # HOURS and DISPLAY OFF stays silent in both directions: a quiet
        # window ending while the toggle is still off leaves the off screen
        # up; the toggle switching off during a window leaves the quiet
        # screen up until the window ends. But entering BATTERY EMPTY from
        # an active DISPLAY OFF or QUIET HOURS hold - or recovering from it
        # - must repaint, or a flat-pack screen would never reach the glass,
        # and a recovered device would be stranded on BATTERY EMPTY forever.
        battery_empty_boundary_crossed = (was_hold == "battery_empty") != (hold_kind == "battery_empty")
        panel_changed = False
        if was_hold is None or battery_empty_boundary_crossed:
            if hold_kind == "battery_empty":
                # The byte-stable BATTERY EMPTY screen: no theme_id/
                # quiet_hours_until/source_fault/battery_low - build_canvas()
                # dispatches this state before any of the four are ever
                # consulted, and this call site never even offers them, so
                # none of this cycle's local values can leak a
                # hash-changing byte into the parked image.
                canvas = render.build_canvas(None, "battery_empty")
            else:
                canvas = render.build_canvas(
                    None, hold_kind, theme_id=theme_id, quiet_hours_until=quiet_until,
                    source_fault=source_fault, battery_low=battery_low,
                )
            rendered = panel_format.pack_panel(canvas)
            panel_changed = write_panel_atomic(state_dir, rendered)
            if panel_changed:
                _save_to_gallery(state_dir, canvas, now_iso)

        # The kind and the hysteresis memory both have to survive this
        # oneshot's process boundary; an unconditional save every 30 seconds
        # would be a pointless write. `was_hold != hold_kind` persists a
        # hold-kind change even though nothing was rendered - the panel did
        # not change but the record of what is on it did. `legacy_present`
        # is the one-time migration flush that retires the stale key.
        # `battery_critical_changed` covers the latch's own transition
        # explicitly - in practice always coincident with a `hold_kind`
        # change given battery_critical's top priority above, but named here
        # rather than relied upon implicitly, so a future priority change
        # cannot silently stop persisting this latch's own flip.
        battery_critical_changed = battery_critical != was_battery_critical
        if was_hold != hold_kind or battery_changed or legacy_present or battery_critical_changed:
            save_poll_state(state_dir, poll_state)

        # This call is not optional - it advances
        # history_db.META_LAST_PIPELINE_RUN, and skipping it for a long hold
        # would make the companion Health page raise a false "ADS-B pipeline
        # run is stale" anomaly. This matters even more for an off period,
        # which (unlike quiet hours) has no scheduled end.
        _record_history(
            state_dir, None, None, None, None, tracked_runway_id,
            source_fault, False, now_iso, caddy_log=caddy_log,
            wake_interval_s=effective_wake_interval_s,
        )

        # A display_off hold has no scheduled end - an operator can leave
        # the display off indefinitely, and nothing else in this branch ever
        # re-checks staleness while it lasts. Without this call, a frame
        # that dies (dead battery, disconnected Wi-Fi) during a hold would
        # never raise a frame_silent push for as long as the hold continues.
        # Placed after this branch's own `_record_history()` call, mirroring
        # the ordering `_notify_silence_transition()`'s own docstring
        # requires: this cycle's check-in (when a `caddy_log` is configured)
        # has already committed and is visible to
        # `history_db.latest_device_health()`. Persisted unconditionally
        # right after, since the hook may have mutated
        # `poll_state["notifications"]`, and that mutation must survive this
        # oneshot's process boundary regardless of whether the branch's own
        # earlier conditional save above ran.
        try:
            with history_db.open_db(state_dir) as conn:
                _notify_silence_transition(state_dir, poll_state, conn, device_cfg)
        except (sqlite3.Error, OSError) as exc:
            print("poll_loop: silence-transition history read failed (hold branch): %s: %s" % (type(exc).__name__, exc))
        save_poll_state(state_dir, poll_state)

        print(
            "poll_loop: hold_state=%s until=%s entered=%s panel_changed=%s "
            "battery_low=%s theme=%s tracked_runway=%s source_fault=%s"
            % (
                hold_kind,
                quiet_until,
                was_hold is None,
                panel_changed,
                battery_low,
                theme_id,
                tracked_runway_id,
                source_fault,
            )
        )

        return {
            "flight": None,
            "state": hold_kind,
            "panel_changed": panel_changed,
            "theme": theme_id,
            # A hold screen's effective theme IS the base theme - no rule or
            # arrivals override is ever consulted for a hold screen - and
            # reporting it uniformly here is what makes this key trustworthy
            # across every branch, held or not.
            "effective_theme": theme_id,
            "tracked_runway": tracked_runway_id,
            "source_fault": source_fault,
            "event_recorded": False,
        }

    geofence_data = detect.load_geofence(geofence)

    # `diagnostics`, when populated, is the only signal that tells "every
    # ADS-B source is down" apart from "nothing is on the runway right now"
    # - both otherwise return the same None selection. The injected-snapshot
    # branch never queries any provider, so it never gets a diagnostics dict
    # (stays None), which _classify_source_fault() correctly reads as "no
    # fault" rather than "unknown".
    diagnostics = None
    if snapshot is not None:
        aircraft = _extract_aircraft(snapshot)
        flight = detect.select_aircraft_for_runway(aircraft, geofence_data, runway_id=tracked_runway_id)
    else:
        diagnostics = {}
        flight = detect.poll_current_aircraft(geofence_data, runway_id=tracked_runway_id, diagnostics=diagnostics)

    source_fault = _classify_source_fault(diagnostics)
    previous_source_fault = _last_source_fault(state_dir)
    # Shared by every history/gallery write this cycle makes (runway_events
    # row, meta table, gallery filename) so they all record the same
    # instant, not three slightly different clock reads.
    now_iso = history_db.utc_now_iso()

    # poll_state is already loaded, once, at the top of this cycle - reused
    # here, never re-read. Reaching this line at all means no hold condition
    # is active any more, so a non-None hold kind here can only mean "this
    # is the first cycle after the last hold ended". Clear it now so every
    # branch below sees the cleared value in poll_state, and remember the
    # fact in hold_exited so the branches that don't unconditionally repaint
    # can force exactly one exit repaint.
    hold_exited = _hold_state(poll_state) is not None
    if hold_exited:
        poll_state["hold_state"] = None
        if "quiet_hours_active" in poll_state:
            del poll_state["quiet_hours_active"]
    current_flight = poll_state.get("last_flight")
    current_confirmed_state = poll_state.get("last_confirmed_state")
    current_route = poll_state.get("last_route")
    # The calendar sibling of current_route immediately above. Both describe
    # the flight that is CURRENTLY on the panel, both were computed on the
    # cycle that first displayed it, and both are reused - never recomputed
    # - by the held/repaint branch further down. Membership-tested against
    # device_config.THEMES here, before it can reach the resolver, so a
    # hand-edited poll_state.json cannot smuggle an unregistered theme id
    # onto the panel.
    current_calendar_theme_id = poll_state.get("last_calendar_theme_id")
    if (not isinstance(current_calendar_theme_id, str)
            or current_calendar_theme_id not in device_config.THEMES):
        current_calendar_theme_id = None
    previous_flight = poll_state.get("previous_flight")
    previous_confirmed_state = poll_state.get("previous_confirmed_state")
    previous_route = poll_state.get("previous_route")
    pending = normalise_pending(poll_state.get("pending_flights"))
    last_advance_at = _as_timestamp(poll_state.get("last_advance_at"))
    now = now_s()
    # Only the flight-detected branch below can ever set this, but every
    # branch falls through to the single shared log statement at the
    # bottom, so it must be defined here, before any branching, or an
    # ordinary cycle that detects nothing raises UnboundLocalError.
    unknown_prefix = None
    # Whether this cycle actually wrote a runway_events row (see
    # _should_record_event()) - surfaced in the returned result dict so the
    # companion service's manual-trigger handler can report it. Only ever
    # set True in the flight-detected branch's confirmed-state sub-branch
    # below.
    event_recorded = False

    # The battery-low decision, computed before any branching - every
    # branch needs it, either to thread into a render call or to decide
    # whether a hold-cycle re-render is warranted.
    was_battery_low = bool(poll_state.get("battery_low_active", False))
    # battery_mv is already loaded, once, at the top of this cycle - reused
    # here, never re-read, so this decision and the top-level
    # battery_critical decision can never observe two different mV figures
    # for one device check-in.
    battery_low = apply_battery_hysteresis(battery_mv, was_battery_low)
    battery_changed = battery_low != was_battery_low
    poll_state["battery_low_active"] = battery_low
    if battery_changed:
        _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg)

    # --- Display pacing: which detection occupies the "current" slot -------
    #
    # `flight` is what this poll detected; it is not necessarily what this
    # cycle displays. A distinct new aircraft goes into the pending queue,
    # and the "current" slot advances no faster than MIN_ADVANCE_INTERVAL_S
    # so the device gets a real chance to fetch and blit each one. Nothing
    # about the two-slot poster layout changes here - the actual
    # current/previous shift happens once, below, at the point a queued
    # aircraft is promoted (whether immediately, on the very first
    # detection, or delayed via the pending queue).
    promoted = None       # the aircraft that BECAME "current" on this cycle
    refreshed = False     # the same aircraft as "current", re-observed
    dropped = []          # hexes this cycle discarded - the residual loss
    queue_dirty = False   # pending/last_advance_at changed -> must persist

    if flight is not None:
        new_hex = flight.get("hex")
        old_hex = current_flight.get("hex") if isinstance(current_flight, dict) else None
        if current_flight is None:
            # Nothing on screen at all: show it immediately. Pacing exists to
            # stop a flight being overwritten before the device can fetch it;
            # there is nothing to overwrite yet, and deferring the very first
            # detection would only leave the frame empty for longer.
            promoted = flight
        elif new_hex == old_hex:
            # Re-detecting the SAME aircraft is not a new one - nothing
            # shifts, nothing queues. Its record is refreshed in place so
            # the vertical rate driving state inference stays current.
            current_flight = flight
            refreshed = True
        else:
            dropped.extend(enqueue_pending(pending, flight, now))
            queue_dirty = True

    # Drain the queue when the device is due for a redraw. This runs even on
    # a cycle that detected nothing: a burst followed by an empty sky is a
    # common shape, and without draining on quiet cycles every queued
    # aircraft would sit there until it expired. `promoted is None` guards
    # the bootstrap case above, which has already advanced.
    if promoted is None and pending and advance_is_due(last_advance_at, now):
        promoted, expired = pop_fresh_pending(pending, now)
        dropped.extend(expired)
        queue_dirty = True

    # Two-deep flight history for the poster's current+previous layout. The
    # aircraft leaving the "current" slot - and its resolved state/route -
    # shifts down into "previous". This shift happens on a paced advance
    # rather than on every distinct detection, and the arriving aircraft is
    # the oldest still-fresh queued one, not whatever was detected this
    # instant.
    prior_confirmed_state = current_confirmed_state
    if promoted is not None:
        if current_flight is not None:
            previous_flight = current_flight
            previous_confirmed_state = current_confirmed_state
            previous_route = current_route
        current_flight = promoted
        last_advance_at = now
        queue_dirty = True

    if promoted is not None or refreshed:
        # Runway-configuration inference from the aircraft's own vertical
        # rate, with a deadband and hold-last-state behaviour
        # (server.plane.runway_config). Inference and enrichment both run
        # against the aircraft now occupying the "current" slot, not against
        # `flight` - on a paced cycle those are different aircraft, and
        # every other field on the log line below describes what is
        # displayed.
        confirmed_state = runway_config.infer_from_flight(current_flight, prior_confirmed_state)
        state_source = _classify_state_source(current_flight.get("vertical_rate_fpm"))
        if confirmed_state is None:
            # A first-ever detection whose vertical rate sits inside the
            # deadband - nothing can be concluded yet. Render the Empty
            # state rather than guessing a colour: an unknown runway
            # configuration must not be shown as a confident Blue/Green
            # field.
            render_state = "empty"
            route_source = "n/a"
            route = None
            # This call site displays no flight, so it keeps passing the
            # bare base theme (theme_id, not effective_theme_id) - a
            # calendar match must never reach an empty state.
            # calendar_theme_id is set to None here purely so the shared
            # write block below always has a bound value to persist.
            calendar_theme_id = None
            canvas = render.build_canvas(
                None, render_state, theme_id=theme_id, runway_id=tracked_runway_id,
                source_fault=source_fault, battery_low=battery_low,
            )
        else:
            render_state = confirmed_state
            # Resolve the airline + route via a persistent, callsign-keyed
            # cache - this cache lives in poll_state.json, not in-process,
            # since this script is a systemd oneshot with no memory between
            # invocations.
            cache = poll_state.get("enrichment_cache")
            if not isinstance(cache, dict):
                cache = {}
            # route_source classifies five categories: "fresh_hit"/
            # "cache_hit" mean the cache spared us a request and returned a
            # usable route (a cached miss is still a "miss"); "airline_only"
            # means adsbdb had no route this cycle but the callsign's ICAO
            # prefix identified the carrier from the static in-repo table -
            # no additional network call, no additional cache entry;
            # "manual" means the same, except the carrier was identified via
            # the runtime, operator-writable manual-resolution registry
            # (server.plane.manual_resolutions) instead of the static
            # table - the static table is always consulted first and wins on
            # a collision, so a prefix present in both tables is reported as
            # "airline_only", never "manual". Nothing derived from the
            # adsbdb response body is ever logged, on any of the five paths.
            route, route_source = enrich.resolve_route(current_flight.get("callsign"), cache)
            enrich.trim_cache(cache)
            poll_state["enrichment_cache"] = cache
            # A "miss" means neither adsbdb, the static prefix table, nor
            # the manual registry resolved anything for a shape-valid
            # callsign - exactly "unrecognized ICAO prefix". Record it into
            # the same durable poll_state.json this cycle already writes, so
            # the finding survives this oneshot's process boundary. Never
            # called for "airline_only"/"manual"/"fresh_hit"/"cache_hit" (a
            # source resolved something) or "held"/"n/a" (no enrichment ran
            # this cycle).
            unresolved_prefixes = poll_state.get("unresolved_prefixes")
            if not isinstance(unresolved_prefixes, dict):
                unresolved_prefixes = {}
            # Unconditionally clear this callsign's prefix from the gap
            # registry if it now resolves, before the miss-recording branch
            # below and before trim_unresolved_prefixes()/the write-back - a
            # deletion after either point would be discarded. Not gated on
            # route_source: route_source describes only this cycle's adsbdb
            # outcome for this one callsign, so gating on it would leave a
            # stale entry uncleaned every time adsbdb happened to answer.
            # The helper below does its own resolvability check via
            # airline_from_callsign().
            enrich.clear_resolved_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
            if route_source == "miss":
                unknown_prefix = enrich.note_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
            enrich.trim_unresolved_prefixes(unresolved_prefixes)
            poll_state["unresolved_prefixes"] = unresolved_prefixes
            # A real hex/confirmed_state/corroborated transition, computed
            # before poll_state's last_recorded_* keys are overwritten below
            # with this cycle's own values.
            #
            # Keyed on `current_flight` (what reached the display), not on
            # `flight` (what this cycle detected) - those are different
            # aircraft on a paced cycle, and `flight` can even be None here
            # since this branch is reached whenever the queue drains,
            # including on a cycle that detected nothing. `confirmed_state`
            # and `route` below are both derived from `current_flight`, so
            # recording `flight` would write a runway_events row whose hex
            # and route describe two different aircraft.
            event_recorded = _should_record_event(current_flight, confirmed_state, poll_state)
            poll_state["last_recorded_hex"] = current_flight.get("hex")
            poll_state["last_recorded_confirmed_state"] = confirmed_state
            poll_state["last_recorded_corroborated"] = current_flight.get("corroborated")
            # The previous flight's own real illustration/text rides along
            # on the same panel as the current detection's.
            #
            # This is the flight-detected branch's confirmed-state render -
            # the invariant this pair exists to hold is that the same
            # flight, drawn again from `current_route` on a later cycle's
            # battery-icon/source-fault repaint (the held branch below),
            # gets the identical effective theme id it got here.
            #
            # This is the single calendar match site, here and nowhere else,
            # because this is the first point where all five of
            # match_calendar_theme's inputs are settled - the route has been
            # enriched, the render state is confirmed, and the flight has
            # survived the pacing/promotion logic. The held/repaint branch
            # below must NOT call this function again - it reuses the
            # persisted value read into current_calendar_theme_id above, for
            # the reason given at that branch's own call site.
            calendar_theme_id = calendar_rules.match_calendar_theme(
                calendar_registry, route, render_state, device_cfg, now_s())
            effective_theme_id = colour_rules.resolve_effective_theme_id(
                render_state, current_flight, device_cfg,
                calendar_theme_id=calendar_theme_id)
            canvas = render.build_canvas(
                current_flight,
                render_state,
                route=route,
                previous_flight=previous_flight,
                previous_route=previous_route,
                previous_state=previous_confirmed_state,
                theme_id=effective_theme_id,
                runway_id=tracked_runway_id,
                source_fault=source_fault,
                battery_low=battery_low,
            )
        rendered = panel_format.pack_panel(canvas)
        panel_changed = write_panel_atomic(state_dir, rendered)
        if panel_changed:
            _save_to_gallery(state_dir, canvas, now_iso)
        poll_state["last_flight"] = current_flight
        poll_state["last_confirmed_state"] = confirmed_state
        poll_state["last_route"] = route
        # Written on the same lines as last_flight/last_route immediately
        # above, in the same block, so the stored calendar value and the
        # stored route can never drift apart and describe two different
        # aircraft.
        poll_state["last_calendar_theme_id"] = calendar_theme_id
        poll_state["previous_flight"] = previous_flight
        poll_state["previous_confirmed_state"] = previous_confirmed_state
        poll_state["previous_route"] = previous_route
        poll_state["pending_flights"] = pending
        poll_state["last_advance_at"] = last_advance_at
        save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, current_flight, confirmed_state, route_source, route,
            tracked_runway_id, source_fault, event_recorded, now_iso,
            caddy_log=caddy_log, wake_interval_s=effective_wake_interval_s,
        )
    elif current_flight is not None:
        # Nothing new reached the display this cycle, but a flight was
        # already on screen - do nothing to panel.bin. No waiting state, no
        # expiry. Two ways to arrive here: nothing was detected at all, or
        # something was detected but is waiting its turn in the pending
        # queue. Both hold the panel, which is exactly the point - the
        # device is still mid-redraw on what it last fetched.
        confirmed_state = current_confirmed_state
        render_state = confirmed_state if confirmed_state is not None else "empty"
        state_source = "held"
        route_source = "held"
        panel_changed = False
        # Two independent things can change while the panel is otherwise
        # held, and both must be able to reach the glass from this branch:
        # the source-fault badge and the battery-low icon. They are folded
        # into one guarded re-render because they draw onto the same
        # canvas - re-rendering twice would write the panel twice for a
        # single cycle.
        #
        # Gated strictly on a transition of either flag, never on either
        # flag's value, so a persistent outage or a persistently flat
        # battery does not force a full-panel refresh every 30-second cycle
        # - a full e-ink refresh measures ~31.5s on this panel, so
        # refreshing every cycle would keep the display in permanent
        # refresh and burn battery for no added information.
        #
        # This stays compatible for a source-fault/battery transition: the
        # only pixels that can differ there are the badge and the icon. It
        # does not invent a waiting state, expire the held flight, or alter
        # any flight-derived pixel.
        #
        # That "only the badge and icon differ" property is NOT true on a
        # hold-exit cycle (hold_exited below). `panel.bin` currently holds
        # whichever held screen the early-return branch above last drew, and
        # this branch's whole purpose is otherwise to NOT repaint. Without
        # this term, a frame whose last detection predates the hold would
        # keep serving the held image for as long as the hold lasted. Forcing
        # one repaint here is "the first normal poll after the device wakes
        # renders the real, live board directly": no new transition state is
        # invented, the branch simply re-renders what it would already have
        # been showing.
        if source_fault != previous_source_fault or battery_changed or hold_exited:
            if confirmed_state is not None:
                # The same flight is being drawn again from `current_route`
                # on this battery-icon/source-fault repaint - it must get
                # the identical effective theme id it got on the cycle that
                # first displayed it (the flight-detected branch above).
                #
                # `calendar_theme_id` here is `current_calendar_theme_id`,
                # the value read from poll_state above, never a fresh call
                # to match_calendar_theme(): the calendar match is the first
                # resolver input that is a function of the clock, so
                # recomputing it here would let a repaint that happens hours
                # after the flight was first displayed fall outside the
                # calendar entry's own time window and silently change the
                # panel's colour. Reusing the persisted value makes the
                # both-branches invariant hold by construction, the same
                # choice this branch already makes for `current_route`,
                # which it reuses rather than re-enriching.
                effective_theme_id = colour_rules.resolve_effective_theme_id(
                    render_state, current_flight, device_cfg,
                    calendar_theme_id=current_calendar_theme_id)
                held_canvas = render.build_canvas(
                    current_flight,
                    render_state,
                    route=current_route,
                    previous_flight=previous_flight,
                    previous_route=previous_route,
                    previous_state=previous_confirmed_state,
                    theme_id=effective_theme_id,
                    runway_id=tracked_runway_id,
                    source_fault=source_fault,
                    battery_low=battery_low,
                )
            else:
                held_canvas = render.build_canvas(
                    None, "empty", theme_id=theme_id, runway_id=tracked_runway_id,
                    source_fault=source_fault, battery_low=battery_low,
                )
            rerendered = panel_format.pack_panel(held_canvas)
            panel_changed = write_panel_atomic(state_dir, rerendered)
            if panel_changed:
                _save_to_gallery(state_dir, held_canvas, now_iso)
        if queue_dirty:
            # Nothing displayed changed, but the queue did, and this script
            # has no memory across invocations - an unpersisted enqueue
            # would be lost the instant this process exits, silently
            # disabling the whole mitigation.
            poll_state["pending_flights"] = pending
            poll_state["last_advance_at"] = last_advance_at
        if battery_changed or queue_dirty or hold_exited:
            save_poll_state(state_dir, poll_state)
        # Every cycle through this branch, transition or not, still records
        # the per-cycle pipeline-run + source-fault meta signals - nothing
        # reached the display this cycle, so no runway_events row
        # (record_event=False) and no last-detection timestamp update.
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log, wake_interval_s=effective_wake_interval_s,
        )
    else:
        # Nothing detected, and nothing has ever been detected since the
        # state directory was last empty - render the Empty state.
        confirmed_state = None
        render_state = "empty"
        state_source = "held"
        route_source = "n/a"
        canvas = render.build_canvas(
            None, render_state, theme_id=theme_id, runway_id=tracked_runway_id,
            source_fault=source_fault, battery_low=battery_low,
        )
        rendered = panel_format.pack_panel(canvas)
        panel_changed = write_panel_atomic(state_dir, rendered)
        if panel_changed:
            _save_to_gallery(state_dir, canvas, now_iso)
        # The flight-detected branch above always calls save_poll_state()
        # unconditionally; this branch otherwise never does, so the
        # hysteresis memory would not survive this oneshot's process
        # boundary on a frame that has never seen an aircraft. hold_exited
        # is included so the cleared latch also survives.
        if battery_changed or hold_exited:
            save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log, wake_interval_s=effective_wake_interval_s,
        )

    # The shared call site for the frame-silence transition check, common
    # to all three branches above. The early-return hold branch further up
    # has its own separate call site immediately after its own
    # `_record_history()` call, for the identical reason this one exists
    # here - a display_off/quiet_hours hold has no scheduled end, so a
    # frame that dies mid-hold must still be reported. Placed here,
    # deliberately after every branch's own `_record_history()` call, so
    # this cycle's Caddy-log-ingested check-in row (when configured) has
    # already committed and is visible to
    # `history_db.latest_device_health()` - a frame that just checked in
    # this cycle can never be reported silent. Persisted unconditionally
    # right after, since the hook may have mutated poll_state and that
    # mutation must survive this oneshot's process boundary.
    try:
        with history_db.open_db(state_dir) as conn:
            _notify_silence_transition(state_dir, poll_state, conn, device_cfg)
    except (sqlite3.Error, OSError) as exc:
        # The same containment shape as `_record_history()` above: opening
        # history.db can fail for the identical reasons (a lock, a
        # permissions error, a missing directory) - the poll cycle must not
        # die on it.
        print("poll_loop: silence-transition history read failed: %s: %s" % (type(exc).__name__, exc))
    save_poll_state(state_dir, poll_state)

    # Logs only this project's own selected-aircraft records and device
    # telemetry - the callsign, the enrichment outcome, the corroboration
    # flag, theme/tracked_runway/source_fault, and the pacing fields below -
    # never a third-party response body, and never the raw battery
    # millivolt reading.
    #
    # `hex=` is still THIS CYCLE'S DETECTION, not what is displayed, so a
    # suppressed cycle still logs `hex=None ... panel_changed=False`,
    # byte-identical to a genuinely empty sky. What is displayed is named
    # separately:
    #   shown=   the hex now occupying the "current" display slot
    #   pending= how many distinct aircraft are waiting their turn
    #   dropped= hexes discarded this cycle, past the staleness bound or
    #            evicted by the depth cap - the residual loss this pacing
    #            mitigation still cannot show.
    print(
        "poll_loop: hex=%s callsign=%s aircraft_type=%s corroborated=%s altitude_ft=%s confirmed_state=%s "
        "render_state=%s state_source=%s route_source=%s unknown_prefix=%s shown=%s pending=%d dropped=%s "
        "battery_low=%s panel_changed=%s theme=%s effective_theme=%s tracked_runway=%s source_fault=%s hold_exited=%s"
        % (
            (flight or {}).get("hex"),
            (flight or {}).get("callsign"),
            (flight or {}).get("aircraft_type"),
            (flight or {}).get("corroborated"),
            (flight or {}).get("altitude_ft"),
            confirmed_state,
            render_state,
            state_source,
            route_source,
            unknown_prefix,
            (current_flight or {}).get("hex"),
            len(pending),
            ",".join(str(h) for h in dropped) if dropped else None,
            battery_low,
            panel_changed,
            theme_id,
            effective_theme_id,
            tracked_runway_id,
            source_fault,
            hold_exited,
        )
    )

    return {
        "flight": flight,
        "state": render_state,
        "panel_changed": panel_changed,
        "theme": theme_id,
        # The base theme on any cycle that displayed no flight (unchanged
        # from the default assignment above); the resolved id on any cycle
        # that displayed one. `theme` keeps meaning the configured base
        # theme; `effective_theme` is what actually reached the glass.
        "effective_theme": effective_theme_id,
        "tracked_runway": tracked_runway_id,
        "source_fault": source_fault,
        "event_recorded": event_recorded,
    }


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit. This script is always single-cycle "
             "(a systemd timer, added in plan 02-05, drives the 30s repeat cadence) - "
             "accepted for explicitness at the CLI.",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Directory holding panel.bin / poll_state.json (default: server/state/).",
    )
    parser.add_argument(
        "--geofence",
        default=None,
        help="Path to the geofence JSON (default: adsb-test/runway3.json).",
    )
    parser.add_argument(
        "--caddy-log",
        default=None,
        help="Path to Caddy's durable device-protocol access log "
             "(SKYPANE_CADDY_ACCESS_LOG in skypane.env), tailed every cycle "
             "for CFG-03's X-Battery-Mv telemetry. Omit to skip ingestion.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        run_once(state_dir=args.state_dir, geofence=args.geofence, caddy_log=args.caddy_log)
    except Exception as exc:
        # A failed cycle must leave the previously served panel intact and
        # never crash-loop the systemd timer silently - log to stdout
        # (journald captures this) and exit non-zero.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
