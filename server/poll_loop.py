#!/usr/bin/env python3
"""The systemd-timer oneshot entrypoint: detect -> render -> atomic swap
(PLANE-03, D-04, D-P2-02).

Poll cadence decision: **30 seconds**, matching Phase 1's validated sampler
interval (adsb-test/RESULTS.md) and comfortably inside both aggregators'
1 req/s limit given one call per cycle. This script itself has no
`while True: sleep()` loop and no APScheduler - it is a single-cycle
oneshot invoked repeatedly by a systemd `.timer`/`.service` unit pair; the
timer unit that actually drives the 30s cadence lands in plan 02-05, not
this plan (02-RESEARCH.md's Don't Hand-Roll table).

Cross-cycle state (D-P2-02): this script has no in-process memory between
invocations, so the last detected flight, last chosen state, the pending
display queue (see "Display pacing" below), the unrecognized-ICAO-prefix
registry (quick task 260827-oz9 - journald rotates, the coverage question
does not), and (05-02, DEVICE-04) the hysteretic battery_low_active decision
all live in `<state_dir>/poll_state.json`, written with the same
tmp-write-then-os.replace() pattern stub-server/byos_server.py's
save_state() uses. An unreadable or malformed state file is treated as empty
state, never as a crash.
`<state_dir>/battery_state.json` is a second, read-only input this module
never writes - it is owned and written exclusively by
stub-server/byos_server.py's save_battery_state() (05-RESEARCH.md
Pitfall 4: two processes read-modify-writing one JSON file is a real
lost-update race, and neither unit takes a lock).

Display pacing (mechanism-C mitigation, 2026-08-28 - see
.planning/debug/resolved/missed-flights-not-displayed.md): this server
re-renders every 30s, but the frame physically cannot redraw that fast, so
handing it a new "current" aircraft on every distinct detection silently
overwrote flights the device never got a chance to fetch. Distinct
selections are therefore queued and the "current" slot advances no faster
than the device's own measured redraw floor. This is a MITIGATION, not a
cure: a burst severe enough to overflow the queue's staleness bound or its
depth cap still loses flights - deliberately, because the alternative is an
unbounded queue whose displayed information drifts arbitrarily far behind
reality, which would defeat the point of a real-time departure board.

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
import server.panel_format as panel_format
import server.plane.detect as detect
import server.plane.enrich as enrich
import server.plane.illustrations as illustrations
import server.plane.render as render
import server.plane.runway_config as runway_config

DEFAULT_STATE_DIR = os.path.join(_HERE, "state")
POLL_INTERVAL_S = 30

# CFG-11 (06-RESEARCH.md Pattern 5, Open Question 3): each archived PNG is
# a full 1200x1600 panel image (a few hundred KB) - this cap bounds the
# gallery directory to single-digit megabytes of disk use regardless of how
# long the server has been running.
GALLERY_DIRNAME = "gallery"
GALLERY_MAX_ENTRIES = 25

# --- Display pacing constants (mechanism-C mitigation) ---------------------
#
# MIN_ADVANCE_INTERVAL_S is the device's own physical redraw floor, not a
# preference. It is the sum of two MEASURED firmware numbers, and if either
# ever changes this constant has to be reconciled against them by hand:
#
#   * CONFIG_FP_MIN_REFRESH_SPACING_S = 60 - firmware/main/Kconfig.projbuild,
#     verified NOT overridden in sdkconfig.defaults or sdkconfig.ee02.defaults,
#     so the Kconfig default is what a flashed board actually runs.
#     fp_panel_draw() re-arms this guard after every successful blit, so it is
#     a floor between two DRAWN images, not between two wakes.
#   * ~31.5s for one full 13.3" Spectra 6 refresh - measured twice on the real
#     hardware (hardware/BRINGUP-LOG.md, and quoted in ARCHITECTURE.md's
#     firmware section as a hard constraint any refresh-cadence decision has
#     to budget for).
#
# 60 + 31.5 = 91.5s; rounded down to 90 so the server paces slightly ahead of
# the device rather than slightly behind it. CAVEAT recorded honestly:
# firmware/sdkconfig is generated at build time and is not committed, so a
# menuconfig change on the flashed board would not be visible from this repo.
MIN_ADVANCE_INTERVAL_S = 90

# The hard staleness bound. A queued aircraft whose turn arrives more than
# this many seconds after it was FIRST detected is discarded rather than ever
# reaching the panel: showing it would mislead the viewer about how current
# the board is, and this is a real-time departure board first. Chosen
# deliberately at 2m30s as the tradeoff point between "never drop a flight"
# (an unbounded queue, whose displayed lag grows without limit during any
# sustained busy period) and "never show anything stale".
MAX_STALENESS_S = 150

# Defensive depth backstop, INDEPENDENT of MAX_STALENESS_S. Expired entries
# are only skipped at advance time (up to MIN_ADVANCE_INTERVAL_S apart), so
# without this cap a pathological burst - a systemd catch-up storm after a
# suspend, a hand-run loop, a clock that jumped - could pile up entries
# between two advances. Derivation: a poll selects AT MOST ONE aircraft, and
# the timer fires every POLL_INTERVAL_S=30s, so at most 150/30 = 5 distinct
# aircraft can legitimately be enqueued inside one staleness window. Anything
# beyond that is not real traffic. Revisit this number if POLL_INTERVAL_S is
# ever retuned - it is written as a literal, not as a division, precisely so
# that a cadence change cannot silently inflate the queue.
MAX_PENDING_FLIGHTS = 5


def now_s():
    """Wall-clock epoch seconds, as a module-level seam.

    This script is a systemd oneshot with no in-process memory (D-P2-02), so
    every pacing and staleness decision is arithmetic over timestamps
    persisted in poll_state.json rather than over anything held in RAM. That
    makes the clock an input, and an input has to be injectable: the test
    harness replaces this function to drive cadence deterministically instead
    of sleeping through real 90s windows.

    Epoch seconds (float) rather than the ISO-8601 strings
    enrich.note_unresolved_prefix() persists, because these values are
    arithmetic operands on every cycle, not a human-readable audit record.
    """
    return time.time()


def _as_timestamp(value):
    """Coerce a persisted timestamp to a float, or None if it is missing or
    not a real number. Booleans are rejected explicitly (bool is an int
    subclass in Python), mirroring runway_config.infer_runway_config()'s own
    guard. A hand-edited or older state file must degrade to "no timestamp",
    never raise.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def normalise_pending(value):
    """Coerce whatever poll_state.json holds under "pending_flights" into a
    list of well-shaped `{"flight": dict, "first_seen": float}` entries.

    Anything malformed - a non-list, a non-dict entry, a missing flight, an
    unusable first_seen - is DROPPED rather than raising, the same
    skip/don't-claim discipline load_poll_state() and _extract_aircraft()
    already apply. A state file written before this key existed simply yields
    an empty queue, which is exactly the pre-fix behaviour.
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

    Named and module-level on purpose: it is the single seam that separates
    the paced behaviour from the pre-fix "advance on every distinct
    detection" behaviour, so the regression harness can restore the bug by
    forcing this True and prove its checks actually catch it.

    - No recorded advance yet (fresh state, or a poll_state.json written
      before this key existed) -> due. A migrated state file therefore behaves
      exactly like the pre-fix code on its first new detection, then paces.
    - A negative elapsed time means the recorded stamp is in the FUTURE - an
      NTP step backwards, or a hand-edited file. Treated as due rather than
      as a wait, because the alternative is stalling the display for the whole
      duration of the jump.
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
    """Append `flight` to the pending queue, and return the list of hexes
    evicted by the depth cap (normally empty).

    Re-detecting an aircraft that is ALREADY queued refreshes its stored
    record - the freshest observation is the one worth eventually displaying -
    but deliberately leaves `first_seen` untouched. `first_seen` answers "how
    long has this aircraft been waiting for its turn?", which is what
    MAX_STALENESS_S bounds; letting it move would let an aircraft loiter in
    the queue indefinitely as long as it kept being re-detected.

    Eviction is OLDEST-FIRST, matching the direction the staleness bound
    already prefers: the entry closest to expiring is the one with least left
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
    """Pop the OLDEST still-fresh entry off `pending` (FIFO), discarding any
    entry that has already exceeded `max_staleness_s` on the way.

    Returns `(flight_or_None, dropped_hexes)`. `pending` is mutated in place.

    FIFO, not last-in - the whole point of the queue is that the aircraft that
    has been waiting longest is the one whose turn it is. An entry whose age
    exceeds the bound is dropped rather than shown, and the scan continues to
    the next one, so one expired entry never blocks a fresher one behind it.
    A negative age (a first_seen stamped in the future by a clock step) reads
    as fresh, which is the safe direction: it shows an aircraft rather than
    silently discarding it.
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


# DEVICE-04 battery-low hysteresis thresholds, raw millivolts (D-02: never a
# derived percentage/state-of-charge estimate - no real discharge curve
# exists for this pack yet, so a percentage would be fabricated precision;
# raw mV is how hardware/logtools.py's check-battery already reasons about
# it). BATTERY_LOW_THRESHOLD_MV = 3500 is 05-CONTEXT.md D-01's reasoned
# estimate, chosen to sit with real margin above hardware/logtools.py's
# --cutoff-mv 3400 "genuinely depleted" convention so the warning fires with
# days of runway left - to be retuned once plan 05-01's Tasks 2-3 produce a
# real discharge curve for this pack (a one-line constant change, not a
# replan). BATTERY_LOW_CLEAR_MV = 3600 is 05-UI-SPEC.md's 100 mV re-arm
# buffer resolving D-01's hysteresis discretion item.
BATTERY_LOW_THRESHOLD_MV = 3500
BATTERY_LOW_CLEAR_MV = 3600


def _extract_aircraft(snapshot):
    """A raw aggregator response dict (as injected by tests, or as returned
    by one of detect.PROVIDERS) carries its aircraft array under a
    provider-specific key ("ac" for airplanes.live and adsb.lol, "aircraft"
    for adsb.fi). Never raises on an unexpected shape - an empty list is
    the safe default (T-02-01-01's "skip/don't-claim" discipline).
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
    reading that actually crossed a D-P2-04 threshold, or held over from a
    prior cycle because this reading sat inside the deadband (or was
    missing/non-numeric)? Log-only classification - mirrors
    runway_config.infer_runway_config()'s own branches without duplicating
    its threshold constants as literals.
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
    """Missing, unreadable, or malformed -> empty state (D-P2-02), never a
    crash.
    """
    try:
        with open(_poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_battery_state(state_dir):
    """Read-only: `<state_dir>/battery_state.json` is owned and written
    exclusively by stub-server/byos_server.py's save_battery_state() (05-02
    Task 2) - this function never writes it (05-RESEARCH.md Pitfall 4).

    Returns the int `battery_mv` reading, or None on: a missing file,
    invalid JSON, a non-dict payload, a missing `battery_mv` key, or a
    `battery_mv` that is a bool, not an int, or not strictly positive.
    Degrades, never raises - matching load_poll_state()'s own shape.
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
    """Pure function: the D-04/D-06 battery-low decision, with hysteresis
    between BATTERY_LOW_THRESHOLD_MV (3500) and BATTERY_LOW_CLEAR_MV (3600).

    `battery_mv=None` (never reported, or load_battery_state() degraded on
    an unreadable/malformed file) returns `was_active` unchanged - a device
    that has never reported must not spuriously show the icon, and a
    temporarily unreadable file must not spuriously clear a real warning.

    Otherwise: when `was_active` is truthy (already showing the warning),
    it clears only once the reading is strictly below BATTERY_LOW_CLEAR_MV
    - `battery_mv < BATTERY_LOW_CLEAR_MV`. When not already active, it sets
    the warning at the threshold, inclusive - `battery_mv <=
    BATTERY_LOW_THRESHOLD_MV`. A reading strictly between the two constants
    deliberately holds the previous decision in BOTH directions (Pitfall
    5): it can neither newly arm nor newly clear the warning.
    """
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV


def save_poll_state(state_dir, state):
    """Atomic tmp-write-then-os.replace(), matching
    stub-server/byos_server.py's save_state() (T-02-01-03 / V12). Never
    leaves a stray .tmp file behind, even if the write itself fails.
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
    """Write `rendered` (packed panel bytes) to <state_dir>/panel.bin only
    if its SHA-256 differs from the currently-served bytes (T-02-01-03 /
    V12) - tmp-write-then-os.replace(), so byos_server.py can never serve a
    half-written file. Returns True if the served panel actually changed.
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
    """CFG-05: true only when every ADS-B provider this cycle actually
    queried failed outright - never merely because providers were queried
    successfully and simply found nothing on the tracked runway.

    Both of those cases return the same thing from
    `detect.poll_current_aircraft()` - a `None` selection - so this
    function is the *only* place that tells "every source is down" apart
    from "nothing is on the runway right now". Collapsing that distinction
    would fire the alert through every one of Orly's ordinary quiet
    periods, training the user to ignore it - exactly the false-alarm trap
    `.planning/seeds/on-device-fault-icon.md`'s CFG-05 scoping section
    rejects, and destroys the signal CFG-05 exists to provide.

    `diagnostics` is the dict `detect.poll_current_aircraft()` populates in
    place - `queried`/`failed`/`selected`/`disagreement`/`runway_id` - only
    when a live poll passes one in. The injected-snapshot test branch never
    queries any provider at all, so it never passes `diagnostics` (it stays
    `None`), which this function correctly classifies as "no fault" - not
    "unknown", since nothing was ever attempted that could have failed.
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
    """Best-effort read of the previously-persisted CFG-05 fault flag from
    `history.db`'s fixed-size meta table (`history_db.META_SOURCE_FAULT`) -
    the durable, cross-process comparison point the fault-transition
    re-render below needs. Deliberately NOT stored in `poll_state.json`:
    this script is a systemd oneshot with no in-process memory between
    invocations, and `poll_state.json` already has exactly one function
    that persists it, called from exactly one place in `run_once()` -
    adding a second write path here would reopen the two-writer race this
    project has already been careful to avoid elsewhere
    (`server/device_config.py`'s own module docstring). `history.db` is a
    separate file with its own concurrency discipline (WAL + busy_timeout),
    so it is the correct home for a per-cycle signal like this one.

    A missing database, a never-yet-set key, or any read failure all
    resolve to `False` (no known prior fault) rather than raising - a read
    failure here must never abort a poll cycle (T-06-10-05).
    """
    try:
        with history_db.open_db(state_dir) as conn:
            value = history_db.get_meta(conn, history_db.META_SOURCE_FAULT)
    except (sqlite3.Error, OSError) as exc:
        print("poll_loop: could not read source_fault meta: %s: %s" % (type(exc).__name__, exc))
        return False
    return value == "True"


def _should_record_event(flight, confirmed_state, poll_state):
    """CFG-06/CFG-08: true only on a real transition - the detected hex
    differs from the last-recorded one, the confirmed state differs, or the
    corroboration flag differs - never on an unchanged repeat detection.

    Pitfall 1 (06-RESEARCH.md): the server polls every 30 seconds, roughly
    2,880 cycles a day. Writing a `runway_events` row on every cycle would
    produce on the order of a million rows a year - roughly thirty times
    what D-13's storage estimate assumed. A transition is the only
    interesting event; that is what CFG-06's flight log and CFG-08's
    resolution statistics are actually about, so this function - not the
    per-cycle pipeline-run timestamp, which lives in history.db's
    fixed-size meta table instead - is the gate.

    Compares against `poll_state["last_recorded_hex"]` /
    `["last_recorded_confirmed_state"]` / `["last_recorded_corroborated"]` -
    persisted in `poll_state.json` (via `run_once()`'s existing single
    `save_poll_state()` call) so the comparison survives this oneshot's
    process boundary. `flight` is expected non-None; a non-dict `flight`
    degrades to "no hex/corroboration known" rather than raising.
    """
    last_hex = poll_state.get("last_recorded_hex")
    last_confirmed = poll_state.get("last_recorded_confirmed_state")
    last_corroborated = poll_state.get("last_recorded_corroborated")
    hex_ = flight.get("hex") if isinstance(flight, dict) else None
    corroborated = flight.get("corroborated") if isinstance(flight, dict) else None
    return hex_ != last_hex or confirmed_state != last_confirmed or corroborated != last_corroborated


def _record_history(state_dir, flight, confirmed_state, route_source, route, tracked_runway_id, source_fault, record_event, now_iso, caddy_log=None):
    """Write this cycle's durable signals into `history.db`, in one
    connection, fully contained: a database or filesystem failure here is
    caught and logged, never allowed to fail the poll cycle or leave the
    panel unwritten (T-06-10-05) - history is an accessory to the panel,
    not a dependency of it.

    `record_event` (from `_should_record_event()`) gates the one thing that
    is NOT written on every cycle: a `runway_events` row, inserted only on
    a real hex/confirmed_state/corroborated transition. Everything else
    here - the pipeline-run timestamp, the CFG-05 source-fault flag, and
    (when `flight` is not None) the last-detection timestamp - is written
    to the fixed-size `meta` table on every single cycle, transition or
    not, so those per-cycle freshness signals never grow the database
    (Pitfall 1).

    `caddy_log`, when given a path, ingests any new `/device/v1/display`
    lines from the Caddy durable access log into `device_health` on every
    cycle (CFG-03's only path to battery-voltage history - see
    history_db.tail_caddy_battery_log()'s module note). This was built and
    unit-tested in plan 06-01 but never wired into a caller until this
    fix - a missing/unreadable log file is a no-op (0 rows), same
    catch-and-log containment as everything else in this function.
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
    """CFG-11: archive `canvas` (the pre-pack render already produced for
    this cycle - never a second render pass) as a PNG into
    `<state_dir>/gallery/`, named from a filesystem-safe form of `now_iso`
    so lexical order is chronological, then prune down to
    GALLERY_MAX_ENTRIES (=25 - 06-RESEARCH.md Open Question 3; each PNG is
    a full-size panel image, so the cap bounds gallery disk use to
    single-digit megabytes).

    The filename is generated server-side from this process's own clock,
    never from any external input (T-06-10-07); the companion service
    additionally only ever serves a name matched against a fresh directory
    listing.

    Called only when `write_panel_atomic()` actually changed the served
    bytes - an unchanged cycle is not a new render, and archiving one would
    fill the gallery with visually-identical duplicates. Wrapped in the
    same catch-and-log containment as `_record_history()` (T-06-10-05): the
    gallery is an accessory, never allowed to fail a poll cycle - by the
    time this is called, `panel.bin` has already been written.
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

    Returns a small result dict: {"flight": ..., "state": ..., "panel_changed": ...,
    "theme": ..., "tracked_runway": ..., "source_fault": ..., "event_recorded": ...}.
    `flight` is what this cycle DETECTED, which since the 2026-08-28
    mechanism-C mitigation is not necessarily what it displayed - a distinct
    new aircraft may have been queued rather than shown. `state` and
    `panel_changed` describe the DISPLAY. Read poll_state.json's "last_flight"
    for what is actually on the panel. Everything derived from the displayed
    aircraft - the render, the enrichment, and the CFG-06/CFG-08 history row -
    is keyed on that displayed aircraft (`current_flight`), never on this
    cycle's raw detection, so a paced cycle can never write a row whose hex
    and route describe two different aircraft.

    Never logs a bearer token or BYOS setup secret - this module has no
    access to either; only the selected hex/callsign/altitude/state and
    whether the panel changed are printed (T-02-01-04).
    """
    state_dir = state_dir or DEFAULT_STATE_DIR
    os.makedirs(state_dir, exist_ok=True)

    # D-01/D-02 (quick task 260902-v26): configure the illustration override
    # resolver from THIS cycle's own state_dir, here rather than in main() -
    # run_once() is the single entry point both the systemd oneshot AND
    # companion/app.py's POST /poll-now in-process trigger go through, so
    # setting it here covers both without a second call site. Idempotent,
    # and both callers pass the same state_dir, so this process-global
    # assignment is safe under companion/app.py's ThreadingHTTPServer (the
    # companion service passes its own --state-dir to run_once(), which is
    # the same directory its own routes use). This is what lets an uploaded
    # override reach render.py's select_illustration() calls without
    # render.py itself gaining any state_dir awareness.
    #
    # server/plane/render.py's standalone CLI main() is deliberately NOT
    # wired - it renders ad-hoc previews from the command line and has no
    # state dir of its own; it keeps resolving vendored art only.
    illustrations.set_override_state_dir(state_dir)

    # CFG-01/CFG-12: read the user's saved theme + tracked runway ONCE per
    # cycle, not once per call site - a mid-cycle save landing between two
    # separate reads is exactly how a panel could end up rendered half in
    # one theme/runway and half in another. The loader never raises and
    # always returns registry-member values, so no validation is needed
    # here.
    device_cfg = device_config.load_device_config(state_dir)
    theme_id = device_cfg["theme"]
    tracked_runway_id = device_cfg["tracked_runway"]

    geofence_data = detect.load_geofence(geofence)

    # CFG-05: `diagnostics`, when populated, is the only signal that tells
    # "every ADS-B source is down" apart from "nothing is on the runway
    # right now" - both otherwise return the same None selection. The
    # injected-snapshot branch never queries any provider, so it never
    # gets a diagnostics dict at all (stays None), which _classify_source_fault()
    # correctly reads as "no fault" rather than "unknown".
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

    poll_state = load_poll_state(state_dir)
    current_flight = poll_state.get("last_flight")
    current_confirmed_state = poll_state.get("last_confirmed_state")
    current_route = poll_state.get("last_route")
    previous_flight = poll_state.get("previous_flight")
    previous_confirmed_state = poll_state.get("previous_confirmed_state")
    previous_route = poll_state.get("previous_route")
    pending = normalise_pending(poll_state.get("pending_flights"))
    last_advance_at = _as_timestamp(poll_state.get("last_advance_at"))
    now = now_s()
    # quick task 260827-oz9: only the flight-detected branch below can ever
    # set this, but every branch (including the two no-detection branches)
    # falls through to the single shared log statement at the bottom, so
    # it must be defined here, before any branching, or an ordinary cycle
    # that detects nothing raises UnboundLocalError.
    unknown_prefix = None
    # CFG-06/CFG-08: whether this cycle actually wrote a runway_events row
    # (see _should_record_event()) - surfaced in the returned result dict
    # so the companion service's manual-trigger handler can report it.
    # Only ever set True in the flight-detected branch's confirmed-state
    # sub-branch below.
    event_recorded = False

    # 05-02 (DEVICE-04): the battery-low decision, computed before any
    # branching for the same reason - every branch (including both
    # no-detection branches) needs it, either to thread into a render call
    # or to decide whether a hold-cycle re-render is warranted.
    was_battery_low = bool(poll_state.get("battery_low_active", False))
    battery_low = apply_battery_hysteresis(load_battery_state(state_dir), was_battery_low)
    battery_changed = battery_low != was_battery_low
    poll_state["battery_low_active"] = battery_low

    # --- Display pacing: which detection occupies the "current" slot -------
    #
    # Mechanism-C mitigation. `flight` is what this poll DETECTED; it is not
    # necessarily what this cycle DISPLAYS. A distinct new aircraft goes into
    # the pending queue, and the "current" slot advances no faster than
    # MIN_ADVANCE_INTERVAL_S so the device gets a real chance to fetch and
    # blit each one. Nothing about the selection that produced `flight`, and
    # nothing about the two-slot poster layout (D-25/D-26), changes here - the
    # actual current/previous shift happens once, below, at the point a
    # queued aircraft is promoted (whether that promotion is immediate, on
    # the very first detection, or delayed via the pending queue).
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
            # D-25: re-detecting the SAME aircraft is not a new one - nothing
            # shifts, nothing queues. Its record is refreshed in place so the
            # vertical rate driving D-P2-04 inference stays current.
            current_flight = flight
            refreshed = True
        else:
            dropped.extend(enqueue_pending(pending, flight, now))
            queue_dirty = True

    # Drain the queue when the device is due for a redraw. This runs even on a
    # cycle that detected NOTHING: a burst followed by an empty sky is the
    # common shape of the bug, and without draining on quiet cycles every
    # queued aircraft would sit there until it expired. `promoted is None`
    # guards the bootstrap case above, which has already advanced.
    if promoted is None and pending and advance_is_due(last_advance_at, now):
        promoted, expired = pop_fresh_pending(pending, now)
        dropped.extend(expired)
        queue_dirty = True

    # D-25 (03-CONTEXT.md): two-deep flight history for the poster's
    # current+previous layout. The aircraft leaving the "current" slot - and
    # its resolved state/route - shifts down into "previous". The only thing
    # this pass changed is WHEN that shift happens (on a paced advance rather
    # than on every distinct detection) and WHICH aircraft arrives (the oldest
    # still-fresh queued one rather than whatever was detected this instant).
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
        # D-03/D-P2-04: real runway-configuration inference from the
        # aircraft's own vertical rate, with a deadband and hold-last-state
        # behaviour (server.plane.runway_config). Replaces the 02-01 stub
        # that hardcoded every detected flight as "arriving". Inference and
        # enrichment both run against the aircraft now occupying the
        # "current" slot, NOT against `flight` - on a paced cycle those are
        # different aircraft, and every other field on the log line below
        # describes what is displayed.
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
            canvas = render.build_canvas(
                None, render_state, theme_id=theme_id, runway_id=tracked_runway_id,
                source_fault=source_fault, battery_low=battery_low,
            )
        else:
            render_state = confirmed_state
            # D-02/D-P2-05: resolve the airline + route for zones 7/9 via a
            # persistent, callsign-keyed cache (D-P2-02 - this cache lives
            # in poll_state.json, not in-process, since this script is a
            # systemd oneshot with no memory between invocations).
            cache = poll_state.get("enrichment_cache")
            if not isinstance(cache, dict):
                cache = {}
            # D-05 (quick task 260827-hyy): a single seam now classifies
            # four categories, not three - "fresh_hit"/"cache_hit" mean
            # exactly what they always did (a cached *miss* is still a
            # "miss" here, not a "cache hit" - "cache hit" means the cache
            # spared us a request AND returned a usable route); the new
            # fourth category, "airline_only", means adsbdb had no route
            # this cycle but the callsign's ICAO prefix identified the
            # carrier from a static in-repo table - no additional network
            # call, no additional cache entry. Nothing derived from the
            # adsbdb response body is ever logged, on any of the four paths.
            route, route_source = enrich.resolve_route(current_flight.get("callsign"), cache)
            enrich.trim_cache(cache)
            poll_state["enrichment_cache"] = cache
            # quick task 260827-oz9: a "miss" means neither adsbdb nor the
            # static prefix table resolved anything for a shape-valid
            # callsign - exactly "unrecognized ICAO prefix". Record it into
            # the same durable poll_state.json this cycle already writes,
            # so the finding survives this oneshot's process boundary.
            # Never called for "airline_only"/"fresh_hit"/"cache_hit" (a
            # source resolved something) or "held"/"n/a" (no enrichment
            # ran this cycle at all).
            unresolved_prefixes = poll_state.get("unresolved_prefixes")
            if not isinstance(unresolved_prefixes, dict):
                unresolved_prefixes = {}
            if route_source == "miss":
                unknown_prefix = enrich.note_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
            enrich.trim_unresolved_prefixes(unresolved_prefixes)
            poll_state["unresolved_prefixes"] = unresolved_prefixes
            # CFG-06/CFG-08: a real hex/confirmed_state/corroborated
            # transition, computed BEFORE poll_state's last_recorded_*
            # keys are overwritten below with this cycle's own values.
            #
            # Keyed on `current_flight` (what reached the DISPLAY), not on
            # `flight` (what this cycle detected). Since the 2026-08-28
            # mechanism-C pacing fix those are different aircraft on a paced
            # cycle, and `flight` can even be None here - this branch is
            # reached whenever the queue drains, including on a cycle that
            # detected nothing at all. `confirmed_state` and `route` below
            # are both derived from `current_flight`, so recording `flight`
            # would write a runway_events row whose hex and route describe
            # two different aircraft.
            event_recorded = _should_record_event(current_flight, confirmed_state, poll_state)
            poll_state["last_recorded_hex"] = current_flight.get("hex")
            poll_state["last_recorded_confirmed_state"] = confirmed_state
            poll_state["last_recorded_corroborated"] = current_flight.get("corroborated")
            # D-25/D-26: the previous flight's own real illustration/text
            # rides along on the same panel as the current detection's.
            canvas = render.build_canvas(
                current_flight,
                render_state,
                route=route,
                previous_flight=previous_flight,
                previous_route=previous_route,
                previous_state=previous_confirmed_state,
                theme_id=theme_id,
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
        poll_state["previous_flight"] = previous_flight
        poll_state["previous_confirmed_state"] = previous_confirmed_state
        poll_state["previous_route"] = previous_route
        poll_state["pending_flights"] = pending
        poll_state["last_advance_at"] = last_advance_at
        save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, current_flight, confirmed_state, route_source, route,
            tracked_runway_id, source_fault, event_recorded, now_iso,
            caddy_log=caddy_log,
        )
    elif current_flight is not None:
        # D-04: nothing NEW reached the display this cycle, but a flight was
        # already on screen - do nothing to panel.bin. No waiting state, no
        # expiry. Two ways to arrive here now: nothing was detected at all
        # (the original D-04 case), or something WAS detected but is waiting
        # its turn in the pending queue (the mechanism-C pacing case). Both
        # hold the panel, which is exactly the point - the device is still
        # mid-redraw on what it last fetched.
        confirmed_state = current_confirmed_state
        render_state = confirmed_state if confirmed_state is not None else "empty"
        state_source = "held"
        route_source = "held"
        panel_changed = False
        # Two independent things can change while the panel is otherwise
        # held, and BOTH must be able to reach the glass from this branch:
        # the CFG-05 source-fault badge (T-06-10-04) and the DEVICE-04
        # battery-low icon (05-02). They are folded into one guarded
        # re-render because they draw onto the same canvas - re-rendering
        # twice would write the panel twice for a single cycle.
        #
        # Gated strictly on a TRANSITION of either flag, never on either
        # flag's value, so a persistent outage or a persistently flat
        # battery does not force a full-panel refresh every 30-second
        # cycle - a full e-ink refresh measures ~31.5s on this panel
        # (Phase 1), so refreshing every cycle would keep the display in
        # permanent refresh and burn battery for no added information.
        #
        # This stays D-04-compatible: the only pixels that can differ are
        # the badge and the icon. It does not invent a waiting state,
        # expire the held flight, or alter any flight-derived pixel. A
        # frame that sits in this branch all night would otherwise never
        # show a warning that arose during it, defeating both DEVICE-04 and
        # CFG-05 in exactly the situation they exist for.
        if source_fault != previous_source_fault or battery_changed:
            if confirmed_state is not None:
                held_canvas = render.build_canvas(
                    current_flight,
                    render_state,
                    route=current_route,
                    previous_flight=previous_flight,
                    previous_route=previous_route,
                    previous_state=previous_confirmed_state,
                    theme_id=theme_id,
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
            # Nothing displayed changed, but the QUEUE did, and this script
            # has no memory across invocations (D-P2-02) - an unpersisted
            # enqueue would be lost the instant this process exits, which
            # would silently disable the whole mitigation.
            poll_state["pending_flights"] = pending
            poll_state["last_advance_at"] = last_advance_at
        if battery_changed or queue_dirty:
            save_poll_state(state_dir, poll_state)
        # T-06-10-05/Pitfall 1: every cycle through this branch, transition
        # or not, still records the per-cycle pipeline-run + source-fault
        # meta signals - nothing reached the display this cycle, so no
        # runway_events row (record_event=False) and no last-detection
        # timestamp update.
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log,
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
        # 05-02 (DEVICE-04): the flight-detected branch above always calls
        # save_poll_state() unconditionally; this branch otherwise never
        # does, so the hysteresis memory would not survive this oneshot's
        # process boundary on a frame that has never seen an aircraft.
        if battery_changed:
            save_poll_state(state_dir, poll_state)
        _record_history(
            state_dir, None, None, None, None,
            tracked_runway_id, source_fault, False, now_iso,
            caddy_log=caddy_log,
        )

    # T-02-04-05: log only the callsign, the enrichment outcome
    # (cache_hit / fresh_hit / miss / n/a / held), and the selection's own
    # corroboration flag - a three-state provenance signal about this
    # project's own ADS-B sources, not third-party response content, so it
    # stays within this rule - never the raw adsbdb response body.
    # quick task 260827-oz9: unknown_prefix is the first three characters
    # of the callsign this same line already prints in full, derived from
    # this project's own selected-aircraft record - not from any
    # third-party response body - so it stays within the rule above too.
    #
    # Plan 06-10: theme/tracked_runway/source_fault are this project's own
    # saved configuration and its own inference about its own ADS-B
    # sources - none is third-party response content - so they stay within
    # the same rule.
    #
    # Mechanism-C mitigation adds three fields, and deliberately does NOT
    # change what `hex=` means. `hex=` is still THIS CYCLE'S DETECTION, so the
    # existing triage recipe keeps working - in particular a suppressed cycle
    # still logs `hex=None ... panel_changed=False`, byte-identical to a
    # genuinely empty sky, which is a documented (if unhelpful) property the
    # runbook already relies on. What is displayed is named separately:
    #   shown=   the hex now occupying the "current" display slot
    #   pending= how many distinct aircraft are waiting their turn
    #   dropped= hexes discarded this cycle, past the staleness bound or
    #            evicted by the depth cap. This is the residual loss - the
    #            flights this mitigation still cannot show. It exists because
    #            the whole reason mechanism C went undiagnosed for so long is
    #            that it was invisible in this server's own logs.
    # 05-02 (DEVICE-04): battery_low is likewise this project's own device
    # telemetry-derived boolean, never third-party response content, so it
    # also stays within the T-02-04-05 logging rule - the raw millivolt
    # value itself is deliberately never logged.
    # All fields above are derived from this project's own selected-aircraft
    # records or device telemetry, never from a third-party response body
    # (T-02-04-05).
    print(
        "poll_loop: hex=%s callsign=%s aircraft_type=%s corroborated=%s altitude_ft=%s confirmed_state=%s "
        "render_state=%s state_source=%s route_source=%s unknown_prefix=%s shown=%s pending=%d dropped=%s "
        "battery_low=%s panel_changed=%s theme=%s tracked_runway=%s source_fault=%s"
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
            tracked_runway_id,
            source_fault,
        )
    )

    return {
        "flight": flight,
        "state": render_state,
        "panel_changed": panel_changed,
        "theme": theme_id,
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
