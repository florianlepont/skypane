#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 YODE PTE LTD
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
# Modified from FlightPortrait (github.com/flightportrait/frame) for
# SkyPane; the changes are listed in stub-server/VENDOR.md. Full licence
# text: firmware/LICENSE.
"""Minimal bring-your-own-server for FlightPortrait frames. Stdlib only,
plus the stdlib-only shared modules server.device_policy, server.state_store
and server.firmware_registry.

Implements the three device endpoints from docs/PROTOCOL.md well enough
to run a stock frame: point the frame at this host during BLE
provisioning (PROTOCOL.md §5) and it will set up, poll, download, and
display whatever panel image you serve.

    python3 byos_server.py --image path/to/panel.bin [--port 8642]
        [--sleep 3600] [--state-dir DIR] [--image-url-scheme http|https]

The image must be exactly 960,000 bytes in the PROTOCOL.md §1 format
(the calibration patterns in first-flash/bins/ work); swap the file on
disk and the next poll advertises the new content's own hash. Each
GET /device/v1/display publishes the served image under
<state-dir>/img/<sha256>.bin (content-addressed, keeping the newest
IMG_KEEP files) before answering, so GET /img/<sha>.bin always serves
exactly the bytes that hash names, even if the on-disk --image changes
before the device downloads; any other /img/ path, or a hash never
published, is 404. Enrolment is gated by a per-device registry
(devices.json in --state-dir maps
each MAC to the SHA-256 of its own enrolment secret, managed with
stub-server/devices_cli.py); a missing or unreadable registry refuses
every enrolment rather than falling back to open. Issued tokens live
in byos_state.json inside --state-dir, so restarts don't strand frames.

GET /device/v1/display's sleep_s is the companion app's saved
wake_interval_s (or --sleep), composed with three overrides in order: a
fixed off-state cadence while display_enabled is false, a fixed parked
cadence while server/poll_cycle.py's battery-empty hold is active
(unless this poll's own X-Battery-Mv already reports recovery), and an
extension spanning the saved quiet-hours window. led_enabled mirrors
the companion app's saved bring-up-LED setting; --image-url-scheme lets
image_url advertise https behind a TLS-terminating reverse proxy.

The same response's firmware field is the operator's scheduled release,
or null, computed by server/firmware_registry.py's compute_offer() from
the request's own X-Fw-Version/X-Ota-Result headers, which this file
records into <state-dir>/firmware/device_report.json. A served release
image is fetched from GET /fw/<sha256>.bin, content-addressed against
that same registry; any other name, or a sha never published, is 404 -
unlike /img/, nothing here prunes a release image once published.

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
import stat
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Repo-root sys.path bootstrap, the same shape server/poll_loop.py and
# server/state_store.py use: the deployed layout already ships server/
# next to stub-server/ (deploy/skypane-byos.service's WorkingDirectory),
# so this always resolves from the file's own location, never a
# cwd-relative path. Insert only if absent - devices_cli.py and the test
# harnesses below may load this file more than once per process.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_policy, firmware_registry, state_store

IMAGE_BYTES = 960000
# X-Battery-Mv bounds: PROTOCOL.md §2 reserves 0 as the "unknown" sentinel,
# so it must be rejected rather than persisted; the ceiling sits above any
# single-cell LiPo (4200 mV full charge).
BATTERY_MV_MIN = 1
BATTERY_MV_MAX = 10000

# Quiet-hours HH:MM shape gate, the quiet-hours timezone, the
# wake_interval_s bounds, the off-state check-in cadence and the
# battery-critical parked cadence/recovery threshold: bindings to
# server/device_policy.py's shared objects, kept under these historical
# names since the handlers below, devices_cli.py and the tests still
# resolve them here.
_HHMM_RE = device_policy.HHMM_RE
QUIET_HOURS_TZ = device_policy.QUIET_HOURS_TZ
WAKE_INTERVAL_MIN_S = device_policy.WAKE_INTERVAL_MIN_S
WAKE_INTERVAL_MAX_S = device_policy.WAKE_INTERVAL_MAX_S
DISPLAY_OFF_SLEEP_S = device_policy.DISPLAY_OFF_SLEEP_S
BATTERY_CRITICAL_SLEEP_S = device_policy.BATTERY_CRITICAL_SLEEP_S
BATTERY_CRITICAL_RECOVER_MV = device_policy.BATTERY_CRITICAL_RECOVER_MV


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
    and the exception re-raised on any failure) - kept as a local copy
    for the files byos alone owns (byos_state.json, devices.json,
    img/*.bin), independent of the shared server.device_policy and
    server.state_store modules this file now imports for quiet-hours,
    battery-critical policy and the poll_state.json latch read; a
    behaviour-parity test in test_byos_hardening.py pins this copy and
    server/atomic_io.py's to the same contract instead of a source-text
    drift guard.
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


# Best-effort, read-only read of poll_state.json's battery_critical_active
# latch (server/device_policy.py's apply_battery_critical_hysteresis(),
# called from server/poll_cycle.py's load_cycle_context(), is the
# sole writer); fail-open to False on any read failure - a wrong False
# costs a few extra wakes, never a missed BATTERY EMPTY render, which
# remains poll_cycle's own responsibility. The one shared reader server/
# state_store.py and this file both use.
read_battery_critical = state_store.read_battery_critical


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
# The shared arithmetic core: seconds remaining until the daily
# [start_hm, end_hm) Europe/Paris window's end, or None when `now_utc`
# falls outside it. server/device_policy.py's own docstring has the full
# DST-safety notes (fold=0 accepted, not engineered around).
seconds_until_quiet_hours_end = device_policy.seconds_until_quiet_hours_end


def read_quiet_hours(state_dir):
    """Best-effort read of the shared device_config.json's quiet-hours
    fields, then device_policy.quiet_hours_window()'s shared fallback
    rule. Never raises; a missing/unreadable/malformed device_config.json
    or a non-dict document degrades to `None` (quiet hours not in
    effect), so a corrupted config can never take down the always-on
    /device/v1/display service.

    An invalid stored bound (wrong shape, wrong type, or missing) no
    longer disables quiet hours here: it falls back to the default
    23:00-07:00 window instead, independently per bound - the same rule
    server/poll_cycle.py's hold decision uses, so a corrupted or
    hand-edited quiet-hours time now extends the device's sleep rather
    than silently letting it poll through the night.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return device_policy.quiet_hours_window(data)


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
    exactly BATTERY_CRITICAL_SLEEP_S (3600) while poll_cycle.py's
    battery-empty hold is active, unless `fresh_battery_mv` (this
    request's own X-Battery-Mv) already signals recovery at or above
    BATTERY_CRITICAL_RECOVER_MV, in which case `base_sleep_s` wins.

    poll_cycle.py clears its latch up to 30s after the recovering
    check-in this request represents, so a plain latch read would still
    see the stale True; `fresh_battery_mv` anticipates that recovery
    instead, without writing anything itself.

    Composition order is load-bearing, extending display_off_sleep_s()'s
    contract: nested INSIDE quiet_hours_sleep_s() but OUTSIDE
    display_off_sleep_s().

    The pin rule itself is device_policy.battery_critical_pin_applies():
    the one canonical latched/fresh-reading truth table this file and
    the poll cycle both apply.
    """
    if device_policy.battery_critical_pin_applies(read_battery_critical(state_dir), fresh_battery_mv):
        return BATTERY_CRITICAL_SLEEP_S
    return base_sleep_s


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


IMG_DIRNAME = "img"
# The newest N published panel images kept on disk; a poll that lands
# between more than this many distinct panels in one wake would see a
# 404 on download, retried like any other failed download - the
# firmware treats it exactly the same as a stale server.
IMG_KEEP = 8

_IMG_NAME_RE = re.compile(r"\A[0-9a-f]{64}\.bin\Z")
_IMG_PATH_RE = re.compile(r"\A/img/([0-9a-f]{64})\.bin\Z")

# Matched against the raw request path (never a query-stripped copy), so
# a query string, a trailing extra path segment, or an uppercase digest
# never matches - all fall through to the generic 404 below rather than
# reaching firmware_image_path() with an unvalidated string.
_FW_PATH_RE = re.compile(r"\A/fw/([0-9a-f]{64})\.bin\Z")
# 64 KiB, matching server/firmware_registry.py's own hashing chunk size -
# a release image is never held in memory all at once.
_FW_STREAM_CHUNK_BYTES = 65536


def _img_dir(state_dir):
    return os.path.join(state_dir, IMG_DIRNAME)


def _publish_image(state_dir, digest, image):
    """Ensure <state_dir>/img/<digest>.bin holds `image`'s bytes and is
    the newest file in img/ (so a re-advertised digest survives
    pruning), then prune img/ down to IMG_KEEP files. Raises OSError on
    any filesystem failure (a full or read-only state dir) - the caller
    must answer 503 rather than advertise a hash it cannot serve.
    """
    img_dir = _img_dir(state_dir)
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(img_dir, "%s.bin" % digest)
    if os.path.exists(path):
        os.utime(path, None)
    else:
        _atomic_write(path, image)
    _prune_images(img_dir, keep_digest=digest)


def _prune_images(img_dir, keep_digest):
    """Keep at most IMG_KEEP files in img/, newest by mtime first, and
    never remove `keep_digest`'s file even if it is not among the
    newest IMG_KEEP by mtime. Names not matching _IMG_NAME_RE are
    ignored (never counted, never removed); a file removed by a
    concurrent pruner is tolerated.
    """
    try:
        names = [name for name in os.listdir(img_dir) if _IMG_NAME_RE.match(name)]
    except OSError:
        return

    def _mtime(name):
        try:
            return os.stat(os.path.join(img_dir, name)).st_mtime
        except OSError:
            return -1.0

    names.sort(key=_mtime, reverse=True)
    keep_name = "%s.bin" % keep_digest
    survivors = names[:IMG_KEEP]
    if keep_name not in survivors:
        survivors = survivors[:max(0, IMG_KEEP - 1)] + [keep_name]
    for name in names:
        if name in survivors:
            continue
        try:
            os.remove(os.path.join(img_dir, name))
        except FileNotFoundError:
            pass


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
    server/poll_cycle.py only reads it (via server/state_store.py's
    load_battery_state()), avoiding a read-modify-write race between
    two processes on one JSON file.
    """
    path = battery_state_path(state_dir)
    _atomic_write(path, json.dumps({"battery_mv": mv, "received_at": time.time()}, indent=1))


# --- OTA offer composition and device report recording -------------------
#
# firmware/device_report.json is owned by this file alone --
# server/firmware_registry.py only ever reads it (see that module's own
# docstring). Every write below goes through _write_device_report(),
# guarded by _device_report_lock against this process's own other
# request-handling threads; no inter-process file lock is added on top,
# since this file is the document's only writer anywhere in the
# deployment.
_device_report_lock = threading.Lock()

# The device-reported firmware version, one to 31 of the same characters
# server/firmware_registry.py's own VERSION_RE allows for a release tag --
# permissive enough for a bench build's free-form suffix too.
_FW_VERSION_HEADER_RE = re.compile(r"\A[A-Za-z0-9._-]{1,31}\Z")

# X-Ota-Result: "<result token>;<version>", the token one of
# firmware_registry.RESULT_TOKENS, the version 1-31 of the same
# characters X-Fw-Version allows. The whole header is capped at 64 bytes
# so a hostile or buggy device cannot grow device_report.json's events
# without bound through this one field.
_OTA_RESULT_HEADER_RE = re.compile(
    r"\A(" + "|".join(re.escape(t) for t in firmware_registry.RESULT_TOKENS) + r");"
    r"([A-Za-z0-9._-]{1,31})\Z"
)
_OTA_RESULT_HEADER_MAX_BYTES = 64

# The newest events kept per device in firmware/device_report.json --
# matches server/firmware_registry.py's own defensive re-cap on load, so
# a value trimmed here on write is never re-expanded by the next read.
_DEVICE_REPORT_EVENTS_KEEP = 50


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_fw_version_header(raw):
    """The device's reported X-Fw-Version, or None for anything not 1-31
    of the allowed version characters -- a malformed header is ignored,
    never recorded.
    """
    if not isinstance(raw, str) or not _FW_VERSION_HEADER_RE.match(raw):
        return None
    return raw


def parse_ota_result_header(raw):
    """(result token, version) parsed from a device's X-Ota-Result
    header, or None for anything unanchored, over the byte cap, an
    unrecognised result token, or a malformed version component.
    """
    if not isinstance(raw, str) or len(raw) > _OTA_RESULT_HEADER_MAX_BYTES:
        return None
    match = _OTA_RESULT_HEADER_RE.match(raw)
    if match is None:
        return None
    return match.group(1), match.group(2)


def read_battery_low_active(state_dir):
    """Best-effort, read-only read of poll_state.json's battery_low_active
    flag (server/poll_cycle.py's update_battery_low() is the sole
    writer). Fails open to False: a wrongly-served offer during a real
    low-battery window costs a wasted download attempt, while a false
    positive here only delays an update the operator already approved
    to the device's next wake.
    """
    return state_store.load_poll_state(state_dir).get("battery_low_active") is True


def _resolve_device_id(state, presented_token):
    """The MAC byos issued `presented_token` to, compared with
    hmac.compare_digest against every stored token (never `==`, the same
    timing reason bearer_ok() above already gives), or "default" when
    none matches. Only ever called after bearer_ok() has already
    confirmed the token is valid, so this decides which device's
    device_report.json entry a poll updates, not whether it may.
    """
    if not isinstance(presented_token, str):
        return "default"
    presented_bytes = presented_token.encode("utf-8", "surrogateescape")
    for mac, stored in state["tokens"].items():
        stored_bytes = stored.encode("utf-8", "surrogateescape")
        if hmac.compare_digest(presented_bytes, stored_bytes):
            return mac
    return "default"


def _write_device_report(state_dir, doc):
    """The one writer of firmware/device_report.json anywhere in this
    process -- server/firmware_registry.py deliberately never writes it.
    Mirrors that module's own firmware/ directory mode fix-up, since
    either module may be the first to create it under a fresh state
    dir.
    """
    path = firmware_registry.device_report_path(state_dir)
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory, mode=0o750, exist_ok=True)
        os.chmod(directory, 0o750)
    _atomic_write(path, json.dumps(doc, indent=1, sort_keys=True))


def _record_device_report_and_offer(state_dir, state, headers, image_url_scheme, host):
    """The single call GET /device/v1/display makes for the whole OTA
    offer contract: parse this request's X-Fw-Version/X-Ota-Result,
    resolve which device sent it, update firmware/device_report.json
    (fw_version/reported_at, a "result" event), compute the offer from
    the now-current entry, and -- when an offer results -- record an
    "offered" event for it before returning, so a schedule the device
    has just been offered is no longer cancellable from that instant.
    Any failure raised by the write below is the caller's to treat as
    no offer, never an error response; the registry/device-report reads
    this function makes are already tolerant and never raise.
    """
    fw_version = parse_fw_version_header(headers.get("X-Fw-Version"))
    ota_result = parse_ota_result_header(headers.get("X-Ota-Result"))
    auth = headers.get("Authorization", "")
    presented = auth[len("Bearer "):] if auth.startswith("Bearer ") else None
    device_id = _resolve_device_id(state, presented)

    registry = firmware_registry.load_registry(state_dir)
    battery_low_active = read_battery_low_active(state_dir)
    base_url = "%s://%s" % (image_url_scheme, host)
    schedule = registry.get("schedule")
    schedule_id = schedule.get("id") if schedule is not None else None

    with _device_report_lock:
        device_report = firmware_registry.load_device_report(state_dir)
        devices = device_report["devices"]
        entry = devices.get(device_id) or {"fw_version": None, "reported_at": None, "events": []}
        # device_report["next_seq"] counts events already assigned (0 for
        # a fresh document), so the next seq to hand out is one more than
        # that - never 0, since compute_offer()'s own reconciled_seq
        # baseline starts at 0 and only counts events with seq strictly
        # greater than it.
        next_seq = device_report["next_seq"]
        changed = False

        if fw_version is not None:
            entry["fw_version"] = fw_version
            entry["reported_at"] = _utc_now_iso()
            changed = True

        if ota_result is not None:
            token, result_version = ota_result
            next_seq += 1
            entry["events"].append({
                "seq": next_seq, "at": _utc_now_iso(), "kind": "result",
                "schedule_id": schedule_id, "token": token, "version": result_version,
            })
            changed = True

        offer = firmware_registry.compute_offer(registry, entry, battery_low_active, base_url)
        if offer is not None:
            next_seq += 1
            entry["events"].append({
                "seq": next_seq, "at": _utc_now_iso(), "kind": "offered",
                "schedule_id": schedule_id, "token": None, "version": offer["version"],
            })
            changed = True

        if changed:
            entry["events"] = entry["events"][-_DEVICE_REPORT_EVENTS_KEEP:]
            devices[device_id] = entry
            device_report["next_seq"] = next_seq
            _write_device_report(state_dir, device_report)

    return offer


# Largest legitimate device body (a batched log upload); anything above
# this is refused with 413 before a single byte of it is read.
MAX_BODY_BYTES = 64 * 1024

# Applied to every accepted connection's socket (StreamRequestHandler.setup()
# reads this class attribute) so a client that stops sending mid-request -
# or never sends a request line at all - cannot pin a handler thread
# forever; main() overrides it from --request-timeout.
REQUEST_TIMEOUT_S = 15.0

# Sentinel Handler.read_body_json() returns after it has already answered
# 400/413 itself for a malformed or oversized Content-Length - the caller
# must return immediately without sending a second response.
_BAD_LENGTH = object()


class Handler(BaseHTTPRequestHandler):
    server_version = "flightportrait-byos-example"
    args = None
    state = None
    timeout = REQUEST_TIMEOUT_S

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body_json(self):
        """Return the parsed JSON body, None for a body that is present
        but not valid UTF-8 JSON (or one whose nesting recurses past the
        decoder's limit), or the _BAD_LENGTH sentinel after already
        answering 400/413 for a malformed or oversized Content-Length -
        the body is never read in that case (an unbounded negative
        length would otherwise read to EOF and block; an oversized
        body's unread tail would otherwise be parsed as the start of the
        next request), and self.close_connection is set so the
        connection is not reused after either error.
        """
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            length = 0
        else:
            try:
                length = int(raw_length)
            except ValueError:
                length = -1
            if length < 0:
                self.close_connection = True
                self.send_json(400, {"detail": "bad content-length"})
                return _BAD_LENGTH
            if length > MAX_BODY_BYTES:
                self.close_connection = True
                self.send_json(413, {"detail": "body too large"})
                return _BAD_LENGTH
        try:
            return json.loads(self.rfile.read(length).decode())
        except (ValueError, UnicodeDecodeError, RecursionError):
            return None

    def bearer_ok(self):
        """True iff the presented bearer token equals one of the stored
        tokens. Every stored token is compared with hmac.compare_digest
        (no early exit on the first mismatch, so the check's timing does
        not depend on which token index would have matched), both sides
        encoded with UTF-8/surrogateescape so a non-ASCII presented value
        (an already-decoded str; the header block itself is parsed as
        Latin-1, so no byte sequence a client sends can raise here)
        degrades to "no match" instead of raising.
        """
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        presented = auth[len("Bearer "):].encode("utf-8", "surrogateescape")
        matched = False
        for stored in list(self.state["tokens"].values()):
            stored_bytes = stored.encode("utf-8", "surrogateescape")
            if hmac.compare_digest(presented, stored_bytes):
                matched = True
        return matched

    def log_telemetry(self):
        parts = []
        for h in ("X-Fw-Version", "X-Boot-Reason", "X-Rssi",
                  "X-Battery-Mv", "X-Ota-Result"):
            v = self.headers.get(h)
            if v:
                parts.append("%s=%s" % (h, v))
        if parts:
            print("  telemetry:", " ".join(parts))

    def do_POST(self):
        if self.path == "/device/v1/setup":
            body = self.read_body_json()
            if body is _BAD_LENGTH:
                return None  # read_body_json() already answered 400/413
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
            if body is _BAD_LENGTH:
                return None  # read_body_json() already answered 400/413
            if not isinstance(body, dict) or \
                    not isinstance(body.get("logs"), list):
                return self.send_json(422, {"detail": "bad body"})
            self.log_telemetry()
            for entry in body["logs"]:
                if not isinstance(entry, dict):
                    # A hostile or buggy client's non-dict entry (int,
                    # str, null, ...) is skipped, never raised on - entry.get
                    # below would otherwise crash the whole request.
                    continue
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
            # degrades to "no battery signal", which server/poll_cycle.py
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
            try:
                _publish_image(self.args.state_dir, digest, image)
            except OSError:
                return self.send_json(503, {"detail": "image unavailable"})
            host = self.headers.get("Host", "localhost")
            try:
                offer = _record_device_report_and_offer(
                    self.args.state_dir, self.state, self.headers,
                    self.args.image_url_scheme, host)
            except OSError:
                # A full or read-only state dir degrades to "no offer",
                # never a 500 - the panel poll above already succeeded
                # and must still be answered.
                offer = None
            return self.send_json(200, {
                "image_url": "%s://%s/img/%s.bin" % (
                    self.args.image_url_scheme, host, digest),
                "image_hash": "sha256:" + digest,
                # sleep_s composes, in order: the companion Settings page's
                # saved wake_interval_s (falling back to --sleep), the flat
                # off-state cadence while display_enabled is false, the
                # flat parked cadence while poll_cycle's battery-empty hold
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
                # The operator's scheduled release, gated by
                # server/firmware_registry.py's compute_offer(): only
                # when it differs from the device's own reported
                # version, is at or above the version floor, has not
                # already failed three times, and the device's own
                # battery-low alert is not active. Deliberately does not
                # go through quiet_hours_sleep_s()/display_off_sleep_s()
                # above - a scheduled update reaches the frame at its
                # next wake whatever the display/quiet-hours mode.
                "firmware": offer,
                "reset": False,
                # The bring-up LED toggle: the firmware half can only be
                # changed by reflashing the board, while this server-side
                # half comes from the shared device_config.json document
                # written by the companion app's Config page
                # (server/device_config.py's save_device_config()).
                "led_enabled": read_led_enabled(self.args.state_dir),
            })
        match = _IMG_PATH_RE.match(self.path)
        if match is not None:
            path = os.path.join(_img_dir(self.args.state_dir), "%s.bin" % match.group(1))
            try:
                with open(path, "rb") as fh:
                    image = fh.read()
            except OSError:
                return self.send_json(404, {"detail": "unknown image"})
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(image)))
            self.end_headers()
            self.wfile.write(image)
            return None
        match = _FW_PATH_RE.match(self.path)
        if match is not None:
            return self._serve_firmware_image(match.group(1))
        return self.send_json(404, {"detail": "unknown endpoint"})

    def _serve_firmware_image(self, sha256):
        """Stream firmware/<sha>.bin for a `sha256` that is both a
        release registered in registry.json and a regular file on disk
        within MAX_IMAGE_BYTES - anything else gets the same 404 body
        the /img/ route above already uses. No authentication, matching
        /img/'s own rule: release images are signed and carry no
        credential, so they are not secret.
        """
        registry = firmware_registry.load_registry(self.args.state_dir)
        release = next(
            (r for r in registry.get("releases", []) if r.get("sha256") == sha256), None)
        if release is None:
            return self.send_json(404, {"detail": "unknown image"})
        path = firmware_registry.firmware_image_path(self.args.state_dir, sha256)
        try:
            file_stat = os.stat(path)
        except OSError:
            return self.send_json(404, {"detail": "unknown image"})
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > firmware_registry.MAX_IMAGE_BYTES:
            return self.send_json(404, {"detail": "unknown image"})
        try:
            fh = open(path, "rb")
        except OSError:
            return self.send_json(404, {"detail": "unknown image"})
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(file_stat.st_size))
            self.end_headers()
            while True:
                chunk = fh.read(_FW_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                self.wfile.write(chunk)
        finally:
            fh.close()
        return None

    def log_message(self, fmt, *fmt_args):
        # getattr, not self.command/self.path directly: a TimeoutError
        # raised while reading the request line itself (a client that
        # connects and sends nothing) is caught by
        # BaseHTTPRequestHandler.handle_one_request() before
        # parse_request() ever runs, so this instance may have neither
        # attribute yet - a direct reference would turn that timeout log
        # into an unhandled AttributeError.
        print("%s %s" % (getattr(self, "command", None), getattr(self, "path", "")))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True,
                    help="960,000-byte panel image to serve")
    ap.add_argument("--port", type=int, default=8642)
    ap.add_argument("--bind", default="0.0.0.0",
                    help="address to listen on (default: 0.0.0.0, for the "
                         "LAN stub flow). Production passes 127.0.0.1 "
                         "because Caddy on loopback is the only intended "
                         "client.")
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
    ap.add_argument("--request-timeout", type=float, default=REQUEST_TIMEOUT_S,
                    help="seconds before a connected-but-stalled client's "
                         "socket is closed (default: %(default)s)")
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
    Handler.timeout = args.request_timeout
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print("serving %s on %s:%d — point the frame at http://<this-host>:%d"
          % (args.image, args.bind, args.port, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()
