"""Fleet poll cycle: which devices to serve, grouped by the zone they poll.

`load_fleet` lists the devices of the state root, `runnable_devices` drops
the ones this cycle must not serve, and `plan_zones` groups the rest by
exact zone so one upstream request set serves every device in a zone.
Device directories come only from `device_dirs.resolve_state_dir` on the
stored `state_path`; a row that does not resolve is skipped, never joined
onto a path. With no readable fleet.db the fleet is the live frame alone,
served from the state root.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server import (
    device_dirs,
    fleet_db,
    fleet_zones,
    hardware,
    history_db,
    panel_format,
    poll_cycle,
)
from server.plane import detect

_BATTERY_STATE_FILENAME = "battery_state.json"

Resolver = Callable[["FleetDevice"], "tuple[fleet_zones.Zone, dict[str, Any]]"]


@dataclass(frozen=True)
class FleetDevice:
    """One device the cycle may serve."""

    id: str
    state_dir: str
    is_live: bool
    hardware_type: str
    created_epoch: float | None


@dataclass
class ZoneGroup:
    """The devices that share one zone, plus the geofence that defines it."""

    zone: fleet_zones.Zone
    geofence: dict[str, Any]
    devices: list[FleetDevice] = field(default_factory=list)


@dataclass
class ZonePlan:
    """Grouping result: zones keyed by zone key, held devices, unresolved ones."""

    zones: dict[str, ZoneGroup] = field(default_factory=dict)
    held: list[FleetDevice] = field(default_factory=list)
    unzoned: list[FleetDevice] = field(default_factory=list)


def _created_epoch(raw: object) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _device_from_row(root: str, row: sqlite3.Row) -> FleetDevice:
    """A FleetDevice for the row; ValueError when its state_path is unusable."""
    state_path = str(row["state_path"])
    state_dir = device_dirs.resolve_state_dir(root, state_path)
    is_live = state_path == device_dirs.LIVE_STATE_PATH
    if not is_live and not os.path.isdir(state_dir):
        raise ValueError("device directory is missing")
    return FleetDevice(
        id=str(row["id"]),
        state_dir=state_dir,
        is_live=is_live,
        hardware_type=str(row["hardware_type"]),
        created_epoch=_created_epoch(row["created_at"]),
    )


def _fleet_rows(root: str) -> list[sqlite3.Row]:
    """Device rows of a migrated, readable fleet.db; [] on any problem."""
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return []
    try:
        if fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None:
            return []
        return fleet_db.list_devices(conn)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return []
    finally:
        conn.close()


def load_fleet(root: str, now: float | None = None) -> list[FleetDevice]:
    """The devices stored in fleet.db, live frame first.

    Falls back to the live frame alone (served from `root`) when fleet.db is
    absent, unreadable or not migrated, or holds no live row. A bad row is
    logged and skipped without affecting the others.
    """
    live: FleetDevice | None = None
    others: list[FleetDevice] = []
    for row in _fleet_rows(root):
        try:
            device = _device_from_row(root, row)
        except (ValueError, KeyError, IndexError, TypeError):
            print("fleet: skipping a device row with an unusable state_path", file=sys.stderr)
            continue
        if device.is_live:
            live = device
        else:
            others.append(device)
    if live is None:
        live = FleetDevice("live", root, True, hardware.LEGACY_KEY, None)
    return [live] + others


def _battery_received_at(state_dir: str) -> float | None:
    try:
        with open(os.path.join(state_dir, _BATTERY_STATE_FILENAME)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    received = data.get("received_at") if isinstance(data, dict) else None
    if isinstance(received, bool) or not isinstance(received, (int, float)):
        return None
    return float(received)


def last_check_in_epoch(state_dir: str) -> float | None:
    """Epoch seconds of the newest check-in recorded for this directory, or None."""
    try:
        if os.path.exists(history_db.history_db_path(state_dir)):
            with history_db.open_db(state_dir) as conn:
                row = history_db.latest_device_health(conn)
            if row is not None:
                parsed = history_db.instant_or_none(row.get("ts"))
                if parsed is not None:
                    return float(parsed.timestamp())
    except (sqlite3.Error, OSError, ValueError, TypeError):
        pass
    return _battery_received_at(state_dir)


def _renders_here(device: FleetDevice, environ: Mapping[str, str] | None) -> bool:
    try:
        profile = hardware.get_profile(
            device.hardware_type, os.environ if environ is None else environ)
    except hardware.UnknownHardwareType:
        return False
    return (profile.width, profile.height) == (panel_format.WIDTH, panel_format.HEIGHT)


def runnable_devices(
    devices: Iterable[FleetDevice],
    now: float,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[FleetDevice], list[tuple[str, str]]]:
    """Split `devices` into those to serve and (id, reason) pairs skipped.

    The live frame is always served. Others are skipped when their hardware
    cannot be rendered by this cycle or when they have been inactive too long.
    """
    keep: list[FleetDevice] = []
    skipped: list[tuple[str, str]] = []
    for device in devices:
        if device.is_live:
            keep.append(device)
        elif not _renders_here(device, environ):
            skipped.append((device.id, "unsupported_hardware"))
        elif not fleet_zones.device_is_active(
            False, device.created_epoch, last_check_in_epoch(device.state_dir), now
        ):
            skipped.append((device.id, "inactive"))
        else:
            keep.append(device)
    return keep, skipped


def geofence_resolver(geofence_path: str | None) -> Resolver:
    """Resolver giving every device the zone of one shared geofence file."""
    cache: dict[str, Any] = {}

    def resolve(device: FleetDevice) -> tuple[fleet_zones.Zone, dict[str, Any]]:
        if "zone" not in cache:
            data = detect.load_geofence(geofence_path)
            cache["zone"] = (fleet_zones.zone_from_geofence(data), data)
        zone, data = cache["zone"]
        return zone, data

    return resolve


def plan_zones(
    devices: Iterable[FleetDevice],
    resolver: Resolver,
    hold_of: Callable[[str], str | None] | None = None,
) -> ZonePlan:
    """Group non-held devices by exact zone key.

    A held device (battery critical, display off, quiet hours) joins no zone
    so a zone made only of held devices costs no request. A device whose
    zone cannot be resolved lands in `unzoned`.
    """
    peek = hold_of if hold_of is not None else poll_cycle.peek_hold
    plan = ZonePlan()
    for device in devices:
        if peek(device.state_dir) is not None:
            plan.held.append(device)
            continue
        try:
            zone, geofence = resolver(device)
        except (OSError, ValueError, KeyError, TypeError):
            plan.unzoned.append(device)
            continue
        group = plan.zones.get(zone.key)
        if group is None:
            group = plan.zones[zone.key] = ZoneGroup(zone, geofence)
        group.devices.append(device)
    return plan
