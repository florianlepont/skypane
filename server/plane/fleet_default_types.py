#!/usr/bin/env python3
"""One-time clean-up of the airlines' default aircraft types that have no
picture (livery).

A default type is only offered, and accepted, for a type the airline has
artwork for (`illustrations.has_type_livery`). Defaults stored before that
rule can name a type with no picture. This module clears each of them once, at
deploy time (`server.fleet_migrate`), after the per-frame registries and
artwork have been merged into the fleet root.

Invariants:
- Default types are fleet-wide: `<root>/airline_default_types.json` is the
  only file read and written. Per-frame files are frozen copies and are never
  touched.
- Every cleared entry is first appended to
  `<root>/airline_default_types_cleared.json` (airline key, type, source, time),
  so nothing is lost silently; the entry is cleared next and the marker
  `<root>/airline_default_types_migration.json` is written last.
- The marker is written only by a run that cleared something; once it exists
  a run does nothing, so a default stored later is never touched by a later
  deploy. A run that finds nothing to clear writes nothing at all. A dry run writes nothing; it judges the
  fleet root as it is now (artwork or defaults still waiting in the per-frame
  merge are not counted).
- Output names airline keys, type codes and counts only.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server import atomic_io
from server.plane import airline_default_types, illustrations

MARKER_FILENAME = "airline_default_types_migration.json"
ARCHIVE_FILENAME = "airline_default_types_cleared.json"
SOURCE_LABEL = "fleet"
_REPORT = "airline default types: "


@dataclass
class DefaultTypesPlan:
    """What a run would do: the entries to clear and whether it was done."""

    done: bool = False
    to_clear: list[tuple[str, str]] = field(default_factory=list)

    @property
    def needs_write(self) -> bool:
        return not self.done and bool(self.to_clear)


def _read_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def plan_clear(root: str) -> DefaultTypesPlan:
    """The defaults of the fleet root that have no livery, sorted by key;
    already done when the marker exists."""
    if isinstance(_read_json(os.path.join(root, MARKER_FILENAME)), dict):
        return DefaultTypesPlan(done=True)
    stored = airline_default_types.load_default_types(root)
    doomed = [
        (key, code) for key, code in sorted(stored.items())
        if not illustrations.has_type_livery(key, code, root)]
    return DefaultTypesPlan(to_clear=doomed)


def report_lines(plan: DefaultTypesPlan, dry_run: bool) -> list[str]:
    if plan.done or not plan.to_clear:
        return [_REPORT + "nothing to do"]
    verb = "would clear" if dry_run else "cleared"
    lines = ["%s%s %d" % (_REPORT, verb, len(plan.to_clear))]
    lines.extend("%s%s %s: %s" % (_REPORT, verb, key, code) for key, code in plan.to_clear)
    return lines


def _write_json(path: str, data: Any) -> None:
    atomic_io.atomic_write(path, json.dumps(data, indent=1))


def apply_clear(root: str, plan: DefaultTypesPlan, now: str | None = None) -> list[str]:
    """Archive, clear, then mark; returns the report lines. Raises `OSError`
    when a write fails (nothing is marked, so the next run retries)."""
    if not plan.needs_write:
        return report_lines(plan, dry_run=False)
    stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(root, exist_ok=True)
    archive_path = os.path.join(root, ARCHIVE_FILENAME)
    archive = _read_json(archive_path)
    records = archive if isinstance(archive, list) else []
    records.extend(
        {"airline_key": key, "type": code, "source": SOURCE_LABEL, "cleared_at": stamp}
        for key, code in plan.to_clear)
    _write_json(archive_path, records)
    for key, _code in plan.to_clear:
        if airline_default_types.set_default_type(root, key, "") != airline_default_types.SET_OK:
            raise OSError("could not clear the default type of %s" % key)
    _write_json(
        os.path.join(root, MARKER_FILENAME),
        {"cleared": len(plan.to_clear), "cleared_at": stamp})
    return report_lines(plan, dry_run=False)
