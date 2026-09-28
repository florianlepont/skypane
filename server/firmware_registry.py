"""The server-side firmware release registry: the single definition of
what has been published, what is scheduled for the frame, and what
happened on the device's last few attempts.

Every other OTA surface reads or writes through this module instead of
touching `firmware/registry.json` directly: byos composes the device
offer from `compute_offer()`, the poll loop turns device reports into
outcomes through `apply_reconcile()`, the companion's Update page reads
`update_view()` and calls `schedule_release()`/`cancel_schedule()`, and
the deploy import calls `publish_release()`. Keeping every rule here as
a pure function (or a single locked read-modify-write) is what stops
the four surfaces from drifting apart on what "scheduled" or "at the
floor" means.

Storage layout under `state_dir`:
  firmware/registry.json       -- this module's own document, written
                                   only here, under firmware/registry.lock.
  firmware/<sha256>.bin        -- release images, content-addressed.
  firmware/device_report.json  -- byos-owned; this module only reads it.

Every write goes through `server.atomic_io.atomic_write` under
`server.atomic_io.exclusive_lock` -- never a hand-rolled temp-file-then-
rename, and never a second lock implementation. No function in this
module ever deletes a release entry or an image file: every release is
kept (a voluntary downgrade needs the old image to still be there), so
there is no pruning to write.
"""
import contextlib
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone

from server import atomic_io

# --- Storage layout --------------------------------------------------------

FIRMWARE_DIRNAME = "firmware"
REGISTRY_FILE = "registry.json"
DEVICE_REPORT_FILE = "device_report.json"
LOCK_FILE = "registry.lock"

# Bounded wait for a second writer (companion HTTP thread, the poll loop,
# or the deploy import) already holding the lock -- the same convention
# as server/device_config.py's DEVICE_CONFIG_LOCK_TIMEOUT_S.
REGISTRY_LOCK_TIMEOUT_S = 10.0

FLOOR_VERSION = "fw-v1.0.0"
MAX_ATTEMPTS = 3
# One OTA slot (firmware/partitions.csv): ota_0/ota_1 are each 0x250000.
MAX_IMAGE_BYTES = 0x250000

# A CI-tagged release, e.g. "fw-v1.3.0". No leading zeros on a non-zero
# component (mirrors semver), each component at most 4 digits.
RELEASE_TAG_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\Z"
)
# RELEASE_TAG_RE's body plus an optional bench-build suffix
# ("-<slug>"), e.g. "fw-v1.3.0-bench1". Total length is capped
# separately at 31 (the ESP-IDF app descriptor's version field) by
# every caller that matches against this pattern -- the pattern itself
# cannot express a length bound on the whole string.
VERSION_RE = re.compile(
    r"\Afw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})"
    r"(?:-[a-z0-9][a-z0-9.-]{0,23})?\Z"
)
VERSION_MAX_LEN = 31
SHA256_HEX_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_COMMIT_SHA_RE = re.compile(r"\A[0-9a-f]{40}\Z")

RESULT_TOKENS = (
    "trial", "installed", "rollback", "deferred-battery",
    "fail-download", "fail-size", "fail-hash", "fail-image",
    "fail-floor", "fail-interrupted",
)
# The tokens that count toward MAX_ATTEMPTS: a rollback and every
# fail-* outcome. "trial" and "deferred-battery" never count.
COUNTED_FAILURES = frozenset(
    token for token in RESULT_TOKENS
    if token == "rollback" or token.startswith("fail-")
)

# Events are capped at the newest 50 per device -- matches byos's own
# documented cap (interfaces block) and is re-applied defensively here
# so a hostile/corrupt device_report.json cannot grow reconcile()'s
# per-call work without bound.
_MAX_EVENTS_PER_DEVICE = 50


def firmware_dir(state_dir):
    return os.path.join(state_dir, FIRMWARE_DIRNAME)


def registry_path(state_dir):
    return os.path.join(firmware_dir(state_dir), REGISTRY_FILE)


def device_report_path(state_dir):
    return os.path.join(firmware_dir(state_dir), DEVICE_REPORT_FILE)


def lock_path(state_dir):
    return os.path.join(firmware_dir(state_dir), LOCK_FILE)


def _ensure_firmware_dir(state_dir):
    """Create firmware/ with mode 0o750 if it is missing. Mode is
    re-applied with an explicit chmod after os.makedirs(), since the
    process umask would otherwise silently narrow the requested mode
    for a freshly created directory.
    """
    path = firmware_dir(state_dir)
    if not os.path.isdir(path):
        os.makedirs(path, mode=0o750, exist_ok=True)
        os.chmod(path, 0o750)
    return path


@contextlib.contextmanager
def registry_lock(state_dir):
    """The one cross-process, cross-thread lock every registry
    read-modify-write in this module runs under, delegating to
    `atomic_io.exclusive_lock`. Never re-implemented here.
    """
    _ensure_firmware_dir(state_dir)
    with atomic_io.exclusive_lock(lock_path(state_dir), REGISTRY_LOCK_TIMEOUT_S):
        yield


def firmware_image_path(state_dir, sha256):
    """The absolute path for a release image, or None for anything that
    is not a bare 64-lowercase-hex SHA-256 -- a path is never built from
    an unvalidated string.
    """
    if not isinstance(sha256, str) or not SHA256_HEX_RE.match(sha256):
        return None
    return os.path.join(firmware_dir(state_dir), sha256 + ".bin")


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


# --- Version helpers ---------------------------------------------------
#
# Only the floor comparison orders versions (D-11); the offer rule
# itself is "differs from running", never "newer than" (D-06). A
# version string is parsed only for that floor check -- releases are
# otherwise identified by their registry entry.

def parse_version(text):
    """(major, minor, patch) for a VERSION_RE match at most
    VERSION_MAX_LEN characters long (the suffix is ignored for
    ordering), else None. Never raises.
    """
    if not isinstance(text, str) or len(text) > VERSION_MAX_LEN:
        return None
    match = VERSION_RE.match(text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def at_or_above_floor(version, floor):
    """False for anything unparsable on either side -- never raises."""
    parsed_version = parse_version(version)
    parsed_floor = parse_version(floor)
    if parsed_version is None or parsed_floor is None:
        return False
    return parsed_version >= parsed_floor


# --- Tolerant document loaders -------------------------------------------
#
# Every loader below degrades a missing, empty, non-JSON, or wrong-shape
# file to the documented empty/default value, field by field, and never
# raises -- the same contract as server/device_config.py's
# load_device_config().

def _default_registry():
    return {
        "schema": 1,
        "floor_version": FLOOR_VERSION,
        "releases": [],
        "schedule": None,
        "last_outcome": None,
        "reconciled_seq": 0,
    }


def _normalise_release(value):
    if not isinstance(value, dict):
        return None
    version = value.get("version")
    sha256 = value.get("sha256")
    size = value.get("size")
    released_at = value.get("released_at")
    published_at = value.get("published_at")
    commit = value.get("commit")
    if not isinstance(version, str) or len(version) > VERSION_MAX_LEN or not VERSION_RE.match(version):
        return None
    if not isinstance(sha256, str) or not SHA256_HEX_RE.match(sha256):
        return None
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        return None
    if not isinstance(released_at, str):
        return None
    if not isinstance(published_at, str):
        return None
    if not isinstance(commit, str):
        return None
    raw_notes = value.get("notes")
    notes = [str(n)[:200] for n in raw_notes if isinstance(n, str)][:60] if isinstance(raw_notes, list) else []
    bench = value.get("bench")
    bench = bench if isinstance(bench, bool) else False
    raw_installed_at = value.get("installed_at")
    installed_at = [t for t in raw_installed_at if isinstance(t, str)] if isinstance(raw_installed_at, list) else []
    return {
        "version": version, "sha256": sha256, "size": size,
        "released_at": released_at, "published_at": published_at,
        "commit": commit, "notes": notes, "bench": bench,
        "installed_at": installed_at,
    }


def _normalise_schedule(value):
    if not isinstance(value, dict):
        return None
    schedule_id = value.get("id")
    version = value.get("version")
    sha256 = value.get("sha256")
    scheduled_at = value.get("scheduled_at")
    state = value.get("state")
    if not isinstance(schedule_id, str) or not schedule_id:
        return None
    if not isinstance(version, str):
        return None
    if not isinstance(sha256, str) or not SHA256_HEX_RE.match(sha256):
        return None
    if not isinstance(scheduled_at, str):
        return None
    if state not in ("scheduled", "failed"):
        return None
    attempts = value.get("attempts")
    attempts = attempts if isinstance(attempts, int) and not isinstance(attempts, bool) and attempts >= 0 else 0
    failed_at = value.get("failed_at")
    failed_at = failed_at if isinstance(failed_at, str) else None
    last_result = value.get("last_result")
    last_result = last_result if last_result in RESULT_TOKENS else None
    return {
        "id": schedule_id, "version": version, "sha256": sha256,
        "scheduled_at": scheduled_at, "state": state, "attempts": attempts,
        "failed_at": failed_at, "last_result": last_result,
    }


def _normalise_last_outcome(value):
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    version = value.get("version")
    at = value.get("at")
    if kind not in ("installed", "rollback", "failed"):
        return None
    if not isinstance(version, str):
        return None
    if not isinstance(at, str):
        return None
    back_on = value.get("back_on")
    back_on = back_on if isinstance(back_on, str) else None
    return {"kind": kind, "version": version, "back_on": back_on, "at": at}


def _normalise_registry(data):
    floor_version = data.get("floor_version")
    if not isinstance(floor_version, str) or len(floor_version) > VERSION_MAX_LEN or not VERSION_RE.match(floor_version):
        floor_version = FLOOR_VERSION
    raw_releases = data.get("releases")
    releases = []
    if isinstance(raw_releases, list):
        for raw_release in raw_releases:
            normalised = _normalise_release(raw_release)
            if normalised is not None:
                releases.append(normalised)
    reconciled_seq = data.get("reconciled_seq")
    reconciled_seq = (
        reconciled_seq
        if isinstance(reconciled_seq, int) and not isinstance(reconciled_seq, bool) and reconciled_seq >= 0
        else 0
    )
    return {
        "schema": 1,
        "floor_version": floor_version,
        "releases": releases,
        "schedule": _normalise_schedule(data.get("schedule")),
        "last_outcome": _normalise_last_outcome(data.get("last_outcome")),
        "reconciled_seq": reconciled_seq,
    }


def load_registry(state_dir):
    """The registry document, tolerant of a missing/empty/non-JSON/
    wrong-shape file -- always the empty schema-1 document (floor_version
    == FLOOR_VERSION) in that case. Never raises.
    """
    try:
        with open(registry_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _default_registry()
    if not isinstance(data, dict):
        return _default_registry()
    return _normalise_registry(data)


def _save_registry(state_dir, doc):
    _ensure_firmware_dir(state_dir)
    atomic_io.atomic_write(registry_path(state_dir), json.dumps(doc, indent=1, sort_keys=True))


def _default_device_report():
    return {"schema": 1, "next_seq": 0, "devices": {}}


def _normalise_event(value):
    if not isinstance(value, dict):
        return None
    seq = value.get("seq")
    kind = value.get("kind")
    at = value.get("at")
    if not isinstance(seq, int) or isinstance(seq, bool):
        return None
    if kind not in ("offered", "result"):
        return None
    if not isinstance(at, str):
        return None
    schedule_id = value.get("schedule_id")
    schedule_id = schedule_id if isinstance(schedule_id, str) else None
    token = value.get("token")
    token = token if token in RESULT_TOKENS else None
    version = value.get("version")
    version = version if isinstance(version, str) else None
    return {
        "seq": seq, "at": at, "kind": kind,
        "schedule_id": schedule_id, "token": token, "version": version,
    }


def _normalise_device_entry(value):
    if not isinstance(value, dict):
        return None
    fw_version = value.get("fw_version")
    fw_version = fw_version if isinstance(fw_version, str) else None
    reported_at = value.get("reported_at")
    reported_at = reported_at if isinstance(reported_at, str) else None
    raw_events = value.get("events")
    events = []
    if isinstance(raw_events, list):
        for raw_event in raw_events:
            normalised = _normalise_event(raw_event)
            if normalised is not None:
                events.append(normalised)
    events = events[-_MAX_EVENTS_PER_DEVICE:]
    return {"fw_version": fw_version, "reported_at": reported_at, "events": events}


def _normalise_device_report(data):
    next_seq = data.get("next_seq")
    next_seq = next_seq if isinstance(next_seq, int) and not isinstance(next_seq, bool) and next_seq >= 0 else 0
    # JSON object keys are always strings (json.load never yields a
    # non-str dict key), so device_id itself needs no further gate here
    # beyond raw_devices already being a dict.
    raw_devices = data.get("devices")
    devices = {}
    if isinstance(raw_devices, dict):
        for device_id, raw_entry in raw_devices.items():
            entry = _normalise_device_entry(raw_entry)
            if entry is not None:
                devices[device_id] = entry
    return {"schema": 1, "next_seq": next_seq, "devices": devices}


def load_device_report(state_dir):
    """byos's own report document, read-only from here. Same tolerant
    contract as load_registry(): a missing/malformed file degrades to
    the empty schema-1 document, never raises.
    """
    try:
        with open(device_report_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _default_device_report()
    if not isinstance(data, dict):
        return _default_device_report()
    return _normalise_device_report(data)


def _find_release(registry, version):
    for release in registry.get("releases", []):
        if release.get("version") == version:
            return release
    return None


def _newest_event_for_schedule(schedule_id, device_report):
    newest = None
    for device_entry in device_report.get("devices", {}).values():
        for event in device_entry.get("events", []):
            if event.get("schedule_id") != schedule_id:
                continue
            if newest is None or event.get("seq", -1) > newest.get("seq", -1):
                newest = event
    return newest


def acknowledged(schedule, device_report):
    """The single rule for "the device has started" (D-05): the newest
    event recorded for this schedule id, across every device. An
    "offered" event, or any "result" whose token is not
    "deferred-battery", means the device has started -- no event at
    all, or a newest "deferred-battery" refusal, means it has not.
    """
    if schedule is None:
        return False
    newest = _newest_event_for_schedule(schedule.get("id"), device_report)
    if newest is None:
        return False
    if newest.get("kind") == "offered":
        return True
    if newest.get("kind") == "result":
        return newest.get("token") != "deferred-battery"
    return False


def _hash_and_size(path):
    """SHA-256 hex digest, byte size, and the full byte content of the
    file at `path`, read in 64 KiB chunks (never the whole file in one
    read() call) so publish_release's own validation never depends on
    how large a caller's image happens to be.
    """
    digest = hashlib.sha256()
    size = 0
    chunks = []
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            chunks.append(chunk)
    return digest.hexdigest(), size, b"".join(chunks)


def publish_release(state_dir, manifest, image_path, bench=False, now=None):
    """Register one release: copy its image into firmware/<sha>.bin
    (only if not already present) and append its registry entry.
    Idempotent on an identical manifest ("exists", no change); raises
    ValueError naming the offending field for anything that does not
    match what the interfaces block documents. Never deletes anything.
    """
    if not isinstance(manifest, dict):
        raise ValueError("manifest: must be a dict, got %r" % (manifest,))

    version = manifest.get("version")
    version_pattern = VERSION_RE if bench else RELEASE_TAG_RE
    if not isinstance(version, str) or len(version) > VERSION_MAX_LEN or not version_pattern.match(version):
        raise ValueError("version: invalid release version %r" % (version,))

    sha256 = manifest.get("sha256")
    if not isinstance(sha256, str) or not SHA256_HEX_RE.match(sha256):
        raise ValueError("sha256: manifest sha256 must be 64 lowercase hex characters, got %r" % (sha256,))

    size = manifest.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_IMAGE_BYTES:
        raise ValueError(
            "size: manifest size must be a positive int at most %d bytes, got %r" % (MAX_IMAGE_BYTES, size)
        )

    released_at = manifest.get("released_at")
    if not isinstance(released_at, str) or not released_at:
        raise ValueError("released_at: must be a non-empty string, got %r" % (released_at,))

    commit = manifest.get("commit")
    if not isinstance(commit, str) or not _COMMIT_SHA_RE.match(commit):
        raise ValueError("commit: must be 40 lowercase hex characters, got %r" % (commit,))

    raw_notes = manifest.get("notes")
    if raw_notes is None:
        raw_notes = []
    if not isinstance(raw_notes, list) or not all(isinstance(n, str) for n in raw_notes):
        raise ValueError("notes: must be a list of strings, got %r" % (raw_notes,))
    notes = [n[:200] for n in raw_notes][:60]

    digest, actual_size, image_bytes = _hash_and_size(image_path)
    if digest != sha256:
        raise ValueError(
            "sha256: image at %r hashes to %s, manifest declares %s" % (image_path, digest, sha256)
        )
    if actual_size != size:
        raise ValueError(
            "size: image at %r is %d bytes, manifest declares %d" % (image_path, actual_size, size)
        )

    now = now if now is not None else _utc_now_iso()

    with registry_lock(state_dir):
        registry = load_registry(state_dir)
        existing = _find_release(registry, version)
        if existing is not None:
            if existing["sha256"] == sha256:
                return "exists"
            raise ValueError(
                "version: %r is already registered with a different sha256 (%s != %s)"
                % (version, existing["sha256"], sha256)
            )
        target = firmware_image_path(state_dir, sha256)
        if not os.path.exists(target):
            atomic_io.atomic_write(target, image_bytes)
        registry["releases"].append({
            "version": version, "sha256": sha256, "size": size,
            "released_at": released_at, "published_at": now, "commit": commit,
            "notes": notes, "bench": bool(bench), "installed_at": [],
        })
        _save_registry(state_dir, registry)
        return "added"


def schedule_release(state_dir, version, running_version, now=None):
    """Make `version` the scheduled release (D-01: recording intent
    only, never touching the device or byos). Any published release at
    or above the floor whose version differs from `running_version` can
    be scheduled, older ones included (D-06, D-11) -- see the return
    value table in this module's tests for every other outcome.
    """
    now = now if now is not None else _utc_now_iso()
    with registry_lock(state_dir):
        registry = load_registry(state_dir)
        release = _find_release(registry, version)
        if release is None:
            return "unknown"
        if not at_or_above_floor(version, registry["floor_version"]):
            return "below_floor"
        if version == running_version:
            return "same_as_running"

        schedule = registry["schedule"]
        if schedule is not None and schedule["state"] == "scheduled":
            device_report = load_device_report(state_dir)
            if acknowledged(schedule, device_report):
                return "busy"

        registry["schedule"] = {
            "id": secrets.token_hex(8),
            "version": version,
            "sha256": release["sha256"],
            "scheduled_at": now,
            "state": "scheduled",
            "attempts": 0,
            "failed_at": None,
            "last_result": None,
        }
        _save_registry(state_dir, registry)
        return "scheduled"


def cancel_schedule(state_dir, now=None):
    """Clear the current schedule, only while it is not yet acknowledged
    (D-05). `now` is accepted for signature symmetry with
    schedule_release() but is not stored anywhere -- cancelling leaves
    no trace in the registry beyond the schedule's absence.
    """
    del now
    with registry_lock(state_dir):
        registry = load_registry(state_dir)
        schedule = registry["schedule"]
        if schedule is None:
            return "none"
        device_report = load_device_report(state_dir)
        if acknowledged(schedule, device_report):
            return "not_cancellable"
        registry["schedule"] = None
        _save_registry(state_dir, registry)
        return "cancelled"

