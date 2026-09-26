#!/usr/bin/env python3
"""The project's first runtime-writable identity namespace.

Before this module, every airline identity `enrich.airline_from_callsign()`
could ever return came from a fixed, code-shipped table. This module adds
a mutable one: a `{3-letter ICAO callsign prefix: operator-supplied
airline name}` registry an authenticated companion-app operator can grow
at runtime, so a flight whose callsign prefix has no static-table entry
(and no adsbdb route) can still get a named illustration instead of the
generic fallback.

Copies `server/device_config.py`'s file contract exactly: never-raising
load, a per-field `normalise_*` gate, validate-before-write, and a write
through `server/atomic_io.py`'s `atomic_write()` (unique per-call temp
name, no leftover file on failure). The
companion writes this file (`add_entry()`/`delete_entry()`, from an
authenticated HTTP route) and the server reads it
(`load_manual_resolutions()`/`set_manual_registry_state_dir()`/
`airline_name_for_prefix()`, wired into `enrich`). Lives at
`{state_dir}/manual_resolutions.json`, outside the git-tracked tree, so
it survives a redeploy.

Imports `server.plane.illustrations` but must never import
`server.plane.enrich` - that direction is reserved for `enrich` to
import this module; the reverse would be an import cycle.

After this module, a value reaching `illustrations.py`'s path-
construction functions can originate from free-typed, authenticated-but-
hostile operator input instead of only ever a fixed-table value.
`_SAFE_KEY_RE` below is this module's own positive allowlist against
that, applied both before persisting and on every read.

`set_manual_registry_state_dir()`/cached `airline_name_for_prefix()` are
for the poll pipeline ONLY - one `run_once()` reads the registry once via
a process-global cache. `companion/` must never use the cache: it is a
long-running `ThreadingHTTPServer`, and every request must call
`load_manual_resolutions(state_dir)` fresh.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone

from server import atomic_io
from server.plane import illustrations

MANUAL_RESOLUTIONS_FILENAME = "manual_resolutions.json"

# A hard reject at the cap, not weakest-entry eviction: this registry is
# authenticated-human-curated one entry at a time through a web form,
# with no "weakest entry" concept the way a passively-observed sighting
# has (count/last_seen). Rejecting outright at the cap is the only policy
# that makes sense here.
MANUAL_RESOLUTION_MAX_ENTRIES = 200

MANUAL_AIRLINE_NAME_MAX_LEN = 100

RESERVED_KEY_PREFIX = "generic-"

_PREFIX_RE = re.compile(r"^[A-Z]{3}$")

# This module's positive allowlist against a hostile, free-typed airline
# name reaching illustrations.py's path construction: the slug must be a
# plain lowercase alphanumeric-and-hyphen token starting with an
# alphanumeric character, refused before it is ever persisted.
_SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Second, independent layer of the same defence, at the RAW input rather
# than the derived slug: illustrations.normalise_airline_key() strips
# every non-alphanumeric run to a single hyphen, so a raw path-shaped
# string (e.g. "../../etc/passwd") slugs to a harmless-looking result
# that would otherwise pass _SAFE_KEY_RE cleanly. Rejecting any raw name
# containing a path separator or a parent-directory sequence closes that
# gap.
_HOSTILE_NAME_RE = re.compile(r"[\\/]|\.\.")

# Result constants returned by add_entry(). Not flash keys -
# companion/app.py maps them onto its own flash keys; this module must
# not know anything about flashes.
ADD_OK = "ok"
ADD_REJECTED_PREFIX = "rejected_prefix"
ADD_REJECTED_NAME_EMPTY = "rejected_name_empty"
ADD_REJECTED_NAME_TOO_LONG = "rejected_name_too_long"
ADD_REJECTED_NAME_RESERVED = "rejected_name_reserved"
ADD_REJECTED_FULL = "rejected_full"
ADD_FAILED = "failed"

# Derived from illustrations.GENERIC_FALLBACK_FILENAME rather than a
# second hardcoded string, so the two can never drift apart.
_GENERIC_FALLBACK_KEY = illustrations.GENERIC_FALLBACK_FILENAME[: -len(".png")]

# Process-scoped cache, mirroring illustrations.set_override_state_dir().
# A None/falsy state_dir means "empty registry", matching pre-existing
# enrich test behaviour. Set once per poll cycle only.
_cached_registry = {}

# add_entry()/delete_entry() are both an unlocked load-modify-write-
# whole-file cycle, and companion/app.py runs under ThreadingHTTPServer -
# without this lock, two concurrent writers can each load the registry
# before either writes, silently losing whichever wrote second. A single
# process-wide lock, not per-state_dir: this codebase runs one companion
# process against one state_dir at a time.
_WRITE_LOCK = threading.Lock()


def manual_resolutions_path(state_dir):
    """Join `state_dir` and `MANUAL_RESOLUTIONS_FILENAME`."""
    return os.path.join(state_dir, MANUAL_RESOLUTIONS_FILENAME)


def normalise_prefix(raw):
    """Return the upper-cased 3-letter ICAO prefix for `raw`, or `None` for
    anything falsy, non-string, or not matching `_PREFIX_RE` after
    stripping and upper-casing. Never raises.
    """
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not _PREFIX_RE.match(candidate):
        return None
    return candidate


def normalise_manual_airline_name(raw):
    """Return `raw` stripped, or `None` for anything non-string, empty
    after stripping, or longer than `MANUAL_AIRLINE_NAME_MAX_LEN`. Never
    raises.

    This is the shared strip/type gate only - `add_entry()` distinguishes
    "empty" from "too long" itself (via two of its own checks) so it can
    return the two different `ADD_REJECTED_NAME_*` reasons; this helper
    just answers "is this a plausible airline name string at all".
    """
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if len(stripped) > MANUAL_AIRLINE_NAME_MAX_LEN:
        return None
    return stripped


def illustration_key_for_name(airline_name):
    """Turn a stored/candidate airline name into the illustration key it
    would resolve to, or `None` if that key would be unsafe or reserved.
    The single function every other module calls to turn a stored name
    into an illustration key.

    Returns `None` when `airline_name` itself contains a path separator
    or parent-directory sequence (checked at the raw input, not the
    derived slug - see `_HOSTILE_NAME_RE`), when
    `illustrations.normalise_airline_key()` returns `None`, when the slug
    fails `_SAFE_KEY_RE`, when it starts with `RESERVED_KEY_PREFIX`, or
    when it equals the generic-fallback stem.
    """
    if isinstance(airline_name, str) and _HOSTILE_NAME_RE.search(airline_name):
        return None
    slug = illustrations.normalise_airline_key(airline_name)
    if slug is None:
        return None
    if not _SAFE_KEY_RE.match(slug):
        return None
    if slug.startswith(RESERVED_KEY_PREFIX):
        return None
    if slug == _GENERIC_FALLBACK_KEY:
        return None
    return slug


def load_manual_resolutions(state_dir):
    """Read `{state_dir}/manual_resolutions.json`; never raises.

    A missing/unreadable/invalid/non-dict file yields `{}`. Otherwise
    entries are visited in sorted key order and each is rebuilt from
    scratch - never the parsed dict itself - dropping any entry with an
    invalid prefix, a non-dict value, an invalid airline name, an unsafe
    illustration key (defence in depth against a hand-edited file, not
    only input from `add_entry()`), or a non-string `created_at`.

    Stops once `MANUAL_RESOLUTION_MAX_ENTRIES` surviving entries have
    been collected, so a hand-edited oversized file can never make a page
    render unbounded.

    Because `add_entry()`/`delete_entry()` rewrite the whole file from
    exactly this validated view, any entry silently dropped here is
    permanently erased on the next write. This function does not (and
    must not) re-persist a rejected entry, but it does print one line
    naming how many entries will be dropped on the next write, whenever
    the raw file holds more than survive validation. The cap-triggered
    `break` is preserved as a `break`, not a `continue` that would keep
    validating every remaining key just to count it - that would reopen
    the unbounded-render risk the cap exists to close.

    Returns `{prefix: {"airline_name": name, "created_at": created_at}}`.
    """
    try:
        with open(manual_resolutions_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    sorted_keys = sorted(data.keys(), key=lambda k: k if isinstance(k, str) else "")
    registry = {}
    rejected = 0
    capped_remainder = 0
    for index, key in enumerate(sorted_keys):
        if len(registry) >= MANUAL_RESOLUTION_MAX_ENTRIES:
            capped_remainder = len(sorted_keys) - index
            break
        prefix = normalise_prefix(key)
        if prefix is None:
            rejected += 1
            continue
        value = data[key]
        if not isinstance(value, dict):
            rejected += 1
            continue
        airline_name = normalise_manual_airline_name(value.get("airline_name"))
        if airline_name is None:
            rejected += 1
            continue
        if illustration_key_for_name(airline_name) is None:
            rejected += 1
            continue
        created_at = value.get("created_at")
        if not isinstance(created_at, str):
            rejected += 1
            continue
        registry[prefix] = {"airline_name": airline_name, "created_at": created_at}

    dropped = rejected + capped_remainder
    if dropped:
        print(
            "manual_resolutions: %d entry/entries will be dropped from %s on the next write "
            "(malformed/unsafe, or beyond the %d-entry cap)"
            % (dropped, manual_resolutions_path(state_dir), MANUAL_RESOLUTION_MAX_ENTRIES))

    return registry


def add_entry(state_dir, prefix, airline_name, now=None):
    """Validate and persist one `{prefix: airline_name}` manual
    resolution. Returns one of the `ADD_*` module constants; never
    raises. The filesystem is touched only after every check passes:

      1. `normalise_prefix(prefix)` -> `ADD_REJECTED_PREFIX` on failure.
      2. type/strip the name; empty -> `ADD_REJECTED_NAME_EMPTY`;
         over-length -> `ADD_REJECTED_NAME_TOO_LONG`.
      3. `illustration_key_for_name(name)` returning `None` ->
         `ADD_REJECTED_NAME_EMPTY` (covers a path-shaped name as well as
         one whose slug collapses to nothing usable - same user-facing
         reason as empty, since the remedy is identical).
      4. reserved slug -> `ADD_REJECTED_NAME_RESERVED`.
      5. load the current registry; a new prefix when already at
         `MANUAL_RESOLUTION_MAX_ENTRIES` -> `ADD_REJECTED_FULL`.

    `now` defaults to a UTC ISO-8601 string, computed here but
    injectable. Re-adding an existing prefix overwrites it with a fresh
    `created_at` - delete-and-re-add is the correction path, so an
    overwrite is treated as a new entry, not an update-in-place.

    Writes via `atomic_io.atomic_write` (unique per-call temp name, no
    leftover file on failure); any exception during the write is caught
    and `ADD_FAILED` returned instead of re-raising - the caller is an
    HTTP route handler that needs a flash key, not a traceback.

    Step 5's load-check-mutate-write is one atomic unit under
    `_WRITE_LOCK`, since a `ThreadingHTTPServer` could otherwise let two
    concurrent writers each load before either writes, silently losing
    whichever wrote second.
    """
    normalised_prefix = normalise_prefix(prefix)
    if normalised_prefix is None:
        return ADD_REJECTED_PREFIX

    name = normalise_manual_airline_name(airline_name)
    if name is None:
        if isinstance(airline_name, str) and len(airline_name.strip()) > MANUAL_AIRLINE_NAME_MAX_LEN:
            return ADD_REJECTED_NAME_TOO_LONG
        return ADD_REJECTED_NAME_EMPTY

    key = illustration_key_for_name(name)
    if key is None:
        # Distinguish "reserved" from "collapsed to nothing usable" so the
        # operator gets an accurate reason.
        slug = illustrations.normalise_airline_key(name)
        if slug is not None and _SAFE_KEY_RE.match(slug) and (
            slug.startswith(RESERVED_KEY_PREFIX) or slug == _GENERIC_FALLBACK_KEY
        ):
            return ADD_REJECTED_NAME_RESERVED
        return ADD_REJECTED_NAME_EMPTY

    with _WRITE_LOCK:
        registry = load_manual_resolutions(state_dir)
        if normalised_prefix not in registry and len(registry) >= MANUAL_RESOLUTION_MAX_ENTRIES:
            return ADD_REJECTED_FULL

        if now is None:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        registry[normalised_prefix] = {"airline_name": name, "created_at": now}

        try:
            os.makedirs(state_dir, exist_ok=True)
            atomic_io.atomic_write(manual_resolutions_path(state_dir), json.dumps(registry, indent=1))
        except Exception:
            return ADD_FAILED

    return ADD_OK


def delete_entry(state_dir, prefix):
    """Remove `prefix` from the registry at `state_dir`. Returns `True`
    when an entry was removed, `False` for an unknown/malformed prefix or
    a write failure. Idempotent, never raises.

    Rewrites the JSON file and nothing else - must not touch the
    illustration override directory. The override is keyed on the
    airline NAME, not the prefix: two different prefixes can resolve to
    the same carrier and share one override file the Airlines gallery
    flow may have written by a different path entirely, so deleting from
    a path this function does not own could destroy an override neither
    this resolution nor its prefix has any exclusive claim to. The
    accepted cost is an orphaned override PNG with no garbage collection.

    The load-check-mutate-write sequence is one atomic unit under
    `_WRITE_LOCK`, shared with `add_entry()` (a `ThreadingHTTPServer` can
    run both concurrently).
    """
    normalised_prefix = normalise_prefix(prefix)
    if normalised_prefix is None:
        return False

    with _WRITE_LOCK:
        registry = load_manual_resolutions(state_dir)
        if normalised_prefix not in registry:
            return False

        del registry[normalised_prefix]

        try:
            os.makedirs(state_dir, exist_ok=True)
            atomic_io.atomic_write(manual_resolutions_path(state_dir), json.dumps(registry, indent=1))
        except Exception:
            return False

    return True


def entry_rows(registry):
    """Return `(prefix, airline_name, created_at)` tuples from an
    already-loaded registry dict, sorted by prefix ascending, skipping any
    malformed entry. Mirrors `health_page.unresolved_rows()`'s defensive
    shape so the management list renders deterministically. Never raises.
    """
    rows = []
    if not isinstance(registry, dict):
        return rows
    for prefix in sorted(k for k in registry.keys() if isinstance(k, str)):
        entry = registry[prefix]
        if not isinstance(entry, dict):
            continue
        airline_name = entry.get("airline_name")
        created_at = entry.get("created_at")
        if not isinstance(airline_name, str) or not isinstance(created_at, str):
            continue
        rows.append((prefix, airline_name, created_at))
    return rows


def set_manual_registry_state_dir(state_dir):
    """Set the process-wide cached registry the poll pipeline reads
    through `airline_name_for_prefix()`, mirroring
    `illustrations.set_override_state_dir()`.

    Call once per poll cycle, beside the existing
    `illustrations.set_override_state_dir(state_dir)` call: a
    companion-side save landing mid-cycle must not split one poll cycle
    across two different registries.

    `state_dir` truthy -> cache `load_manual_resolutions(state_dir)`.
    `state_dir` falsy (including `None`) -> cache `{}`.
    """
    global _cached_registry
    if state_dir:
        _cached_registry = load_manual_resolutions(state_dir)
    else:
        _cached_registry = {}


def airline_name_for_prefix(prefix):
    """Return the cached manual-resolution airline name for a normalised
    3-letter prefix, or `None`. Reads only the process-wide cache set by
    `set_manual_registry_state_dir()` - never touches the disk.

    A process that never calls the setter sees an empty registry here,
    matching pre-existing `enrich` test behaviour.
    """
    normalised_prefix = normalise_prefix(prefix)
    if normalised_prefix is None:
        return None
    entry = _cached_registry.get(normalised_prefix)
    if not isinstance(entry, dict):
        return None
    airline_name = entry.get("airline_name")
    if not isinstance(airline_name, str):
        return None
    return airline_name
