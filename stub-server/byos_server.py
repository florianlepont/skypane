#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 YODE PTE LTD
# SPDX-License-Identifier: Apache-2.0
"""Minimal bring-your-own-server for FlightPortrait frames. Stdlib only.

Implements the three device endpoints from docs/PROTOCOL.md well enough
to run a stock frame: point the frame at this host during BLE
provisioning (PROTOCOL.md §5) and it will set up, poll, download, and
display whatever panel image you serve.

    python3 byos_server.py --image path/to/panel.bin [--port 8642]
        [--secret VALUE] [--sleep 3600] [--state-dir DIR]

The image must be exactly 960,000 bytes in the PROTOCOL.md §1 format
(the calibration patterns in first-flash/bins/ work). Swap the file on
disk and the next poll serves the new content — the frame notices via
the hash and refreshes. --secret, when set, must match the structured
BYOS setup secret entered during provisioning; without it any
provision_secret is accepted. Issued device tokens live in
byos_state.json inside --state-dir (default: next to this script), so
restarts don't strand frames.

This is a reference, not a product: no TLS (the frame allows plain http
for hand-set targets), no rate limiting, one image for every frame.

SkyPane local modifications: added --state-dir so a throwaway harness
run (stub-server/test_poll_cycle.py) can isolate its own token state
from the long-running instance the hardware bring-up plans keep alive;
added --image-url-scheme (default: http) so the served image_url can
advertise https when this process runs behind a TLS-terminating
reverse proxy (Phase 2's Caddy-fronted deployment), instead of always
hardcoding http; added DEVICE-04 X-Battery-Mv validation/persistence
(parse_battery_mv() / save_battery_state()) - an authenticated
/device/v1/display poll carrying a plausible reading writes
battery_state.json ({"battery_mv": int, "received_at": float}) in
--state-dir, the single writer of that file anywhere in this repo (see
stub-server/VENDOR.md); added a read-only led_enabled lookup
(device_config_path() / read_led_enabled()) so /device/v1/display serves
the companion app's saved bring-up-LED setting instead of a hardcoded
constant (Phase 06.2); added a quiet-hours-aware sleep_s extension
(read_quiet_hours() / quiet_hours_sleep_s()) so /device/v1/display
extends the base --sleep value to span the companion app's saved
scheduled-quiet-hours window instead of always returning the raw
per-poll value (Phase 10); added a read-only wake_interval_s lookup
(read_wake_interval_s()) so the base value fed into that quiet-hours
extension is the companion app's saved wake interval when one is set,
falling back to --sleep when it is not (Phase 11); and added a
read-only display_enabled lookup (read_display_enabled()) plus a
display_off_sleep_s() composer so /device/v1/display pins sleep_s to a
fixed 300s off-state cadence when the companion app's saved
display_enabled is False, composed inside the quiet-hours extension so
the longer of the two always wins (Phase 12). See stub-server/VENDOR.md
for the full list of local changes.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# zoneinfo is stdlib since Python 3.9 - this module's "Stdlib only" claim
# above stays true.
from zoneinfo import ZoneInfo

IMAGE_BYTES = 960000
# DEVICE-04 X-Battery-Mv sanity bounds. BATTERY_MV_MIN = 1: PROTOCOL.md §2
# defines "0" as the *unknown* sentinel, so zero must be rejected rather than
# persisted as a real reading. BATTERY_MV_MAX = 10000: a sanity ceiling far
# above any single-cell LiPo (4200 mV full charge), per 05-RESEARCH.md's V5
# Input Validation row.
BATTERY_MV_MIN = 1
BATTERY_MV_MAX = 10000

# Shape gate for a submitted/stored quiet-hours HH:MM string. Copied
# character-for-character from server/device_config.py's own _HHMM_RE -
# see the cross-reference comment above seconds_until_quiet_hours_end()
# below for why this file carries its own copy instead of importing it.
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")

# The device has exactly one fixed physical location, so the quiet-hours
# window's timezone is deliberately hardcoded here, matching
# server/device_config.py's own QUIET_HOURS_TZ.
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

# Phase 11 (D-02): bounds for the companion Settings page's saved
# wake_interval_s field. Independently redefined here rather than imported
# from server/device_config.py - this file must never import a server.*
# module (see the vendor-boundary rationale above seconds_until_quiet_hours_end()
# below). These two values must stay numerically equal to
# server/device_config.py's WAKE_INTERVAL_MIN_S/WAKE_INTERVAL_MAX_S of the
# same names, by hand, in the same commit - the same discipline _HHMM_RE's
# own comment already states. Unlike _HHMM_RE and seconds_until_quiet_hours_end(),
# these two are NOT covered by test_poll_cycle.py's _quiet_hours_drift_guard,
# which pins only the arithmetic core and the shared regex.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600

# Phase 12 (D-01): the fixed off-state check-in cadence while display_enabled is False.
# Independently redefined here rather than imported from server/device_config.py - the
# same vendor-boundary rationale as WAKE_INTERVAL_MIN_S/MAX_S immediately above. Origin:
# server/device_config.py's DISPLAY_OFF_SLEEP_S constant of the same name and value; the
# two must be kept numerically equal by hand, in the same commit, matching that module's
# own cross-reference comment. Like WAKE_INTERVAL_MIN_S/MAX_S, this is NOT covered by
# test_poll_cycle.py's byte-for-byte _quiet_hours_drift_guard, which extracts whole `def`
# blocks and has nothing to compare for a bare integer - Task 2 adds a lighter,
# purpose-built parity check instead.
DISPLAY_OFF_SLEEP_S = 300


def state_path(state_dir):
    return os.path.join(state_dir, "byos_state.json")


def load_state(state_dir):
    try:
        with open(state_path(state_dir)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}


def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))


def device_config_path(state_dir):
    return os.path.join(state_dir, "device_config.json")


def read_led_enabled(state_dir):
    """Best-effort read of the shared device_config.json's led_enabled
    field. Never raises.

    The file is written by companion/app.py's config page via
    server/device_config.py's save_device_config(); every failure mode
    here (missing file, unreadable file, malformed JSON, a non-dict
    document, or a present-but-non-bool led_enabled value) degrades to
    enabled, matching the firmware's own fail-open contract in
    firmware/main/api_client.c. This is the only place in this file that
    reads that document.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    value = data.get("led_enabled")
    if isinstance(value, bool):
        return value
    return True


def read_display_enabled(state_dir):
    """Best-effort read of the shared device_config.json's display_enabled
    field. Never raises.

    The file is written by companion/app.py's config page via
    server/device_config.py's save_device_config(); every failure mode
    here (missing file, unreadable file, malformed JSON, a non-dict
    document, or a present-but-non-bool display_enabled value) degrades
    to enabled (True) - the same fail-open direction
    server/device_config.py's normalise_display_enabled() chose, and for
    the same reason: a missing, unreadable, malformed or wrong-typed
    config can never pin a healthy device to the 300s off-state cadence
    (DISPLAY_OFF_SLEEP_S) and can never darken a frame that a corrupted
    file merely failed to describe. This is the only place in this file
    that reads that key.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    value = data.get("display_enabled")
    if isinstance(value, bool):
        return value
    return True


def read_wake_interval_s(state_dir, default):
    """Best-effort read of the shared device_config.json's wake_interval_s
    field. Never raises.

    The file is written by companion/app.py's config page via
    server/device_config.py's save_device_config(); every failure mode
    here - a missing file, an unreadable file, malformed JSON, a
    non-dict document, an absent wake_interval_s key, a wrong-typed
    value (including a bool - isinstance(True, int) is True in Python,
    so a bare int test would let a JSON `true` become a deep-sleep
    duration), or a value outside the inclusive
    [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] range - degrades to
    `default`, the caller's `--sleep` CLI value. This is the only place
    in this file that reads wake_interval_s.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return default
    if not isinstance(data, dict):
        return default
    value = data.get("wake_interval_s")
    if (isinstance(value, int) and not isinstance(value, bool)
            and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S):
        return value
    return default


# --- Quiet-hours sleep_s extension (Phase 10, D-01) --------------------
#
# seconds_until_quiet_hours_end() below is a deliberate, byte-for-byte
# DUPLICATE of server/device_config.py's function of the same name, as
# committed by plan 10-01. This file must never import a server.* module
# - there is no sys.path bootstrap here to make such an import even
# resolve, it would break the module docstring's "Stdlib only" claim
# above, and it would blur the vendor-provenance boundary
# stub-server/VENDOR.md exists to track. The two copies are pinned equal
# by an automated drift guard in stub-server/test_poll_cycle.py; if you
# change one, you must change the other identically, in the same commit.
def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Return the whole seconds remaining until the daily [start_hm, end_hm)
    Europe/Paris wall-clock window's end time, or `None` when `now_utc`
    falls outside the window. The window wraps midnight whenever
    `end_hm <= start_hm` (e.g. "23:00"/"07:00"); when `start_hm == end_hm`
    the window is zero-width and this always returns `None` for every
    instant - a zero-width window is never active, and that is intentional
    rather than a bug to "fix" into an always-active window.

    Parameter contract - this function is the arithmetic core only and
    performs no validation of its own, because stub-server/byos_server.py
    (plan 10-03) duplicates it byte-for-byte across the vendor boundary and
    every byte it carries has to be reproducible there:
      - `now_utc` MUST be a timezone-aware datetime.
      - `start_hm`/`end_hm` MUST already have passed `_HHMM_RE`.

    Two mandatory deviations from 10-PATTERNS.md's reference body, both
    load-bearing - do not "restore" the reference version:

    (a) The final return subtracts in UTC, not in local time:
    `end_dt.astimezone(timezone.utc) - now_utc`, NOT `end_dt - local_now`.
    This is a correctness fix, verified numerically during planning:
    `end_dt` and `local_now` share the same `tzinfo` object, and Python's
    documented rule for subtracting two aware datetimes with the same
    `tzinfo` is to ignore the zone and subtract the wall-clock numerals -
    so the reference body's naive numeral difference is wrong by exactly
    one hour across a Europe/Paris DST transition. Converting `end_dt` to
    UTC first restores the true-elapsed-duration property.

    (b) Accepted caveat (10-RESEARCH.md Pitfall 2), not engineered around: a
    window boundary configured inside the 02:00-03:00 transition hour on
    the last Sunday of March or October resolves via PEP 495's default
    `fold=0` semantics and can be up to an hour off for that one instant.
    No `fold=1` override is added - D-01's "never shorter than the base
    sleep" rule bounds the worst case to one extra or one missing wake,
    twice a year, only for a boundary configured inside that specific hour.
    """
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
    start_h, start_m = (int(x) for x in start_hm.split(":"))
    end_h, end_m = (int(x) for x in end_hm.split(":"))
    start_today = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_today = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if (start_h, start_m) <= (end_h, end_m):
        if not (start_today <= local_now < end_today):
            return None
        end_dt = end_today
    else:
        if local_now >= start_today:
            end_dt = end_today + timedelta(days=1)
        elif local_now < end_today:
            end_dt = end_today
        else:
            return None
    return max(0, int((end_dt.astimezone(timezone.utc) - now_utc).total_seconds()))


def read_quiet_hours(state_dir):
    """Best-effort read of the shared device_config.json's quiet-hours
    fields. Never raises.

    The file is written by companion/app.py's config page via
    server/device_config.py's save_device_config(); every failure mode
    here - a missing file, an unreadable file, malformed JSON, a
    non-dict document, `quiet_hours_enabled` not literally `True`, or
    either `quiet_hours_start`/`quiet_hours_end` failing
    `isinstance(value, str) and _HHMM_RE.match(value)` - degrades to
    `None` (meaning "quiet hours are not in effect", i.e. the
    pre-existing unmodified sleep_s behaviour), matching
    read_led_enabled()'s fail-open shape immediately above. A corrupted
    config file must never be able to take down the single always-on
    /device/v1/display service for every future poll.

    Returns the `(start_hm, end_hm)` tuple when every check passes,
    otherwise `None`.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("quiet_hours_enabled") is not True:
        return None
    start_hm = data.get("quiet_hours_start")
    end_hm = data.get("quiet_hours_end")
    if not (isinstance(start_hm, str) and _HHMM_RE.match(start_hm)):
        return None
    if not (isinstance(end_hm, str) and _HHMM_RE.match(end_hm)):
        return None
    return start_hm, end_hm


def display_off_sleep_s(base_sleep_s, state_dir):
    """Return the sleep_s to feed into quiet_hours_sleep_s() as its base:
    exactly DISPLAY_OFF_SLEEP_S (300) when the display is off, otherwise
    `base_sleep_s` unchanged (Phase 12, D-01).

    This is a flat REPLACEMENT, deliberately not a max() or a min()
    against `base_sleep_s` - that is the whole content of D-01. The
    asymmetry is intentional in both directions, not an oversight for a
    later reader to "restore consistency" on: against a short configured
    wake_interval_s (floor 60s) the pin cuts the wake count roughly
    fivefold while off; against a long one (ceiling 3600s) it makes
    switching the display back on *faster* than the configured interval
    would have - a predictable within-five-minutes instead of up to an
    hour (D-02). Serving a value shorter than the configured interval is
    the intended off-state behaviour here.

    Composition order is load-bearing (D-05, sleep axis): this function's
    result must be passed as quiet_hours_sleep_s()'s `base_sleep_s`
    argument, i.e. `quiet_hours_sleep_s(display_off_sleep_s(...), ...)`,
    never the other way round. Nested this way, the 300s pin becomes the
    base that quiet_hours_sleep_s()'s own `max(base_sleep_s, remaining)`
    operates on, yielding `max(300, quiet_hours_remaining)` for free with
    no change to that function. Inverted - display_off_sleep_s() wrapping
    quiet_hours_sleep_s() - an active quiet-hours window's remaining time
    would be overwritten by a flat 300s, and the device would wake all
    night with the display off, defeating quiet hours entirely. See the
    do_GET /device/v1/display response construction below for the actual
    composition, and Task 2's negative control for a live-executed proof
    that the inverted order fails.
    """
    if read_display_enabled(state_dir) is False:
        return DISPLAY_OFF_SLEEP_S
    return base_sleep_s


def quiet_hours_sleep_s(base_sleep_s, state_dir, now=None):
    """Return the sleep_s value to hand back on GET /device/v1/display:
    `base_sleep_s` unchanged unless a poll lands inside an enabled
    quiet-hours window, in which case it is extended to span the
    window's remaining local end time (D-01 - this is the sole
    mechanism that pauses the device, no firmware change exists or is
    needed).

    `now` defaults to `datetime.now(timezone.utc)`; it is an injectable
    seam so a test harness can drive DST and boundary scenarios
    deterministically instead of depending on real wall-clock timing.

    The `max(base_sleep_s, remaining)` below is load-bearing and is the
    resolution of 10-CONTEXT.md's own "Claude's Discretion" edge case: a
    quiet-hours computation must never make the device sleep for LESS
    time than it otherwise would, so a long configured --sleep that
    already carries the device past a short window simply wins.
    """
    window = read_quiet_hours(state_dir)
    if window is None:
        return base_sleep_s
    start_hm, end_hm = window
    if now is None:
        now = datetime.now(timezone.utc)
    remaining = seconds_until_quiet_hours_end(now, start_hm, end_hm)
    if remaining is None:
        return base_sleep_s
    return max(base_sleep_s, remaining)


def battery_state_path(state_dir):
    return os.path.join(state_dir, "battery_state.json")


def parse_battery_mv(raw):
    """Parse a raw X-Battery-Mv header value into a plausible millivolt
    reading, or None. Never raises, never logs the raw value.

    Rejects anything that is not a string; a string whose length is not
    between 1 and 5 characters; and any string containing a character
    outside the literal ASCII digit set below - checked explicitly against
    that set, not via a general digit-classification predicate, which
    would accept non-ASCII decimal digits that int() then either misparses
    or raises on. No whitespace, no sign character - a well-formed device
    sends bare digits and nothing else. Only after those checks does this
    convert to int and reject anything outside BATTERY_MV_MIN..BATTERY_MV_MAX
    inclusive (T-05-02-01).
    """
    if not isinstance(raw, str):
        return None
    if not (1 <= len(raw) <= 5):
        return None
    if any(c not in "0123456789" for c in raw):
        return None
    mv = int(raw)
    if not (BATTERY_MV_MIN <= mv <= BATTERY_MV_MAX):
        return None
    return mv


def save_battery_state(state_dir, mv):
    """Persist {"battery_mv": mv, "received_at": time.time()} to
    battery_state.json in state_dir, atomically (tmp-write then
    os.replace(), mirroring save_state()'s pattern). This function - and
    this process - are the ONLY writer of that file anywhere in the repo;
    server/poll_loop.py only ever reads it (05-RESEARCH.md Pitfall 4: two
    processes doing read-modify-write on one JSON file is a real
    lost-update race, and neither unit takes a lock).
    """
    path = battery_state_path(state_dir)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"battery_mv": mv, "received_at": time.time()}, fh, indent=1)
    os.replace(tmp, path)


class Handler(BaseHTTPRequestHandler):
    server_version = "flightportrait-byos-example"
    args = None
    state = None

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n).decode())
        except (ValueError, UnicodeDecodeError):
            return None

    def bearer_ok(self):
        auth = self.headers.get("Authorization", "")
        return (auth.startswith("Bearer ") and
                auth[7:] in self.state["tokens"].values())

    def log_telemetry(self):
        parts = []
        for h in ("X-Fw-Version", "X-Boot-Reason", "X-Rssi",
                  "X-Battery-Mv"):
            v = self.headers.get(h)
            if v:
                parts.append("%s=%s" % (h, v))
        if parts:
            print("  telemetry:", " ".join(parts))

    def do_POST(self):
        if self.path == "/device/v1/setup":
            body = self.read_body_json()
            if not isinstance(body, dict) or "mac" not in body:
                return self.send_json(422, {"detail": "bad body"})
            if (self.args.secret and
                    body.get("provision_secret") != self.args.secret):
                return self.send_json(401, {"detail": "bad secret"})
            token = secrets.token_hex(32)
            self.state["tokens"][body["mac"]] = token
            save_state(self.args.state_dir, self.state)
            print("setup: %s enrolled (hw_rev=%s)"
                  % (body["mac"], body.get("hw_rev", "?")))
            # No pairing block: account pairing is a first-party
            # extension this example does not implement (PROTOCOL.md §2).
            return self.send_json(200, {"device_token": token})
        if self.path == "/device/v1/log":
            if not self.bearer_ok():
                return self.send_json(401, {"detail": "unknown token"})
            body = self.read_body_json()
            if not isinstance(body, dict) or \
                    not isinstance(body.get("logs"), list):
                return self.send_json(422, {"detail": "bad body"})
            self.log_telemetry()
            for entry in body["logs"]:
                print("  frame log [%s] %s (ts=%s)"
                      % (entry.get("level", "error"),
                         entry.get("message", ""), entry.get("ts")))
            return self.send_json(200, {"ok": True})
        return self.send_json(404, {"detail": "unknown endpoint"})

    def do_GET(self):
        if self.path == "/device/v1/display":
            if not self.bearer_ok():
                return self.send_json(401, {"detail": "unknown token"})
            self.log_telemetry()
            # DEVICE-04: strictly after the bearer_ok() gate above, so an
            # unauthenticated/wrong-token caller can never pin a victim
            # frame's panel into a permanent low-battery warning
            # (T-05-02-04). A telemetry side-effect must never turn a
            # healthy panel poll into a 500 - a full or read-only state
            # directory degrades to "no battery signal", which
            # poll_loop.py already treats as legitimate (single-writer
            # rule: this is the only place battery_state.json is written).
            battery_mv = parse_battery_mv(self.headers.get("X-Battery-Mv"))
            if battery_mv is not None:
                try:
                    save_battery_state(self.args.state_dir, battery_mv)
                except OSError:
                    pass
            try:
                with open(self.args.image, "rb") as fh:
                    image = fh.read()
            except OSError:
                return self.send_json(503, {"detail": "image unreadable"})
            if len(image) != IMAGE_BYTES:
                return self.send_json(503, {"detail": "image wrong size"})
            digest = hashlib.sha256(image).hexdigest()
            host = self.headers.get("Host", "localhost")
            return self.send_json(200, {
                "image_url": "%s://%s/img/%s.bin" % (
                    self.args.image_url_scheme, host, digest),
                "image_hash": "sha256:" + digest,
                # Phase 10 (D-01): used to be the fixed --sleep CLI value
                # (fed by SKYPANE_SLEEP_S in the deployed unit). It is now
                # that same base value, extended when this poll lands
                # inside the window the companion Settings page saved into
                # device_config.json - no deployment or env change is
                # required, SKYPANE_SLEEP_S remains the base, and deploy/
                # is untouched by this phase.
                # Phase 11 (D-01/D-03): the base value fed into the
                # quiet-hours extension above is no longer the fixed
                # --sleep CLI value itself - it is the companion Settings
                # page's saved wake_interval_s when one is set, falling
                # back to --sleep (fed by SKYPANE_SLEEP_S in the deployed
                # unit) when it is not. The quiet-hours extension still
                # layers on top of whichever base wins; no deployment, env
                # or firmware change is required.
                # Phase 12 (D-01/D-05): display_off_sleep_s() sits between
                # read_wake_interval_s() and quiet_hours_sleep_s(),
                # replacing the wake-interval-derived base with the fixed
                # DISPLAY_OFF_SLEEP_S (300) whenever display_enabled is
                # False. The nesting order below is deliberate and must
                # not be swapped: composed as
                # quiet_hours_sleep_s(display_off_sleep_s(...), ...), the
                # 300s pin becomes quiet_hours_sleep_s()'s own base, so its
                # existing max(base_sleep_s, remaining) produces
                # max(300, quiet_hours_remaining) - the display toggle and
                # quiet hours can overlap without either one shortening the
                # device's sleep below what the other alone would have
                # given it (D-05's sleep axis). Composed the other way
                # round, an active quiet-hours window would be overwritten
                # by a flat 300s and the device would wake all night with
                # the display off. See display_off_sleep_s()'s own
                # docstring for the full reasoning, and
                # stub-server/test_poll_cycle.py for an executed negative
                # control proving the inverted order fails.
                "sleep_s": quiet_hours_sleep_s(
                    display_off_sleep_s(
                        read_wake_interval_s(self.args.state_dir, self.args.sleep),
                        self.args.state_dir),
                    self.args.state_dir),
                "firmware": None,
                "reset": False,
                # DEVICE-05 bring-up LED toggle: originally a hardcoded
                # constant, not a per-device setting - there was no store,
                # no endpoint and no web control behind it yet. It shipped
                # that way anyway because the firmware half of this toggle
                # can only be changed by physically reflashing the board,
                # while this server-side half can be redeployed any
                # afternoon - so putting the field on the wire early made
                # the eventual real per-device setting (CFG-01..CFG-04) a
                # server-only change with no reflash required. Phase 06.2
                # closes that gap: the value below now comes from the
                # shared device_config.json document written by the
                # companion app's Config page (server/device_config.py's
                # save_device_config()), not a hardcoded literal.
                "led_enabled": read_led_enabled(self.args.state_dir),
            })
        if self.path.startswith("/img/"):
            try:
                with open(self.args.image, "rb") as fh:
                    image = fh.read()
            except OSError:
                return self.send_json(503, {"detail": "image unreadable"})
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(image)))
            self.end_headers()
            self.wfile.write(image)
            return None
        return self.send_json(404, {"detail": "unknown endpoint"})

    def log_message(self, fmt, *fmt_args):
        print("%s %s" % (self.command, self.path))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True,
                    help="960,000-byte panel image to serve")
    ap.add_argument("--port", type=int, default=8642)
    ap.add_argument("--secret", default="",
                    help="require this BYOS setup secret (default: any)")
    ap.add_argument("--sleep", type=int, default=3600,
                    help="sleep_s handed to the frame (default 3600)")
    ap.add_argument("--state-dir", default=None,
                    help="parent directory for byos_state.json "
                         "(default: the directory containing this script)")
    ap.add_argument("--image-url-scheme", choices=["http", "https"],
                    default="http",
                    help="scheme advertised in the /device/v1/display "
                         "response's image_url (default: http). Leave at "
                         "http for the local Phase 1 stub flow on the LAN; "
                         "set to https for a deployment fronted by a "
                         "TLS-terminating reverse proxy (e.g. Caddy), so "
                         "the panel download is not silently downgraded "
                         "to plaintext.")
    args = ap.parse_args()
    if not os.path.exists(args.image):
        sys.exit("no such image: %s" % args.image)
    if args.state_dir is None:
        args.state_dir = os.path.dirname(os.path.abspath(__file__))
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    Handler.state = load_state(args.state_dir)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("serving %s on port %d — point the frame at http://<this-host>:%d"
          % (args.image, args.port, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()
