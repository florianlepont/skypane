#!/usr/bin/env python3
"""Import the live frame's legacy identity files into fleet.db.

Run as `python3 -m server.fleet_migrate --state-dir DIR --owner-email E
[--dry-run]` from a release directory. It is an explicit deploy step and is
never run at service start.

Invariants:
- Expand only: devices.json and byos_state.json are read, never written,
  and no other file in the state directory is touched. The previous
  release keeps working from those files.
- Idempotent: when fleet.db already matches the legacy files no write
  connection is opened, so the database bytes do not change.
- One transaction: the owner, the location, the devices and the migrated
  marker commit together, the marker last.
- A present-but-malformed legacy file aborts the run. Importing "nothing"
  from a corrupt file would silently drop the frame.
- Reconcile after a rollback period is legacy-wins on the secret hash and
  token of devices present in both places, inserts devices present only in
  the legacy files, and never deletes anything.
- A token for a MAC absent from devices.json (left by an earlier device
  removal) is skipped and counted, never copied into fleet.db. So is a
  token whose key is not the canonical lowercase MAC: byos lowercases MACs,
  so such a key can never match a device.
- Output names MACs and counts only; never a token, secret hash or file
  content.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field

# Same repo-root sys.path bootstrap as server/fleet_db.py.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import fleet_db, hardware  # noqa: E402

LEGACY_REGISTRY_FILE = "devices.json"
LEGACY_STATE_FILE = "byos_state.json"

ORLY_NAME = "Orly"
ORLY_LATITUDE = 48.7233
ORLY_LONGITUDE = 2.3794
ORLY_TIMEZONE = "Europe/Paris"
LIVE_DEVICE_NAME = "Orly frame"
LIVE_STATE_PATH = "."

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
# byos accepts and lowercases MACs of any case, so token keys are shape-checked
# case-insensitively here; only the canonical lowercase key can match a device.
_TOKEN_KEY_RE = re.compile(r"\A[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}\Z")
_SHA256_RE =re.compile(r"^[0-9a-f]{64}$")


class LegacyStateError(Exception):
    """A legacy file is present but unusable."""


class MigrationError(Exception):
    """The migration cannot run safely."""


@dataclass(frozen=True)
class LegacyState:
    devices: dict[str, str]  # mac -> secret_sha256
    tokens: dict[str, str]  # mac -> token
    skipped_tokens: int = 0  # tokens under unregistered or non-canonical MACs, never imported


@dataclass(frozen=True)
class Snapshot:
    marker: bool = False
    schema: int = 0  # PRAGMA user_version of an existing fleet.db, else 0
    bootstrap_owner_id: int | None = None
    user_emails: frozenset[str] = frozenset()
    location_names: frozenset[str] = frozenset()
    secrets: dict[str, str] = field(default_factory=dict)
    tokens: dict[str, str | None] = field(default_factory=dict)


Action = tuple[str, ...]


@dataclass(frozen=True)
class MigrationPlan:
    actions: tuple[Action, ...]
    needs_write: bool
    schema_upgrade: tuple[int, int] | None = None  # (from, to) when behind


@dataclass(frozen=True)
class MigrationReport:
    lines: list[str]
    changed: bool


# ---- legacy reader -----------------------------------------------------


def _load_json(path: str) -> object | None:
    try:
        with open(path, encoding="utf-8") as fh:
            doc: object = json.load(fh)
            return doc
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise LegacyStateError(f"{os.path.basename(path)} is unreadable") from exc


def _read_registry(state_dir: str) -> dict[str, str]:
    name = LEGACY_REGISTRY_FILE
    doc = _load_json(os.path.join(state_dir, name))
    if doc is None:
        return {}
    if not isinstance(doc, dict) or not isinstance(doc.get("devices"), dict):
        raise LegacyStateError(f"{name} has the wrong shape")
    out: dict[str, str] = {}
    for mac, entry in doc["devices"].items():
        if not isinstance(mac, str) or not _MAC_RE.match(mac):
            raise LegacyStateError(f"{name} holds a malformed MAC")
        digest = entry.get("secret_sha256") if isinstance(entry, dict) else None
        if not isinstance(digest, str) or not _SHA256_RE.match(digest):
            raise LegacyStateError(f"{name} holds a malformed secret hash for {mac}")
        out[mac] = digest
    return out


def _read_tokens(state_dir: str, known: dict[str, str]) -> tuple[dict[str, str], int]:
    """Tokens under canonical registered MACs, and how many other tokens were skipped."""
    name = LEGACY_STATE_FILE
    doc = _load_json(os.path.join(state_dir, name))
    if doc is None:
        return {}, 0
    if not isinstance(doc, dict) or not isinstance(doc.get("tokens"), dict):
        raise LegacyStateError(f"{name} has the wrong shape")
    out: dict[str, str] = {}
    skipped = 0
    for mac, token in doc["tokens"].items():
        if not isinstance(mac, str) or not _TOKEN_KEY_RE.match(mac):
            raise LegacyStateError(f"{name} holds a malformed MAC")
        if not isinstance(token, str) or not token:
            raise LegacyStateError(f"{name} holds a malformed token for {mac}")
        if mac != mac.lower() or mac not in known:
            skipped += 1
            continue
        out[mac] = token
    return out, skipped


def read_legacy(state_dir: str) -> LegacyState:
    """Strict reader: a missing file is empty, an invalid one raises."""
    devices = _read_registry(state_dir)
    tokens, skipped = _read_tokens(state_dir, devices)
    return LegacyState(devices=devices, tokens=tokens, skipped_tokens=skipped)


# ---- planning ----------------------------------------------------------


def _device_actions(legacy: LegacyState, snapshot: Snapshot) -> list[Action]:
    actions: list[Action] = []
    for mac in sorted(legacy.devices):
        if mac not in snapshot.secrets:
            actions.append(("add_device", mac))
            continue
        if snapshot.secrets[mac] != legacy.devices[mac]:
            actions.append(("sync_secret", mac))
        token = legacy.tokens.get(mac)
        # A missing legacy token never clears a database token.
        if token is not None and snapshot.tokens.get(mac) != token:
            actions.append(("sync_token", mac))
    return actions


def plan_migration(
    legacy: LegacyState, snapshot: Snapshot, owner_email: str | None
) -> MigrationPlan:
    """Ordered actions to bring fleet.db in line with the legacy files."""
    if not snapshot.marker and not owner_email:
        raise MigrationError(
            "--owner-email is required for the first migration"
        )
    device_actions = _device_actions(legacy, snapshot)
    actions: list[Action] = []
    if not snapshot.marker:
        actions.append(("ensure_owner",))
    adds = any(a[0] == "add_device" for a in device_actions)
    if ORLY_NAME not in snapshot.location_names and (not snapshot.marker or adds):
        actions.append(("ensure_location",))
    actions.extend(device_actions)
    upgrade: tuple[int, int] | None = None
    if 0 < snapshot.schema < fleet_db.SCHEMA_VERSION:
        upgrade = (snapshot.schema, fleet_db.SCHEMA_VERSION)
    return MigrationPlan(
        actions=tuple(actions),
        needs_write=bool(actions) or not snapshot.marker or upgrade is not None,
        schema_upgrade=upgrade,
    )


# ---- reading fleet.db --------------------------------------------------


def _snapshot_from(conn: sqlite3.Connection) -> Snapshot:
    version = fleet_db.schema_version(conn)
    if version == 0:
        return Snapshot()
    owner = fleet_db.meta_get(conn, fleet_db.META_BOOTSTRAP_OWNER)
    secrets: dict[str, str] = {}
    tokens: dict[str, str | None] = {}
    for row in conn.execute("SELECT mac, secret_sha256, token FROM devices"):
        secrets[str(row["mac"])] = str(row["secret_sha256"])
        tokens[str(row["mac"])] = None if row["token"] is None else str(row["token"])
    return Snapshot(
        schema=version,
        marker=fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is not None,
        bootstrap_owner_id=int(owner) if owner is not None else None,
        user_emails=frozenset(str(r["email"]) for r in fleet_db.list_users(conn)),
        location_names=frozenset(str(r["name"]) for r in fleet_db.list_locations(conn)),
        secrets=secrets,
        tokens=tokens,
    )


def read_snapshot(state_dir: str) -> Snapshot:
    """Current fleet.db contents; an absent file is an empty snapshot."""
    try:
        conn = fleet_db.connect_readonly(state_dir)
    except fleet_db.FleetDbAbsent:
        return Snapshot()
    except (fleet_db.FleetDbError, sqlite3.DatabaseError) as exc:
        raise MigrationError(f"fleet.db cannot be opened: {type(exc).__name__}") from exc
    try:
        return _snapshot_from(conn)
    except sqlite3.DatabaseError as exc:
        raise MigrationError(f"fleet.db cannot be read: {type(exc).__name__}") from exc
    finally:
        conn.close()


# ---- applying ----------------------------------------------------------


def _ensure_owner(conn: sqlite3.Connection, email: str) -> int:
    row = fleet_db.get_user_by_email(conn, email)
    if row is not None:
        return int(row["id"])
    return fleet_db.add_user(conn, email, "admin")


def _ensure_location(conn: sqlite3.Connection, create: bool) -> int | None:
    for row in fleet_db.list_locations(conn):
        if row["name"] == ORLY_NAME:
            return int(row["id"])
    if not create:
        return None
    return fleet_db.add_location(
        conn, ORLY_NAME, ORLY_LATITUDE, ORLY_LONGITUDE, ORLY_TIMEZONE
    )


def _apply_device(
    conn: sqlite3.Connection,
    action: Action,
    legacy: LegacyState,
    owner_id: int,
    location_id: int | None,
) -> None:
    kind, mac = action
    if kind == "add_device":
        fleet_db.add_device(
            conn,
            mac,
            legacy.devices[mac],
            hardware.LEGACY_KEY,
            owner_id,
            location_id=location_id,
            name=LIVE_DEVICE_NAME,
            token=legacy.tokens.get(mac),
            state_path=LIVE_STATE_PATH,
            allow_shared_live=True,
        )
    elif kind == "sync_secret":
        fleet_db.set_device_secret(conn, mac, legacy.devices[mac])
    elif kind == "sync_token":
        fleet_db.set_device_token(conn, mac, legacy.tokens[mac])


def _resolve_owner(
    conn: sqlite3.Connection, plan: MigrationPlan, owner_email: str | None
) -> int:
    if ("ensure_owner",) in plan.actions:
        assert owner_email is not None
        owner_id = _ensure_owner(conn, owner_email)
        fleet_db.meta_set(conn, fleet_db.META_BOOTSTRAP_OWNER, str(owner_id))
        return owner_id
    stored = fleet_db.meta_get(conn, fleet_db.META_BOOTSTRAP_OWNER)
    if stored is None:
        raise MigrationError("fleet.db has no recorded bootstrap owner")
    return int(stored)


def _apply(
    state_dir: str, plan: MigrationPlan, legacy: LegacyState, owner_email: str | None
) -> None:
    conn = fleet_db.connect(state_dir)
    try:
        with fleet_db.transaction(conn):
            owner_id = _resolve_owner(conn, plan, owner_email)
            location_id = _ensure_location(conn, ("ensure_location",) in plan.actions)
            for action in plan.actions:
                if len(action) == 2:
                    _apply_device(conn, action, legacy, owner_id, location_id)
            fleet_db.meta_set(conn, fleet_db.META_MIGRATED, fleet_db.utc_now_iso())
    finally:
        conn.close()


# ---- entry points ------------------------------------------------------


def _describe(plan: MigrationPlan, dry_run: bool) -> list[str]:
    verb = "would " if dry_run else ""
    labels = {
        "ensure_owner": f"{verb}create the owner as admin",
        "ensure_location": f"{verb}ensure the {ORLY_NAME} location",
        "add_device": f"{verb}add device",
        "sync_secret": f"{verb}update secret from legacy for",
        "sync_token": f"{verb}update token from legacy for",
    }
    lines = []
    if plan.schema_upgrade is not None:
        old, new = plan.schema_upgrade
        lines.append(f"{verb}upgrade fleet.db schema {old} -> {new}")
    for action in plan.actions:
        text = labels[action[0]]
        lines.append(f"{text} {action[1]}" if len(action) == 2 else text)
    return lines


def _with_skipped(lines: list[str], legacy: LegacyState) -> list[str]:
    if legacy.skipped_tokens:
        lines.append(
            f"skipped {legacy.skipped_tokens} token(s) for unregistered device(s)"
        )
    return lines


def migrate(state_dir: str, owner_email: str | None, dry_run: bool) -> MigrationReport:
    """Plan and (unless dry_run) apply the import; reads legacy files first."""
    email: str | None = None
    if owner_email:
        try:
            email = fleet_db.normalize_email(owner_email)
        except ValueError as exc:
            raise MigrationError(str(exc)) from exc
    try:
        legacy = read_legacy(state_dir)
    except LegacyStateError as exc:
        raise MigrationError(str(exc)) from exc
    snapshot = read_snapshot(state_dir)
    plan = plan_migration(legacy, snapshot, email)
    if not plan.needs_write:
        return MigrationReport(_with_skipped(["nothing to do"], legacy), changed=False)
    lines = _describe(plan, dry_run)
    if dry_run:
        lines = lines or ["would mark fleet.db migrated"]
        return MigrationReport(_with_skipped(lines, legacy), changed=False)
    if plan.actions or not snapshot.marker:
        _apply(state_dir, plan, legacy, email)
        lines.append(f"migrated {len(legacy.devices)} legacy device(s)")
    else:
        # Only the schema is behind: connect() applies the pending steps.
        fleet_db.connect(state_dir).close()
    return MigrationReport(_with_skipped(lines, legacy), changed=True)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Import the legacy device files into fleet.db (expand only)."
    )
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--owner-email", default=None,
                    help="required for the first migration")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change without writing anything")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = migrate(args.state_dir, args.owner_email, args.dry_run)
    except (MigrationError, LegacyStateError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (sqlite3.Error, OSError) as exc:
        print(f"error: {type(exc).__name__}", file=sys.stderr)
        return 1
    for line in report.lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
