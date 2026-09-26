#!/usr/bin/env python3
"""The systemd-timer oneshot entrypoint: detect -> render -> atomic swap.

Poll cadence: 30 seconds, inside both aggregators' 1 req/s limit. No
in-process loop - a systemd `.timer`/`.service` unit pair drives the
cadence by invoking this repeatedly.

No in-process memory between invocations: cross-cycle state lives in
`<state_dir>/poll_state.json` (written through server/atomic_io.py's
same-directory-mkstemp-then-os.replace(), so this process and a
concurrent companion/app.py trigger can never collide on one fixed temp
name); malformed state degrades to empty, never a crash.
`<state_dir>/battery_state.json` is a second, read-only input owned
exclusively by stub-server/byos_server.py.

Display pacing: the frame can't redraw as fast as this server polls, so a
distinct new detection is queued rather than shown immediately, and the
"current" slot advances no faster than the device's measured redraw floor
- a mitigation, not a cure: a severe burst can still overflow the queue
and lose flights.

Usage:
    server/.venv/bin/python3 server/poll_loop.py --once
    server/.venv/bin/python3 server/poll_loop.py --once --state-dir /tmp/x
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timezone

# Allow both `import server.poll_loop` and direct script execution:
# sys.path[0] is server/ itself when run directly.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import server.atomic_io as atomic_io
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
# MIN_ADVANCE_INTERVAL_S is the device's physical redraw floor: 60s
# (firmware Kconfig FP_MIN_REFRESH_SPACING_S default) + ~31.5s (measured
# full Spectra 6 refresh) = 91.5s, rounded down to 90 so the server paces
# slightly ahead of the device.
MIN_ADVANCE_INTERVAL_S = 90

# Hard staleness bound: a queued aircraft older than this is discarded
# rather than shown as stale. 150s trades "never drop a flight" against
# "never show anything stale".
MAX_STALENESS_S = 150

# Depth backstop, independent of MAX_STALENESS_S, against a pathological
# burst piling up entries between two advances: at most 150/30 = 5
# aircraft can legitimately queue inside one staleness window.
MAX_PENDING_FLIGHTS = 5

# --- Cross-process poll-cycle lock ------------------------------------------
#
# poll.lock serialises run_once() across every process that shares
# state_dir: the systemd oneshot (main()) and the companion's POST
# /poll-now both go through poll_cycle_lock() below. A normal cycle takes
# a few seconds; POLL_LOCK_WAIT_S=10 plus a worst-case cycle (every
# upstream at its own bounded deadline) stays comfortably under the
# systemd unit's TimeoutStartSec=90s.
POLL_LOCK_FILENAME = "poll.lock"
POLL_LOCK_WAIT_S = 10.0


class PollBusy(RuntimeError):
    """Raised when another process (or thread) holds poll.lock past the
    caller's own wait budget. The companion's lock_timeout_s=0 fast path
    catches this to answer the existing "already running" flash without
    ever blocking a request thread; the systemd oneshot waits up to
    POLL_LOCK_WAIT_S, then fails the cycle cleanly (main() prints this
    exception's message and returns 1).
    """

    def __init__(self, lock_path, waited_s):
        self.lock_path = lock_path
        self.waited_s = waited_s
        super().__init__(
            "poll_loop: another poll cycle holds %s; this cycle was skipped after %s s"
            % (lock_path, waited_s)
        )


@contextlib.contextmanager
def poll_cycle_lock(state_dir, timeout_s=None):
    """Serialises a poll cycle across every process sharing `state_dir`.
    `timeout_s=None` (the systemd oneshot's default) waits up to
    POLL_LOCK_WAIT_S; `timeout_s=0` (the companion's non-blocking fast
    path) raises PollBusy at once rather than ever blocking a request
    thread; any other value waits up to that many seconds. Read from the
    module global at call time (not a default-argument value), so a test
    that monkeypatches POLL_LOCK_WAIT_S is honoured. Translates
    atomic_io.LockBusy into the poll-cycle-specific PollBusy, so a caller
    need not import atomic_io just to catch this.
    """
    if timeout_s is None:
        timeout_s = POLL_LOCK_WAIT_S
    os.makedirs(state_dir, exist_ok=True)
    lock_path = os.path.join(state_dir, POLL_LOCK_FILENAME)
    try:
        with atomic_io.exclusive_lock(lock_path, timeout_s, blocking=timeout_s != 0):
            yield
    except atomic_io.LockBusy as exc:
        raise PollBusy(lock_path, timeout_s) from exc


def now_s():
    """Wall-clock epoch seconds, injectable so tests can drive cadence
    without sleeping through real 90s windows.
    """
    return time.time()


def _as_timestamp(value):
    """A persisted timestamp as a float, or None if missing/not a real
    number (bools rejected explicitly). Never raises.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def normalise_pending(value):
    """Coerce poll_state.json's "pending_flights" into a list of
    `{"flight": dict, "first_seen": float}` entries, dropping anything
    malformed rather than raising.
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
    """May the "current" display slot advance on this cycle? No recorded
    advance, or a negative elapsed time (clock stepped backwards), both
    read as due.
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
    """Append `flight` to the pending queue; return hexes evicted by the
    depth cap. Re-detecting an already-queued aircraft refreshes its
    record but leaves `first_seen` untouched (it measures wait time, and
    must not be reset by re-detection). Eviction is oldest-first.
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
    """Pop the oldest still-fresh entry (FIFO), dropping any entry that
    exceeded `max_staleness_s` on the way. Returns `(flight_or_None,
    dropped_hexes)`; mutates `pending` in place. A negative age (clock
    step) reads as fresh - the safe direction.
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


# Battery-low hysteresis, raw millivolts - never a derived percentage,
# since no real discharge curve exists for this pack. THRESHOLD_MV=3500
# sits with margin above hardware/logtools.py's --cutoff-mv 3400;
# CLEAR_MV=3600 is a 100 mV re-arm buffer against flapping.
BATTERY_LOW_THRESHOLD_MV = 3500
BATTERY_LOW_CLEAR_MV = 3600

# BATTERY EMPTY hysteresis, raw millivolts, sourced from a measured
# discharge run (~3500 mV at ~43h remaining, 2960 mV ~17 min before the
# panel froze). CRITICAL_MV=3300 sits below the 3500 mV badge and above
# the 2960 mV failure point; RECOVER_MV=3700 is a wider 400 mV re-arm
# buffer than the badge's, since a false recovery risks dying mid-refresh.
BATTERY_CRITICAL_MV = 3300
BATTERY_CRITICAL_RECOVER_MV = 3700


def _extract_aircraft(snapshot):
    """A raw aggregator response's aircraft array, under a provider-specific
    key ("ac" or "aircraft"). Never raises; [] on any unexpected shape.
    """
    if not isinstance(snapshot, dict):
        return []
    for key in ("ac", "aircraft"):
        value = snapshot.get(key)
        if isinstance(value, list):
            return value
    return []


def _classify_state_source(vertical_rate_fpm):
    """Log-only: was this cycle's state newly inferred from a vertical-rate
    reading that crossed a threshold, or held over (deadband/missing/
    non-numeric)?
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


# Tri-valued hold-state latch; `None` means not holding. A single key
# keeps "already holding?" the single test `was_hold is None` for any
# number of hold mechanisms.
_HOLD_KINDS = ("quiet_hours", "display_off", "battery_empty")


def _hold_state(poll_state):
    """The current hold kind, or `None` when not holding. Falls back to
    the legacy `quiet_hours_active` boolean when `hold_state` is absent
    (an older poll_state.json); the caller retires that key on its next
    write. Never raises.
    """
    if "hold_state" in poll_state:
        kind = poll_state.get("hold_state")
        return kind if kind in _HOLD_KINDS else None
    return "quiet_hours" if poll_state.get("quiet_hours_active") is True else None


def load_battery_state(state_dir):
    """Read-only: `<state_dir>/battery_state.json` is owned and written
    exclusively by stub-server/byos_server.py's save_battery_state().
    Returns the int `battery_mv` reading, or None on any failure (missing
    file, invalid JSON, wrong type, non-positive). Never raises.
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
    """Pure function: the battery-low decision, hysteresis between
    BATTERY_LOW_THRESHOLD_MV (3500) and BATTERY_LOW_CLEAR_MV (3600).
    `battery_mv=None` returns `was_active` unchanged. A reading strictly
    between the two constants holds the previous decision either way.
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV


def apply_battery_critical_hysteresis(battery_mv, was_active):
    """Pure function: the BATTERY EMPTY latch decision - the identical
    shape as `apply_battery_hysteresis()` above, applied to the park/hold
    decision, with hysteresis between BATTERY_CRITICAL_MV (3300) and
    BATTERY_CRITICAL_RECOVER_MV (3700).
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_CRITICAL_RECOVER_MV
    return battery_mv <= BATTERY_CRITICAL_MV


# The shared "notifications" sub-dict of poll_state.json and its two
# never-raising transition hooks below: each sends at most one push per
# genuine transition and records the reported state regardless of send
# success, so a flapping endpoint can't turn one transition into a push
# every cycle.

# Duplicated (not imported) from companion/battery.py's identical
# BATTERY_DISCHARGE_CURVE/battery_percent(), since this module must never
# import companion/. companion/test_companion_app.py pins the two copies
# equal.
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
    non-positive or NaN reading. Mirrors companion/battery.py's
    battery_fraction() + battery_percent(). Never raises.
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
    """A short "2 h"-shaped duration string, floored at 0 so a negative age
    (clock skew) never reads as "in the future".
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
    """An ISO-8601 string to epoch seconds, or None if unparsable. A
    timezone-naive value is stamped UTC first. Never raises.
    """
    try:
        parsed = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _notifications_group(device_cfg):
    """The `notifications` sub-dict off `device_cfg`, or None. Never
    raises.
    """
    if not isinstance(device_cfg, dict):
        return None
    notifications = device_cfg.get("notifications")
    return notifications if isinstance(notifications, dict) else None


def _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg, sender=None):
    """Push exactly one notification per genuine battery-low transition,
    gated on the caller's own `battery_changed`. A no-op when the group
    has no `topic_url` or `battery_low` is off. Never raises: any
    exception is logged by type name and swallowed. `state_dir` is
    unused, kept for signature symmetry with `_notify_silence_transition()`.
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
    the same staleness threshold the Health page displays
    (`wake.device_staleness_thresholds()`'s WARN value). A no-op when the
    group has no `topic_url`, `frame_silent` is off, or there's no
    check-in row yet.

    Must be called only after this cycle's own `_record_history()` call
    has committed, so a frame that just checked in can't be reported
    silent before that fresh row is visible. Never raises.
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
        # Same critical-aware mirror run_once() feeds into
        # effective_wake_interval_s - without it, a parked frame would
        # cross the warn threshold on its short pre-park cadence and raise
        # a false push every hour it stays parked.
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
    """Atomic same-directory-mkstemp-then-os.replace() via atomic_io, so two
    processes writing this same path (the systemd oneshot and the
    companion's POST /poll-now, both under poll_cycle_lock()) can never
    collide on one fixed temp name. Never leaves a stray temp file behind,
    even if the write itself fails.
    """
    atomic_io.atomic_write(_poll_state_path(state_dir), json.dumps(state, indent=1))


def write_panel_atomic(state_dir, rendered):
    """Write `rendered` (packed panel bytes) to <state_dir>/panel.bin only if
    its SHA-256 differs from the currently-served bytes - a same-directory-
    mkstemp-then-os.replace() via atomic_io, so byos_server.py can never
    serve a half-written file and two writers can never collide on one
    fixed temp name. Returns True if the served panel actually changed.
    """
    panel_path = os.path.join(state_dir, "panel.bin")
    if os.path.exists(panel_path):
        with open(panel_path, "rb") as fh:
            existing = fh.read()
        if hashlib.sha256(existing).hexdigest() == hashlib.sha256(rendered).hexdigest():
            return False

    atomic_io.atomic_write(panel_path, rendered)
    return True


def _classify_source_fault(diagnostics):
    """True only when every ADS-B provider this cycle queried failed
    outright - never merely because providers found nothing on the
    runway (both cases return a `None` selection from
    `detect.poll_current_aircraft()`, so this is the only place that
    distinguishes them). `diagnostics=None` (the injected-snapshot test
    branch never queries) classifies as "no fault", not "unknown".
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
    `history.db`'s meta table - not `poll_state.json`, to avoid a second
    writer race. A missing database or any read failure resolves to
    `False`, never raises.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            value = history_db.get_meta(conn, history_db.META_SOURCE_FAULT)
    except (sqlite3.Error, OSError) as exc:
        print("poll_loop: could not read source_fault meta: %s: %s" % (type(exc).__name__, exc))
        return False
    return value == "True"


def _should_record_event(flight, confirmed_state, poll_state):
    """True only on a real transition - hex, confirmed state, or
    corroboration differs from what `poll_state["last_recorded_*"]` last
    saw - never on an unchanged repeat detection (writing a row every
    30s cycle would produce ~a million rows/year for no new information).
    """
    last_hex = poll_state.get("last_recorded_hex")
    last_confirmed = poll_state.get("last_recorded_confirmed_state")
    last_corroborated = poll_state.get("last_recorded_corroborated")
    hex_ = flight.get("hex") if isinstance(flight, dict) else None
    corroborated = flight.get("corroborated") if isinstance(flight, dict) else None
    return hex_ != last_hex or confirmed_state != last_confirmed or corroborated != last_corroborated


# Sentinel for "no epoch to record" - can't be None, since None is a
# legitimate effective wake interval ("cadence undetermined") worth
# recording in its own right.
_NO_WAKE_EPOCH = object()


def _record_history(state_dir, flight, confirmed_state, route_source, route, tracked_runway_id, source_fault, record_event, now_iso, caddy_log=None, wake_interval_s=_NO_WAKE_EPOCH, detected=False):
    """Write this cycle's durable signals into `history.db`, in one
    connection: a database/filesystem failure is caught and logged, never
    allowed to fail the poll cycle - history is an accessory to the
    panel, not a dependency of it.

    `record_event` gates the one thing not written every cycle: a
    `runway_events` row, on a real transition only. The pipeline-run
    timestamp, source-fault flag, and last-detection timestamp go to the
    fixed-size `meta` table every cycle regardless, so they never grow
    the database. `caddy_log`, when given, ingests new Caddy access-log
    lines. `wake_interval_s` records a `wake_epochs` row only when it
    differs from the newest one stored.

    `detected` covers the one case `flight is not None` alone misses: a
    cycle that detected an aircraft but only queued it (the held branch
    passes `flight=None` - nothing new reached the display - while the
    queue this cycle enqueued is a real detection in its own right). The
    last-detection timestamp advances on either signal, so "Last aircraft
    detected" never lags behind a genuinely queued sighting.
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
            if flight is not None or detected:
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
    lexical (= chronological, via ISO-8601 filenames) sort order. Never
    raises.
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
    called, `panel.bin` has already been written. The PNG is encoded into
    memory first, then published through atomic_io.atomic_write() (a
    same-directory-mkstemp-then-os.replace()), so a reader can never see a
    half-written gallery file and a failed encode/write leaves no temp
    file behind.
    """
    try:
        gallery_dir = _gallery_dir(state_dir)
        os.makedirs(gallery_dir, exist_ok=True)
        safe_name = now_iso.replace(":", "-") + ".png"
        buffer = io.BytesIO()
        canvas.convert("RGB").save(buffer, format="PNG")
        atomic_io.atomic_write(os.path.join(gallery_dir, safe_name), buffer.getvalue())
        _prune_gallery(gallery_dir)
    except Exception as exc:
        print("poll_loop: gallery archive failed: %s: %s" % (type(exc).__name__, exc))


def run_once(snapshot=None, state_dir=None, geofence=None, caddy_log=None, lock_timeout_s=None):
    """One poll cycle, serialised across every process that shares
    `state_dir` by `poll_cycle_lock()`: the lock is held for the cycle's
    whole body, acquired before any state read. `lock_timeout_s`
    is passed straight through to `poll_cycle_lock()` - `None` (the
    systemd oneshot's default) waits up to `POLL_LOCK_WAIT_S`; `0` (the
    companion's POST /poll-now) raises `PollBusy` at once rather than
    ever blocking a request thread. See `_run_once_locked()` for the
    cycle itself.
    """
    state_dir = state_dir or DEFAULT_STATE_DIR
    with poll_cycle_lock(state_dir, lock_timeout_s):
        return _run_once_locked(
            snapshot=snapshot, state_dir=state_dir, geofence=geofence, caddy_log=caddy_log)


def _run_once_locked(snapshot=None, state_dir=None, geofence=None, caddy_log=None):
    """The poll cycle itself, called by `run_once()` only while
    `poll_cycle_lock()` is held. `snapshot=None` polls the live
    aggregators; a non-None `snapshot` is a raw aggregator response dict
    injected by tests (no live network call).

    Returns {"flight", "state", "panel_changed", "theme",
    "effective_theme", "tracked_runway", "source_fault",
    "event_recorded"}. `flight` is what this cycle detected, not
    necessarily what it displayed (see "Display pacing" module note) -
    read poll_state.json's "last_flight" for what's actually on the
    panel. `effective_theme` equals `theme` on a no-flight cycle, else the
    colour_rules-resolved id. Everything derived from the display (render,
    enrichment, history row) is keyed on the displayed aircraft, never on
    this cycle's raw detection.

    Hold states: a quiet-hours window and the manual display-off toggle
    both gate through one shared `poll_state["hold_state"]` latch
    (`_hold_state()`). Either active takes an early return before any
    ADS-B call - a hold suppresses detection entirely, not just display.
    "Render once at entry, then hold": the held screen draws once, on the
    first cycle a hold starts, and every subsequent held cycle is a
    no-op. `display_enabled=False` wins over a standing quiet-hours
    window on what the panel shows; the opposite resolution (longest
    sleep wins) governs only how long the device sleeps, in
    stub-server/byos_server.py. The first cycle after all holds clear
    forces one repaint of the live board.
    """
    state_dir = state_dir or DEFAULT_STATE_DIR
    os.makedirs(state_dir, exist_ok=True)

    # Configure the illustration override resolver and manual-resolution
    # registry from THIS cycle's state_dir, here rather than in main() -
    # run_once() is the single entry point both the systemd oneshot and
    # companion/app.py's POST /poll-now trigger go through. Reloaded once
    # per cycle so a companion-side save landing mid-cycle can't split one
    # cycle across two registries (a manual resolution reaches the glass
    # at the next wake, never instantly).
    illustrations.set_override_state_dir(state_dir)
    manual_resolutions.set_manual_registry_state_dir(state_dir)
    # Same per-cycle priming for the colour-rule registry cache. The
    # resolver itself is not called here - render_state and current_flight
    # aren't settled yet.
    colour_rules.set_colour_rules_state_dir(state_dir)

    # The calendar refresh is its own distinct step (may open a socket,
    # unlike the JSON-only priming above). Safe unconditionally:
    # refresh_calendar_registry() makes no transport call when unconfigured
    # or throttled, one bounded call otherwise, and never raises.
    _, calendar_registry = calendar_rules.refresh_calendar_registry(state_dir, now_s())

    # Read the user's saved theme + tracked runway once per cycle - a
    # mid-cycle save landing between two reads is how a panel ends up
    # rendered half in one config and half in another.
    device_cfg = device_config.load_device_config(state_dir)
    theme_id = device_cfg["theme"]
    # poll_state.json/battery_state.json read once here; every branch
    # below reuses these objects rather than re-reading. One battery read
    # feeds three decisions: the badge, the BATTERY EMPTY latch, and (via
    # that latch) the wake-interval pin below.
    poll_state = load_poll_state(state_dir)
    battery_mv = load_battery_state(state_dir)
    # Stored back into poll_state immediately, before
    # wake.effective_wake_interval_s() below, so it sees this cycle's own
    # decision, not last cycle's stale one.
    was_battery_critical = poll_state.get(wake.BATTERY_CRITICAL_STATE_KEY) is True
    battery_critical = apply_battery_critical_hysteresis(battery_mv, was_battery_critical)
    poll_state[wake.BATTERY_CRITICAL_STATE_KEY] = battery_critical
    # The cadence in force this cycle, resolved once and passed to every
    # _record_history() call rather than re-resolved. None is a legitimate
    # "cannot be determined" value. See wake.effective_wake_interval_s()'s
    # own docstring for the battery_critical precedence.
    effective_wake_interval_s = wake.effective_wake_interval_s(device_cfg, battery_critical=battery_critical)
    # Default assignment, not a resolution: render_state/current_flight
    # aren't settled yet, so the colour_rules/calendar resolvers can't run
    # here without either raising or resolving against stale values. Both
    # are computed at the flight-detected branch's resolver call site
    # below.
    effective_theme_id = theme_id
    tracked_runway_id = device_cfg["tracked_runway"]
    # now_s(), not datetime.now(): this module's harness-replaceable clock
    # seam, so the test harness's fake clock drives this arithmetic too.
    quiet_remaining, quiet_until = device_config.quiet_hours_status(device_cfg, now_s())
    # The operator's display toggle wins over a standing quiet-hours
    # window on what the panel shows (checked first below) - the
    # sleep-duration axis resolves the opposite way, in
    # stub-server/byos_server.py, not here.
    display_enabled = device_cfg["display_enabled"]
    # Priority: battery_empty > display_off > quiet_hours. A flat pack
    # overrides everything else - it doesn't matter what was configured if
    # the device is about to lose power mid-refresh.
    if battery_critical:
        hold_kind = "battery_empty"
    elif not display_enabled:
        hold_kind = "display_off"
    elif quiet_remaining is not None:
        hold_kind = "quiet_hours"
    else:
        hold_kind = None

    if hold_kind is not None:
        # Early return before detect.load_geofence()/poll_current_aircraft():
        # inside a hold, this cycle must not touch `detect` at all, or an
        # off period (no scheduled end) would query the aggregators
        # unbounded. poll_state/battery_mv reused from above so this
        # branch's battery_low decision can't observe a different mV
        # reading than the top-level battery_critical one.
        was_hold = _hold_state(poll_state)
        legacy_present = "quiet_hours_active" in poll_state

        # Same battery decision the main path computes below - the held
        # screen carries the same battery-low icon.
        was_battery_low = bool(poll_state.get("battery_low_active", False))
        battery_low = apply_battery_hysteresis(battery_mv, was_battery_low)
        battery_changed = battery_low != was_battery_low
        poll_state["battery_low_active"] = battery_low
        if battery_changed:
            _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg)

        # No provider was queried this cycle - carry the previous fault
        # flag forward rather than inventing or clearing one.
        source_fault = _last_source_fault(state_dir)
        poll_state["hold_state"] = hold_kind
        if legacy_present:
            del poll_state["quiet_hours_active"]
        now_iso = history_db.utc_now_iso()

        # Render on entry into a hold (`was_hold is None`), never merely on
        # `was_hold != hold_kind`, except crossing into/out of BATTERY
        # EMPTY: the device can't fetch anything mid-hold, so re-rendering
        # for no new information wastes the panel. A move between QUIET
        # HOURS and DISPLAY OFF stays silent either way, but entering or
        # recovering from BATTERY EMPTY must repaint, or the parked screen
        # (or its recovery) would never reach the glass.
        battery_empty_boundary_crossed = (was_hold == "battery_empty") != (hold_kind == "battery_empty")
        panel_changed = False
        if was_hold is None or battery_empty_boundary_crossed:
            if hold_kind == "battery_empty":
                # The byte-stable BATTERY EMPTY screen: build_canvas() never
                # consults theme_id/quiet_hours_until/source_fault/
                # battery_low for this state, so none can leak a
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

        # `was_hold != hold_kind` persists a hold-kind change even with
        # nothing rendered; `legacy_present` is the one-time migration
        # flush; `battery_critical_changed` is named explicitly rather than
        # relied on implicitly, so a future priority change can't silently
        # stop persisting this latch's flip.
        battery_critical_changed = battery_critical != was_battery_critical
        if was_hold != hold_kind or battery_changed or legacy_present or battery_critical_changed:
            save_poll_state(state_dir, poll_state)

        # Not optional: advances META_LAST_PIPELINE_RUN, or a long hold
        # would make the companion Health page raise a false staleness
        # anomaly.
        _record_history(
            state_dir, None, None, None, None, tracked_runway_id,
            source_fault, False, now_iso, caddy_log=caddy_log,
            wake_interval_s=effective_wake_interval_s,
        )

        # A display_off hold has no scheduled end, and nothing else here
        # re-checks staleness while it lasts - without this, a frame that
        # dies mid-hold would never raise a frame_silent push. After
        # _record_history() so this cycle's check-in has already
        # committed. Persisted unconditionally after, since the hook may
        # have mutated poll_state["notifications"].
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
            # A hold screen's effective theme IS the base theme - no rule
            # or arrivals override is ever consulted for a hold screen.
            "effective_theme": theme_id,
            "tracked_runway": tracked_runway_id,
            "source_fault": source_fault,
            "event_recorded": False,
        }

    geofence_data = detect.load_geofence(geofence)

    # `diagnostics`, when populated, is the only signal that tells "every
    # source is down" apart from "nothing on the runway" - both otherwise
    # return the same None selection.
    diagnostics = None
    if snapshot is not None:
        aircraft = _extract_aircraft(snapshot)
        flight = detect.select_aircraft_for_runway(aircraft, geofence_data, runway_id=tracked_runway_id)
    else:
        diagnostics = {}
        flight = detect.poll_current_aircraft(geofence_data, runway_id=tracked_runway_id, diagnostics=diagnostics)

    source_fault = _classify_source_fault(diagnostics)
    previous_source_fault = _last_source_fault(state_dir)
    # Shared by every history/gallery write this cycle makes, so they all
    # record the same instant.
    now_iso = history_db.utc_now_iso()

    # Reaching this line means no hold is active any more, so a non-None
    # hold kind here means "first cycle after the last hold ended". Clear
    # it now, and remember the fact in hold_exited so branches that don't
    # unconditionally repaint can force exactly one exit repaint.
    hold_exited = _hold_state(poll_state) is not None
    if hold_exited:
        poll_state["hold_state"] = None
        if "quiet_hours_active" in poll_state:
            del poll_state["quiet_hours_active"]
    current_flight = poll_state.get("last_flight")
    current_confirmed_state = poll_state.get("last_confirmed_state")
    current_route = poll_state.get("last_route")
    # Calendar sibling of current_route: reused, never recomputed, by the
    # held/repaint branch below. Membership-tested against
    # device_config.THEMES so a hand-edited poll_state.json can't smuggle
    # an unregistered theme id onto the panel.
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
    # Defined before any branching - the shared log statement at the
    # bottom needs it even on a cycle that detects nothing.
    unknown_prefix = None
    # Whether this cycle wrote a runway_events row - surfaced so the
    # companion's manual-trigger handler can report it.
    event_recorded = False

    # Battery-low decision, computed before any branching - every branch
    # needs it, to thread into a render call or gate a hold-cycle repaint.
    was_battery_low = bool(poll_state.get("battery_low_active", False))
    battery_low = apply_battery_hysteresis(battery_mv, was_battery_low)
    battery_changed = battery_low != was_battery_low
    poll_state["battery_low_active"] = battery_low
    if battery_changed:
        _notify_battery_transition(state_dir, poll_state, battery_low, battery_mv, device_cfg)

    # --- Display pacing: which detection occupies the "current" slot -------
    #
    # `flight` is what this poll detected, not necessarily what this cycle
    # displays: a distinct new aircraft is queued, and the "current" slot
    # advances no faster than MIN_ADVANCE_INTERVAL_S so the device gets a
    # real chance to fetch and blit each one.
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

    # Drain the queue when the device is due for a redraw, even on a cycle
    # that detected nothing - without draining on quiet cycles, a queued
    # aircraft would sit there until it expired. `promoted is None` guards
    # the bootstrap case above, which has already advanced.
    if promoted is None and pending and advance_is_due(last_advance_at, now):
        promoted, expired = pop_fresh_pending(pending, now)
        dropped.extend(expired)
        queue_dirty = True

    # Two-deep flight history for the poster's current+previous layout: the
    # aircraft leaving "current" shifts into "previous" on a paced advance,
    # not on every distinct detection.
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
        # Runway-configuration inference from vertical rate, with a
        # deadband and hold-last-state behaviour (server.plane.runway_config).
        # Inference and enrichment run against the "current" slot, not
        # `flight` - on a paced cycle those differ.
        confirmed_state = runway_config.infer_from_flight(current_flight, prior_confirmed_state)
        state_source = _classify_state_source(current_flight.get("vertical_rate_fpm"))
        if confirmed_state is None:
            # A first-ever detection inside the deadband: render Empty
            # rather than guess a colour.
            render_state = "empty"
            route_source = "n/a"
            route = None
            # Bare base theme (never effective_theme_id): a calendar match
            # must never reach an empty state. calendar_theme_id stays None
            # only so the shared write block below has a bound value.
            calendar_theme_id = None
            canvas = render.build_canvas(
                None, render_state, theme_id=theme_id, runway_id=tracked_runway_id,
                source_fault=source_fault, battery_low=battery_low,
            )
        else:
            render_state = confirmed_state
            # Callsign-keyed cache lives in poll_state.json, not
            # in-process (no memory between oneshot invocations).
            cache = poll_state.get("enrichment_cache")
            if not isinstance(cache, dict):
                cache = {}
            # route_source: "fresh_hit"/"cache_hit" resolved via adsbdb;
            # "airline_only" via the static ICAO-prefix table (no adsbdb
            # route this cycle); "manual" via the operator-writable
            # registry (only when the static table has no entry - it wins
            # on a collision); "miss" resolved nothing.
            route, route_source = enrich.resolve_route(
                current_flight.get("callsign"), cache, now=now_s())
            enrich.trim_cache(cache)
            poll_state["enrichment_cache"] = cache
            # A "miss" is an unrecognized ICAO prefix - recorded so the
            # finding survives this oneshot's process boundary.
            unresolved_prefixes = poll_state.get("unresolved_prefixes")
            if not isinstance(unresolved_prefixes, dict):
                unresolved_prefixes = {}
            # Clear this prefix from the gap registry unconditionally if it
            # now resolves, before the miss-recording branch below -
            # gating on route_source would leave stale entries uncleaned.
            enrich.clear_resolved_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
            if route_source == "miss":
                unknown_prefix = enrich.note_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
            enrich.trim_unresolved_prefixes(unresolved_prefixes)
            poll_state["unresolved_prefixes"] = unresolved_prefixes
            # A real transition, computed before last_recorded_* is
            # overwritten below. Keyed on `current_flight` (what reached
            # the display), not `flight` - those are different
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
            # The single calendar match site: the first point where all of
            # match_calendar_theme's inputs are settled. The held/repaint
            # branch below must NOT call this again - it reuses the
            # persisted current_calendar_theme_id instead.
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
        # Written in the same block as last_flight/last_route so the
        # calendar value and route can never drift apart.
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
        # already on screen - do nothing to panel.bin. Two ways to arrive
        # here: nothing detected, or something is waiting in the pending
        # queue. Both hold the panel, which is the point - the device is
        # still mid-redraw on what it last fetched.
        confirmed_state = current_confirmed_state
        render_state = confirmed_state if confirmed_state is not None else "empty"
        state_source = "held"
        route_source = "held"
        panel_changed = False
        # The source-fault badge and battery-low icon can still change
        # while otherwise held; folded into one guarded re-render since
        # both draw onto the same canvas. Gated on a TRANSITION of either
        # flag, not its value, so a persistent outage/flat battery doesn't
        # force a refresh every 30s cycle (a full e-ink refresh costs
        # ~31.5s of battery for no new information).
        #
        # hold_exited also forces a repaint here: `panel.bin` may still
        # hold whichever screen the early-return branch last drew, and
        # without this a frame whose last detection predates the hold
        # would keep serving that stale image indefinitely.
        if source_fault != previous_source_fault or battery_changed or hold_exited:
            if confirmed_state is not None:
                # Reuses current_calendar_theme_id (persisted), never a
                # fresh match_calendar_theme() call: that resolver is a
                # function of the clock, so recomputing it here could move
                # a flight outside its calendar window hours after first
                # display, silently changing colour mid-hold.
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
            # has no memory across invocations - unpersisted, an enqueue
            # would be lost the instant this process exits.
            poll_state["pending_flights"] = pending
            poll_state["last_advance_at"] = last_advance_at
        if battery_changed or queue_dirty or hold_exited:
            save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log, wake_interval_s=effective_wake_interval_s,
            # This cycle's own raw detection (`flight`), not what reached
            # the display (`current_flight`, unchanged here) - a distinct
            # aircraft that only got queued is still a real detection.
            detected=flight is not None,
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
        # The flight-detected branch always saves unconditionally; this
        # branch otherwise never would, losing hysteresis memory for a
        # frame that has never seen an aircraft.
        if battery_changed or hold_exited:
            save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log, wake_interval_s=effective_wake_interval_s,
        )

    # Shared call site for the frame-silence check, common to all three
    # branches above (the hold branch has its own, right after its own
    # _record_history()). Placed after every branch's history write so a
    # frame that just checked in this cycle can never be reported silent.
    try:
        with history_db.open_db(state_dir) as conn:
            _notify_silence_transition(state_dir, poll_state, conn, device_cfg)
    except (sqlite3.Error, OSError) as exc:
        print("poll_loop: silence-transition history read failed: %s: %s" % (type(exc).__name__, exc))
    save_poll_state(state_dir, poll_state)

    # Logs only this project's own records/telemetry, never a third-party
    # response body or the raw battery millivolt reading. `hex=` is this
    # cycle's detection, not necessarily what's displayed (`shown=`);
    # `pending=`/`dropped=` report the pacing queue's residual loss.
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
        # The base theme on a no-flight cycle; the resolved id otherwise.
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
    except PollBusy as exc:
        # Distinct from the generic failure below: another process (the
        # companion, or an overlapping timer firing) is mid-cycle, not a
        # cycle that itself failed. No traceback - this is an expected,
        # bounded wait outcome, not a bug.
        print(str(exc))
        return 1
    except Exception as exc:
        # A failed cycle must leave the previously served panel intact and
        # never crash-loop the systemd timer silently - log to stdout
        # (journald captures this) and exit non-zero.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        # journald captures stdout, not this process's own traceback
        # rendering choices - a one-line summary alone leaves no way to
        # tell which line raised without reproducing the failure locally.
        traceback.print_exc(file=sys.stdout)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
