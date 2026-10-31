"""Admin console routes for the pairing area: the Fleet page, frame
registration and the pairing-code claim.

Security invariants:
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
import os
import re
import sqlite3

from companion import (
    audit, console_flash, device_scope, i18n, route_types, throttle)
from companion.pages import fleet_page
from server import (
    device_dirs, fleet_db, fleet_ops, hardware, history_db, state_store)

# Same literals as companion/console_routes.py (which imports this module, so
# it cannot be imported here); a test pins that the two agree.
FLEET_PATH = "/fleet"
REGISTER_PATH = "/fleet/register"
PAIR_PATH = "/fleet/pair"

SESSION_LIMIT = 5
SESSION_LOCKOUT_S = 300
GLOBAL_LIMIT = 20
GLOBAL_LOCKOUT_S = 900
_GLOBAL_KEY = "pairing-claim"
_SESSION_KEY_HEX = 16
_MAX_ECHOED_CODE = 32

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


def _firmware_version(state_dir):
    """The firmware version of the newest health row, or ""."""
    if not os.path.exists(history_db.history_db_path(state_dir)):
        return ""
    try:
        with history_db.open_db(state_dir) as conn:
            row = history_db.latest_device_health(conn)
    except (OSError, sqlite3.Error):
        return ""
    version = None if row is None else row.get("fw_version")
    return version if isinstance(version, str) else ""


def _percent(millivolts):
    from companion import battery
    return None if millivolts is None else battery.battery_percent(millivolts)


def _hardware_label(key):
    profile = hardware.REGISTRY.get(key)
    return profile.label if profile is not None else key


def _device_rows(state_dir, device_rows, now_epoch):
    by_id = {str(row["id"]): row for row in device_rows}
    rows = []
    for device in device_scope.load_devices(state_dir):
        row = by_id.get(device.id)
        if row is None:
            continue
        status = device_scope.device_status(device, now_epoch)
        rows.append(fleet_page.FleetRow(
            kind=fleet_page.KIND_LIVE, frame_id=device.id,
            name=row["name"] or fleet_page.unnamed_text(), mono_id=device.id,
            owner_email=row["owner_email"], previous_owner=False,
            hardware=_hardware_label(device.hardware_type),
            last_seen=device_scope.last_check_in_epoch(device.state_dir),
            battery_percent=_percent(state_store.load_battery_state(device.state_dir)),
            firmware=_firmware_version(device.state_dir),
            is_live_frame=device.state_path == device_dirs.LIVE_STATE_PATH,
            offline=status == device_scope.STATUS_OFFLINE))
    return rows


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
            battery_percent=_percent(row["battery_mv"]),
            firmware=row["fw_version"] or "",
            is_live_frame=False, offline=False))
    return rows


def _hardware_choices():
    return tuple((key, _hardware_label(key)) for key in hardware.available_types())


def build_view(state_dir, **state):
    """The `FleetView` for the current database plus the form state of a
    refused submission (`state` overrides the form fields)."""
    users, device_rows, pending_rows = _read_all(state_dir)
    now = datetime.datetime.now(datetime.timezone.utc)
    emails = {row["id"]: row["email"] for row in users}
    rows = _device_rows(state_dir, device_rows, now.timestamp())
    rows += _pending_rows(pending_rows, emails)
    owners = tuple(
        (str(row["id"]), fleet_page.owner_label(row["email"], row["role"]))
        for row in users if not row["disabled"])
    return fleet_page.FleetView(
        rows=tuple(fleet_page.sort_rows(rows)), owners=owners,
        hardware_choices=_hardware_choices(),
        has_pending=any(
            row["status"] == fleet_db.PENDING_STATUS_PENDING for row in pending_rows),
        now=now, **state)


def _render(h, status=200, **state):
    from companion import console_routes
    return h._console_page(
        console_routes.FLEET_ROUTE, None,
        lambda: fleet_page.render(build_view(h.args.state_dir, **state)),
        fleet_page.FLEET_PURPOSE, status=status)


def handle_fleet_get(h, m):
    from urllib.parse import parse_qs, urlsplit
    query = parse_qs(urlsplit(h.path).query)
    return _render(h, autofocus_code=query.get(fleet_page.PAIR_QUERY_FLAG) == ["1"])


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
    errors = {}
    if mac is None:
        errors["mac_error"] = i18n.t(fleet_page.REGISTER_MAC_ERROR)
    if not _HASH_RE.match(secret_hash):
        errors["hash_error"] = i18n.t(fleet_page.REGISTER_HASH_ERROR)
    if hardware_type not in hardware.available_types():
        errors["hardware_error"] = i18n.t(fleet_page.REGISTER_HARDWARE_ERROR)
    if errors:
        # The hash field is never echoed: a refused paste may be a secret.
        return _render(
            h, status=400, mac_value=form.get(fleet_page.MAC_FIELD, "")[:32],
            hardware_selected=hardware_type[:64], **errors)
    conn = fleet_db.connect(h.args.state_dir)
    try:
        fleet_ops.register_frame(conn, mac, secret_hash, hardware_type, audit.actor_for(h))
    except fleet_ops.DuplicateFrame:
        return h.redirect(FLEET_PATH, set_cookie=console_flash.queue_flash(FLASH_DUPLICATE))
    finally:
        conn.close()
    return h.redirect(FLEET_PATH, set_cookie=console_flash.queue_flash(FLASH_REGISTERED))


# ---- pair ---------------------------------------------------------------


def _session_key(h):
    """First 16 hex of sha256 of the raw session token; never the token."""
    token = h._raw_session_token() or ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:_SESSION_KEY_HEX]


def _docked(tone, title_msg, detail_msg):
    from companion import ui_components
    return ui_components.toast_html(
        i18n.t(title_msg), i18n.t(detail_msg), tone=tone, docked=True)


def _owner_choice(raw):
    """The chosen owner id, or None when it is not a plain integer."""
    text = raw.strip()
    return int(text) if text.isascii() and text.isdigit() and len(text) < 10 else None


def _owner_is_active(state_dir, owner_id):
    conn = fleet_db.connect(state_dir)
    try:
        row = conn.execute(
            "SELECT disabled FROM users WHERE id = ?", (owner_id,)).fetchone()
    finally:
        conn.close()
    return row is not None and not row["disabled"]


def _echoed_code(raw):
    return raw.strip().upper()[:_MAX_ECHOED_CODE]


def _refuse_claim(h, code, owner_raw, transitioned):
    """The one answer for a refused code; audits the failure (reason enum
    only) and a lockout transition once."""
    conn = fleet_db.connect(h.args.state_dir)
    try:
        actor = audit.actor_for(h)
        fleet_ops.record_claim_failure(conn, actor, fleet_ops.FAIL_INVALID)
        if transitioned:
            fleet_ops.record_claim_failure(conn, actor, fleet_ops.FAIL_THROTTLED)
    finally:
        conn.close()
    return _render(
        h, status=200, code_value=_echoed_code(code), owner_selected=owner_raw.strip(),
        claim_toast_html=_docked(
            "error", fleet_page.CLAIM_REFUSED_TITLE, fleet_page.CLAIM_REFUSED_DETAIL),
        code_error=i18n.t(fleet_page.CLAIM_CODE_ERROR))


def _field_failure(h, code, owner_raw, **errors):
    return _render(
        h, status=400, code_value=_echoed_code(code), owner_selected=owner_raw.strip(),
        **errors)


def _claim(h, code, owner_id):
    conn = fleet_db.connect(h.args.state_dir)
    try:
        result = fleet_ops.claim_pairing_code(
            conn, h.args.state_dir, code, owner_id, audit.actor_for(h))
        device = fleet_db.get_device(conn, result.device_id)
        owner = conn.execute(
            "SELECT email FROM users WHERE id = ?", (owner_id,)).fetchone()
    finally:
        conn.close()
    frame = (device["name"] if device is not None and device["name"] else result.device_id)
    return frame, owner["email"] if owner is not None else ""


def handle_pair(h, m):
    form = h.read_form()
    code = form.get(fleet_page.CODE_FIELD, "")
    owner_raw = form.get(fleet_page.OWNER_FIELD, "")
    owner_id = _owner_choice(owner_raw)
    errors = {}
    if not code.strip():
        errors["code_error"] = i18n.t(fleet_page.CLAIM_EMPTY_CODE)
    if owner_id is None:
        errors["owner_error"] = i18n.t(fleet_page.CLAIM_EMPTY_OWNER)
    if errors:
        return _field_failure(h, code, owner_raw, **errors)
    key = _session_key(h)
    if SESSION_THROTTLE.locked_for(key) or GLOBAL_THROTTLE.locked_for(_GLOBAL_KEY):
        return _render(
            h, status=429, code_value=_echoed_code(code), owner_selected=owner_raw.strip(),
            claim_toast_html=_docked(
                "warning", fleet_page.CLAIM_THROTTLED_TITLE,
                fleet_page.CLAIM_THROTTLED_DETAIL))
    if not _owner_is_active(h.args.state_dir, owner_id):
        return _field_failure(
            h, code, owner_raw, owner_error=i18n.t(fleet_page.CLAIM_OWNER_GONE))
    try:
        frame, email = _claim(h, code, owner_id)
    except fleet_ops.ClaimRefused:
        # Both counters always advance (no short-circuit).
        started_session = SESSION_THROTTLE.record_failure(key)
        started_global = GLOBAL_THROTTLE.record_failure(_GLOBAL_KEY)
        return _refuse_claim(h, code, owner_raw, started_session or started_global)
    except fleet_ops.OwnerUnavailable:
        return _field_failure(
            h, code, owner_raw, owner_error=i18n.t(fleet_page.CLAIM_OWNER_GONE))
    SESSION_THROTTLE.record_success(key)
    return h.redirect(
        FLEET_PATH, set_cookie=console_flash.queue_flash(
            FLASH_PAIRED, frame=frame, email=email))


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(FLEET_PATH), handle_fleet_get, route_types.ADMIN_ONLY),
    route_types.Route(
        "POST", route_types.Exact(REGISTER_PATH), handle_register,
        route_types.ADMIN_ONLY, csrf=True),
    route_types.Route(
        "POST", route_types.Exact(PAIR_PATH), handle_pair,
        route_types.ADMIN_ONLY, csrf=True),
)
