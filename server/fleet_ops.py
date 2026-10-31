"""Server-side frame operations: register, claim, retire, re-activate, reassign.

Leaf module shared by the console handlers and the CLI so each operation is
testable without HTTP. It imports only `fleet_db`, `device_dirs`,
`pairing_code` and `hardware`; the poll loop's lock is injected as a
`busy_guard`.

Security invariants:
- A claim is one BEGIN IMMEDIATE transaction that deletes the pending row,
  inserts the device, provisions its directory and writes the audit row, so
  two simultaneous claims of one code have exactly one winner.
- Wrong, expired, used and malformed codes raise the same `ClaimRefused`
  after the same scan; neither the guess nor a code appears in any message,
  audit row or log.
- Operations that delete data run the delete inside the transaction, so a
  failure rolls the database change back.
- The live frame (state path ".") is never wiped, retired or re-provisioned.
"""
from __future__ import annotations

import contextlib
import os
import re
import shutil
import sqlite3
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager
from typing import NamedTuple

# Same repo-root sys.path bootstrap as server/fleet_db.py.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_dirs, fleet_db, hardware, pairing_code  # noqa: E402

PAIRING_DIRNAME = "pairing"

ACTION_REGISTER = "frame.register"
ACTION_CLAIM = "pairing.claim"
ACTION_REASSIGN = "device.reassign"
ACTION_RETIRE = "device.retire"
ACTION_REACTIVATE = "device.reactivate"

FAIL_INVALID = "invalid"
FAIL_THROTTLED = "throttled"
_FAIL_REASONS = (FAIL_INVALID, FAIL_THROTTLED)

# A well-formed code used to run the scan when the typed text is malformed.
_DUMMY_CODE = "2" * pairing_code.CODE_LENGTH

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

BusyGuard = Callable[[str], AbstractContextManager[bool]]


class OpsError(Exception):
    """Base class; no message carries a secret, code or guess."""


class ClaimRefused(OpsError):
    """The code is wrong, expired, already used or malformed."""


class OwnerUnavailable(OpsError):
    """The chosen owner is missing or disabled."""


class LiveFrameProtected(OpsError):
    """The live frame cannot be retired or wiped."""


class FrameBusy(OpsError):
    """A poll for this frame is running."""


class NotFound(OpsError):
    """No such frame in the expected state."""


class DuplicateFrame(OpsError):
    """The MAC is already registered or pending."""


class ClaimResult(NamedTuple):
    device_id: str
    pending_id: str
    owner_user_id: int


def pairing_dir(root: str, pending_id: str) -> str:
    """`<root>/pairing/<pending_id>`; the id must have the pending shape."""
    if not fleet_db.PENDING_ID_RE.match(pending_id):
        raise ValueError("invalid pending id")
    return os.path.join(root, PAIRING_DIRNAME, pending_id)


def _now(now: int | None) -> int:
    return int(time.time()) if now is None else now


def _owner_is_active(conn: sqlite3.Connection, owner_user_id: int) -> bool:
    row = conn.execute(
        "SELECT disabled FROM users WHERE id = ?", (owner_user_id,)
    ).fetchone()
    return row is not None and not row["disabled"]


def _require_owner(conn: sqlite3.Connection, owner_user_id: int) -> None:
    if not _owner_is_active(conn, owner_user_id):
        raise OwnerUnavailable("owner is unknown or disabled")


def _audit_standalone(
    conn: sqlite3.Connection,
    actor: fleet_db.AuditActor,
    action: str,
    target_type: str,
    target_id: str | None,
    outcome: str,
    detail: Mapping[str, object] | None,
) -> None:
    """One audit row in its own short transaction (denied and failed rows)."""
    with fleet_db.transaction(conn):
        fleet_db.audit_append(conn, actor, action, target_type, target_id, outcome, detail)


# ---- register ---------------------------------------------------------


def register_frame(
    conn: sqlite3.Connection,
    mac: str,
    secret_sha256: str,
    hardware_type: str,
    actor: fleet_db.AuditActor,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Register a frame awaiting a pairing code; returns the pending id.

    Only the SHA-256 of the enrolment secret is accepted.
    """
    mac = mac.strip().lower()
    if not _MAC_RE.match(mac):
        raise ValueError("invalid MAC (aa:bb:cc:dd:ee:ff)")
    if not _SHA256_RE.match(secret_sha256):
        raise ValueError("secret_sha256 must be 64 lowercase hex characters")
    if hardware_type not in hardware.available_types(environ):
        raise ValueError("unknown hardware type")
    with fleet_db.transaction(conn):
        if (
            fleet_db.get_device_by_mac(conn, mac) is not None
            or fleet_db.get_pending_by_mac(conn, mac) is not None
        ):
            raise DuplicateFrame("MAC is already registered")
        pending_id = fleet_db.register_pending(
            conn, mac, secret_sha256, hardware_type, actor.user_id, environ
        )
        fleet_db.audit_append(
            conn, actor, ACTION_REGISTER, "pending", pending_id, "ok",
            {"mac": mac, "hardware_type": hardware_type},
        )
    return pending_id


# ---- claim ------------------------------------------------------------


def record_claim_failure(
    conn: sqlite3.Connection, actor: fleet_db.AuditActor, reason: str
) -> None:
    """Audit a failed claim. Only the reason enum is stored, never the guess."""
    if reason not in _FAIL_REASONS:
        raise ValueError("invalid claim failure reason")
    if conn.in_transaction:
        fleet_db.audit_append(
            conn, actor, ACTION_CLAIM, "pairing", None, "failed", {"reason": reason}
        )
        return
    _audit_standalone(
        conn, actor, ACTION_CLAIM, "pairing", None, "failed", {"reason": reason}
    )


def _live_macs(conn: sqlite3.Connection) -> set[str]:
    return {
        str(r["mac"])
        for r in conn.execute(
            "SELECT mac FROM devices WHERE state_path = ?", (device_dirs.LIVE_STATE_PATH,)
        )
    }


def _claim_candidates(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        "SELECT id, mac, secret_sha256, token, hardware_type, code_salt, code_hash, "
        "code_expires_at FROM pending_devices "
        "WHERE status = ? AND code_hash IS NOT NULL",
        (fleet_db.PENDING_STATUS_PENDING,),
    )
    return [dict(r) for r in rows]


def claim_pairing_code(
    conn: sqlite3.Connection,
    root: str,
    code_text: str,
    owner_user_id: int,
    actor: fleet_db.AuditActor,
    now: int | None = None,
    environ: Mapping[str, str] | None = None,
) -> ClaimResult:
    """Turn the pending frame showing `code_text` into a device of the owner.

    Raises ClaimRefused (identical for every failure of the code),
    OwnerUnavailable (the code stays valid) or lets a storage error through
    after rolling everything back.
    """
    ts = _now(now)
    normalised = pairing_code.normalise_code(code_text)
    created_dir: str | None = None
    try:
        with fleet_db.transaction(conn):
            row = pairing_code.match_candidates(
                _claim_candidates(conn), normalised or _DUMMY_CODE, ts
            )
            if normalised is None or row is None:
                raise ClaimRefused("pairing code not accepted")
            _require_owner(conn, owner_user_id)
            pending_id = str(row["id"])
            profile = hardware.get_profile(str(row["hardware_type"]), environ)
            conn.execute("DELETE FROM pending_devices WHERE id = ?", (pending_id,))
            device_id = fleet_db.add_device(
                conn, str(row["mac"]), str(row["secret_sha256"]), profile.key,
                owner_user_id,
                token=None if row["token"] is None else str(row["token"]),
                state_path="auto", environ=environ,
            )
            # Recorded before devices/ first appears, so a corrupt fleet.db
            # can never leave per-device state without the live-frame record.
            device_dirs.record_live_macs(root, _live_macs(conn))
            created_dir = device_dirs.provision_device_dir(
                root, device_id, profile.width, profile.height
            )
            fleet_db.audit_append(
                conn, actor, ACTION_CLAIM, "device", device_id, "ok",
                {"pending_id": pending_id, "owner_user_id": owner_user_id},
            )
    except BaseException:
        if created_dir is not None:
            shutil.rmtree(created_dir, ignore_errors=True)
        raise
    shutil.rmtree(pairing_dir(root, pending_id), ignore_errors=True)
    return ClaimResult(device_id, pending_id, owner_user_id)


# ---- wipe helpers -----------------------------------------------------


@contextlib.contextmanager
def _guarded(busy_guard: BusyGuard | None, directory: str | None) -> Iterator[None]:
    """Hold the injected poll guard for `directory`, or refuse when busy."""
    if busy_guard is None or directory is None:
        yield
        return
    with busy_guard(directory) as free:
        if not free:
            raise FrameBusy("a poll for this frame is running")
        yield


def _wipe_and_reprovision(
    root: str, state_path: str, hardware_type: str, environ: Mapping[str, str] | None
) -> None:
    """Remove the frame's directory and seed a fresh one; verify the panel."""
    profile = hardware.get_profile(hardware_type, environ)
    device_dirs.wipe_device_dir(root, state_path)
    directory = device_dirs.provision_device_dir(
        root, state_path[len(device_dirs.DEVICES_DIRNAME) + 1:],
        profile.width, profile.height,
    )
    panel = os.path.join(directory, device_dirs.PANEL_FILENAME)
    if (
        not os.path.isfile(panel)
        or os.path.getsize(panel) != (profile.width // 2) * profile.height
    ):
        raise OpsError("fresh panel image missing or the wrong size")


def _directory_for(state_path: str | None, root: str) -> str | None:
    """The directory a wiping operation touches, None for none or the live frame."""
    if state_path is None or state_path == device_dirs.LIVE_STATE_PATH:
        return None
    return device_dirs.resolve_state_dir(root, state_path)


# ---- reassign ---------------------------------------------------------


def reassign_frame(
    conn: sqlite3.Connection,
    root: str,
    device_id: str,
    new_owner_user_id: int,
    actor: fleet_db.AuditActor,
    busy_guard: BusyGuard | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Give a frame to another owner.

    A non-live frame loses the previous owner's data (config, history, poll
    state, gallery), location and name; MAC, secret and token are kept. The
    live frame only changes owner and its files are not touched.
    """
    first = fleet_db.get_device(conn, device_id)
    if first is None:
        raise NotFound("no such frame")
    _require_owner(conn, new_owner_user_id)
    with _guarded(busy_guard, _directory_for(str(first["state_path"]), root)):
        with fleet_db.transaction(conn):
            dev = fleet_db.get_device(conn, device_id)
            if dev is None or dev["state_path"] != first["state_path"]:
                raise NotFound("no such frame")
            _require_owner(conn, new_owner_user_id)
            old_owner = dev["owner_user_id"]
            if dev["state_path"] == device_dirs.LIVE_STATE_PATH:
                conn.execute(
                    "UPDATE devices SET owner_user_id = ? WHERE id = ?",
                    (new_owner_user_id, device_id),
                )
            else:
                conn.execute(
                    "UPDATE devices SET owner_user_id = ?, location_id = NULL, "
                    "name = NULL WHERE id = ?",
                    (new_owner_user_id, device_id),
                )
                _wipe_and_reprovision(
                    root, str(dev["state_path"]), str(dev["hardware_type"]), environ
                )
            fleet_db.audit_append(
                conn, actor, ACTION_REASSIGN, "device", device_id, "ok",
                {"old_owner_user_id": old_owner, "new_owner_user_id": new_owner_user_id},
            )


# ---- retire and re-activate -------------------------------------------


def retire_frame(
    conn: sqlite3.Connection,
    root: str,
    device_id: str,
    actor: fleet_db.AuditActor,
    now: int | None = None,
) -> str:
    """Park a frame as a retired pending row, keeping its data and token.

    Returns the new pending id. The live frame is refused and the refusal is
    audited.
    """
    dev = fleet_db.get_device(conn, device_id)
    if dev is None:
        raise NotFound("no such frame")
    if dev["state_path"] == device_dirs.LIVE_STATE_PATH:
        _audit_standalone(
            conn, actor, ACTION_RETIRE, "device", device_id, "denied",
            {"reason": "live_frame"},
        )
        raise LiveFrameProtected("the live frame cannot be retired")
    with fleet_db.transaction(conn):
        pending_id = fleet_db.park_retired(conn, device_id, _now(now))
        if pending_id is None:
            raise NotFound("no such frame")
        fleet_db.audit_append(
            conn, actor, ACTION_RETIRE, "device", device_id, "ok",
            {"pending_id": pending_id, "owner_user_id": dev["owner_user_id"]},
        )
    return pending_id


def reactivate_frame(
    conn: sqlite3.Connection,
    root: str,
    pending_id: str,
    actor: fleet_db.AuditActor,
    busy_guard: BusyGuard | None = None,
) -> None:
    """Return a retired frame to pending, wiping its previous directory.

    The next display poll issues a fresh pairing code. MAC, secret and token
    are kept.
    """
    first = fleet_db.get_pending(conn, pending_id)
    if first is None or first["status"] != fleet_db.PENDING_STATUS_RETIRED:
        raise NotFound("no such retired frame")
    previous = first["previous_state_path"]
    directory = _directory_for(None if previous is None else str(previous), root)
    with _guarded(busy_guard, directory):
        with fleet_db.transaction(conn):
            row = fleet_db.get_pending(conn, pending_id)
            if row is None or row["status"] != fleet_db.PENDING_STATUS_RETIRED:
                raise NotFound("no such retired frame")
            fleet_db.reactivate_pending(conn, pending_id)
            if directory is not None:
                device_dirs.wipe_device_dir(root, str(previous))
            fleet_db.audit_append(
                conn, actor, ACTION_REACTIVATE, "pending", pending_id, "ok",
                {"previous_device_id": row["previous_device_id"]},
            )
