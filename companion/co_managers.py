"""Add, remove and leave handlers for a frame's co-managers.

Security invariants:
- The frame is always the device the dispatcher already authorised
  (`m.device`); no frame id is read from the form.
- Adding and removing run behind the owner-or-admin gate. Leaving runs behind
  the owner/co-manager gate but reads nothing from the form: it only ever
  touches the caller's own membership row.
- Every add failure (unknown, not invited, disabled, the owner's own address,
  already a co-manager, malformed) ends in the same flash key and redirect.
  The typed address is never echoed, logged, put in a URL or stored in an
  audit row; a refusal's audit detail holds a short internal reason only.
- Each change and its audit row share one `BEGIN IMMEDIATE` transaction, so a
  failed audit write rolls the change back too.
- Only co-manager rows are ever deleted here, so no path can remove the owner.
"""
import re
import sqlite3
import unicodedata

from companion import audit, device_scope
from companion.pages import co_managers_card as card
from server import fleet_db

_MAX_EMAIL_CHARS = 254
_USER_ID_RE = re.compile(r"\A[0-9]{1,9}\Z")

# Where a user lands after leaving a frame they can no longer open.
_ACCOUNT_PATH = "/account"

_VIA_OWNER = "owner"
_VIA_ADMIN = "admin"
_VIA_SELF = "self"

_REASON_MALFORMED = "malformed"
_REASON_UNKNOWN = "unknown"
_REASON_INELIGIBLE = "ineligible"
_REASON_DUPLICATE = "duplicate"

_ADD = fleet_db.ACTION_CO_MANAGER_ADD
_REMOVE = fleet_db.ACTION_CO_MANAGER_REMOVE

# What a database or store failure can raise while a handler works.
_STORE_ERRORS = (sqlite3.Error, fleet_db.FleetDbError, OSError)


def _redirect_home(h, flash_key):
    return h.redirect("%s?flash=%s" % (device_scope.scoped("/"), flash_key))


def _actor_via(principal):
    """Who acts on the frame: an administrator, else its owner."""
    return _VIA_ADMIN if principal is not None and principal.role == "admin" else _VIA_OWNER


def _actor_id(principal):
    return None if principal is None else principal.user_id


def _typed_email(form):
    """The `email` field, or None when it cannot be an address: empty, over
    length, or containing a control character. The value is never altered
    beyond the trimming `fleet_db.normalize_email` does.
    """
    raw = form.get(card.FIELD_EMAIL, "")
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or len(value) > _MAX_EMAIL_CHARS:
        return None
    if any(unicodedata.category(ch) == "Cc" for ch in value):
        return None
    return value


def _failed(h, device, action):
    """A write failed: a best-effort `failed` audit row, then the failure
    flash. The audit write cannot raise out of here.
    """
    try:
        audit.record_standalone(h, action, "device", device.id, "failed", {"reason": "write"})
    except _STORE_ERRORS:
        pass
    return _redirect_home(h, card.FLASH_FAILED)


def _refusal_reason(conn, device, email):
    """The internal reason an address could not be added, for the audit row
    only. Never contains the address.
    """
    try:
        normalized = fleet_db.normalize_email(email)
    except ValueError:
        return _REASON_MALFORMED
    row = conn.execute("SELECT id FROM users WHERE email = ?", (normalized,)).fetchone()
    if row is None:
        return _REASON_UNKNOWN
    if fleet_db.is_co_manager(conn, device.id, int(row["id"])):
        return _REASON_DUPLICATE
    return _REASON_INELIGIBLE


def _try_add(h, conn, device, email, principal):
    """Add the person `email` names inside the open transaction and audit it.
    Returns None on success or the internal refusal reason; a refusal
    leaves nothing behind.
    """
    candidate = None if email is None else fleet_db.find_eligible_co_manager(
        conn, device.id, email)
    if candidate is None:
        return _REASON_MALFORMED if email is None else _refusal_reason(conn, device, email)
    try:
        fleet_db.add_co_manager(conn, device.id, candidate, _actor_id(principal))
    except fleet_db.AlreadyCoManager:
        return _REASON_DUPLICATE
    except fleet_db.IneligibleUser:
        return _REASON_INELIGIBLE
    except fleet_db.UnknownDevice:
        return _REASON_UNKNOWN
    audit.record_in(
        h, conn, _ADD, "device", device.id, "ok",
        {"co_manager_user_id": candidate, "via": _actor_via(principal)})
    return None


def handle_add(h, m):
    device = m.device
    principal = h._safe_principal()
    email = _typed_email(h.read_form())
    try:
        conn = fleet_db.connect(h.args.state_dir)
        try:
            with fleet_db.transaction(conn):
                reason = _try_add(h, conn, device, email, principal)
        finally:
            conn.close()
    except _STORE_ERRORS:
        return _failed(h, device, _ADD)
    if reason is None:
        return _redirect_home(h, card.FLASH_ADDED)
    try:
        audit.record_standalone(h, _ADD, "device", device.id, "denied", {"reason": reason})
    except _STORE_ERRORS:
        return _failed(h, device, _ADD)
    return _redirect_home(h, card.FLASH_ADD_REFUSED)


def _remove_row(h, device, user_id, via):
    """Delete one membership row and audit it in one transaction. Returns
    whether a row existed; raises a store error on failure.
    """
    conn = fleet_db.connect(h.args.state_dir)
    try:
        with fleet_db.transaction(conn):
            if not fleet_db.remove_co_manager(conn, device.id, user_id):
                return False
            audit.record_in(
                h, conn, _REMOVE, "device", device.id, "ok",
                {"co_manager_user_id": user_id, "via": via})
            return True
    finally:
        conn.close()


def handle_remove(h, m):
    device = m.device
    raw = h.read_form().get(card.FIELD_USER_ID, "")
    if not isinstance(raw, str) or not _USER_ID_RE.match(raw):
        return _redirect_home(h, card.FLASH_FAILED)
    principal = h._safe_principal()
    try:
        removed = _remove_row(h, device, int(raw), _actor_via(principal))
    except _STORE_ERRORS:
        return _failed(h, device, _REMOVE)
    return _redirect_home(h, card.FLASH_REMOVED if removed else card.FLASH_FAILED)


def handle_leave(h, m):
    """Remove the caller's own membership. The form is never read."""
    device = m.device
    principal = h._safe_principal()
    if principal is None:
        return _redirect_home(h, card.FLASH_LEAVE_NOOP)
    try:
        left = _remove_row(h, device, principal.user_id, _VIA_SELF)
    except _STORE_ERRORS:
        return _failed(h, device, _REMOVE)
    if not left:
        return _redirect_home(h, card.FLASH_LEAVE_NOOP)
    return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_LEFT))
