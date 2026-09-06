#!/usr/bin/env python3
"""The per-flight colour-rule registry (D-07/D-08/D-09/D-12) plus the single
effective-theme resolution function every render of a displayed flight
goes through (D-13).

This module imports `server.device_config` (for `THEMES` membership
validation against a persisted or resolved theme id) plus stdlib only. It
must NEVER import `server.plane.enrich`, `server.plane.detect`,
`server.plane.illustrations`, `server.plane.manual_resolutions`, or
`server.plane.render` — `poll_loop.py` already imports all of those plus
this module, and the reverse direction would make
`poll_loop -> colour_rules -> X -> poll_loop` a real import cycle (D-13).
Its callsign/prefix normalisers therefore deliberately DUPLICATE small
primitives already defined in `enrich.py` (`normalise_callsign()`) and
`manual_resolutions.py` (`normalise_prefix()`) rather than import them —
the same layering choice `stub-server/byos_server.py` already makes for
`seconds_until_quiet_hours_end()` across its own vendor boundary.

**Caching warning:** `set_colour_rules_state_dir()` and the cache
`resolve_effective_theme_id()` reads through are for the once-per-cycle
poll pipeline ONLY — a single `run_once()` invocation reads the registry
once at cycle start via a process-global cache, exactly mirroring
`illustrations.set_override_state_dir()` /
`manual_resolutions.set_manual_registry_state_dir()`. `companion/` is a
long-running `ThreadingHTTPServer`; every request must call
`load_colour_rules(state_dir)` fresh instead, exactly as `page_context()`
already does for `manual_resolutions.load_manual_resolutions(state_dir)`.

**D-02 extensibility note:** a rule record is a dict (`{"theme_id": ...,
"created_at": ...}`), deliberately not a bare theme-id string, so a future
entry can carry fields this phase does not define (a roster link, for
instance). No such field is reserved, added, or read here — every rule in
this phase is purely manual, added and removed one at a time through the
Settings UI.

This file survives a redeploy because `deploy/deploy.sh` rsyncs `server/`
with `--delete` while excluding `state` — like `manual_resolutions.json`
and `device_config.json`, it lives at `{state_dir}/colour_rules.json`,
never inside a git-tracked directory.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone

from server import device_config

COLOUR_RULES_FILENAME = "colour_rules.json"

# T-14-04: a hard reject at the cap, never weakest-entry eviction, following
# manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES (200)'s precedent and
# its same policy: this registry is authenticated-human-curated one entry
# at a time, with no "weakest entry" concept to evict. This count is
# summed ACROSS all three kinds, not per kind. This number is also what
# companion/'s registry-full flash copy interpolates, so it and that copy
# must agree.
COLOUR_RULE_MAX_ENTRIES = 200

RULE_KIND_CALLSIGN = "callsign"
RULE_KIND_HEX = "hex"
RULE_KIND_PREFIX = "prefix"
# This tuple's order is load-bearing twice over: it is D-09's
# most-specific-wins resolution order (exact callsign > hex > prefix), and
# it is rule_rows()'s sort order.
RULE_KINDS = (RULE_KIND_CALLSIGN, RULE_KIND_HEX, RULE_KIND_PREFIX)

# The one render state the arrivals override applies to (D-04/D-06).
ARRIVING_STATE = "arriving"

# T-14-01's three positive-allowlist regexes, each compiled once, each this
# module's share of the defence against a hand-edited or corrupted file
# smuggling a crafted key into a live comparison.
#
# Duplicates enrich.normalise_callsign()'s strip-and-upper transform plus
# an eight-character real-world bound taken from enrich.py's own comment
# ("real callsigns are at most eight characters", near its
# _AIRLINE_PREFIX_SHAPE_RE).
_CALLSIGN_RULE_RE = re.compile(r"^[A-Z0-9]{2,8}$")
# New ground: no ICAO24 normaliser exists anywhere in this codebase today.
# Canonicalises to UPPERCASE even though live ADS-B `hex` values arrive
# lowercase (server/plane/detect.py's _normalise_selection() passes it
# through raw and unvalidated) — the resolver below uppercases the live
# value before ever looking it up.
_HEX_RULE_RE = re.compile(r"^[0-9A-F]{6}$")
# Duplicates manual_resolutions.normalise_prefix()'s gate exactly.
_PREFIX_RE = re.compile(r"^[A-Z]{3}$")

# Result constants returned by add_rule(). These are NOT flash keys —
# companion/app.py (plan 14-05) maps them onto its own flash vocabulary;
# this module must not know flashes exist.
#
# The ADD_OK_NEW/ADD_OK_REPLACED split is this module's one deliberate
# divergence from manual_resolutions.py's single ADD_OK: D-09 requires the
# companion to say "replaced" rather than "added", and computing that at
# the HTTP layer would be a TOCTOU race against the write that just
# happened — so it is computed here, inside the write lock, before the
# mutation (see add_rule()'s `replacing` local).
ADD_OK_NEW = "ok_new"
ADD_OK_REPLACED = "ok_replaced"
ADD_REJECTED_KIND = "rejected_kind"
ADD_REJECTED_KEY = "rejected_key"
ADD_REJECTED_THEME = "rejected_theme"
ADD_REJECTED_FULL = "rejected_full"
ADD_FAILED = "failed"

# WR-02-style fix, applied from day one here (T-14-02): add_rule()/
# delete_rule() are both a load-modify-write whole-file cycle, and
# companion/app.py runs under ThreadingHTTPServer — a real deployment.
# This single process-wide lock serialises the ENTIRE load-check-mutate-
# write sequence per writer, not just the final os.replace(), so two
# concurrent writers can never each load the registry before either has
# written and silently lose one of their updates.
_WRITE_LOCK = threading.Lock()

# Process-scoped cache, mirroring illustrations.set_override_state_dir()/
# manual_resolutions.set_manual_registry_state_dir(). A process that never
# calls set_colour_rules_state_dir() sees the empty registry shape here —
# exactly today's (pre-phase-14) behaviour.
_cached_rules = {kind: {} for kind in RULE_KINDS}


def colour_rules_path(state_dir):
    """Join `state_dir` and `COLOUR_RULES_FILENAME`."""
    return os.path.join(state_dir, COLOUR_RULES_FILENAME)


def normalise_rule_kind(raw):
    """Return the member of `RULE_KINDS` when `raw` is exactly one of
    them, else `None`. Never raises.
    """
    if isinstance(raw, str) and raw in RULE_KINDS:
        return raw
    return None


def normalise_rule_callsign(raw):
    """Strip and upper-case `raw`; return the canonical value only when it
    matches `_CALLSIGN_RULE_RE` (two-to-eight uppercase alphanumerics),
    else `None`. Never raises.
    """
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not candidate or not _CALLSIGN_RULE_RE.match(candidate):
        return None
    return candidate


def normalise_rule_hex(raw):
    """Strip and upper-case `raw`; return the canonical value only when it
    matches `_HEX_RULE_RE` (exactly six uppercase hex digits), else
    `None`. Never raises.
    """
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not _HEX_RULE_RE.match(candidate):
        return None
    return candidate


def normalise_rule_prefix(raw):
    """Strip and upper-case `raw`; return the canonical value only when it
    matches `_PREFIX_RE` (exactly three uppercase letters), else `None`.
    Never raises.
    """
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not _PREFIX_RE.match(candidate):
        return None
    return candidate


def normalise_rule_value(kind, raw):
    """Dispatch to the per-kind normaliser above on a normalised `kind`;
    an unknown kind returns `None`. Never raises.

    This is the single entry point `add_rule()`, `load_colour_rules()`,
    `delete_rule()` and `companion/app.py`'s delete route all use, so
    there is exactly one definition of "a valid rule key" in the
    codebase.
    """
    normalised_kind = normalise_rule_kind(kind)
    if normalised_kind is None:
        return None
    if normalised_kind == RULE_KIND_CALLSIGN:
        return normalise_rule_callsign(raw)
    if normalised_kind == RULE_KIND_HEX:
        return normalise_rule_hex(raw)
    return normalise_rule_prefix(raw)


def normalise_rule_theme_id(raw):
    """Return `raw` unchanged only when it is a string present in
    `device_config.THEMES`, else `None`. Never raises, and never degrades
    to `device_config.DEFAULT_THEME_ID` — an unrecognised theme id means
    the rule is invalid and gets dropped, not silently retargeted at the
    default.
    """
    if isinstance(raw, str) and raw in device_config.THEMES:
        return raw
    return None


def load_colour_rules(state_dir):
    """Read `{state_dir}/colour_rules.json`; never raises.

    A missing file, an unreadable file, invalid JSON, or a non-dict top
    level all yield the empty registry shape — a dict with all three
    `RULE_KINDS` keys mapping to `{}` — so every caller can index by kind
    without a `.get()` dance.

    Entries are visited kind-by-kind in `RULE_KINDS` order, then in
    `sorted()` key order within a kind, and each surviving entry is
    rebuilt from scratch — never the parsed dict reused directly —
    dropping any entry where `normalise_rule_value(kind, key)` is `None`,
    the value is not a dict, `normalise_rule_theme_id(value.get("theme_id"))`
    is `None`, or `value.get("created_at")` is not a string. This is
    defence in depth against a hand-edited file: the same allowlist
    `add_rule()` applies before persisting is re-applied here on every
    read (T-14-01), and the same THEMES membership check `add_rule()`
    applies is re-applied here too (T-14-05).

    Stops once `COLOUR_RULE_MAX_ENTRIES` surviving entries have been
    accumulated across all kinds, so a hand-edited oversized file cannot
    make a page render or a poll cycle unbounded (T-14-04). When the raw
    file held more entries than survived, prints (never raises) a
    one-line warning naming the drop count.
    """
    try:
        with open(colour_rules_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    ordered_pairs = []
    for kind in RULE_KINDS:
        kind_data = data.get(kind)
        if not isinstance(kind_data, dict):
            continue
        for key in sorted(k for k in kind_data.keys() if isinstance(k, str)):
            ordered_pairs.append((kind, key, kind_data[key]))

    registry = {kind: {} for kind in RULE_KINDS}
    rejected = 0
    capped_remainder = 0
    surviving = 0
    for index, (kind, key, value) in enumerate(ordered_pairs):
        if surviving >= COLOUR_RULE_MAX_ENTRIES:
            capped_remainder = len(ordered_pairs) - index
            break
        normalised_key = normalise_rule_value(kind, key)
        if normalised_key is None:
            rejected += 1
            continue
        if not isinstance(value, dict):
            rejected += 1
            continue
        theme_id = normalise_rule_theme_id(value.get("theme_id"))
        if theme_id is None:
            rejected += 1
            continue
        created_at = value.get("created_at")
        if not isinstance(created_at, str):
            rejected += 1
            continue
        registry[kind][normalised_key] = {"theme_id": theme_id, "created_at": created_at}
        surviving += 1

    dropped = rejected + capped_remainder
    if dropped:
        print(
            "colour_rules: %d entry/entries will be dropped from %s on the next write "
            "(malformed/unsafe, or beyond the %d-entry cap)"
            % (dropped, colour_rules_path(state_dir), COLOUR_RULE_MAX_ENTRIES))

    return registry


def add_rule(state_dir, kind, value, theme_id, now=None):
    """Validate and persist one `(kind, value) -> theme_id` colour rule.
    Returns one of the `ADD_*` module constants; never raises.

    Validation order (the filesystem is touched only after every check
    passes): `normalise_rule_kind()` -> `ADD_REJECTED_KIND`;
    `normalise_rule_value()` -> `ADD_REJECTED_KEY`;
    `normalise_rule_theme_id()` -> `ADD_REJECTED_THEME`.

    Then `_WRITE_LOCK` is held across the entire load-check-mutate-write
    sequence, not just the final replace. Inside the lock: the current
    registry is loaded; `replacing` is computed as whether the normalised
    value is already a key under that kind — this membership test is the
    added-versus-replaced answer and is computed here, inside the lock,
    before mutating (D-09) — a second read outside the lock would be a
    TOCTOU race against a concurrent writer. When not replacing and the
    total entry count across all kinds is already at
    `COLOUR_RULE_MAX_ENTRIES`, returns `ADD_REJECTED_FULL` (a replace is
    not growth, so re-adding an existing key at the cap still succeeds).

    `now` defaults to a timezone-aware UTC ISO-8601 string (seconds
    precision), injectable so a harness can pin it. Writes with
    `manual_resolutions.py`'s tmp-write-then-`os.replace()` idiom: the
    temp filename embeds both `os.getpid()` and `threading.get_ident()`
    so two concurrent companion writers can never interleave into the
    same temp path (T-14-02). Any exception during the write is caught,
    the stray temp file is removed if present, and `ADD_FAILED` is
    returned rather than re-raised — the caller is an HTTP route handler
    that needs a flash key, not a traceback.
    """
    normalised_kind = normalise_rule_kind(kind)
    if normalised_kind is None:
        return ADD_REJECTED_KIND

    normalised_value = normalise_rule_value(normalised_kind, value)
    if normalised_value is None:
        return ADD_REJECTED_KEY

    normalised_theme_id = normalise_rule_theme_id(theme_id)
    if normalised_theme_id is None:
        return ADD_REJECTED_THEME

    with _WRITE_LOCK:
        registry = load_colour_rules(state_dir)
        replacing = normalised_value in registry[normalised_kind]
        total_entries = sum(len(registry[k]) for k in RULE_KINDS)
        if not replacing and total_entries >= COLOUR_RULE_MAX_ENTRIES:
            return ADD_REJECTED_FULL

        if now is None:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        registry[normalised_kind][normalised_value] = {
            "theme_id": normalised_theme_id,
            "created_at": now,
        }

        path = colour_rules_path(state_dir)
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

    return ADD_OK_REPLACED if replacing else ADD_OK_NEW


def delete_rule(state_dir, kind, value):
    """Remove `(kind, value)` from the registry at `state_dir`. Returns
    `True` when an entry was removed, `False` otherwise (unknown kind,
    malformed value, absent key, or a write failure). Idempotent, never
    raises.

    Same `_WRITE_LOCK` discipline and the same tmp-write-then-
    `os.replace()` block with `except` cleanup as `add_rule()`, returning
    `False` instead of `ADD_FAILED` on exception.
    """
    normalised_kind = normalise_rule_kind(kind)
    if normalised_kind is None:
        return False

    normalised_value = normalise_rule_value(normalised_kind, value)
    if normalised_value is None:
        return False

    with _WRITE_LOCK:
        registry = load_colour_rules(state_dir)
        if normalised_value not in registry[normalised_kind]:
            return False

        del registry[normalised_kind][normalised_value]

        path = colour_rules_path(state_dir)
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


def rule_rows(registry):
    """Return `(kind, value, theme_id, created_at)` tuples from an
    already-loaded registry, ordered by kind in `RULE_KINDS` order then by
    value ascending, skipping any malformed entry. Never raises. This is
    what the Settings rules list renders from, so its determinism is what
    makes that list's markup testable.
    """
    rows = []
    if not isinstance(registry, dict):
        return rows
    for kind in RULE_KINDS:
        kind_data = registry.get(kind)
        if not isinstance(kind_data, dict):
            continue
        for value in sorted(k for k in kind_data.keys() if isinstance(k, str)):
            entry = kind_data[value]
            if not isinstance(entry, dict):
                continue
            theme_id = entry.get("theme_id")
            created_at = entry.get("created_at")
            if not isinstance(theme_id, str) or not isinstance(created_at, str):
                continue
            rows.append((kind, value, theme_id, created_at))
    return rows


def set_colour_rules_state_dir(state_dir):
    """Set the process-wide cached registry `resolve_effective_theme_id()`
    reads through, mirroring `illustrations.set_override_state_dir()` /
    `manual_resolutions.set_manual_registry_state_dir()`.

    Call once per poll cycle from `run_once()`, beside those two existing
    calls, for the reason `poll_loop.py`'s own comment already gives for
    `device_cfg`: a companion-side save landing mid-cycle must never split
    one rendered panel across two configurations.

    `state_dir` truthy -> cache `load_colour_rules(state_dir)`.
    `state_dir` falsy (including `None`) -> cache the empty registry
    shape. A process that never calls this setter sees an empty registry,
    i.e. exactly today's behaviour, which is what keeps every existing
    test unchanged.
    """
    global _cached_rules
    if state_dir:
        _cached_rules = load_colour_rules(state_dir)
    else:
        _cached_rules = {kind: {} for kind in RULE_KINDS}


def _rule_theme_from_cache(cache, kind, key):
    """Defensive nested lookup used only by `resolve_effective_theme_id()`
    below — never raises regardless of `cache`'s shape (a tampered cache
    dict is exactly what T-14-05's ninth harness check injects).
    """
    if key is None:
        return None
    kind_data = cache.get(kind)
    if not isinstance(kind_data, dict):
        return None
    entry = kind_data.get(key)
    if not isinstance(entry, dict):
        return None
    return entry.get("theme_id")


def resolve_effective_theme_id(state, flight, device_cfg):
    """The D-13 resolver — the only function in this phase that decides
    what colour the panel is. Reads `_cached_rules` only; never touches
    disk. Never raises; always returns a member of `device_config.THEMES`.

    Order: exact callsign rule, then hex rule, then prefix rule, then the
    arrivals override when and only when `state` equals `ARRIVING_STATE`,
    then `device_cfg["theme"]`.

    Ordering trap this module cannot enforce on its own: this function
    must be called only where `render_state` and `current_flight` are
    already settled, never hoisted beside `poll_loop`'s top-of-cycle
    config read — plan 14-03 owns that placement.
    """
    cache = _cached_rules if isinstance(_cached_rules, dict) else {}

    raw_callsign = flight.get("callsign") if isinstance(flight, dict) else None
    raw_hex = flight.get("hex") if isinstance(flight, dict) else None

    callsign = normalise_rule_callsign(raw_callsign)
    hex_value = normalise_rule_hex(raw_hex)
    prefix = None
    if callsign is not None:
        candidate_prefix = callsign[:3]
        if _PREFIX_RE.match(candidate_prefix):
            prefix = candidate_prefix

    rule_theme = _rule_theme_from_cache(cache, RULE_KIND_CALLSIGN, callsign)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_HEX, hex_value)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_PREFIX, prefix)
    if rule_theme is not None and rule_theme in device_config.THEMES:
        return rule_theme

    if isinstance(device_cfg, dict) and state == ARRIVING_STATE:
        arriving = device_cfg.get("theme_arriving")
        if isinstance(arriving, str) and arriving in device_config.THEMES:
            return arriving

    base_theme = device_cfg.get("theme") if isinstance(device_cfg, dict) else None
    if isinstance(base_theme, str) and base_theme in device_config.THEMES:
        return base_theme
    return device_config.DEFAULT_THEME_ID
