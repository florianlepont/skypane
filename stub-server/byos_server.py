#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 YODE PTE LTD
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
# Modified from FlightPortrait (github.com/flightportrait/frame) for
# SkyPane; the changes are listed in stub-server/VENDOR.md. Full licence
# text: firmware/LICENSE.
"""Minimal bring-your-own-server for FlightPortrait frames. Stdlib only.

Implements the three device endpoints from docs/PROTOCOL.md well enough
to run a stock frame: point the frame at this host during BLE
provisioning (PROTOCOL.md §5) and it will set up, poll, download, and
display whatever panel image you serve.

    python3 byos_server.py --image path/to/panel.bin [--port 8642]
        [--sleep 3600] [--state-dir DIR] [--image-url-scheme http|https]

The image must be exactly 960,000 bytes in the PROTOCOL.md §1 format
(the calibration patterns in first-flash/bins/ work); swap the file on
disk and the next poll serves the new content via its hash. Enrolment
is gated by a per-device registry (devices.json in --state-dir maps
each MAC to the SHA-256 of its own enrolment secret, managed with
stub-server/devices_cli.py); a missing or unreadable registry refuses
every enrolment rather than falling back to open. Issued tokens live
in byos_state.json inside --state-dir, so restarts don't strand frames.

GET /device/v1/display's sleep_s is the companion app's saved
wake_interval_s (or --sleep), composed with three overrides in order: a
fixed off-state cadence while display_enabled is false, a fixed parked
cadence while server/poll_loop.py's battery-empty hold is active
(unless this poll's own X-Battery-Mv already reports recovery), and an
extension spanning the saved quiet-hours window. led_enabled mirrors
the companion app's saved bring-up-LED setting; --image-url-scheme lets
image_url advertise https behind a TLS-terminating reverse proxy.

This is a reference, not a product: no TLS (the frame accepts plain
http for hand-set targets), no rate limiting, one image for every
frame. See stub-server/VENDOR.md for the local changes from upstream
FlightPortrait.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# zoneinfo is stdlib since Python 3.9 - this module's "Stdlib only" claim
# above stays true.
from zoneinfo import ZoneInfo

IMAGE_BYTES = 960000
# X-Battery-Mv bounds: PROTOCOL.md §2 reserves 0 as the "unknown" sentinel,
# so it must be rejected rather than persisted; the ceiling sits above any
# single-cell LiPo (4200 mV full charge).
BATTERY_MV_MIN = 1
BATTERY_MV_MAX = 10000

# Quiet-hours HH:MM shape gate, kept in lockstep with server/device_config.py's
# own _HHMM_RE (see the vendor-boundary note above seconds_until_quiet_hours_end()).
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")

# One fixed physical location, so the quiet-hours timezone is hardcoded
# here, matching server/device_config.py's own QUIET_HOURS_TZ.
QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

# wake_interval_s bounds, redefined here (never imported - see the
# vendor-boundary note below) and kept numerically equal by hand to
# server/device_config.py's WAKE_INTERVAL_MIN_S/MAX_S; not covered by the
# byte-for-byte drift guard, which pins only the arithmetic core and regex.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600

# Off-state check-in cadence while display_enabled is false, mirrored by
# hand from server/device_config.py's DISPLAY_OFF_SLEEP_S; a bare integer,
# so a lighter parity check covers it instead of the drift guard above.
DISPLAY_OFF_SLEEP_S = 300

# Parked cadence while server/poll_loop.py's battery-empty hold is active,
# and the recovery-mv threshold, both mirrored by hand from that module's
# constants of the same name/value - byos only anticipates a recovery
# already reported in the poll it is answering, never decides to park.
BATTERY_CRITICAL_SLEEP_S = 3600
BATTERY_CRITICAL_RECOVER_MV = 3700


def _read_umask():
    """Return the process umask without racing another thread's
    umask-sensitive open() the way os.umask(0)/os.umask(old) read-then-
    restore would. Mirrors server/atomic_io.py's helper of the same name
    byte-for-byte in intent (a local copy - see _atomic_write below for
    why); a behaviour-parity test in test_byos_hardening.py pins the two
    to the same observable default mode.
    """
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("Umask:"):
                    return int(line.split(":", 1)[1].strip(), 8)
    except OSError:
        pass
    old = os.umask(0)
    os.umask(old)
    return old


# open(path, "w") on a fresh path has always produced 0o666 & ~umask; this
# is _atomic_write's default so migrating a caller from open() to
# _atomic_write() does not silently change its file's mode.
_DEFAULT_FILE_MODE = 0o666 & ~_read_umask()


def _atomic_write(path, data, mode=None):
    """Write `data` (bytes, or str encoded as UTF-8) to `path` via a
    same-directory unique-name temp file, fsync, then os.replace -
    never a partial write, never a stray temp file left behind on any
    failure. This is a local copy of server/atomic_io.py's atomic_write()
    with the same observable contract (unique temp name, requested mode
    set on the temp file's descriptor before any byte is written, never
    chmod'ed after the rename, fsynced before the rename, temp removed
    and the exception re-raised on any failure) - byos must never import
    server.* (stub-server/VENDOR.md's vendor boundary); a behaviour-
    parity test in test_byos_hardening.py pins the two to the same
    contract instead of a source-text drift guard.
    """
    if isinstance(data, str):
        payload = data.encode("utf-8")
    elif isinstance(data, bytes):
        payload = data
    else:
        raise TypeError(
            "byos_server._atomic_write: data must be bytes or str, got %s"
            % type(data).__name__)

    directory = os.path.dirname(path) or "."
    prefix = "." + os.path.basename(path) + "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".tmp")
    try:
        os.fchmod(fd, mode if mode is not None else _DEFAULT_FILE_MODE)
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        # os.fdopen's own `with` already closed fd if it got that far;
        # closing it again raises, which the failed write should not mask.
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

    committed = False
    try:
        os.replace(tmp, path)
        committed = True
    finally:
        if not committed:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def state_path(state_dir):
    return os.path.join(state_dir, "byos_state.json")


def load_state(state_dir):
    try:
        with open(state_path(state_dir)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}


def save_state(state_dir, state):
    _atomic_write(state_path(state_dir), json.dumps(state, indent=1))


# --- Per-device enrolment registry -----------------------------------
#
# Maps each MAC to the SHA-256 hex digest of its own enrolment secret,
# never the secret itself: {"devices": {mac: {"secret_sha256": hex}}}.
# Closes the gap a single shared --secret left open - anyone who learned
# the one shared value could re-enrol (and hijack) any device. Re-enrolling
# a MAC requires that MAC's own secret; a wrong one (including another
# device's) leaves the existing token untouched.
REGISTRY_FILE = "devices.json"

_MAC_RE = re.compile(r"\A([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\Z")
_SHA256_HEX_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def registry_path(state_dir):
    return os.path.join(state_dir, REGISTRY_FILE)


def normalize_mac(value):
    """Return `value` lowercased as "aa:bb:cc:dd:ee:ff", or None for
    anything not a str matching six colon-separated hex byte pairs, so
    a malformed or hostile mac field degrades to a 422 instead of a 500.
    """
    if not isinstance(value, str) or not _MAC_RE.match(value):
        return None
    return value.lower()


def load_registry(state_dir):
    """Load <state_dir>/devices.json as {"devices": {mac: {"secret_sha256": hex}}}.
    Fails CLOSED (the opposite of load_state()'s fail-open contract
    above): any missing, unreadable, malformed, or wrongly-shaped
    document returns an empty registry, so corruption enrols nobody
    rather than everybody.
    """
    try:
        with open(registry_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {"devices": {}}
    if not isinstance(data, dict) or not isinstance(data.get("devices"), dict):
        return {"devices": {}}
    return data


def save_registry(state_dir, registry):
    """Atomically write `registry` to devices.json via _atomic_write with
    mode=0o600 (set on the temp file's descriptor before any byte is
    written, never chmod'ed after the rename, so the registry is never
    briefly world-readable). Holds only SHA-256 hashes, never a plaintext
    secret.
    """
    _atomic_write(registry_path(state_dir), json.dumps(registry, indent=1), mode=0o600)


def register_device(state_dir, mac, secret_sha256, replace=False):
    """Add (or, with replace=True, overwrite) one MAC's registry entry.
    Returns the normalized MAC. Raises ValueError for a malformed
    mac/secret_sha256, or for an already-registered MAC when replace is
    False - devices_cli.py turns that into a non-zero exit rather than
    a silent no-op or accidental overwrite.
    """
    normalized = normalize_mac(mac)
    if normalized is None:
        raise ValueError("not a MAC address: %r" % (mac,))
    if not isinstance(secret_sha256, str) or not _SHA256_HEX_RE.match(secret_sha256):
        raise ValueError(
            "secret_sha256 must be 64 lowercase hex characters: %r" % (secret_sha256,))
    registry = load_registry(state_dir)
    if normalized in registry["devices"] and not replace:
        raise ValueError(
            "%s is already registered (pass replace=True to overwrite)" % normalized)
    registry["devices"][normalized] = {"secret_sha256": secret_sha256}
    save_registry(state_dir, registry)
    return normalized


def secret_matches(registry, mac, presented):
    """True only if `mac` is registered AND `presented` is 64 lowercase
    hex characters whose SHA-256 equals the hash registered for that
    MAC, compared with hmac.compare_digest (never `==`, which would leak
    timing information about the matching prefix length).
    """
    if not isinstance(presented, str) or not re.fullmatch(r"[0-9a-f]{64}", presented):
        return False
    entry = registry["devices"].get(mac)
    if not isinstance(entry, dict):
        return False
    stored = entry.get("secret_sha256")
    if not isinstance(stored, str):
        return False
    presented_hash = hashlib.sha256(presented.encode("ascii")).hexdigest()
    return hmac.compare_digest(presented_hash, stored)


def device_config_path(state_dir):
    return os.path.join(state_dir, "device_config.json")


def read_led_enabled(state_dir):
    """Best-effort read of the shared device_config.json's led_enabled
    field. Never raises; any failure (missing/unreadable/malformed
    file, non-dict document, non-bool value) degrades to enabled,
    matching the firmware's own fail-open contract in
    firmware/main/api_client.c.
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
    """Best-effort read of the shared device_config.json's
    display_enabled field. Never raises; any failure degrades to
    enabled (True), matching server/device_config.py's
    normalise_display_enabled() - a broken config can never pin a
    healthy device to the off-state cadence, or darken a frame whose
    config merely failed to load.
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


def read_battery_critical(state_dir):
    """Best-effort, read-only read of poll_state.json's
    battery_critical_active latch (server/poll_loop.py's
    apply_battery_critical_hysteresis() is the sole writer). Never
    raises; any failure degrades to False - a wrong False costs a few
    extra wakes, never a missed BATTERY EMPTY render, which remains
    poll_loop's own responsibility. Mirrors
    server.wake.read_battery_critical() field-for-field (this file must
    never import that module).
    """
    try:
        with open(os.path.join(state_dir, "poll_state.json")) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    return data.get("battery_critical_active") is True


def read_wake_interval_s(state_dir, default):
    """Best-effort read of the shared device_config.json's
    wake_interval_s field. Never raises; any failure - including a
    bool value (isinstance(True, int) is True in Python, so a bare int
    test would let a JSON `true` become a deep-sleep duration) or one
    outside [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] - degrades to
    `default`, the caller's `--sleep` CLI value.
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


# --- Quiet-hours sleep_s extension --------------------------------------
#
# seconds_until_quiet_hours_end() below is a byte-for-byte duplicate of
# server/device_config.py's function of the same name - this file must
# never import a server.* module (breaks the "Stdlib only" claim above
# and blurs the vendor boundary stub-server/VENDOR.md tracks). Pinned
# equal by a drift guard in stub-server/test_poll_cycle.py; change one,
# change the other identically, in the same commit.
def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Seconds remaining until the daily [start_hm, end_hm) Europe/Paris
    window's end, or None when `now_utc` falls outside it. Wraps midnight
    when `end_hm <= start_hm`; a zero-width window (`start_hm == end_hm`)
    is never active.

    Arithmetic core only, no validation: `now_utc` must be timezone-aware;
    `start_hm`/`end_hm` must already match `_HHMM_RE`.
    stub-server/byos_server.py duplicates this byte-for-byte.

    Two DST-safety properties: (a) the final subtraction converts to UTC
    first (`end_dt.astimezone(timezone.utc) - now_utc`), since two aware
    datetimes sharing a `tzinfo` subtract by wall-clock numerals only,
    which is wrong by an hour across a DST transition; (b) a boundary
    configured inside the 02:00-03:00 transition hour can resolve up to
    an hour off (PEP 495 `fold=0`, accepted, not engineered around).
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
    fields. Never raises; any failure - including `quiet_hours_enabled`
    not literally `True`, or either bound failing
    `isinstance(value, str) and _HHMM_RE.match(value)` - degrades to
    `None` (quiet hours not in effect), so a corrupted config can never
    take down the always-on /device/v1/display service. Returns
    `(start_hm, end_hm)` when every check passes, otherwise `None`.
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
    `base_sleep_s` unchanged - a flat replacement, not a max()/min(),
    since the pin must both shorten a long configured interval and
    lengthen a short one while off.

    Composition order is load-bearing: this result must be passed as
    quiet_hours_sleep_s()'s own base, never the reverse - inverted, an
    active quiet-hours window would be overwritten by the flat 300s and
    the device would wake all night with the display off.
    """
    if read_display_enabled(state_dir) is False:
        return DISPLAY_OFF_SLEEP_S
    return base_sleep_s


def battery_critical_sleep_s(base_sleep_s, state_dir, fresh_battery_mv):
    """Return the sleep_s to feed into quiet_hours_sleep_s() as its base:
    exactly BATTERY_CRITICAL_SLEEP_S (3600) while poll_loop.py's
    battery-empty hold is active, unless `fresh_battery_mv` (this
    request's own X-Battery-Mv) already signals recovery at or above
    BATTERY_CRITICAL_RECOVER_MV, in which case `base_sleep_s` wins.

    poll_loop.py clears its latch up to 30s after the recovering
    check-in this request represents, so a plain latch read would still
    see the stale True; `fresh_battery_mv` anticipates that recovery
    instead, without writing anything itself.

    Composition order is load-bearing, extending display_off_sleep_s()'s
    contract: nested INSIDE quiet_hours_sleep_s() but OUTSIDE
    display_off_sleep_s().
    """
    if read_battery_critical(state_dir) is not True:
        return base_sleep_s
    if fresh_battery_mv is not None and fresh_battery_mv >= BATTERY_CRITICAL_RECOVER_MV:
        return base_sleep_s
    return BATTERY_CRITICAL_SLEEP_S


def quiet_hours_sleep_s(base_sleep_s, state_dir, now=None):
    """Return the sleep_s for GET /device/v1/display: `base_sleep_s`
    unchanged unless a poll lands inside an enabled quiet-hours window,
    in which case it's extended to span the window's remaining local
    end time - the sole mechanism that pauses the device.

    `now` defaults to `datetime.now(timezone.utc)`; an injectable seam
    for deterministic DST/boundary tests.

    `max(base_sleep_s, remaining)` is load-bearing: quiet hours must
    never make the device sleep for LESS time than it otherwise would.
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

    Rejects anything but a string of 1-5 ASCII digit characters (no
    whitespace, no sign - a well-formed device sends bare digits), then
    rejects anything outside BATTERY_MV_MIN..BATTERY_MV_MAX.
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
    battery_state.json via _atomic_write (unique temp name, fsync,
    os.replace). The only writer of that file anywhere in the repo -
    server/poll_loop.py only reads it, avoiding a read-modify-write
    race between two processes on one JSON file.
    """
    path = battery_state_path(state_dir)
    _atomic_write(path, json.dumps({"battery_mv": mv, "received_at": time.time()}, indent=1))


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
            mac = normalize_mac(body.get("mac")) if isinstance(body, dict) else None
            if mac is None:
                return self.send_json(422, {"detail": "bad body"})
            # Load fresh on every request (not cached on self.args), so a
            # devices_cli.py add/remove takes effect for the very next
            # setup call with no service restart required.
            registry = load_registry(self.args.state_dir)
            if mac not in registry["devices"]:
                print("setup: %s refused (not registered)" % mac)
                return self.send_json(403, {"detail": "device not registered"})
            if not secret_matches(registry, mac, body.get("provision_secret")):
                print("setup: %s refused (bad secret)" % mac)
                return self.send_json(401, {"detail": "bad secret"})
            token = secrets.token_hex(32)
            self.state["tokens"][mac] = token
            save_state(self.args.state_dir, self.state)
            print("setup: %s enrolled (hw_rev=%s)"
                  % (mac, body.get("hw_rev", "?")))
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
            # Strictly after the bearer_ok() gate above, so an
            # unauthenticated or wrong-token caller can never pin a
            # victim frame's panel into a permanent low-battery warning.
            # A telemetry side-effect must never turn a healthy panel
            # poll into a 500 - a full or read-only state directory
            # degrades to "no battery signal", which poll_loop.py
            # already treats as legitimate (this is the only place
            # battery_state.json is written).
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
                # sleep_s composes, in order: the companion Settings page's
                # saved wake_interval_s (falling back to --sleep), the flat
                # off-state cadence while display_enabled is false, the
                # flat parked cadence while poll_loop's battery-empty hold
                # is active (unless this poll's own battery_mv already
                # reports recovery), and the quiet-hours extension.
                # Composition order is load-bearing - see each function's
                # own docstring above; do not reorder the calls below.
                "sleep_s": quiet_hours_sleep_s(
                    battery_critical_sleep_s(
                        display_off_sleep_s(
                            read_wake_interval_s(self.args.state_dir, self.args.sleep),
                            self.args.state_dir),
                        self.args.state_dir, battery_mv),
                    self.args.state_dir),
                "firmware": None,
                "reset": False,
                # The bring-up LED toggle: the firmware half can only be
                # changed by reflashing the board, while this server-side
                # half comes from the shared device_config.json document
                # written by the companion app's Config page
                # (server/device_config.py's save_device_config()).
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
                    help="retired: ignored; enrolment uses the per-device "
                         "registry (devices.json)")
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
    if args.secret:
        # Accepted-and-ignored rather than removed outright, so a systemd
        # unit still passing the old flag (mid-migration) starts cleanly
        # instead of crash-looping on an unrecognized argument.
        print("WARNING: --secret is retired and grants nothing; register "
              "devices with stub-server/devices_cli.py instead (writes "
              "devices.json in --state-dir)", file=sys.stderr)
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    Handler.state = load_state(args.state_dir)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("serving %s on port %d — point the frame at http://<this-host>:%d"
          % (args.image, args.port, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()
