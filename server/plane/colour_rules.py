#!/usr/bin/env python3
"""The per-flight colour-rule registry plus the single effective-theme
resolution function every render of a displayed flight goes through.

Imports `server.device_config` plus stdlib only - must never import
`enrich`/`detect`/`illustrations`/`manual_resolutions`/`render`/
`calendar_rules`, since `poll_loop.py` already imports all of those plus
this module (the reverse direction would cycle). Its callsign/prefix
normalisers duplicate small primitives from `enrich.py`/
`manual_resolutions.py` rather than import them, for the same reason.

**Caching:** `set_colour_rules_state_dir()`'s cache is for the
once-per-cycle poll pipeline only. `companion/`'s long-running
`ThreadingHTTPServer` must call `load_colour_rules(state_dir)` fresh per
request instead.

A rule record is a dict (`{"theme_id": ..., "created_at": ...}`), not a
bare theme-id string, so a future entry can carry fields not yet defined.

Lives at `{state_dir}/colour_rules.json`, excluded from `deploy/deploy.sh`'s
rsync so it survives a redeploy.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone

from server import atomic_io, device_config

COLOUR_RULES_FILENAME = "colour_rules.json"

# Hard reject at the cap, never weakest-entry eviction: this registry is
# authenticated-human-curated one entry at a time. Summed across all
# three kinds, not per kind; must agree with companion/'s registry-full
# flash copy.
COLOUR_RULE_MAX_ENTRIES = 200

RULE_KIND_CALLSIGN = "callsign"
RULE_KIND_HEX = "hex"
RULE_KIND_PREFIX = "prefix"
# Order is load-bearing twice: most-specific-wins resolution order
# (callsign > hex > prefix), and rule_rows()'s sort order.
RULE_KINDS = (RULE_KIND_CALLSIGN, RULE_KIND_HEX, RULE_KIND_PREFIX)

# The one render state the arrivals override applies to.
ARRIVING_STATE = "arriving"

# Positive-allowlist regexes, defence against a hand-edited/corrupted
# file smuggling a crafted key into a live comparison.
_CALLSIGN_RULE_RE = re.compile(r"^[A-Z0-9]{2,8}$")  # mirrors enrich.normalise_callsign()
_HEX_RULE_RE = re.compile(r"^[0-9A-F]{6}$")  # live ADS-B hex arrives lowercase
_PREFIX_RE = re.compile(r"^[A-Z]{3}$")  # mirrors manual_resolutions.normalise_prefix()

# Result constants for add_rule(). Not flash keys - companion/app.py maps
# them onto its own vocabulary. ADD_OK_NEW/ADD_OK_REPLACED split lets the
# companion say "replaced" vs "added" without a second, TOCTOU-prone read.
ADD_OK_NEW = "ok_new"
ADD_OK_REPLACED = "ok_replaced"
ADD_REJECTED_KIND = "rejected_kind"
ADD_REJECTED_KEY = "rejected_key"
ADD_REJECTED_THEME = "rejected_theme"
ADD_REJECTED_FULL = "rejected_full"
ADD_FAILED = "failed"

# Serialises the entire load-check-mutate-write sequence per writer (not
# just os.replace()), so two concurrent companion writers can never each
# load before either has written and lose an update.
_WRITE_LOCK = threading.Lock()

# Process-scoped cache; unset means the empty registry shape.
_cached_rules = {kind: {} for kind in RULE_KINDS}


def colour_rules_path(state_dir):
    """Join `state_dir` and `COLOUR_RULES_FILENAME`."""
    return os.path.join(state_dir, COLOUR_RULES_FILENAME)


def normalise_rule_kind(raw):
    """Member of `RULE_KINDS` matching `raw` exactly, else `None`. Never raises."""
    if isinstance(raw, str) and raw in RULE_KINDS:
        return raw
    return None


def normalise_rule_callsign(raw):
    """Stripped/upper-cased `raw` when it matches `_CALLSIGN_RULE_RE`, else `None`. Never raises."""
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not candidate or not _CALLSIGN_RULE_RE.match(candidate):
        return None
    return candidate


def normalise_rule_hex(raw):
    """Stripped/upper-cased `raw` when it matches `_HEX_RULE_RE`, else `None`. Never raises."""
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not _HEX_RULE_RE.match(candidate):
        return None
    return candidate


def normalise_rule_prefix(raw):
    """Stripped/upper-cased `raw` when it matches `_PREFIX_RE`, else `None`. Never raises."""
    if not isinstance(raw, str) or not raw:
        return None
    candidate = raw.strip().upper()
    if not _PREFIX_RE.match(candidate):
        return None
    return candidate


def normalise_rule_value(kind, raw):
    """Dispatch to the per-kind normaliser for a normalised `kind`; an
    unknown kind returns `None`. The single definition of "a valid rule
    key" every caller shares. Never raises.
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
    """`raw` unchanged when it is a member of `device_config.THEMES`,
    else `None` - never degrades to the default theme; an unrecognised
    id makes the rule invalid, dropped rather than retargeted.
    """
    if isinstance(raw, str) and raw in device_config.THEMES:
        return raw
    return None


def load_colour_rules(state_dir):
    """Read `{state_dir}/colour_rules.json`; never raises. A missing/
    unreadable/invalid file yields the empty registry shape. Each
    surviving entry is rebuilt from scratch, re-applying `add_rule()`'s
    allowlist and THEMES check - defence in depth against a hand-edited
    file. Stops at `COLOUR_RULE_MAX_ENTRIES` entries and prints (never
    raises) a one-line warning naming the drop count.
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
    Returns an `ADD_*` module constant; never raises. Validates kind,
    value and theme_id before touching the filesystem, then holds
    `_WRITE_LOCK` across the whole load-check-mutate-write sequence to
    avoid a TOCTOU race on the added-vs-replaced decision. Rejects when
    full unless replacing an existing key. Writes via
    `atomic_io.atomic_write` (unique per-call temp name, no leftover on
    failure); any write exception returns `ADD_FAILED` rather than raising.
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

        try:
            os.makedirs(state_dir, exist_ok=True)
            atomic_io.atomic_write(colour_rules_path(state_dir), json.dumps(registry, indent=1))
        except Exception:
            return ADD_FAILED

    return ADD_OK_REPLACED if replacing else ADD_OK_NEW


def delete_rule(state_dir, kind, value):
    """Remove `(kind, value)` from the registry at `state_dir`. `True`
    when removed, `False` otherwise (unknown kind, malformed value,
    absent key, write failure). Idempotent, never raises; same
    `_WRITE_LOCK`/`atomic_io.atomic_write` discipline as `add_rule()`.
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

        try:
            os.makedirs(state_dir, exist_ok=True)
            atomic_io.atomic_write(colour_rules_path(state_dir), json.dumps(registry, indent=1))
        except Exception:
            return False

    return True


def rule_rows(registry):
    """`(kind, value, theme_id, created_at)` tuples from an already-loaded
    registry, ordered by kind then value, skipping malformed entries.
    Never raises. What the Settings rules list renders from.
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
    reads through. Call once per poll cycle so a companion-side save
    landing mid-cycle never splits one rendered panel across two
    configurations. Falsy `state_dir` caches the empty registry shape.
    """
    global _cached_rules
    if state_dir:
        _cached_rules = load_colour_rules(state_dir)
    else:
        _cached_rules = {kind: {} for kind in RULE_KINDS}


def _rule_theme_from_cache(cache, kind, key):
    """Defensive nested lookup used only by `resolve_effective_theme_id()`
    below — never raises regardless of `cache`'s shape, including a
    tampered or malformed cache dict.
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


def resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None):
    """The single resolver that decides what colour the panel is. Reads
    `_cached_rules` only, never touches disk. Never raises; always
    returns a member of `device_config.THEMES`.

    Order: `calendar_theme_id`, then exact callsign rule, hex rule,
    prefix rule, then the arrivals override (only when `state ==
    ARRIVING_STATE`), then `device_cfg["theme"]`. A calendar match
    intentionally beats even an exact-callsign rule: a calendar entry
    designates one specific flight, and that is the point of the feature.

    `calendar_theme_id` is computed by the caller (`poll_loop.py`, via
    `calendar_rules.match_calendar_theme()`), preserving this module's
    leaf-import contract.
    """
    if isinstance(calendar_theme_id, str) and calendar_theme_id in device_config.THEMES:
        return calendar_theme_id

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
