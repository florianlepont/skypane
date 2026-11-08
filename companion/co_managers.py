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
- Removing a frame acts on the authorised device for its own owner only (an
  administrator who is not the owner is refused, since retiring is theirs on
  Fleet), re-checks the owner inside the retire transaction, and never
  touches the live frame: `fleet_ops.retire_frame` refuses and audits it.
- `return_to` is attacker-controlled: it is honoured only when it equals one
  of the whitelisted host pages exactly (`card.safe_return_to`); anything else
  is ignored and the redirect is the frame's Home as before. The frame id put
  in `?access=` is the one the dispatcher authorised, never a form value.
"""
import re
import sqlite3
import unicodedata
import urllib.parse

from companion import access, audit, console_flash, device_scope
from companion.pages import co_managers_card as card
from server import fleet_db, fleet_ops

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


_FLEET_TONES = (
    (card.FLASH_ADDED, "success", card.FLASH_ADDED_TEXT),
    (card.FLASH_REMOVED, "success", card.FLASH_REMOVED_TEXT),
    (card.FLASH_ADD_REFUSED, "error", card.FLASH_ADD_REFUSED_TEXT),
    (card.FLASH_FAILED, "error", card.FLASH_FAILED_TEXT),
)
for _key, _tone, _text in _FLEET_TONES:
    console_flash.register_flash(_key, _tone, _text)


def _redirect_home(h, flash_key):
    return h.redirect("%s?flash=%s" % (device_scope.scoped("/"), flash_key))


def _redirect_back(h, device, flash_key):
    """Back to where the form came from: the whitelisted host page, with the
    Manage access dialog reopened (Account) or the frame selected (Fleet),
    else the frame's Home as before. Fleet shows the result as its console toast, Account through `?flash=`."""
    return_to = card.safe_return_to(h.read_form().get(card.FIELD_RETURN_TO))
    if return_to is None:
        return _redirect_home(h, flash_key)
    access_query = "%s=%s" % (card.ACCESS_QUERY, urllib.parse.quote(device.id, safe=""))
    if return_to == card.RETURN_FLEET:
        # Fleet selects the frame on its Access tab, where the result shows.
        return h.redirect(
            "%s?frame=%s&tab=%s" % (
                return_to, urllib.parse.quote(device.id, safe=""), card.ACCESS_QUERY),
            set_cookie=console_flash.queue_flash(flash_key))
    return h.redirect("%s?%s&flash=%s" % (return_to, access_query, flash_key))


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


def _failed(h, device, action, back=True):
    """A write failed: a best-effort `failed` audit row, then the failure
    flash. The audit write cannot raise out of here. `back` is False for
    leaving, whose form is never read.
    """
    try:
        audit.record_standalone(h, action, "device", device.id, "failed", {"reason": "write"})
    except _STORE_ERRORS:
        pass
    if back:
        return _redirect_back(h, device, card.FLASH_FAILED)
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
        return _redirect_back(h, device, card.FLASH_ADDED)
    try:
        audit.record_standalone(h, _ADD, "device", device.id, "denied", {"reason": reason})
    except _STORE_ERRORS:
        return _failed(h, device, _ADD)
    return _redirect_back(h, device, card.FLASH_ADD_REFUSED)


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
        return _redirect_back(h, device, card.FLASH_FAILED)
    principal = h._safe_principal()
    try:
        removed = _remove_row(h, device, int(raw), _actor_via(principal))
    except _STORE_ERRORS:
        return _failed(h, device, _REMOVE)
    return _redirect_back(
        h, device, card.FLASH_REMOVED if removed else card.FLASH_FAILED)


def handle_leave(h, m):
    """Remove the caller's own membership. The form is never read."""
    device = m.device
    principal = h._safe_principal()
    if principal is None:
        return _redirect_home(h, card.FLASH_LEAVE_NOOP)
    try:
        left = _remove_row(h, device, principal.user_id, _VIA_SELF)
    except _STORE_ERRORS:
        return _failed(h, device, _REMOVE, back=False)
    if not left:
        return _redirect_home(h, card.FLASH_LEAVE_NOOP)
    return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_LEFT))


def handle_remove_frame(h, m):
    """The owner retires their own frame: it leaves their account, keeps its
    history and can be assigned again by an administrator. The live frame is
    refused and left untouched. The form is never read."""
    device = m.device
    principal = h._safe_principal()
    if principal is None or principal.user_id != device.owner_user_id:
        return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_FRAME_REMOVE_REFUSED))
    try:
        conn = fleet_db.connect(h.args.state_dir)
        try:
            fleet_ops.retire_frame(
                conn, h.args.state_dir, device.id, audit.actor_for(h),
                owner_user_id=principal.user_id)
        finally:
            conn.close()
    except fleet_ops.LiveFrameProtected:
        return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_FRAME_REMOVE_LIVE))
    except fleet_ops.NotFound:
        return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_FRAME_REMOVE_REFUSED))
    except (*_STORE_ERRORS, fleet_ops.OpsError, ValueError):
        return _failed(h, device, "device.retire", back=False)
    return h.redirect("%s?flash=%s" % (_ACCOUNT_PATH, card.FLASH_FRAME_REMOVED))


def _owner_email(conn, owner_user_id):
    row = conn.execute("SELECT email FROM users WHERE id = ?", (owner_user_id,)).fetchone()
    return None if row is None else str(row["email"])


def access_view(conn, device, principal):
    """The Manage access dialog's view for `principal`, or None when there is
    nothing to offer: no fleet row, no owner, or a viewer who is neither the
    owner nor an administrator. Management is decided from the role and the
    owner, never from having reached the page.
    """
    if fleet_db.get_device(conn, device.id) is None or device.owner_user_id is None:
        return None
    is_admin = principal.role == access.ADMIN
    viewer_id = principal.user_id
    if not (is_admin or (viewer_id is not None and device.owner_user_id == viewer_id)):
        return None
    owner_email = _owner_email(conn, device.owner_user_id)
    if owner_email is None:
        return None
    members = tuple(
        (int(r["user_id"]), str(r["email"]), bool(r["disabled"]))
        for r in fleet_db.list_co_managers(conn, device.id))
    # The invited-user list is filled for an administrator only.
    candidates = tuple(
        str(r["email"]) for r in fleet_db.eligible_co_manager_candidates(conn, device.id)
    ) if is_admin else ()
    # Removing a frame is the owner's own act; an administrator retires a
    # frame from Fleet, and the live frame is never offered.
    can_remove = (
        viewer_id is not None and device.owner_user_id == viewer_id and not device.is_live)
    return card.CardView(owner_email, members, candidates, viewer_id, is_admin, can_remove)
