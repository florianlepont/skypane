"""Admin console routes for the pairing area: the Fleet page, frame
registration, and the shared pairing-code claim.

Security invariants:
- Pairing by code is served by companion/user_pairing.py (the one Add a
  frame page); this module keeps what it shares: claim_code, the throttles
  and the audit of a refusal.
- The typed pairing code is a guess until proven. It is never stored, put
  in an audit row, a cookie, a URL, a log line or a flash; it is re-rendered
  only into the input of the immediate (no-store) refusal response.
- Wrong, expired, used and malformed codes give one identical answer.
- Both throttles are checked before the database is touched; a locked
  caller never has a code evaluated.
- Registration accepts only the SHA-256 of the enrolment secret.
"""
import datetime
import hashlib
import re
import sqlite3

from companion import (
    audit, co_managers, console_fleet_view, console_flash, device_scope, frame_state,
    i18n, route_types, throttle, wake)
from companion.pages import co_managers_card, fleet_page
from server import (
    device_config, device_dirs, fleet_db, fleet_ops, hardware, pairing_code, state_store)

# Same literals as companion/console_routes.py and the Add a frame page (both
# import this module, so they cannot be imported here); a test pins that they
# agree.
FLEET_PATH = "/fleet"
REGISTER_PATH = "/fleet/register"
PAIR_FRAME_PATH = "/pair-frame"

SESSION_LIMIT = 5
SESSION_LOCKOUT_S = 300
GLOBAL_LIMIT = 20
GLOBAL_LOCKOUT_S = 900
_GLOBAL_KEY = "pairing-claim"
_SESSION_KEY_HEX = 16

SESSION_THROTTLE = throttle.LockoutThrottle(limit=SESSION_LIMIT, lockout_s=SESSION_LOCKOUT_S)
GLOBAL_THROTTLE = throttle.LockoutThrottle(limit=GLOBAL_LIMIT, lockout_s=GLOBAL_LOCKOUT_S)

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")
_BARE_MAC_RE = re.compile(r"^[0-9a-f]{12}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

FLASH_PAIRED = "fleet.paired"
FLASH_REGISTERED = "fleet.registered"
FLASH_DUPLICATE = "fleet.register_duplicate"
console_flash.register_flash(
    FLASH_PAIRED, "success",
    i18n.msg("admin_fleet.flash_frame_paired", "Frame paired"),
    i18n.msg(
        "admin_fleet.flash_frame_paired_detail",
        "{frame} now belongs to {email}. It shows its first image at the next update."))
console_flash.register_flash(
    FLASH_REGISTERED, "success",
    i18n.msg("admin_fleet.flash_frame_registered", "Frame registered"),
    i18n.msg(
        "admin_fleet.flash_frame_registered_detail",
        "Power it on. It shows a pairing code within 5 minutes."))
console_flash.register_flash(
    FLASH_DUPLICATE, "error",
    i18n.msg(
        "admin_fleet.flash_frame_duplicate",
        "A frame with this address is already registered."),
    None)


# ---- page data ----------------------------------------------------------


def _read_all(state_dir):
    conn = fleet_db.connect(state_dir)
    try:
        return (
            fleet_db.list_users(conn), fleet_db.list_devices(conn),
            fleet_db.list_pending(conn))
    finally:
        conn.close()


def _percent(millivolts, curve=None):
    """Battery percent of `millivolts` on `curve` (None: the legacy curve)."""
    from companion import battery
    return None if millivolts is None else battery.percent(millivolts, curve)


def _stored_type_curve(key):
    """The discharge curve of the stored hardware type `key`, read from the
    registry whatever the production switch says, so a pending frame of a
    hidden type still shows its own curve. An unknown type reads as legacy."""
    profile = hardware.REGISTRY.get(key) if isinstance(key, str) else None
    return None if profile is None else profile.battery.curve


def _hardware_label(key):
    profile = hardware.REGISTRY.get(key)
    return profile.label if profile is not None else key


def frame_signals(device, now_iso):
    """(frame state, screen off, battery empty) of a frame, derived the way
    the frame's Home page derives them, so one frame has one status dot."""
    cfg = device_config.load_device_config(device.state_dir)
    critical = wake.read_battery_critical(device.state_dir)
    next_triple = wake.next_wake_status(
        device_scope.last_check_in_ts(device.state_dir), cfg, battery_critical=critical)
    state = frame_state.resolve_state(*next_triple, now_iso)
    return state, cfg.get("display_enabled") is False, critical


def _device_rows(state_dir, device_rows, now):
    # Imported on use: page_context loads modules that import this one.
    from companion import page_context
    by_id = {str(row["id"]): row for row in device_rows}
    rows = []
    for device in device_scope.load_devices(state_dir):
        row = by_id.get(device.id)
        if row is None:
            continue
        status = device_scope.device_status(device, now.timestamp())
        state, screen_off, critical = frame_signals(device, now.isoformat(timespec="seconds"))
        rows.append(fleet_page.FleetRow(
            kind=fleet_page.KIND_LIVE, frame_id=device.id,
            name=row["name"] or fleet_page.unnamed_text(), mono_id=device.id,
            owner_email=row["owner_email"], previous_owner=False,
            hardware=_hardware_label(device.hardware_type),
            last_seen=device_scope.last_check_in_epoch(device.state_dir),
            battery_percent=0 if critical else _percent(
                state_store.load_battery_state(device.state_dir),
                page_context.device_curve(device)),
            is_live_frame=device.state_path == device_dirs.LIVE_STATE_PATH,
            offline=status == device_scope.STATUS_OFFLINE,
            state=state, screen_off=screen_off))
    return rows


def _epoch(value):
    """`value` as epoch seconds when the column holds a number, else None."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _code_issued_at(row):
    """When the pairing code now stored for a pending frame was issued: the
    expiry minus the fixed code lifetime; None while no code is stored."""
    expires = _epoch(row["code_expires_at"])
    return None if expires is None else expires - pairing_code.CODE_TTL_S


def _pending_rows(pending_rows, emails):
    rows = []
    for row in pending_rows:
        retired = row["status"] == fleet_db.PENDING_STATUS_RETIRED
        owner_id = row["previous_owner_user_id"]
        rows.append(fleet_page.FleetRow(
            kind=fleet_page.KIND_RETIRED if retired else fleet_page.KIND_PENDING,
            frame_id=str(row["id"]),
            name=(
                (row["previous_name"] or fleet_page.unnamed_text()) if retired
                else str(row["mac"])),
            mono_id=(
                str(row["previous_device_id"] or row["id"]) if retired else str(row["id"])),
            owner_email=emails.get(owner_id) if retired else None,
            previous_owner=retired,
            hardware=_hardware_label(str(row["hardware_type"])),
            last_seen=row["last_seen_at"],
            battery_percent=_percent(
                row["battery_mv"], _stored_type_curve(str(row["hardware_type"]))),
            is_live_frame=False, offline=False,
            retired_at=_epoch(row["retired_at"]) if retired else None,
            code_issued_at=None if retired else _code_issued_at(row)))
    return rows


def _access_views(state_dir, principal):
    """((frame id, Manage access view), ...) for the frames `principal` can
    manage access of; empty without a principal or when the database cannot
    be read."""
    if principal is None:
        return ()
    views = []
    try:
        conn = fleet_db.connect(state_dir)
        try:
            for device in device_scope.load_devices(state_dir):
                view = co_managers.access_view(conn, device, principal)
                if view is not None:
                    views.append((device.id, view))
        finally:
            conn.close()
    except (sqlite3.Error, fleet_db.FleetDbError, OSError):
        return ()
    return tuple(views)


def owner_options(users, first_id=None):
    """(id, label) of every enabled user; the user `first_id` leads."""
    options = [
        (str(row["id"]), fleet_page.owner_label(row["email"], row["role"]))
        for row in users if not row["disabled"]]
    options.sort(key=lambda option: option[0] != str(first_id))
    return tuple(options)


def pairing_owners(state_dir, first_id):
    """The Owner choices of the administrator's Add a frame page."""
    conn = fleet_db.connect(state_dir)
    try:
        return owner_options(fleet_db.list_users(conn), first_id)
    finally:
        conn.close()


def build_view(state_dir, principal=None, **state):
    """The `FleetView` for the current database plus the form state of a
    refused submission (`state` overrides the form fields)."""
    users, device_rows, pending_rows = _read_all(state_dir)
    now = datetime.datetime.now(datetime.timezone.utc)
    emails = {row["id"]: row["email"] for row in users}
    rows = _device_rows(state_dir, device_rows, now)
    rows += _pending_rows(pending_rows, emails)
    owners = owner_options(users)
    return fleet_page.FleetView(
        rows=tuple(fleet_page.sort_rows(rows)), owners=owners,
        now=now, access=_access_views(state_dir, principal), **state)


def _page_body(h, query, state):
    view = build_view(h.args.state_dir, principal=h._safe_principal(), **state)
    page = console_fleet_view.page_html(h, query, view)
    return page if _is_system(query) else page + fleet_page.render(view)


def _is_system(query):
    """The System view is a page of its own: no frames list and none of the
    Fleet page's dialogs."""
    return query.get(console_fleet_view.VIEW_QUERY) == [console_fleet_view.VIEW_SYSTEM]


def _render(h, status=200, query=None, **state):
    from companion import console_routes
    system = _is_system(query or {})
    return h._console_page(
        console_routes.FLEET_ROUTE,
        console_fleet_view.SYSTEM_HEADING if system else None,
        lambda: _page_body(h, query or {}, state),
        console_fleet_view.SYSTEM_SUB if system else None, status=status,
        page_flash=console_fleet_view.query_flash_html(h, query or {}),
        omit_title=not system, scripts=console_fleet_view.page_scripts(system))


def handle_fleet_get(h, m):
    from urllib.parse import parse_qs, urlsplit
    query = parse_qs(urlsplit(h.path).query)
    if query.get(fleet_page.PAIR_QUERY_FLAG) == ["1"]:
        # The old Add a frame address: the dialog became the page.
        return h.redirect(PAIR_FRAME_PATH)
    return _render(
        h, query=query,
        open_access=(query.get(co_managers_card.ACCESS_QUERY) or [""])[0])


# ---- register -----------------------------------------------------------


def _normalise_mac(raw):
    """`aa:bb:cc:dd:ee:ff` for a MAC typed with colons, hyphens or none."""
    text = raw.strip().lower().replace("-", ":")
    if _BARE_MAC_RE.match(text):
        text = ":".join(text[i:i + 2] for i in range(0, 12, 2))
    return text if _MAC_RE.match(text) else None


def handle_register(h, m):
    form = h.read_form()
    mac = _normalise_mac(form.get(fleet_page.MAC_FIELD, ""))
    secret_hash = form.get(fleet_page.HASH_FIELD, "").strip().lower()
    hardware_type = form.get(fleet_page.HARDWARE_FIELD, "")
    errors = []
    if mac is None:
        errors.append(i18n.t(fleet_page.REGISTER_MAC_ERROR))
    if not _HASH_RE.match(secret_hash):
        errors.append(i18n.t(fleet_page.REGISTER_HASH_ERROR))
    if hardware_type not in hardware.available_types():
        errors.append(i18n.t(fleet_page.REGISTER_HARDWARE_ERROR))
    if errors:
        # Nothing typed is echoed: a refused paste may be a secret.
        return _render(h, status=400, register_errors=tuple(errors))
    conn = fleet_db.connect(h.args.state_dir)
    try:
        fleet_ops.register_frame(conn, mac, secret_hash, hardware_type, audit.actor_for(h))
    except fleet_ops.DuplicateFrame:
        return h.redirect(FLEET_PATH, set_cookie=console_flash.queue_flash(FLASH_DUPLICATE))
    finally:
        conn.close()
    return h.redirect(FLEET_PATH, set_cookie=console_flash.queue_flash(FLASH_REGISTERED))


# ---- pair ---------------------------------------------------------------


def session_key(h):
    """First 16 hex of sha256 of the raw session token; never the token."""
    token = h._raw_session_token() or ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:_SESSION_KEY_HEX]


def docked_toast(tone, title_msg, detail_msg):
    from companion import ui_components
    return ui_components.toast_html(
        i18n.t(title_msg), i18n.t(detail_msg), tone=tone, docked=True)


def owner_choice(raw):
    """The chosen owner id, or None when it is not a plain integer."""
    text = raw.strip()
    return int(text) if text.isascii() and text.isdigit() and len(text) < 10 else None


def owner_is_active(state_dir, owner_id):
    conn = fleet_db.connect(state_dir)
    try:
        row = conn.execute(
            "SELECT disabled FROM users WHERE id = ?", (owner_id,)).fetchone()
    finally:
        conn.close()
    return row is not None and not row["disabled"]


def audit_refusal(h, transitioned):
    """Audit a refused code (reason enum only, never the guess) and, once, a
    lockout transition."""
    conn = fleet_db.connect(h.args.state_dir)
    try:
        actor = audit.actor_for(h)
        fleet_ops.record_claim_failure(conn, actor, fleet_ops.FAIL_INVALID)
        if transitioned:
            fleet_ops.record_claim_failure(conn, actor, fleet_ops.FAIL_THROTTLED)
    finally:
        conn.close()


def record_refused_attempt(h, key):
    """Advance both throttles (no short-circuit) for a refused code and
    audit it."""
    started_session = SESSION_THROTTLE.record_failure(key)
    started_global = GLOBAL_THROTTLE.record_failure(_GLOBAL_KEY)
    audit_refusal(h, started_session or started_global)


def is_locked(key):
    """True when the session bucket `key` or the global bucket is locked;
    checked before any code is evaluated."""
    return SESSION_THROTTLE.locked_for(key) or GLOBAL_THROTTLE.locked_for(_GLOBAL_KEY)


def claim_code(h, code, owner_id):
    """(device id, frame name, owner email) of the frame the typed `code`
    turns into a device of `owner_id`. Raises fleet_ops.ClaimRefused or
    fleet_ops.OwnerUnavailable."""
    conn = fleet_db.connect(h.args.state_dir)
    try:
        result = fleet_ops.claim_pairing_code(
            conn, h.args.state_dir, code, owner_id, audit.actor_for(h))
        device = fleet_db.get_device(conn, result.device_id)
        owner = conn.execute(
            "SELECT email FROM users WHERE id = ?", (owner_id,)).fetchone()
    finally:
        conn.close()
    # A frame without a name is shown as "Unnamed frame", never by its id.
    frame = (device["name"] if device is not None and device["name"]
             else fleet_page.unnamed_text())
    return result.device_id, frame, owner["email"] if owner is not None else ""


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(FLEET_PATH), handle_fleet_get, route_types.ADMIN_ONLY),
    route_types.Route(
        "POST", route_types.Exact(REGISTER_PATH), handle_register,
        route_types.ADMIN_ONLY, csrf=True),
)
