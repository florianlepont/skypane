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
import time
import traceback
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
    request_budget,
    state_store,
    zone_fetch,
)
from server.plane import detect
from server.plane.shared_route_cache import SharedRouteTransport

# No new zone or device starts after this many seconds into a run. The timer
# fires every 30 s, so a longer run would delay the live frame's next cycle;
# one zone costs two spaced requests, so roughly a dozen zones fit.
FLEET_START_DEADLINE_S = 25.0

STATUS_OK = "ok"
STATUS_HELD = "held"
STATUS_BUSY = "busy"
STATUS_FAILED = "failed"
STATUS_DEFERRED = "deferred"
STATUS_SKIPPED = "skipped"

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


@dataclass
class DeviceOutcome:
    """What happened to one device in a run."""

    device_id: str
    is_live: bool
    status: str
    detail: str = ""
    trace: str = ""


@dataclass
class FleetResult:
    """Per-device outcomes plus how many zone fetches and providers were used."""

    outcomes: list[DeviceOutcome] = field(default_factory=list)
    zone_fetches: int = 0
    requests: int = 0

    def count(self, status: str) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == status)

    @property
    def live_outcome(self) -> DeviceOutcome | None:
        for outcome in self.outcomes:
            if outcome.is_live:
                return outcome
        return None


def _failed_fetch() -> zone_fetch.ZoneFetch:
    """A zone whose fetch blew up: every provider counts as failed."""
    names = tuple(detect.DEFAULT_PROVIDER_ORDER)
    return zone_fetch.ZoneFetch((), names, names)


def _last_run(device: FleetDevice) -> float:
    try:
        path = os.path.join(device.state_dir, state_store.POLL_STATE_FILENAME)
        return os.stat(path).st_mtime
    except OSError:
        return 0.0


class _FleetRun:
    """One run's collaborators and the steps that serve zones and devices."""

    def __init__(self, state_root, geofence_path, caddy_log, deadline_s, clock,
                 monotonic, ledger, runner, fetcher, route_transport):
        self.root = state_root
        self.geofence_path = geofence_path
        self.caddy_log = caddy_log
        self.clock = clock
        self.monotonic = monotonic
        self.ledger = ledger
        self.runner = runner
        self.fetcher = fetcher
        self.route_transport = route_transport
        self.started = monotonic()
        self.deadline_at = self.started + deadline_s
        self.result = FleetResult()

    def expired(self) -> bool:
        return self.monotonic() >= self.deadline_at

    def _defer(self, device: FleetDevice) -> None:
        self.result.outcomes.append(DeviceOutcome(device.id, device.is_live, STATUS_DEFERRED))

    def run_device(self, device: FleetDevice, fetched, held: bool = False) -> str:
        """Run one device's cycle; failures are recorded, never raised."""
        try:
            self.runner(
                state_dir=device.state_dir,
                geofence=self.geofence_path,
                caddy_log=self.caddy_log if device.is_live else None,
                zone_fetch=fetched,
                route_transport=self.route_transport,
                ledger_root=self.root,
                reconcile_firmware=device.is_live,
            )
        except poll_cycle.PollBusy as exc:
            status, detail, trace = STATUS_BUSY, str(exc), ""
        except Exception as exc:
            status = STATUS_FAILED
            detail = "%s: %s" % (type(exc).__name__, exc)
            trace = traceback.format_exc()
        else:
            status, detail, trace = (STATUS_HELD if held else STATUS_OK), "", ""
        self.result.outcomes.append(
            DeviceOutcome(device.id, device.is_live, status, detail, trace))
        return status

    def fetch(self, group: ZoneGroup):
        """Fetch a zone once; an unexpected error yields an all-failed result."""
        zone = group.zone
        self.result.zone_fetches += 1
        try:
            fetched = self.fetcher(
                self.ledger, zone.lat, zone.lon, zone.radius_nm,
                clock=self.monotonic, deadline_at=self.deadline_at)
        except Exception as exc:
            print("fleet: zone fetch failed: %s" % type(exc).__name__, file=sys.stderr)
            fetched = _failed_fetch()
        self.result.requests += len(fetched.results) + len(fetched.failed)
        return fetched

    def serve_zone(self, group: ZoneGroup) -> None:
        has_live = any(d.is_live for d in group.devices)
        ordered = sorted(group.devices, key=lambda d: (not d.is_live, _last_run(d)))
        if self.expired() and not has_live:
            for device in ordered:
                self._defer(device)
            return
        fetched = self.fetch(group)
        ran = False
        for device in ordered:
            if self.expired() and not device.is_live:
                self._defer(device)
                continue
            status = self.run_device(device, fetched)
            ran = ran or status in (STATUS_OK, STATUS_FAILED)
        if fetched.results and ran:
            self.mark_served(group.zone.key)

    def mark_served(self, key: str) -> None:
        try:
            self.ledger.mark_zone_served(key, self.clock())
        except (request_budget.BudgetUnavailable, OSError, ValueError):
            print("fleet: could not record zone service time", file=sys.stderr)

    def serve_held(self, devices: Iterable[FleetDevice]) -> None:
        """Held devices run without a fetch; they cost no request."""
        for device in devices:
            if self.expired() and not device.is_live:
                self._defer(device)
            else:
                self.run_device(device, zone_fetch.ZoneFetch.not_fetched(), held=True)

    def ordered_groups(self, plan: ZonePlan) -> list[ZoneGroup]:
        try:
            last_served = self.ledger.zone_last_served()
        except (request_budget.BudgetUnavailable, OSError, ValueError):
            last_served = {}
        entries = [
            fleet_zones.ZoneEntry(g.zone, any(d.is_live for d in g.devices))
            for g in plan.zones.values()
        ]
        return [plan.zones[zone.key] for zone in fleet_zones.order_zones(entries, last_served)]


def run_fleet(
    state_root: str,
    geofence_path: str | None,
    caddy_log: str | None,
    *,
    start_deadline_s: float | None = None,
    clock: Callable[[], float] | None = None,
    monotonic: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
    ledger: Any = None,
    runner: Callable[..., Any] | None = None,
    fetcher: Callable[..., Any] | None = None,
    resolver: Resolver | None = None,
    route_transport: Any = None,
    environ: Mapping[str, str] | None = None,
) -> FleetResult:
    """Serve every runnable device once: one budgeted fetch per zone.

    Zones holding the live frame go first, then the rest oldest-served first.
    After `start_deadline_s` no new zone or device starts and the devices not
    reached keep their current image. A failing device, zone fetch or lock wait
    never stops the others. Held devices cost no request.
    """
    wall = clock if clock is not None else time.time
    if ledger is None:
        ledger = request_budget.RequestLedger(state_root, clock=clock, sleep=sleep)
    deadline = FLEET_START_DEADLINE_S if start_deadline_s is None else start_deadline_s
    run = _FleetRun(
        state_root, geofence_path, caddy_log, deadline, wall,
        monotonic if monotonic is not None else time.monotonic,
        ledger,
        runner if runner is not None else poll_cycle.run_once,
        fetcher if fetcher is not None else zone_fetch.fetch_zone,
        route_transport if route_transport is not None else SharedRouteTransport(state_root),
    )
    devices, skipped = runnable_devices(load_fleet(state_root, wall()), wall(), environ)
    for device_id, reason in skipped:
        run.result.outcomes.append(DeviceOutcome(device_id, False, STATUS_SKIPPED, reason))
    plan = plan_zones(devices, resolver if resolver is not None else geofence_resolver(geofence_path))
    live_first = [d for d in plan.held + plan.unzoned if d.is_live]
    for device in live_first:
        if device in plan.unzoned:
            run.run_device(device, None)
        else:
            run.serve_held([device])
    for device in plan.unzoned:
        if not device.is_live:
            run.result.outcomes.append(DeviceOutcome(device.id, False, STATUS_SKIPPED, "no_zone"))
    for group in run.ordered_groups(plan):
        run.serve_zone(group)
    run.serve_held([d for d in plan.held if not d.is_live])
    return run.result
