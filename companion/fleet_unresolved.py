"""The unidentified callsign prefixes of the whole fleet, merged.

Each frame's poll loop keeps its own `unresolved_prefixes` registry in its
own `poll_state.json`. The administrator's Airlines editor names a prefix for
every frame, so it reads the registries of every frame in the request's scope
(an administrator's scope is the whole fleet) and merges them: counts add up,
the first sighting is the earliest, the last sighting the latest, and the
example callsign is the one of the frame that saw the prefix last. Nothing is
written. A frame whose state cannot be read contributes nothing.

Only the request scope decides which frames are read, so a plain user's scope
(their own frames) can never pull in another user's prefixes.
"""
import os

from companion import device_scope
from server import history_db, state_store


def scope_dirs(state_dir):
    """The state directories to merge: every frame in this request's scope,
    then `state_dir` itself, each once, in scope order."""
    dirs = []
    seen = set()
    candidates = [device.state_dir for device in device_scope.current_devices()]
    candidates.append(state_dir)
    for directory in candidates:
        if not directory:
            continue
        real = os.path.realpath(directory)
        if real not in seen:
            seen.add(real)
            dirs.append(directory)
    return dirs


def _valid_entry(entry):
    if not isinstance(entry, dict):
        return None
    count = entry.get("count")
    if not isinstance(count, int) or isinstance(count, bool):
        return None
    return count


def _instant(value):
    return history_db.instant_or_none(value) if isinstance(value, str) and value else None


def _earlier(current, candidate):
    """The earlier of two stamps: an unreadable one never beats a readable one."""
    if not current:
        return candidate
    if not candidate:
        return current
    first, second = _instant(current), _instant(candidate)
    if first is None or second is None:
        return current if second is None else candidate
    return candidate if second < first else current


def _later(current, candidate):
    if not current:
        return candidate
    if not candidate:
        return current
    first, second = _instant(current), _instant(candidate)
    if first is None or second is None:
        return current if second is None else candidate
    return candidate if second > first else current


def merged_registry(state_dirs):
    """`{prefix: {count, first_seen, last_seen, example_callsign}}` over the
    registries of `state_dirs` (in that order; an equal last sighting keeps the
    example of the earlier directory)."""
    merged = {}
    for directory in state_dirs:
        registry = state_store.load_poll_state(directory).get("unresolved_prefixes")
        if not isinstance(registry, dict):
            continue
        for prefix, entry in registry.items():
            count = _valid_entry(entry)
            if count is None or not isinstance(prefix, str):
                continue
            first = entry.get("first_seen") or ""
            last = entry.get("last_seen") or ""
            found = merged.get(prefix)
            if found is None:
                merged[prefix] = {
                    "count": count, "first_seen": first, "last_seen": last,
                    "example_callsign": entry.get("example_callsign") or ""}
                continue
            newer = _later(found["last_seen"], last)
            if newer == last and newer != found["last_seen"]:
                found["example_callsign"] = entry.get("example_callsign") or ""
            found["count"] += count
            found["first_seen"] = _earlier(found["first_seen"], first)
            found["last_seen"] = newer
    return merged
