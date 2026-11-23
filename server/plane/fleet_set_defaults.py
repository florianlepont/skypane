#!/usr/bin/env python3
"""One-time choice of a default aircraft type for every airline that has
pictures but none.

An airline has no picture of its own: its pictures are those of its aircraft
types (`illustrations.type_pictures`; the legacy `{airline}.png` is the picture
of its airframe type) and one type is the airline's default, the safety net
shown when a flight has a type with no picture. This module gives each airline
that has pictures and no stored default the default a person would have
chosen, by fixed rules, at deploy time (`server.fleet_migrate`), after the
per-frame merges and after the clearing of defaults without a picture
(`fleet_default_types`). Nothing is left to an Editor flag.

Rules, in order, for an airline with pictures and no stored default:
  a. it has a legacy `{airline}.png` whose airframe is known -> that type;
  b. otherwise it has typed pictures: exactly one -> that type; several ->
     the type with the most sightings across the fleet, a tie or no sighting
     -> the first type code in alphabetical order;
  c. a legacy picture whose airframe is unknown -> the most-seen typed
     picture of the airline; with no sighting of any typed picture the airline
     is reported `unresolved` and nothing is invented;
  d. no picture at all -> nothing.

Invariants:
- Default types are fleet-wide: `<root>/airline_default_types.json` is the
  only registry written, through `airline_default_types.set_default_type`
  (the livery rule holds). Per-frame files are frozen copies, never touched.
- Every default set is first appended to `<root>/airline_default_types_set.json`
  (airline key, type, rule, time); the marker
  `<root>/airline_default_types_set_migration.json` is written last. Only a
  run that sets or reports something writes anything; once the marker exists a
  run does nothing, so a default the owner clears later is never set again.
- Sightings are counted from the `runway_events` of the root and of every
  frame directory, read-only, a sighting of an airline's built-in original
  counting for its renamed airline. A history that cannot be read counts as no
  sighting.
- A dry run writes nothing and judges the fleet root as it is now (pictures or
  defaults still waiting in the per-frame merge are not counted).
- Output names airline keys, type codes, rules and counts only.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server import atomic_io, history_db
from server.plane import airline_default_types, fleet_registries, illustrations

MARKER_FILENAME = "airline_default_types_set_migration.json"
ARCHIVE_FILENAME = "airline_default_types_set.json"
_REPORT = "airline default types: "
RULE_LEGACY = "a"
RULE_TYPED = "b"
RULE_UNKNOWN_LEGACY = "c"


@dataclass
class SetPlan:
    """What a run would do: `(airline key, type code, rule)` to set and
    `(airline key, reason)` the rules could not settle."""

    done: bool = False
    to_set: list[tuple[str, str, str]] = field(default_factory=list)
    unresolved: list[tuple[str, str]] = field(default_factory=list)

    @property
    def needs_write(self) -> bool:
        return not self.done and bool(self.to_set or self.unresolved)


def _read_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _candidate_keys(root: str) -> list[str]:
    """Every airline key that can have a picture: the built-in airlines and
    the airline of each fleet-wide upload, sorted."""
    keys = {illustrations.normalise_airline_key(name) for name in illustrations.target_airline_names()}
    override_dir = illustrations.override_dir_for_state_dir(root)
    try:
        names = os.listdir(override_dir) if override_dir else []
    except OSError:
        names = []
    for name in names:
        if name.endswith(".png") and not name.startswith("."):
            keys.add(illustrations.airline_key_of_artwork(name[:-4]))
    return sorted(
        key for key in keys
        if key and not key.startswith("generic-") and key != "generic")


def _frame_counts(directory: str) -> dict[tuple[str, str], int]:
    """`{(airline key, aircraft type): sightings}` of one frame's history,
    read-only; empty when the file is missing or unreadable."""
    path = history_db.history_db_path(directory)
    if not os.path.isfile(path):
        return {}
    counts: dict[tuple[str, str], int] = {}
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=5.0)
        try:
            rows = conn.execute(
                "SELECT airline, aircraft_type, COUNT(*) FROM runway_events "
                "GROUP BY airline, aircraft_type").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    for airline, code, count in rows:
        key = illustrations.normalise_airline_key(airline)
        designator = code.strip().upper() if isinstance(code, str) else ""
        if key and designator:
            counts[(key, designator)] = counts.get((key, designator), 0) + int(count)
    return counts


def fleet_sightings(root: str) -> dict[tuple[str, str], int]:
    """The sightings of every frame added up, per airline key and type."""
    total: dict[tuple[str, str], int] = {}
    for _label, directory in fleet_registries.frame_state_dirs(root):
        for pair, count in _frame_counts(directory).items():
            total[pair] = total.get(pair, 0) + count
    return total


def _seen_by_picture(key: str, pictures: dict, sightings: dict, root: str) -> dict[str, int]:
    """Sightings credited to each picture's type code: a flight of a type with
    no picture of its own counts for the picture it would be drawn with."""
    original = illustrations.builtin_name_for_key(key, root)
    owners = {key, illustrations.normalise_airline_key(original) or key}
    seen = {code: 0 for code in pictures}
    for (airline, code), count in sightings.items():
        if airline not in owners:
            continue
        slots = illustrations.type_artwork_keys(key, code)
        target = code if code in pictures else next(
            (c for c in sorted(pictures) if pictures[c].key in slots), None)
        if target is not None:
            seen[target] += count
    return seen


def _decide(key: str, root: str, sightings: dict) -> tuple[str, str, str] | tuple[str, str] | None:
    """`(key, type, rule)` to set, `(key, reason)` unresolved, or `None`."""
    pictures = illustrations.type_pictures(key, root)
    legacy = illustrations.resolved_illustration_path(key, root) is not None
    if not pictures and not legacy:
        return None
    legacy_type = illustrations.legacy_picture_type(key, root)
    if legacy_type:
        return (key, legacy_type, RULE_LEGACY)
    seen = _seen_by_picture(key, pictures, sightings, root)
    ranked = sorted(pictures, key=lambda code: (-seen[code], code))
    if legacy:
        if ranked and seen[ranked[0]] > 0:
            return (key, ranked[0], RULE_UNKNOWN_LEGACY)
        return (key, "legacy picture of an unknown airframe and no seen typed picture")
    return (key, ranked[0], RULE_TYPED)


def plan_set(root: str, cleared: set[str] | frozenset[str] = frozenset()) -> SetPlan:
    """The defaults to set for the fleet root, sorted by airline key; already
    done when the marker exists. `cleared` names stored defaults that are about
    to be cleared (a dry run), judged as already gone."""
    if isinstance(_read_json(os.path.join(root, MARKER_FILENAME)), dict):
        return SetPlan(done=True)
    stored = airline_default_types.load_default_types(root)
    sightings = fleet_sightings(root)
    plan = SetPlan()
    for key in _candidate_keys(root):
        if key in stored and key not in cleared:
            continue
        decision = _decide(key, root, sightings)
        if decision is None:
            continue
        if len(decision) == 3:
            plan.to_set.append(decision)
        else:
            plan.unresolved.append(decision)
    return plan


def report_lines(plan: SetPlan, dry_run: bool) -> list[str]:
    if plan.done or not (plan.to_set or plan.unresolved):
        return [_REPORT + "nothing to do"]
    verb = "would set" if dry_run else "set"
    lines = []
    if plan.to_set:
        lines.append("%s%s %d" % (_REPORT, verb, len(plan.to_set)))
        lines.extend(
            "%s%s %s: %s (rule %s)" % (_REPORT, verb, key, code, rule)
            for key, code, rule in plan.to_set)
    if plan.unresolved:
        lines.append("%sunresolved %d" % (_REPORT, len(plan.unresolved)))
        lines.extend("%sunresolved %s: %s" % (_REPORT, key, reason) for key, reason in plan.unresolved)
    return lines


def _write_json(path: str, data: Any) -> None:
    atomic_io.atomic_write(path, json.dumps(data, indent=1))


def apply_set(root: str, plan: SetPlan, now: str | None = None) -> list[str]:
    """Archive, set, then mark; returns the report lines. Raises `OSError` when
    a write fails (nothing is marked, so the next run retries). An entry the
    registry has no room for is reported unresolved instead."""
    if not plan.needs_write:
        return report_lines(plan, dry_run=False)
    stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(root, exist_ok=True)
    archive_path = os.path.join(root, ARCHIVE_FILENAME)
    archive = _read_json(archive_path)
    records = archive if isinstance(archive, list) else []
    records.extend(
        {"airline_key": key, "type": code, "rule": rule, "set_at": stamp}
        for key, code, rule in plan.to_set)
    _write_json(archive_path, records)
    done = SetPlan(unresolved=list(plan.unresolved))
    for key, code, rule in plan.to_set:
        result = airline_default_types.set_default_type(root, key, code)
        if result == airline_default_types.SET_OK:
            done.to_set.append((key, code, rule))
        elif result == airline_default_types.SET_FULL:
            done.unresolved.append((key, "the default types registry is full"))
        else:
            raise OSError("could not set the default type of %s" % key)
    _write_json(
        os.path.join(root, MARKER_FILENAME),
        {"set": len(done.to_set), "unresolved": len(done.unresolved), "set_at": stamp})
    return report_lines(done, dry_run=False)
