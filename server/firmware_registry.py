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
import copy
import hashlib
import json
import os
import re
import secrets
import time
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
# Only the floor comparison orders versions; the offer rule itself is
# "differs from running", never "newer than" -- a voluntary downgrade
# is allowed. A version string is parsed only for that floor check --
# releases are otherwise identified by their registry entry.

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

    For *readers* only (byos's offer decision, the companion's Update
    page, `firmware_cli list`): a poll or a page load that shows "nothing
    published yet" for a corrupt file is far safer than one that raises.
    Every locked read-modify-write below uses `_load_registry_for_write`
    instead, which never lets this tolerance turn a corrupt on-disk file
    into a silent, unrecoverable reset to empty.
    """
    try:
        with open(registry_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _default_registry()
    if not isinstance(data, dict):
        return _default_registry()
    return _normalise_registry(data)


class RegistryCorruptError(OSError):
    """Raised by `_load_registry_for_write` (never by `load_registry`,
    which stays tolerant for readers) when firmware/registry.json exists
    but is not parseable JSON, or does not parse to an object. A
    subclass of OSError so it is caught wherever schedule_release() and
    cancel_schedule()'s existing `except (OSError, TimeoutError)` already
    treat a locked write it could not complete as "no change made" --
    exactly the right response here too, since this write never
    happened.
    """


def _load_registry_for_write(state_dir):
    """Like load_registry(), but never quietly substitutes the empty
    document for a file that exists and fails to parse. A missing file
    (a fresh state directory) is still the empty schema-1 document --
    there is nothing to lose. A file that exists and either is not valid
    JSON or does not parse to an object is moved aside intact, under a
    timestamped name next to it, and raises RegistryCorruptError instead
    of returning defaults: every caller here is about to read-modify-
    write the registry, and load_registry()'s own tolerance would
    otherwise have every release, the installed_at history, the
    schedule and the floor silently replaced by the next write this
    process makes.
    """
    path = registry_path(state_dir)
    try:
        with open(path) as fh:
            raw = fh.read()
    except FileNotFoundError:
        return _default_registry()
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict):
        return _normalise_registry(data)
    corrupt_path = "%s.corrupt-%d" % (path, int(time.time()))
    try:
        os.replace(path, corrupt_path)
    except OSError:
        corrupt_path = None
    raise RegistryCorruptError(
        "firmware/registry.json is not a valid registry document"
        + (" -- moved aside to %s" % corrupt_path if corrupt_path else " -- could not move it aside")
    )


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
    """The single rule for "the device has started": the newest
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
        registry = _load_registry_for_write(state_dir)
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
        else:
            # The path is content-addressed by sha256, but its
            # filename encoding that digest is not proof the bytes on
            # disk still match it -- a hand-copied partial file, disk
            # corruption, or a restore of a truncated archive would
            # otherwise be kept forever and re-imported "idempotently"
            # on every deploy with nothing to notice it. Re-verify and
            # repair from the bytes this call already hashed above.
            existing_digest, existing_size, _ = _hash_and_size(target)
            if existing_digest != sha256 or existing_size != size:
                atomic_io.atomic_write(target, image_bytes)
        registry["releases"].append({
            "version": version, "sha256": sha256, "size": size,
            "released_at": released_at, "published_at": now, "commit": commit,
            "notes": notes, "bench": bool(bench), "installed_at": [],
        })
        _save_registry(state_dir, registry)
        return "added"


def schedule_release(state_dir, version, running_version, now=None):
    """Make `version` the scheduled release -- recording intent only,
    never touching the device or byos. Any published release at or
    above the floor whose version differs from `running_version` can be
    scheduled, older ones (a voluntary downgrade) included -- see the
    return value table in this module's tests for every other outcome.
    """
    now = now if now is not None else _utc_now_iso()
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir)
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
    """Clear the current schedule, only while it is not yet acknowledged.
    `now` is accepted for signature symmetry with schedule_release() but
    is not stored anywhere -- cancelling leaves no trace in the registry
    beyond the schedule's absence.
    """
    del now
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir)
        schedule = registry["schedule"]
        if schedule is None:
            return "none"
        device_report = load_device_report(state_dir)
        if acknowledged(schedule, device_report):
            return "not_cancellable"
        registry["schedule"] = None
        _save_registry(state_dir, registry)
        return "cancelled"


# --- Pure offer, reconcile and view functions ---------------------------
#
# No I/O, no clock reads: every timestamp this section needs is a
# parameter. This is what keeps the offer gate, the outcome transitions
# and the view model testable without a filesystem.

def compute_offer(registry, device_entry, battery_low_active, base_url):
    """The device offer, or None. Deliberately has no quiet-hours or
    display-off parameter at all -- a scheduled update goes out at the
    frame's next wake whatever the mode, so only these four inputs ever
    decide whether an offer is served.
    """
    if battery_low_active:
        return None
    schedule = registry.get("schedule")
    if schedule is None or schedule.get("state") == "failed":
        return None
    version = schedule.get("version")
    entry = device_entry or {}
    reported_version = entry.get("fw_version")
    if version == reported_version:
        return None
    floor_version = registry.get("floor_version", FLOOR_VERSION)
    if not at_or_above_floor(version, floor_version):
        return None
    # A device whose own reported version cannot even reach the floor
    # (a pre-OTA build's raw `git describe`, for instance) can never
    # confirm, replace or roll back an OTA install -- serving it an
    # offer only wastes its next wake on a download, or, worse, an
    # offer it can never act on leaves the schedule permanently
    # "offered" and so permanently un-cancellable (acknowledged() below
    # requires a device event, and this refusal here never produces
    # one). `reported_version is None` (nothing valid ever reported
    # yet) is deliberately let through: it is the ordinary state of
    # every device before its very first poll response, not evidence
    # of an ineligible device.
    if reported_version is not None and not at_or_above_floor(reported_version, floor_version):
        return None
    # A device whose own reported version cannot even reach the floor
    # (a pre-OTA build's raw `git describe`, for instance) can never
    # confirm, replace or roll back an OTA install -- serving it an
    # offer only wastes its next wake on a download, or, worse, an
    # offer it can never act on leaves the schedule permanently
    # "offered" and so permanently un-cancellable (acknowledged() below
    # requires a device event, and this refusal here never produces
    # one). `reported_version is None` (nothing valid ever reported
    # yet) is deliberately let through: it is the ordinary state of
    # every device before its very first poll response, not evidence
    # of an ineligible device.

    reconciled_seq = registry.get("reconciled_seq", 0)
    schedule_id = schedule.get("id")
    attempts = schedule.get("attempts", 0)
    for event in entry.get("events", []):
        if event.get("kind") != "result" or event.get("schedule_id") != schedule_id:
            continue
        seq = event.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= reconciled_seq:
            continue
        if event.get("token") in COUNTED_FAILURES:
            attempts += 1
    if attempts >= MAX_ATTEMPTS:
        return None

    release = _find_release(registry, version)
    if release is None:
        return None
    sha256 = release["sha256"]
    return {
        "version": version,
        "url": base_url.rstrip("/") + "/fw/" + sha256 + ".bin",
        "sha256": "sha256:" + sha256,
        "size": release["size"],
    }


def _collect_events(device_report, min_seq):
    """(seq, event, reporting device's fw_version) for every event with
    seq > min_seq across every device, oldest first.
    """
    collected = []
    for device_entry in device_report.get("devices", {}).values():
        fw_version = device_entry.get("fw_version")
        for event in device_entry.get("events", []):
            seq = event.get("seq")
            if not isinstance(seq, int) or isinstance(seq, bool) or seq <= min_seq:
                continue
            collected.append((seq, event, fw_version))
    collected.sort(key=lambda item: item[0])
    return collected


def reconcile(registry, device_report, now):
    """Turn every unreconciled device report event into a registry
    update and a notification list. Deep-copies `registry` -- neither
    input is ever mutated. Only "result" events for the *current*
    schedule's id move attempts or clear the schedule; a "result" for
    any other schedule id still refreshes last_outcome for "installed"/
    "rollback" but never touches attempts. reconciled_seq always
    advances to the highest seq seen, offered events included,
    so a replay with unchanged input produces no new notification and
    no change.
    """
    new_registry = copy.deepcopy(registry)
    notifications = []
    reconciled_seq = new_registry.get("reconciled_seq", 0)
    highest_seq = reconciled_seq

    for seq, event, device_fw_version in _collect_events(device_report, reconciled_seq):
        if seq > highest_seq:
            highest_seq = seq
        if event.get("kind") != "result":
            continue

        token = event.get("token")
        event_version = event.get("version")
        schedule = new_registry.get("schedule")
        current_id = schedule.get("id") if schedule is not None else None

        if schedule is not None and event.get("schedule_id") == current_id:
            if token in ("trial", "deferred-battery"):
                continue
            if token == "installed":
                release = _find_release(new_registry, schedule["version"])
                if release is not None:
                    release["installed_at"].append(now)
                new_registry["schedule"] = None
                new_registry["last_outcome"] = {
                    "kind": "installed", "version": schedule["version"],
                    "back_on": None, "at": now,
                }
                notifications.append(("installed", schedule["version"], None))
            elif token in COUNTED_FAILURES:
                schedule["attempts"] = schedule.get("attempts", 0) + 1
                schedule["last_result"] = token
                if token == "rollback":
                    new_registry["last_outcome"] = {
                        "kind": "rollback", "version": schedule["version"],
                        "back_on": device_fw_version, "at": now,
                    }
                if schedule["attempts"] >= MAX_ATTEMPTS:
                    schedule["state"] = "failed"
                    schedule["failed_at"] = now
                    new_registry["last_outcome"] = {
                        "kind": "failed", "version": schedule["version"],
                        "back_on": device_fw_version, "at": now,
                    }
                    notifications.append(("failed", schedule["version"], device_fw_version))
        else:
            # A stale schedule id (the operator has already replaced or
            # cancelled it): still worth recording for the view, but
            # this is not the pending action any attempt counter or
            # notification belongs to.
            if token == "installed":
                new_registry["last_outcome"] = {
                    "kind": "installed", "version": event_version,
                    "back_on": None, "at": now,
                }
            elif token == "rollback":
                new_registry["last_outcome"] = {
                    "kind": "rollback", "version": event_version,
                    "back_on": device_fw_version, "at": now,
                }

    new_registry["reconciled_seq"] = highest_seq
    return new_registry, notifications


def apply_reconcile(state_dir, now=None):
    """The one locked I/O wrapper around reconcile(), used by the poll
    loop. Writes only when reconciled_seq actually moved.
    """
    now = now if now is not None else _utc_now_iso()
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir)
        device_report = load_device_report(state_dir)
        new_registry, notifications = reconcile(registry, device_report, now)
        if new_registry.get("reconciled_seq") != registry.get("reconciled_seq"):
            _save_registry(state_dir, new_registry)
        return notifications


def _most_recent_device_entry(device_report):
    """The device entry with the latest reported_at -- the per-device
    map stays (so multiple devices are not ruled out) but the Update
    page shows one frame's state (single-frame UI).
    """
    best = None
    best_reported_at = None
    for device_entry in device_report.get("devices", {}).values():
        reported_at = device_entry.get("reported_at")
        if reported_at is None:
            continue
        if best_reported_at is None or reported_at > best_reported_at:
            best = device_entry
            best_reported_at = reported_at
    return best


def _newest_release_published_at(registry):
    published_ats = [r.get("published_at") for r in registry.get("releases", []) if r.get("published_at")]
    return max(published_ats) if published_ats else None


def update_view(registry, device_report, now):
    """The Update page's view model. `now` is accepted for signature
    symmetry with the rest of this pure section; the derivation below
    never reads the clock.
    """
    del now
    device_entry = _most_recent_device_entry(device_report) or {}
    running_version = device_entry.get("fw_version")
    reported_at = device_entry.get("reported_at")

    schedule = registry.get("schedule")
    last_outcome = registry.get("last_outcome")

    rollback = None
    if last_outcome is not None and last_outcome.get("kind") == "rollback":
        rollback = {"version": last_outcome.get("version"), "back_on": last_outcome.get("back_on")}

    cancellable = False
    if schedule is not None and schedule.get("state") == "scheduled":
        if acknowledged(schedule, device_report):
            state = "in_progress"
            state_at = _newest_event_for_schedule(schedule.get("id"), device_report)
            state_at = state_at.get("at") if state_at else None
        else:
            state = "scheduled"
            state_at = schedule.get("scheduled_at")
            cancellable = True
    elif schedule is not None and schedule.get("state") == "failed":
        state = "failed"
        state_at = schedule.get("failed_at")
    elif (
        schedule is None and last_outcome is not None
        and last_outcome.get("kind") == "installed"
        and last_outcome.get("version") == running_version
    ):
        state = "installed"
        state_at = last_outcome.get("at")
    else:
        state = "available"
        state_at = _newest_release_published_at(registry)

    floor_version = registry.get("floor_version", FLOOR_VERSION)
    releases = []
    for release in sorted(registry.get("releases", []), key=lambda r: r.get("published_at") or "", reverse=True):
        releases.append({
            "version": release.get("version"),
            "released_at": release.get("released_at"),
            "notes": release.get("notes", []),
            "installed_at": release.get("installed_at", []),
            "bench": release.get("bench", False),
            "installable": (
                at_or_above_floor(release.get("version"), floor_version)
                and release.get("version") != running_version
            ),
        })

    return {
        "running_version": running_version,
        "reported_at": reported_at,
        "state": state,
        "state_at": state_at,
        "cancellable": cancellable,
        "rollback": rollback,
        "releases": releases,
    }
