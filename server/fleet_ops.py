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
- Operations that delete data move the old directory aside inside the
  transaction, and delete it only after COMMIT. A failure before COMMIT rolls
  the database back and moves the directory back, so nothing is lost or
  half-wiped; the new owner always starts from a fresh provisioned directory.
- The live frame (state path ".") is never wiped, retired or re-provisioned.
"""
from __future__ import annotations

import contextlib
import logging
import os
import re
import secrets
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

_LOG = logging.getLogger(__name__)

_ASIDE_PREFIX = ".wipe-"
FAIL_REFUSED = "refused"
FAIL_INVALID_PATH = "invalid_path"
FAIL_STORAGE = "storage_error"
FAILURE_REASONS = (FAIL_REFUSED, FAIL_INVALID_PATH, FAIL_STORAGE)
_ID_ATTEMPTS = 8

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


def record_failure(
    conn: sqlite3.Connection,
    actor: fleet_db.AuditActor,
    action: str,
    target_type: str,
    target_id: str | None,
    reason: str,
) -> None:
    """Audit a failed operation; `reason` is a fixed enum word, never text."""
    if reason not in FAILURE_REASONS:
        raise ValueError("invalid failure reason")
    if conn.in_transaction:
        conn.execute("ROLLBACK")
    _audit_standalone(conn, actor, action, target_type, target_id, "failed", {"reason": reason})


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


def _add_device_with_free_directory(
    conn: sqlite3.Connection,
    root: str,
    row: Mapping[str, object],
    hardware_key: str,
    owner_user_id: int,
    environ: Mapping[str, str] | None,
) -> str:
    """Insert the device, never reusing an id whose directory already exists.

    A leftover directory (for example a retired frame's kept data) must not be
    inherited by, or deleted with, a new device. A taken id is rolled back to a
    savepoint and a new one is generated.
    """
    for _attempt in range(_ID_ATTEMPTS):
        conn.execute("SAVEPOINT claim_id")
        device_id = fleet_db.add_device(
            conn, str(row["mac"]), str(row["secret_sha256"]), hardware_key,
            owner_user_id,
            token=None if row["token"] is None else str(row["token"]),
            state_path="auto", environ=environ,
        )
        taken = os.path.lexists(
            os.path.join(root, device_dirs.DEVICES_DIRNAME, device_id)
        )
        if not taken:
            conn.execute("RELEASE claim_id")
            return device_id
        conn.execute("ROLLBACK TO claim_id")
        conn.execute("RELEASE claim_id")
    raise OpsError("no free device directory")


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
            device_id = _add_device_with_free_directory(
                conn, root, row, profile.key, owner_user_id, environ
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


def _require_canonical_path(state_path: str, device_id: object) -> None:
    """Refuse a wipe unless the stored path is exactly `devices/<its own id>`."""
    if state_path == device_dirs.LIVE_STATE_PATH:
        return
    if not isinstance(device_id, str) or not device_dirs.is_valid_device_id(device_id):
        raise OpsError("state path does not belong to this frame")
    if state_path != device_dirs.state_path_for(device_id):
        raise OpsError("state path does not belong to this frame")


def _move_aside(root: str, state_path: str) -> tuple[str, str] | None:
    """Rename the device directory next to itself; returns (directory, aside).

    Same filesystem, so the rename is atomic. None when there is no directory.
    The live path "." is refused before anything is touched.
    """
    if state_path == device_dirs.LIVE_STATE_PATH:
        raise ValueError("refusing to wipe the live state directory")
    directory = device_dirs.resolve_state_dir(root, state_path)
    if not os.path.lexists(directory):
        return None
    aside = os.path.join(
        os.path.dirname(directory), _ASIDE_PREFIX + secrets.token_hex(8)
    )
    os.rename(directory, aside)
    return directory, aside


def _restore_aside(moved: tuple[str, str] | None) -> None:
    """Undo `_move_aside`, discarding any fresh directory created since."""
    if moved is None:
        return
    directory, aside = moved
    if os.path.lexists(directory):
        shutil.rmtree(directory, ignore_errors=True)
    os.rename(aside, directory)


def _discard_aside(moved: tuple[str, str] | None) -> None:
    """Delete the renamed directory after COMMIT; a failure is logged only."""
    if moved is None:
        return
    try:
        shutil.rmtree(moved[1])
    except OSError as exc:
        _LOG.warning("could not delete %s after commit: %s", moved[1], exc.__class__.__name__)


def _reset_directory(
    root: str, state_path: str, hardware_type: str, environ: Mapping[str, str] | None
) -> tuple[str, str] | None:
    """Move the old directory aside and seed a fresh one; verify the panel."""
    profile = hardware.get_profile(hardware_type, environ)
    moved = _move_aside(root, state_path)
    try:
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
    except BaseException:
        _restore_aside(moved)
        raise
    return moved


@contextlib.contextmanager
def _transaction_keeping_directory(
    conn: sqlite3.Connection, moved: list[tuple[str, str] | None]
) -> Iterator[None]:
    """A fleet transaction whose directory move is undone on any failure.

    `moved` receives the aside pair; the caller appends it inside the body.
    After a successful COMMIT the renamed directory is deleted.
    """
    try:
        with fleet_db.transaction(conn):
            yield
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        for pair in moved:
            _restore_aside(pair)
        raise
    for pair in moved:
        _discard_aside(pair)


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
    _require_canonical_path(str(first["state_path"]), device_id)
    moved: list[tuple[str, str] | None] = []
    with _guarded(busy_guard, _directory_for(str(first["state_path"]), root)):
        with _transaction_keeping_directory(conn, moved):
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
                moved.append(_reset_directory(
                    root, str(dev["state_path"]), str(dev["hardware_type"]), environ
                ))
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
    are kept. The old directory is renamed aside, deleted only after COMMIT and
    restored on any failure.
    """
    first = fleet_db.get_pending(conn, pending_id)
    if first is None or first["status"] != fleet_db.PENDING_STATUS_RETIRED:
        raise NotFound("no such retired frame")
    previous = first["previous_state_path"]
    if previous is not None:
        _require_canonical_path(str(previous), first["previous_device_id"])
    directory = _directory_for(None if previous is None else str(previous), root)
    moved: list[tuple[str, str] | None] = []
    with _guarded(busy_guard, directory):
        with _transaction_keeping_directory(conn, moved):
            row = fleet_db.get_pending(conn, pending_id)
            if row is None or row["status"] != fleet_db.PENDING_STATUS_RETIRED:
                raise NotFound("no such retired frame")
            fleet_db.reactivate_pending(conn, pending_id)
            if directory is not None:
                moved.append(_move_aside(root, str(previous)))
            fleet_db.audit_append(
                conn, actor, ACTION_REACTIVATE, "pending", pending_id, "ok",
                {"previous_device_id": row["previous_device_id"]},
            )
