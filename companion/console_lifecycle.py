"""Admin console routes for the lifecycle area: reassign, retire and
re-activate a frame, and the read-only Audit log page.

Security invariants:
- Every frame action is admin-only and carries a CSRF token.
- The frame id in the path is shape-checked before any lookup.
- The live frame is never wiped or retired: `fleet_ops` refuses (and audits)
  a retire, and a reassign of it changes only the owner.
- A frame's directory is wiped only while no poll for it can write: the busy
  guard holds the in-process lock and the cross-process poll-cycle lock.
- The audit page has one GET route; nothing here changes or deletes a row.
"""
import contextlib
import datetime
from urllib.parse import parse_qs, urlsplit

from companion import audit, console_flash, device_scope, i18n, route_types
from companion.pages import audit_page
from server import device_dirs, fleet_db, fleet_ops

# Same literals as companion/console_routes.py (which imports this module, so
# it cannot be imported at module level); a test pins that the two agree.
FRAME_ACTION_PREFIX = "/fleet/frames/"
RETIRE_SUFFIX = "/retire"
REACTIVATE_SUFFIX = "/reactivate"
REASSIGN_SUFFIX = "/reassign"
FLEET_PATH = "/fleet"
AUDIT_PATH = "/audit"

OWNER_FIELD = "owner_user_id"

FLASH_REASSIGNED = "lifecycle.reassigned"
FLASH_RETIRED = "lifecycle.retired"
FLASH_REACTIVATED = "lifecycle.reactivated"
FLASH_LIVE_PROTECTED = "lifecycle.live_protected"
FLASH_BUSY = "lifecycle.busy"
FLASH_NOT_FOUND = "lifecycle.not_found"
FLASH_OWNER_UNAVAILABLE = "lifecycle.owner_unavailable"
FLASH_SAME_OWNER = "lifecycle.same_owner"

console_flash.register_flash(
    FLASH_REASSIGNED, "success",
    i18n.msg("admin_lifecycle.flash_reassigned", "Frame reassigned"),
    i18n.msg("admin_lifecycle.flash_reassigned_detail", "{frame} now belongs to {email}."))
console_flash.register_flash(
    FLASH_RETIRED, "success",
    i18n.msg("admin_lifecycle.flash_retired", "Frame retired"),
    i18n.msg(
        "admin_lifecycle.flash_retired_detail",
        "{frame} shows a retired screen at its next update. Its data is kept."))
console_flash.register_flash(
    FLASH_REACTIVATED, "success",
    i18n.msg("admin_lifecycle.flash_reactivated", "Frame re-activated"),
    i18n.msg(
        "admin_lifecycle.flash_reactivated_detail",
        "It returns to pairing and shows a new code at its next update."))
console_flash.register_flash(
    FLASH_LIVE_PROTECTED, "error",
    i18n.msg("admin_lifecycle.flash_action_refused", "Action refused"),
    i18n.msg(
        "admin_lifecycle.flash_live_protected_detail",
        "The live frame cannot be retired."))
console_flash.register_flash(
    FLASH_BUSY, "error",
    i18n.msg("admin_lifecycle.flash_frame_busy", "Frame is busy"),
    i18n.msg(
        "admin_lifecycle.flash_frame_busy_detail",
        "An update for this frame is running. Try again in a minute."))
console_flash.register_flash(
    FLASH_NOT_FOUND, "error",
    i18n.msg("admin_lifecycle.flash_frame_not_found", "Frame not found"),
    i18n.msg(
        "admin_lifecycle.flash_frame_not_found_detail",
        "It may already have been changed. Nothing was modified."))
console_flash.register_flash(
    FLASH_OWNER_UNAVAILABLE, "error",
    i18n.msg("admin_lifecycle.flash_owner_unavailable", "Choose an active owner"),
    i18n.msg(
        "admin_lifecycle.flash_owner_unavailable_detail",
        "That user is disabled or does not exist. Nothing was modified."))
console_flash.register_flash(
    FLASH_SAME_OWNER, "error",
    i18n.msg("admin_lifecycle.flash_same_owner", "Already the owner"),
    i18n.msg(
        "admin_lifecycle.flash_same_owner_detail",
        "That user already owns this frame. Nothing was modified."))


# ---- guards -----------------------------------------------------------------


@contextlib.contextmanager
def busy_guard(state_dir):
    """Yield True while neither the in-process poll lock nor the cross-process
    poll-cycle lock for `state_dir` is held by someone else; False otherwise.
    Neither lock is ever waited for."""
    from server import poll_cycle
    lock = device_scope.poll_lock_for(state_dir)
    with contextlib.ExitStack() as stack:
        if not lock.acquire(blocking=False):
            yield False
            return
        stack.callback(lock.release)
        try:
            stack.enter_context(poll_cycle.poll_cycle_lock(state_dir, 0))
        except poll_cycle.PollBusy:
            yield False
            return
        yield True


def _owner_choice(raw):
    """The chosen owner id, or None when it is not a plain integer."""
    text = raw.strip()
    return int(text) if text.isascii() and text.isdigit() and len(text) < 10 else None


def _back(flash_key, **params):
    return console_flash.queue_flash(flash_key, **params)


def _frame_label(device):
    return str(device["name"]) if device["name"] else str(device["id"])


# ---- handlers -------------------------------------------------------------


def handle_retire(h, m):
    device_id = m.captured
    if not device_dirs.DEVICE_ID_RE.match(device_id):
        return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
    conn = fleet_db.connect(h.args.state_dir)
    try:
        device = fleet_db.get_device(conn, device_id)
        if device is None:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
        label = _frame_label(device)
        try:
            fleet_ops.retire_frame(conn, h.args.state_dir, device_id, audit.actor_for(h))
        except fleet_ops.LiveFrameProtected:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_LIVE_PROTECTED))
        except fleet_ops.NotFound:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
    finally:
        conn.close()
    return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_RETIRED, frame=label))


def handle_reactivate(h, m):
    pending_id = m.captured
    if not fleet_db.PENDING_ID_RE.match(pending_id):
        return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
    conn = fleet_db.connect(h.args.state_dir)
    try:
        fleet_ops.reactivate_frame(
            conn, h.args.state_dir, pending_id, audit.actor_for(h), busy_guard)
    except fleet_ops.NotFound:
        return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
    except fleet_ops.FrameBusy:
        return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_BUSY))
    finally:
        conn.close()
    return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_REACTIVATED))


def _reassign_refusal(conn, device_id, owner_id):
    """The flash key refusing this reassign before anything runs, or None."""
    device = fleet_db.get_device(conn, device_id)
    if device is None:
        return FLASH_NOT_FOUND
    if owner_id is None:
        return FLASH_OWNER_UNAVAILABLE
    row = conn.execute(
        "SELECT email, disabled FROM users WHERE id = ?", (owner_id,)).fetchone()
    if row is None or row["disabled"]:
        return FLASH_OWNER_UNAVAILABLE
    if device["owner_user_id"] == owner_id:
        return FLASH_SAME_OWNER
    return None


def handle_reassign(h, m):
    device_id = m.captured
    if not device_dirs.DEVICE_ID_RE.match(device_id):
        return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
    owner_id = _owner_choice(h.read_form().get(OWNER_FIELD, ""))
    conn = fleet_db.connect(h.args.state_dir)
    try:
        refusal = _reassign_refusal(conn, device_id, owner_id)
        if refusal is not None:
            return h.redirect(FLEET_PATH, set_cookie=_back(refusal))
        try:
            fleet_ops.reassign_frame(
                conn, h.args.state_dir, device_id, owner_id, audit.actor_for(h), busy_guard)
        except fleet_ops.NotFound:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_NOT_FOUND))
        except fleet_ops.OwnerUnavailable:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_OWNER_UNAVAILABLE))
        except fleet_ops.FrameBusy:
            return h.redirect(FLEET_PATH, set_cookie=_back(FLASH_BUSY))
        device = fleet_db.get_device(conn, device_id)
        email = conn.execute(
            "SELECT email FROM users WHERE id = ?", (owner_id,)).fetchone()["email"]
        label = _frame_label(device) if device is not None else device_id
    finally:
        conn.close()
    return h.redirect(
        FLEET_PATH, set_cookie=_back(FLASH_REASSIGNED, frame=label, email=email))


# ---- audit log page -----------------------------------------------------------

_MAX_PAGE_DIGITS = 9


def _query_value(h, name):
    values = parse_qs(urlsplit(h.path).query).get(name)
    return values[0] if values else ""


def _category(raw):
    return raw if raw in fleet_db.AUDIT_CATEGORIES else "all"


def _page_number(raw):
    """The requested page: 1 for anything that is not a positive integer."""
    text = raw.strip()
    if not (text.isascii() and text.isdigit()) or len(text) > _MAX_PAGE_DIGITS:
        return 1
    return max(1, int(text))


def _target_name(conn, target_type, target_id):
    """A display name for the audited target, "" when none can be found."""
    if target_id is None:
        return ""
    if target_type == "device":
        row = conn.execute(
            "SELECT name FROM devices WHERE id = ?", (target_id,)).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT previous_name AS name FROM pending_devices "
                "WHERE previous_device_id = ?", (target_id,)).fetchone()
        return str(row["name"]) if row is not None and row["name"] else ""
    if target_id.isascii() and target_id.isdigit() and len(target_id) < 10:
        table, column = {
            "user": ("users", "email"), "location": ("locations", "name")
        }.get(target_type, (None, None))
        if table is not None:
            row = conn.execute(
                "SELECT %s AS name FROM %s WHERE id = ?" % (column, table),
                (int(target_id),)).fetchone()
            return str(row["name"]) if row is not None and row["name"] else ""
    return ""


def _event(conn, row):
    return audit_page.AuditEvent(
        ts=int(row["ts"]), actor_label=str(row["actor_label"]),
        actor_is_user=row["actor_user_id"] is not None, action=str(row["action"]),
        target_primary=_target_name(conn, row["target_type"], row["target_id"]),
        target_id=None if row["target_id"] is None else str(row["target_id"]),
        outcome=str(row["outcome"]), source_ip=row["source_ip"])


def build_audit_view(state_dir, category, requested_page):
    """The `AuditView` for a category chip and page; a page past the end
    falls back to the last page."""
    conn = fleet_db.connect(state_dir)
    try:
        total = fleet_db.count_audit(conn, category)
        last_page = max(1, -(-total // audit_page.PAGE_SIZE))
        page = min(requested_page, last_page)
        rows = fleet_db.list_audit(
            conn, category, audit_page.PAGE_SIZE, (page - 1) * audit_page.PAGE_SIZE)
        events = tuple(_event(conn, row) for row in rows)
    finally:
        conn.close()
    return audit_page.AuditView(
        events=events, category=category, total=total, page=page,
        now=datetime.datetime.now(datetime.timezone.utc))


def handle_audit_get(h, m):
    from companion import console_routes
    category = _category(_query_value(h, audit_page.CATEGORY_QUERY))
    page = _page_number(_query_value(h, audit_page.PAGE_QUERY))
    return h._console_page(
        console_routes.AUDIT_ROUTE, None,
        lambda: audit_page.render(build_audit_view(h.args.state_dir, category, page)),
        audit_page.AUDIT_PURPOSE)


ROUTES = (
    route_types.Route(
        "POST", route_types.PrefixSuffix(FRAME_ACTION_PREFIX, RETIRE_SUFFIX),
        handle_retire, route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(FRAME_ACTION_PREFIX, REACTIVATE_SUFFIX),
        handle_reactivate, route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.PrefixSuffix(FRAME_ACTION_PREFIX, REASSIGN_SUFFIX),
        handle_reassign, route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "GET", route_types.Exact(AUDIT_PATH), handle_audit_get, route_types.ADMIN_ONLY),
)
