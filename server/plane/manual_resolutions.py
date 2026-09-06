#!/usr/bin/env python3
"""The project's first runtime-writable identity namespace (D-01, phase 13
CONTEXT.md).

Before this phase, every airline identity `enrich.airline_from_callsign()`
could ever return came from a fixed, code-shipped table
(`_ICAO_AIRLINE_PREFIXES`). This module adds the first mutable one: a
`{3-letter ICAO callsign prefix: operator-supplied airline name}` registry
that an authenticated companion-app operator can grow at runtime, so a
flight whose callsign prefix has no static-table entry (and no adsbdb
route) can still get a named illustration instead of the generic fallback.

D-05 says to copy `server/device_config.py`'s file contract *exactly*:
never-raising load, a per-field `normalise_*` gate, validate-before-write,
tmp-write then `os.replace()`, and stray-`.tmp` cleanup in the `except`
branch. The companion writes this file (via `add_entry()`/`delete_entry()`
from an authenticated HTTP route handler, plan 13-06) and the server reads
it (via `load_manual_resolutions()`/`set_manual_registry_state_dir()`/
`airline_name_for_prefix()`, wired into `enrich` by plan 13-03). It
survives a redeploy for the same reason `device_config.json` and
`illustration_overrides/` do: `deploy/deploy.sh` rsyncs `server/` with
`--delete`, excluding only `state` (`server/state/.gitignore` is `*` +
`!.gitignore`) — this file lives at `{state_dir}/manual_resolutions.json`,
never inside a git-tracked directory.

This module imports `server.plane.illustrations` (for
`normalise_airline_key()` and `GENERIC_FALLBACK_FILENAME`) but must NEVER
import `server.plane.enrich` — that direction is reserved for
`enrich` to import *this* module (plan 13-03); the reverse would be an
import cycle.

**Threat T-13-02** (see 13-01-PLAN.md's threat model): after D-01, a value
that reaches `illustrations.py`'s path-construction functions
(`illustration_path_for_key()` / `override_path_for_key()`) can originate
from a free-typed, authenticated-but-hostile operator input instead of only
ever a fixed-table value. `_SAFE_KEY_RE` below is this module's own
positive allowlist against that threat, applied both before persisting
(`add_entry()`) and on every read (`load_manual_resolutions()`), so
`illustrations.py`'s own `_UNSAFE_KEY_RE` stays a defence-in-depth second
line rather than the sole line.

**Caching warning:** `set_manual_registry_state_dir()` / cached
`airline_name_for_prefix()` are for the poll pipeline ONLY — a single
`run_once()` invocation that reads the registry once at cycle start via a
process-global cache, exactly mirroring
`illustrations.set_override_state_dir()`. `companion/` must NEVER use the
cache: it is a long-running `ThreadingHTTPServer`, and every request must
call `load_manual_resolutions(state_dir)` fresh, exactly as
`page_context()` already calls `device_config.load_device_config(state_dir)`
per request.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone

from server.plane import illustrations

MANUAL_RESOLUTIONS_FILENAME = "manual_resolutions.json"

# T-13-04: a hard reject at the cap, not weakest-entry eviction, following
# enrich.UNRESOLVED_PREFIX_MAX_ENTRIES (200)'s precedent for "bound a
# JSON-file-backed registry against unbounded growth" — but with a
# deliberately different policy (RESEARCH.md Assumption A2): this registry
# is authenticated-human-curated, one entry at a time through a web form,
# with no "weakest entry" concept the way a passively-observed
# unresolved-prefix sighting has (count/last_seen). Rejecting outright at
# the cap is the only policy that makes sense here.
MANUAL_RESOLUTION_MAX_ENTRIES = 200

MANUAL_AIRLINE_NAME_MAX_LEN = 100

RESERVED_KEY_PREFIX = "generic-"

_PREFIX_RE = re.compile(r"^[A-Z]{3}$")

# T-13-02's positive allowlist: this module's share of the defence against a
# hostile, free-typed airline name reaching illustrations.py's path
# construction. After D-01, illustrations.normalise_airline_key()'s output
# is no longer only ever derived from a fixed table of airline names — it
# can now be derived from operator-supplied text. Anything whose slug is
# not a plain lowercase alphanumeric-and-hyphen token, starting with an
# alphanumeric character, is refused before it is ever persisted.
_SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Second, independent layer of the same T-13-02 defence, at the RAW input
# rather than the derived slug: illustrations.normalise_airline_key() is a
# total function that strips every non-alphanumeric run down to a single
# hyphen, so a raw path-shaped string like "../../etc/passwd" or "a/b"
# slugs to a *harmless-looking* result ("etc-passwd", "a-b") that would
# otherwise pass `_SAFE_KEY_RE` cleanly. Rejecting any raw name containing
# a path separator or a parent-directory sequence - mirroring
# illustrations.py's own `_UNSAFE_KEY_RE` shape exactly - means a
# path-shaped free-typed name is refused outright rather than silently
# reduced to something unrelated and stored as a real airline's display
# name.
_HOSTILE_NAME_RE = re.compile(r"[\\/]|\.\.")

# Result constants returned by add_entry(). These are NOT flash keys —
# companion/app.py (plan 13-06) maps them onto its own FLASH_MANUAL_* keys;
# this module must not know anything about flashes.
ADD_OK = "ok"
ADD_REJECTED_PREFIX = "rejected_prefix"
ADD_REJECTED_NAME_EMPTY = "rejected_name_empty"
ADD_REJECTED_NAME_TOO_LONG = "rejected_name_too_long"
ADD_REJECTED_NAME_RESERVED = "rejected_name_reserved"
ADD_REJECTED_FULL = "rejected_full"
ADD_FAILED = "failed"

# The generic-fallback filename's stem, derived from
# illustrations.GENERIC_FALLBACK_FILENAME rather than a second hardcoded
# "generic-fallback" string, so the two can never drift apart.
_GENERIC_FALLBACK_KEY = illustrations.GENERIC_FALLBACK_FILENAME[: -len(".png")]

# Process-scoped cache, mirroring illustrations.set_override_state_dir().
# `None` state_dir (never called, or called with a falsy state_dir) means
# "empty registry" — exactly today's behaviour, which is what keeps every
# existing enrich test unchanged. Set once per poll cycle only.
_cached_registry = {}

# WR-02 fix: `add_entry()`/`delete_entry()` are both an unlocked
# load-modify-write-whole-file cycle, and `companion/app.py` runs under
# `ThreadingHTTPServer` — a real deployment. Without this lock, two
# concurrent writers (an add and a delete, or two adds) can each load the
# registry before either has written, then each write back a version that
# is missing the other's change (a silent lost update); serialising the
# whole load-modify-write cycle per writer, not just the final
# `os.replace()`, is what closes that window. This is a single process-wide
# lock, not per-state_dir — this codebase runs one companion process
# against one state_dir at a time, exactly like `illustrations.py`'s own
# override-write path assumes.
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

    This is the shared strip/type gate only — `add_entry()` distinguishes
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

    This is the single function every other module in this phase calls to
    turn a stored name into an illustration key — plan 13-06 uses it to
    build the membership union with the vendored/override illustration
    filenames, plan 13-04 uses it to decide whether artwork already exists
    for a given manual resolution.

    Returns `None` when the raw `airline_name` itself contains a path
    separator or a parent-directory sequence (`_HOSTILE_NAME_RE` - a
    second, independent layer of T-13-02's defence, checked at the raw
    input rather than the derived slug; see that constant's own comment
    for why this check cannot be replaced by a slug-shape check alone),
    when `illustrations.normalise_airline_key(airline_name)` returns
    `None`, when the slug does not match `_SAFE_KEY_RE`, when the slug
    starts with `RESERVED_KEY_PREFIX`, or when the slug equals the
    generic-fallback filename's stem (`"generic-fallback"`).
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

    A missing file, an unreadable file, invalid JSON, or a non-dict top
    level all yield `{}`. Otherwise the parsed dict's items are visited in
    `sorted()` key order and each entry is rebuilt from scratch — never the
    parsed dict itself — dropping any entry where:
      - `normalise_prefix(key)` is `None`,
      - the value is not a dict,
      - `normalise_manual_airline_name(value.get("airline_name"))` is
        `None`,
      - `illustration_key_for_name(...)` of that name is `None` (defence in
        depth against a hand-edited file storing a reserved/unsafe name,
        not only against one submitted through `add_entry()`), or
      - `value.get("created_at")` is not a string.

    Stops once `MANUAL_RESOLUTION_MAX_ENTRIES` surviving entries have been
    collected, so a hand-edited oversized file can never make a page
    render unbounded (T-13-04/T-13-12).

    WR-03 fix: because `add_entry()`/`delete_entry()` rewrite the whole
    file from exactly this validated view, any entry this function
    silently dropped is permanently erased the next time either function
    writes — a 250-entry hand-migrated file loses 50 entries the moment
    the operator clicks Delete on one row, and a rejected/malformed entry
    vanishes on the next Add. This function does not (and, given
    `illustration_key_for_name()`'s own re-check being deliberate defence
    in depth against a hand-edited unsafe/reserved name — T-13-02 — must
    not) silently re-persist an entry it itself rejects. What it CAN do
    is stop the loss from being silent: whenever the raw file holds more
    entries than survive validation (whether rejected outright or beyond
    the cap), this prints one line naming how many will be dropped on the
    next write, before returning the validated view exactly as before.
    The cap-triggered `break` below is preserved as a `break`, not
    changed to a `continue` that would keep validating every remaining
    key just to count it — that would reopen the exact unbounded-render
    risk (T-13-04/T-13-12) the cap exists to close; the drop count for
    that case is the untouched remainder's size, not a per-entry re-walk.

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
    """Validate and persist one `{prefix: airline_name}` manual resolution.
    Returns one of the `ADD_*` module constants; never raises.

    Validation order (the filesystem is touched only after every check
    passes):
      1. `normalise_prefix(prefix)` -> `ADD_REJECTED_PREFIX` on failure.
      2. type/strip the name; empty -> `ADD_REJECTED_NAME_EMPTY`;
         over-length -> `ADD_REJECTED_NAME_TOO_LONG`.
      3. `illustration_key_for_name(name)` returning `None` ->
         `ADD_REJECTED_NAME_EMPTY` (covers a raw name shaped like a path -
         `_HOSTILE_NAME_RE` - as well as one whose slug collapses to
         nothing usable; both get the same user-facing reason as an empty
         name, since the operator's remedy is identical: type a real
         airline name).
      4. reserved slug (`RESERVED_KEY_PREFIX` or the generic-fallback stem)
         -> `ADD_REJECTED_NAME_RESERVED`.
      5. load the current registry; when `prefix` is not already a key AND
         the registry is already at `MANUAL_RESOLUTION_MAX_ENTRIES` ->
         `ADD_REJECTED_FULL`.

    Only once all of the above pass does this function touch the
    filesystem. `now` defaults to a timezone-aware UTC ISO-8601 string
    (seconds precision), computed here but injectable so a harness can pin
    it. `registry[prefix] = {"airline_name": name, "created_at": now}` is
    set unconditionally at this point — re-adding an existing prefix
    overwrites it with a *fresh* `created_at` (D-07 makes delete-and-re-add
    the correction path, so an overwrite is treated as a new entry, not an
    update-in-place).

    Writes with `device_config.py`'s tmp-write-then-`os.replace()` idiom:
    `os.makedirs(state_dir, exist_ok=True)`, write to a per-writer-unique
    temp path, then `os.replace(tmp, path)`. Unlike `save_device_config()`
    (which raises on a write failure), any exception during the write is
    caught here, the stray temp file is removed if present, and
    `ADD_FAILED` is returned instead of re-raising — the caller is an HTTP
    route handler that needs a flash key to show the operator, not a
    traceback.

    WR-02 fix: step 5's load-check-mutate-write is one atomic unit under
    `_WRITE_LOCK` — `companion/app.py` is a `ThreadingHTTPServer`, so two
    concurrent writers (this function and/or `delete_entry()`) could
    otherwise each load the registry before either writes, silently
    losing whichever wrote second. The temp filename additionally
    includes the writer's own pid and thread id (rather than a single
    fixed `path + ".tmp"`), so two writers — even ones that briefly raced
    outside the lock, or a hand-run script sharing the same state dir —
    can never have their `json.dump()` calls interleave into the same
    file descriptor.
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

        path = manual_resolutions_path(state_dir)
        tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(tmp, "w") as fh:
                json.dump(registry, fh, indent=1)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            return ADD_FAILED

    return ADD_OK


def delete_entry(state_dir, prefix):
    """Remove `prefix` from the registry at `state_dir`. Returns `True`
    when an entry was removed, `False` for an unknown prefix, a malformed
    prefix, or a write failure. Idempotent, never raises.

    This function rewrites the JSON file and nothing else — it must not
    construct, stat, or unlink any path under the illustration override
    directory (D-08). The override is keyed on the *airline name*, not the
    prefix: two different prefixes resolved to the same carrier share one
    override file, and the existing Airlines gallery flow can have written
    that same key by a different path entirely. Deleting a file from a
    path this function does not own could destroy an override neither this
    manual resolution nor its prefix has any exclusive claim to. The
    accepted cost is an orphaned override PNG with no garbage collection —
    deliberately, not an oversight.

    WR-02 fix: the load-check-mutate-write sequence below is one atomic
    unit under `_WRITE_LOCK`, shared with `add_entry()` — see that
    function's own docstring for why (a `ThreadingHTTPServer` can run this
    function and `add_entry()` concurrently). The temp filename likewise
    carries this writer's own pid and thread id rather than a single fixed
    name.
    """
    normalised_prefix = normalise_prefix(prefix)
    if normalised_prefix is None:
        return False

    with _WRITE_LOCK:
        registry = load_manual_resolutions(state_dir)
        if normalised_prefix not in registry:
            return False

        del registry[normalised_prefix]

        path = manual_resolutions_path(state_dir)
        tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
        try:
            os.makedirs(state_dir, exist_ok=True)
            with open(tmp, "w") as fh:
                json.dump(registry, fh, indent=1)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            return False

    return True


def entry_rows(registry):
    """Return `(prefix, airline_name, created_at)` tuples from an
    already-loaded registry dict, sorted by prefix ascending, skipping any
    malformed entry. Mirrors `health_page.unresolved_rows()`'s defensive
    shape so the management list (plan 13-04) renders deterministically.
    Never raises.
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
    """Set the process-wide cached registry the poll pipeline reads through
    `airline_name_for_prefix()`, mirroring
    `illustrations.set_override_state_dir()`.

    Call once per poll cycle from `run_once()`, beside the existing
    `illustrations.set_override_state_dir(state_dir)` call, for exactly
    the reason `poll_loop.py`'s own comment gives for `device_cfg`: a
    companion-side save landing mid-cycle must not split one poll cycle
    across two different registries (one read at the start, a different
    one read partway through).

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
    `set_manual_registry_state_dir()` — never touches the disk.

    A process that never calls the setter sees an empty registry here,
    i.e. exactly today's (pre-phase-13) behaviour — this is what keeps
    every existing `enrich` test unchanged.
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
