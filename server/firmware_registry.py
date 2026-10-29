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
  firmware/registry.json       -- this module's own document for the legacy
                                   hardware type, written only here, under
                                   firmware/registry.lock.
  firmware/registry.<key>.json -- the same document for any other hardware
                                   type; schedule, floor and reconcile
                                   counter are independent per document.
  firmware/registry.json.pre-fleet -- the original registry.json bytes,
                                   copied once before its first rewrite.
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

from server import atomic_io, firmware_image, hardware

# --- Storage layout --------------------------------------------------------

FIRMWARE_DIRNAME = "firmware"
REGISTRY_FILE = "registry.json"
DEVICE_REPORT_FILE = "device_report.json"
LOCK_FILE = "registry.lock"
PRE_FLEET_SUFFIX = ".pre-fleet"

# Stamped by byos on a device entry whose hardware type cannot be
# resolved. It is not a hardware key, so no registry document ever has
# this type and such an entry is excluded from every reconcile and view.
UNRESOLVED_TYPE = "unresolved"

_TYPE_KEY_RE = re.compile(r"\A[a-z0-9-]{1,64}\Z")

# Bounded wait for a second writer (companion HTTP thread, the poll loop,
# or the deploy import) already holding the lock -- the same convention
# as server/device_config.py's DEVICE_CONFIG_LOCK_TIMEOUT_S.
REGISTRY_LOCK_TIMEOUT_S = 10.0

FLOOR_VERSION = "fw-v1.0.0"
# The newest release tag that may omit hardware_type from its manifest;
# anything later must declare the type it is built for.
GRANDFATHERED_MAX_TAG = "fw-v1.0.2"
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


def _checked_type(hardware_type):
    """The hardware type key, validated before any path is built from
    it: shape first, then membership in the types usable here.
    """
    if not isinstance(hardware_type, str) or not _TYPE_KEY_RE.match(hardware_type):
        raise ValueError("hardware_type: invalid key %r" % (hardware_type,))
    if hardware_type not in hardware.available_types():
        raise ValueError("hardware_type: unknown hardware type %r" % (hardware_type,))
    return hardware_type


def _type_document_name(hardware_type):
    if hardware_type == hardware.LEGACY_KEY:
        return REGISTRY_FILE
    return "registry.%s.json" % hardware_type


def registry_path(state_dir, hardware_type=hardware.LEGACY_KEY):
    name = _type_document_name(_checked_type(hardware_type))
    return os.path.join(firmware_dir(state_dir), name)


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


def build_number(version):
    """A monotonically comparable integer for a release tag; bench
    versions have no build number. Components are at most 4 digits, so
    the packing is injective and order preserving.
    """
    if not isinstance(version, str) or not RELEASE_TAG_RE.match(version):
        raise ValueError("version: not a release tag %r" % (version,))
    return _pack_build(parse_version(version))


def _pack_build(parsed):
    major, minor, patch = parsed
    return major * 10**8 + minor * 10**4 + patch


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

def _default_registry(hardware_type=hardware.LEGACY_KEY):
    doc = {
        "schema": 1,
        "floor_version": FLOOR_VERSION,
        "releases": [],
        "schedule": None,
        "last_outcome": None,
        "reconciled_seq": 0,
    }
    if hardware_type != hardware.LEGACY_KEY:
        doc["hardware_type"] = hardware_type
    return doc


def _document_type(registry):
    """The hardware type a registry document belongs to; a document
    without the field is the legacy one.
    """
    value = registry.get("hardware_type") if isinstance(registry, dict) else None
    return value if isinstance(value, str) else hardware.LEGACY_KEY


def _normalise_release(value, hardware_type=hardware.LEGACY_KEY):
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
        "hardware_type": hardware_type,
        "build": _pack_build(parse_version(version)),
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


def _normalise_registry(data, hardware_type=hardware.LEGACY_KEY):
    floor_version = data.get("floor_version")
    if not isinstance(floor_version, str) or len(floor_version) > VERSION_MAX_LEN or not VERSION_RE.match(floor_version):
        floor_version = FLOOR_VERSION
    raw_releases = data.get("releases")
    releases = []
    if isinstance(raw_releases, list):
        for raw_release in raw_releases:
            normalised = _normalise_release(raw_release, hardware_type)
            if normalised is not None:
                releases.append(normalised)
    reconciled_seq = data.get("reconciled_seq")
    reconciled_seq = (
        reconciled_seq
        if isinstance(reconciled_seq, int) and not isinstance(reconciled_seq, bool) and reconciled_seq >= 0
        else 0
    )
    doc = {
        "schema": 1,
        "floor_version": floor_version,
        "releases": releases,
        "schedule": _normalise_schedule(data.get("schedule")),
        "last_outcome": _normalise_last_outcome(data.get("last_outcome")),
        "reconciled_seq": reconciled_seq,
    }
    if hardware_type != hardware.LEGACY_KEY:
        doc["hardware_type"] = hardware_type
    return doc


def load_registry(state_dir, hardware_type=hardware.LEGACY_KEY):
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
    path = registry_path(state_dir, hardware_type)
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return _default_registry(hardware_type)
    if not isinstance(data, dict):
        return _default_registry(hardware_type)
    return _normalise_registry(data, hardware_type)


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


def _load_registry_for_write(state_dir, hardware_type=hardware.LEGACY_KEY):
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
    path = registry_path(state_dir, hardware_type)
    try:
        with open(path) as fh:
            raw = fh.read()
    except FileNotFoundError:
        return _default_registry(hardware_type)
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict):
        return _normalise_registry(data, hardware_type)
    corrupt_path = "%s.corrupt-%d" % (path, int(time.time()))
    try:
        os.replace(path, corrupt_path)
    except OSError:
        corrupt_path = None
    raise RegistryCorruptError(
        "firmware/%s is not a valid registry document" % os.path.basename(path)
        + (" -- moved aside to %s" % corrupt_path if corrupt_path else " -- could not move it aside")
    )


def _write_pre_fleet_copy(path):
    """Copy the exact bytes of an existing registry.json to
    registry.json.pre-fleet, once: an existing copy is never replaced.
    """
    copy_path = path + PRE_FLEET_SUFFIX
    if os.path.exists(copy_path):
        return
    try:
        with open(path, "rb") as fh:
            original = fh.read()
    except FileNotFoundError:
        return
    atomic_io.atomic_write(copy_path, original)


def _serialisable(doc):
    """The legacy document keeps its original shape on disk: release
    entries carry no hardware_type or build there (both are filled in at
    read time). Other types store the full entries.
    """
    if _document_type(doc) != hardware.LEGACY_KEY:
        return doc
    out = dict(doc)
    out["releases"] = [
        {k: v for k, v in r.items() if k not in ("hardware_type", "build")}
        for r in doc.get("releases", [])
    ]
    return out


def _save_registry(state_dir, doc, hardware_type=hardware.LEGACY_KEY):
    _ensure_firmware_dir(state_dir)
    path = registry_path(state_dir, hardware_type)
    if hardware_type == hardware.LEGACY_KEY:
        _write_pre_fleet_copy(path)
    atomic_io.atomic_write(path, json.dumps(_serialisable(doc), indent=1, sort_keys=True))


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
    entry = {"fw_version": fw_version, "reported_at": reported_at, "events": events}
    stored_type = value.get("hardware_type")
    if isinstance(stored_type, str) and (
        stored_type == UNRESOLVED_TYPE or hardware.is_known(stored_type)
    ):
        entry["hardware_type"] = stored_type
    return entry


def _entry_type(entry):
    """The hardware type stamped on a device entry: the stored value
    (the UNRESOLVED_TYPE sentinel included, unchanged), or the legacy
    type for an entry written before the field existed.
    """
    stored = entry.get("hardware_type") if isinstance(entry, dict) else None
    return stored if isinstance(stored, str) else hardware.LEGACY_KEY


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


def _signing_policy(hardware_type):
    """(require_signature, expected_modulus) applied to an image at
    publish time. Every type currently requires a signed image and
    compares no modulus; the per-type profile supplies the value once a
    signing option is recorded for it.
    """
    return True, None


def _validate_manifest(manifest, hardware_type, bench):
    """Check the manifest fields alone (no image, no registry state)
    and return (version, sha256, size, released_at, commit, notes).
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

    max_bytes = hardware.get_profile(hardware_type).firmware.max_app_bytes
    size = manifest.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > max_bytes:
        raise ValueError(
            "size: manifest size must be a positive int at most %d bytes, got %r" % (max_bytes, size)
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
    _check_declared_type(manifest, version, hardware_type)
    return version, sha256, size, released_at, commit, [n[:200] for n in raw_notes][:60]


def _check_declared_type(manifest, version, hardware_type):
    """A manifest names its hardware type; only releases at or below the
    pinned grandfather tag, for the legacy type, may omit it.
    """
    declared = manifest.get("hardware_type")
    if declared is None:
        if hardware_type != hardware.LEGACY_KEY:
            raise ValueError(
                "hardware_type: manifest must declare %r for this type" % (hardware_type,)
            )
        if parse_version(version) > parse_version(GRANDFATHERED_MAX_TAG):
            raise ValueError(
                "hardware_type: manifest for %s must declare hardware_type "
                "(only releases up to %s may omit it)" % (version, GRANDFATHERED_MAX_TAG)
            )
        return
    if declared != hardware_type:
        raise ValueError(
            "hardware_type: manifest declares %r but the release is published for %r"
            % (declared, hardware_type)
        )


def _validate_image(manifest, version, image_bytes, hardware_type, bench):
    """Check the image against the hardware type's firmware target and
    the signing policy; the manifest build, when given, must equal the
    build derived from the signed descriptor version. Returns the
    parsed image.
    """
    target = hardware.get_profile(hardware_type).firmware
    require_signature, expected_modulus = _signing_policy(hardware_type)
    image = firmware_image.validate_for_target(
        image_bytes, target, manifest_version=version, bench=bench,
        require_signature=require_signature, expected_modulus=expected_modulus,
    )
    declared_build = manifest.get("build")
    if declared_build is not None and declared_build != _pack_build(parse_version(image.version)):
        raise ValueError(
            "build: manifest build %r differs from the build of descriptor version %s"
            % (declared_build, image.version)
        )
    return image


def _apply_build_gate(registry, version, bench):
    """Refuse a new non-bench release whose build is not strictly above
    the highest non-bench build already in this type's document. Only
    publishing is gated: scheduling an older published release stays
    possible, and the floor still bounds what may be offered.
    """
    if bench:
        return
    new_build = build_number(version)
    highest = max(
        (r["build"] for r in registry["releases"] if not r.get("bench")), default=None
    )
    if highest is not None and new_build <= highest:
        raise ValueError(
            "build: %s (build %d) is not above the newest published build %d"
            % (version, new_build, highest)
        )


def _store_image(state_dir, sha256, size, image_bytes):
    """Write firmware/<sha256>.bin, repairing a file whose bytes no
    longer match the digest it is named after.
    """
    target = firmware_image_path(state_dir, sha256)
    if not os.path.exists(target):
        atomic_io.atomic_write(target, image_bytes)
        return
    # The filename encodes the digest but is not proof the bytes still
    # match it (hand-copied partial file, disk corruption, truncated
    # restore); re-verify and repair from the bytes already hashed.
    existing_digest, existing_size, _ = _hash_and_size(target)
    if existing_digest != sha256 or existing_size != size:
        atomic_io.atomic_write(target, image_bytes)


def publish_release(state_dir, manifest, image_path, bench=False, now=None,
                    hardware_type=hardware.LEGACY_KEY):
    """Register one release for `hardware_type`: validate the manifest,
    then (only when it is new) the image against that type's firmware
    target and the per-type build gate, copy the image into
    firmware/<sha>.bin and append the registry entry. Idempotent on an
    identical (type, version, sha256): "exists", and the image is not
    validated again. Raises ValueError naming the offending field.
    Never deletes anything.
    """
    _checked_type(hardware_type)
    version, sha256, size, released_at, commit, notes = _validate_manifest(
        manifest, hardware_type, bench
    )
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
        registry = _load_registry_for_write(state_dir, hardware_type)
        existing = _find_release(registry, version)
        if existing is not None:
            if existing["sha256"] == sha256:
                return "exists"
            raise ValueError(
                "version: %r is already registered with a different sha256 (%s != %s)"
                % (version, existing["sha256"], sha256)
            )
        _validate_image(manifest, version, image_bytes, hardware_type, bench)
        _apply_build_gate(registry, version, bench)
        _store_image(state_dir, sha256, size, image_bytes)
        registry["releases"].append({
            "version": version, "sha256": sha256, "size": size,
            "released_at": released_at, "published_at": now, "commit": commit,
            "notes": notes, "bench": bool(bench), "installed_at": [],
            "hardware_type": hardware_type,
            "build": _pack_build(parse_version(version)),
        })
        _save_registry(state_dir, registry, hardware_type)
        return "added"


def schedule_release(state_dir, version, running_version, now=None,
                     hardware_type=hardware.LEGACY_KEY):
    """Make `version` the scheduled release -- recording intent only,
    never touching the device or byos. Any published release at or
    above the floor whose version differs from `running_version` can be
    scheduled, older ones (a voluntary downgrade) included -- see the
    return value table in this module's tests for every other outcome.
    """
    now = now if now is not None else _utc_now_iso()
    _checked_type(hardware_type)
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir, hardware_type)
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
        _save_registry(state_dir, registry, hardware_type)
        return "scheduled"


def cancel_schedule(state_dir, now=None, hardware_type=hardware.LEGACY_KEY):
    """Clear the current schedule, only while it is not yet acknowledged.
    `now` is accepted for signature symmetry with schedule_release() but
    is not stored anywhere -- cancelling leaves no trace in the registry
    beyond the schedule's absence.
    """
    del now
    _checked_type(hardware_type)
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir, hardware_type)
        schedule = registry["schedule"]
        if schedule is None:
            return "none"
        device_report = load_device_report(state_dir)
        if acknowledged(schedule, device_report):
            return "not_cancellable"
        registry["schedule"] = None
        _save_registry(state_dir, registry, hardware_type)
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


def _collect_events(device_report, min_seq, hardware_type=hardware.LEGACY_KEY):
    """(seq, event, reporting device's fw_version) for every event with
    seq > min_seq across every device of `hardware_type`, oldest first.
    """
    collected = []
    for device_entry in device_report.get("devices", {}).values():
        if _entry_type(device_entry) != hardware_type:
            continue
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
    update and a list of install/failure outcomes. Deep-copies `registry` -- neither
    input is ever mutated. Only "result" events for the *current*
    schedule's id move attempts or clear the schedule; a "result" for
    any other schedule id still refreshes last_outcome for "installed"/
    "rollback" but never touches attempts. reconciled_seq always
    advances to the highest seq seen, offered events included,
    so a replay with unchanged input produces no new outcome and
    no change.
    """
    new_registry = copy.deepcopy(registry)
    outcomes = []
    reconciled_seq = new_registry.get("reconciled_seq", 0)
    highest_seq = reconciled_seq
    doc_type = _document_type(new_registry)

    for seq, event, device_fw_version in _collect_events(device_report, reconciled_seq, doc_type):
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
                outcomes.append(("installed", schedule["version"], None))
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
                    outcomes.append(("failed", schedule["version"], device_fw_version))
        else:
            # A stale schedule id (the operator has already replaced or
            # cancelled it): still worth recording for the view, but
            # this is not the pending action any attempt counter or
            # outcome belongs to.
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
    return new_registry, outcomes


def apply_reconcile(state_dir, now=None, hardware_type=hardware.LEGACY_KEY):
    """The one locked I/O wrapper around reconcile(), used by the poll
    loop. Writes only when reconciled_seq actually moved.
    """
    now = now if now is not None else _utc_now_iso()
    _checked_type(hardware_type)
    with registry_lock(state_dir):
        registry = _load_registry_for_write(state_dir, hardware_type)
        device_report = load_device_report(state_dir)
        new_registry, outcomes = reconcile(registry, device_report, now)
        if new_registry.get("reconciled_seq") != registry.get("reconciled_seq"):
            _save_registry(state_dir, new_registry, hardware_type)
        return outcomes


def apply_reconcile_all(state_dir, now=None):
    """Reconcile the legacy document and every other available type that
    has a document on disk. Returns all outcomes, legacy first. A type
    whose reconciled_seq did not move is not rewritten.
    """
    now = now if now is not None else _utc_now_iso()
    outcomes = list(apply_reconcile(state_dir, now))
    for hardware_type in hardware.available_types():
        if hardware_type == hardware.LEGACY_KEY:
            continue
        if not os.path.exists(registry_path(state_dir, hardware_type)):
            continue
        outcomes.extend(apply_reconcile(state_dir, now, hardware_type))
    return outcomes


def relevant_types(state_dir, device_report):
    """Available hardware types that have at least one release or one
    device entry, in registry order. A type unavailable in this
    environment is never relevant.
    """
    device_types = {_entry_type(e) for e in device_report.get("devices", {}).values()}
    relevant = []
    for hardware_type in hardware.available_types():
        has_releases = bool(load_registry(state_dir, hardware_type)["releases"])
        if has_releases or hardware_type in device_types:
            relevant.append(hardware_type)
    return relevant


def _most_recent_device_entry(device_report, hardware_type=hardware.LEGACY_KEY):
    """The device entry of `hardware_type` with the latest reported_at --
    the per-device map stays (so multiple devices are not ruled out) but
    the Update page shows one frame's state (single-frame UI).
    """
    best = None
    best_reported_at = None
    for device_entry in device_report.get("devices", {}).values():
        if _entry_type(device_entry) != hardware_type:
            continue
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


def _direction_from_running(version, running_version):
    """"newer" or "older" when `version` orders above or below the running
    release, None when they tie on (major, minor, patch) or either side
    does not parse -- so the Update page words a lower version as a
    rollback and never guesses when it cannot compare.
    """
    candidate = parse_version(version)
    running = parse_version(running_version)
    if candidate is None or running is None or candidate == running:
        return None
    return "newer" if candidate > running else "older"


def _release_views(registry, running_version):
    """The Update page's per-release rows, newest published first.

    `running` marks the one release whose version is the frame's
    reported X-Fw-Version. `installed_at` stays the raw list of every
    over-the-air install this release has had (only an "installed"
    result appends to it), so it is history, not proof of what runs now.

    `installed_now_at` is the time to print beside the running release's
    check mark, and it is only honest when that release's newest OTA
    install is also the newest OTA install of any release: a frame
    reached again by USB flash, or rolled forward by a later OTA install
    of another release that was then flashed over, would otherwise show
    an install time that was overtaken. ISO timestamps compare
    lexicographically, the same way `_newest_release_published_at()`
    does. A failed or rolled-back attempt never appends to
    `installed_at`, so it cannot move this. It is None on every
    non-running row.

    `direction` orders the release against the running one: "newer",
    "older", or None (running itself, equal, or not comparable).
    """
    floor_version = registry.get("floor_version", FLOOR_VERSION)
    releases = sorted(
        registry.get("releases", []), key=lambda r: r.get("published_at") or "", reverse=True)
    newest_install_anywhere = max(
        (r["installed_at"][-1] for r in releases if r.get("installed_at")), default=None)
    views = []
    for release in releases:
        version = release.get("version")
        installed_at = release.get("installed_at", [])
        running = running_version is not None and version == running_version
        installed_now_at = None
        if running and installed_at and installed_at[-1] >= newest_install_anywhere:
            installed_now_at = installed_at[-1]
        views.append({
            "version": version,
            "released_at": release.get("released_at"),
            "notes": release.get("notes", []),
            "installed_at": installed_at,
            "bench": release.get("bench", False),
            "running": running,
            "installed_now_at": installed_now_at,
            "direction": _direction_from_running(version, running_version),
            "installable": (
                at_or_above_floor(version, floor_version) and version != running_version
            ),
        })
    return views


def update_view(registry, device_report, now):
    """The Update page's view model. `now` is accepted for signature
    symmetry with the rest of this pure section; the derivation below
    never reads the clock.
    """
    del now
    device_entry = _most_recent_device_entry(device_report, _document_type(registry)) or {}
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

    releases = _release_views(registry, running_version)

    return {
        "running_version": running_version,
        "reported_at": reported_at,
        "state": state,
        "state_at": state_at,
        "cancellable": cancellable,
        "rollback": rollback,
        # The version the current schedule targets, or None with no
        # schedule -- so the Update page can say WHICH release is
        # scheduled/in progress/failed and tag its history row, without
        # re-deriving the schedule's own rule.
        "target_version": schedule.get("version") if schedule is not None else None,
        "releases": releases,
    }
