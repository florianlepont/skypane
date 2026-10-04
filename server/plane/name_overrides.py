#!/usr/bin/env python3
"""The owner's airline-name overrides: `{3-letter ICAO callsign prefix:
owner-chosen display name}`, applied to new flights as they are enriched and to stored flights as they are read.

`manual_resolutions` names prefixes nothing else can name, and loses to
the built-in table and adsbdb for any prefix they know. This registry is
the opposite layer: a name stored here wins over both, so the owner can
rename an airline SkyPane already recognises. Precedence for a callsign's
airline name, highest first:

  1. this registry (`apply_to_route()` in `enrich.resolve_route()`)
  2. adsbdb's route, after the fixed corrections table
  3. the built-in ICAO prefix table
  4. `manual_resolutions` (only for prefixes 2 and 3 do not know)

Stored history rows are never rewritten: `history_db.recent_runway_events()`
takes `airline_names` (see `names_by_prefix()`) and swaps the name in on
read, by callsign prefix. The original name stays in the row, so removing
an override restores it with no migration and nothing to keep atomic with
the poll loop's writes.

Same file contract as `manual_resolutions` (never-raising load through
its shared `load_registry_file()`, so the same name allowlist guards both
files; validate-before-write through `check_name()`; atomic write; hard
cap, no eviction). Lives at `{state_dir}/airline_name_overrides.json`.
Imports `manual_resolutions`, never `enrich` (which imports this).
"""
import json
import os
import threading
from datetime import datetime, timezone

from server import atomic_io
from server.plane import manual_resolutions

NAME_OVERRIDES_FILENAME = "airline_name_overrides.json"

# Result constants are `manual_resolutions`' own ADD_* values, so a caller
# maps one vocabulary onto its flash keys.
SET_OK = manual_resolutions.ADD_OK

# One process-wide lock around the load-modify-write cycle, for the same
# reason as `manual_resolutions._WRITE_LOCK`.
_WRITE_LOCK = threading.Lock()


def name_overrides_path(state_dir):
    """Join `state_dir` and `NAME_OVERRIDES_FILENAME`."""
    return os.path.join(state_dir, NAME_OVERRIDES_FILENAME)


def load_name_overrides(state_dir):
    """The validated registry, `{prefix: {"airline_name", "created_at"}}`;
    `{}` for a missing, unreadable or invalid file. Never raises."""
    if not state_dir:
        return {}
    return manual_resolutions.load_registry_file(name_overrides_path(state_dir))


def name_for_prefix(prefix, overrides):
    """The override name for a 3-letter `prefix` in an already-loaded
    registry, or `None`. Reads only `overrides`, never the disk."""
    return manual_resolutions.airline_name_for_prefix(prefix, overrides)


def names_by_prefix(overrides):
    """`{prefix: name}` from an already-loaded registry, for readers that
    show stored flights under the owner's names (`history_db`'s
    `airline_names`). `{}` for anything that is not a registry."""
    if not isinstance(overrides, dict):
        return {}
    return {p: e["airline_name"] for p, e in overrides.items()
            if isinstance(e, dict) and isinstance(e.get("airline_name"), str)}


def _write(state_dir, registry):
    os.makedirs(state_dir, exist_ok=True)
    atomic_io.atomic_write(name_overrides_path(state_dir), json.dumps(registry, indent=1))


def set_names(state_dir, prefixes, airline_name, now=None):
    """Store `airline_name` as the override for every prefix in
    `prefixes` in one write. Returns a `manual_resolutions.ADD_*` value;
    never raises. Nothing is written unless every check passes: at least
    one well-formed prefix, a usable name (`check_name()`), and room under
    the registry cap for the prefixes that are new.
    """
    clean = sorted({p for p in (manual_resolutions.normalise_prefix(x) for x in prefixes or ()) if p})
    if not clean:
        return manual_resolutions.ADD_REJECTED_PREFIX
    name, rejection = manual_resolutions.check_name(airline_name)
    if rejection is not None:
        return rejection
    with _WRITE_LOCK:
        registry = load_name_overrides(state_dir)
        added = [p for p in clean if p not in registry]
        if len(registry) + len(added) > manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES:
            return manual_resolutions.ADD_REJECTED_FULL
        stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        for prefix in clean:
            registry[prefix] = {"airline_name": name, "created_at": stamp}
        try:
            _write(state_dir, registry)
        except Exception:
            return manual_resolutions.ADD_FAILED
    return SET_OK


def clear_names(state_dir, prefixes):
    """Remove the override of every prefix in `prefixes`. Returns `True`
    when the registry is afterwards free of them (including when none was
    set), `False` on a write failure. Idempotent, never raises."""
    clean = {p for p in (manual_resolutions.normalise_prefix(x) for x in prefixes or ()) if p}
    with _WRITE_LOCK:
        registry = load_name_overrides(state_dir)
        if not clean & set(registry):
            return True
        for prefix in clean:
            registry.pop(prefix, None)
        try:
            _write(state_dir, registry)
        except Exception:
            return False
    return True
