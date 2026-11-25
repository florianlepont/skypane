#!/usr/bin/env python3
"""Merge the per-frame airline registries into the fleet registry.

The three airline registries (`manual_resolutions.json`,
`airline_name_overrides.json`, `airline_default_types.json`) used to live in
each frame's state directory. They now live once, at the fleet root (the
live frame's directory). This module folds every other frame's files into
the root files. It is run by `server.fleet_migrate` at deploy time and never
at service start; reads elsewhere stay side-effect free.

Invariants:
- Per-frame files are read, never written, renamed or deleted: a rollback
  to the release that still reads them loses nothing.
- Only plain regular files are read: a symlinked registry file, a symlinked
  or oddly named `devices/<id>` directory and a file over `MAX_SOURCE_BYTES`
  are skipped and reported.
- Every entry is rebuilt through the registries' own validators
  (`manual_resolutions.load_registry_file`, `airline_default_types.
  load_default_types_file`), so a hand-edited file cannot inject a path-like
  name or a bad key.
- One total order picks the winner for a prefix, identical on every run
  whatever the listing order: the newest `created_at` (an unparsable stamp
  is the oldest), then the root entry, then the lowest frame id. Default
  types carry no stamp: the root entry, then the lowest frame id. A loser is
  reported with both values and recorded in the marker.
- A marker in the root records the SHA-256 of every source already merged:
  an unchanged source is not merged again (so a name deleted since is not
  brought back) and a changed one is merged once more.
- The marker is written last; a write failure raises `OSError`.
- Output names counts, prefixes, public airline names and frame ids only.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server import atomic_io, device_dirs
from server.plane import airline_default_types, illustrations, manual_resolutions, name_overrides

MARKER_FILENAME = "airline_registry_migration.json"
LIVE_LABEL = "live"
MAX_SOURCE_BYTES = 1024 * 1024
MAX_RECORDED_LOSERS = 50

KIND_MANUAL = "manual_resolutions"
KIND_OVERRIDES = "name_overrides"
KIND_TYPES = "default_types"
_FILENAMES = {
    KIND_MANUAL: manual_resolutions.MANUAL_RESOLUTIONS_FILENAME,
    KIND_OVERRIDES: name_overrides.NAME_OVERRIDES_FILENAME,
    KIND_TYPES: airline_default_types.DEFAULT_TYPES_FILENAME,
}
_CAPS = {
    KIND_MANUAL: manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES,
    KIND_OVERRIDES: manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES,
    KIND_TYPES: airline_default_types.MAX_ENTRIES,
}
_KINDS = (KIND_MANUAL, KIND_OVERRIDES, KIND_TYPES)

Registry = dict[str, Any]


@dataclass
class Source:
    """One per-frame registry file."""

    kind: str
    frame: str
    path: str
    rel: str
    sha: str = ""
    entries: Registry = field(default_factory=dict)


@dataclass
class MergePlan:
    """What a merge would write, computed without writing anything."""

    root: str
    merged: dict[str, Registry] = field(default_factory=dict)
    current: dict[str, Registry] = field(default_factory=dict)
    sources_seen: int = 0
    sources_pending: int = 0
    marker: dict[str, Any] = field(default_factory=dict)
    marker_changed: bool = False
    details: list[str] = field(default_factory=list)
    counts: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def changed_kinds(self) -> list[str]:
        return [k for k in _KINDS if self.merged.get(k) != self.current.get(k)]

    @property
    def needs_write(self) -> bool:
        return bool(self.changed_kinds) or self.marker_changed


def frame_state_dirs(root: str) -> list[tuple[str, str]]:
    """`(frame label, directory)`: the root (the live frame) first, then every
    valid `devices/<id>` directory in sorted id order. A directory whose name
    is not a device id, a symlink, or one resolving outside `devices/` is
    skipped through the same rules as `device_dirs.resolve_state_dir`."""
    frames = [(LIVE_LABEL, root)]
    devices = os.path.join(root, device_dirs.DEVICES_DIRNAME)
    try:
        names = sorted(os.listdir(devices))
    except OSError:
        return frames
    real_devices = device_dirs.real_devices_dir(root)
    for name in names:
        if not device_dirs.is_valid_device_id(name):
            continue
        try:
            directory = device_dirs.resolve_state_dir(
                root, device_dirs.state_path_for(name), real_devices)
        except ValueError:
            continue
        if os.path.isdir(directory):
            frames.append((name, directory))
    return frames


def _read_marker(root: str) -> dict[str, Any]:
    try:
        with open(os.path.join(root, MARKER_FILENAME), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _merged_hashes(marker: dict[str, Any]) -> dict[str, str]:
    raw = marker.get("merged")
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}


def _read_source_bytes(path: str) -> tuple[bytes | None, str]:
    """The file bytes, or `(None, reason)` for anything that is not a plain,
    small, readable regular file. Never follows a symlink."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None, ""
    except OSError:
        return None, "unreadable"
    if stat.S_ISLNK(info.st_mode):
        return None, "symlink"
    if not stat.S_ISREG(info.st_mode):
        return None, "not a regular file"
    if info.st_size > MAX_SOURCE_BYTES:
        return None, "over %d bytes" % MAX_SOURCE_BYTES
    try:
        with open(path, "rb") as fh:
            return fh.read(MAX_SOURCE_BYTES + 1), ""
    except OSError:
        return None, "unreadable"


def _collect_sources(root: str, merged: dict[str, str], plan: MergePlan) -> list[Source]:
    """Every per-frame file not yet merged at its current hash, each entry
    set rebuilt through the validators. The root's own files are not sources."""
    pending: list[Source] = []
    for frame, directory in frame_state_dirs(root)[1:]:
        for kind in _KINDS:
            path = os.path.join(directory, _FILENAMES[kind])
            rel = "%s/%s/%s" % (device_dirs.DEVICES_DIRNAME, frame, _FILENAMES[kind])
            raw, reason = _read_source_bytes(path)
            if raw is None:
                if reason:
                    plan.details.append("skipped %s of frame %s: %s" % (_FILENAMES[kind], frame, reason))
                continue
            plan.sources_seen += 1
            sha = hashlib.sha256(raw).hexdigest()
            if merged.get(rel) == sha:
                continue
            try:
                json.loads(raw.decode("utf-8"))
            except ValueError:
                plan.details.append("skipped %s of frame %s: not valid JSON" % (_FILENAMES[kind], frame))
                continue
            source = Source(kind, frame, path, rel, sha)
            source.entries = (
                airline_default_types.load_default_types_file(path) if kind == KIND_TYPES
                else manual_resolutions.load_registry_file(path))
            pending.append(source)
    return pending


def _stamp_value(entry: Any) -> float:
    """The `created_at` of an entry as an epoch; an unparsable stamp ranks oldest."""
    raw = entry.get("created_at") if isinstance(entry, dict) else None
    try:
        parsed = datetime.fromisoformat(raw) if isinstance(raw, str) else None
    except ValueError:
        parsed = None
    if parsed is None:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _value_of(kind: str, entry: Any) -> str:
    return entry if kind == KIND_TYPES else entry["airline_name"]


def _rank(kind: str, frame: str, entry: Any) -> tuple[float, int, str]:
    """Sort key: the first candidate in ascending order wins."""
    stamp = 0.0 if kind == KIND_TYPES else -_stamp_value(entry)
    return (stamp, 0 if frame == LIVE_LABEL else 1, frame)


def _describe_side(kind: str, frame: str, entry: Any) -> str:
    if kind == KIND_TYPES:
        return "%r [frame %s]" % (entry, frame)
    return "%r [frame %s, %s]" % (entry["airline_name"], frame, entry["created_at"])


def _winners(kind: str, root_entries: Registry, sources: list[Source], plan: MergePlan,
             marker_losers: list[dict[str, str]]) -> dict[str, tuple[str, Any]]:
    """`{key: (frame, entry)}` for every key whose winner is not the root's own
    entry, conflicts logged. Candidates are the root entry and every pending
    source's entry for the key."""
    candidates: dict[str, list[tuple[str, Any]]] = {}
    for key, entry in root_entries.items():
        candidates.setdefault(key, []).append((LIVE_LABEL, entry))
    for source in sources:
        if source.kind != kind:
            continue
        for key, entry in source.entries.items():
            candidates.setdefault(key, []).append((source.frame, entry))
    won: dict[str, tuple[str, Any]] = {}
    for key in sorted(candidates):
        ranked = sorted(candidates[key], key=lambda c: _rank(kind, c[0], c[1]))
        winner = ranked[0]
        same_as_root = key in root_entries and (
            _value_of(kind, root_entries[key]) == _value_of(kind, winner[1]))
        if winner[0] != LIVE_LABEL and not same_as_root:
            won[key] = winner
        for loser in ranked[1:]:
            if _value_of(kind, loser[1]) == _value_of(kind, winner[1]):
                continue
            plan.details.append("conflict %s %s: keep %s over %s" % (
                kind, key, _describe_side(kind, *winner), _describe_side(kind, *loser)))
            marker_losers.append({
                "registry": kind, "key": key,
                "kept": _value_of(kind, winner[1]), "kept_frame": winner[0],
                "lost": _value_of(kind, loser[1]), "lost_frame": loser[0]})
    return won


def _override_group(prefix: str) -> str:
    from server.plane import enrich  # lazy: enrich must never import this module
    return enrich.static_airline_name_for_prefix(prefix) or ("prefix " + prefix)


def _builtin_keys() -> dict[str, str]:
    return {k: name for name, _s in illustrations.target_variants_by_airline()
            if (k := illustrations.normalise_airline_key(name))}


def _admit_overrides(root_entries: Registry, won: dict[str, tuple[str, Any]],
                     plan: MergePlan) -> dict[str, tuple[str, Any]]:
    """Drop merged overrides that would break the overrides' own rule: a name
    may not take the artwork key of another built-in airline or of another
    airline's override (`name_overrides._name_is_taken`). Newest first, so the
    older one loses; entries already in the root are never removed."""
    from server.plane import enrich  # lazy: enrich must never import this module
    builtin = _builtin_keys()
    claimed: dict[str, str] = {}
    for prefix, entry in root_entries.items():
        key = illustrations.normalise_airline_key(entry["airline_name"])
        if key:
            claimed.setdefault(key, _override_group(prefix))
    kept: dict[str, tuple[str, Any]] = {}
    order = sorted(won, key=lambda p: (-_stamp_value(won[p][1]), p))
    for prefix in order:
        frame, entry = won[prefix]
        key = illustrations.normalise_airline_key(entry["airline_name"])
        group = _override_group(prefix)
        own = enrich.static_airline_name_for_prefix(prefix)
        reason = ""
        if key in builtin and builtin[key] != own:
            reason = "the name of the built-in airline %s" % builtin[key]
        elif key in claimed and claimed[key] != group:
            reason = "the name of another airline's override"
        if reason:
            plan.details.append("not merged %s %s from frame %s: %r is %s" % (
                KIND_OVERRIDES, prefix, frame, entry["airline_name"], reason))
            continue
        if key:
            claimed.setdefault(key, group)
        kept[prefix] = (frame, entry)
    return kept


def _fold_kind(kind: str, root_entries: Registry, won: dict[str, tuple[str, Any]],
               plan: MergePlan) -> Registry:
    """The root entries with the winners applied, capped; entries that would
    exceed the cap are not merged and counted."""
    result: Registry = dict(root_entries)
    cap = _CAPS[kind]
    new_keys = sorted((k for k in won if k not in result),
                      key=lambda k: (_stamp_value(won[k][1]), k)
                      if kind != KIND_TYPES else (0.0, k))
    replaced = 0
    for key, (_frame, entry) in sorted(won.items()):
        if key in result:
            result[key] = entry
            replaced += 1
    added = 0
    for key in new_keys:
        if len(result) >= cap:
            break
        result[key] = won[key][1]
        added += 1
    skipped = len(new_keys) - added
    if skipped:
        plan.details.append("not merged %s: %d entr%s beyond the %d-entry cap, nothing deleted" % (
            kind, skipped, "y" if skipped == 1 else "ies", cap))
    plan.counts[kind] = (added, replaced)
    return dict(sorted(result.items()))


def plan_merge(root: str) -> MergePlan:
    """Read the root files, the marker and every per-frame file and compute
    the merged registries. Writes nothing."""
    plan = MergePlan(root)
    marker = _read_marker(root)
    merged_hashes = _merged_hashes(marker)
    sources = _collect_sources(root, merged_hashes, plan)
    plan.sources_pending = len(sources)
    plan.current = {
        KIND_MANUAL: manual_resolutions.load_registry_file(
            os.path.join(root, _FILENAMES[KIND_MANUAL])),
        KIND_OVERRIDES: manual_resolutions.load_registry_file(
            os.path.join(root, _FILENAMES[KIND_OVERRIDES])),
        KIND_TYPES: airline_default_types.load_default_types_file(
            os.path.join(root, _FILENAMES[KIND_TYPES])),
    }
    losers: list[dict[str, str]] = []
    for kind in _KINDS:
        won = _winners(kind, plan.current[kind], sources, plan, losers)
        if kind == KIND_OVERRIDES:
            won = _admit_overrides(plan.current[kind], won, plan)
        plan.merged[kind] = _fold_kind(kind, plan.current[kind], won, plan)
    if sources:
        new_hashes = dict(merged_hashes)
        for source in sources:
            new_hashes[source.rel] = source.sha
        previous = marker.get("losers")
        recorded = (previous if isinstance(previous, list) else []) + losers
        plan.marker = {
            "merged": dict(sorted(new_hashes.items())),
            "losers": recorded[-MAX_RECORDED_LOSERS:],
        }
        plan.marker_changed = True
    return plan


def report_lines(plan: MergePlan, dry_run: bool) -> list[str]:
    """Human-readable lines for a plan; empty on an install with no
    per-frame registry file at all."""
    if not plan.sources_seen and not plan.details:
        return []
    if not plan.sources_pending:
        return ["airline names: nothing to do"] + ["airline names: " + d for d in plan.details]
    verb = "would merge" if dry_run else "merged"
    lines = ["airline names: %s %d per-frame file(s) into the fleet registry" % (verb, plan.sources_pending)]
    for kind in _KINDS:
        added, replaced = plan.counts.get(kind, (0, 0))
        lines.append("airline names: %s %s: %d added, %d replaced" % (verb, kind, added, replaced))
    lines.extend("airline names: " + d for d in plan.details)
    return lines


def _write_registry(path: str, data: Registry) -> None:
    atomic_io.atomic_write(path, json.dumps(data, indent=1))


def apply_merge(root: str, plan: MergePlan, now: str | None = None) -> list[str]:
    """Write the changed root files, then the marker; returns the report
    lines. Never opens a per-frame file for writing. Raises `OSError` when a
    write fails."""
    if plan.needs_write:
        os.makedirs(root, exist_ok=True)
        for kind in plan.changed_kinds:
            _write_registry(os.path.join(root, _FILENAMES[kind]), plan.merged[kind])
        if plan.marker_changed:
            stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
            _write_registry(
                os.path.join(root, MARKER_FILENAME), dict(plan.marker, merged_at=stamp))
    return report_lines(plan, dry_run=False)
