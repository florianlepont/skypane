#!/usr/bin/env python3
"""scripts/multi_site_export.py -- writes the runway_events and poll_cycles of
scratch-fleet devices in the exact line format of /api/export/flights and
/api/export/poll-cycles, so runway_compare.py and runway_external_compare.py
read them unchanged.

Read-only: each device's history.db is opened with mode=ro (a missing
database is an error, never created), the device directory comes only from
the fleet's own state path through device_dirs.resolve_state_dir, and no
network connection is opened. Files are evidence: an existing file is never
replaced.

Output: <out>/<device id>/{runway_events.jsonl, poll_cycles.jsonl, MANIFEST.json}
"""
import argparse
import dataclasses
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import export_api  # noqa: E402
from server import device_dirs, fleet_db, history_db  # noqa: E402

# (file name, route whose rows and line format the file reproduces)
FILES = (
    ("runway_events.jsonl", export_api.FLIGHTS_ROUTE),
    ("poll_cycles.jsonl", export_api.POLL_CYCLES_ROUTE),
)
_SINCE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class ExportError(Exception):
    """A device or its history cannot be exported."""


@dataclasses.dataclass(frozen=True)
class ScratchDevice:
    id: str
    name: str
    state_dir: str


def scratch_devices(root):
    """The non-live devices of the fleet at `root`, in creation order."""
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError) as exc:
        raise ExportError("cannot read fleet.db under %s" % root) from exc
    try:
        rows = fleet_db.list_devices(conn)
    finally:
        conn.close()
    devices = []
    for row in rows:
        if row["state_path"] == device_dirs.LIVE_STATE_PATH:
            continue
        try:
            state_dir = device_dirs.resolve_state_dir(root, row["state_path"])
        except ValueError:
            continue
        devices.append(ScratchDevice(str(row["id"]), str(row["name"] or ""), state_dir))
    return devices


def _select(root, device):
    devices = scratch_devices(root)
    if device == "all":
        return devices
    if not device_dirs.is_valid_device_id(device):
        raise ExportError("not a device id: %r" % device)
    for entry in devices:
        if entry.id == device:
            return [entry]
    raise ExportError("no such scratch device: %s" % device)


def _render(entry, since):
    rendered = {}
    for name, route in FILES:
        columns, reader = export_api._LINE_EXPORTS[route]
        try:
            rows = reader(entry.state_dir, since, export_api.MAX_ROWS)
        except (sqlite3.Error, history_db.TooManyRows) as exc:
            raise ExportError(
                "cannot read %s of %s: %s" % (name, entry.id, type(exc).__name__)) from exc
        rendered[name] = (route, len(rows), export_api._render_lines(rows, columns))
    return rendered


def export_devices(root, device, since, out_dir, skip_missing=False):
    """Export one device (an id) or every scratch device ("all"); returns
    {device id: manifest}. Raises FileExistsError before writing anything
    when a target file exists, and ExportError for an unknown device, a bad
    `since` or a missing history.db (with skip_missing, "all" leaves such
    devices out instead).
    """
    if not _SINCE_RE.fullmatch(since):
        raise ExportError("since must look like 2026-11-01T00:00:00Z")
    chosen = _select(root, device)
    ready = []
    for entry in chosen:
        if not os.path.exists(history_db.history_db_path(entry.state_dir)):
            if skip_missing and device == "all":
                continue
            raise ExportError("%s has no history.db yet" % entry.id)
        ready.append(entry)
    if not ready:
        raise ExportError("nothing to export")
    rendered = {entry.id: _render(entry, since) for entry in ready}
    targets = [os.path.join(out_dir, entry.id) for entry in ready]
    for target in targets:
        for name in [n for n, _ in FILES] + ["MANIFEST.json"]:
            if os.path.exists(os.path.join(target, name)):
                raise FileExistsError("%s already exists in %s" % (name, target))
    fetched_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifests = {}
    for entry, target in zip(ready, targets):
        os.makedirs(target, exist_ok=True)
        manifest = {"fetched_at": fetched_at, "since": since, "source": "scratch-root",
                    "device": entry.id, "files": {}}
        for name, (route, count, data) in rendered[entry.id].items():
            with open(os.path.join(target, name), "xb") as handle:
                handle.write(data)
            manifest["files"][name] = {
                "route": route, "rows": count, "sha256": hashlib.sha256(data).hexdigest()}
        with open(os.path.join(target, "MANIFEST.json"), "x", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
        manifests[entry.id] = manifest
    return manifests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", required=True, help="scratch state root")
    parser.add_argument("--device", default="all", help='a device id or "all"')
    parser.add_argument("--since", default="1970-01-01T00:00:00Z",
                        help="UTC time, e.g. 2026-11-20T00:00:00Z")
    parser.add_argument("--out", required=True, help="output directory")
    args = parser.parse_args(argv)
    try:
        manifests = export_devices(
            args.root, args.device, args.since, args.out, skip_missing=args.device == "all")
    except (ExportError, FileExistsError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for device_id, manifest in manifests.items():
        for name, entry in manifest["files"].items():
            print("%s/%s: %d rows sha256=%s" % (device_id, name, entry["rows"], entry["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
